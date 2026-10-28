import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN, CONF_OFFICE, CONF_AREA, CONF_STATION
from .jma import fetch_latest, fetch_daily

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor", "weather"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    c = entry.data
    office, area, station = c[CONF_OFFICE], c[CONF_AREA], c[CONF_STATION]

    async def update():
        hourly = await hass.async_add_executor_job(
            fetch_latest, office, area, station)
        daily = await hass.async_add_executor_job(
            fetch_daily, office, area, station)
        return {"hourly": hourly, "daily": daily}

    coord = DataUpdateCoordinator(
        hass, _LOGGER, name=f"jma_forecast_{office}_{area}_{station}",
        config_entry=entry, update_method=update,
        update_interval=timedelta(minutes=10))
    await coord.async_config_entry_first_refresh()

    # 登録ごと(entry_id)に1つだけ作り、sensor / weather で共有する
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coord

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return ok

