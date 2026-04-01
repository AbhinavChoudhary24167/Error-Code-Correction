import subprocess
import sys
from pathlib import Path

import pytest

import ecc_wizard


REPO = Path(__file__).resolve().parents[2]
WIZARD = REPO / "ecc_wizard.py"


def test_menu_render_and_quit_smoke():
    res = subprocess.run(
        [sys.executable, str(WIZARD)],
        input="q\n",
        text=True,
        capture_output=True,
        check=True,
        cwd=REPO,
    )
    assert "ECC Guided Workflow Wizard" in res.stdout
    assert "1. Energy Estimation Mode" in res.stdout


def test_energy_mode_command_construction_print_only(monkeypatch: pytest.MonkeyPatch):
    inputs = iter(["sec-ded", "7", "0.8", "45", "1000", "10", "2"])
    monkeypatch.setattr("builtins.input", lambda _prompt="": next(inputs))
    captured = {}

    def fake_action(command):
        captured["command"] = command

    monkeypatch.setattr(ecc_wizard, "_command_action", fake_action)
    ecc_wizard._energy_mode()

    assert captured["command"] == [
        "energy",
        "--code",
        "sec-ded",
        "--node",
        "7",
        "--vdd",
        "0.8",
        "--temp",
        "45",
        "--ops",
        "1000",
        "--lifetime-h",
        "10",
    ]


def test_config_path_validation(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    cfg = tmp_path / "cfg.json"
    cfg.write_text("{}", encoding="utf-8")
    inputs = iter([str(cfg), "results/run2"])
    monkeypatch.setattr("builtins.input", lambda _prompt="": next(inputs))
    captured = {}
    monkeypatch.setattr(ecc_wizard, "_command_action", lambda command: captured.setdefault("command", command))

    ecc_wizard._config_mode()
    assert captured["command"][0] == "compare"
    assert captured["command"][2] == str(cfg)


def test_back_keyword_raises_control(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("builtins.input", lambda _prompt="": "back")
    with pytest.raises(ecc_wizard.WizardControl):
        ecc_wizard._prompt(ecc_wizard.FieldSpec("x", "x"))
