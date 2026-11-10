# Agent examples

An agent asks `lookup_docs` for a document. Its first attempt times out. Its
second attempt succeeds. The agent reports success in both the Python and
TypeScript examples. The failed child span tells you it took a retry.

## Run locally

Choose one implementation. Both use a stub model, raise the first timeout
immediately, and export spans to the console. No account or server is required.

**Python 3.13** — from the repository root:

```sh
cd python
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python main.py
```

On Windows PowerShell, activate with `.\.venv\Scripts\Activate.ps1`.
Use `python` for environment creation on Windows. Use a fresh virtual
environment so the distro loads only the pinned packages.

**Node.js 22.18 or newer** — from the repository root:

```sh
cd typescript
npm ci
npm start
```

After the three spans, the example prints:

```text
lookup_docs timed out on attempt 1 and succeeded on attempt 2. Trace ID: <32 hex digits>
```

The two `execute_tool lookup_docs` spans share a trace ID, parent span ID and
`gen_ai.tool.call.id`. Their span IDs differ because each records one execution.
The first child has status ERROR and `error.type=timeout`. The second child
and the `invoke_agent docs_agent` parent have status OK. Neither example
records prompts, responses, tool arguments or tool results.

For a real provider invocation, see the [OpenAI recipe](docs/OPENAI_EXAMPLE.md).
It uses a provider key supplied through the environment.

## Send the trace to a backend

Set these standard OpenTelemetry variables in the process environment, then run
the same command again. The following values target a local OTLP/HTTP collector:

```text
OTEL_TRACES_EXPORTER=otlp
OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318
```

Use the base URL for `OTEL_EXPORTER_OTLP_ENDPOINT`. The HTTP exporter appends
`/v1/traces`. If your backend supplies a complete trace URL, set
`OTEL_EXPORTER_OTLP_TRACES_ENDPOINT=http://localhost:4318/v1/traces` instead.
A traces-specific setting takes precedence over its general counterpart.

Python supports `grpc` and `http/protobuf`. Node also supports `http/json`.
Both launchers default to HTTP/protobuf for OTLP. Python rejects an unsupported
protocol; the pinned Node SDK can warn and fall back to HTTP/protobuf.
Node defaults to the synchronous `env` resource detector so console spans finish
printing before the summary. Host and process details are omitted by default.
Setting `OTEL_NODE_RESOURCE_DETECTORS=all` restores those details and can cause
the summary to print before the console spans.
Metrics and logs are disabled by default. To return to local output, set
`OTEL_TRACES_EXPORTER=console`.

### Find the recovered failure in PackDB Cloud

1. Set the OTLP base URL to your workspace's HTTPS ingest endpoint. Configure
   your secret manager to inject `OTEL_EXPORTER_OTLP_HEADERS` with the value
   `x-api-key=<ingest key>`. A PackDB ingest key uses the `X-API-Key` header.
2. Run the example and copy the printed trace ID. In the signed-in dashboard
   open `/dashboard/traces/detail?trace=<trace-id>`. Expand the two tool spans.
   The errored span has `error.type=timeout`; the sibling with the same call ID
   shows where the retry succeeded.
3. To inspect both attempts as rows, open the workspace SQL console and replace
   the trace placeholder below with the printed lowercase ID. Select a window
   covering the run. Click the `genai_operations` template to get its UTC start
   and end bounds, then copy those values into the query.

```sql
SELECT tool_name, tool_call_id, span_status_code, error_type, start_time_unix_nano
FROM genai_operations
WHERE trace_id = decode('<trace-id>', 'hex')
  AND operation = 'execute_tool'
  AND start_time_unix_nano >= TIMESTAMP '<window-start-utc>'
  AND start_time_unix_nano <= TIMESTAMP '<window-end-utc>'
ORDER BY start_time_unix_nano, span_status_code DESC;
```

This query is for the dashboard SQL console, whose validator converts the
UTC timestamp bounds to integer nanoseconds. For CLI, HTTP SQL or MCP clients,
replace each timestamp literal with its Unix epoch nanosecond integer.

The status tie-breaker puts the failed attempt first when timestamps match.
Expect two rows with the same tool call ID. In order, their status codes are
`2` (ERROR) and `1` (OK), and their error types are `timeout` and NULL.
Check any reported partial-result causes before interpreting a missing row.
PackDB's MCP GenAI reliability query counts one tool-call failure for this
trace even though the overall agent run succeeded.

## Compatibility

The manual spans use OpenTelemetry semantic conventions `v1.43.0` and GenAI
conventions at
[`2e994c6`](https://github.com/open-telemetry/semantic-conventions-genai/tree/2e994c6d59a93bb4fc1752c5378eedb9b8e14d6b).
These attributes are also recognized by PackDB's `packdb.genai.v2` profile.
Each backend controls how it stores and displays the spans.

See [contributing](CONTRIBUTING.md) for the review process and
[code standards](CODING_STANDARDS.md) for the test commands. First-party
source is licensed under [Apache 2.0](LICENSE).
