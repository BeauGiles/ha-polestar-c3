"""The car's alarm (exterior field 15) is read, so the Alarm sensor can show it triggered."""

from __future__ import annotations

from polestar_api.codec import encode
from polestar_api.models.exterior import CarAlarmStatus
from polestar_api.services.exterior import ExteriorServiceClient


def _parse(**fields: int):
    schema = {name: (number, "int32") for name, number in (("central_lock", 2), ("front_left", 3), ("alarm", 15))}
    return ExteriorServiceClient._parse({"exterior": encode(schema, fields)})


def test_idle_alarm_as_both_cars_send_it():
    # 28 Nov 2026: a Polestar 2 and an XC40 both send ALARM_STATUS_IDLE (1).
    assert _parse(central_lock=2, front_left=2, alarm=1).alarm is CarAlarmStatus.IDLE


def test_triggered_alarm_is_read():
    assert _parse(central_lock=2, alarm=2).alarm is CarAlarmStatus.TRIGGERED


def test_an_update_with_only_the_alarm_counts_and_merges():
    full = _parse(central_lock=2, front_left=2, alarm=1)
    update = _parse(alarm=2)

    assert update is not None  # an alarm-only stream message is not thrown away as empty
    merged = update.merge(full)
    assert merged.alarm is CarAlarmStatus.TRIGGERED
    assert merged.is_locked is True


def test_an_update_without_the_alarm_keeps_the_last_state():
    full = _parse(central_lock=2, alarm=2)
    update = _parse(front_left=3)

    assert update.merge(full).alarm is CarAlarmStatus.TRIGGERED
