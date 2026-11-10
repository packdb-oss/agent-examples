# Copyright 2026 PackDB Contributors
# Licensed under the Apache License, Version 2.0

import os

from agent import run_agent
from opentelemetry import trace
from opentelemetry.instrumentation.auto_instrumentation import initialize


def configure_telemetry() -> None:
    os.environ.setdefault("OTEL_TRACES_EXPORTER", "console")
    os.environ.setdefault("OTEL_EXPORTER_OTLP_PROTOCOL", "http/protobuf")
    os.environ.setdefault("OTEL_METRICS_EXPORTER", "none")
    os.environ.setdefault("OTEL_LOGS_EXPORTER", "none")
    os.environ.setdefault("OTEL_SERVICE_NAME", "docs-agent-python")
    initialize(swallow_exceptions=False)


def main() -> None:
    configure_telemetry()
    try:
        trace_id = run_agent()
    finally:
        trace.get_tracer_provider().shutdown()
    print(
        f"lookup_docs timed out on attempt 1 and succeeded on attempt 2. Trace ID: {trace_id}"
    )


if __name__ == "__main__":
    main()
