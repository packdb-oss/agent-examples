// Copyright 2026 PackDB Contributors
// Licensed under the Apache License, Version 2.0

import { NodeSDK } from "@opentelemetry/sdk-node";
import { runAgent } from "./agent.ts";

process.env.OTEL_TRACES_EXPORTER ??= "console";
process.env.OTEL_EXPORTER_OTLP_PROTOCOL ??= "http/protobuf";
process.env.OTEL_METRICS_EXPORTER ??= "none";
process.env.OTEL_LOGS_EXPORTER ??= "none";
process.env.OTEL_NODE_RESOURCE_DETECTORS ??= "env";
process.env.OTEL_SERVICE_NAME ??= "docs-agent-node";

const sdk = new NodeSDK();
sdk.start();
let traceId: string;
try {
  traceId = runAgent();
} finally {
  await sdk.shutdown();
}
console.log(
  `lookup_docs timed out on attempt 1 and succeeded on attempt 2. Trace ID: ${traceId}`,
);
