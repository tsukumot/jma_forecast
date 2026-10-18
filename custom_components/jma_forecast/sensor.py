import logging
from datetime import timedelta

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.const import UnitOfTemperature
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity, DataUpdateCoordinator,
)
from homeassistant.util import dt as dt_util

from .jma import fetch_latest, current_value
from .const import (
    DOMAIN,
    CONF_OFFICE,
    CONF_AREA,
    CONF_STATION,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    c = entry.data
    office, area, station = c[CONF_OFFICE], c[CONF_AREA], c[CONF_STATION]

    async def update():
        return await hass.async_add_executor_job(
            fetch_latest, office, area, station)

    coord = DataUpdateCoordinator(
        hass, _LOGGER, name="jma_forecast", config_entry=entry,
        update_method=update, update_interval=timedelta(minutes=10))
    await coord.async_config_entry_first_refresh()
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
        return current_value(self.coordinator.data, key, dt_util.now())


class JmaTemp(_Base):
    _attr_name = "気温予報"
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_device_class = SensorDeviceClass.TEMPERATURE

    def __init__(self, coord, station, entry):
        super().__init__(coord, entry)
        self._attr_unique_id = f"jma_temp_{station}"

    @property
    def native_value(self):
        return self._current("temp")


class JmaWeather(_Base):
    _attr_name = "天気予報"

    def __init__(self, coord, area, entry):
        super().__init__(coord, entry)
        self._attr_unique_id = f"jma_weather_{area}"

    @property
    def native_value(self):
        return self._current("weather")