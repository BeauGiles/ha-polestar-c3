"""Charge-now state and the chronos error stream (models only; the app's field numbers)."""

from __future__ import annotations

from polestar_api.codec import encode_int32, encode_message, encode_string
from polestar_api.models.chronos_errors import (
    ChargeNowState,
    ChronosError,
    ChronosErrors,
    EnabledOverrideChargeTimerAction,
    OverrideChargeTimerState,
)
from polestar_api.wire import describe_raw


def test_charge_now_state_as_both_cars_sent_it():
    # 28 Nov 2026, Polestar 2 and XC40 parked: SUCCESS, NOT_APPLICABLE, OVERRIDE_NOT_ACTIVE.
    state = ChargeNowState.from_bytes(encode_int32(1, 1) + encode_int32(2, 3) + encode_int32(3, 1))

    assert state.enabled_action is EnabledOverrideChargeTimerAction.NOT_APPLICABLE
    assert state.state is OverrideChargeTimerState.OVERRIDE_NOT_ACTIVE
    assert state.state.is_active is False


def test_charge_now_active_and_pending_count_as_on():
    assert OverrideChargeTimerState.OVERRIDE_ACTIVE.is_active is True
    assert OverrideChargeTimerState.OVERRIDE_ACTIVE_PENDING.is_active is True
    assert OverrideChargeTimerState.OVERRIDE_NOT_ACTIVE_PENDING.is_active is False
    assert OverrideChargeTimerState.UNSPECIFIED.is_active is None


def test_an_error_names_the_setting_that_failed():
    reply = (
        encode_string(1, "id")
        + encode_message(5, encode_int32(1, 2) + encode_int32(2, 1))  # charge now: CAR, START_OVERRIDE_CHARGE_TIMER
        + encode_message(9, encode_int32(1, 1795851836))
    )
    errors = ChronosErrors.from_bytes(reply)

    assert errors.domain == "charge_now"
    assert errors.detail.error is ChronosError.CAR
    assert errors.detail.action.name == "START_OVERRIDE_CHARGE_TIMER"
    assert errors.error_time.seconds == 1795851836


def test_an_error_with_no_setting():
    errors = ChronosErrors.from_bytes(encode_string(1, "id"))

    assert errors.domain is None
    assert errors.detail is None


def test_raw_values_are_described():
    assert describe_raw(b"536") == "536"
    assert describe_raw(encode_message(1, encode_int32(1, 5))) == {"unknown_1": {"unknown_1": 5}}
    assert describe_raw(b"\xff\xfe") == "hex:fffe"
    assert describe_raw(7) == 7
