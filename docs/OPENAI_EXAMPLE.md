# OpenAI tool-call recipe

This Python recipe sends one real request to OpenAI's Responses API. The request
forces a call to `lookup_docs`, then the example runs that local tool. Its first
execution raises a synthetic timeout and its retry succeeds. The provider's
call ID links both attempts. The recipe ends after the tool succeeds.

OpenAI's Responses API provides the tool-call ID and token-usage metadata this
recipe traces. The standard-library HTTP call keeps the request and attribute
mapping visible in one file and adds no dependencies. The `chat` span is created
manually so the example also shows how to instrument a provider call directly.

## Run

Install the Python dependencies using the main README. Have your secret manager
inject `OPENAI_API_KEY` into the process environment and set `OPENAI_MODEL` to
a model available to your account that supports function calling.

With 1Password CLI, create a file outside the repository containing secret
references, for example:

```text
OPENAI_API_KEY=op://your-vault/your-provider-item/credential
OPENAI_MODEL=your-model-id
```

From the `python` directory, with its virtual environment active:

```sh
op run --env-file /path/to/provider-references.env -- python openai_example.py
```

Your secret manager resolves the key at launch. Keep resolved secrets out of
shell history and repository files. The recipe sends a fixed synthetic prompt
to `https://api.openai.com/v1/responses`. Each run makes one billable request,
with a 256-output-token limit and a 60-second network timeout.

The request uses `store=false`. Prompt text, tool arguments, provider response
content, and credentials are omitted from the spans. Provider transport and
response-validation failures mark the model span as ERROR and stop the run.
HTTP failures use their status code as `error.type` and include it in the error
message. Other failures use `timeout`, `connection_error`, or `invalid_response`.
For example, HTTP 401 indicates an authentication failure, HTTP 404 can indicate
an unavailable model, and HTTP 429 indicates a rate or quota limit.

## Inspect

A successful run exports four spans:

- An OK `invoke_agent docs_agent` parent.
- An OK `chat <model>` child with the response ID, actual model, input and output
  token counts, and cached-input and reasoning counts when returned by OpenAI.
- An ERROR `execute_tool lookup_docs` child with `error.type=timeout`.
- An OK `execute_tool lookup_docs` child with the same provider call ID.

Trace IDs, call IDs, timing, model identifiers, and token counts vary.
The same `OTEL_*` settings and PackDB Cloud walkthrough from the main README
apply. The console export includes `gen_ai.response.id`. With PackDB’s default
policy, profiles v1 and v2 remove the ID, while v3 and later retain it on the
source span. Check `genai_operations.profile_version` for the profile applied
to your row, then open its span to inspect the ID.
Query `operation = 'execute_tool'` for the two attempts or include
`operation = 'chat'` to inspect the real model invocation.

The default Python and TypeScript examples remain deterministic. CI tests the
OpenAI request contract with synthetic provider responses and checks failure
handling without a provider key. Live provider runs are manual.

The request follows the official
[OpenAI function-calling guide](https://developers.openai.com/api/docs/guides/function-calling).
