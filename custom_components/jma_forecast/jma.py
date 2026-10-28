import json
import logging
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from .const import (
    FEED,
    PRODUCT,
    AREA_JSON,
    DAILY_URL,
    TYPE_WEATHER,
    TYPE_WIND,
    TYPE_TEMP,
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


#週間予報
_daily_cache = {}


def _pick(areas, code, fallback=True):
    """codeが一致する区域を返す。なければ先頭(fallback=Falseならなし)。"""
    for a in areas:
        if a["area"]["code"] == code:
            return a
    return areas[0] if (fallback and areas) else None


def _num(values, i):
    """配列のi番目を数値にする。空文字・範囲外はNone。"""
    try:
        return float(values[i])
    except (IndexError, ValueError, TypeError):
        return None


def _weekly_days(j, office, station):
    """週間予報(j[1])から、日付ごとの値を作る。"""
    series = j[1]["timeSeries"]
    w = _pick(series[0]["areas"], office)
    t = _pick(series[1]["areas"], station)
    days = {}
    for i, d in enumerate(series[0]["timeDefines"]):
        days[d[:10]] = {
            "weather_code": w["weatherCodes"][i] if w else None,
            "pop": _num(w["pops"], i) if w else None,
            "temp_max": _num(t["tempsMax"], i) if t else None,
            "temp_min": _num(t["tempsMin"], i) if t else None,
        }
    return days


def _short_days(j, area, station):
    """3日分の予報(j[0])から、日付ごとの値を作る。見つかった項目だけ入れる。"""
    series = j[0]["timeSeries"]
    days = {}

    # 天気コード(一次細分区域ごと)
    w = _pick(series[0]["areas"], area, fallback=False)
    if w:
        for i, d in enumerate(series[0]["timeDefines"]):
            days.setdefault(d[:10], {})["weather_code"] = w["weatherCodes"][i]

    # 降水確率(6時間ごと) → その日の最大値
    p = _pick(series[1]["areas"], area, fallback=False)
    if p:
        pops = {}
        for d, v in zip(series[1]["timeDefines"], p["pops"]):
            if v != "":
                pops.setdefault(d[:10], []).append(float(v))
        for day, vals in pops.items():
            days.setdefault(day, {})["pop"] = max(vals)

    # 気温(地点ごと): 時刻や並び順は信用せず、日付ごとに集めて大小で判断する
    t = _pick(series[2]["areas"], station)
    if t:
        temps = {}
        for d, v in zip(series[2]["timeDefines"], t["temps"]):
            if v != "":
                temps.setdefault(d[:10], []).append(float(v))
        for day, vals in temps.items():
            if len(vals) >= 2:
                entry = days.setdefault(day, {})
                entry["temp_min"] = min(vals)
                entry["temp_max"] = max(vals)
    return days


def _parse_daily(j, office, area, station):
    days = _weekly_days(j, office, station)
    # 3日分の予報で見つかった項目は、週間予報の値を上書きする
    for day, vals in _short_days(j, area, station).items():
        days.setdefault(day, {}).update(vals)
    return [{
        "datetime": f"{day}T00:00:00+09:00",
        "weather_code": v.get("weather_code"),
        "pop": v.get("pop"),
        "temp_max": v.get("temp_max"),
        "temp_min": v.get("temp_min"),
    } for day, v in sorted(days.items())]


def fetch_daily(office, area, station):
    key = (office, area, station)
    url = DAILY_URL.format(office=office)
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            j = json.load(r)
        days = _parse_daily(j, office, area, station)
        if days:
            _daily_cache[key] = days
    except Exception as err:  # 失敗しても3時間予報は止めない
        _LOGGER.warning("jma daily fetch failed: %s", err)
    return _daily_cache.get(key, [])