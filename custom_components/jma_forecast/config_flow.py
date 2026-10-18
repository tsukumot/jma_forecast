import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers.selector import (
    SelectSelector,
    SelectSelectorConfig,
    SelectOptionDict
)

from .const import (
    DOMAIN,
    CONF_CENTER,
    CONF_OFFICE,
    CONF_AREA,
    CONF_STATION,
)
from .jma import fetch_offices, list_choices


def _select(options):
    return SelectSelector(SelectSelectorConfig(
        options=[SelectOptionDict(value=v, label=l) for v, l in options]))


class JmaConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self):
        self._centers = None
        self._offices = None
        self._center = None
        self._office = None
        self._stations = {}

    async def _load(self):
        if self._centers is None:
            self._centers, self._offices = await self.hass.async_add_executor_job(
                fetch_offices)

    async def async_step_user(self, user_input=None):
        """1. 地方を選ぶ"""
        await self._load()
        if user_input is not None:
            self._center = user_input[CONF_CENTER]
            return await self.async_step_office()

        options = [(code, c["name"]) for code, c in self._centers.items()]
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required(CONF_CENTER): _select(options)}))

    async def async_step_office(self, user_input=None):
        """2. その地方の府県予報区を選ぶ"""
        if user_input is not None:
            self._office = user_input[CONF_OFFICE]
            return await self.async_step_point()

        options = [(code, self._offices[code]["name"])
                   for code in self._centers[self._center]["children"]
                   if code in self._offices]
        return self.async_show_form(
            step_id="office",
            data_schema=vol.Schema({vol.Required(CONF_OFFICE): _select(options)}))

    async def async_step_point(self, user_input=None):
        if user_input is not None:
            uid = f"{self._office}_{user_input[CONF_AREA]}_{user_input[CONF_STATION]}"
            await self.async_set_unique_id(uid)
            self._abort_if_unique_id_configured()

            title = self._offices[self._office]["name"]
            if title in {e.title for e in self._async_current_entries()}:
                title = f"{title} {self._stations[user_input[CONF_STATION]]}"
            return self.async_create_entry(
                title=title,
                data={CONF_CENTER: self._center, CONF_OFFICE: self._office,
                      **user_input})

        res = await self.hass.async_add_executor_job(list_choices, self._office)
        if not res or not res[0] or not res[1]:
            return self.async_abort(reason="no_data")
        areas, stations = res
        self._stations = stations
        return self.async_show_form(
            step_id="point",
            data_schema=vol.Schema({
                vol.Required(CONF_AREA): _select(areas.items()),
                vol.Required(CONF_STATION): _select(stations.items()),
            }))