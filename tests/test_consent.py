"""Tests for data-sharing / privacy-consent models — round-trip encode/decode."""

from polestar_api.models.common import Timestamp
from polestar_api.models.consent import (
    PrivacySetting,
    PrivacySettingDetail,
    PrivacySettingStateExRequest,
    PrivacySettingTexts,
    PrivacySettingType,
    PrivacySettingsStreamRequest,
    RemoteFunctionDataSharing,
    RemoteFunctionDataSharingRequest,
    SetPrivacySettingStateRequest,
)


class TestRemoteFunctionDataSharing:
    def test_round_trip(self):
        sharing = RemoteFunctionDataSharing(enabled=True, car_in_sync=True, read_only=False)
        restored = RemoteFunctionDataSharing.from_bytes(sharing.to_bytes())
        assert restored == sharing

    def test_request_round_trip(self):
        req = RemoteFunctionDataSharingRequest(vin="YV1ABC123")
        restored = RemoteFunctionDataSharingRequest.from_bytes(req.to_bytes())
        assert restored.vin == "YV1ABC123"

    def test_empty(self):
        restored = RemoteFunctionDataSharing.from_bytes(b"")
        assert restored.enabled is False
        assert restored.car_in_sync is False
        assert restored.read_only is False


class TestPrivacySetting:
    def test_round_trip(self):
        setting = PrivacySetting(
            setting_type=PrivacySettingType.VEHICLE_DATA_SHARING,
            service_id="vehicle-data-sharing",
            enabled=True,
            read_only=False,
        )
        restored = PrivacySetting.from_bytes(setting.to_bytes())
        assert restored == setting

    def test_stream_request_round_trip(self):
        req = PrivacySettingsStreamRequest(vin="YV1ABC123")
        restored = PrivacySettingsStreamRequest.from_bytes(req.to_bytes())
        assert restored.vin == "YV1ABC123"


class TestPrivacySettingDetail:
    def test_round_trip(self):
        detail = PrivacySettingDetail(
            texts=PrivacySettingTexts(
                service_name="Vehicle location sharing",
                service_description="Share location data with third parties.",
                privacy_notice_version="3",
                privacy_notice_market="SE",
            ),
            enabled=True,
            set_by_user=True,
            read_only=False,
            read_only_reason="",
            expiry_time=Timestamp(seconds=1_700_000_000, nanos=0),
        )
        restored = PrivacySettingDetail.from_bytes(detail.to_bytes())
        assert restored == detail

    def test_state_ex_request_round_trip(self):
        req = PrivacySettingStateExRequest(vin="YV1ABC123", service_id="vehicle-data-sharing", locale="en")
        restored = PrivacySettingStateExRequest.from_bytes(req.to_bytes())
        assert restored == req

    def test_empty(self):
        restored = PrivacySettingDetail.from_bytes(b"")
        assert restored.texts is None
        assert restored.expiry_time is None


class TestSetPrivacySettingStateRequest:
    def test_round_trip(self):
        req = SetPrivacySettingStateRequest(
            vin="YV1ABC123",
            service_id="vehicle-data-sharing",
            enabled=False,
            expiry_time=Timestamp(seconds=42),
            privacy_notice_market="SE",
            privacy_notice_version="3",
        )
        restored = SetPrivacySettingStateRequest.from_bytes(req.to_bytes())
        assert restored == req


# -- Reading the data-sharing toggle (a server stream in the app) --


async def test_data_sharing_is_read_from_the_first_stream_message(monkeypatch):
    from types import SimpleNamespace
    from unittest.mock import AsyncMock

    from polestar_api.backend import C3
    from polestar_api.services.consent import ConsentServiceClient

    calls = []

    async def stream(channel, method, request, *, metadata=None, retries=2):
        calls.append(method)
        yield RemoteFunctionDataSharing(enabled=True, car_in_sync=True, read_only=True).to_bytes()
        raise AssertionError("only the first message should be read")

    async def unary(*args, **kwargs):
        raise AssertionError("GetRemoteFunctionDataSharing is a stream, not a unary call")

    monkeypatch.setattr("polestar_api.services.consent.grpc_call.unary_stream", stream)
    monkeypatch.setattr("polestar_api.services.consent.grpc_call.unary_unary", unary)
    connection = SimpleNamespace(backend=C3, channel=object(), get_metadata=AsyncMock(return_value={}))

    result = await ConsentServiceClient(connection, "TESTVIN").get_remote_function_data_sharing()

    assert result == RemoteFunctionDataSharing(enabled=True, car_in_sync=True, read_only=True)
    assert calls == [f"{C3.privacy_settings_svc}/GetRemoteFunctionDataSharing"]


async def test_data_sharing_is_none_when_the_stream_sends_nothing(monkeypatch):
    from types import SimpleNamespace
    from unittest.mock import AsyncMock

    from polestar_api.backend import C3
    from polestar_api.services.consent import ConsentServiceClient

    async def stream(*args, **kwargs):
        return
        yield

    monkeypatch.setattr("polestar_api.services.consent.grpc_call.unary_stream", stream)
    connection = SimpleNamespace(backend=C3, channel=object(), get_metadata=AsyncMock(return_value={}))

    assert await ConsentServiceClient(connection, "TESTVIN").get_remote_function_data_sharing() is None
