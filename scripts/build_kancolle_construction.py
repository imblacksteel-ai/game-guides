#!/usr/bin/env python3
"""
建造ページ（建造時間の逆引き表）を生成する。
  1. assets/data/kancolle-construction.json を書き出す
  2. 英日ページの <!-- BUILD-TABLE:START --> 〜 <!-- BUILD-TABLE:END --> に表を書き込む（冪等）

出典:
  - 建造時間: マスターデータ api_start2.json の api_buildtime（kcwiki/kancolle-data 経由）
  - 通常建造/大型艦建造で出るか: kcwiki/kancolle-data の wiki/ship.json（_buildable / _buildable_lsc）。
    マスターデータには無い情報なので、日本の攻略Wiki（wikiwiki.jp/kancolle/建造）の建造時間一覧表と
    照合する。各艦が「その建造時間の行」に載っていなければ書き出さずに止める。
  - 秘書艦条件（海外艦）: 同Wikiの建造時間一覧表。SECRETARY に手で持ち、艦名の存在だけ機械的に確認する。

使い方: python3 scripts/build_kancolle_construction.py
"""
import html
import json
import os
import re
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "assets/data/kancolle-construction.json")
BASE = "https://raw.githubusercontent.com/kcwiki/kancolle-data/master"
WIKI_URL = "https://wikiwiki.jp/kancolle/%E5%BB%BA%E9%80%A0"
UA = {"User-Agent": "Mozilla/5.0 (Macintosh) Chrome/131.0"}
PAGES = {"en": "games/kancolle/construction/index.html", "ja": "ja/games/kancolle/construction/index.html"}

# 海外艦の秘書艦条件（wikiwiki.jp/kancolle/建造 の建造時間一覧表より）
SECRETARY = {
    "Z1": ("Z3 as secretary", "秘書艦にZ3"),
    "Z3": ("Z1 as secretary", "秘書艦にZ1"),
    "Zara": ("a Maestrale- or Zara-class secretary", "秘書艦にMaestrale級またはZara級"),
    "Pola": ("an Italian surface ship as secretary", "秘書艦に伊水上艦"),
    "Aquila": ("an Italian surface ship as secretary", "秘書艦に伊水上艦"),
    "Ark Royal": ("Warspite as secretary", "秘書艦にWarspite"),
    "Graf Zeppelin": ("a German ship as secretary", "秘書艦に独艦"),
    "Warspite": ("Kongou Kai Ni or later as secretary", "秘書艦に金剛改二以降"),
    "Valiant": ("Warspite as secretary", "秘書艦にWarspite"),
    "Bismarck": ("Z1 or Z3 as secretary", "秘書艦にZ1またはZ3"),
    "Richelieu": ("a French ship as secretary", "秘書艦に仏艦"),
    "Jean Bart": ("a French ship as secretary", "秘書艦に仏艦"),
    "Saratoga": ("Iowa or Kamoi as secretary", "秘書艦にIowaまたは神威"),
    "Iowa": ("Yamato Kai or later as secretary", "秘書艦に大和改以降"),
}

TYPE_EN = {1: "DE", 2: "DD", 3: "CL", 4: "CLT", 5: "CA", 6: "CAV", 7: "CVL", 8: "FBB", 9: "BB", 10: "BBV",
           11: "CV", 13: "SS", 14: "SSV", 16: "AV", 17: "LHA", 18: "CVB", 19: "AR", 20: "AS", 21: "CT", 22: "AO"}

T = {
    "en": {"head": ["Time", "Type", "Standard construction", "Large construction only"], "lsc": "LSC", "none": "—"},
    "ja": {"head": ["建造時間", "艦種", "通常建造", "大型艦建造のみ"], "lsc": "大型", "none": "—"},
}


def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
        return r.read().decode("utf-8", "ignore")


def wiki_time_rows():
    t = get(WIKI_URL)
    t = html.unescape(re.sub(r"<(script|style)[^>]*>.*?</\1>", "", t, flags=re.S))
    t = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", t))
    a = t.find("建造時間一覧表")
    b = t.find("建造レシピ掲示板", a) if "建造レシピ掲示板" in t[a:] else len(t)
    if a < 0:
        sys.exit("wiki layout changed: build time table not found")
    parts = re.split(r"(\d\d:\d\d):00", t[a:b])
    rows = {}
    for i in range(1, len(parts), 2):
        h, m = parts[i].split(":")
        rows[int(h) * 60 + int(m)] = parts[i + 1]
    return rows


def hhmm(m):
    return f"{m // 60:02d}:{m % 60:02d}"


def main():
    master = json.loads(get(f"{BASE}/api/api_start2.json"))
    master = master.get("api_data", master)
    mships = {s["api_id"]: s for s in master["api_mst_ship"]}
    stype_ja = {s["api_id"]: s["api_name"] for s in master["api_mst_stype"]}
    wiki = json.loads(get(f"{BASE}/wiki/ship.json"))
    rows = wiki_time_rows()

    ships, errors = [], []
    for v in wiki.values():
        if not (v.get("_buildable") or v.get("_buildable_lsc")):
            continue
        m = mships.get(v["_api_id"])
        if not m:
            errors.append(f"{v['_name']}: not in master data")
            continue
        t = m["api_buildtime"]
        if t != v["_build_time"]:
            errors.append(f"{v['_name']}: build time wiki={v['_build_time']} master={t}")
        if v["_japanese_name"] not in rows.get(t, ""):
            errors.append(f"{v['_name']} ({v['_japanese_name']}): not listed at {hhmm(t)} on wikiwiki")
        ships.append({
            "id": v["_api_id"], "name_en": v["_name"], "name_ja": v["_japanese_name"],
            "type": m["api_stype"], "time": t,
            "normal": bool(v.get("_buildable")), "lsc": bool(v.get("_buildable_lsc")),
        })
    names = {s["name_en"] for s in ships}
    for k in SECRETARY:
        if k not in names:
            errors.append(f"secretary note for unknown ship {k}")
    if errors:
        sys.exit("verification failed — not writing:\n  " + "\n  ".join(errors))

    ships.sort(key=lambda s: (s["time"], s["type"], s["id"]))
    data = {"source": "KanColle master data (build time) + kcwiki (buildability), checked against wikiwiki.jp",
            "ship_types": {k: stype_ja[k] for k in sorted({s["type"] for s in ships})},
            "secretary": SECRETARY, "ships": ships}
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
    print(f"wrote {len(ships)} ships to {os.path.relpath(OUT, ROOT)} (times match master data and wikiwiki)")

    for lang, page in PAGES.items():
        path = os.path.join(ROOT, page)
        s = open(path, encoding="utf-8").read()
        new, n = re.subn(r"(<!-- BUILD-TABLE:START -->\n).*?(<!-- BUILD-TABLE:END -->)",
                         lambda mm: mm.group(1) + render(lang, data, stype_ja) + "\n" + mm.group(2), s, flags=re.S)
        if n != 1:
            sys.exit(f"table markers not found in {page}")
        open(path, "w", encoding="utf-8").write(new)
        print(f"rendered into {page}")


def render(lang, data, stype_ja):
    t = T[lang]
    esc = html.escape

    def label(s):
        name = s["name_en"] if lang == "en" else s["name_ja"]
        note = SECRETARY.get(s["name_en"])
        out = esc(name)
        if note:
            out += f' <span class="build-note">({esc(note[0])})</span>' if lang == "en" else f' <span class="build-note">（{esc(note[1])}）</span>'
        return out

    body = []
    times = sorted({s["time"] for s in data["ships"]})
    for tm in times:
        group = [s for s in data["ships"] if s["time"] == tm]
        types = sorted({s["type"] for s in group})
        for ty in types:
            g = [s for s in group if s["type"] == ty]
            normal = [label(s) for s in g if s["normal"]]
            lsc_only = [label(s) for s in g if s["lsc"] and not s["normal"]]
            search = " ".join(f"{s['name_en']} {s['name_ja']}" for s in g).lower()
            tname = TYPE_EN.get(ty, "?") if lang == "en" else stype_ja[ty]
            time_cell = f'<td class="tag-mono">{hhmm(tm)}</td>'
            body.append(
                f'<tr data-time="{tm}" data-search="{esc(search)}">{time_cell}'
                f"<td>{esc(tname)}</td><td>{' · '.join(normal) or t['none']}</td>"
                f"<td>{' · '.join(lsc_only) or t['none']}</td></tr>")
    head = "".join(f"<th>{h}</th>" for h in t["head"])
    return (f'<table class="glossary build-table" id="build-table">\n<thead><tr>{head}</tr></thead>\n<tbody>\n'
            + "\n".join(body) + "\n</tbody>\n</table>")


if __name__ == "__main__":
    main()
