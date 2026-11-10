# Releasing

The named maintainer releases a reviewed source revision. Run the checks in
CODING_STANDARDS.md on that revision, review the lockfile changes, and check
the release file list with `git ls-tree -r --name-only HEAD`. Run both README commands from a clean
checkout. Verify the Cloud walkthrough in a test workspace and record the
results, dependency review and commit ID before creating a tag. This repository
distributes examples as source. There is no npm or PyPI publication step.
