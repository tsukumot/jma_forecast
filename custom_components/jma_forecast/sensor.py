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
from .jma import current_value, is_ja


_LOGGER = logging.getLogger(__name__)


MM = UnitOfPrecipitationDepth.MILLIMETERS
MS = UnitOfSpeed.METERS_PER_SECOND
CM = UnitOfLength.CENTIMETERS
C = UnitOfTemperature.CELSIUS
HPA = UnitOfPressure.HPA
SDC = SensorDeviceClass
# 気象庁JSONのキー: (単位, device_class)  ※名前は translations の entity で定義
AMEDAS_SENSORS = {
    "temp": (C, SDC.TEMPERATURE),
    "humidity": (PERCENTAGE, SDC.HUMIDITY),
    "pressure": (HPA, SDC.ATMOSPHERIC_PRESSURE),
    "normalPressure": (HPA, SDC.ATMOSPHERIC_PRESSURE),
    "precipitation10m": (MM, SDC.PRECIPITATION),
    "precipitation1h": (MM, SDC.PRECIPITATION),
    "precipitation3h": (MM, SDC.PRECIPITATION),
    "precipitation24h": (MM, SDC.PRECIPITATION),
    "sun10m": (UnitOfTime.MINUTES, SDC.DURATION),
    "sun1h": (UnitOfTime.HOURS, SDC.DURATION),
    "wind": (MS, SDC.WIND_SPEED),
    "windDirection": (DEGREE, None),
    "snow": (CM, None),
    "snow1h": (CM, None),
    "snow6h": (CM, None),
    "snow12h": (CM, None),
    "snow24h": (CM, None),
}


async def async_setup_entry(hass, entry, async_add_entities):
    coord = hass.data[DOMAIN][entry.entry_id]
    c = entry.data
    area, station = c[CONF_AREA], c[CONF_STATION]
    entities = [
        JmaTemp(coord, station, entry),
        JmaWeather(coord, area, entry),
        JmaOverview(coord, entry),
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
            name="JMA 予報" if is_ja(coord.hass) else "JMA Forecast",
            manufacturer="気象庁",
            entry_type=DeviceEntryType.SERVICE,
        )

    def _current(self, key):
        hourly = (self.coordinator.data or {}).get("hourly")
        return current_value(hourly, key, dt_util.now())

class JmaTemp(_Base):
    _attr_translation_key = "forecast_temp"
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_device_class = SensorDeviceClass.TEMPERATURE

    def __init__(self, coord, station, entry):
        super().__init__(coord, entry)
        self._attr_unique_id = f"{entry.entry_id}_temp"

    @property
    def native_value(self):
        return self._current("temp")


class JmaWeather(_Base):
    _attr_translation_key = "forecast_weather"

    def __init__(self, coord, area, entry):
        super().__init__(coord, entry)
        self._attr_unique_id = f"{entry.entry_id}_weather"

    @property
    def native_value(self):
        return self._current("weather")


class JmaAmedas(_Base):
    def __init__(self, coord, entry, key, unit, dclass):
        super().__init__(coord, entry)
        self._key = key
        self._attr_translation_key = f"amedas_{key.lower()}"
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


class JmaOverview(_Base):
    _attr_translation_key = "overview"
    # 行数が日によって変わり、長文にもなるので履歴(recorder)には残さない
    _unrecorded_attributes = frozenset({"details"})

    def __init__(self, coord, entry):
        super().__init__(coord, entry)
        self._attr_unique_id = f"{entry.entry_id}_overview"

    @property
    def _data(self):
        return (self.coordinator.data or {}).get("overview") or {}

    @property
    def _lines(self):
        # 空行を除いて1行ずつのリストにする
        text = self._data.get("text") or ""
        return [s.strip() for s in text.splitlines() if s.strip()]

    @property
    def native_value(self):
        lines = self._lines
        # stateは255文字まで。1行目が長い場合に備えて切る
        return lines[0][:255] if lines else None

    @property
    def extra_state_attributes(self):
        d = self._data
        return {
            "details": self._lines[1:],   # 2行目以降のリスト
            "headline": d.get("headline"),
            "report_datetime": d.get("report_datetime"),
            "publishing_office": d.get("publishing_office"),
            "target_area": d.get("target_area"),
        }