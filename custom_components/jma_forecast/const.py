DOMAIN = "jma_forecast"
FEED = "https://www.data.jma.go.jp/developer/xml/feed/regular_l.xml"
AREA_JSON = "area.json"
PRODUCT = "VPFD51_"   # 府県天気予報(Ｒ１)

#coniguration
CONF_CENTER = "center"
CONF_OFFICE = "office"
CONF_AREA = "area"
CONF_STATION = "station"
CONF_AMEDAS_MODE = "amedas_mode"
CONF_AMEDAS_ID = "amedas_id"
AMEDAS_HOME = "home"
AMEDAS_STATION = "station"
AMEDAS_NONE = "none"

# Ｒ１電文の項目名
TYPE_WEATHER = "３時間内卓越天気"
TYPE_WIND = "３時間内代表風"
TYPE_TEMP = "３時間毎気温"

DAILY_URL = "https://www.jma.go.jp/bosai/forecast/data/forecast/{office}.json"
AMEDAS_TABLE_URL = "https://www.jma.go.jp/bosai/amedas/const/amedastable.json"
AMEDAS_LATEST_URL = "https://www.jma.go.jp/bosai/amedas/data/latest_time.txt"
AMEDAS_MAP_URL = "https://www.jma.go.jp/bosai/amedas/data/map/{ts}.json"

