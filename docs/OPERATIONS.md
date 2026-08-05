# Operations Notes

Operator-facing runbook for the local freshness CLI. Commands assume a fresh
checkout and Python 3.11+.

## Fresh-checkout commands

Prerequisites:

```text
Python 3.11+
make
POSIX shell
```

If `python3` on PATH is older than 3.11, point `PYTHON` at a 3.11+ binary:

```sh
PYTHON="$(command -v python3.11 || uv python find 3.11)" make setup
make test
make smoke
make docs-check
```

Healthy status:

```sh
.venv/bin/python -m sre_work_sample.cli status --state data/healthy.json
```

Expected healthy outcome: `overall_status=eligible`, empty `unsafe_feeds`, and
all feeds `freshness_status=fresh` with `safe_to_serve=true`.

CI should run the same core checks: install or setup, tests, smoke, and docs
validation via `.github/workflows/validate.yml`.

## Stale-feed scenario

Trigger:

```sh
.venv/bin/python -m sre_work_sample.cli scenario stale \
  --feed bravo \
  --output /tmp/bravo-stale.json
```

Detect:

```sh
.venv/bin/python -m sre_work_sample.cli status --state /tmp/bravo-stale.json
```

Expected detection signal:

- `overall_status=restricted`
- `unsafe_feeds=["bravo"]`
- `bravo.freshness_status=stale`
- `bravo.safe_to_serve=false`
- blocked reason references age exceeding `max_age_seconds`
- blocked actions: `price_order`, `publish_signal`, `rebalance_position`
- allowed on `bravo`: `read_last_price`, `serve_cached_status`
- `alpha` and `charlie` remain `safe_to_serve=true`

Recover:

```sh
.venv/bin/python -m sre_work_sample.cli recover \
  --feed bravo \
  --state /tmp/bravo-stale.json \
  --output /tmp/bravo-recovered.json
.venv/bin/python -m sre_work_sample.cli status --state /tmp/bravo-recovered.json
```

Evidence location: `evidence/04-stale-scenario.json`,
`evidence/05-stale-status.json`, `evidence/08-recover-scenario.json`,
`evidence/09-recovered-status.json`.

## Unknown tick-age scenario

Trigger:

```sh
.venv/bin/python -m sre_work_sample.cli scenario unknown \
  --feed bravo \
  --output /tmp/bravo-unknown.json
.venv/bin/python -m sre_work_sample.cli status --state /tmp/bravo-unknown.json
```

Expected detection signal:

- `bravo.freshness_status=unknown`
- `bravo.last_tick_age_seconds=null`
- `bravo.safe_to_serve=false`
- blocked reason: `last tick age is unknown`
- blocked actions: `price_order`, `publish_signal`, `rebalance_position`
- `alpha` and `charlie` remain eligible

Operator decision: keep unsafe `bravo` work blocked until tick age is known and
fresh again. Do not infer freshness from process liveness alone.

Evidence location: `evidence/06-unknown-scenario.json`,
`evidence/07-unknown-status.json`.

Expected-state contract:

| State | Operational expectation |
| --- | --- |
| Healthy feeds | No unsafe feeds and no blocked reason. |
| Stale `bravo` | Unsafe actions blocked by age threshold. |
| Unknown `bravo` tick age | Unsafe actions blocked by missing age. |
| Partial availability | Safe work continues for unaffected feeds. |
| Recovered `bravo` | Eligibility restored with re-check evidence. |

## Bad configuration and rollback

Scenario: someone ships `max_age_seconds` as `0`, negative, boolean, float, or
string. That is a broken gate, not a feed failure.

Detection: `evaluate_system` raises `ValueError` matching
`invalid max_age_seconds` before any feed is marked safe. Covered by
`tests/test_freshness.py::test_invalid_max_age_fails_closed`.

Blast radius: evaluation fails closed globally until config is corrected. This
is preferred over silently treating all feeds as fresh under a broken threshold.

Rollback:

1. Restore known-good state from `data/healthy.json` or the previous valid
   fixture.
2. Re-run `status` and `make smoke`.
3. Keep unsafe actions blocked while the gate is invalid.

Proof of rollback: `status` returns `overall_status=eligible` against restored
healthy state, and pytest/smoke pass.

## Alerts and operator actions

Stale feed pages:

- Threshold: tick age > `max_age_seconds` and no recovery within 5 minutes
- Severity: page
- Owner: on-call SRE + feed owner
- First action: block unsafe actions, run status, open incident

Freshness warning ticket:

- Threshold: tick age crosses 50% of `max_age_seconds`
- Severity: ticket
- Owner: feed owner
- First action: investigate source lag; do not page yet

Unknown tick age:

- Threshold: `last_tick_age_seconds` is null while process is alive
- Severity: page
- Owner: on-call SRE
- First action: fail closed; treat as unsafe until age is known

SLIs for this sample:

- Freshness SLI: share of feeds with `freshness_status=fresh`.
- Liveness SLI: share of feeds with `alive=true`.

These alerts map only to states the local evidence exercises: healthy, stale,
unknown, partial availability, and recovery. Structured evidence is JSON status
output plus captured files under `evidence/`.
