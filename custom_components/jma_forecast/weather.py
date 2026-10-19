import logging
from datetime import datetime, timedelta
from homeassistant.components.weather import (
    WeatherEntity, WeatherEntityFeature)
from homeassistant.const import UnitOfSpeed, UnitOfTemperature
from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util
from .jma import current_value
from .const import (
    DOMAIN,
    CONF_AREA,
)

_LOGGER = logging.getLogger(__name__)

_BEARING = {"北": 0, "北東": 45, "東": 90, "南東": 135,
            "南": 180, "南西": 225, "西": 270, "北西": 315}


def _condition(text, night):
    if not text:
        return None
    if "雪" in text and "雨" in text:
        return "snowy-rainy"
    if "雷" in text:
        return "lightning"
    if "雪" in text:
        return "snowy"
    if "雨" in text:
        return "rainy"
    if "霧" in text:
        return "fog"
    if "くもり" in text or "曇" in text:
        return "cloudy"
    if "晴" in text:
        return "clear-night" if night else "sunny"
    return None


def _speed(rng):
    try:
        nums = [float(x) for x in (rng or "").split()]
    except ValueError:
        return None
    return sum(nums) / len(nums) if nums else None


async def async_setup_entry(hass, entry, async_add_entities):
    coord = hass.data[DOMAIN][entry.entry_id]
    area = entry.data[CONF_AREA]
    async_add_entities([JmaWeatherEntity(coord, area, entry)])

    async def update():
        return await hass.async_add_executor_job(
            fetch_latest, office, area, station)

    coord = DataUpdateCoordinator(
        hass, _LOGGER, name="jma_forecast_weather", config_entry=entry,
        update_method=update, update_interval=timedelta(minutes=30))
    await coord.async_config_entry_first_refresh()
    async_add_entities([JmaWeatherEntity(coord, area, entry)])


class JmaWeatherEntity(CoordinatorEntity, WeatherEntity):
    _attr_has_entity_name = True
    _attr_name = "天気"
    _attr_attribution = "出典: 気象庁"
    _attr_native_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_native_wind_speed_unit = UnitOfSpeed.METERS_PER_SECOND
    _attr_supported_features = WeatherEntityFeature.FORECAST_HOURLY

    def __init__(self, coord, area, entry):
        super().__init__(coord)
        self._attr_unique_id = f"{entry.entry_id}_forecast"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="気象庁",
            entry_type=DeviceEntryType.SERVICE,
        )

    def _cur(self, key):
        return current_value(self.coordinator.data, key, dt_util.now())

    @property
    def condition(self):
        night = self.hass.states.is_state("sun.sun", "below_horizon")
        return _condition(self._cur("weather"), night)

    @property
    def native_temperature(self):
        return self._cur("temp")

    @property
    def native_wind_speed(self):
        return _speed(self._cur("wind_speed_ms"))

    @property
    def wind_bearing(self):
        return _BEARING.get(self._cur("wind_dir"))

    async def async_forecast_hourly(self):
        now = dt_util.now()
        out = []
        for t, v in (self.coordinator.data or {}).items():
            dt = datetime.fromisoformat(t)
            if dt < now - timedelta(hours=3):
                continue
            night = dt.hour < 6 or dt.hour >= 18
            out.append({
                "datetime": t,
                "condition": _condition(v.get("weather"), night),
                "native_temperature": v.get("temp"),
                "native_wind_speed": _speed(v.get("wind_speed_ms")),
                "wind_bearing": _BEARING.get(v.get("wind_dir")),
            })
        return out

    @callback
    def _handle_coordinator_update(self):
        super()._handle_coordinator_update()
        self.hass.async_create_task(self.async_update_listeners(("hourly",)))