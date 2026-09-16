#!/usr/bin/env python3
"""
assets/data/kancolle-ships.json をゲーム本体のマスターデータと照合する。

JSONは scripts/build_kancolle_ships.py で生成するが、手編集や生成スクリプトの
列ずれ（過去に運の「初期値」と「改修上限値」を取り違えて8隻ぶん誤掲載した）を
検出するため、生成とは独立にマスターデータ（api_start2）と突き合わせる。

照合できるのはマスターデータに存在する項目のみ:
  耐久(初期) / 火力(最大) / 雷装(最大) / 対空(最大) / 装甲(最大) / 運(初期) / スロット数 / 速力
対潜・索敵はマスターデータに無いので、ここでは値の妥当範囲だけ確認する。

使い方: python3 scripts/verify_kancolle_stats.py
終了コード 0 = 全一致、1 = 不一致あり
"""
import json
import os
import sys
import urllib.request

MASTER_URL = "https://raw.githubusercontent.com/kcwiki/kancolle-data/master/api/api_start2.json"
CACHE = "/tmp/kcdata/master.json"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "assets/data/kancolle-ships.json")

CHECKS = {
    "hp":    lambda s: s["api_taik"][0],
    "fire":  lambda s: s["api_houg"][1],
    "torp":  lambda s: s["api_raig"][1],
    "aa":    lambda s: s["api_tyku"][1],
    "armor": lambda s: s["api_souk"][1],
    "luck":  lambda s: s["api_luck"][0],
    "slots": lambda s: s["api_slot_num"],
    "speed": lambda s: 1 if s["api_soku"] >= 10 else 0,
}


def main():
    if not os.path.exists(CACHE):
        os.makedirs(os.path.dirname(CACHE), exist_ok=True)
        urllib.request.urlretrieve(MASTER_URL, CACHE)
    master = {s["api_name"]: s for s in json.load(open(CACHE))["api_mst_ship"]}

    data = json.load(open(DATA))
    idx = {name: i for i, name in enumerate(data["fields"])}
    ships = data["ships"]

    problems = []
    if len(ships) < 800:
        problems.append(f"only {len(ships)} ships — expected 800+, generator may have filtered too much")

    checked = 0
    for row in ships:
        jp = row[idx["jp"]]
        m = master.get(jp)
        if m is None:
            problems.append(f"{jp}: not in master data")
            continue
        for field, getter in CHECKS.items():
            checked += 1
            if row[idx[field]] != getter(m):
                problems.append(f"{jp} {field}: data {row[idx[field]]} / master {getter(m)}")
        for field in ("asw", "los"):
            if not 0 <= row[idx[field]] <= 200:
                problems.append(f"{jp} {field}: out of range ({row[idx[field]]})")

    for p in problems:
        print("MISMATCH", p)
    print(f"{len(ships)} ships, checked {checked} values against master data, {len(problems)} problems")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
