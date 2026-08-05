# Incident Note

## Prompt

At 09:37, the service is reachable and latency is normal, but `bravo` has not
received fresh ticks for 11 minutes. `alpha` and `charlie` are fresh. Operators
ask whether downstream work should continue. What do you do in the first 30
minutes?

## Severity and why

Severity: **SEV-2 / partial degradation**.

The service process is alive and latency is normal, so this is not a hard
outage. `bravo` age is about 660s against a 90s freshness gate, so any unsafe
`bravo` trading action would use stale marks. Impact is limited to `bravo`
unsafe work because `alpha` and `charlie` remain fresh.

## First five checks

1. Confirm feed-level status, not only process uptime:
   `python -m sre_work_sample.cli status --state <current-state>`.
2. Verify `bravo.alive=true` with `freshness_status=stale` and
   `safe_to_serve=false`.
3. Confirm `alpha` and `charlie` stay fresh and eligible.
4. Confirm blocked actions include `price_order`, `publish_signal`, and
   `rebalance_position`.
5. Check recent change/window: deploy, config edit to `max_age_seconds`, source
   feed outage, or clock/timestamp anomaly.

## Block / allow decision

Block for `bravo`:

- `price_order`
- `publish_signal`
- `rebalance_position`

Allow:

- `bravo` read-only inspection and cached status
- all eligible unsafe and safe actions for fresh `alpha` and `charlie`

Do not shut down the whole service because process health alone is green.

## Who to notify

- Page on-call SRE and the `bravo` feed owner.
- Notify trading/ops stakeholders that only `bravo` unsafe work is paused.
- Open a ticket for the upstream data owner if source lag is confirmed.
- Room or channel update every 10 minutes until mitigated or recovered.

## Operator-facing status

Publish a short status based on CLI JSON:

- `overall_status=restricted`
- `unsafe_feeds=["bravo"]`
- `bravo.blocked_reason` includes age exceeding threshold
- `alpha`/`charlie` remain eligible

Example evidence shape is captured in `evidence/05-stale-status.json`.

## First runbook action

1. Fail closed on unsafe `bravo` actions immediately.
2. Capture current status output for the incident timeline.
3. Reproduce the stale state deterministically if needed:
   `scenario stale --feed bravo --output /tmp/bravo-stale.json`.
4. Start recovery path only after fresh ticks are observed, then run
   `recover` and re-check status.
5. Keep the incident open until recovered status shows
   `overall_status=eligible` and smoke/tests still pass.

## Closure evidence

Close or downgrade only when all are true:

- `bravo.freshness_status=fresh` and `safe_to_serve=true`
- `unsafe_feeds` is empty / `overall_status=eligible`
- recovered state file retained (see `evidence/09-recovered-status.json`)
- alert annotations include detection time, block decision, and recovery command
- no unresolved bad-config issue on `max_age_seconds`
