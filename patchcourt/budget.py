"""Persistent request reservations for an explicitly started experiment session.

Reservations happen before transport and are never refunded. A crash or timeout
therefore cannot silently open an unbounded retry loop. Not a billing estimate.
"""
from contextlib import contextmanager
from copy import deepcopy
import os
from pathlib import Path
import tempfile
import threading

from .evidence import now, read_json, write_json


MAX_REQUEST_LIMIT = 10_000
_APPLIED_LOCK = threading.RLock()


@contextmanager
def _ledger_lock(path):
    """OS-owned lock: concurrent runners fail closed; a crash releases it."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.with_name(path.name + ".lock").open("a+b") as handle:
        if handle.seek(0, os.SEEK_END) == 0:
            handle.write(b"\0")
            handle.flush()
        handle.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            raise ValueError("Experiment budget ledger is already in use; no request sent") from None
        try:
            yield
        finally:
            handle.seek(0)
            if os.name == "nt":
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


class RequestBudget:
    def __init__(self, path, *, model_calls=30, searches=10, discovery_calls=5):
        self.path = Path(path).resolve()
        self.lock = threading.Lock()
        limits = {"model_calls": model_calls, "searches": searches, "discovery_calls": discovery_calls}
        self.limits = self._validate_limits(limits)
        with _ledger_lock(self.path):
            if self.path.exists():
                self.state = self._read_state()
            else:
                self.state = {"created_at": now(), "limits": limits, "reservations": [],
                              "limit_adjustments": [],
                              "scope": "Request reservations, not a dollar-cost estimate. No automatic retries."}
                self._persist()

    @staticmethod
    def _validate_limits(limits):
        if (not isinstance(limits, dict)
                or set(limits) != {"model_calls", "searches", "discovery_calls"}
                or any(type(n) is not int or n < 0 or n > MAX_REQUEST_LIMIT for n in limits.values())):
            raise ValueError(f"Invalid experiment request limits: use integers in 0..{MAX_REQUEST_LIMIT}")
        return dict(limits)

    @classmethod
    def _validate_state(cls, state):
        if not isinstance(state, dict):
            raise ValueError("Experiment budget ledger must be an object")
        limits = cls._validate_limits(state.get("limits"))
        if not isinstance(state.get("reservations"), list):
            raise ValueError("Experiment budget ledger contains invalid reservations")
        used = dict.fromkeys(limits, 0)
        for row in state["reservations"]:
            if not isinstance(row, dict) or not isinstance(row.get("kind"), str) or row["kind"] not in limits:
                raise ValueError("Experiment budget ledger contains an invalid reservation")
            used[row["kind"]] += 1
        if any(used[kind] > limit for kind, limit in limits.items()):
            raise ValueError("Experiment budget limits are below recorded usage")
        adjustments = state.get("limit_adjustments", [])
        if not isinstance(adjustments, list):
            raise ValueError("Experiment budget ledger contains invalid limit adjustments")
        previous = None
        for record in adjustments:
            if (not isinstance(record, dict) or not isinstance(record.get("reason"), str)
                    or not record["reason"].strip() or not isinstance(record.get("changed_at"), str)
                    or not record["changed_at"].strip()):
                raise ValueError("Experiment budget ledger contains an invalid limit adjustment")
            before = cls._validate_limits(record.get("old_limits"))
            after = cls._validate_limits(record.get("new_limits"))
            if previous is not None and before != previous:
                raise ValueError("Experiment budget limit adjustment history is inconsistent")
            previous = after
        if previous is not None and previous != limits:
            raise ValueError("Experiment budget limit adjustment history differs from current limits")
        return state

    @classmethod
    def from_existing(cls, path):
        """Explicitly load saved limits; never create or silently reset a ledger."""
        instance = cls.__new__(cls)
        instance.path = Path(path).resolve()
        instance.lock = threading.Lock()
        if not instance.path.is_file():
            raise ValueError("Experiment budget ledger does not exist")
        with instance.lock, _ledger_lock(instance.path):
            state = cls._validate_state(read_json(instance.path))
            instance.limits = dict(state["limits"])
            instance.state = state
        return instance

    def _read_state(self):
        state = self._validate_state(read_json(self.path))
        if state["limits"] != self.limits:
            raise ValueError("Experiment budget identity differs from the saved ledger")
        return state

    def _persist(self, state=None):
        """Atomic replacement preserves the previous ledger if writing fails."""
        descriptor, temporary = tempfile.mkstemp(prefix=".budget-", suffix=".tmp", dir=self.path.parent)
        os.close(descriptor)
        target = Path(temporary)
        try:
            saved = write_json(target, self.state if state is None else state)
            self._validate_state(saved)
            os.replace(target, self.path)
            return saved
        finally:
            target.unlink(missing_ok=True)

    def adjust_limits(self, *, model_calls=None, searches=None, discovery_calls=None, reason):
        """Apply an explicit operator change without removing any reservations.

        Every successful call appends an audit record, including an explicitly
        requested no-op. Other instances keep their old identity and fail closed.
        """
        if not isinstance(reason, str) or not reason.strip():
            raise ValueError("A non-empty reason is required for an experiment limit adjustment")
        requested = {"model_calls": model_calls, "searches": searches, "discovery_calls": discovery_calls}
        if all(value is None for value in requested.values()):
            raise ValueError("Specify at least one experiment request limit to adjust")
        with self.lock, _ledger_lock(self.path):
            state = self._read_state()
            limits = self._validate_limits({kind: state["limits"][kind] if value is None else value
                                            for kind, value in requested.items()})
            used = {kind: sum(row["kind"] == kind for row in state["reservations"]) for kind in limits}
            if any(limits[kind] < count for kind, count in used.items()):
                raise ValueError("Adjusted experiment limits cannot be below recorded usage")
            record = {"old_limits": dict(state["limits"]), "new_limits": limits,
                      "reason": reason.strip(), "changed_at": now()}
            updated = deepcopy(state)
            updated["limits"] = dict(limits)
            updated.setdefault("limit_adjustments", []).append(record)
            self._validate_state(updated)
            # Keep the live instance's identity/state intact until disk commit.
            saved = self._persist(updated)
            self.limits = dict(saved["limits"])
            self.state = saved
            return deepcopy(saved["limit_adjustments"][-1])

    def reserve(self, provider, payload=None, endpoint="chat/completions"):
        kind = "searches" if provider == "tavily" else "discovery_calls" if endpoint == "models" else "model_calls"
        if provider == "tavily" and (not isinstance(payload, dict) or payload.get("search_depth", "basic") != "basic"):
            raise ValueError("This experiment budget permits Tavily basic search only")
        if kind == "model_calls":
            from .providers import validate_output_tokens
            validate_output_tokens(provider, payload.get("max_tokens") if isinstance(payload, dict) else None)
        with self.lock, _ledger_lock(self.path):
            # Other instances/processes may have reserved since construction.
            self.state = self._read_state()
            used = sum(row["kind"] == kind for row in self.state["reservations"])
            if used >= self.state["limits"][kind]:
                raise ValueError("Experiment " + kind + " budget exhausted; no request sent")
            self.state["reservations"].append({"kind": kind, "provider": provider,
                                                "model": payload.get("model") if isinstance(payload, dict) else None,
                                                "max_tokens": payload.get("max_tokens") if kind == "model_calls" else None,
                                                "reserved_at": now()})
            self._persist()

    def remaining(self, kind="model_calls"):
        """Read current headroom without reserving or changing the ledger.

        This preflight is not a reservation: a concurrent runner can consume
        headroom later, and reserve() still checks the ledger before transport.
        """
        if kind not in self.limits:
            raise ValueError("Unsupported experiment budget kind")
        with self.lock, _ledger_lock(self.path):
            self.state = self._read_state()
            used = sum(row["kind"] == kind for row in self.state["reservations"])
            return max(0, self.state["limits"][kind] - used)

    @contextmanager
    def applied(self):
        from . import providers
        if not _APPLIED_LOCK.acquire(blocking=False):
            raise ValueError("Another experiment budget context is active in this process")
        original = providers.request
        def bounded(provider, payload=None, endpoint="chat/completions"):
            self.reserve(provider, payload, endpoint)
            return original(provider, payload, endpoint)
        providers.request = bounded
        try:
            yield self
        finally:
            providers.request = original
            _APPLIED_LOCK.release()
