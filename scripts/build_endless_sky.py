#!/usr/bin/env python3
"""
Endless Sky（オープンソース、GPL-3.0）のデータから、船・武器・交易ルート・最初の船の表を生成し、
英日ページの <!-- ES-* --> マーカー間に書き込む（冪等）。

出典: endless-sky/endless-sky の COMMIT 時点の data/（インデントで階層を表す独自テキスト形式）。
式はソースで確認済み:
  ShipInfoDisplay.cpp … 最高速度 = 60×推力/抵抗、加速 = 3600×推力/質量、旋回 = 60×turn/質量
  System.cpp          … 価格 = 基準価格 − 100×erf(在庫/20000)（基準から最大±100程度しか動かない）
武器のDPSは 60/reload × 1発のダメージ（サブミュニションは再帰的に合計）、射程は velocity×lifetime（サブミュニションは足す）。
銀河は開始時点の状態（イベントで変わる店・政府は反映しない）。ゲーム内の説明文（GPLのテキスト）は転載しない。

使い方: python3 scripts/build_endless_sky.py              （COMMIT を /tmp に sparse clone）
        ES_DIR=/path/to/endless-sky python3 scripts/build_endless_sky.py
"""
import html
import json
import math
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = "endless-sky/endless-sky"
COMMIT = "b28e3c36fb1f10e79607d5d27f5cb3721909b94e"  # 2026-10-03
COMMIT_DATE = "2026-10-03"
PAGES = {
    "ships": {"en": "games/endless-sky/ships/index.html", "ja": "ja/games/endless-sky/ships/index.html"},
    "weapons": {"en": "games/endless-sky/weapons/index.html", "ja": "ja/games/endless-sky/weapons/index.html"},
    "trade": {"en": "games/endless-sky/making-money/index.html", "ja": "ja/games/endless-sky/making-money/index.html"},
    "starter": {"en": "games/endless-sky/first-ship/index.html", "ja": "ja/games/endless-sky/first-ship/index.html"},
    "outfits": {"en": "games/endless-sky/outfits/index.html", "ja": "ja/games/endless-sky/outfits/index.html"},
    "licenses": {"en": "games/endless-sky/licenses/index.html", "ja": "ja/games/endless-sky/licenses/index.html"},
}
OUT = os.path.join(ROOT, "assets/data/endless-sky.json")
HUMAN_GOV = {"Republic", "Syndicate", "Pirate", "Free Worlds", "Independent", "Neutral", "Militia", "Merchant"}


# ---------- data loading ----------
def data_dir():
    d = os.environ.get("ES_DIR")
    if d:
        return os.path.join(d, "data")
    tmp = "/tmp/es-build"
    if not os.path.isdir(os.path.join(tmp, "data")):
        subprocess.run(["git", "clone", "-q", "--filter=blob:none", "--sparse", f"https://github.com/{REPO}.git", tmp], check=True)
        subprocess.run(["git", "-C", tmp, "sparse-checkout", "set", "data"], check=True)
    subprocess.run(["git", "-C", tmp, "checkout", "-q", COMMIT], check=True)
    return os.path.join(tmp, "data")


def tokenize(line):
    toks, i, n = [], 0, len(line)
    while i < n:
        c = line[i]
        if c in " \t":
            i += 1; continue
        if c == "#":
            break
        if c in '"`':
            j = line.find(c, i + 1); j = n if j < 0 else j
            toks.append(line[i + 1:j]); i = j + 1
        else:
            j = i
            while j < n and line[j] not in " \t":
                j += 1
            toks.append(line[i:j]); i = j
    return toks


class Node:
    __slots__ = ("tokens", "children", "file")

    def __init__(self, t, f=""):
        self.tokens, self.children, self.file = t, [], f

    def get(self, key):
        for c in self.children:
            if c.tokens and c.tokens[0] == key:
                return c

    def all(self, key):
        return [c for c in self.children if c.tokens and c.tokens[0] == key]


def parse_dir(d):
    out = []
    for dp, _, fs in os.walk(d):
        if "_deprecated" in dp:
            continue
        for f in sorted(fs):
            if not f.endswith(".txt"):
                continue
            rel = os.path.relpath(os.path.join(dp, f), d)
            root = Node([]); stack = [(-1, root)]
            for raw in open(os.path.join(dp, f), encoding="utf-8"):
                line = raw.rstrip("\n")
                if not line.strip() or line.lstrip().startswith("#"):
                    continue
                depth = len(line) - len(line.lstrip("\t"))
                t = tokenize(line)
                if not t:
                    continue
                node = Node(t, rel)
                while stack[-1][0] >= depth:
                    stack.pop()
                stack[-1][1].children.append(node); stack.append((depth, node))
            out.extend(root.children)
    return out


def num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return 0.0


# ---------- main ----------
def main():
    nodes = parse_dir(data_dir())
    by = {}
    for n in nodes:
        if len(n.tokens) >= 2:
            by.setdefault(n.tokens[0], {}).setdefault(n.tokens[1], []).append(n)

    def first(kind, name):
        lst = by.get(kind, {}).get(name)
        return lst[0] if lst else None

    # outfits: attributes are direct children "key value"
    outfits = {}
    for name, lst in by.get("outfit", {}).items():
        o = lst[0]
        a = {}
        for c in o.children:
            if len(c.tokens) >= 2 and c.tokens[0] not in ("description", "thumbnail", "sprite", "sound", "flare sprite", "flare sound"):
                a[c.tokens[0]] = num(c.tokens[1]) if re.fullmatch(r"-?[\d.]+", c.tokens[1]) else c.tokens[1]
        outfits[name] = {"node": o, "attr": a}

    # shipyards / outfitters (base definitions, merged)
    def stock(kind):
        res = {}
        for name, lst in by.get(kind, {}).items():
            items = []
            for n in lst:
                items += [c.tokens[0] for c in n.children if c.tokens and c.tokens[0] != "remove"]
            res[name] = items
        return res
    shipyards, outfitters = stock("shipyard"), stock("outfitter")

    # planets -> system
    planet_sys = {}

    def walk_objects(node, sysname):
        for c in node.all("object"):
            if len(c.tokens) >= 2:
                planet_sys[c.tokens[1]] = sysname
            walk_objects(c, sysname)

    systems = {}
    for name, lst in by.get("system", {}).items():
        s = lst[0]
        walk_objects(s, name)
        g = s.get("government")
        systems[name] = {"node": s, "gov": g.tokens[1] if g else "", "links": [c.tokens[1] for c in s.all("link")],
                         "trade": {c.tokens[1]: num(c.tokens[2]) for c in s.all("trade") if len(c.tokens) >= 3},
                         "hidden": any(c.tokens[0] in ("hidden", "shrouded", "inaccessible") for c in s.children)}
    planet_info = {}
    for name, lst in by.get("planet", {}).items():
        p = lst[0]
        planet_info[name] = {"spaceport": p.get("spaceport") is not None,
                             "shipyards": [c.tokens[1] for c in p.all("shipyard") if len(c.tokens) > 1],
                             "outfitters": [c.tokens[1] for c in p.all("outfitter") if len(c.tokens) > 1],
                             "system": planet_sys.get(name, "")}
    market_systems = {pi["system"] for pi in planet_info.values() if pi["spaceport"] and pi["system"]}

    def where_sold(item, kind):
        lists = shipyards if kind == "ship" else outfitters
        names = {k for k, v in lists.items() if item in v}
        locs = sorted({pi["system"] for pn, pi in planet_info.items() if set(pi["shipyards" if kind == "ship" else "outfitters"]) & names and pi["system"]})
        return locs

    # ---------- ships ----------
    sold_ships = {s for v in shipyards.values() for s in v}
    ships = []
    for name in sorted(sold_ships):
        sn = first("ship", name)
        if not sn or len(sn.tokens) > 2:  # variants have a 3rd token
            continue
        at = sn.get("attributes")
        if not at:
            continue
        a = {c.tokens[0]: (num(c.tokens[1]) if len(c.tokens) > 1 and re.fullmatch(r"-?[\d.]+", c.tokens[1]) else (c.tokens[1] if len(c.tokens) > 1 else "")) for c in at.children}
        mass, thrust, turn, cost, ospace = num(a.get("mass")), 0.0, 0.0, num(a.get("cost")), num(a.get("outfit space"))
        oc = sn.get("outfits")
        if oc:
            for c in oc.children:
                o = outfits.get(c.tokens[0])
                if not o:
                    continue
                k = int(num(c.tokens[1])) if len(c.tokens) > 1 else 1
                oa = o["attr"]
                mass += k * num(oa.get("mass")); thrust += k * num(oa.get("thrust")); turn += k * num(oa.get("turn"))
                cost += k * num(oa.get("cost")); ospace += k * num(oa.get("outfit space"))
        lic_node = at.get("licenses")
        lic = [c.tokens[0] for c in lic_node.children] if lic_node else []
        drag = num(a.get("drag")) or 1
        faction = sn.file.split("/")[0] if "/" in sn.file else "other"
        ships.append({"name": name, "faction": faction, "category": a.get("category", ""), "price": round(cost),
                      "hull_cost": round(num(a.get("cost"))), "shields": round(num(a.get("shields"))), "hull": round(num(a.get("hull"))),
                      "cargo": round(num(a.get("cargo space"))), "crew": round(num(a.get("required crew"))), "bunks": round(num(a.get("bunks"))),
                      "fuel": round(num(a.get("fuel capacity"))), "free_space": round(ospace),
                      "speed": round(60 * thrust / min(drag, mass), 1) if thrust and mass else 0,
                      "accel": round(3600 * thrust / mass, 1) if thrust and mass else 0,
                      "turn": round(60 * turn / mass, 1) if turn and mass else 0,
                      "licenses": lic, "where": where_sold(name, "ship")})

    # ---------- weapons ----------
    def wnode(name):
        o = outfits.get(name)
        return o["node"].get("weapon") if o else None

    def wstats(w, depth=0):
        if w is None or depth > 5:
            return 0.0, 0.0, 0.0
        g = {c.tokens[0]: num(c.tokens[1]) for c in w.children if len(c.tokens) >= 2 and re.fullmatch(r"-?[\d.]+", c.tokens[1])}
        sd, hd = g.get("shield damage", 0), g.get("hull damage", 0)
        rng = g.get("velocity", 0) * g.get("lifetime", 0)
        sub_r = 0.0
        for c in w.all("submunition"):
            k = num(c.tokens[2]) if len(c.tokens) > 2 else 1
            s2, h2, r2 = wstats(wnode(c.tokens[1]), depth + 1)
            sd += k * s2; hd += k * h2; sub_r = max(sub_r, r2)
        return sd, hd, rng + sub_r

    weapons = []
    sold_outfits = {o for v in outfitters.values() for o in v}
    for name in sorted(sold_outfits):
        o = outfits.get(name)
        if not o:
            continue
        cat = o["attr"].get("category", "")
        if cat not in ("Guns", "Turrets", "Secondary Weapons"):
            continue
        w = o["node"].get("weapon")
        if w is None:
            continue
        g = {c.tokens[0]: num(c.tokens[1]) for c in w.children if len(c.tokens) >= 2 and re.fullmatch(r"-?[\d.]+", c.tokens[1])}
        reload = g.get("reload", 1) or 1
        sd, hd, rng = wstats(w)
        per_s = 60 / reload
        ammo = w.get("ammo")
        weapons.append({"name": name, "category": cat, "faction": o["node"].file.split("/")[0] if "/" in o["node"].file else "other",
                        "cost": round(num(o["attr"].get("cost"))), "space": round(-num(o["attr"].get("outfit space"))),
                        "shield_dps": round(sd * per_s, 1), "hull_dps": round(hd * per_s, 1), "range": round(rng),
                        "energy_s": round(g.get("firing energy", 0) * per_s, 1), "heat_s": round(g.get("firing heat", 0) * per_s, 1),
                        "ammo": ammo.tokens[1] if ammo and len(ammo.tokens) > 1 else "", "where": where_sold(name, "outfit")})

    # ---------- trade ----------
    routes = []
    for a_name, A in systems.items():
        if a_name not in market_systems or A["hidden"] or A["gov"] not in HUMAN_GOV:
            continue
        for b_name in A["links"]:
            B = systems.get(b_name)
            if not B or b_name not in market_systems or B["hidden"] or B["gov"] not in HUMAN_GOV or b_name < a_name:
                continue
            common = set(A["trade"]) & set(B["trade"])
            if not common:
                continue
            ab = max(common, key=lambda c: B["trade"][c] - A["trade"][c])
            ba = max(common, key=lambda c: A["trade"][c] - B["trade"][c])
            p_ab, p_ba = B["trade"][ab] - A["trade"][ab], A["trade"][ba] - B["trade"][ba]
            routes.append({"a": a_name, "b": b_name, "ab": ab, "ab_profit": round(p_ab), "ba": ba, "ba_profit": round(p_ba),
                           "round": round(max(p_ab, 0) + max(p_ba, 0)), "gov": f"{A['gov']} / {B['gov']}"})
    routes.sort(key=lambda r: -r["round"])

    # ---------- starter ships (New Boston "Basic Ships") ----------
    start = first("start", "default")
    start_planet = start.get("planet").tokens[1] if start and start.get("planet") else "New Boston"
    acct = start.get("account") if start else None
    credits = num(acct.get("credits").tokens[1]) if acct and acct.get("credits") else 0
    start_yards = planet_info.get(start_planet, {}).get("shipyards", [])
    starter_names = [s for y in start_yards for s in shipyards.get(y, [])]
    starter = [s for s in ships if s["name"] in starter_names]

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump({"meta": {"repo": REPO, "commit": COMMIT, "date": COMMIT_DATE, "start_planet": start_planet, "start_credits": credits},
                   "ships": ships, "weapons": weapons, "routes": routes[:60], "starter": [s["name"] for s in starter]}, f, ensure_ascii=False, indent=1)

    e = html.escape
    FAC = {"human": ("Human", "人類"), "hai": ("Hai", "ハイ"), "korath": ("Korath", "コラス"), "wanderer": ("Wanderer", "ワンダラー"),
           "coalition": ("Coalition", "連合"), "remnant": ("Remnant", "レムナント"), "quarg": ("Quarg", "クアーグ"), "pug": ("Pug", "パグ"),
           "drak": ("Drak", "ドラク"), "avgi": ("Avgi", "アヴギ"), "bunrodea": ("Bunrodea", "ブンロデア"), "gegno": ("Gegno", "ゲグノ"),
           "successors": ("Successors", "サクセサーズ"), "kahet": ("Ka'het", "カヘット"), "incipias": ("Incipias", "インシピアス"),
           "rulei": ("Rulei", "ルレイ"), "sheragi": ("Sheragi", "シェラギ"), "iije": ("Iije", "イージェ"), "vyrmeid": ("Vyrmeid", "ヴィルメイド")}

    def fac(f, lang):
        return FAC.get(f, (f.capitalize(), f.capitalize()))[0 if lang == "en" else 1]

    def where(lst, lang, limit=4):
        if not lst:
            return "—"
        more = len(lst) - limit
        s = ", ".join(lst[:limit])
        return e(s) + ((f" +{more} more" if lang == "en" else f" ほか{more}") if more > 0 else "")

    def tbl(head, rows):
        h = "".join(f"<th>{x}</th>" for x in head)
        return f'<div class="table-scroll"><table class="glossary"><thead><tr>{h}</tr></thead><tbody>\n' + "\n".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows) + "\n</tbody></table></div>"

    def ship_rows(lang, lst):
        head = (["Ship", "Category", "Price (as sold)", "Shields", "Hull", "Cargo", "Crew / bunks", "Free outfit space", "Max speed", "Accel.", "Turning", "Where sold"] if lang == "en"
                else ["船", "分類", "価格（販売時）", "シールド", "船体", "貨物", "必要乗員／寝台", "空き装備スペース", "最高速度", "加速", "旋回", "販売場所（星系）"])
        rows = [[f"<b>{e(s['name'])}</b>", e(s["category"]), f"{s['price']:,}", f"{s['shields']:,}", f"{s['hull']:,}", s["cargo"], f"{s['crew']} / {s['bunks']}",
                 s["free_space"], s["speed"] or "—", s["accel"] or "—", s["turn"] or "—", where(s["where"], lang)] for s in lst]
        return tbl(head, rows)

    def ships_all(lang):
        out = []
        order = ["human"] + sorted({s["faction"] for s in ships} - {"human"})
        for f in order:
            lst = sorted([s for s in ships if s["faction"] == f], key=lambda s: s["price"])
            if not lst:
                continue
            out.append(f'<h3 style="margin:22px 0 8px;">{e(fac(f, lang))} ({len(lst)})</h3>')
            out.append(ship_rows(lang, lst))
        return "\n".join(out)

    def weapons_all(lang):
        out = []
        CAT = {"Guns": ("Guns (fixed)", "固定砲"), "Turrets": ("Turrets", "砲塔"), "Secondary Weapons": ("Secondary weapons (ammo)", "副兵装（弾薬式）")}
        for cat in ("Guns", "Turrets", "Secondary Weapons"):
            for f in ["human"] + sorted({w["faction"] for w in weapons} - {"human"}):
                lst = sorted([w for w in weapons if w["category"] == cat and w["faction"] == f], key=lambda w: w["cost"])
                if not lst:
                    continue
                out.append(f'<h3 style="margin:22px 0 8px;">{CAT[cat][0 if lang == "en" else 1]} — {e(fac(f, lang))}</h3>')
                head = (["Weapon", "Cost", "Space", "Shield DPS", "Hull DPS", "Range", "Energy/s", "Heat/s", "Ammo", "Where sold"] if lang == "en"
                        else ["武器", "価格", "スペース", "対シールドDPS", "対船体DPS", "射程", "エネルギー/秒", "熱/秒", "弾薬", "販売場所（星系）"])
                rows = [[f"<b>{e(w['name'])}</b>", f"{w['cost']:,}", w["space"], w["shield_dps"], w["hull_dps"], w["range"] or "—", w["energy_s"], w["heat_s"], e(w["ammo"]) or "—", where(w["where"], lang, 3)] for w in lst]
                out.append(tbl(head, rows))
        return "\n".join(out)

    def trade_rows(lang):
        head = (["#", "Route", "Buy here → sell there", "Profit/ton", "Return cargo", "Profit/ton", "Round trip/ton", "Governments"] if lang == "en"
                else ["#", "ルート", "行き（ここで買ってあちらで売る）", "利益/トン", "帰りの積み荷", "利益/トン", "往復の利益/トン", "政府"])
        rows = []
        for i, r in enumerate(routes[:40], 1):
            rows.append([i, f"<b>{e(r['a'])} ⇄ {e(r['b'])}</b>", e(r["ab"]) + f" ({e(r['a'])} → {e(r['b'])})", r["ab_profit"],
                         e(r["ba"]) if r["ba_profit"] > 0 else "—", r["ba_profit"] if r["ba_profit"] > 0 else "—", f"<b>{r['round']}</b>", e(r["gov"])])
        return tbl(head, rows)

    def starter_rows(lang):
        return ship_rows(lang, sorted(starter, key=lambda s: s["price"]))

    # ---------- other outfits ----------
    def series(name):
        o = outfits[name]["node"].get("series")
        return o.tokens[1] if o and len(o.tokens) > 1 else ""

    def per_s(a, k):
        return round(60 * num(a.get(k)), 1)

    OUTCATS = [
        ("Engines (thrust)", "エンジン（推力）", lambda n, a: a.get("category") == "Engines" and num(a.get("thrust")) > 0,
         ["Thrust", "Thrust / space", "Energy/s", "Heat/s"], ["推力", "スペースあたり推力", "エネルギー/秒", "熱/秒"],
         lambda a: [round(num(a.get("thrust")), 2), round(num(a.get("thrust")) / max(1, -num(a.get("outfit space"))), 3), per_s(a, "thrusting energy"), per_s(a, "thrusting heat")]),
        ("Engines (steering)", "エンジン（旋回）", lambda n, a: a.get("category") == "Engines" and num(a.get("turn")) > 0 and not num(a.get("thrust")),
         ["Turn", "Turn / space", "Energy/s", "Heat/s"], ["旋回力", "スペースあたり旋回力", "エネルギー/秒", "熱/秒"],
         lambda a: [round(num(a.get("turn")), 1), round(num(a.get("turn")) / max(1, -num(a.get("outfit space"))), 2), per_s(a, "turning energy"), per_s(a, "turning heat")]),
        ("Generators", "発電機", lambda n, a: a.get("category") == "Power" and num(a.get("energy generation")) > 0,
         ["Energy/s", "Energy/s per space", "Heat/s", "Battery"], ["エネルギー/秒", "スペースあたりエネルギー/秒", "熱/秒", "蓄電"],
         lambda a: [per_s(a, "energy generation"), round(60 * num(a.get("energy generation")) / max(1, -num(a.get("outfit space"))), 2), per_s(a, "heat generation"), round(num(a.get("energy capacity")))]),
        ("Batteries", "バッテリー", lambda n, a: a.get("category") == "Power" and num(a.get("energy capacity")) > 0 and not num(a.get("energy generation")),
         ["Energy capacity", "Capacity / space", "—", "—"], ["蓄電量", "スペースあたり蓄電量", "—", "—"],
         lambda a: [round(num(a.get("energy capacity"))), round(num(a.get("energy capacity")) / max(1, -num(a.get("outfit space"))), 1), "—", "—"]),
        ("Shield generators", "シールド発生装置", lambda n, a: num(a.get("shield generation")) > 0,
         ["Shield/s", "Shield/s per space", "Energy/s", "Heat/s"], ["シールド回復/秒", "スペースあたり回復/秒", "エネルギー/秒", "熱/秒"],
         lambda a: [per_s(a, "shield generation"), round(60 * num(a.get("shield generation")) / max(1, -num(a.get("outfit space"))), 2), per_s(a, "shield energy"), per_s(a, "shield heat")]),
        ("Cooling", "冷却", lambda n, a: num(a.get("cooling")) > 0 or num(a.get("active cooling")) > 0,
         ["Cooling/s", "Cooling/s per space", "Energy/s (active)", "—"], ["冷却/秒", "スペースあたり冷却/秒", "エネルギー/秒（能動）", "—"],
         lambda a: [round(60 * (num(a.get("cooling")) + num(a.get("active cooling"))), 1), round(60 * (num(a.get("cooling")) + num(a.get("active cooling"))) / max(1, -num(a.get("outfit space"))), 2), per_s(a, "cooling energy"), "—"]),
    ]

    def outfits_all(lang):
        res = []
        for en_t, ja_t, pred, h_en, h_ja, vals in OUTCATS:
            lst = [n for n in sorted(sold_outfits) if n in outfits and pred(n, outfits[n]["attr"])]
            human = [n for n in lst if outfits[n]["node"].file.startswith("human/")]
            other = [n for n in lst if n not in human]
            for grp, names in (("human", human), ("other", other)):
                if not names:
                    continue
                label = (en_t if lang == "en" else ja_t) + (" — " + ("Human" if lang == "en" else "人類") if grp == "human" else " — " + ("Alien" if lang == "en" else "異星"))
                res.append(f'<h3 style="margin:22px 0 8px;">{label} ({len(names)})</h3>')
                head = (["Outfit", "Cost", "Space"] + h_en + ["Where sold"]) if lang == "en" else (["装備", "価格", "スペース"] + h_ja + ["販売場所（星系）"])
                rows = []
                for n in sorted(names, key=lambda n: num(outfits[n]["attr"].get("cost"))):
                    a = outfits[n]["attr"]
                    rows.append([f"<b>{e(n)}</b>", f"{round(num(a.get('cost'))):,}", round(-num(a.get("outfit space")))] + vals(a) + [where(where_sold(n, "outfit"), lang, 3)])
                res.append(tbl(head, rows))
        return "\n".join(res)

    # ---------- licenses ----------
    grants = {}
    def scan(node, mname):
        for c in node.children:
            if len(c.tokens) >= 2 and c.tokens[0] == "set" and c.tokens[1].startswith("license: "):
                grants.setdefault(c.tokens[1][9:], set()).add(mname)
            scan(c, mname)
    for mname, lst in by.get("mission", {}).items():
        if "_deprecated" in lst[0].file:
            continue
        for m in lst:
            scan(m, mname)
    for st_name, lst in by.get("start", {}).items():
        for m in lst:
            for c in m.children:
                if len(c.tokens) >= 2 and c.tokens[0] == "set" and c.tokens[1].startswith("license: "):
                    grants.setdefault(c.tokens[1][9:], set()).add(f"(start: {st_name})")
    out_lic = {}
    for n, o in outfits.items():
        ln = o["node"].get("licenses")
        if ln:
            for c in ln.children:
                out_lic.setdefault(c.tokens[0], []).append(n)
    ship_lic = {}
    for sh in ships:
        for l in sh["licenses"]:
            ship_lic.setdefault(l, []).append(sh["name"])

    def license_rows(lang):
        names = sorted(set(ship_lic) | set(out_lic) | set(grants))
        rows = []
        for l in names:
            sh = sorted(ship_lic.get(l, [])); ou = sorted(n for n in out_lic.get(l, []) if n in sold_outfits)
            gr = sorted(grants.get(l, []))
            if not sh and not ou:
                continue
            fmt = lambda xs, k=6: (e(", ".join(xs[:k])) + ((f" +{len(xs) - k} more" if lang == "en" else f" ほか{len(xs) - k}") if len(xs) > k else "")) if xs else "—"
            lo = f"{l} License"
            buy = ""
            if lo in sold_outfits and lo in outfits:
                cost = round(num(outfits[lo]["attr"].get("cost")))
                buy = (f"Buy for {cost:,} at outfitters in " if lang == "en" else f"装備屋で{cost:,}クレジットで購入：") + where(where_sold(lo, "outfit"), lang, 3)
            how = " / ".join(x for x in (buy, (("Missions: " if lang == "en" else "ミッション：") + fmt(gr, 4)) if gr else "") if x)
            if not how:
                how = "No way to get it found in the data" if lang == "en" else "データ上に入手方法が見つからない"
            rows.append([f"<b>{e(l)}</b>", fmt(sh), fmt(ou), how])
        head = (["License", "Ships that need it", "Outfits that need it", "How to get it (from the data)"] if lang == "en"
                else ["免許", "必要な船", "必要な装備", "入手方法（データより）"])
        return tbl(head, rows)

    for key, fn in (("ships", ships_all), ("weapons", weapons_all), ("trade", trade_rows), ("starter", starter_rows), ("outfits", outfits_all), ("licenses", license_rows)):
        marker = "ES-" + key.upper()
        for lang, rel in PAGES[key].items():
            p = os.path.join(ROOT, rel)
            if not os.path.exists(p):
                print("skip (no page yet):", rel); continue
            s = open(p, encoding="utf-8").read()
            new = f"<!-- {marker} -->\n{fn(lang)}\n<!-- /{marker} -->"
            s2, n = re.subn(rf"<!-- {marker} -->.*?<!-- /{marker} -->", lambda m: new, s, flags=re.S)
            if n != 1:
                sys.exit(f"marker {marker} not found once in {rel}")
            open(p, "w", encoding="utf-8").write(s2)
            print("wrote", rel)
    print(f"ships={len(ships)} weapons={len(weapons)} routes={len(routes)} starter={[s['name'] for s in starter]} credits={credits}")


if __name__ == "__main__":
    main()
