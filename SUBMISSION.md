# Submission Report

## 1. Summary

This submission keeps the provided Python 3.11+ freshness CLI and makes the
reliability contract explicit, tested, and operable. The stack is standard
library JSON + argparse, pytest, Makefile targets, and GitHub Actions.

The main reliability idea is to separate process liveness from safe-to-serve
eligibility. A feed can be alive and still unsafe when tick age is stale or
unknown. Unsafe actions (`price_order`, `publish_signal`, `rebalance_position`)
fail closed for that feed only, so healthy feeds remain eligible.

Small code change: invalid `max_age_seconds` values raise before any feed is
treated as safe. Scenario/recovery CLI paths, smoke checks, and CI scaffolding
from the starter are retained and evidenced.

Reviewer first run:

```sh
PYTHON="$(command -v python3.11 || uv python find 3.11)" make setup
make test
make smoke
make docs-check
```

## 2. Fresh-checkout setup and run commands

Prerequisites and supported versions:

```text
Python 3.11+
make
POSIX shell
GitHub Actions runner or equivalent CI
```

Setup commands:

```sh
PYTHON="$(command -v python3.11 || uv python find 3.11)" make setup
```

Test command:

```sh
make test
```

Smoke command:

```sh
make smoke
```

Docs check:

```sh
make docs-check
```

Captured local results (Python 3.11.15):

```text
make test  -> 12 passed
make smoke -> smoke=passed with all five starter checks
make docs-check -> candidate documentation validation passed
```

Evidence files:

- `evidence/01-pytest.txt`
- `evidence/02-smoke.json`
- `evidence/03-healthy-status.json`

CI minimum: `.github/workflows/validate.yml` installs the package and runs
pytest, smoke, and docs validation.

GitHub Actions run (success):
https://github.com/Akash-29-1995/sre-work-sample/actions/runs/31045140537

Fork repository:
https://github.com/Akash-29-1995/sre-work-sample

## 3. Minimum implementation scope

Confirmed:

- Local Python 3.11+ implementation runs from a fresh checkout.
- CLI covers healthy, stale, unknown, and recovered states.
- Automated tests cover healthy, stale `bravo`, unknown `bravo`, recovered
  `bravo`, unknown feed errors, and invalid `max_age_seconds`.
- Smoke covers fail-closed stale data, fail-closed unknown data, partial
  availability, and recovery.
- CI workflow runs install, tests, smoke, and docs validation.
- `docs/ARCHITECTURE.md` and `docs/OPERATIONS.md` match implemented behavior.

## 4. Health model

Process liveness and safe-to-serve eligibility are separate fields.

| Feed | Alive signal | Freshness signal | Allowed when unsafe | Blocked when unsafe | Recovery path |
| --- | --- | --- | --- | --- | --- |
| alpha | `alive` | age vs `max_age_seconds` | read/status inspect | unsafe action set | `recover --feed alpha` |
| bravo | `alive` | age vs `max_age_seconds` | read/status inspect | unsafe action set | `recover --feed bravo` |
| charlie | `alive` | age vs `max_age_seconds` | read/status inspect | unsafe action set | `recover --feed charlie` |

Expected-state contract:

| State | Expected result | Evidence |
| --- | --- | --- |
| Healthy feeds | fresh and safe | `evidence/03-healthy-status.json` |
| Stale `bravo` | stale, not safe | `evidence/05-stale-status.json` |
| Unknown `bravo` | unknown, not safe | `evidence/07-unknown-status.json` |
| Partial availability | alpha/charlie stay safe | `evidence/05-stale-status.json` |
| Recovered `bravo` | overall eligible | `evidence/09-recovered-status.json` |

Canonical unsafe actions: `price_order`, `publish_signal`, `rebalance_position`.

## 5. Stale-feed scenario

Trigger:

```sh
.venv/bin/python -m sre_work_sample.cli scenario stale \
  --feed bravo \
  --output /tmp/bravo-stale.json
```

Detection:

```sh
.venv/bin/python -m sre_work_sample.cli status --state /tmp/bravo-stale.json
```

Observed transition:

- `bravo.last_tick_age_seconds=660`
- `bravo.freshness_status=stale`
- `bravo.safe_to_serve=false`
- blocked reason: `last tick age 660s exceeds 90s`
- blocked: `price_order`, `publish_signal`, `rebalance_position`
- still allowed on bravo: `read_last_price`, `serve_cached_status`
- `alpha` and `charlie` remain eligible

Alert path: page for sustained stale unsafe feed; ticket-only warning earlier at
half threshold. See `docs/OPERATIONS.md`.

Recovery:

```sh
.venv/bin/python -m sre_work_sample.cli recover \
  --feed bravo \
  --state /tmp/bravo-stale.json \
  --output /tmp/bravo-recovered.json
.venv/bin/python -m sre_work_sample.cli status --state /tmp/bravo-recovered.json
```

Recovery proof: `overall_status=eligible` in `evidence/09-recovered-status.json`.

## 6. Unknown tick-age scenario

Trigger:

```sh
.venv/bin/python -m sre_work_sample.cli scenario unknown \
  --feed bravo \
  --output /tmp/bravo-unknown.json
.venv/bin/python -m sre_work_sample.cli status --state /tmp/bravo-unknown.json
```

Observed:

- `freshness_status=unknown`
- `last_tick_age_seconds=null`
- `safe_to_serve=false`
- blocked unsafe actions listed above
- blocked reason: `last tick age is unknown`
- unaffected feeds remain eligible

Evidence: `evidence/06-unknown-scenario.json`, `evidence/07-unknown-status.json`.

## 7. GitHub Actions evidence

Workflow file: `.github/workflows/validate.yml`

Successful run:
https://github.com/Akash-29-1995/sre-work-sample/actions/runs/31045140537

Steps in that run:

1. checkout
2. setup Python 3.11
3. editable install with dev extras
4. pytest
5. smoke
6. candidate docs validation

Repository:
https://github.com/Akash-29-1995/sre-work-sample

## 8. Observability and alerting

- Freshness SLI: fraction of feeds with `freshness_status=fresh`.
- Liveness SLI: fraction of feeds with `alive=true`.
- Page-worthy alert: stale or unknown feed that blocks unsafe actions.
- Non-page warning: tick age crosses 50% of `max_age_seconds`.
- Structured output: sorted JSON from `status` and `smoke`
  (`evidence/02-smoke.json`, `evidence/05-stale-status.json`).

## 9. Bad configuration and rollback note

Bad config: invalid `max_age_seconds` (`0`, negative, bool, string, float,
`null`).

Detection: `resolve_max_age_seconds` raises `ValueError` before eligibility is
computed. Test: `test_invalid_max_age_fails_closed`.

Blast radius: evaluation fails closed until config is restored. Prefer this over
silently serving under a broken gate.

Rollback: restore `data/healthy.json` or prior known-good fixture, re-run
`status` and `make smoke`.

Proof: healthy status returns `overall_status=eligible` and tests/smoke pass.

## 10. Incident note

See `INCIDENT_NOTE.md` for the 09:37 stale-`bravo` first-30-minute response:
severity, first checks, block/allow decision, notifications, operator status,
first runbook action, and closure evidence.

## 11. Security and operator controls

- Audit: recoveries, threshold changes, and overrides of blocked unsafe actions.
- Confirmation/review: any change to `max_age_seconds` and any temporary allow of
  unsafe actions on a non-fresh feed.
- Secrets/external accounts: none required; local fixtures only.
- Never allow unaudited clients to force `safe_to_serve=true` without re-evaluating
  freshness.

## 12. AI usage

See `AI_USAGE.md`. Cursor/Composer assisted setup, validation, evidence capture,
and documentation. One caught issue was attempting setup on Python 3.9 despite
the 3.11 requirement.

## 13. Senior evaluation dimensions

- Reliability model: `src/sre_work_sample/freshness.py`, `docs/ARCHITECTURE.md`
- Incident response: `INCIDENT_NOTE.md`, `docs/OPERATIONS.md`
- Automation/CI/recovery: Makefile, workflow, smoke, recover command
- Observability/actionability: JSON status fields and alert table
- Tradeoffs/restraint: this report section 14 and architecture tradeoffs

## 14. Tradeoffs and follow-up discussion

Intentionally not built:

- Real market-data buses, brokers, or exchange adapters
- Kubernetes/Terraform/cloud deploy requirements
- Restart-only recovery without freshness re-evaluation
- Broad metrics platforms beyond JSON + CI evidence

With more time: add an explicit action-gate CLI, shadow-mode threshold rollout,
and producer watermark validation against clock skew.

Follow-up discussion notes are in `FOLLOWUP_NOTES.md`.
