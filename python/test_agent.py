# Copyright 2026 PackDB Contributors
# Licensed under the Apache License, Version 2.0

import unittest

from agent import run_agent
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace import StatusCode


class ToolRetryTest(unittest.TestCase):
    def test_retry_preserves_tool_identity(self):
        exporter = InMemorySpanExporter()
        provider = TracerProvider()
        provider.add_span_processor(SimpleSpanProcessor(exporter))
        trace.set_tracer_provider(provider)
        self.addCleanup(provider.shutdown)
        trace_id = run_agent()
        first, second, parent = exporter.get_finished_spans()
        self.assertEqual(parent.name, "invoke_agent docs_agent")
        self.assertIsNone(parent.parent)
        self.assertEqual(parent.status.status_code, StatusCode.OK)
        self.assertEqual(trace_id, format(parent.context.trace_id, "032x"))
        for attempt in (first, second):
            self.assertEqual(attempt.parent, parent.context)
            self.assertEqual(attempt.name, "execute_tool lookup_docs")
        self.assertNotEqual(first.context.span_id, second.context.span_id)
        self.assertEqual(
            first.attributes["gen_ai.tool.call.id"],
            second.attributes["gen_ai.tool.call.id"],
        )
        self.assertEqual(first.status.status_code, StatusCode.ERROR)
        self.assertEqual(first.attributes["error.type"], "timeout")
        self.assertEqual(second.status.status_code, StatusCode.OK)
        self.assertNotIn("error.type", second.attributes)
