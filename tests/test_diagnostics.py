"""Diagnostics: the api_calls block that measures load on the Polestar backend."""

from __future__ import annotations

import importlib.util
import sys
import time
import types
from collections import Counter
from pathlib import Path

import pytest

from polestar_api import grpc as grpc_call


def _stub_module(monkeypatch, name: str, **attributes):
    module = types.ModuleType(name)
    for key, value in attributes.items():
        setattr(module, key, value)
    monkeypatch.setitem(sys.modules, name, module)
    return module


def _load_diagnostics(monkeypatch):
    """Load diagnostics.py standalone, without executing the real package __init__."""
    _stub_module(monkeypatch, "homeassistant")
    _stub_module(monkeypatch, "homeassistant.components")
    _stub_module(
        monkeypatch,
        "homeassistant.components.diagnostics",
        async_redact_data=lambda data, to_redact: data,
    )
    _stub_module(monkeypatch, "homeassistant.config_entries", ConfigEntry=object)
    _stub_module(monkeypatch, "homeassistant.const", CONF_EMAIL="email", CONF_PASSWORD="password")
    _stub_module(monkeypatch, "homeassistant.core", HomeAssistant=object)

    package_name = "_polestar_diagnostics_under_test"
    component_dir = Path(__file__).parents[1] / "custom_components" / "polestar"
    package = types.ModuleType(package_name)
    package.__path__ = [str(component_dir)]
    monkeypatch.setitem(sys.modules, package_name, package)
    _stub_module(monkeypatch, f"{package_name}.const", CONF_VIN="vin", DOMAIN="polestar")
    _stub_module(monkeypatch, f"{package_name}.coordinator", PolestarCoordinator=object)

    spec = importlib.util.spec_from_file_location(
        f"{package_name}.diagnostics", component_dir / "diagnostics.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, f"{package_name}.diagnostics", module)
    spec.loader.exec_module(module)
    return module


def test_api_calls_reports_counts_and_daily_rate(monkeypatch):
    diagnostics = _load_diagnostics(monkeypatch)
    started = time.time() - 12 * 60 * 60
    monkeypatch.setattr(grpc_call, "CALL_COUNTS", Counter({"/svc.B/Get": 30, "/svc.A/Get": 20}))
    monkeypatch.setattr(grpc_call, "CALL_COUNTS_SINCE", started)

    api_calls = diagnostics._api_call_diagnostics()

    assert api_calls["total"] == 50
    assert list(api_calls["per_method"]) == ["/svc.A/Get", "/svc.B/Get"]
    assert api_calls["per_method"]["/svc.B/Get"] == 30
    assert api_calls["since"].startswith(time.strftime("%Y-%m-%d", time.gmtime(started)))
    assert api_calls["per_day_rate"] == pytest.approx(100, rel=0.01)


def test_api_calls_with_no_traffic(monkeypatch):
    diagnostics = _load_diagnostics(monkeypatch)
    monkeypatch.setattr(grpc_call, "CALL_COUNTS", Counter())
    monkeypatch.setattr(grpc_call, "CALL_COUNTS_SINCE", time.time())

    api_calls = diagnostics._api_call_diagnostics()

    assert api_calls["total"] == 0
    assert api_calls["per_method"] == {}
    # Too early to tell: the startup burst would otherwise read as thousands of calls a day.
    assert api_calls["per_day_rate"] == "counted after the first hour"


def test_api_call_rate_waits_for_the_first_hour(monkeypatch):
    diagnostics = _load_diagnostics(monkeypatch)
    # As a real download showed: 45 calls in the first 4 minutes.
    monkeypatch.setattr(grpc_call, "CALL_COUNTS", Counter({"/svc.A/Get": 45}))
    monkeypatch.setattr(grpc_call, "CALL_COUNTS_SINCE", time.time() - 4 * 60)

    api_calls = diagnostics._api_call_diagnostics()

    assert api_calls["per_day_rate"] == "counted after the first hour"
    assert api_calls["minutes_counted"] == pytest.approx(4, abs=0.2)


def test_bytes_are_listed_as_numbers(monkeypatch):
    diagnostics = _load_diagnostics(monkeypatch)
    assert diagnostics._serialize({"reports_light_warnings": b"\x01\x02\x15"}) == {"reports_light_warnings": [1, 2, 21]}


def test_vehicle_block_reports_parking_climate_capabilities(monkeypatch):
    from types import SimpleNamespace

    from polestar_api.models.car_information import ParkingClimatizationCapabilities

    diagnostics = _load_diagnostics(monkeypatch)
    vehicle = SimpleNamespace(
        model_name="Polestar 2",
        model_year=2026,
        parking_climate_capabilities=ParkingClimatizationCapabilities(supports_steering_wheel_settings=False),
        steering_wheel_heat_levels=None,
    )
    coordinator = SimpleNamespace(
        vehicle=vehicle, update_interval=None, last_update_success=True, _poll_count=0,
        _unsupported_fetches=set(), _unsupported_streams=set(), _unsupported_commands=set(),
        _STREAMS=(), _stream_tasks={}, _stream_last_data={}, data=None,
    )

    block = diagnostics._coordinator_diagnostics(coordinator)

    assert block["parking_climate_capabilities"]["supports_steering_wheel_settings"] is False
    assert block["parking_climate_capabilities"]["steering_wheel_setting_levels"] == 0
    assert block["steering_wheel_heat_levels"] is None
