#!/usr/bin/env python3
"""
Fleet Builderの艦娘ステータスをゲーム本体のマスターデータと照合する。

照合元: kcwiki/kancolle-data の api_start2.json（艦これのapi_start2、つまりゲームが
配信しているマスターデータそのもの）。攻略サイトから拾った数値は「初期値」と
「近代化改修の上限値」を取り違えやすく、実際に運の値を8隻ぶん間違えて公開した
ことがあるため、このスクリプトで機械的に検証する。

照合できるのはマスターデータに存在する項目のみ:
  耐久(初期) / 火力(最大) / 雷装(最大) / 対空(最大) / 装甲(最大) / 運(初期) / スロット数
対潜・索敵はレベル成長で決まりマスターデータに無いので、ここでは検証できない。

運は「レベルでは上がらず近代化改修でのみ上昇する」ため、ページの表記
（Lv99・改修なし）に対応する正解は api_luck[0]（初期値）side である点に注意。

使い方: python3 scripts/verify_kancolle_stats.py
終了コード 0 = 全一致、1 = 不一致あり
"""
import json
import os
import re
import sys
import urllib.request

MASTER_URL = "https://raw.githubusercontent.com/kcwiki/kancolle-data/master/api/api_start2.json"
CACHE = "/tmp/kc_api_start2.json"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LANGS = ["", "ja", "ko", "zh", "de", "fr", "ar"]

SHIPS = ["雪風改", "島風改", "綾波改", "夕立改", "時雨改", "川内改", "夕張改", "那珂改",
         "鳥海改", "千歳改", "瑞鳳改", "赤城改", "加賀改", "金剛改", "長門改", "伊19改"]

# 表の列位置 -> マスターデータ上の値の取り出し方
COLUMNS = {
    2:  ("耐久",     lambda s: s["api_taik"][0]),
    3:  ("火力",     lambda s: s["api_houg"][1]),
    4:  ("雷装",     lambda s: s["api_raig"][1]),
    5:  ("対空",     lambda s: s["api_tyku"][1]),
    6:  ("装甲",     lambda s: s["api_souk"][1]),
    9:  ("運",       lambda s: s["api_luck"][0]),
    11: ("スロット", lambda s: s["api_slot_num"]),
}


def load_master():
    if not os.path.exists(CACHE):
        urllib.request.urlretrieve(MASTER_URL, CACHE)
    data = json.load(open(CACHE))
    return {s["api_name"]: s for s in data["api_mst_ship"]}


def main():
    master = load_master()
    checked = mismatches = 0

    for lang in LANGS:
        path = os.path.join(ROOT, lang, "games/kancolle/fleet-builder/index.html")
        html = open(path).read()
        for row in re.findall(r"<tr>.*?</tr>", html, re.S):
            for name in SHIPS:
                if name not in row:
                    continue
                cells = [re.sub("<[^>]+>", "", c).strip()
                         for c in re.findall(r"<td[^>]*>(.*?)</td>", row, re.S)]
                if len(cells) != 12:
                    continue
                for idx, (label, getter) in COLUMNS.items():
                    checked += 1
                    expected = str(getter(master[name]))
                    if cells[idx] != expected:
                        mismatches += 1
                        rel = os.path.relpath(path, ROOT)
                        print(f"MISMATCH {rel} {name} {label}: 掲載 {cells[idx]} / 正解 {expected}")

    print(f"checked {checked} values, {mismatches} mismatches")
    return 1 if mismatches else 0


if __name__ == "__main__":
    sys.exit(main())
