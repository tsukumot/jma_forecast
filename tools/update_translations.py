"""気象庁の最新データから、area.json と選択肢の翻訳(地方・府県予報区・区域・地点)を更新する。

どこで実行してもよい。translations フォルダは自動で探す。
見つからないとき、または別の場所を使うときは、フォルダを引数で渡す:
    python update_translations.py
    python update_translations.py /path/to/translations

ネットワークが必要(気象庁から area.json と観測所表を取得する)。
area.json は translations フォルダの1つ上に書き出す。変更点は git diff で確認できる。
"""
import json
import sys
import urllib.request
from pathlib import Path

AREA_URL = "https://www.jma.go.jp/bosai/common/const/area.json"
TABLE_URL = "https://www.jma.go.jp/bosai/amedas/const/amedastable.json"
HERE = Path(__file__).resolve().parent
# translations フォルダの候補(上から順に探す)
CANDIDATES = [
    HERE.parent / "custom_components" / "jma_forecast" / "translations",
    HERE.parent / "translations",
    Path.cwd() / "custom_components" / "jma_forecast" / "translations",
    Path.cwd() / "translations",
]
# area.json の区分 -> 翻訳のキー
AREA_KEYS = {"centers": "jma_center", "offices": "jma_office", "class10s": "jma_area"}


def _get(url):
    with urllib.request.urlopen(url, timeout=30) as r:
        return json.load(r)


def clean_area(area):
    """centers の children から、末尾が00でないコードを取り除く(area を直接書き換える)。
    取り除いたコードの一覧を返す。"""
    removed = []
    for code, center in area["centers"].items():
        keep = [c for c in center["children"] if c.endswith("00")]
        removed += [(code, c) for c in center["children"] if c not in keep]
        center["children"] = keep
    return removed


def build_area(area):
    """area.json -> {"ja": {翻訳キー: {コード: 名前}}, "en": {...}}"""
    out = {"ja": {}, "en": {}}
    for section, key in AREA_KEYS.items():
        out["ja"][key] = {c: v["name"] for c, v in area[section].items()}
        out["en"][key] = {c: v.get("enName") or v["name"]
                          for c, v in area[section].items()}
    return out


def build_stations(table):
    """観測所表 -> {"ja": {翻訳キー: {コード: 名前}}, "en": {...}}"""
    ja, en = {}, {}
    for code, s in table.items():
        if s.get("kjName") and s.get("enName"):
            ja[code] = s["kjName"]
            en[code] = s["enName"]
    return {"ja": {"jma_station": ja}, "en": {"jma_station": en}}


def merge(path, selectors):
    data = json.loads(path.read_text(encoding="utf-8"))
    for key, options in selectors.items():
        data.setdefault("selector", {})[key] = {"options": options}
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def find_dir(arg):
    if arg:
        return Path(arg)
    for d in CANDIDATES:
        if (d / "ja.json").exists() and (d / "en.json").exists():
            return d
    return None


def main(arg=None):
    directory = find_dir(arg)
    if directory is None:
        sys.exit("translations フォルダ(ja.json と en.json があるところ)が見つかりません。\n"
                 "引数で渡してください: python update_translations.py <フォルダ>")
    for lang in ("ja", "en"):
        if not (directory / f"{lang}.json").exists():
            sys.exit(f"{directory / (lang + '.json')} がありません。先にファイルを置いてください。")
    print("対象:", directory)

    area = _get(AREA_URL)
    # 形式が変わっていたら、何も書き換えずに止める
    for section in AREA_KEYS:
        if not area.get(section):
            sys.exit(f"area.json に {section} がありません。形式が変わった可能性があります。")
    removed = clean_area(area)
    for center, code in removed:
        print(f"取り除いた: {center} の children {code}")
    names_area = build_area(area)
    names_station = build_stations(_get(TABLE_URL))

    area_path = directory.parent / "area.json"
    area_path.write_text(
        json.dumps(area, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"area.json を更新: {area_path}")

    for lang in ("ja", "en"):
        selectors = {**names_area[lang], **names_station[lang]}
        merge(directory / f"{lang}.json", selectors)
        print(f"{lang}.json: " + ", ".join(
            f"{k} {len(v)}件" for k, v in selectors.items()))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
