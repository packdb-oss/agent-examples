# Changelog

## Unreleased

- Add Python and TypeScript examples of a tool timeout followed by a successful
  retry, with console and OTLP export.

- Rename the repository to agent-examples.
- Flush default Node console output before printing the summary and verify the
  exported tool retry relationships and statuses.
- Require TypeScript syntax supported by Node's type stripping.

- Add a Python recipe using a real OpenAI function call, with credentials supplied
  through the environment and provider-contract tests requiring no API key.
