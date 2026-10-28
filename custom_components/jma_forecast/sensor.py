import logging
from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.const import UnitOfTemperature
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util
from .jma import current_value
from .const import (
    DOMAIN,
    CONF_AREA,
    CONF_STATION,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    coord = hass.data[DOMAIN][entry.entry_id]
    c = entry.data
    area, station = c[CONF_AREA], c[CONF_STATION]
    async_add_entities([
        JmaTemp(coord, station, entry),
        JmaWeather(coord, area, entry),
    ])


class _Base(CoordinatorEntity, SensorEntity):
    _attr_has_entity_name = True

    def __init__(self, coord, entry):
        super().__init__(coord)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="JMA 予報",
            manufacturer="気象庁",
            entry_type=DeviceEntryType.SERVICE,
        )

    def _current(self, key):
        hourly = (self.coordinator.data or {}).get("hourly")
        return current_value(hourly, key, dt_util.now())

class JmaTemp(_Base):
    _attr_name = "気温予報"
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_device_class = SensorDeviceClass.TEMPERATURE

    def __init__(self, coord, station, entry):
        super().__init__(coord, entry)
        self._attr_unique_id = f"{entry.entry_id}_temp"  # ← ここだけ変更

    @property
    def native_value(self):
        return self._current("temp")


class JmaWeather(_Base):
    _attr_name = "天気予報"

    def __init__(self, coord, area, entry):
        super().__init__(coord, entry)
        self._attr_unique_id = f"{entry.entry_id}_weather"  # ← ここだけ変更

    @property
    def native_value(self):
        return self._current("weather")