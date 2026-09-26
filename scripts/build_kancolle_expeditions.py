#!/usr/bin/env python3
"""
遠征条件一覧用のデータ assets/data/kancolle-expeditions.json を生成する。

出典:
  1. Kcanotify（antest1/kcanotify, GPL-3.0）の app/src/main/assets/expedition.json
     = 編成条件（艦種・旗艦Lv・合計Lv・ドラム缶・火力/対空/対潜/索敵の合計）と獲得資源。
     編成条件と資源量はマスターデータに存在しないため、ここだけが情報源。
     取り込むのは数値（事実）だけで、コードは使っていない。
  2. api_start2.json（kcwiki/kancolle-data 経由のマスターデータ）
     = 遠征名・所要時間・艦数・海域・アイテム報酬・月間遠征かどうか。

重複する項目（名前・時間・艦数・海域）はマスターデータと照合し、食い違いがあれば
書き出さずに止める。アイテム報酬はマスターデータを採用する（差分は表示だけする）。支援遠征（S1/S2）は条件が特殊なので除く。

total-cond の形式（Kcanotify）: "/" で区切った候補のどれか1つを満たせばよい。
候補の中は "|" 区切りのAND条件で、各条件は "艦種ID[,艦種ID...]-隻数"。
艦種ID 27 は Kcanotify 独自の「護衛空母」（マスターデータの艦種ではない）。

使い方: python3 scripts/build_kancolle_expeditions.py
"""
import json
import os
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "assets/data/kancolle-expeditions.json")
KCN_URL = "https://raw.githubusercontent.com/antest1/kcanotify/master/app/src/main/assets/expedition.json"
MASTER_URL = "https://raw.githubusercontent.com/kcwiki/kancolle-data/master/api/api_start2.json"
UA = {"User-Agent": "Mozilla/5.0 (Macintosh) Chrome/131.0"}
CVE = 27


def get_json(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


def parse_cond(s):
    options = []
    for opt in s.split("/"):
        reqs = []
        for part in opt.split("|"):
            types, count = part.split("-")
            reqs.append({"types": [int(t) for t in types.split(",")], "count": int(count)})
        options.append(reqs)
    return options


def main():
    kcn = get_json(KCN_URL)
    master = get_json(MASTER_URL)
    master = master.get("api_data", master)
    missions = {m["api_id"]: m for m in master["api_mst_mission"]}
    stypes = {s["api_id"]: s["api_name"] for s in master["api_mst_stype"]}
    useitems = {u["api_id"]: u["api_name"] for u in master["api_mst_useitem"]}

    out, errors = [], []
    used_types, used_items = set(), set()
    for e in kcn:
        if e["area"] == 99:  # 支援遠征
            continue
        mid = int(e["no"])
        m = missions.get(mid)
        if m is None:
            errors.append(f"{e['code']}: not in master data")
            continue
        checks = [
            ("name", e["name"]["jp"], m["api_name"]),
            ("time", e["time"], m["api_time"]),
            ("ships", e["total-num"], m["api_deck_num"]),
            ("area", e["area"], m["api_maparea_id"]),
        ]
        for label, a, b in checks:
            if a != b:
                errors.append(f"{e['code']} {label}: kcanotify={a} master={b}")
        # アイテム報酬はマスターデータを採用する（Kcanotify側が古い遠征がある）。
        for label, a, b in (("item1", e["reward"][0], m["api_win_item1"]), ("item2", e["reward"][1], m["api_win_item2"])):
            if a != b:
                print(f"note: {e['code']} {label} kcanotify={a} master={b} -> using master")

        cond = parse_cond(e["total-cond"]) if "total-cond" in e else []
        for opt in cond:
            for r in opt:
                used_types.update(r["types"])
        flag_types = [int(t) for t in e["flag-cond"].split("/")] if "flag-cond" in e else []
        used_types.update(flag_types)
        items = [r for r in (m["api_win_item1"], m["api_win_item2"]) if r[0]]
        used_items.update(r[0] for r in items)

        out.append({
            "id": mid,
            "code": m["api_disp_no"],
            "area": m["api_maparea_id"],
            "name_ja": m["api_name"],
            "name_en": e["name"]["en"],
            "time": m["api_time"],
            "monthly": m["api_reset_type"] == 1,
            "ships": m["api_deck_num"],
            "flag_lv": e.get("flag-lv", 1),
            "flag_types": flag_types,
            "total_lv": e.get("total-lv", 0),
            "comp": cond,
            "drum_ships": e.get("drum-ship", 0),
            "drums": e.get("drum-num", 0),
            "drums_bonus": e.get("drum-num-optional", 0),
            "firepower": e.get("total-firepower", 0),
            "aa": e.get("total-fp", 0),
            "asw": e.get("total-asw", 0),
            "los": e.get("total-los", 0),
            "fuel": e["resource"][0], "ammo": e["resource"][1],
            "steel": e["resource"][2], "bauxite": e["resource"][3],
            "item1": m["api_win_item1"], "item2": m["api_win_item2"],
        })

    if errors:
        sys.exit("master data mismatch — not writing:\n  " + "\n  ".join(errors))

    type_names = {}
    for t in sorted(used_types):
        if t == CVE:
            type_names[t] = "護衛空母"
        elif t in stypes:
            type_names[t] = stypes[t]
        else:
            sys.exit(f"unknown ship type id {t}")
    data = {
        "source": "Kcanotify expedition.json (conditions, resources) + KanColle master data",
        "ship_types": type_names,
        "items": {i: useitems[i] for i in sorted(used_items)},
        "expeditions": out,
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
    print(f"wrote {len(out)} expeditions to {os.path.relpath(OUT, ROOT)} (name/time/ships/area match master data)")


if __name__ == "__main__":
    main()
