"""Operator budget changes use temporary ledgers and never call providers."""
from copy import deepcopy
import json
from pathlib import Path
import threading
from concurrent.futures import ThreadPoolExecutor

import pytest

from patchcourt import budget as budget_module
from patchcourt.budget import MAX_REQUEST_LIMIT, RequestBudget


def model_reservation(budget):
    budget.reserve("deepseek", {"model": "deepseek-flash", "max_tokens": 100})


def test_explicit_six_more_calls_preserve_all_thirty_reservations(tmp_path: Path):
    path = tmp_path / "budget.json"
    budget = RequestBudget(path)
    for _ in range(30):
        model_reservation(budget)
    previous = deepcopy(budget.state["reservations"])
    assert budget.remaining() == 0
    audit = budget.adjust_limits(model_calls=36, reason="User explicitly approved six further calls")
    assert audit["old_limits"] == {"model_calls": 30, "searches": 10, "discovery_calls": 5}
    assert audit["new_limits"] == {"model_calls": 36, "searches": 10, "discovery_calls": 5}
    assert audit["reason"] == "User explicitly approved six further calls" and audit["changed_at"]
    assert budget.state["reservations"] == previous
    assert budget.state["limit_adjustments"] == [audit]
    reopened = RequestBudget.from_existing(path)
    assert reopened.remaining() == 6
    assert reopened.state["reservations"] == previous
    assert RequestBudget(path, model_calls=36).remaining() == 6
    unchanged = path.read_bytes()
    with pytest.raises(ValueError, match="identity differs"):
        RequestBudget(path)
    assert path.read_bytes() == unchanged
    for _ in range(6):
        model_reservation(reopened)
    with pytest.raises(ValueError, match="budget exhausted"):
        model_reservation(reopened)
    assert len(reopened.state["reservations"]) == 36


def test_from_existing_never_creates_a_missing_ledger(tmp_path: Path):
    path = tmp_path / "missing" / "budget.json"
    with pytest.raises(ValueError, match="does not exist"):
        RequestBudget.from_existing(path)
    assert not path.exists() and not path.parent.exists()


def test_legacy_ledger_without_adjustment_history_is_loaded_without_rewriting(tmp_path: Path):
    path = tmp_path / "budget.json"
    budget = RequestBudget(path)
    model_reservation(budget)
    old = deepcopy(budget.state)
    old.pop("limit_adjustments")
    path.write_text(json.dumps(old), encoding="utf-8")
    prior = path.read_bytes()
    reopened = RequestBudget.from_existing(path)
    assert path.read_bytes() == prior
    assert reopened.state == old
    reopened.adjust_limits(model_calls=36, reason="Explicit operator approval")
    assert reopened.state["reservations"] == old["reservations"]
    assert len(reopened.state["limit_adjustments"]) == 1


def test_old_instances_fail_closed_after_an_operator_change(tmp_path: Path):
    path = tmp_path / "budget.json"
    operator = RequestBudget(path, model_calls=2)
    stale = RequestBudget(path, model_calls=2)
    model_reservation(stale)
    operator.adjust_limits(model_calls=3, reason="An explicitly approved extra call")
    prior = path.read_bytes()
    for action in [lambda: stale.remaining(), lambda: model_reservation(stale),
                   lambda: stale.adjust_limits(model_calls=4, reason="Stale operator")]:
        with pytest.raises(ValueError, match="identity differs"):
            action()
    assert path.read_bytes() == prior
    assert RequestBudget.from_existing(path).remaining() == 2


@pytest.mark.parametrize("kind", ["model_calls", "searches", "discovery_calls"])
def test_adjustment_cannot_shrink_below_real_reserved_usage(tmp_path: Path, kind):
    path = tmp_path / "budget.json"
    budget = RequestBudget(path, model_calls=3, searches=3, discovery_calls=3)
    model_reservation(budget)
    budget.reserve("tavily", {"query": "mock", "search_depth": "basic"})
    budget.reserve("nebius", endpoint="models")
    prior = path.read_bytes()
    with pytest.raises(ValueError, match="below recorded usage"):
        budget.adjust_limits(**{kind: 0}, reason="Reduce safely")
    assert path.read_bytes() == prior
    reservations = deepcopy(budget.state["reservations"])
    budget.adjust_limits(**{kind: 1}, reason="Set exactly to already used")
    assert budget.remaining(kind) == 0
    assert budget.state["reservations"] == reservations


@pytest.mark.parametrize("invalid", [True, False, -1, 10001, 1.5, "36"])
def test_invalid_adjusted_limits_do_not_write_or_change_identity(tmp_path: Path, invalid):
    path = tmp_path / "budget.json"
    budget = RequestBudget(path)
    prior = path.read_bytes()
    original = deepcopy(budget.state)
    with pytest.raises(ValueError, match="Invalid experiment request limits"):
        budget.adjust_limits(model_calls=invalid, reason="Invalid change")
    assert path.read_bytes() == prior
    assert budget.state == original and budget.limits == original["limits"]


@pytest.mark.parametrize("reason", [None, "", "   ", 123])
def test_audit_reason_must_be_nonempty_text(tmp_path: Path, reason):
    path = tmp_path / "budget.json"
    budget = RequestBudget(path)
    prior = path.read_bytes()
    with pytest.raises(ValueError, match="non-empty reason"):
        budget.adjust_limits(model_calls=36, reason=reason)
    assert path.read_bytes() == prior


def test_reason_is_required_and_at_least_one_limit_is_explicit(tmp_path: Path):
    path = tmp_path / "budget.json"
    budget = RequestBudget(path)
    prior = path.read_bytes()
    with pytest.raises(TypeError):
        budget.adjust_limits(model_calls=36)
    with pytest.raises(ValueError, match="at least one"):
        budget.adjust_limits(reason="No explicit limit")
    assert path.read_bytes() == prior


@pytest.mark.parametrize("failure", ["write_json", "replace"])
def test_failed_atomic_adjustment_preserves_disk_and_instance(tmp_path: Path, monkeypatch, failure):
    path = tmp_path / "budget.json"
    budget = RequestBudget(path)
    model_reservation(budget)
    prior = path.read_bytes()
    old_state = deepcopy(budget.state)
    old_limits = dict(budget.limits)

    def fail(*args, **kwargs):
        raise OSError("synthetic disk failure")

    if failure == "write_json":
        monkeypatch.setattr(budget_module, "write_json", fail)
    else:
        monkeypatch.setattr(budget_module.os, "replace", fail)
    with pytest.raises(OSError, match="synthetic disk failure"):
        budget.adjust_limits(model_calls=36, reason="Approved increase")
    assert path.read_bytes() == prior
    assert budget.state == old_state and budget.limits == old_limits
    assert list(tmp_path.glob(".budget-*.tmp")) == []


def test_adjustment_and_explicit_reload_obey_the_os_lock(tmp_path: Path):
    path = tmp_path / "budget.json"
    budget = RequestBudget(path)
    prior = path.read_bytes()
    with budget_module._ledger_lock(path):
        with pytest.raises(ValueError, match="already in use"):
            budget.adjust_limits(model_calls=36, reason="Approved increase")
        with pytest.raises(ValueError, match="already in use"):
            RequestBudget.from_existing(path)
    assert path.read_bytes() == prior


def test_adjustment_shares_the_instance_thread_lock(tmp_path: Path):
    path = tmp_path / "budget.json"
    budget = RequestBudget(path)
    started = threading.Event()

    def adjust():
        started.set()
        return budget.adjust_limits(model_calls=36, reason="Approved increase")

    with ThreadPoolExecutor(max_workers=1) as pool:
        with budget.lock:
            prior = path.read_bytes()
            future = pool.submit(adjust)
            assert started.wait(timeout=5)
            assert not future.done()
            assert path.read_bytes() == prior
        result = future.result(timeout=5)
    assert result["new_limits"]["model_calls"] == 36


@pytest.mark.parametrize("malformed", [None, {}, {"model_calls": 30},
    {"model_calls": True, "searches": 10, "discovery_calls": 5},
    {"model_calls": -1, "searches": 10, "discovery_calls": 5},
    {"model_calls": 10001, "searches": 10, "discovery_calls": 5},
    {"model_calls": 30, "searches": 10, "discovery_calls": 5, "extra": 1}])
def test_corrupt_saved_limits_are_not_accepted_or_reset(tmp_path: Path, malformed):
    path = tmp_path / "budget.json"
    path.write_text(json.dumps({"limits": malformed, "reservations": []}), encoding="utf-8")
    prior = path.read_bytes()
    with pytest.raises(ValueError):
        RequestBudget.from_existing(path)
    with pytest.raises(ValueError):
        RequestBudget(path)
    assert path.read_bytes() == prior


def test_corrupt_usage_and_adjustment_history_fail_closed(tmp_path: Path):
    path = tmp_path / "budget.json"
    budget = RequestBudget(path)
    budget.adjust_limits(model_calls=36, reason="First explicit change")
    budget.adjust_limits(model_calls=35, reason="Second explicit change")
    original = deepcopy(budget.state)
    for mutate in [
        lambda value: value.update(limit_adjustments={}),
        lambda value: value["limit_adjustments"][0].update(reason=""),
        lambda value: value["limit_adjustments"][1]["old_limits"].update(model_calls=31),
        lambda value: value["limits"].update(model_calls=34),
        lambda value: value.update(reservations=[{"kind": "unknown"}]),
        lambda value: value.update(reservations=[{"kind": "discovery_calls"}] * 6),
    ]:
        damaged = deepcopy(original)
        mutate(damaged)
        path.write_text(json.dumps(damaged), encoding="utf-8")
        prior = path.read_bytes()
        with pytest.raises(ValueError):
            RequestBudget.from_existing(path)
        assert path.read_bytes() == prior


def test_noop_is_audited_and_returned_audit_cannot_mutate_live_state(tmp_path: Path):
    budget = RequestBudget(tmp_path / "budget.json")
    record = budget.adjust_limits(model_calls=30, reason="Explicitly keep the existing cap")
    assert record["old_limits"] == record["new_limits"] == budget.limits
    record["new_limits"]["model_calls"] = 99
    assert budget.limits["model_calls"] == 30
    assert budget.state["limit_adjustments"][0]["new_limits"]["model_calls"] == 30


def test_returned_audit_matches_sanitized_persisted_reason(tmp_path: Path):
    path = tmp_path / "budget.json"
    budget = RequestBudget(path)
    record = budget.adjust_limits(model_calls=36, reason="Mock secret sk-synthetic-token-12345")
    assert "sk-synthetic-token" not in record["reason"]
    assert record == json.loads(path.read_text(encoding="utf-8"))["limit_adjustments"][-1]
    assert budget.state == json.loads(path.read_text(encoding="utf-8"))


@pytest.mark.parametrize("limit", [200, 10000])
def test_explicit_large_limits_support_creation_reload_and_audited_adjustment(tmp_path: Path, limit):
    assert MAX_REQUEST_LIMIT == 10000
    path = tmp_path / "budget.json"
    budget = RequestBudget(path, model_calls=limit, searches=limit, discovery_calls=limit)
    model_reservation(budget)
    saved = deepcopy(budget.state["reservations"])
    assert RequestBudget.from_existing(path).limits == dict.fromkeys(budget.limits, limit)
    budget.adjust_limits(model_calls=30, searches=10, discovery_calls=5, reason="Explicitly restore defaults")
    record = budget.adjust_limits(model_calls=limit, searches=limit, discovery_calls=limit,
                                  reason="Explicitly configure a larger operator budget")
    assert record["new_limits"] == {"model_calls": limit, "searches": limit, "discovery_calls": limit}
    assert budget.state["reservations"] == saved
    assert RequestBudget.from_existing(path).remaining() == limit - 1


@pytest.mark.parametrize("kind", ["model_calls", "searches", "discovery_calls"])
def test_absolute_limit_rejects_10001_before_creation_or_adjustment(tmp_path: Path, kind):
    path = tmp_path / "budget.json"
    with pytest.raises(ValueError, match=r"0\.\.10000"):
        RequestBudget(path, **{kind: 10001})
    assert not path.exists()
    budget = RequestBudget(path)
    original = path.read_bytes()
    with pytest.raises(ValueError, match=r"0\.\.10000"):
        budget.adjust_limits(**{kind: 10001}, reason="Above the absolute application limit")
    assert path.read_bytes() == original
