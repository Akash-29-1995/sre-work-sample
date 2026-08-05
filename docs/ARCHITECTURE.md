# Architecture Notes

Local Python 3.11+ CLI that evaluates market-data freshness for three fictional
feeds: `alpha`, `bravo`, and `charlie`. No exchanges, brokers, or cloud services
are used. Reviewers should start with `make setup`, `make test`, and `make
smoke`.

## Local system shape

- Runtime: Python 3.11+ with an editable install from `pyproject.toml`.
- Package: `src/sre_work_sample/` with model logic in `freshness.py` and CLI in
  `cli.py`.
- State: JSON fixtures. Healthy baseline is `data/healthy.json`; scenario
  commands write deterministic state files under `/tmp` or `evidence/`.
- Control surface:
  - `status` evaluates eligibility
  - `scenario stale|unknown` creates failure states
  - `recover` restores a feed to a fresh age
  - `smoke` proves the hard-path contract
- Threshold: `max_age_seconds` defaults to 90. Invalid thresholds raise before
  any feed is treated as safe.
- Observability: stable sorted JSON on stdout plus pytest and smoke output.
- CI minimum: install, pytest, smoke, and `scripts/validate_candidate_docs.py`.

Minimum scope stays local and reviewable: health model, fail-closed decisions,
recovery, tests, smoke, CI, and operating notes.

## Liveness versus eligibility

The model answers two different questions:

- **Liveness (`alive`)**: can the feed consumer answer at all?
- **Eligibility (`safe_to_serve`)**: may unsafe downstream work continue?

Exposed fields:

| Field | Meaning |
| --- | --- |
| `alive` | Process reachability for the feed consumer. |
| `last_tick_age_seconds` | Age of the newest known tick, or `null` if unknown. |
| `freshness_status` | `fresh`, `stale`, or `unknown`. |
| `safe_to_serve` | Whether unsafe actions may continue for that feed. |
| `allowed_actions` | Actions still permitted. |
| `blocked_actions` | Actions refused while the feed is unsafe. |
| `blocked_reason` | Operator-readable reason for refusal. |

Decision order for one feed:

1. If not alive: `freshness_status=unknown`, fail closed.
2. If tick age is missing: `freshness_status=unknown`, fail closed.
3. If age exceeds `max_age_seconds`: `freshness_status=stale`, fail closed.
4. Otherwise: fresh and safe to serve.

Canonical unsafe actions: `price_order`, `publish_signal`, `rebalance_position`.
They can create irreversible trading impact from stale or unknown marks, so they
are blocked whenever eligibility fails. Read-only actions such as
`read_last_price`, `serve_cached_status`, and `inspect_status` remain available
for diagnosis.

Expected-state contract:

| State | Architecture behavior |
| --- | --- |
| Healthy feeds | All feeds fresh and `safe_to_serve=true`. |
| Stale `bravo` | `bravo` blocked with age-threshold reason. |
| Unknown `bravo` tick age | `bravo` blocked with missing-age reason. |
| Partial availability | Fresh `alpha` and `charlie` stay eligible. |
| Recovered `bravo` | System returns to `overall_status=eligible`. |

## Feed boundaries

Each feed is an independent consumer identity in the state file. Freshness is
evaluated per feed. One stale feed restricts only that feed's unsafe actions.
This keeps blast radius narrow: a `bravo` incident does not require freezing
healthy `alpha` or `charlie` work.

Configuration boundary is `max_age_seconds` plus per-feed `alive` and
`last_tick_age_seconds`. Bad threshold config fails before eligibility is
computed, so operators cannot silently serve under a broken gate.

## Design tradeoffs

Implemented now:

- Deterministic ages in JSON instead of wall-clock sampling.
- Fail closed on unknown age rather than guessing freshness.
- Partial availability instead of all-or-nothing cluster shutdown.
- Small CLI and unittest/pytest surface instead of a service mesh.

Intentionally not built:

- Real market-data ingestion, brokers, or exchange APIs.
- Kubernetes, Terraform, DNS, or cloud deploy gates.
- Restart-only recovery without a re-evaluated fresh state.
- Broad platform telemetry stacks beyond JSON status and CI.

Senior evaluation focus maps to this local proof: reliability model in
`freshness.py`, incident path in `INCIDENT_NOTE.md` and `docs/OPERATIONS.md`,
automation via Makefile/CI/smoke, observability via JSON status fields, and
restraint in what remains out of scope.
