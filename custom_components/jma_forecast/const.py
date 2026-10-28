DOMAIN = "jma_forecast"
FEED = "https://www.data.jma.go.jp/developer/xml/feed/regular_l.xml"
AREA_JSON = "area.json"
PRODUCT = "VPFD51_"   # 府県天気予報(Ｒ１)
# Ｒ１電文の項目名
TYPE_WEATHER = "３時間内卓越天気"
TYPE_WIND = "３時間内代表風"
TYPE_TEMP = "３時間毎気温"

#coniguration
CONF_CENTER = "center"
CONF_OFFICE = "office"
CONF_AREA = "area"
CONF_STATION = "station"

DAILY_URL = "https://www.jma.go.jp/bosai/forecast/data/forecast/{office}.json"
