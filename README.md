日本語READMEは[→こちら](README.ja.md)

# JMA Forecast for Home Assistant

A custom integration that automatically retrieves weather forecasts published by the Japan Meteorological Agency (JMA) and makes weather conditions, temperature, and wind forecasts available in Home Assistant.

For 3-hourly forecasts, this integration uses the JMA *Prefectural Weather Forecast (R1) bulletin*.

- Retrieves 3-hourly forecasts: weather conditions, temperature, wind direction, wind speed, and probability of precipitation.
- Retrieves daily forecasts: weather conditions, minimum and maximum temperatures, and probability of precipitation.
- Creates two history sensors (forecast temperature and forecast weather) and a weather entity (`weather`).
- Creates a sensor for the weather synopsis (Prefectural Weather Overview).
- - *Note:* The weather synopsis is provided in Japanese only. It is not translated into English.
- Optionally creates sensors for real-time AMeDAS observations published by JMA.
- All entities for a location are grouped under a single device named "JMA Forecast".
- Supports registering multiple forecast locations.
- No YAML configuration is required.
- Uses cached data instead of re-parsing bulletins when an updated bulletin contains no changes.

Data source: [![JMA](banner_jma.gif)](https://www.jma.go.jp)

## Installation

### HACS (Custom Repository)

1. Open HACS → menu in the upper-right corner → **Custom repositories**.
2. Add `https://github.com/tsukumot/jma_forecast` and select **Integration** as the category.
3. Download "JMA Forecast" and restart Home Assistant.

## Configuration

1. Go to **Settings → Devices & Services → Add Integration** and select "JMA Forecast".
2. Select a **Region** (e.g. Kanto-Koshin).
3. Select a **Prefectural Forecast Area** (e.g. Tokyo).
4. Select a **Primary Subdivision (Weather)** and a **Location (Temperature)**.
5. Select how to retrieve AMeDAS observations:
   - **Nearest station to home (automatic):** Selects the nearest observation station that provides temperature data, based on the home latitude and longitude configured in Home Assistant.
   - **Specify station ID:** Enter an observation station ID (e.g. `44132` = Tokyo).
   - **Disabled:** No AMeDAS sensors will be created.

Multiple forecast locations can be registered.

If the same Prefectural Forecast Area is registered more than once, the location name is appended to the titles of the second and subsequent entries.

> Adding `platform: jma_forecast` to `configuration.yaml` is not required.

### If you see "Forecast bulletin for this Prefectural Forecast Area has not been published yet"

This most likely indicates an invalid selection.

Please let me know if this occurs so I can investigate and address the issue.

## Created Entities

| Entity | Type | Description | Update Interval |
| --- | --- | --- | --- |
| Weather Overview | `sensor` | First line of the weather synopsis (provided in Japanese only; remaining lines are stored in attributes) | 10 minutes |
| Forecast Temperature | `sensor` (temperature) | Temperature (°C) for the forecast time slot corresponding to the current time | 10 minutes |
| Forecast Weather | `sensor` | Original JMA weather description for the forecast time slot corresponding to the current time (e.g. sunny, cloudy) | 10 minutes |
| Forecast | `weather` | Weather conditions, temperature, probability of precipitation, wind direction, wind speed, daily forecast, and 3-hourly forecast data (`forecast_hourly`) | 10 minutes |

For the weather entity, JMA weather descriptions are mapped to Home Assistant `condition` values as follows:

| Keywords in the original description | `condition` |
| --- | --- |
| Snow and rain | `snowy-rainy` |
| Thunder | `lightning` |
| Snow | `snowy` |
| Rain | `rainy` |
| Fog | `fog` |
| Cloudy | `cloudy` |
| Clear (after sunset) | `clear-night` |
| Clear (during daytime) | `sunny` |

Conditions are evaluated in the order shown above. For example, a description meaning "rain with thunderstorms" is mapped to `lightning`.

### Weather Entity Attributes

The weather entity provides the following attributes:

| Attribute | Description |
| --- | --- |
| `weather_text` | Original JMA weather description for the forecast time slot corresponding to the current time |
| `forecast_3h` | List of 3-hourly forecasts (including slots from 3 hours before the current time onward) |

Each entry in `forecast_3h` contains the following fields:

| Field | Description |
| --- | --- |
| `datetime` | Forecast time (ISO 8601) |
| `weather` | Original weather description (e.g. cloudy, rain) |
| `temperature` | Temperature (°C) |
| `temperature_min` | Minimum temperature (°C) |
| `temperature_max` | Maximum temperature (°C) |
| `precipitation_probability` | Probability of precipitation (%) |
| `wind_direction` | Wind direction (e.g. west, northwest) |
| `wind_speed_min` | Minimum wind speed (m/s) |
| `wind_speed_max` | Maximum wind speed (m/s) |
| `wind_speed_average` | Average wind speed (m/s) |

Wind speed ranges from the original bulletin are preserved as minimum and maximum values.

Because `forecast_3h` contains a relatively large amount of data, it is excluded from the recorder history.

### Weather Overview Sensor Attributes

Since the weather synopsis can be quite long, only its first line is stored as the sensor state. The remaining lines are stored in the `details` attribute as an array of individual lines.

| Attribute | Description |
| --- | --- |
| `details` | Lines following the first line of the synopsis (an array with one element per line; empty lines are omitted) |
| `headline` | Headline (empty if unavailable) |
| `report_datetime` | Publication time (ISO 8601) |
| `publishing_office` | Publishing JMA office |
| `target_area` | Target area |

Because `details` contains a relatively large amount of data, it is excluded from the recorder history.

### AMeDAS Observation Sensors

When any option other than "Disabled" is selected for AMeDAS observations, sensors are created for each parameter reported by the selected observation station. These sensors are updated every 10 minutes.

| Sensor | Unit |
| --- | --- |
| Temperature | °C |
| Humidity | % |
| Station pressure / Sea-level pressure | hPa |
| Precipitation (10-minute, 1-hour, 3-hour, and 24-hour) | mm |
| Sunshine duration (10-minute and 1-hour) | minutes / hours |
| Wind speed | m/s |
| Wind direction | degrees (no value when calm) |
| Snow depth | cm |
| Snowfall (1-hour, 6-hour, 12-hour, and 24-hour) | cm |

Each sensor also provides the following attributes:

- `station_name`: Observation station name
- `distance_km`: Distance from home
- `observed_at`: Observation timestamp

## Limitations and Notes

- Short-range forecasts are provided at 3-hour intervals. `forecast_hourly` contains the original 3-hourly forecast slots from 3 hours before the current time onward. No hourly interpolation is performed.
- Probability of precipitation is forecast at 6-hour intervals. Therefore, the same value is displayed twice in the 3-hourly forecast.
- Weekly forecasts use the selected forecast area for up to day 3 (maximum). From day 4 onward, forecasts are provided at the prefecture level.
- The predicted minimum and maximum temperatures for the current day are determined differently depending on the time of day:
  - **Minimum temperature:** From 9:00 AM onward, the minimum is calculated from the current day's 3-hourly forecast. This is primarily intended to reflect temperature drops expected in the evening and later.
  - **Maximum temperature:** Since this value is no longer provided in the forecast during the evening and later, it is calculated from the current day's 3-hourly forecast.
- Wind speed is represented by the average of the minimum and maximum values of the wind speed range specified in the bulletin, in m/s. The original minimum and maximum values are available as attributes.
- Sunset detection uses `sun.sun` for the current state of the weather entity. For `forecast_hourly`, a simplified time-based rule is used: 6:00 PM to 6:00 AM.
- AMeDAS sensors are created only for parameters reported by the selected station at the time of registration (e.g. snow-related sensors are available only at stations in snowy regions). If additional parameters become available later, they will not be retrieved or reflected until the integration is reloaded.
- If retrieving AMeDAS observations fails, the most recently retrieved values continue to be displayed.
- The nearest station to home is selected based on straight-line distance among stations that provide temperature observations.
- The publication intervals and contents of bulletins and other data depend on JMA's operational schedule.

## License and Data Sources

- Forecasts and AMeDAS observation data are provided by the Japan Meteorological Agency (JMA). Use of these data is subject to the [JMA Website Terms of Use](https://www.jma.go.jp/jma/kishou/info/coment.html).
- This integration is an unofficial project and is not affiliated with or endorsed by JMA.