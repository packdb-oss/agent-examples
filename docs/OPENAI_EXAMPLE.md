# OpenAI tool-call recipe

This Python recipe sends one real request to OpenAI's Responses API. The request
forces a call to `lookup_docs`, then the example runs that local tool. Its first
execution raises a synthetic timeout and its retry succeeds. The provider's
call ID links both attempts. The recipe ends after the tool succeeds.

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

## Inspect

A successful run exports four spans:

- An OK `invoke_agent docs_agent` parent.
- An OK `chat <model>` child with the actual response model and token usage.
- An ERROR `execute_tool lookup_docs` child with `error.type=timeout`.
- An OK `execute_tool lookup_docs` child with the same provider call ID.

Trace IDs, call IDs, timing, model identifiers, and token counts vary.
The same `OTEL_*` settings and PackDB Cloud walkthrough from the main README
apply. Query `operation = 'execute_tool'` for the two attempts or include
`operation = 'chat'` to inspect the real model invocation.

The default Python and TypeScript examples remain deterministic. CI tests the
OpenAI request contract with synthetic provider responses and checks failure
handling without a provider key. Live provider runs are manual.

The request follows the official
[OpenAI function-calling guide](https://developers.openai.com/api/docs/guides/function-calling).
