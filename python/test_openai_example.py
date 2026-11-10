# Copyright 2026 PackDB Contributors
# Licensed under the Apache License, Version 2.0

import copy
import io
import json
import os
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch
from urllib.error import HTTPError

import openai_example
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace import StatusCode

RESPONSE = {
    "model": "test-model",
    "output": [
        {
            "type": "function_call",
            "name": "lookup_docs",
            "call_id": "provider-call-123",
            "arguments": "{}",
        }
    ],
    "usage": {"input_tokens": 23, "output_tokens": 7},
}


class OpenAIExampleTest(unittest.TestCase):
    def setUp(self):
        self.exporter = InMemorySpanExporter()
        self.provider = TracerProvider()
        self.provider.add_span_processor(SimpleSpanProcessor(self.exporter))
        self.addCleanup(self.provider.shutdown)
        self.enterContext(
            patch.dict(
                os.environ,
                {
                    "OPENAI_API_KEY": "synthetic-provider-key",
                    "OPENAI_MODEL": "test-model",
                },
            )
        )
        self.enterContext(
            patch.object(
                openai_example.trace,
                "get_tracer",
                return_value=self.provider.get_tracer("test"),
            )
        )

    def test_provider_call_drives_the_retry(self):
        def respond(request, timeout):
            self.assertEqual(request.full_url, "https://api.openai.com/v1/responses")
            self.assertEqual(request.get_method(), "POST")
            self.assertEqual(
                request.get_header("Authorization"), "Bearer synthetic-provider-key"
            )
            self.assertEqual(timeout, 60)
            body = json.loads(request.data)
            self.assertFalse(body["store"])
            self.assertFalse(body["parallel_tool_calls"])
            self.assertEqual(body["max_output_tokens"], 256)
            self.assertEqual(body["model"], "test-model")
            self.assertEqual(
                body["tool_choice"], {"type": "function", "name": "lookup_docs"}
            )
            self.assertNotIn("synthetic-provider-key", request.data.decode())
            return io.BytesIO(json.dumps(RESPONSE).encode())

        with (
            patch.object(openai_example, "urlopen", side_effect=respond),
            patch.object(openai_example, "configure_telemetry"),
            patch.object(
                openai_example.trace, "get_tracer_provider", return_value=self.provider
            ),
            redirect_stdout(io.StringIO()) as stdout,
        ):
            openai_example.main()

        model, failed, succeeded, parent = self.exporter.get_finished_spans()
        self.assertIn(format(parent.context.trace_id, "032x"), stdout.getvalue())
        self.assertEqual(model.name, "chat test-model")
        self.assertEqual(model.status.status_code, StatusCode.OK)
        self.assertEqual(model.attributes["gen_ai.usage.input_tokens"], 23)
        self.assertEqual(model.attributes["gen_ai.usage.output_tokens"], 7)
        self.assertEqual(model.attributes["gen_ai.response.model"], "test-model")
        self.assertEqual(parent.status.status_code, StatusCode.OK)
        for child in (model, failed, succeeded):
            self.assertEqual(child.parent, parent.context)
            self.assertFalse(child.events)
        self.assertEqual(failed.status.status_code, StatusCode.ERROR)
        self.assertEqual(succeeded.status.status_code, StatusCode.OK)
        for tool in (failed, succeeded):
            self.assertEqual(
                tool.attributes["gen_ai.tool.call.id"], "provider-call-123"
            )
        self.assertEqual(
            set(model.attributes),
            {
                "gen_ai.operation.name",
                "gen_ai.provider.name",
                "gen_ai.request.model",
                "gen_ai.response.model",
                "gen_ai.usage.input_tokens",
                "gen_ai.usage.output_tokens",
            },
        )

    def test_provider_error_does_not_capture_response_content(self):
        error = HTTPError(
            "https://api.openai.com/v1/responses",
            401,
            "private-response-content",
            {},
            io.BytesIO(b"private body"),
        )
        with (
            patch.object(openai_example, "urlopen", side_effect=error),
            self.assertRaisesRegex(RuntimeError, "OpenAI model call failed") as caught,
        ):
            openai_example.request_tool()
        self.assertNotIn("private", str(caught.exception))
        (span,) = self.exporter.get_finished_spans()
        self.assertEqual(span.status.status_code, StatusCode.ERROR)
        self.assertEqual(span.attributes["error.type"], "HTTPError")
        self.assertFalse(span.events)

    def test_rejects_unexpected_tool_calls(self):
        for output in (
            [],
            [
                {
                    "type": "function_call",
                    "name": "other",
                    "call_id": "x",
                    "arguments": "{}",
                }
            ],
        ):
            with self.subTest(output=output):
                result = copy.deepcopy(RESPONSE)
                result["output"] = output
                with (
                    patch.object(
                        openai_example,
                        "urlopen",
                        return_value=io.BytesIO(json.dumps(result).encode()),
                    ),
                    self.assertRaises(RuntimeError),
                ):
                    openai_example.request_tool()

    def test_requires_credentials_and_model(self):
        with (
            patch.dict(os.environ, {}, clear=True),
            patch.object(openai_example, "configure_telemetry") as configure,
        ):
            with self.assertRaisesRegex(SystemExit, "OPENAI_API_KEY and OPENAI_MODEL"):
                openai_example.main()
            configure.assert_not_called()
