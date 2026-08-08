"""Sensor platform for the YouLess (custom) integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from youless_api import YoulessAPI

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfPower,
    UnitOfVolume,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import YoulessConfigEntry, YoulessCoordinator


def _get(api: YoulessAPI, name: str) -> Any:
    """Return a top-level sensor object, or None if the device lacks it."""
    return getattr(api, name, None)


def _nested(api: YoulessAPI, obj: str, attr: str) -> Any:
    """Return a nested sensor object (e.g. power_meter.total), or None."""
    parent = getattr(api, obj, None)
    return getattr(parent, attr, None) if parent is not None else None


def _has_value(sensor: Any) -> bool:
    """True only when the meter exists AND currently reports a value.

    The youless_api library instantiates the water_meter / extra_meter
    objects even when those inputs are disabled on the device; only their
    ``.value`` stays None. Filtering on the object alone (``is not None``)
    would therefore register permanently-``unknown`` entities, so we filter
    on the value instead. A meter that is switched off now will appear after
    a reload once it is enabled again.
    """
    return sensor is not None and getattr(sensor, "value", None) is not None


# English display names, matching the built-in `youless` integration's
# translated device strings, but hardcoded so they stay in English regardless
# of the Home Assistant UI language.
DEVICE_GROUP_NAMES: dict[str, str] = {
    "power": "Power meter",
    "delivery": "Energy delivery meter",
    "gas": "Gas meter",
    "water": "Water meter",
    "extra": "S0 meter",
}


@dataclass(frozen=True, kw_only=True)
class YoulessSensorDescription(SensorEntityDescription):
    """A YouLess sensor plus how to read its value object from the API."""

    get_sensor: Callable[[YoulessAPI], Any]
    device_group: str


# key / name pairs match the built-in integration one-to-one. `name` holds the
# English text that the built-in integration produces via its translation keys.
SENSORS: list[YoulessSensorDescription] = [
    YoulessSensorDescription(
        key="usage",
        name="Current power usage",
        device_group="power",
        get_sensor=lambda api: _get(api, "current_power_usage"),
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    YoulessSensorDescription(
        key="power_total",
        name="Total energy import",
        device_group="power",
        get_sensor=lambda api: _nested(api, "power_meter", "total"),
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    YoulessSensorDescription(
        key="power_high",
        name="Energy import tariff 2",
        device_group="power",
        get_sensor=lambda api: _nested(api, "power_meter", "high"),
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    YoulessSensorDescription(
        key="power_low",
        name="Energy import tariff 1",
        device_group="power",
        get_sensor=lambda api: _nested(api, "power_meter", "low"),
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    YoulessSensorDescription(
        key="delivery_high",
        name="Energy export tariff 2",
        device_group="delivery",
        get_sensor=lambda api: _nested(api, "delivery_meter", "high"),
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    YoulessSensorDescription(
        key="delivery_low",
        name="Energy export tariff 1",
        device_group="delivery",
        get_sensor=lambda api: _nested(api, "delivery_meter", "low"),
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    YoulessSensorDescription(
        key="gas",
        name="Total gas usage",
        device_group="gas",
        get_sensor=lambda api: _get(api, "gas_meter"),
        device_class=SensorDeviceClass.GAS,
        native_unit_of_measurement=UnitOfVolume.CUBIC_METERS,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    YoulessSensorDescription(
        key="water",
        name="Total water usage",
        device_group="water",
        get_sensor=lambda api: _get(api, "water_meter"),
        device_class=SensorDeviceClass.WATER,
        native_unit_of_measurement=UnitOfVolume.CUBIC_METERS,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    YoulessSensorDescription(
        key="extra_total",
        name="Total energy",
        device_group="extra",
        get_sensor=lambda api: _nested(api, "extra_meter", "total"),
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    YoulessSensorDescription(
        key="extra_usage",
        name="Current usage",
        device_group="extra",
        get_sensor=lambda api: _nested(api, "extra_meter", "usage"),
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
]

# Per-phase sensors. Keys use the official `phase_<n>_...` form (WITH the
# underscore) so unique_ids and entity_ids line up with the built-in
# integration. Only created on devices/firmware that expose phase data.
for _p in (1, 2, 3):
    SENSORS.extend(
        [
            YoulessSensorDescription(
                key=f"phase_{_p}_power",
                name=f"Power phase {_p}",
                device_group="power",
                get_sensor=lambda api, o=f"phase{_p}": _nested(api, o, "power"),
                device_class=SensorDeviceClass.POWER,
                native_unit_of_measurement=UnitOfPower.WATT,
                state_class=SensorStateClass.MEASUREMENT,
            ),
            YoulessSensorDescription(
                key=f"phase_{_p}_voltage",
                name=f"Voltage phase {_p}",
                device_group="power",
                get_sensor=lambda api, o=f"phase{_p}": _nested(api, o, "voltage"),
                device_class=SensorDeviceClass.VOLTAGE,
                native_unit_of_measurement=UnitOfElectricPotential.VOLT,
                state_class=SensorStateClass.MEASUREMENT,
            ),
            YoulessSensorDescription(
                key=f"phase_{_p}_current",
                name=f"Current phase {_p}",
                device_group="power",
                get_sensor=lambda api, o=f"phase{_p}": _nested(api, o, "current"),
                device_class=SensorDeviceClass.CURRENT,
                native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
                state_class=SensorStateClass.MEASUREMENT,
            ),
        ]
    )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: YoulessConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the YouLess sensors that this particular device exposes."""
    coordinator = entry.runtime_data
    api = coordinator.device

    async_add_entities(
        YoulessSensor(coordinator, description)
        for description in SENSORS
        if _has_value(description.get_sensor(api))
    )


class YoulessSensor(CoordinatorEntity[YoulessCoordinator], SensorEntity):
    """A single YouLess measurement."""

    entity_description: YoulessSensorDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: YoulessCoordinator,
        description: YoulessSensorDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description

        device = coordinator.device
        base_identifier = (
            getattr(device, "mac_address", None)
            or coordinator.config_entry.entry_id
        )
        # Mirrors the built-in integration's `f"{DOMAIN}_{device}_{key}"`,
        # where its `device` is the MAC address it stores under CONF_DEVICE.
        # This only lines up with the built-in's registry entries when this
        # custom component's DOMAIN is also "youless" (see const.py).
        self._attr_unique_id = f"{DOMAIN}_{base_identifier}_{description.key}"

        # One virtual device per meter type, using the SAME identifier form as
        # the built-in integration: (DOMAIN, "power"), (DOMAIN, "gas"), ...
        # (Assumes a single YouLess device, exactly like the built-in.)
        group = description.device_group
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, group)},
            name=DEVICE_GROUP_NAMES.get(group, group.title()),
            manufacturer="YouLess",
            model=getattr(device, "model", None),
            sw_version=getattr(device, "firmware_version", None),
        )

    @property
    def native_value(self) -> float | None:
        """Return the current value of the underlying sensor object."""
        sensor = self.entity_description.get_sensor(self.coordinator.device)
        if sensor is None:
            return None
        return getattr(sensor, "value", None)

    @property
    def available(self) -> bool:
        """Only available while the coordinator succeeds and the meter exists."""
        return (
            super().available
            and self.entity_description.get_sensor(self.coordinator.device)
            is not None
        )
