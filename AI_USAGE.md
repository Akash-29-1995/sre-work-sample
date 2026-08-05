# AI Usage

AI coding tools were used for this submission.

## Tools

- Cursor agent (Composer) for repository setup, local validation, evidence
  capture, and drafting documentation.

## What I asked the tools to do

- Explain the assignment from the hiring page and repository README.
- Clone the starter repository and move work into that project root.
- Install a Python 3.11 runtime because the machine default was Python 3.9.
- Run `make setup`, tests, smoke, and scenario commands.
- Draft architecture, operations, incident, submission, and follow-up notes.
- Add a small invalid-`max_age_seconds` fail-closed check with tests.

## Accepted, edited, or rejected generated changes

Accepted with edits:

- Documentation drafts for architecture, operations, incident response, and
  submission evidence packaging.
- `resolve_max_age_seconds` validation and parameterized pytest coverage.

Rejected or corrected:

- Early assumption that forking the upstream repo was required before local
  setup. Local clone and validation came first; GitHub fork/CI evidence is a
  separate submit step.
- Any suggestion that would expand into cloud deploy, Kubernetes, or real
  market-data integrations. Those were out of scope.

## One wrong or incomplete generated result

The first setup attempt used system `python3` (3.9.6). The package correctly
refused install because it requires Python `>=3.11`. That miss was caught by the
pip/requires-python error during `make setup`.

Fix: install CPython 3.11 via `uv`, recreate `.venv` with that interpreter, and
document `PYTHON=... make setup` for machines whose default `python3` is older.

## Verification I ran myself

- `PYTHON=<python3.11> make setup`
- `make test`
- `make smoke`
- `make docs-check`
- CLI scenarios for stale, unknown, and recovered `bravo`
- Review of generated docs against README hard gates and the submission
  template
