"""Powertrain, battery capacity and capability flags decoded from the C3 car-information reply."""

import struct

from polestar_api.models.car_information import CarDetails, DigitalKeyType, DrivetrainType, EngineType


def _varint(n: int) -> bytes:
    out = b""
    while True:
        b = n & 0x7F
        n >>= 7
        out += bytes([b | (0x80 if n else 0)])
        if not n:
            return out


def _field(num: int, wire: int, payload: bytes) -> bytes:
    return _varint(num << 3 | wire) + payload


def _ld(num: int, data: bytes) -> bytes:
    return _field(num, 2, _varint(len(data)) + data)


def test_propulsion_digital_key_and_flags_decode():
    propulsion = _field(1, 0, _varint(1)) + _field(5, 5, struct.pack("<f", 82.0)) + _field(6, 0, _varint(1))
    car = (
        _ld(1, b"VIN")
        + _ld(39, _field(1, 0, _varint(3)))
        + _ld(40, propulsion)
        + _field(43, 0, _varint(4))
        + _field(70, 0, _varint(1))
    )
    decoded = CarDetails.from_bytes(car)
    assert decoded.propulsion.engine_type is EngineType.ELECTRIC
    assert decoded.propulsion.drivetrain_type is DrivetrainType.AWD
    assert decoded.propulsion.battery_capacity_kwh == 82.0
    assert decoded.propulsion.fuel_tank_volume == 0
    assert decoded.digital_key.type is DigitalKeyType.POLESTAR_2
    assert decoded.num_doors == 4
    assert decoded.has_performance_software_upgrade is True
    assert decoded.supports_engine_start is False


def test_reporting_flags_decode_and_default_to_false():
    car = CarDetails.from_bytes(
        _ld(1, b"VIN") + _field(23, 0, _varint(1)) + _field(50, 0, _varint(1)) + _field(87, 0, _varint(1))
    )
    assert car.reports_tyre_pressure_warning and car.reports_tyre_pressure_in_kpa and car.reports_service_warning
    bare = CarDetails.from_bytes(_ld(1, b"VIN"))
    # A Polestar 2 sends neither tyre flag, so they decode as False (the car says it does not report them).
    assert not bare.reports_tyre_pressure_warning and not bare.reports_tyre_pressure_in_kpa


def test_air_purification_capability_decodes_and_is_absent_without_the_plus_pack():
    with_pack = CarDetails.from_bytes(_ld(1, b"VIN") + _ld(34, _field(1, 0, _varint(1)) + _field(2, 0, _varint(1))))
    assert with_pack.air_purification is not None and with_pack.air_purification.any_supported
    # A car without the feature does not send field 34 at all.
    assert CarDetails.from_bytes(_ld(1, b"VIN")).air_purification is None


def test_car_facts_decode():
    # Field values as a Polestar 2 sends them (28 Nov 2026): 2600 kg, pilot assist, DC inlet on the left,
    # electric parking heating and cooling, climate runs of up to 30 minutes.
    from polestar_api.models.car_information import (
        DriverSide,
        ElectricInletDcLocation,
        ParkingClimatizationType,
        ParkingHeatingType,
    )

    car = CarDetails.from_bytes(
        _ld(1, b"VIN")
        + _ld(35, _field(2, 0, _varint(2)))
        + _ld(37, _field(1, 0, _varint(3)) + _field(2, 0, _varint(3)) + _field(3, 0, _varint(30)))
        + _field(44, 5, struct.pack("<f", 2600.0))
        + _field(46, 0, _varint(1))
        + _field(86, 0, _varint(1))
    )
    assert car.gross_vehicle_weight_rating == 2600.0
    assert car.driver_side is DriverSide.LEFT
    assert car.supports_pilot_assist is True
    assert car.charging.electric_inlet_dc_location is ElectricInletDcLocation.LEFT
    assert car.parking_climatization.type is ParkingClimatizationType.HEATING_AND_COOLING
    assert car.parking_climatization.heating_type is ParkingHeatingType.ELECTRICAL
    assert car.parking_climatization.max_runtime == 30
    from polestar_api.wire import unknown_fields

    assert not unknown_fields(car)


def test_negative_int_decodes_as_negative():
    # The OTA scheduler sends relative_time -2 (nothing scheduled) as a 10-byte varint.
    from polestar_api.models.ota import Scheduler

    scheduler = Scheduler.from_bytes(_field(2, 0, _varint((1 << 64) - 2)))
    assert scheduler.relative_time == -2
    assert Scheduler.from_bytes(scheduler.to_bytes()).relative_time == -2
