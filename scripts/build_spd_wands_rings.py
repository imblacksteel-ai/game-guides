#!/usr/bin/env python3
"""
Shattered Pixel Dungeon の杖・指輪の数値表を生成し、英日ページの
<!-- SPD-WANDS --> / <!-- SPD-RINGS --> マーカー間に書き込む（冪等）。

出典: 本体（00-Evan/shattered-pixel-dungeon, GPL-3.0）の最新リリースタグ
  items/wands/*.java  … min(int lvl) / max(int lvl) / initialCharges()
  items/rings/*.java  … statsInfo 内の「100f * (Math.pow(B, level+1)-1f)」または「100f * (1f - Math.pow(B, level+1))」
  messages/items/items(_ja).properties … 英日の名称
説明文はゲーム内テキストを転載せず、効果の要約は WAND_NOTES / RING_NOTES に手で書いている。
式を評価できないものは推測せず止める。

使い方: python3 scripts/build_spd_wands_rings.py
"""
import html
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_spd_weapons import REPO, UA, ev, get, method_expr  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "assets/data/spd-wands-rings.json")
BASE = "core/src/main/java/com/shatteredpixel/shatteredpixeldungeon/items"
MSG = "core/src/main/assets/messages/items"
PAGES = {"en": "games/shattered-pixel-dungeon/wands-rings/index.html",
         "ja": "ja/games/shattered-pixel-dungeon/wands-rings/index.html"}

WAND_NOTES = {
    "wandofmagicmissile": ("Cheap, reliable single-target damage; starts with 3 charges.", "安定した単体ダメージ。初期充填が3回。"),
    "wandoflightning": ("Lightning that arcs between nearby targets.", "近くの敵に連鎖する雷。"),
    "wandofdisintegration": ("A beam that pierces through every enemy in its path.", "直線上の敵をすべて貫くビーム。"),
    "wandoffireblast": ("A cone of fire; can spend up to 3 charges at once for a bigger blast (damage shown for 1 charge).", "扇状の炎。一度に最大3回分の充填を使って強化できる（表は1回分）。"),
    "wandofcorrosion": ("Releases corrosive gas that keeps damaging enemies inside it.", "中にいる敵を傷つけ続ける腐食ガスを放つ。"),
    "wandofblastwave": ("Damages and knocks enemies back.", "ダメージを与えて敵を吹き飛ばす。"),
    "wandoffrost": ("Damages and chills enemies, and can freeze them.", "ダメージを与えて敵を冷やし、凍らせることもある。"),
    "wandofprismaticlight": ("Damages and blinds; extra effect on demonic and undead enemies.", "ダメージを与えて目をくらませる。悪魔・アンデッドに追加効果。"),
    "wandofcorruption": ("Turns a weakened enemy into an ally; otherwise inflicts debuffs.", "弱った敵を味方にする。失敗時は弱体効果を与える。"),
    "wandofliving earth".replace(" ", ""): ("Gives you rock armor and forms an earthen guardian to fight for you.", "岩の鎧をまとい、戦ってくれる土の守護者を作る。"),
    "wandofregrowth": ("Grows grass and plants over an area.", "範囲に草や植物を生やす。"),
    "wandoftransfusion": ("Spends your HP to heal allies or charm enemies; hurts undead.", "自分の体力を使って味方を回復したり敵を魅了したりする。アンデッドには有害。"),
    "wandofwarding": ("Summons stationary sentries that shoot at enemies.", "敵を撃つ固定式の番兵を呼び出す。"),
}
RING_NOTES = {
    "ringofaccuracy": ("Accuracy", "命中"), "ringofarcana": ("Enchantment and glyph power", "エンチャント・刻印の効果"),
    "ringofelements": ("Less damage and duration from elemental effects", "属性効果のダメージ・持続を軽減"),
    "ringofenergy": ("Wand and artifact recharge speed", "杖・アーティファクトの充填速度"),
    "ringofevasion": ("Evasion", "回避"), "ringoffuror": ("Attack speed", "攻撃速度"),
    "ringofhaste": ("Movement speed", "移動速度"), "ringofmight": ("Max HP (plus +1 STR per step)", "最大体力（段階ごとに筋力も+1）"),
    "ringofsharpshooting": ("Thrown-weapon durability (and their level)", "投擲武器の耐久（とレベル）"),
    "ringoftenacity": ("Less damage taken, scaling with missing HP", "被ダメージ軽減（体力が減るほど強い）"),
    "ringofwealth": ("Extra item drops from enemies", "敵からの追加ドロップ"),
    "ringofforce": ("Unarmed and weapon-ability damage (special formula)", "素手・武器技のダメージ（独自の式）"),
}


def props(text, kind):
    return {m.group(1): m.group(2).strip() for m in re.finditer(rf"items\.{kind}\.(\w+)\.name=(.+)", text)}


def main():
    tag = get(f"https://api.github.com/repos/{REPO}/releases/latest", True)["tag_name"]
    raw = lambda p: get(f"https://raw.githubusercontent.com/{REPO}/{tag}/{p}")
    en_txt, ja_txt = raw(f"{MSG}/items.properties"), raw(f"{MSG}/items_ja.properties")
    names = lambda kind: (props(en_txt, kind), props(ja_txt, kind))
    errors = []

    wen, wja = names("wands")
    wands = []
    for f in get(f"https://api.github.com/repos/{REPO}/contents/{BASE}/wands?ref={tag}", True):
        cls = f["name"][:-5]
        if not cls.startswith("WandOf"):
            continue
        s = raw(f"{BASE}/wands/{f['name']}")
        wid = cls.lower()
        ic = re.search(r"public int initialCharges\(\)\s*\{\s*return (\d+);", s)
        w = {"id": wid, "name_en": wen.get(wid, cls), "name_ja": wja.get(wid, wen.get(wid, cls)),
             "charges": int(ic.group(1)) if ic else 2}
        mn, mx = method_expr(s, r"min\(int lvl\)"), method_expr(s, r"max\(int lvl\)")
        if mn and mx:
            if "chargesPerCast" in mn or "switch" in s[s.find("max(int lvl)"):s.find("max(int lvl)") + 300]:
                mn, mx = mn.replace("* chargesPerCast()", "* 1"), None  # 火炎の杖は充填数で分岐する
                m2 = re.search(r"case 1:(?:\s*default:)?\s*return (.*?);", s)
                mx = m2.group(1) if m2 else None
            try:
                w.update({"min": ev(mn, 0, 0), "max": ev(mx, 0, 0),
                          "min_per_lvl": ev(mn, 0, 1) - ev(mn, 0, 0), "max_per_lvl": ev(mx, 0, 1) - ev(mx, 0, 0)})
            except (ValueError, TypeError) as e:
                errors.append(f"{cls}: {e}")
        if wid not in WAND_NOTES:
            errors.append(f"{cls}: no note written")
        wands.append(w)

    ren, rja = names("rings")
    rings = []
    for f in get(f"https://api.github.com/repos/{REPO}/contents/{BASE}/rings?ref={tag}", True):
        cls = f["name"][:-5]
        if not cls.startswith("RingOf"):
            continue
        s = raw(f"{BASE}/rings/{f['name']}")
        rid = cls.lower()
        r = {"id": rid, "name_en": ren.get(rid, cls), "name_ja": rja.get(rid, ren.get(rid, cls))}
        up = re.search(r"100f \* \(Math\.pow\(([\d.]+)f?, level\+1\)-1f\)", s)
        down = re.search(r"100f \* \(1f - Math\.pow\(([\d.]+)f?, level\+1\)\)", s)
        if up:
            r.update({"base": float(up.group(1)), "dir": "up"})
        elif down:
            r.update({"base": float(down.group(1)), "dir": "down"})
        if rid not in RING_NOTES:
            errors.append(f"{cls}: no note written")
        rings.append(r)

    if errors:
        sys.exit("not writing:\n  " + "\n  ".join(errors))
    wands.sort(key=lambda w: ("min" not in w, w["name_en"]))
    rings.sort(key=lambda r: r["name_en"])
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump({"version": tag, "wands": wands, "rings": rings}, fh, ensure_ascii=False, separators=(",", ":"))
    print(f"{tag}: {len(wands)} wands, {len(rings)} rings -> {os.path.relpath(OUT, ROOT)}")
    render(tag, wands, rings)


T = {
    "en": {"wh": ["Wand", "Damage at +0", "Per upgrade", "Charges", "What it does"],
           "rh": ["Ring", "Affects", "+0", "+1", "+2", "+3", "Per level"], "up": "+{v}%", "down": "−{v}%",
           "special": "special", "charges": "{c} (+1 per upgrade, max 10)"},
    "ja": {"wh": ["杖", "+0のダメージ", "強化ごと", "充填回数", "効果"],
           "rh": ["指輪", "効果", "+0", "+1", "+2", "+3", "1段階あたり"], "up": "+{v}%", "down": "−{v}%",
           "special": "独自", "charges": "{c}（強化ごと+1、最大10）"},
}


def cap(s):
    return " ".join(x if x == "of" else x[:1].upper() + x[1:] for x in s.split())


def pct(base, lvl, d):
    v = (base ** (lvl + 1) - 1) * 100 if d == "up" else (1 - base ** (lvl + 1)) * 100
    return f"{v:.1f}".rstrip("0").rstrip(".")


def render(tag, wands, rings):
    for lang, page in PAGES.items():
        path = os.path.join(ROOT, page)
        if not os.path.exists(path):
            print(f"  (page not created yet: {page})")
            continue
        t, i = T[lang], (0 if lang == "en" else 1)
        e = html.escape
        wr = []
        for w in wands:
            nm, sub = (cap(w["name_en"]), w["name_ja"]) if lang == "en" else (w["name_ja"], cap(w["name_en"]))
            dmg = f'{w["min"]}–{w["max"]}' if "min" in w else "—"
            per = f'+{w["min_per_lvl"]} / +{w["max_per_lvl"]}' if "min" in w else "—"
            wr.append(f'<tr><td>{e(nm)}<br><span class="romaji">{e(sub)}</span></td><td class="tag-mono">{dmg}</td>'
                      f'<td class="tag-mono">{per}</td><td>{t["charges"].format(c=w["charges"])}</td><td>{e(WAND_NOTES[w["id"]][i])}</td></tr>')
        rr = []
        for r in rings:
            nm, sub = (cap(r["name_en"]), r["name_ja"]) if lang == "en" else (r["name_ja"], cap(r["name_en"]))
            if "base" in r:
                cells = "".join(f'<td class="tag-mono">{t[r["dir"]].format(v=pct(r["base"], l, r["dir"]))}</td>' for l in range(4))
                step = f'×{r["base"]:g}'
            else:
                cells, step = "".join(f'<td class="build-note">{t["special"]}</td>' for _ in range(4)), "—"
            rr.append(f'<tr><td>{e(nm)}<br><span class="romaji">{e(sub)}</span></td><td>{e(RING_NOTES[r["id"]][i])}</td>{cells}<td class="tag-mono">{step}</td></tr>')
        s = open(path, encoding="utf-8").read()
        for marker, head, rows in (("SPD-WANDS", t["wh"], wr), ("SPD-RINGS", t["rh"], rr)):
            table = (f'<table class="glossary spd-table">\n<thead><tr>{"".join(f"<th>{h}</th>" for h in head)}</tr></thead>\n<tbody>\n'
                     + "\n".join(rows) + "\n</tbody>\n</table>")
            s, n = re.subn(rf"(<!-- {marker}:START -->\n).*?(<!-- {marker}:END -->)",
                           lambda m: m.group(1) + table + "\n" + m.group(2), s, flags=re.S)
            if n != 1:
                sys.exit(f"{marker} markers not found in {page}")
        s = re.sub(r'(<span id="spd-version">)[^<]*(</span>)', lambda m: m.group(1) + tag + m.group(2), s)
        open(path, "w", encoding="utf-8").write(s)
        print(f"rendered into {page}")


if __name__ == "__main__":
    main()
