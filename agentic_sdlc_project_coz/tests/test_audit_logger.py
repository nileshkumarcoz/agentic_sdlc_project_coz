import json
import logging
import os
import pytest
from datetime import datetime


@pytest.fixture(autouse=True)
def isolated_log_dir(tmp_path, monkeypatch):
    log_dir = tmp_path / "logs"
    monkeypatch.setenv("AUDIT_LOG_DIR", str(log_dir))
    logging.getLogger("add_two_numbers.audit").handlers.clear()
    yield log_dir


def last_entry(log_dir) -> dict:
    with open(os.path.join(log_dir, "audit.log")) as f:
        return json.loads([l for l in f.read().splitlines() if l.strip()][-1])


def test_success_event(isolated_log_dir):
    from add_two_numbers.audit_logger import log_success
    log_success("42", "8", 50.0)
    e = last_entry(isolated_log_dir)
    assert e["event"] == "SUCCESS"
    assert e["result"] == 50.0
    assert e["error"] is None


def test_failure_event(isolated_log_dir):
    from add_two_numbers.audit_logger import log_failure
    log_failure("abc", "8", "bad input")
    e = last_entry(isolated_log_dir)
    assert e["event"] == "VALIDATION_ERROR"
    assert e["result"] is None
    assert e["error"] == "bad input"


def test_timestamp_is_iso8601(isolated_log_dir):
    from add_two_numbers.audit_logger import log_success
    log_success("1", "2", 3.0)
    datetime.fromisoformat(last_entry(isolated_log_dir)["timestamp"])


def test_hostname_and_user_present(isolated_log_dir):
    from add_two_numbers.audit_logger import log_success
    log_success("1", "2", 3.0)
    e = last_entry(isolated_log_dir)
    assert isinstance(e["hostname"], str) and e["hostname"]
    assert isinstance(e["os_user"], str) and e["os_user"]


def test_logging_error_does_not_propagate(monkeypatch):
    import add_two_numbers.audit_logger as al
    monkeypatch.setattr(al, "_get_audit_logger",
                        lambda: (_ for _ in ()).throw(OSError("disk full")))
    al.log_success("1", "2", 3.0)   # must not raise
    al.log_failure("x", "2", "err")  # must not raise
