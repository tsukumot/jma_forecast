import json
import urllib.request

from .const import OVERVIEW_URL


def fetch_overview(office):
    with urllib.request.urlopen(
            OVERVIEW_URL.format(office=office), timeout=30) as r:
        d = json.load(r)
    return {
        "report_datetime": d.get("reportDatetime"),
        "publishing_office": d.get("publishingOffice"),
        "target_area": d.get("targetArea"),
        "headline": d.get("headlineText") or "",
        "text": d.get("text") or "",
    }