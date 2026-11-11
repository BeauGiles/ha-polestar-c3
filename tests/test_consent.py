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
