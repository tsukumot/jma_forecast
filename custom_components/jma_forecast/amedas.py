import json
import math
import urllib.request
from datetime import datetime

from .const import (
    AMEDAS_TABLE_URL, AMEDAS_LATEST_URL, AMEDAS_MAP_URL, AMEDAS_STATION,
)

_table = None


def _json(url):
    with urllib.request.urlopen(url, timeout=30) as r:
        return json.load(r)


def get_table():
    global _table
    if _table is None:
        _table = _json(AMEDAS_TABLE_URL)
    return _table


def _deg(v):
    return v[0] + v[1] / 60


def _dist_km(lat1, lon1, lat2, lon2):
    dx = (lon2 - lon1) * math.cos(math.radians(lat1))
    return math.hypot(dx, lat2 - lat1) * 111


def _val(obs, key):
    v = obs.get(key)
    return v[0] if v else None


def _bearing(i):
    """風向の番号(1〜16)を角度にする。0(静穏)はNone"""
    if i is None or i == 0:
        return None
    return (i * 22.5) % 360


def fetch_amedas(mode, station_id, lat, lon):
    table = get_table()
    with urllib.request.urlopen(AMEDAS_LATEST_URL, timeout=30) as r:
        t = datetime.fromisoformat(r.read().decode().strip())
    obs = _json(AMEDAS_MAP_URL.format(ts=t.strftime("%Y%m%d%H%M%S")))

    def dist(code):
        s = table[code]
        return _dist_km(lat, lon, _deg(s["lat"]), _deg(s["lon"]))

    if mode == AMEDAS_STATION:
        code = station_id
        if code not in table or code not in obs:
            return {}
    else:  # 自宅の近く: 気温が取れている観測所のうち最寄り
        cands = [c for c in table
                 if c in obs and _val(obs[c], "temp") is not None]
        if not cands:
            return {}
        code = min(cands, key=dist)

    o = obs[code]
    # 観測所が公表している項目をすべて集める(値は [値, 品質] の先頭)
    values = {k: v[0] for k, v in o.items()
              if isinstance(v, list) and v}
    for k in ("windDirection", "gustDirection"):
        if k in values:
            values[k] = _bearing(values[k])
    return {
        "station_name": table[code]["kjName"],
        "station_id": code,
        "distance_km": round(dist(code), 1),
        "observed_at": t.isoformat(),
        "values": values,
    }