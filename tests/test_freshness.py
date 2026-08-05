import pytest

from sre_work_sample.freshness import (
    UNSAFE_ACTIONS,
    evaluate_system,
    healthy_state,
    set_feed_age,
    set_feed_age_unknown,
)


def test_healthy_feeds_are_eligible() -> None:
    status = evaluate_system(healthy_state())

    assert status["overall_status"] == "eligible"
    assert status["unsafe_feeds"] == []
    assert all(feed["safe_to_serve"] for feed in status["feeds"])


def test_stale_feed_fails_closed_without_blocking_fresh_feeds() -> None:
    stale_state = set_feed_age(healthy_state(), "bravo", 660)
    status = evaluate_system(stale_state)
    feeds = {feed["name"]: feed for feed in status["feeds"]}

    assert status["overall_status"] == "restricted"
    assert status["unsafe_feeds"] == ["bravo"]
    assert feeds["bravo"]["freshness_status"] == "stale"
    assert not feeds["bravo"]["safe_to_serve"]
    assert feeds["bravo"]["blocked_actions"] == UNSAFE_ACTIONS
    assert feeds["alpha"]["safe_to_serve"]
    assert feeds["charlie"]["safe_to_serve"]


def test_unknown_feed_age_fails_closed_without_blocking_fresh_feeds() -> None:
    unknown_state = set_feed_age_unknown(healthy_state(), "bravo")
    status = evaluate_system(unknown_state)
    feeds = {feed["name"]: feed for feed in status["feeds"]}

    assert status["overall_status"] == "restricted"
    assert status["unsafe_feeds"] == ["bravo"]
    assert feeds["bravo"]["freshness_status"] == "unknown"
    assert feeds["bravo"]["last_tick_age_seconds"] is None
    assert not feeds["bravo"]["safe_to_serve"]
    assert feeds["bravo"]["blocked_actions"] == UNSAFE_ACTIONS
    assert feeds["bravo"]["blocked_reason"] == "last tick age is unknown"
    assert feeds["alpha"]["safe_to_serve"]
    assert feeds["charlie"]["safe_to_serve"]


def test_recovered_feed_restores_eligibility() -> None:
    stale_state = set_feed_age(healthy_state(), "bravo", 660)
    recovered_state = set_feed_age(stale_state, "bravo", 5)
    status = evaluate_system(recovered_state)

    assert status["overall_status"] == "eligible"
    assert status["unsafe_feeds"] == []


def test_unknown_feed_is_actionable_error() -> None:
    try:
        set_feed_age(healthy_state(), "delta", 5)
    except ValueError as error:
        assert "unknown feed" in str(error)
    else:
        raise AssertionError("expected unknown feed to raise ValueError")


@pytest.mark.parametrize("max_age", [0, -1, True, "90", 90.5, None])
def test_invalid_max_age_fails_closed(max_age: object) -> None:
    state = healthy_state()
    state["max_age_seconds"] = max_age

    with pytest.raises(ValueError, match="invalid max_age_seconds"):
        evaluate_system(state)
