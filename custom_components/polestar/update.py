"""Update platform for Polestar OTA state."""

from __future__ import annotations

from datetime import UTC, datetime

from homeassistant.components.update import (
    UpdateDeviceClass,
    UpdateEntity,
    UpdateEntityDescription,
    UpdateEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import DOMAIN
from .coordinator import PolestarCoordinator
from .entity import PolestarEntity
from polestar_api.models.ota import SoftwareState
from .utils import enum_name, release_notes, timestamp_to_iso

PARALLEL_UPDATES = 1


def _installed_at(seconds: int | None) -> str | None:
    """Epoch seconds from the car record as an ISO time, or None."""
    if not seconds:
        return None
    return datetime.fromtimestamp(seconds, tz=UTC).isoformat()

_IN_PROGRESS_STATES = {
    SoftwareState.DOWNLOAD_STARTED,
    SoftwareState.DOWNLOAD_COMPLETED,
    SoftwareState.INSTALLATION_INITIATED,
    SoftwareState.INSTALLATION_STARTED,
    SoftwareState.INSTALLATION_SCHEDULED,
    SoftwareState.INSTALLATION_SCHEDULE_TRIGGERED,
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Polestar update entities."""
    data = hass.data[DOMAIN][entry.entry_id]
    entities = [
        PolestarOtaUpdate(coordinator)
        for coordinator in data["coordinators"].values()
    ]
    async_add_entities(entities)


class PolestarOtaUpdate(PolestarEntity, UpdateEntity, RestoreEntity):
    """OTA update entity backed by the Polestar software info API."""

    _attr_device_class = UpdateDeviceClass.FIRMWARE
    _attr_translation_key = "software_update"
    _attr_supported_features = UpdateEntityFeature.INSTALL | UpdateEntityFeature.RELEASE_NOTES

    @property
    def entity_picture(self) -> str | None:
        """No picture, so Home Assistant shows the standard update icon instead of the Polestar logo.

        UpdateEntity falls back to the brand logo whenever the picture is None, so setting
        ``_attr_entity_picture = None`` is not enough (the logo was still shown, Nov 2026): the property itself
        is overridden.
        """
        return None

    def __init__(self, coordinator: PolestarCoordinator) -> None:
        super().__init__(coordinator)
        self.entity_description = UpdateEntityDescription(key="software_update")
        self._attr_unique_id = f"{self._vehicle.vin}_software_update"

    async def async_added_to_hass(self) -> None:
        """Restore the last known installed version across restarts."""
        await super().async_added_to_hass()
        if self.coordinator.installed_version_cache:
            return
        last_state = await self.async_get_last_state()
        if last_state is None:
            return
        installed_version = last_state.attributes.get("installed_version")
        if isinstance(installed_version, str) and installed_version:
            self.coordinator.restore_installed_version_cache(installed_version)

    @property
    def available(self) -> bool:
        return super().available and self.coordinator.data is not None and (
            self.coordinator.data.software is not None or bool(self.coordinator.installed_version_cache)
        )

    @property
    def installed_version(self) -> str | None:
        if self.coordinator.installed_version_cache:
            return self.coordinator.installed_version_cache
        if (
            self.coordinator.data
            and self.coordinator.data.software
            and self.coordinator.data.software.state in {
                SoftwareState.UNKNOWN,
                SoftwareState.INSTALLATION_COMPLETED,
                SoftwareState.INSTALLATION_UNKNOWN,
            }
        ):
            return self.coordinator.data.software.new_sw_version or None
        return None

    @property
    def latest_version(self) -> str | None:
        if self.coordinator.data and self.coordinator.data.software:
            return self.coordinator.data.software.new_sw_version or None
        return self.installed_version  # no OTA record: nothing newer is known

    @property
    def in_progress(self) -> bool | int:
        if self.coordinator.data and self.coordinator.data.software:
            return self.coordinator.data.software.state in _IN_PROGRESS_STATES
        return False

    @property
    def release_summary(self) -> str | None:
        software = self.coordinator.data.software if self.coordinator.data else None
        if software is None or software.description is None:
            return None
        # The short description only: the full notes are under "Release notes" (Home Assistant caps this at 255).
        summary = release_notes(software.description.short_desc)
        return summary[:255] if summary else None

    async def async_release_notes(self) -> str | None:
        """The full release notes the app shows, converted from the backend's markup."""
        software = self.coordinator.data.software if self.coordinator.data else None
        if software is None or software.description is None:
            return None
        return release_notes(software.description.long_desc) or release_notes(software.description.short_desc)

    @property
    def extra_state_attributes(self) -> dict[str, str | None]:
        software = self.coordinator.data.software if self.coordinator.data else None
        schedule = self.coordinator.data.ota_schedule if self.coordinator.data else None
        return {
            "software_id": software.software_id if software else None,
            "software_state": enum_name(software.state) if software else None,
            "software_state_timestamp": timestamp_to_iso(software.state_timestamp) if software else None,
            "scheduled_for": timestamp_to_iso(software.schedule_info.scheduled_at) if software and software.schedule_info else None,
            "scheduler_status": enum_name(schedule.status) if schedule else None,
            "scheduler_scheduled_time": timestamp_to_iso(schedule.scheduled_time) if schedule else None,
            "scheduler_set_by": enum_name(schedule.set_by) if schedule else None,
            # When the current software was installed (car record field 92). Not sent before a car's first OTA.
            "installed_at": _installed_at(getattr(self._vehicle, "software_installed_at", None)),
        }

    async def async_install(
        self,
        version: str | None,
        backup: bool,
        **kwargs,
    ) -> None:
        """Install the currently available OTA update immediately."""
        if version is not None and version != self.latest_version:
            raise HomeAssistantError(f"Version {version} is not the advertised OTA version")
        await self.coordinator.async_install_ota_now()
