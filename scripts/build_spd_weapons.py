#!/usr/bin/env python3
"""
Shattered Pixel Dungeon の近接武器データ assets/data/spd-weapons.json を生成し、
英日ページの <!-- SPD-WEAPONS:START --> 〜 <!-- SPD-WEAPONS:END --> に表を書き込む（冪等）。

出典: Shattered Pixel Dungeon 本体（00-Evan/shattered-pixel-dungeon, GPL-3.0）の最新リリースタグの
  items/weapon/melee/*.java（各武器の tier・ACC・DLY・RCH と min/max/STRReq の上書き）と
  Weapon.java の STRReq(tier, lvl)、messages/items/items(_ja).properties（英日の武器名）。
取り込むのは数値と武器名だけ。説明文（ゲーム内テキスト）は転載しない。

min/max/STRReq の式はソースの return 式をそのまま評価する（Math.round は Java と同じ「0.5で切り上げ」）。
評価できない式があれば推測で埋めず止める。

使い方: python3 scripts/build_spd_weapons.py
"""
import html
import json
import math
import os
import re
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "assets/data/spd-weapons.json")
REPO = "00-Evan/shattered-pixel-dungeon"
SRC = "core/src/main/java/com/shatteredpixel/shatteredpixeldungeon/items/weapon/melee"
MSG = "core/src/main/assets/messages/items"
UA = {"User-Agent": "Mozilla/5.0 (Macintosh) Chrome/131.0"}
SKIP = {"MeleeWeapon"}
PAGES = {"en": "games/shattered-pixel-dungeon/index.html", "ja": "ja/games/shattered-pixel-dungeon/index.html",
         "en_w": "games/shattered-pixel-dungeon/weapons/index.html", "ja_w": "ja/games/shattered-pixel-dungeon/weapons/index.html"}


def get(url, as_json=False):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
        body = r.read().decode("utf-8")
    return json.loads(body) if as_json else body


def jround(x):
    return math.floor(x + 0.5)


def strreq(tier, lvl):
    lvl = max(0, lvl)
    return (8 + tier * 2) - int((math.sqrt(8 * lvl + 1) - 1) / 2)


def method_expr(src, sig):
    m = re.search(r"public int " + sig + r"\s*\{\s*(?:int req = )?(.*?);", src, flags=re.S)
    if not m:
        return None
    e = re.sub(r"//[^\n]*", "", m.group(1))
    return re.sub(r"\s+", " ", e.replace("return", "")).strip()


def ev(expr, tier, lvl):
    e = expr.replace("Math.round", "jround").replace("Math.max", "max").replace("Math.min", "min")
    e = re.sub(r"(\d+(?:\.\d+)?)f\b", r"\1", e)
    e = re.sub(r"STRReq\(", "strreq(", e)
    if re.search(r"[A-Za-z_]", re.sub(r"\b(jround|max|min|strreq|tier|lvl)\b", "", e)):
        raise ValueError(expr)
    return eval(e, {"__builtins__": {}}, {"jround": jround, "max": max, "min": min, "strreq": strreq, "tier": tier, "lvl": lvl})


def props(text):
    out = {}
    for line in text.splitlines():
        m = re.match(r"items\.weapon\.melee\.(\w+)\.name=(.+)", line)
        if m:
            out[m.group(1)] = m.group(2).strip()
    return out


def main():
    tag = get(f"https://api.github.com/repos/{REPO}/releases/latest", True)["tag_name"]
    files = get(f"https://api.github.com/repos/{REPO}/contents/{SRC}?ref={tag}", True)
    raw = lambda p: get(f"https://raw.githubusercontent.com/{REPO}/{tag}/{p}")
    en = props(raw(f"{MSG}/items.properties"))
    ja = props(raw(f"{MSG}/items_ja.properties"))

    weapons, errors = [], []
    for f in files:
        cls = f["name"][:-5]
        if cls in SKIP:
            continue
        s = raw(f"{SRC}/{f['name']}")
        tm = re.search(r"\btier\s*=\s*(\d+);", s)
        if not tm:
            errors.append(f"{cls}: no tier")
            continue
        tier = int(tm.group(1))
        g = lambda k: float(m.group(1)) if (m := re.search(rf"\b{k}\s*=\s*([\d.]+)f?;", s)) else 1.0
        try:
            mn = method_expr(s, r"min\(int lvl\)") or "tier + lvl"
            mx = method_expr(s, r"max\(int lvl\)") or "5*(tier+1) + lvl*(tier+1)"
            sr = method_expr(s, r"STRReq\(int lvl\)") or "STRReq(tier, lvl)"
            w = {
                "id": cls.lower(), "tier": tier,
                "name_en": en.get(cls.lower(), cls), "name_ja": ja.get(cls.lower(), en.get(cls.lower(), cls)),
                "min": ev(mn, tier, 0), "max": ev(mx, tier, 0),
                "min_per_lvl": ev(mn, tier, 1) - ev(mn, tier, 0), "max_per_lvl": ev(mx, tier, 1) - ev(mx, tier, 0),
                "str": ev(sr, tier, 0), "acc": g("ACC"), "dly": g("DLY"), "rch": int(g("RCH")),
            }
            # 追加防御（ダメージ軽減の上限に加算）。定数か DRMax(lvl) の式。
            df = re.search(r"public int defenseFactor\( ?Char owner ?\)\s*\{\s*return (.*?);", s, flags=re.S)
            if df:
                if df.group(1).strip() == "DRMax()":
                    dr = method_expr(s, r"DRMax\(int lvl\)")
                    w["block"], w["block_per_lvl"] = ev(dr, tier, 0), ev(dr, tier, 1) - ev(dr, tier, 0)
                else:
                    w["block"], w["block_per_lvl"] = ev(df.group(1), tier, 0), 0
        except ValueError as e:
            errors.append(f"{cls}: cannot evaluate {e}")
            continue
        if cls.lower() not in en:
            errors.append(f"{cls}: no English name")
        weapons.append(w)
    if errors:
        sys.exit("not writing:\n  " + "\n  ".join(errors))
    weapons.sort(key=lambda w: (w["tier"], w["name_en"]))
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump({"version": tag, "weapons": weapons}, fh, ensure_ascii=False, separators=(",", ":"))
    print(f"{tag}: wrote {len(weapons)} melee weapons to {os.path.relpath(OUT, ROOT)}")
    render(tag, weapons)


T = {
    "en": {"head": ["Weapon", "Tier", "STR", "Damage", "Per upgrade", "Avg / turn", "Notes"],
           "acc": "accuracy ×{v}", "dly": "{v} turns per attack", "rch": "reach {v}", "blocks": "+{v} armor", "blocks_lvl": " (+{v}/upgrade)"},
    "ja": {"head": ["武器", "Tier", "必要筋力", "ダメージ", "強化ごと", "1ターン平均", "特徴"],
           "acc": "命中×{v}", "dly": "攻撃に{v}ターン", "rch": "射程{v}", "blocks": "防御+{v}", "blocks_lvl": "（強化ごと+{v}）"},
}


def fmt(v):
    return f"{v:.2f}".rstrip("0").rstrip(".")


def render(tag, weapons):
    for key, page in PAGES.items():
        lang = key.split("_")[0]
        path = os.path.join(ROOT, page)
        if not os.path.exists(path):
            print(f"  (page not created yet: {page})")
            continue
        t = T[lang]
        rows = []
        for w in weapons:
            notes = []
            if w["acc"] != 1:
                notes.append(t["acc"].format(v=fmt(w["acc"])))
            if w["dly"] != 1:
                notes.append(t["dly"].format(v=fmt(w["dly"])))
            if w["rch"] != 1:
                notes.append(t["rch"].format(v=w["rch"]))
            if w.get("block"):
                notes.append(t["blocks"].format(v=w["block"]) + (t["blocks_lvl"].format(v=w["block_per_lvl"]) if w["block_per_lvl"] else ""))
            cap = " ".join(x if x == "of" else x[:1].upper() + x[1:] for x in w["name_en"].split())  # title() だと Mage'S になる
            name = cap if lang == "en" else w["name_ja"]
            sub = w["name_ja"] if lang == "en" else cap
            avg = (w["min"] + w["max"]) / 2 / w["dly"]
            slug = re.sub(r"[^a-z0-9]+", "-", w["name_en"].lower()).strip("-")
            rows.append(
                f'<tr data-tier="{w["tier"]}" id="w-{slug}"><td>{html.escape(name)}<br><span class="romaji">{html.escape(sub)}</span></td>'
                f'<td class="tag-mono">{w["tier"]}</td><td class="tag-mono">{w["str"]}</td>'
                f'<td class="tag-mono">{w["min"]}–{w["max"]}</td>'
                f'<td class="tag-mono">+{w["min_per_lvl"]} / +{w["max_per_lvl"]}</td>'
                f'<td class="tag-mono">{fmt(avg)}</td><td>{" · ".join(notes) or "—"}</td></tr>')
        head = "".join(f"<th>{x}</th>" for x in t["head"])
        table = (f'<table class="glossary spd-table" id="spd-weapons">\n<thead><tr>{head}</tr></thead>\n<tbody>\n'
                 + "\n".join(rows) + "\n</tbody>\n</table>")
        if key.endswith("_w"):
            def nm(w):
                c = " ".join(x if x == "of" else x[:1].upper() + x[1:] for x in w["name_en"].split())
                return c if lang == "en" else w["name_ja"]
            jump = ("Jump to: " if lang == "en" else "移動：") + " · ".join(
                f'<a href="#w-{re.sub(r"[^a-z0-9]+", "-", w["name_en"].lower()).strip("-")}">{html.escape(nm(w))}</a>' for w in weapons)
            table = f'<p style="font-size:.88rem;line-height:1.9;margin:0 0 12px;">{jump}</p>\n<div class="table-scroll">' + table + "</div>"
        s = open(path, encoding="utf-8").read()
        new, n = re.subn(r"(<!-- SPD-WEAPONS:START -->\n).*?(<!-- SPD-WEAPONS:END -->)",
                         lambda m: m.group(1) + table + "\n" + m.group(2), s, flags=re.S)
        if n != 1:
            sys.exit(f"markers not found in {page}")
        new = re.sub(r'(<span id="spd-version">)[^<]*(</span>)', lambda m: m.group(1) + tag + m.group(2), new)
        open(path, "w", encoding="utf-8").write(new)
        print(f"rendered into {page}")


if __name__ == "__main__":
    main()
