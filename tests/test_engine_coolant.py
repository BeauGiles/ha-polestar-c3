"""Engine coolant low binary sensor (health field 7), matching Volvo C3."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "custom_components" / "polestar"


def test_sensor_is_defined_hidden_when_unreported_and_named_like_volvo():
    src = (ROOT / "binary_sensor.py").read_text()
    assert 'key="engine_coolant_problem"' in src
    assert 'd.health.engine_coolant_level_warning.name != "UNSPECIFIED"' in src
    # Same problem flag as brake fluid: off for NO_WARNING, on for TOO_LOW.
    assert "_level_problem(d.health.engine_coolant_level_warning)" in src
    import json

    for path in (ROOT / "strings.json", ROOT / "translations" / "en.json"):
        names = json.loads(path.read_text())["entity"]["binary_sensor"]
        assert names["engine_coolant_problem"]["name"] == "Engine coolant low"
