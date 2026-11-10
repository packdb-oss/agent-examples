# Copyright 2026 PackDB Contributors
# Licensed under the Apache License, Version 2.0

import json
import os
from http.client import HTTPException
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from agent import run_agent
from main import configure_telemetry
from opentelemetry import trace
from opentelemetry.trace import SpanKind, StatusCode


def request_tool() -> tuple[str, str]:
    api_key = os.environ["OPENAI_API_KEY"]
    model = os.environ["OPENAI_MODEL"]
    tracer = trace.get_tracer("agent_examples.openai")
    with tracer.start_as_current_span(
        f"chat {model}",
        kind=SpanKind.CLIENT,
        attributes={
            "gen_ai.operation.name": "chat",
            "gen_ai.provider.name": "openai",
            "gen_ai.request.model": model,
        },
        record_exception=False,
    ) as span:
        try:
            payload = {
                "model": model,
                "input": "Find documentation explaining how to inspect a trace by ID.",
                "tools": [
                    {
                        "type": "function",
                        "name": "lookup_docs",
                        "description": "Look up the trace inspection documentation.",
                        "parameters": {
                            "type": "object",
                            "properties": {},
                            "required": [],
                            "additionalProperties": False,
                        },
                        "strict": True,
                    }
                ],
                "tool_choice": {"type": "function", "name": "lookup_docs"},
                "store": False,
                "parallel_tool_calls": False,
                "max_output_tokens": 256,
            }
            request = Request(
                "https://api.openai.com/v1/responses",
                data=json.dumps(payload).encode(),
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
            )
            with urlopen(request, timeout=60) as response:
                result = json.load(response)
            calls = [
                item for item in result["output"] if item["type"] == "function_call"
            ]
            if len(calls) != 1:
                raise ValueError("Expected one tool call")
            call = calls[0]
            if (
                call["name"] != "lookup_docs"
                or not isinstance(call["call_id"], str)
                or not call["call_id"]
                or json.loads(call["arguments"]) != {}
            ):
                raise ValueError("Unexpected tool call")
            span.set_attribute("gen_ai.response.model", result["model"])
            span.set_attribute("gen_ai.response.id", result["id"])
            usage = result.get("usage") or {}
            token_counts = {
                "input_tokens": usage.get("input_tokens"),
                "output_tokens": usage.get("output_tokens"),
                "cached_input_tokens": (usage.get("input_tokens_details") or {}).get(
                    "cached_tokens"
                ),
                "reasoning_tokens": (usage.get("output_tokens_details") or {}).get(
                    "reasoning_tokens"
                ),
            }
            for name, value in token_counts.items():
                if value is not None:
                    span.set_attribute(f"gen_ai.usage.{name}", value)
            span.set_status(StatusCode.OK)
            return call["name"], call["call_id"]
        except (
            OSError,
            HTTPException,
            ValueError,
            KeyError,
            TypeError,
            AttributeError,
        ) as error:
            if isinstance(error, HTTPError):
                error_type = str(error.code)
                detail = f"HTTP {error.code}"
            elif isinstance(error, TimeoutError) or (
                isinstance(error, URLError) and isinstance(error.reason, TimeoutError)
            ):
                error_type = detail = "timeout"
            elif isinstance(error, (OSError, HTTPException)):
                error_type = detail = "connection_error"
            else:
                error_type = detail = "invalid_response"
            span.set_attribute("error.type", error_type)
            span.set_status(StatusCode.ERROR)
            raise RuntimeError(f"OpenAI model call failed ({detail}).") from None


def main() -> None:
    if not os.environ.get("OPENAI_API_KEY") or not os.environ.get("OPENAI_MODEL"):
        raise SystemExit(
            "OPENAI_API_KEY and OPENAI_MODEL must be set in the environment"
        )
    configure_telemetry()
    try:
        trace_id = run_agent(request_tool)
    finally:
        trace.get_tracer_provider().shutdown()
    print(
        f"OpenAI requested lookup_docs, which timed out once and succeeded on retry. Trace ID: {trace_id}"
    )


if __name__ == "__main__":
    main()
