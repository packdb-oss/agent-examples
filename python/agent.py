# Copyright 2026 PackDB Contributors
# Licensed under the Apache License, Version 2.0

from uuid import uuid4

from opentelemetry import trace
from opentelemetry.trace import StatusCode


def stub_model() -> tuple[str, str]:
    return "lookup_docs", uuid4().hex


def lookup_docs(attempt: int) -> str:
    if attempt == 1:
        raise TimeoutError("synthetic timeout")
    return "Use the trace ID to find both attempts."


def run_agent() -> str:
    tracer = trace.get_tracer("agent_examples.tool_retry")
    with tracer.start_as_current_span(
        "invoke_agent docs_agent",
        attributes={
            "gen_ai.operation.name": "invoke_agent",
            "gen_ai.agent.name": "docs_agent",
        },
    ) as parent:
        tool_name, call_id = stub_model()
        for attempt in (1, 2):
            with tracer.start_as_current_span(
                f"execute_tool {tool_name}",
                attributes={
                    "gen_ai.operation.name": "execute_tool",
                    "gen_ai.tool.name": tool_name,
                    "gen_ai.tool.call.id": call_id,
                },
            ) as child:
                try:
                    lookup_docs(attempt)
                except TimeoutError:
                    child.set_attribute("error.type", "timeout")
                    child.set_status(StatusCode.ERROR)
                    if attempt == 2:
                        raise
                else:
                    child.set_status(StatusCode.OK)
                    break
        parent.set_status(StatusCode.OK)
        return format(parent.get_span_context().trace_id, "032x")
