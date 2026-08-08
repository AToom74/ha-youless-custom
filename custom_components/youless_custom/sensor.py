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


# Mirrors the device grouping of the built-in `youless` integration, so a
# YouLess device shows up the same way in the device list: one virtual
# device per meter type instead of a single device holding every sensor.
DEVICE_GROUP_NAMES: dict[str, str] = {
    "power": "Power",
    "delivery": "Delivery",
    "gas": "Gas",
    "water": "Water",
    "extra": "Extra",
}


@dataclass(frozen=True, kw_only=True)
class YoulessSensorDescription(SensorEntityDescription):
    """A YouLess sensor plus how to read its value object from the API."""

    get_sensor: Callable[[YoulessAPI], Any]
    device_group: str


SENSORS: list[YoulessSensorDescription] = [
    YoulessSensorDescription(
        key="power_usage",
        name="Usage",
        device_group="power",
        get_sensor=lambda api: _get(api, "current_power_usage"),
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    YoulessSensorDescription(
        key="power_total",
        name="Total",
        device_group="power",
        get_sensor=lambda api: _nested(api, "power_meter", "total"),
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    YoulessSensorDescription(
        key="power_high",
        name="High tariff",
        device_group="power",
        get_sensor=lambda api: _nested(api, "power_meter", "high"),
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    YoulessSensorDescription(
        key="power_low",
        name="Low tariff",
        device_group="power",
        get_sensor=lambda api: _nested(api, "power_meter", "low"),
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    YoulessSensorDescription(
        key="delivery_high",
        name="High tariff",
        device_group="delivery",
        get_sensor=lambda api: _nested(api, "delivery_meter", "high"),
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    YoulessSensorDescription(
        key="delivery_low",
        name="Low tariff",
        device_group="delivery",
        get_sensor=lambda api: _nested(api, "delivery_meter", "low"),
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    YoulessSensorDescription(
        key="gas",
        name=None,
        device_group="gas",
        get_sensor=lambda api: _get(api, "gas_meter"),
        device_class=SensorDeviceClass.GAS,
        native_unit_of_measurement=UnitOfVolume.CUBIC_METERS,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    YoulessSensorDescription(
        key="water",
        name=None,
        device_group="water",
        get_sensor=lambda api: _get(api, "water_meter"),
        device_class=SensorDeviceClass.WATER,
        native_unit_of_measurement=UnitOfVolume.CUBIC_METERS,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    YoulessSensorDescription(
        key="extra_total",
        name="Total",
        device_group="extra",
        get_sensor=lambda api: _nested(api, "extra_meter", "total"),
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    YoulessSensorDescription(
        key="extra_usage",
        name="Usage",
        device_group="extra",
        get_sensor=lambda api: _nested(api, "extra_meter", "usage"),
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
]

# Per-phase sensors: only created on devices/firmware that expose phase data.
# Grouped under "power", same as the built-in integration.
for _p in (1, 2, 3):
    SENSORS.extend(
        [
            YoulessSensorDescription(
                key=f"phase{_p}_power",
                name=f"Phase {_p} power",
                device_group="power",
                get_sensor=lambda api, o=f"phase{_p}": _nested(api, o, "power"),
                device_class=SensorDeviceClass.POWER,
                native_unit_of_measurement=UnitOfPower.WATT,
                state_class=SensorStateClass.MEASUREMENT,
            ),
            YoulessSensorDescription(
                key=f"phase{_p}_voltage",
                name=f"Phase {_p} voltage",
                device_group="power",
                get_sensor=lambda api, o=f"phase{_p}": _nested(api, o, "voltage"),
                device_class=SensorDeviceClass.VOLTAGE,
                native_unit_of_measurement=UnitOfElectricPotential.VOLT,
                state_class=SensorStateClass.MEASUREMENT,
            ),
            YoulessSensorDescription(
                key=f"phase{_p}_current",
                name=f"Phase {_p} current",
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
        if description.get_sensor(api) is not None
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
        self._attr_unique_id = f"{base_identifier}_{description.key}"

        # One virtual device per meter type (power/delivery/gas/water/extra),
        # mirroring the built-in `youless` integration's device layout,
        # instead of a single device holding every sensor.
        group = description.device_group
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{base_identifier}_{group}")},
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
