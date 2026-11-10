# Copyright 2026 PackDB Contributors
# Licensed under the Apache License, Version 2.0

import os
import queue
import re
import shutil
import subprocess
import sys
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import (
    ExportTraceServiceRequest,
)

ROOT = Path(__file__).resolve().parents[1]


class ExportTest(unittest.TestCase):
    def test_console_summary_follows_all_spans(self):
        env = {k: v for k, v in os.environ.items() if not k.startswith("OTEL_")}
        for directory, command in [
            ("python", [sys.executable, "main.py"]),
            ("typescript", [shutil.which("npm"), "start", "--silent"]),
        ]:
            with self.subTest(language=directory):
                result = subprocess.run(
                    command,
                    cwd=ROOT / directory,
                    env=env,
                    text=True,
                    capture_output=True,
                    check=True,
                    timeout=30,
                )
                lines = result.stdout.strip().splitlines()
                self.assertRegex(
                    lines[-1],
                    r"^lookup_docs timed out on attempt 1 and succeeded on attempt 2\. Trace ID: [0-9a-f]{32}$",
                )
                span_output = "\n".join(lines[:-1])
                self.assertEqual(span_output.count("execute_tool lookup_docs"), 2)
                self.assertEqual(span_output.count("invoke_agent docs_agent"), 1)
                self.assertEqual(result.stdout.count("Trace ID:"), 1)

    def test_launchers_deliver_three_spans(self):
        requests = queue.Queue()

        class Receiver(BaseHTTPRequestHandler):
            def do_POST(self):
                if self.headers.get("Transfer-Encoding") == "chunked":
                    chunks = []
                    while size := int(self.rfile.readline().strip(), 16):
                        chunks.append(self.rfile.read(size))
                        self.rfile.read(2)
                    self.rfile.readline()
                    body = b"".join(chunks)
                else:
                    body = self.rfile.read(int(self.headers["Content-Length"]))
                requests.put((self.path, self.headers, body))
                self.send_response(200)
                self.send_header("Content-Type", "application/x-protobuf")
                self.end_headers()

            def log_message(self, *args):
                pass

        with ThreadingHTTPServer(("127.0.0.1", 0), Receiver) as receiver:
            thread = threading.Thread(target=receiver.serve_forever)
            thread.start()
            try:
                env = {k: v for k, v in os.environ.items() if not k.startswith("OTEL_")}
                env.update(
                    OTEL_TRACES_EXPORTER="otlp",
                    OTEL_EXPORTER_OTLP_ENDPOINT=f"http://127.0.0.1:{receiver.server_port}",
                    OTEL_EXPORTER_OTLP_HEADERS="x-api-key=synthetic-test-key",
                )
                for directory, command in [
                    ("python", [sys.executable, "main.py"]),
                    ("typescript", [shutil.which("npm"), "start", "--silent"]),
                ]:
                    with self.subTest(language=directory):
                        result = subprocess.run(
                            command,
                            cwd=ROOT / directory,
                            env=env,
                            text=True,
                            stdout=subprocess.PIPE,
                            check=True,
                            timeout=30,
                        )
                        trace_id = re.search(r"Trace ID: ([0-9a-f]{32})", result.stdout)
                        self.assertIsNotNone(trace_id)
                        spans = []
                        while not requests.empty():
                            path, headers, body = requests.get_nowait()
                            self.assertEqual(path, "/v1/traces")
                            self.assertEqual(headers["X-API-Key"], "synthetic-test-key")
                            self.assertEqual(
                                headers.get_content_type(), "application/x-protobuf"
                            )
                            batch = ExportTraceServiceRequest.FromString(body)
                            spans.extend(
                                span
                                for resource in batch.resource_spans
                                for scope in resource.scope_spans
                                for span in scope.spans
                            )
                        self.assertCountEqual(
                            [s.name for s in spans],
                            [
                                "invoke_agent docs_agent",
                                "execute_tool lookup_docs",
                                "execute_tool lookup_docs",
                            ],
                        )
                        parent = next(
                            s for s in spans if s.name == "invoke_agent docs_agent"
                        )
                        first, second = sorted(
                            (s for s in spans if s.name == "execute_tool lookup_docs"),
                            key=lambda s: s.start_time_unix_nano,
                        )
                        self.assertEqual(parent.parent_span_id, b"")
                        self.assertEqual(parent.status.code, 1)
                        self.assertEqual(first.status.code, 2)
                        self.assertEqual(second.status.code, 1)
                        for child in (first, second):
                            self.assertEqual(child.parent_span_id, parent.span_id)
                        self.assertEqual(len({s.span_id for s in spans}), 3)
                        attrs = [
                            {a.key: a.value.string_value for a in s.attributes}
                            for s in (first, second)
                        ]
                        for fields in attrs:
                            self.assertEqual(
                                fields["gen_ai.operation.name"], "execute_tool"
                            )
                            self.assertEqual(fields["gen_ai.tool.name"], "lookup_docs")
                            self.assertTrue(fields["gen_ai.tool.call.id"])
                        self.assertEqual(
                            attrs[0]["gen_ai.tool.call.id"],
                            attrs[1]["gen_ai.tool.call.id"],
                        )
                        self.assertEqual(attrs[0]["error.type"], "timeout")
                        self.assertNotIn("error.type", attrs[1])
                        parent_attrs = {
                            a.key: a.value.string_value for a in parent.attributes
                        }
                        self.assertEqual(
                            parent_attrs["gen_ai.operation.name"], "invoke_agent"
                        )
                        self.assertNotIn("error.type", parent_attrs)
                        for span in spans:
                            self.assertEqual(span.trace_id.hex(), trace_id[1])
                            self.assertFalse(span.events)
                            fields = {a.key for a in span.attributes}
                            self.assertLessEqual(
                                fields,
                                {
                                    "gen_ai.operation.name",
                                    "gen_ai.agent.name",
                                    "gen_ai.tool.name",
                                    "gen_ai.tool.call.id",
                                    "error.type",
                                },
                            )
            finally:
                receiver.shutdown()
                thread.join()
