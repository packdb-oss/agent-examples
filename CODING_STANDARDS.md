# Code standards

Keep the agent independent of SDK setup. Use a fresh Python environment and
the committed dependency locks. Keep run metadata synthetic and capture no
message bodies. Both implementations must preserve the span names, relationships,
attributes and OTLP configuration documented in the README.

From the repository root, with the Python environment activated and Node
dependencies installed:

```sh
python scripts/check_source_headers.py
python -m unittest discover -s python
npm --prefix typescript run check
npm --prefix typescript test
python -m unittest discover -s tests
```

The last test runs the normal launch commands against a loopback receiver and
decodes their protobuf output, checks the retry tree and statuses, and verifies
that console output ends with the summary. Pull-request checks use synthetic credentials.
Check both console commands after changing a launcher. The maintainer verifies
the Cloud walkthrough before tagging a release and after dashboard or ingest
authentication changes.

Python and TypeScript sources open with the PackDB copyright and Apache 2.0
notice. The checker is adapted from packdb-oss/packdb-sdk for these languages.
Preserve third-party notices. Review dependency licenses and advisories on
lockfile changes. The Python lock includes certifi under MPL-2.0 and
typing_extensions under PSF-2.0. Dependencies are installed from their
registries and retain their own licenses.

Keep comments focused on non-obvious behavior. Cover changed executable code,
including failure paths. Record compatibility changes in CHANGELOG.md.
Pin workflow actions by full commit and exact release tag. Review the final
diff and include validation and contribution provenance in the pull request.

CI checks Ruff and Prettier formatting, TypeScript types, and at least 80%
line coverage for each example source file. The weekly action-pin check pairs
each commit SHA with its upstream release. Regenerate the Python lock from the
repository root with `uv pip compile python/requirements.in --python 3.13
--universal --generate-hashes --no-header -o python/requirements.txt`.
