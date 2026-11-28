"""Diagnostics support for the Polestar integration."""

from __future__ import annotations

import asyncio
import time
from dataclasses import fields, is_dataclass
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import HomeAssistant

from polestar_api import codec
from polestar_api import grpc as grpc_call
from polestar_api.services.chronos import wrap_chronos
from polestar_api.wire import describe_raw, unknown_fields

from .const import CONF_VIN, DOMAIN
from .coordinator import PolestarCoordinator

TO_REDACT = {
    CONF_EMAIL,
    CONF_PASSWORD,
    CONF_VIN,
    "username",
    "internal_id",
    "registration_no",
    "id",
    "location_id",
    "location_alias",
    "latitude",
    "longitude",
    "altitude",
    "plug_and_charge_pcid",
    "vin",
    "battery_pack_serial_number",
    "visual_id",
    "registration_plate",
    "nickname",
}


def _serialize(value: Any) -> Any:
    """Convert models to JSON-friendly structures, keeping enum names readable."""
    if is_dataclass(value) and not isinstance(value, type):
        # Fields the library doesn't know yet are kept as unknown_<n>, so new ones show up here first.
        return {f.name: _serialize(getattr(value, f.name)) for f in fields(value)} | unknown_fields(value)
    if isinstance(value, Enum):
        return value.name
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: _serialize(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_serialize(item) for item in value]
    return value


def _stream_diagnostics(coordinator: PolestarCoordinator) -> dict[str, Any]:
    """Report liveness of the long-lived streaming subscriptions."""
    now = time.monotonic()
    streams: dict[str, Any] = {}
    for attr in sorted(coordinator._STREAMS):
        task = coordinator._stream_tasks.get(attr)
        last_data = coordinator._stream_last_data.get(attr)
        info: dict[str, Any] = {
            "started": task is not None,
            "running": task is not None and not task.done(),
            "supported": attr not in coordinator._unsupported_streams,
            "seconds_since_last_data": (
                round(now - last_data, 1) if last_data is not None else None
            ),
        }
        if task is not None and task.done() and not task.cancelled():
            err = task.exception()
            if err is not None:
                info["failed_with"] = type(err).__name__
        streams[attr] = info
    return streams


def _api_call_diagnostics() -> dict[str, Any]:
    """Report gRPC call attempts per method since the library was loaded."""
    total = sum(grpc_call.CALL_COUNTS.values())
    elapsed = max(time.time() - grpc_call.CALL_COUNTS_SINCE, 1.0)
    return {
        "total": total,
        "per_method": dict(sorted(grpc_call.CALL_COUNTS.items())),
        "since": datetime.fromtimestamp(grpc_call.CALL_COUNTS_SINCE, UTC).isoformat(),
        "per_day_rate": round(total * 86400 / elapsed, 1),
    }


def _pb_str(field: int, value: str) -> bytes:
    return codec.encode_string(field, value)


async def _extra_reads(vehicle: Any) -> dict[str, Any]:
    """Read-only calls the integration doesn't poll, made once when diagnostics are downloaded.

    Raw replies are shown by field number (unknown_<n>), as nothing in the integration names them.
    """
    read_raw = getattr(vehicle, "read_raw", None)
    if read_raw is None:  # demo mode
        return {}
    vin = vehicle.vin
    raw_calls = {
        "car_preview": ("/car_information.CarInformation/GetCarPreview", _pb_str(1, vin), False),
        "connected_services": (
            "/userServices.ConnectedServices/GetConnectedServicesStatusByVin", _pb_str(1, vin) + _pb_str(2, "en"), False
        ),
        "pnc_enabled": ("/pnc_enabled.PncEnabledService/GetPncEnabled", _pb_str(1, vin), False),
        # Silent while there are no errors, so "no reply" is normal.
        "chronos_errors": ("/chronos.services.v1.ErrorService/GetErrors", wrap_chronos(vin), True),
    }

    async def raw(method: str, request: bytes, stream: bool) -> Any:
        data = await read_raw(method, request, stream=stream, timeout=5.0)
        return describe_raw(data) if data else "no reply within 5 s"

    async def model(fn: Any) -> Any:
        value = await asyncio.wait_for(fn(), 15)
        return _serialize(value) if value is not None else "no reply"

    jobs: dict[str, Any] = {name: raw(*call) for name, call in raw_calls.items()}
    jobs["charge_now"] = model(vehicle.get_charge_now_state)
    jobs["remote_function_data_sharing"] = model(vehicle.get_remote_function_data_sharing)
    results = await asyncio.gather(*jobs.values(), return_exceptions=True)
    out: dict[str, Any] = {}
    for name, result in zip(jobs, results, strict=True):
        if isinstance(result, BaseException):
            out[name] = f"{type(result).__name__}: {str(result)[:200]}"
        else:
            out[name] = result
    return out


def _scrub(value: Any, secrets: tuple[str, ...]) -> Any:
    """Replace the VIN and similar strings wherever they turn up, including in fields nothing names yet."""
    if isinstance(value, dict):
        return {k: _scrub(v, secrets) for k, v in value.items()}
    if isinstance(value, list):
        return [_scrub(v, secrets) for v in value]
    if isinstance(value, str):
        for secret in secrets:
            value = value.replace(secret, "**REDACTED**")
    return value


def _coordinator_diagnostics(coordinator: PolestarCoordinator) -> dict[str, Any]:
    """Dump one vehicle's coordinator state."""
    return {
        "model_name": coordinator.vehicle.model_name,
        "model_year": coordinator.vehicle.model_year,
        "parking_climate_capabilities": _serialize(
            getattr(coordinator.vehicle, "parking_climate_capabilities", None)
        ),
        "steering_wheel_heat_levels": getattr(coordinator.vehicle, "steering_wheel_heat_levels", None),
        "update_interval_seconds": (
            coordinator.update_interval.total_seconds()
            if coordinator.update_interval is not None
            else None
        ),
        "last_update_success": coordinator.last_update_success,
        "poll_count": coordinator._poll_count,
        "unsupported_fetches": sorted(coordinator._unsupported_fetches),
        "unsupported_streams": sorted(coordinator._unsupported_streams),
        "unsupported_commands": sorted(coordinator._unsupported_commands),
        "streams": _stream_diagnostics(coordinator),
        # The whole car record as last read (capabilities, limits, unknown fields), identifiers redacted.
        "car_record": async_redact_data(_serialize(getattr(coordinator.vehicle, "car_record", None)), TO_REDACT),
        "data": async_redact_data(_serialize(coordinator.data), TO_REDACT),
    }


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    data = hass.data[DOMAIN][entry.entry_id]
    coordinators = list(data["coordinators"].values())
    extra = await asyncio.gather(*(_extra_reads(c.vehicle) for c in coordinators), return_exceptions=True)
    vehicles = []
    for coordinator, reads in zip(coordinators, extra, strict=True):
        vehicle = _coordinator_diagnostics(coordinator)
        vehicle["extra_reads"] = (
            async_redact_data(reads, TO_REDACT) if isinstance(reads, dict) else f"{type(reads).__name__}: {reads}"
        )
        vehicles.append(vehicle)
    secrets = tuple(
        s for c in coordinators
        for s in (c.vehicle.vin, getattr(c.vehicle, "plug_and_charge_pcid", None), getattr(c.vehicle, "registration_no", None))
        if isinstance(s, str) and len(s) >= 4
    )
    return _scrub({
        "entry_data": async_redact_data(dict(entry.data), TO_REDACT),
        "entry_options": async_redact_data(dict(entry.options), TO_REDACT),
        "demo_mode": data["api"] is None,
        "api_calls": _api_call_diagnostics(),
        "vehicles": vehicles,
    }, secrets)
