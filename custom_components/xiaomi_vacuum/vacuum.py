"""Xiaomi 1C Vacuum (STYTJ01ZHM) – Home Assistant 2025.1+ compatible."""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from datetime import timedelta

from homeassistant.components.vacuum import (
    StateVacuumEntity,
    VacuumActivity,
    VacuumEntityFeature,
)
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_TOKEN
from homeassistant.helpers.icon import icon_for_battery_level
import voluptuous as vol

# --------------  relative imports from bundled miio  --------------
from .miio.dreamevacuum import DreameVacuum as DreameDevice
from .miio.exceptions import DeviceException
# ------------------------------------------------------------------

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(seconds=30)

SUPPORT_XIAOMI_1C = (
    VacuumEntityFeature.START
    | VacuumEntityFeature.STOP
    | VacuumEntityFeature.PAUSE
    | VacuumEntityFeature.RETURN_HOME
    | VacuumEntityFeature.FAN_SPEED
    | VacuumEntityFeature.SEND_COMMAND
    | VacuumEntityFeature.LOCATE
    | VacuumEntityFeature.STATE
)

FAN_SPEEDS = {"Silent": 0, "Standard": 1, "Medium": 2, "Turbo": 3}

# Map device status enum -> VacuumActivity
STATUS_TO_ACTIVITY = {
    1: VacuumActivity.CLEANING,    # Sweeping
    2: VacuumActivity.IDLE,        # Idle
    3: VacuumActivity.PAUSED,      # Paused
    4: VacuumActivity.ERROR,       # Error
    5: VacuumActivity.RETURNING,   # Go_charging
    6: VacuumActivity.DOCKED,      # Charging
}

PLATFORM_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_TOKEN): str,
        vol.Optional(CONF_NAME, default="Xiaomi 1C"): str,
    },
    extra=vol.ALLOW_EXTRA,
)


def setup_platform(hass, config, add_entities, discovery_info=None) -> None:
    """Set up the vacuum platform."""
    host = config[CONF_HOST]
    token = config[CONF_TOKEN]
    name = config[CONF_NAME]

    try:
        device = DreameDevice(host, token)
        vacuum = Xiaomi1CVacuum(name, device)
        add_entities([vacuum], True)
    except DeviceException as exc:
        _LOGGER.error("Failed to connect to Xiaomi 1C vacuum: %s", exc)
        return False


class Xiaomi1CVacuum(StateVacuumEntity):
    """Representation of the vacuum."""

    def __init__(self, name: str, device: DreameDevice) -> None:
        self._name = name
        self._device = device
        self._available = False
        self._battery: Optional[int] = None
        self._fan_speed: Optional[int] = None
        self._status: Optional[int] = None
        self._error: Optional[int] = None
        self._clean_time: Optional[int] = None
        self._clean_area: Optional[int] = None

    @property
    def name(self) -> str:
        return self._name

    @property
    def unique_id(self) -> str:
        return f"xiaomi_1c_{self._device.ip}"

    @property
    def available(self) -> bool:
        return self._available

    @property
    def supported_features(self) -> int:
        return SUPPORT_XIAOMI_1C

    @property
    def activity(self) -> VacuumActivity | None:
        """Return the current activity (HA 2025.1+)."""
        if self._status is None:
            return None
        return STATUS_TO_ACTIVITY.get(self._status, VacuumActivity.IDLE)

    @property
    def battery_level(self) -> Optional[int]:
        return self._battery

    @property
    def battery_icon(self) -> str:
        charging = self._status == 6  # Charging
        return icon_for_battery_level(self._battery, charging=charging)

    @property
    def fan_speed(self) -> Optional[str]:
        if self._fan_speed is None:
            return None
        rev = {v: k for k, v in FAN_SPEEDS.items()}
        return rev.get(self._fan_speed, "Standard")

    @property
    def fan_speed_list(self) -> List[str]:
        return list(FAN_SPEEDS.keys())

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        attrs: Dict[str, Any] = {}
        if self._clean_time is not None:
            attrs["cleaning_time"] = self._clean_time
        if self._clean_area is not None:
            attrs["cleaning_area"] = self._clean_area
        if self._error is not None and self._error != 0:
            attrs["error_code"] = self._error
        return attrs

    def update(self) -> None:
        """Fetch state from the device."""
        try:
            status = self._device.status()
            self._available = True
            self._battery = status.battery
            self._fan_speed = status.fan_speed
            self._status = status.status
            self._error = status.error
            self._clean_time = status.last_clean
            self._clean_area = status.area
        except DeviceException as exc:
            _LOGGER.error("Update failed: %s", exc)
            self._available = False

    # ----------  Vacuum commands  ----------
    def start(self) -> None:
        self._device.start()

    def stop(self, **kwargs: Any) -> None:
        self._device.stop()

    def pause(self, **kwargs: Any) -> None:
        self._device.stop_sweeping()  # 1C has no real pause, map to stop

    def return_to_base(self, **kwargs: Any) -> None:
        self._device.return_home()

    def locate(self, **kwargs: Any) -> None:
        self._device.find()

    def set_fan_speed(self, fan_speed: str, **kwargs: Any) -> None:
        if fan_speed not in FAN_SPEEDS:
            _LOGGER.error("Invalid fan speed %s", fan_speed)
            return
        self._device.set_fan_speed(FAN_SPEEDS[fan_speed])

    def send_command(self, command: str, params: Optional[Dict] = None, **kwargs: Any) -> None:
        self._device.raw_command(command, params or [])