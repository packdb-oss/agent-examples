# Repository checks

Require `oss-ci / checks`, `oss-ci / coverage`, `oss-ci / compatibility` and
`oss-security / audit` for changes to main and in the merge queue. The
compatibility check uses the public launch commands and a local OTLP receiver.
Pull-request workflows need read-only repository access and no tenant secrets.

Before opening the hosted repository, the release owner configures main and
tag protection, CODEOWNERS review, dismissal of stale approvals, restricted
bypass, secret scanning and push protection. Check the security and conduct
contacts. Record the settings and review the exact initial tree. The weekly
action-pin check verifies the pinned versions used by CI.

The manual candidate workflow on main runs the same checks before archiving
the source, dependency locks and commit inventory. Publication is a maintainer
action described in RELEASING.md.
