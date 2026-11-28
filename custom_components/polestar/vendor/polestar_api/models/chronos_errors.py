"""Charge-now state and chronos error models (``chronos.services.v1``).

Field numbers from the Polestar app 5.15.1 (``GetEnabledOverrideChargeTimerActionResponse`` and ``GetErrorsResponse``).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum

from ..wire import ProtoMessage
from .common import Timestamp


class EnabledOverrideChargeTimerAction(IntEnum):
    """Which charge-now button the app offers right now."""

    UNSPECIFIED = 0
    CHARGE_NOW = 1
    RESUME_SCHEDULE = 2
    NOT_APPLICABLE = 3


class OverrideChargeTimerState(IntEnum):
    UNSPECIFIED = 0
    OVERRIDE_NOT_ACTIVE = 1
    OVERRIDE_ACTIVE_PENDING = 2
    OVERRIDE_ACTIVE = 3
    OVERRIDE_NOT_ACTIVE_PENDING = 4

    @property
    def is_active(self) -> bool | None:
        """True while charge now overrides the timer (or is about to), None when unknown."""
        if self is OverrideChargeTimerState.UNSPECIFIED:
            return None
        return self in (OverrideChargeTimerState.OVERRIDE_ACTIVE, OverrideChargeTimerState.OVERRIDE_ACTIVE_PENDING)


@dataclass(frozen=True)
class ChargeNowState(ProtoMessage, schema={
    1: "status",
    2: "enabled_action",
    3: "state",
    4: "updated_at",
}):
    """Whether charge now is overriding the charge timer (seen on a Polestar 2 and an XC40, 28 Nov 2026)."""

    status: int = 0  # chronos ResponseStatus: 1 = SUCCESS
    enabled_action: EnabledOverrideChargeTimerAction = EnabledOverrideChargeTimerAction.UNSPECIFIED
    state: OverrideChargeTimerState = OverrideChargeTimerState.UNSPECIFIED
    updated_at: int = 0  # epoch milliseconds


class ChronosError(IntEnum):
    UNSPECIFIED = 0
    TIMEOUT = 1
    CAR = 2
    WRONG_USAGE_MODE = 3
    PRIVACY_SETTINGS_ENABLED = 4


class ChargeLocationAction(IntEnum):
    UNSPECIFIED = 0
    CREATE_LOCATION = 1
    UPDATE_ALIAS = 2
    UPDATE_AMP_LIMIT = 3
    UPDATE_MINIMUM_SOC = 4
    UPDATE_TIMER = 5
    UPDATE_DEPARTURE_TIME = 6
    UPDATE_OPTIMIZED_SETTING = 7
    ADD_TIMER = 8
    ADD_DEPARTURE_TIME = 9
    DELETE_TIMER = 10
    DELETE_DEPARTURE_TIME = 11
    DELETE_LOCATION = 12


class ChargeNowAction(IntEnum):
    UNSPECIFIED = 0
    START_OVERRIDE_CHARGE_TIMER = 1
    STOP_OVERRIDE_CHARGE_TIMER = 2


class ParkingClimateTimerAction(IntEnum):
    UNSPECIFIED = 0
    SET_TIMER = 1
    DELETE_TIMER = 2
    SET_TIMER_SETTINGS = 3


@dataclass(frozen=True)
class PlainError(ProtoMessage, schema={1: "error"}):
    error: ChronosError = ChronosError.UNSPECIFIED


@dataclass(frozen=True)
class ChargeLocationError(ProtoMessage, schema={1: "error", 2: "action"}):
    error: ChronosError = ChronosError.UNSPECIFIED
    action: ChargeLocationAction = ChargeLocationAction.UNSPECIFIED


@dataclass(frozen=True)
class ChargeNowError(ProtoMessage, schema={1: "error", 2: "action"}):
    error: ChronosError = ChronosError.UNSPECIFIED
    action: ChargeNowAction = ChargeNowAction.UNSPECIFIED


@dataclass(frozen=True)
class ParkingClimateTimerError(ProtoMessage, schema={1: "error", 2: "action"}):
    error: ChronosError = ChronosError.UNSPECIFIED
    action: ParkingClimateTimerAction = ParkingClimateTimerAction.UNSPECIFIED


@dataclass(frozen=True)
class ChronosErrors(ProtoMessage, schema={
    1: "id",
    2: "vin",
    3: "amp_limit_error",
    4: "charge_location_error",
    5: "charge_now_error",
    6: "global_charge_timer_error",
    7: "parking_climate_timer_error",
    8: "target_soc_error",
    9: "error_time",
}):
    """One message from ``ErrorService/GetErrors``: a charging or climate timer change the car couldn't apply.

    The stream stays silent while there are no errors. Normally one of the ``*_error`` fields is set.
    """

    id: str = ""
    vin: str = ""
    amp_limit_error: PlainError | None = None
    charge_location_error: ChargeLocationError | None = None
    charge_now_error: ChargeNowError | None = None
    global_charge_timer_error: PlainError | None = None
    parking_climate_timer_error: ParkingClimateTimerError | None = None
    target_soc_error: PlainError | None = None
    error_time: Timestamp | None = None

    _DOMAINS = (
        "amp_limit", "charge_location", "charge_now", "global_charge_timer", "parking_climate_timer", "target_soc",
    )

    @property
    def domain(self) -> str | None:
        """Which setting failed, e.g. ``charge_now``; None when the message names none."""
        for name in self._DOMAINS:
            if getattr(self, f"{name}_error") is not None:
                return name
        return None

    @property
    def detail(self) -> PlainError | ChargeLocationError | ChargeNowError | ParkingClimateTimerError | None:
        name = self.domain
        return getattr(self, f"{name}_error") if name else None
