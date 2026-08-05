# Follow-up Notes

## Three design decisions to explain

1. Separate `alive` from `safe_to_serve`. A reachable process can still be
   unsafe when ticks are stale or unknown.
2. Fail closed on unknown tick age. Missing freshness data is treated as unsafe,
   not as an implicit healthy state.
3. Keep blast radius per feed. Stale `bravo` blocks only `bravo` unsafe actions
   so fresh `alpha` and `charlie` can continue.

## One redesign with more time

Add an explicit action-gate command that takes `--feed` and `--action` and
returns allow/deny with the same blocked reason used by `status`. The model
already encodes this in JSON; a dedicated gate would make fail-closed checks
easier for callers and CI assertions.

## AI mistake caught

Initial setup used Python 3.9. Package install failed on `requires-python >=3.11`.
Fixed by installing Python 3.11 and recreating the virtualenv. Details are in
`AI_USAGE.md`.

## Unresolved production risk

This sample uses deterministic fixture ages rather than live clock-sampled tick
timestamps. Production needs agreed clock sources, producer watermark semantics,
and protection against stale-but-replayed timestamps before thresholds can be
trusted at trading impact.

## Strongest evidence artifact

`make smoke` plus `evidence/05-stale-status.json`: one command path proves
healthy eligibility, stale fail-closed behavior, unknown fail-closed behavior,
partial availability, and recovery.

## Questions before productionizing

- What is the business cost of a false block versus serving one stale price?
- Who owns each feed's upstream SLA and escalation path?
- How should threshold changes roll out: dark launch, shadow compare, then
  enforce?
- What audit trail is required for every blocked unsafe action?
- How do we detect producer clock skew versus genuine feed stall?
