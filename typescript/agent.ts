// Copyright 2026 PackDB Contributors
// Licensed under the Apache License, Version 2.0

import { randomUUID } from "node:crypto";
import { SpanStatusCode, trace } from "@opentelemetry/api";

function stubModel() {
  return { name: "lookup_docs", id: randomUUID() };
}

class ToolTimeout extends Error {}

function lookupDocs(attempt: number): string {
  if (attempt === 1) throw new ToolTimeout("synthetic timeout");
  return "Use the trace ID to find both attempts.";
}

export function runAgent(): string {
  const tracer = trace.getTracer("agent_examples.tool_retry");
  return tracer.startActiveSpan(
    "invoke_agent docs_agent",
    {
      attributes: {
        "gen_ai.operation.name": "invoke_agent",
        "gen_ai.agent.name": "docs_agent",
      },
    },
    (parent) => {
      try {
        const tool = stubModel();
        for (const attempt of [1, 2]) {
          const child = tracer.startSpan(`execute_tool ${tool.name}`, {
            attributes: {
              "gen_ai.operation.name": "execute_tool",
              "gen_ai.tool.name": tool.name,
              "gen_ai.tool.call.id": tool.id,
            },
          });
          try {
            lookupDocs(attempt);
            child.setStatus({ code: SpanStatusCode.OK });
            break;
          } catch (error) {
            if (!(error instanceof ToolTimeout)) throw error;
            child.setAttribute("error.type", "timeout");
            child.setStatus({ code: SpanStatusCode.ERROR });
            if (attempt === 2) throw error;
          } finally {
            child.end();
          }
        }
        parent.setStatus({ code: SpanStatusCode.OK });
        return parent.spanContext().traceId;
      } catch (error) {
        parent.setStatus({ code: SpanStatusCode.ERROR });
        throw error;
      } finally {
        parent.end();
      }
    },
  );
}
