#!/usr/bin/env python3
"""
Shattered Pixel Dungeon のトリンケット表を生成し、英日ページの <!-- SPD-TRINKETS --> マーカー間に書き込む（冪等）。

出典: 本体（00-Evan/shattered-pixel-dungeon, GPL-3.0）の最新リリースタグの items/trinkets/*.java と
      messages/items/items(_ja).properties（英日の名称）。
各トリンケットの「public static float/int 関数名(int level)」をソースから取り出し、+0〜+3で評価する。
評価できる書き方は次の3つだけ（それ以外は推測せず止める）:
  - return 式;
  - if (条件) { return A; } else { return B; }
  - switch (level) { case N: return X; ... default: return Y; }
表示用の変換（×100 など）と効果の説明は SPECS に手で書いている。ゲーム内の文章は転載しない。

使い方: python3 scripts/build_spd_trinkets.py
"""
import html
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_spd_weapons import REPO, get, jround  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "assets/data/spd-trinkets.json")
BASE = "core/src/main/java/com/shatteredpixel/shatteredpixeldungeon/items/trinkets"
MSG = "core/src/main/assets/messages/items"
PAGES = {"en": "games/shattered-pixel-dungeon/trinkets/index.html", "ja": "ja/games/shattered-pixel-dungeon/trinkets/index.html"}

# (クラス名, [(英ラベル, 日ラベル, 値の計算, 単位)], 英の一言, 日の一言)
# 値の計算は f(関数名) で +0〜+3 の値を得る。
SPECS = [
    ("ChaoticCenser", [("Gas near enemies every ~N turns", "約Nターンごとに敵の近くにガス", lambda f: f("averageTurnsUntilGas"), "")],
     "Periodically releases harmful gas next to enemies.", "敵の近くに定期的に有害なガスを発生させる。"),
    ("CrackedSpyglass", [("Chance of an extra hidden item per floor", "階層ごとに隠しアイテムが増える確率", lambda f: [100 * v for v in f("extraLootChance")], "%")],
     "Adds hidden items on non-boss floors (over 100% means one guaranteed plus a chance of a second).", "ボス以外の階層に隠しアイテムを追加（100%超は1個確定＋2個目の確率）。"),
    ("DimensionalSundial", [("Fewer enemy spawns by day", "昼の敵出現の減少", lambda f: [100 * (1 - v) for v in f("enemySpawnMultiplierDaytime")], "%"),
                            ("More enemy spawns at night", "夜の敵出現の増加", lambda f: [100 * (v - 1) for v in f("enemySpawnMultiplierNighttime")], "%")],
     "Uses your real-world clock: fewer enemies 8am–8pm, more at night.", "現実の時刻を使う：8時〜20時は敵が減り、夜は増える。"),
    ("ExoticCrystals", [("Potion/scroll drops turned exotic", "ポーション・巻物がエキゾチックになる割合", lambda f: [100 * v for v in f("consumableExoticChance")], "%")],
     "Replaces some potion and scroll drops with their exotic versions.", "ポーション・巻物の一部をエキゾチック版に置き換える。"),
    ("EyeOfNewt", [("Vision range reduction", "視界の縮小", lambda f: [100 * (1 - v) for v in f("visionRangeMultiplier")], "%"),
                   ("Mind vision on enemies within (tiles)", "敵を透視できる距離（タイル）", lambda f: f("mindVisionRange"), "")],
     "Shrinks your vision but lets you sense nearby enemies through walls.", "視界は狭くなるが、近くの敵を壁越しに感知できる。"),
    ("FerretTuft", [("Evasion for all characters", "全キャラクターの回避", lambda f: [100 * (v - 1) for v in f("evasionMultiplier")], "%")],
     "Raises evasion for everyone — you and enemies alike.", "自分にも敵にも回避を上げる。"),
    ("MimicTooth", [("Mimics more common", "ミミックの出現", lambda f: f("mimicChanceMultiplier"), "×"),
                    ("Chance of an ebony mimic per floor", "階層ごとの黒檀ミミックの確率", lambda f: [100 * v for v in f("ebonyMimicChance")], "%")],
     "More (and better hidden) mimics, which drop more loot.", "ミミックが増えて見破りにくくなるが、ドロップも増える。"),
    ("MossyClump", [("Unthemed floors turned water/grass", "水・草の階層に変わる割合", lambda f: [100 * v for v in f("overrideNormalLevelChance")], "%")],
     "Turns some ordinary floors into water or grass floors.", "普通の階層の一部を水か草の階層にする。"),
    ("ParchmentScrap", [("Enchantments & glyphs", "エンチャント・刻印", lambda f: f("enchantChanceMultiplier"), "×"),
                        ("Curses on weapons & armor", "武器・鎧の呪い", lambda f: f("curseChanceMultiplier"), "×")],
     "More enchanted gear; curses rise at first, then drop to zero at +3.", "エンチャント付き装備が増える。呪いは最初は増えるが+3でゼロになる。"),
    ("PetrifiedSeed", [("Trampled grass drops runestones", "踏んだ草がルーンストーンを落とす割合", lambda f: [100 * v for v in f("stoneInsteadOfSeedChance")], "%"),
                       ("More items from tall grass", "背の高い草からのドロップ増加", lambda f: [100 * (v - 1) for v in f("grassLootMultiplier")], "%")],
     "Grass gives runestones instead of seeds, and more items overall.", "草から種の代わりにルーンストーンが出て、ドロップも増える。"),
    ("RatSkull", [("Rare exotic enemies", "レアなエキゾチック敵の出現", lambda f: f("exoticChanceMultiplier"), "×")],
     "Makes rare exotic enemy variants more likely.", "レアなエキゾチック版の敵が出やすくなる。"),
    ("SaltCube", [("Longer until hungry", "空腹になるまでの時間の延長", lambda f: [100 * (1 / v - 1) for v in f("hungerGainMultiplier")], "%"),
                  ("Slower HP regeneration", "体力回復の低下", lambda f: [100 * (1 - v) for v in f("healthRegenMultiplier")], "%")],
     "Food lasts longer, but natural healing is slower (except on locked boss floors).", "食料が長持ちするが、自然回復が遅くなる（ボス階の封鎖中は除く）。"),
    ("ThirteenLeafClover", [("Hits at max damage", "最大ダメージになる確率", lambda f: [100 * 0.6 * v for v in f("alterHeroDamageChance")], "%"),
                            ("Hits at min damage", "最小ダメージになる確率", lambda f: [100 * 0.4 * v for v in f("alterHeroDamageChance")], "%")],
     "Your hits roll max or min damage more often — more swingy, slightly higher on average.", "攻撃が最大か最小ダメージになりやすくなる（振れ幅が大きく、平均はやや上がる）。"),
    ("TrapMechanism", [("Unthemed floors turned traps/chasms", "罠・奈落の階層に変わる割合", lambda f: [100 * v for v in f("overrideNormalLevelChance")], "%"),
                       ("Hidden traps made visible", "隠し罠が見える割合", lambda f: [100 * v for v in f("revealHiddenTrapChance")], "%")],
     "More trap floors, but more of the hidden traps are revealed.", "罠の階層が増えるが、隠し罠の一部が見えるようになる。"),
    ("VialOfBlood", [("More total healing from potions/waterskin/wells", "治癒ポーション・水袋・泉の回復量の増加", lambda f: [100 * (v - 1) for v in f("totalHealMultiplier")], "%")],
     "Heals more in total, but the healing is spread over more turns.", "合計の回復量は増えるが、回復にかかるターンが長くなる。"),
    ("WondrousResin", [("Cursed wand effects made neutral/positive", "呪われた杖の効果が無害・有益になる確率", lambda f: [100 * v for v in f("positiveCurseEffectChance")], "%"),
                       ("Extra positive cursed zap from normal wands", "通常の杖から追加の有益な呪い効果", lambda f: [100 * v for v in f("extraCurseEffectChance")], "%")],
     "Tames cursed wand effects and adds bonus random effects to normal wands.", "呪われた杖の効果を穏やかにし、通常の杖にも追加のランダム効果を加える。"),
    ("ShardOfOblivion", [("Max unidentified items counted (+20% loot each)", "数える未識別装備の上限（1つにつき敵ドロップ+20%）", lambda f: [l + 1 for l in range(4)], "")],
     "Rewards using unidentified gear with more enemy drops, and lets you identify by using items.", "未識別の装備を使うほど敵のドロップが増え、使うことで識別もできる。"),
]


def fn_body(src, name):
    m = re.search(rf"public static (?:float|int) {name}\(\s*int level\s*\)\s*\{{", src)
    if not m:
        raise ValueError(f"function {name} not found")
    i, depth = m.end(), 1
    while depth:
        depth += {"{": 1, "}": -1}.get(src[i], 0)
        i += 1
    return re.sub(r"\s+", " ", src[m.end():i - 1]).strip()


def py(expr, level):
    e = expr.replace("Math.round", "jround")
    e = re.sub(r"(\d+(?:\.\d+)?|\.\d+)f\b", r"\1", e)
    if re.search(r"[A-Za-z_]", re.sub(r"\b(jround|level)\b", "", e)):
        raise ValueError(f"unsupported expression: {expr}")
    v = eval(e.replace("level", str(level)), {"__builtins__": {}}, {"jround": jround})
    return v


def evaluate(body, level):
    m = re.fullmatch(r"return (.+?);", body)
    if m:
        return py(m.group(1), level)
    m = re.fullmatch(r"if \((.+?)\) ?\{? ?return (.+?); ?\}? ?else ?\{? ?return (.+?); ?\}?", body)
    if m:
        cond = py(m.group(1).replace("==", "=="), level)
        return py(m.group(2) if cond else m.group(3), level)
    m = re.fullmatch(r"switch \(level\) ?\{(.*)\}", body)
    if m:
        cases, default = {}, None
        for labels, val in re.findall(r"((?:(?:case -?\d+|default): ?)+)return (.+?);", m.group(1)):
            for lab in re.findall(r"case (-?\d+)|(default)", labels):
                if lab[1]:
                    default = val
                else:
                    cases[int(lab[0])] = val
        return py(cases.get(level, default), level)
    raise ValueError(f"unsupported body: {body[:80]}")


def main():
    tag = get(f"https://api.github.com/repos/{REPO}/releases/latest", True)["tag_name"]
    raw = lambda p: get(f"https://raw.githubusercontent.com/{REPO}/{tag}/{p}")
    en = dict(re.findall(r"items\.trinkets\.(\w+)\.name=(.+)", raw(f"{MSG}/items.properties")))
    ja = dict(re.findall(r"items\.trinkets\.(\w+)\.name=(.+)", raw(f"{MSG}/items_ja.properties")))
    listed = {f["name"][:-5] for f in get(f"https://api.github.com/repos/{REPO}/contents/{BASE}?ref={tag}", True)}
    specced = {s[0] for s in SPECS}
    missing = listed - specced - {"Trinket", "TrinketCatalyst"}
    if missing:
        sys.exit(f"trinkets without a SPECS entry (add them): {sorted(missing)}")

    out = []
    for cls, stats, note_en, note_ja in SPECS:
        src = raw(f"{BASE}/{cls}.java")
        cost = re.search(r"upgradeEnergyCost\(\)\s*\{[^}]*?return (.+?);", src, flags=re.S).group(1)
        costs = [py(cost.replace("level()", "level"), l) for l in range(3)]
        cache = {}

        def f(name):
            if name not in cache:
                body = fn_body(src, name)
                cache[name] = [evaluate(body, l) for l in range(4)]
            return cache[name]

        rows = []
        for le, lj, calc, unit in stats:
            vals = calc(f)
            rows.append({"en": le, "ja": lj, "values": [round(v, 2) for v in vals], "unit": unit})
        key = cls.lower()
        out.append({"id": key, "name_en": en[key].strip(), "name_ja": ja.get(key, en[key]).strip(),
                    "upgrade_costs": costs, "stats": rows, "note_en": note_en, "note_ja": note_ja})
    out.sort(key=lambda t: t["name_en"])
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump({"version": tag, "trinkets": out}, fh, ensure_ascii=False, separators=(",", ":"))
    print(f"{tag}: {len(out)} trinkets -> {os.path.relpath(OUT, ROOT)}")
    render(tag, out)


def fmt(v):
    return f"{v:.2f}".rstrip("0").rstrip(".")


def cap(s):
    return " ".join(x if x == "of" else x[:1].upper() + x[1:] for x in s.split())


def render(tag, trinkets):
    head = {"en": ["Trinket", "Effect", "+0", "+1", "+2", "+3", "Energy to upgrade"],
            "ja": ["トリンケット", "効果", "+0", "+1", "+2", "+3", "強化に必要なエネルギー"]}
    for lang, page in PAGES.items():
        path = os.path.join(ROOT, page)
        if not os.path.exists(path):
            print(f"  (page not created yet: {page})")
            continue
        e = html.escape
        rows = []
        for t in trinkets:
            nm, sub = (cap(t["name_en"]), t["name_ja"]) if lang == "en" else (t["name_ja"], cap(t["name_en"]))
            costs = " → ".join(str(c) for c in t["upgrade_costs"])
            n = len(t["stats"])
            for i, s in enumerate(t["stats"]):
                vals = "".join(f'<td class="tag-mono">{fmt(v)}{s["unit"] if s["unit"] != "×" else ""}{"×" if s["unit"] == "×" else ""}</td>' for v in s["values"])
                first = (f'<td rowspan="{n}">{e(nm)}<br><span class="romaji">{e(sub)}</span>'
                         f'<br><span class="build-note">{e(t["note_" + lang])}</span></td>') if i == 0 else ""
                last = f'<td class="tag-mono" rowspan="{n}">{costs}</td>' if i == 0 else ""
                rows.append(f"<tr>{first}<td>{e(s[lang])}</td>{vals}{last}</tr>")
        table = (f'<table class="glossary spd-table">\n<thead><tr>{"".join(f"<th>{h}</th>" for h in head[lang])}</tr></thead>\n<tbody>\n'
                 + "\n".join(rows) + "\n</tbody>\n</table>")
        s = open(path, encoding="utf-8").read()
        s, k = re.subn(r"(<!-- SPD-TRINKETS:START -->\n).*?(<!-- SPD-TRINKETS:END -->)",
                       lambda m: m.group(1) + table + "\n" + m.group(2), s, flags=re.S)
        if k != 1:
            sys.exit(f"markers not found in {page}")
        s = re.sub(r'(<span id="spd-version">)[^<]*(</span>)', lambda m: m.group(1) + tag + m.group(2), s)
        open(path, "w", encoding="utf-8").write(s)
        print(f"rendered into {page}")


if __name__ == "__main__":
    main()
