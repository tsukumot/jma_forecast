import json
import logging
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from .const import (
    FEED,
    PRODUCT,
    AREA_JSON,
    TYPE_WEATHER,
    TYPE_WIND,
    TYPE_TEMP
)

_LOGGER = logging.getLogger(__name__)
_AREA_FILE = Path(__file__).parent / AREA_JSON

NS = {"a": "http://www.w3.org/2005/Atom"}
_cache = {}


def _open(url):
    with urllib.request.urlopen(url, timeout=30) as r:
        return ET.parse(r).getroot()


def _latest_url(office):
    for e in _open(FEED).findall("a:entry", NS):
        href = e.find("a:link", NS).attrib["href"]
        if PRODUCT + office in href:
            return href
    return None


def _parse(url, area, station):
    root = _open(url)
    slots = {}
    for ts in root.findall(".//{*}TimeSeriesInfo"):
        times = {td.get("timeId"): td.find("{*}DateTime").text
                 for td in ts.find("{*}TimeDefines")}
        for item in ts.findall("{*}Item"):
            code = item.find("{*}Area/{*}Code")
            if code is None:
                code = item.find("{*}Station/{*}Code")
            if code is None or code.text not in (area, station):
                continue
            for prop in item.findall(".//{*}Property"):
                t = prop.find("{*}Type").text
                if t == TYPE_WEATHER:
                    for e in prop.findall(".//{*}Weather"):
                        slots.setdefault(times[e.get("refID")], {})["weather"] = e.text
                elif t == TYPE_WIND:
                    for e in prop.findall(".//{*}WindDirection"):
                        slots.setdefault(times[e.get("refID")], {})["wind_dir"] = e.text
                    for e in prop.findall(".//{*}WindSpeedLevel"):
                        slots.setdefault(times[e.get("refID")], {})["wind_speed_ms"] = e.get("range")
                elif t == TYPE_TEMP:
                    for e in prop.findall(".//{*}Temperature"):
                        slots.setdefault(times[e.get("refID")], {})["temp"] = float(e.text)
    # 天気と気温が両方そろっている枠だけ残す
    return {t: v for t, v in sorted(slots.items())
            if "weather" in v and "temp" in v}

def fetch_latest(office, area, station):
    key = (office, area, station)
    entry = _cache.setdefault(key, {"url": None, "data": {}})

    url = _latest_url(office)
    _LOGGER.debug("jma url=%s", url)
    if url and url != entry["url"]:
        data = _parse(url, area, station)
        if data:  # 空のときは保存せず、次回また試す
            entry["data"] = data
            entry["url"] = url
    return entry["data"]


from datetime import datetime


def current_value(data, key, now):
    value = None
    for t, v in (data or {}).items():
        if key not in v:
            continue
        if value is None:
            value = v[key]
        if datetime.fromisoformat(t) <= now:
            value = v[key]
    return value

def fetch_offices():
    with open(_AREA_FILE, encoding="utf-8") as r:
        j = json.load(r)
    return j["centers"], j["offices"]


def list_choices(office):
    """最新のR1電文から (area, station) の候補を取る"""
    url = _latest_url(office)
    if not url:
        return None
    root = _open(url)
    areas, stations = {}, {}
    for item in root.findall(".//{*}TimeSeriesInfo/{*}Item"):
        for tag, dest in (("Area", areas), ("Station", stations)):
            el = item.find(f"{{*}}{tag}")
            if el is not None:
                dest[el.find("{*}Code").text] = el.find("{*}Name").text
    return areas, stations