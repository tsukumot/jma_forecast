"""アメダス観測所表から、地点(気温)の選択肢の翻訳を作って translations/*.json に入れる。

どこで実行してもよい。translations フォルダは自動で探す。
見つからないとき、または別の場所を使うときは、フォルダを引数で渡す:
    python gen_station_translations.py
    python gen_station_translations.py /path/to/translations

ネットワークが必要(気象庁の観測所表を1回取得する)。何度実行しても同じ結果になる。
"""
import json
import sys
import urllib.request
from pathlib import Path

TABLE_URL = "https://www.jma.go.jp/bosai/amedas/const/amedastable.json"
HERE = Path(__file__).resolve().parent
# translations フォルダの候補(上から順に探す)
CANDIDATES = [
    HERE.parent / "custom_components" / "jma_forecast" / "translations",
    HERE.parent / "translations",
    Path.cwd() / "custom_components" / "jma_forecast" / "translations",
    Path.cwd() / "translations",
]
KEY = "jma_station"


def build(table):
    """観測所表 -> {"ja": {コード: 日本語名}, "en": {コード: 英語名}}"""
    ja, en = {}, {}
    for code, s in table.items():
        if s.get("kjName") and s.get("enName"):
            ja[code] = s["kjName"]
            en[code] = s["enName"]
    return {"ja": ja, "en": en}


def merge(path, options):
    data = json.loads(path.read_text(encoding="utf-8"))
    data.setdefault("selector", {})[KEY] = {"options": options}
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
                 "引数で渡してください: python gen_station_translations.py <フォルダ>")
    for lang in ("ja", "en"):
        if not (directory / f"{lang}.json").exists():
            sys.exit(f"{directory / (lang + '.json')} がありません。先にファイルを置いてください。")
    print("対象:", directory)
    with urllib.request.urlopen(TABLE_URL, timeout=30) as r:
        names = build(json.load(r))
    for lang, options in names.items():
        merge(directory / f"{lang}.json", options)
        print(f"{lang}.json: {len(options)} 件")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
