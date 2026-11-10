// Copyright 2026 PackDB Contributors
// Licensed under the Apache License, Version 2.0

import assert from "node:assert/strict";
import test from "node:test";
import { SpanStatusCode } from "@opentelemetry/api";
import {
  InMemorySpanExporter,
  NodeTracerProvider,
  SimpleSpanProcessor,
} from "@opentelemetry/sdk-trace-node";
import { runAgent } from "./agent.ts";

test("retry preserves the tool request and records both outcomes", async (t) => {
  const exporter = new InMemorySpanExporter();
  const provider = new NodeTracerProvider({
    spanProcessors: [new SimpleSpanProcessor(exporter)],
  });
  provider.register();
  t.after(() => provider.shutdown());

  const traceId = runAgent();
  const spans = exporter.getFinishedSpans();
  assert.equal(spans.length, 3);
  const [first, second, parent] = spans;
  assert.equal(parent.name, "invoke_agent docs_agent");
  assert.equal(parent.parentSpanContext, undefined);
  assert.equal(parent.status.code, SpanStatusCode.OK);
  assert.equal(parent.spanContext().traceId, traceId);
  for (const child of [first, second]) {
    assert.equal(child.name, "execute_tool lookup_docs");
    assert.equal(child.parentSpanContext?.spanId, parent.spanContext().spanId);
    assert.equal(child.spanContext().traceId, traceId);
  }
  assert.notEqual(first.spanContext().spanId, second.spanContext().spanId);
  assert.ok(first.attributes["gen_ai.tool.call.id"]);
  assert.equal(
    first.attributes["gen_ai.tool.call.id"],
    second.attributes["gen_ai.tool.call.id"],
  );
  assert.equal(first.status.code, SpanStatusCode.ERROR);
  assert.equal(first.attributes["error.type"], "timeout");
  assert.equal(second.status.code, SpanStatusCode.OK);
  assert.equal(second.attributes["error.type"], undefined);
});
