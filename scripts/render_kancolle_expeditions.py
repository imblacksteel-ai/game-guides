#!/usr/bin/env python3
"""
遠征条件一覧ページの表を assets/data/kancolle-expeditions.json から生成し、
各言語のHTMLの <!-- EXPED-TABLE:START --> 〜 <!-- EXPED-TABLE:END --> の間に書き込む（冪等）。

表をJSで描画せずHTMLに埋め込むのは、検索エンジンが中身を読めるようにするため。
絞り込み（検索・海域）は assets/games/kancolle-expedition-requirements.js が既存の行を
表示/非表示にするだけ。

データを更新したら: python3 scripts/build_kancolle_expeditions.py && python3 scripts/render_kancolle_expeditions.py
"""
import html
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "assets/data/kancolle-expeditions.json")
AREA_ORDER = [1, 2, 3, 4, 7, 5, 6]

L = {
    "en": {
        "page": "games/kancolle/expedition-requirements/index.html",
        "types": {1: "DE", 2: "DD", 3: "CL", 5: "CA", 7: "CVL", 10: "BBV", 11: "CV", 13: "SS", 14: "SSV",
                  16: "AV", 18: "CVB", 20: "AS", 21: "CT", 27: "CVE"},
        "items": {1: "Bucket", 2: "Flamethrower", 3: "Dev Material", 4: "Screw", 10: "Furniture Box (S)",
                  11: "Furniture Box (M)", 12: "Furniture Box (L)", 59: "Irako"},
        "areas": {1: "Home Waters", 2: "Nansei Islands", 3: "Northern", 4: "Western", 5: "Southern",
                  6: "Central", 7: "Southwestern"},
        "head": ["No.", "Expedition", "Time", "Fleet requirements", "Rewards"],
        "or": " <i>or</i> ", "ships": "{n} ships", "flag": "Flagship Lv{n}+", "flag_type": "Flagship: {t}",
        "total": "Fleet total Lv{n}+", "any": "any ship types",
        "drums": "Drums: {n} across {s}+ ships", "drum_ships": "Drums on {s}+ ships",
        "drums_bonus": "{n}+ drums raise great-success odds",
        "fp": "Firepower", "aa": "AA", "asw": "ASW", "los": "LoS", "stats": "Fleet totals: {v}",
        "fuel": "Fuel", "ammo": "Ammo", "steel": "Steel", "baux": "Bauxite",
        "item": "{name} ×{r} (chance)", "item_gs": "{name} ×{r} (great success)", "monthly": "Monthly",
        "none": "—",
    },
    "ja": {
        "page": "ja/games/kancolle/expedition-requirements/index.html",
        "types": {1: "海防", 2: "駆逐", 3: "軽巡", 5: "重巡", 7: "軽空母", 10: "航戦", 11: "正規空母", 13: "潜水艦",
                  14: "潜水空母", 16: "水母", 18: "装甲空母", 20: "潜水母艦", 21: "練巡", 27: "護衛空母"},
        "items": {1: "高速修復材", 2: "高速建造材", 3: "開発資材", 4: "改修資材", 10: "家具箱（小）",
                  11: "家具箱（中）", 12: "家具箱（大）", 59: "伊良湖"},
        "areas": {1: "鎮守府海域", 2: "南西諸島海域", 3: "北方海域", 4: "西方海域", 5: "南方海域",
                  6: "中部海域", 7: "南西海域"},
        "head": ["番号", "遠征名", "時間", "編成条件", "報酬"],
        "or": " <i>または</i> ", "ships": "{n}隻", "flag": "旗艦Lv{n}以上", "flag_type": "旗艦：{t}",
        "total": "合計Lv{n}以上", "any": "艦種自由",
        "drums": "ドラム缶{n}個（{s}隻以上に搭載）", "drum_ships": "ドラム缶搭載艦{s}隻以上",
        "drums_bonus": "ドラム缶{n}個以上で大成功率アップ",
        "fp": "火力", "aa": "対空", "asw": "対潜", "los": "索敵", "stats": "合計：{v}",
        "fuel": "燃料", "ammo": "弾薬", "steel": "鋼材", "baux": "ボーキ",
        "item": "{name}×{r}（確率）", "item_gs": "{name}×{r}（大成功時）", "monthly": "月間",
        "none": "—",
    },
}


def fmt_time(m, lang):
    h, mm = divmod(m, 60)
    if lang == "ja":
        return f"{h}時間{mm:02d}分" if h else f"{mm}分"
    return f"{h}h {mm:02d}m" if h else f"{mm}m"


def type_group(types, t):
    return "/".join(t[x] for x in types)


def row(e, t, lang):
    esc = html.escape
    req = []
    req.append(t["ships"].format(n=e["ships"]))
    if e["flag_lv"] > 1:
        req.append(t["flag"].format(n=e["flag_lv"]))
    if e["flag_types"]:
        req.append(t["flag_type"].format(t=type_group(e["flag_types"], t["types"])))
    if e["total_lv"]:
        req.append(t["total"].format(n=e["total_lv"]))
    lines = [" · ".join(req)]
    if e["comp"]:
        opts = [" + ".join(f"{type_group(r['types'], t['types'])}×{r['count']}" for r in opt) for opt in e["comp"]]
        lines.append(t["or"].join(opts))
    else:
        lines.append(t["any"])
    if e["drums"]:
        lines.append(t["drums"].format(n=e["drums"], s=e["drum_ships"]))
    elif e["drum_ships"]:
        lines.append(t["drum_ships"].format(s=e["drum_ships"]))
    if e["drums_bonus"]:
        lines.append(t["drums_bonus"].format(n=e["drums_bonus"]))
    stats = [f"{t[k]} {e[f]}" for k, f in (("fp", "firepower"), ("aa", "aa"), ("asw", "asw"), ("los", "los")) if e[f]]
    if stats:
        lines.append(t["stats"].format(v=" / ".join(stats)))

    res = [f"{t[k]} {e[f]}" for k, f in (("fuel", "fuel"), ("ammo", "ammo"), ("steel", "steel"), ("baux", "bauxite")) if e[f]]
    rew = [" · ".join(res) or t["none"]]
    items = []
    # アイテム1は成功時に確率で、アイテム2は大成功時に確定で入手。個数はどちらも1〜Nのランダム。
    for key, tpl in (("item1", "item"), ("item2", "item_gs")):
        iid, n = e[key]
        if iid:
            r = "1" if n == 1 else ("1〜%d" % n if lang == "ja" else "1–%d" % n)
            items.append(t[tpl].format(name=t["items"][iid], r=r))
    if items:
        rew.append(" · ".join(items))

    name_main, name_sub = (e["name_en"], e["name_ja"]) if lang == "en" else (e["name_ja"], "")
    search = f"{e['code']} {e['code'].lstrip('0')} {e['name_en']} {e['name_ja']}".lower()
    monthly = f' <span class="badge-monthly">{t["monthly"]}</span>' if e["monthly"] else ""
    sub = f'<br><span class="romaji">{esc(name_sub)}</span>' if name_sub else ""
    return (
        f'<tr id="exp-{esc(e["code"].lower())}" data-area="{e["area"]}" data-search="{esc(search)}">'
        f'<td class="tag-mono">{esc(e["code"])}</td>'
        f'<td>{esc(name_main)}{monthly}{sub}</td>'
        f'<td class="tag-mono">{fmt_time(e["time"], lang)}</td>'
        f'<td>{"<br>".join(lines)}</td>'
        f'<td>{"<br>".join(rew)}</td></tr>'
    )


def render(lang, data):
    t = L[lang]
    exps = sorted(data["expeditions"], key=lambda e: (AREA_ORDER.index(e["area"]), e["id"]))
    out = []
    for area in AREA_ORDER:
        rows = [row(e, t, lang) for e in exps if e["area"] == area]
        if not rows:
            continue
        out.append(f'<tr class="area-row" data-area="{area}"><th colspan="5">{t["areas"][area]}</th></tr>')
        out.extend(rows)
    head = "".join(f"<th>{h}</th>" for h in t["head"])
    return (f'<table class="glossary exped-table" id="exped-table">\n<thead><tr>{head}</tr></thead>\n<tbody>\n'
            + "\n".join(out) + "\n</tbody>\n</table>")


def main():
    data = json.load(open(DATA, encoding="utf-8"))
    for lang, t in L.items():
        path = os.path.join(ROOT, t["page"])
        s = open(path, encoding="utf-8").read()
        new, n = re.subn(r"(<!-- EXPED-TABLE:START -->\n).*?(<!-- EXPED-TABLE:END -->)",
                         lambda m: m.group(1) + render(lang, data) + "\n" + m.group(2), s, flags=re.S)
        if n != 1:
            raise SystemExit(f"table markers not found in {t['page']}")
        open(path, "w", encoding="utf-8").write(new)
        print(f"rendered {len(data['expeditions'])} rows into {t['page']}")


if __name__ == "__main__":
    main()
