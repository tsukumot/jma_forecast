import logging
from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.const import (
    DEGREE, PERCENTAGE, UnitOfLength, UnitOfPrecipitationDepth,
    UnitOfPressure, UnitOfSpeed, UnitOfTemperature, UnitOfTime,
)
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util
from .const import (
    DOMAIN,
    CONF_AREA,
    CONF_STATION,
    CONF_AMEDAS_MODE,
    AMEDAS_NONE,
)
from .jma import current_value


_LOGGER = logging.getLogger(__name__)


MM = UnitOfPrecipitationDepth.MILLIMETERS
MS = UnitOfSpeed.METERS_PER_SECOND
CM = UnitOfLength.CENTIMETERS
C = UnitOfTemperature.CELSIUS
HPA = UnitOfPressure.HPA
SDC = SensorDeviceClass
# 気象庁JSONのキー: (名前, 単位, device_class)
AMEDAS_SENSORS = {
    "temp": ("気温", C, SDC.TEMPERATURE),
    "humidity": ("湿度", PERCENTAGE, SDC.HUMIDITY),
    "pressure": ("現地気圧", HPA, SDC.ATMOSPHERIC_PRESSURE),
    "normalPressure": ("海面気圧", HPA, SDC.ATMOSPHERIC_PRESSURE),
    "precipitation10m": ("降水量(10分)", MM, SDC.PRECIPITATION),
    "precipitation1h": ("降水量(1時間)", MM, SDC.PRECIPITATION),
    "precipitation3h": ("降水量(3時間)", MM, SDC.PRECIPITATION),
    "precipitation24h": ("降水量(24時間)", MM, SDC.PRECIPITATION),
    "sun10m": ("日照時間(10分)", UnitOfTime.MINUTES, SDC.DURATION),
    "sun1h": ("日照時間(1時間)", UnitOfTime.HOURS, SDC.DURATION),
    "wind": ("風速", MS, SDC.WIND_SPEED),
    "windDirection": ("風向", DEGREE, None),
    "snow": ("積雪", CM, None),
    "snow1h": ("降雪量(1時間)", CM, None),
    "snow6h": ("降雪量(6時間)", CM, None),
    "snow12h": ("降雪量(12時間)", CM, None),
    "snow24h": ("降雪量(24時間)", CM, None),
}


async def async_setup_entry(hass, entry, async_add_entities):
    coord = hass.data[DOMAIN][entry.entry_id]
    c = entry.data
    area, station = c[CONF_AREA], c[CONF_STATION]
    entities = [
        JmaTemp(coord, station, entry),
        JmaWeather(coord, area, entry),
    ]
    if c.get(CONF_AMEDAS_MODE, AMEDAS_NONE) != AMEDAS_NONE:
        got = ((coord.data or {}).get("amedas") or {}).get("values", {})
        entities += [JmaAmedas(coord, entry, key, *spec)
                     for key, spec in AMEDAS_SENSORS.items() if key in got]
    async_add_entities(entities)


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
    _attr_name = "予想気温"
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_device_class = SensorDeviceClass.TEMPERATURE

    def __init__(self, coord, station, entry):
        super().__init__(coord, entry)
        self._attr_unique_id = f"{entry.entry_id}_temp"

    @property
    def native_value(self):
        return self._current("temp")


class JmaWeather(_Base):
    _attr_name = "予報天気"

    def __init__(self, coord, area, entry):
        super().__init__(coord, entry)
        self._attr_unique_id = f"{entry.entry_id}_weather"

    @property
    def native_value(self):
        return self._current("weather")


class JmaAmedas(_Base):
    def __init__(self, coord, entry, key, name, unit, dclass):
        super().__init__(coord, entry)
        self._key = key
        self._attr_name = name
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = dclass
        self._attr_unique_id = f"{entry.entry_id}_amedas_{key}"

    @property
    def _data(self):
        return (self.coordinator.data or {}).get("amedas") or {}

    @property
    def native_value(self):
        return self._data.get("values", {}).get(self._key)

    @property
    def extra_state_attributes(self):
        d = self._data
        return {k: d.get(k) for k in
                ("station_name", "distance_km", "observed_at")}