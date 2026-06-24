import json
import logging
from unittest.mock import patch


def _reset_audit_logger():
    logging.getLogger("add_two_numbers.audit").handlers.clear()


def test_happy_path_prints_result(capsys, tmp_path, monkeypatch):
    monkeypatch.setenv("AUDIT_LOG_DIR", str(tmp_path / "logs"))
    _reset_audit_logger()
    with patch("builtins.input", side_effect=["10", "20"]):
        from add_two_numbers.main import main
        main()
    assert "30.0" in capsys.readouterr().out


def test_invalid_input_prints_error(capsys, tmp_path, monkeypatch):
    monkeypatch.setenv("AUDIT_LOG_DIR", str(tmp_path / "logs"))
    _reset_audit_logger()
    with patch("builtins.input", side_effect=["abc", "5"]):
        from add_two_numbers.main import main
        main()
    assert "Error" in capsys.readouterr().out


def test_happy_path_writes_success_log(tmp_path, monkeypatch):
    monkeypatch.setenv("AUDIT_LOG_DIR", str(tmp_path / "logs"))
    _reset_audit_logger()
    with patch("builtins.input", side_effect=["3", "7"]):
        from add_two_numbers.main import main
        main()
    entry = json.loads((tmp_path / "logs" / "audit.log").read_text().strip().splitlines()[-1])
    assert entry["event"] == "SUCCESS"
    assert entry["result"] == 10.0


def test_invalid_input_writes_failure_log(tmp_path, monkeypatch):
    monkeypatch.setenv("AUDIT_LOG_DIR", str(tmp_path / "logs"))
    _reset_audit_logger()
    with patch("builtins.input", side_effect=["xyz", "7"]):
        from add_two_numbers.main import main
        main()
    entry = json.loads((tmp_path / "logs" / "audit.log").read_text().strip().splitlines()[-1])
    assert entry["event"] == "VALIDATION_ERROR"
    assert entry["result"] is None
