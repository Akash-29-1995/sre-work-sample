"""Market-data freshness model for the SRE work sample starter."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


DEFAULT_MAX_AGE_SECONDS = 90
SAFE_ACTIONS = ["read_last_price", "serve_cached_status"]
UNSAFE_ACTIONS = ["price_order", "publish_signal", "rebalance_position"]


@dataclass(frozen=True)
class FeedStatus:
    """Operator-facing status for one market-data feed."""

    name: str
    alive: bool
    last_tick_age_seconds: int | None
    freshness_status: str
    safe_to_serve: bool
    allowed_actions: list[str]
    blocked_actions: list[str]
    blocked_reason: str | None


def healthy_state() -> dict[str, Any]:
    """Return the deterministic healthy starter state."""
    return {
        "max_age_seconds": DEFAULT_MAX_AGE_SECONDS,
        "feeds": [
            {"name": "alpha", "alive": True, "last_tick_age_seconds": 8},
            {"name": "bravo", "alive": True, "last_tick_age_seconds": 11},
            {"name": "charlie", "alive": True, "last_tick_age_seconds": 7},
        ],
    }


def resolve_max_age_seconds(state: dict[str, Any]) -> int:
    """Resolve and validate the freshness threshold from state.

    Invalid thresholds fail closed before any feed is marked safe to serve.
    """
    if "max_age_seconds" not in state:
        return DEFAULT_MAX_AGE_SECONDS

    max_age = state["max_age_seconds"]
    if isinstance(max_age, bool) or not isinstance(max_age, int) or max_age <= 0:
        raise ValueError(
            f"invalid max_age_seconds={max_age!r}; expected a positive integer"
        )
    return max_age


def evaluate_feed(feed: dict[str, Any], max_age_seconds: int) -> FeedStatus:
    """Evaluate one feed without depending on wall-clock time."""
    name = str(feed["name"])
    alive = bool(feed.get("alive", False))
    raw_age = feed.get("last_tick_age_seconds")
    age = int(raw_age) if raw_age is not None else None

    if not alive:
        return FeedStatus(
            name=name,
            alive=False,
            last_tick_age_seconds=age,
            freshness_status="unknown",
            safe_to_serve=False,
            allowed_actions=["inspect_status"],
            blocked_actions=UNSAFE_ACTIONS,
            blocked_reason="feed process is not reachable",
        )

    if age is None:
        return FeedStatus(
            name=name,
            alive=True,
            last_tick_age_seconds=None,
            freshness_status="unknown",
            safe_to_serve=False,
            allowed_actions=["inspect_status"],
            blocked_actions=UNSAFE_ACTIONS,
            blocked_reason="last tick age is unknown",
        )

    if age > max_age_seconds:
        return FeedStatus(
            name=name,
            alive=True,
            last_tick_age_seconds=age,
            freshness_status="stale",
            safe_to_serve=False,
            allowed_actions=SAFE_ACTIONS,
            blocked_actions=UNSAFE_ACTIONS,
            blocked_reason=f"last tick age {age}s exceeds {max_age_seconds}s",
        )

    return FeedStatus(
        name=name,
        alive=True,
        last_tick_age_seconds=age,
        freshness_status="fresh",
        safe_to_serve=True,
        allowed_actions=SAFE_ACTIONS + UNSAFE_ACTIONS,
        blocked_actions=[],
        blocked_reason=None,
    )


def evaluate_system(state: dict[str, Any]) -> dict[str, Any]:
    """Evaluate all feeds and return a JSON-safe operator view."""
    max_age = resolve_max_age_seconds(state)
    feeds = [evaluate_feed(feed, max_age) for feed in state.get("feeds", [])]
    unsafe = [feed.name for feed in feeds if not feed.safe_to_serve]

    return {
        "max_age_seconds": max_age,
        "overall_status": "eligible" if not unsafe else "restricted",
        "unsafe_feeds": unsafe,
        "feeds": [
            {
                "name": feed.name,
                "alive": feed.alive,
                "last_tick_age_seconds": feed.last_tick_age_seconds,
                "freshness_status": feed.freshness_status,
                "safe_to_serve": feed.safe_to_serve,
                "allowed_actions": feed.allowed_actions,
                "blocked_actions": feed.blocked_actions,
                "blocked_reason": feed.blocked_reason,
            }
            for feed in feeds
        ],
    }


def set_feed_age(
    state: dict[str, Any],
    feed_name: str,
    age_seconds: int,
) -> dict[str, Any]:
    """Return a copy of state with one feed age changed."""
    changed = False
    feeds = []

    for feed in state.get("feeds", []):
        copy = dict(feed)
        if copy.get("name") == feed_name:
            copy["alive"] = True
            copy["last_tick_age_seconds"] = age_seconds
            changed = True
        feeds.append(copy)

    if not changed:
        raise ValueError(f"unknown feed {feed_name!r}")

    next_state = dict(state)
    next_state["feeds"] = feeds
    return next_state


def set_feed_age_unknown(state: dict[str, Any], feed_name: str) -> dict[str, Any]:
    """Return a copy of state with one alive feed's tick age unknown."""
    changed = False
    feeds = []

    for feed in state.get("feeds", []):
        copy = dict(feed)
        if copy.get("name") == feed_name:
            copy["alive"] = True
            copy["last_tick_age_seconds"] = None
            changed = True
        feeds.append(copy)

    if not changed:
        raise ValueError(f"unknown feed {feed_name!r}")

    next_state = dict(state)
    next_state["feeds"] = feeds
    return next_state
