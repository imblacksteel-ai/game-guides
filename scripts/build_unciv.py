#!/usr/bin/env python3
"""
Unciv（オープンソース版シヴィライゼーション5）の文明・ユニット表を生成し、英日ページの
<!-- UNCIV-CIVS --> / <!-- UNCIV-UNITS --> マーカー間に書き込む（冪等）。

出典: 本体リポジトリ yairm210/Unciv（MPL-2.0）の COMMIT 時点
  android/assets/jsons/Civ V - Gods & Kings/{Nations,Units,Buildings,Techs}.json
  android/assets/jsons/translations/Japanese.properties … ゲーム内の公式日本語訳
JSONはコメント・末尾カンマ入りの緩い形式なので strip() で通常のJSONにしてから読む。
日本語訳は Unciv と同じく「[ ]内を差し替えるテンプレート」で引き、条件 <...> は本文の前に置く
（Japanese.properties の ConditionalsPlacement = before に合わせる）。訳が無いものは英語のまま残し、件数を表示する。

使い方: python3 scripts/build_unciv.py            （COMMIT を取得）
        UNCIV_DIR=/path/to/Unciv python3 scripts/build_unciv.py   （手元のクローンを使う）
"""
import html
import json
import os
import re
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = "yairm210/Unciv"
COMMIT = "31524beafbfdbcc6e07b5ca54d0b28fbe361e0dd"  # 2026-10-02
COMMIT_DATE = "2026-10-02"
RULESET = "android/assets/jsons/Civ V - Gods & Kings"
TRANS = "android/assets/jsons/translations/Japanese.properties"
PAGES = {
    "civs": {"en": "games/unciv/civilizations/index.html", "ja": "ja/games/unciv/civilizations/index.html"},
    "units": {"en": "games/unciv/units/index.html", "ja": "ja/games/unciv/units/index.html"},
    "diff": {"en": "games/unciv/difficulty/index.html", "ja": "ja/games/unciv/difficulty/index.html"},
    "policies": {"en": "games/unciv/policies/index.html", "ja": "ja/games/unciv/policies/index.html"},
    "wonders": {"en": "games/unciv/wonders/index.html", "ja": "ja/games/unciv/wonders/index.html"},
    "techs": {"en": "games/unciv/tech-tree/index.html", "ja": "ja/games/unciv/tech-tree/index.html"},
    "beliefs": {"en": "games/unciv/beliefs/index.html", "ja": "ja/games/unciv/beliefs/index.html"},
    "buildings": {"en": "games/unciv/buildings/index.html", "ja": "ja/games/unciv/buildings/index.html"},
    "promotions": {"en": "games/unciv/promotions/index.html", "ja": "ja/games/unciv/promotions/index.html"},
    "terrain": {"en": "games/unciv/terrain/index.html", "ja": "ja/games/unciv/terrain/index.html"},
    "citystates": {"en": "games/unciv/city-states/index.html", "ja": "ja/games/unciv/city-states/index.html"},
    "greatpeople": {"en": "games/unciv/great-people/index.html", "ja": "ja/games/unciv/great-people/index.html"},
    "growth": {"en": "games/unciv/growth-happiness/index.html", "ja": "ja/games/unciv/growth-happiness/index.html"},
    "speeds": {"en": "games/unciv/game-speed/index.html", "ja": "ja/games/unciv/game-speed/index.html"},
    "ruins": {"en": "games/unciv/opening/index.html", "ja": "ja/games/unciv/opening/index.html"},
    "victory": {"en": "games/unciv/victory/index.html", "ja": "ja/games/unciv/victory/index.html"},
}
STATS = ["food", "production", "gold", "science", "culture", "faith", "happiness"]
SKIP_UNIQUE = ("for AI decisions", "leader title", "global alert", "map editor", "generate naturally", "Map Generation", "start locations", "Comment", "hidden from users", "Never destroyed", "Indicates the capital")
OUT = {"civs": os.path.join(ROOT, "assets/data/unciv-civs.json"),
       "units": os.path.join(ROOT, "assets/data/unciv-units.json")}


def fetch(path):
    local = os.environ.get("UNCIV_DIR")
    if local:
        with open(os.path.join(local, path), encoding="utf-8") as f:
            return f.read()
    url = f"https://raw.githubusercontent.com/{REPO}/{COMMIT}/" + urllib.request.quote(path)
    req = urllib.request.Request(url, headers={"User-Agent": "kouryakulab-build"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode("utf-8")


def strip(s):
    out, i, n, ins = [], 0, len(s), False
    while i < n:
        c = s[i]
        if ins:
            out.append(c)
            if c == "\\":
                out.append(s[i + 1]); i += 2; continue
            if c == '"':
                ins = False
            i += 1; continue
        if c == '"':
            ins = True; out.append(c); i += 1; continue
        if s.startswith("//", i):
            j = s.find("\n", i); i = n if j < 0 else j; continue
        if s.startswith("/*", i):
            j = s.find("*/", i); i = n if j < 0 else j + 2; continue
        out.append(c); i += 1
    return re.sub(r",(\s*[\]}])", r"\1", "".join(out))


def load(name):
    return json.loads(strip(fetch(f"{RULESET}/{name}")))


# ---------- translation ----------
class Tr:
    def __init__(self, text):
        self.exact, self.tmpl = {}, {}
        for line in text.splitlines():
            if not line or line.startswith("#") or " = " not in line:
                continue
            k, v = line.split(" = ", 1)
            v = v.strip()
            if not v:
                continue
            self.exact[k] = v
            if "[" in k:
                self.tmpl[re.sub(r"\[[^\]]*\]", "[]", k)] = (k, v)
        self.missing = set()

    @staticmethod
    def split_params(s):
        """Top-level [..] params, allowing nested brackets."""
        params, depth, cur = [], 0, ""
        body = ""
        for ch in s:
            if ch == "[":
                if depth == 0:
                    cur = ""; body += "[]"
                else:
                    cur += ch
                depth += 1
            elif ch == "]":
                depth -= 1
                if depth == 0:
                    params.append(cur)
                else:
                    cur += ch
            elif depth > 0:
                cur += ch
            else:
                body += ch
        return body, params

    # パラメータとして使われたときだけ訳語を差し替える（"Land" が「領土」になる等の誤訳対策）
    PARAM_OVERRIDE = {"Land": "地上", "Water": "水上", "Strategic": "戦略"}

    def word(self, s):
        if s in self.PARAM_OVERRIDE:
            return self.PARAM_OVERRIDE[s]
        if s in self.exact:
            return self.exact[s]
        if re.fullmatch(r"[+-]?\d+(\.\d+)?%?", s):
            return s
        if s.startswith("{") and s.endswith("}"):  # {Military} {Land}
            parts = re.findall(r"\{([^}]*)\}", s)
            return "".join(self.word(p) for p in parts)
        if "[" in s:
            return self.sentence(s)
        if ", " in s and all(re.fullmatch(r"[+-]?\d+ .+", x) for x in s.split(", ")):  # "+1 Gold, +1 Happiness"
            return "・".join(self.word(x) for x in s.split(", "))
        m = re.fullmatch(r"([+-]?\d+) (.+)", s)  # "+2 Culture"
        if m and m.group(2) in self.exact:
            return f"{self.exact[m.group(2)]}{m.group(1)}"
        self.missing.add(s)
        return s

    def sentence(self, s):
        if s in self.exact:
            return self.exact[s]
        body, params = self.split_params(s)
        hit = self.tmpl.get(body)
        if not hit:
            self.missing.add(s)
            return None
        key, val = hit
        names = re.findall(r"\[([^\]]*)\]", key)
        out = val
        for name, p in zip(names, params):
            out = out.replace(f"[{name}]", self.word(p), 1)
        return out

    def unique(self, u):
        conds = re.findall(r"<([^>]*)>", u)
        main = re.sub(r"\s*<[^>]*>", "", u).strip()
        conds = [c for c in conds if not c.startswith("Suppress warning") and not c.startswith("hidden")]
        m = self.sentence(main) if "[" in main else self.exact.get(main)
        if m is None:
            self.missing.add(main)
            return None
        cs = []
        for c in conds:
            t = self.sentence(c) if "[" in c else self.exact.get(c)
            if t is None:
                self.missing.add(c)
                return None
            cs.append(t)
        return "、".join(cs) + ("、" if cs else "") + m


def clean_en(u):
    u = re.sub(r"\s*<Suppress warning[^>]*>", "", u)
    u = re.sub(r"[\[\]{}]", "", u)
    return u.replace("<", "(").replace(">", ")")


def main():
    nations, units, buildings, techs, diffs = (load(f) for f in ("Nations.json", "Units.json", "Buildings.json", "Techs.json", "Difficulties.json"))
    tr = Tr(fetch(TRANS))
    era_of, era_order = {}, []
    for col in techs:
        if col["era"] not in era_order:
            era_order.append(col["era"])
        for t in col["techs"]:
            era_of[t["name"]] = col["era"]
    ja = lambda s: tr.exact.get(s) or s

    civs = []
    for c in nations:
        if "cityStateType" in c or c["name"] in ("Barbarians", "Spectator"):
            continue
        uu = [x for x in units if x.get("uniqueTo") == c["name"]]
        bb = [x for x in buildings if x.get("uniqueTo") == c["name"]]
        ab_ja = []
        for u in c["uniques"]:
            if u.startswith("Comment"):
                continue
            t = tr.unique(u)
            ab_ja.append(t if t else clean_en(u))
        civs.append({
            "name": c["name"], "name_ja": ja(c["name"]), "leader": c["leaderName"], "leader_ja": ja(c["leaderName"]),
            "ability": c["uniqueName"], "ability_ja": ja(c["uniqueName"]),
            "effects_en": [clean_en(u) for u in c["uniques"] if not u.startswith("Comment")], "effects_ja": ab_ja,
            "victory": c["preferredVictoryType"],
            "units": [{"name": x["name"], "name_ja": ja(x["name"]), "replaces": x.get("replaces"), "replaces_ja": ja(x.get("replaces") or "")} for x in uu],
            "buildings": [{"name": x["name"], "name_ja": ja(x["name"]), "replaces": x.get("replaces"), "replaces_ja": ja(x.get("replaces") or "")} for x in bb],
        })

    ulist = []
    for x in units:
        if x["unitType"] == "Civilian" and x["name"] not in ("Settler", "Worker", "Work Boats"):
            continue
        if x.get("uniqueTo") == "Barbarians":
            continue
        tech = x.get("requiredTech")
        ulist.append({
            "name": x["name"], "name_ja": ja(x["name"]), "type": x["unitType"], "type_ja": ja(x["unitType"]),
            "era": era_of.get(tech, "Ancient era") if tech else "—", "tech": tech or "—", "tech_ja": ja(tech) if tech else "—",
            "strength": x.get("strength", 0), "ranged": x.get("rangedStrength", 0), "range": x.get("range", 2 if x.get("rangedStrength") else 0),
            "move": x["movement"], "cost": x.get("cost", 0), "resource": x.get("requiredResource", ""),
            "resource_ja": ja(x.get("requiredResource", "")) if x.get("requiredResource") else "",
            "upgrades": x.get("upgradesTo", ""), "upgrades_ja": ja(x.get("upgradesTo", "")) if x.get("upgradesTo") else "",
            "unique_to": x.get("uniqueTo", ""), "unique_to_ja": ja(x.get("uniqueTo", "")) if x.get("uniqueTo") else "",
            "replaces": x.get("replaces", ""),
        })
    ulist.sort(key=lambda u: (era_order.index(u["era"]) if u["era"] in era_order else 99, u["cost"], u["name"]))

    meta = {"repo": REPO, "commit": COMMIT, "date": COMMIT_DATE, "ruleset": "Civ V - Gods & Kings"}
    for k, data in (("civs", civs), ("units", ulist)):
        with open(OUT[k], "w", encoding="utf-8") as f:
            json.dump({"meta": meta, "data": data}, f, ensure_ascii=False, indent=1)

    e = html.escape
    era_ja = {x: ja(x) for x in era_order}

    def civ_rows(lang):
        rows = []
        for c in civs:
            if lang == "en":
                name = f"<b>{e(c['name'])}</b><br><span style='color:var(--ink-dim);font-size:.85rem'>{e(c['leader'])}</span>"
                ab = f"<b>{e(c['ability'])}</b><ul class='exped-notes' style='margin:4px 0 0'>" + "".join(f"<li>{e(x)}</li>" for x in c["effects_en"]) + "</ul>"
                uq = "<br>".join(f"{e(u['name'])} <span style='color:var(--ink-dim)'>({e(u['replaces'] or '—')})</span>" for u in c["units"] + c["buildings"])
                vic = e(c["victory"])
            else:
                name = f"<b>{e(c['name_ja'])}</b><br><span style='color:var(--ink-dim);font-size:.85rem'>{e(c['leader_ja'])}</span>"
                ab = f"<b>{e(c['ability_ja'])}</b><ul class='exped-notes' style='margin:4px 0 0'>" + "".join(f"<li>{e(x)}</li>" for x in c["effects_ja"]) + "</ul>"
                uq = "<br>".join(f"{e(u['name_ja'])} <span style='color:var(--ink-dim)'>（{e(u['replaces_ja'] or '—')}）</span>" for u in c["units"] + c["buildings"])
                vic = {"Scientific": "科学", "Cultural": "文化", "Diplomatic": "外交", "Domination": "制覇"}.get(c["victory"], c["victory"])
            rows.append(f"<tr><td>{name}</td><td>{ab}</td><td>{uq}</td><td>{vic}</td></tr>")
        head = ("<th>Civilization</th><th>Ability</th><th>Unique units &amp; buildings (replaces)</th><th>AI's preferred victory</th>" if lang == "en"
                else "<th>文明</th><th>能力</th><th>固有ユニット・建物（置き換え対象）</th><th>AIが目指す勝利</th>")
        return (f'<div class="table-scroll"><table class="glossary"><thead><tr>{head}</tr></thead><tbody>\n' + "\n".join(rows) + "\n</tbody></table></div>")

    def unit_rows(lang):
        out = []
        for era in era_order + ["—"]:
            us = [u for u in ulist if u["era"] == era]
            if not us:
                continue
            title = era if lang == "en" else era_ja.get(era, era)
            out.append(f'<h3 style="margin:22px 0 8px;">{e(title)}</h3>')
            head = ("<th>Unit</th><th>Type</th><th>Tech</th><th>Str</th><th>Ranged</th><th>Range</th><th>Move</th><th>Cost</th><th>Resource</th><th>Upgrades to</th>" if lang == "en"
                    else "<th>ユニット</th><th>種類</th><th>技術</th><th>戦闘力</th><th>遠隔</th><th>射程</th><th>移動</th><th>コスト</th><th>資源</th><th>アップグレード先</th>")
            rows = []
            for u in us:
                if lang == "en":
                    nm = e(u["name"]) + (f" <span style='color:var(--ink-dim);font-size:.82rem'>({e(u['unique_to'])}, replaces {e(u['replaces'])})</span>" if u["unique_to"] else "")
                    cells = [nm, e(u["type"]), e(u["tech"]), u["strength"] or "—", u["ranged"] or "—", u["range"] or "—", u["move"], u["cost"] or "—", e(u["resource"]) or "—", e(u["upgrades"]) or "—"]
                else:
                    nm = e(u["name_ja"]) + (f" <span style='color:var(--ink-dim);font-size:.82rem'>（{e(u['unique_to_ja'])}固有）</span>" if u["unique_to"] else "")
                    cells = [nm, e(u["type_ja"]), e(u["tech_ja"]), u["strength"] or "—", u["ranged"] or "—", u["range"] or "—", u["move"], u["cost"] or "—", e(u["resource_ja"]) or "—", e(u["upgrades_ja"]) or "—"]
                rows.append("<tr>" + "".join(f"<td>{c}</td>" for c in cells) + "</tr>")
            out.append(f'<div class="table-scroll"><table class="glossary"><thead><tr>{head}</tr></thead><tbody>\n' + "\n".join(rows) + "\n</tbody></table></div>")
        return "\n".join(out)

    base = {u["name"]: u for u in ulist}
    raw_unit = {x["name"]: x for x in units}
    promos = load("UnitPromotions.json")
    promo_of = {x["name"]: x for x in promos}

    def ul(items):
        return "<ul class='exped-notes' style='margin:0'>" + "".join(f"<li>{e(i)}</li>" for i in items) + "</ul>" if items else "—"

    def unit_abilities(name, base_name, lang):
        """Uniques and promotion effects the unique unit has that the replaced unit doesn't."""
        def effects(n):
            x = raw_unit.get(n, {})
            out = [u for u in x.get("uniques", []) if not any(k in u for k in ("Unbuildable", "Uncapturable"))]
            for pn in x.get("promotions", []):
                out += promo_of.get(pn, {}).get("uniques", [])
            return out
        mine, theirs = effects(name), set(effects(base_name))
        diff = [u for u in mine if u not in theirs and not any(k in u for k in SKIP_UNIQUE)]
        res = []
        for u in diff:
            if lang == "en":
                res.append(clean_en(u))
            else:
                t = tr.unique(u)
                res.append(t if t else clean_en(u))
        return res

    def uniq_rows(lang):
        rows = []
        for u in ulist:
            b = base.get(u["replaces"]) if u["unique_to"] else None
            if not b:
                continue
            def d(k):
                v = u[k] - b[k]
                return "±0" if v == 0 else (f"+{v}" if v > 0 else str(v))
            ab = unit_abilities(u["name"], b["name"], lang)
            if lang == "en":
                cells = [f"<b>{e(u['name'])}</b>", e(u["unique_to"]), e(b["name"]), d("strength"), d("ranged"), d("move"), d("cost"), ul(ab)]
            else:
                cells = [f"<b>{e(u['name_ja'])}</b>", e(u["unique_to_ja"]), e(b["name_ja"]), d("strength"), d("ranged"), d("move"), d("cost"), ul(ab)]
            rows.append("<tr>" + "".join(f"<td>{c}</td>" for c in cells) + "</tr>")
        head = ("<th>Unique unit</th><th>Civilization</th><th>Replaces</th><th>Strength</th><th>Ranged</th><th>Move</th><th>Cost</th><th>Extra abilities (vs the unit it replaces)</th>" if lang == "en"
                else "<th>固有ユニット</th><th>文明</th><th>置き換え対象</th><th>戦闘力</th><th>遠隔</th><th>移動</th><th>コスト</th><th>追加の能力（置き換え対象との差）</th>")
        return f'<div class="table-scroll"><table class="glossary"><thead><tr>{head}</tr></thead><tbody>\n' + "\n".join(rows) + "\n</tbody></table></div>"

    def pct(v):
        return f"{round(v * 100)}%"

    def diff_rows(lang):
        cols = [  # (key, en, ja, formatter)
            ("researchCostModifier", "Your tech cost", "あなたの研究コスト", pct),
            ("unitCostModifier", "Your unit cost", "あなたのユニットコスト", pct),
            ("buildingCostModifier", "Your building cost", "あなたの建物コスト", pct),
            ("policyCostModifier", "Your policy cost", "あなたの社会制度コスト", pct),
            ("baseHappiness", "Base happiness", "基本幸福度", str),
            ("unhappinessModifier", "Your unhappiness", "あなたの不満", pct),
            ("barbarianBonus", "Your bonus vs barbarians", "蛮族への戦闘ボーナス", lambda v: f"+{round(v * 100)}%"),
            ("aiCityGrowthModifier", "AI food needed to grow", "AIの成長に必要な食料", pct),
            ("aiUnitCostModifier", "AI unit cost", "AIのユニットコスト", pct),
            ("aiBuildingCostModifier", "AI building cost", "AIの建物コスト", pct),
            ("aiUnitSupplyModifier", "AI extra unit supply", "AIのユニット上限の上乗せ", lambda v: f"+{round(v * 100)}%"),
        ]
        head = "<th>" + ("Difficulty" if lang == "en" else "難易度") + "</th>" + "".join(f"<th>{c[1] if lang == 'en' else c[2]}</th>" for c in cols)
        rows = []
        for d in diffs:
            nm = d["name"] if lang == "en" else f"{ja(d['name'])}<br><span style='color:var(--ink-dim);font-size:.82rem'>{d['name']}</span>"
            rows.append("<tr><td><b>" + nm + "</b></td>" + "".join(f"<td>{c[3](d.get(c[0], 1 if 'Modifier' in c[0] else 0))}</td>" for c in cols) + "</tr>")
        t1 = f'<div class="table-scroll"><table class="glossary"><thead><tr>{head}</tr></thead><tbody>\n' + "\n".join(rows) + "\n</tbody></table></div>"
        r2 = []
        for d in diffs:
            units_ = d.get("aiMajorCivBonusStartingUnits") or []
            techs_ = d.get("aiFreeTechs") or []
            if lang == "en":
                u = ", ".join(x.replace("Era Starting Unit", "era starting unit") for x in units_) or "—"
                t = ", ".join(techs_) or "—"
                r2.append(f"<tr><td><b>{d['name']}</b></td><td>{e(u)}</td><td>{e(t)}</td></tr>")
            else:
                u = "、".join(("時代の初期軍事ユニット" if x == "Era Starting Unit" else ja(x)) for x in units_) or "—"
                t = "、".join(ja(x) for x in techs_) or "—"
                r2.append(f"<tr><td><b>{ja(d['name'])}</b></td><td>{e(u)}</td><td>{e(t)}</td></tr>")
        h2 = ("<th>Difficulty</th><th>Extra starting units for each AI civ</th><th>Free techs for AI</th>" if lang == "en"
              else "<th>難易度</th><th>AI文明が追加で持つ初期ユニット</th><th>AIが最初から持つ技術</th>")
        t2 = f'<div class="table-scroll" style="margin-top:14px"><table class="glossary"><thead><tr>{h2}</tr></thead><tbody>\n' + "\n".join(r2) + "\n</tbody></table></div>"
        return t1 + "\n" + t2

    # ---------- policies / wonders / techs / beliefs ----------
    policies, beliefs, imps, ress = (load(f) for f in ("Policies.json", "Beliefs.json", "TileImprovements.json", "TileResources.json"))
    col_of = {}
    for col in techs:
        for t in col["techs"]:
            col_of[t["name"]] = col

    def uq(lst, lang):
        out = []
        for u in lst or []:
            if any(k in u for k in SKIP_UNIQUE):
                continue
            if lang == "en":
                out.append(clean_en(u))
            else:
                t = tr.unique(u)
                out.append(t if t else clean_en(u))
        return out

    def stats(x, lang):
        out = []
        for k in STATS:
            v = x.get(k)
            if v:
                name = k.capitalize()
                out.append(f"+{v:g} {name}" if lang == "en" else f"{ja(name)}+{v:g}")
        for k, v in (x.get("percentStatBonus") or {}).items():
            name = k.capitalize()
            out.append(f"+{v:g}% {name}" if lang == "en" else f"{ja(name)}+{v:g}%")
        for sp, v in (x.get("specialistSlots") or {}).items():
            out.append(f"+{v} {sp} slot" + ("s" if v > 1 else "") if lang == "en" else f"{ja(sp)}の枠+{v}")
        if x.get("cityStrength"):
            out.append(f"+{x['cityStrength']:g} city defense" if lang == "en" else f"都市の防御力+{x['cityStrength']:g}")
        if x.get("cityHealth"):
            out.append(f"+{x['cityHealth']:g} city HP" if lang == "en" else f"都市の耐久力+{x['cityHealth']:g}")
        for gp, v in (x.get("greatPersonPoints") or {}).items():
            out.append(f"+{v} {gp} points" if lang == "en" else f"{ja(gp)}ポイント+{v}")
        return out

    def ul(items):
        return "<ul class='exped-notes' style='margin:0'>" + "".join(f"<li>{e(i)}</li>" for i in items) + "</ul>" if items else "—"

    def tbl(head, rows, extra=""):
        h = "".join(f"<th>{x}</th>" for x in head)
        return f'<div class="table-scroll"{extra}><table class="glossary"><thead><tr>{h}</tr></thead><tbody>\n' + "\n".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows) + "\n</tbody></table></div>"

    VIC = ["Scientific", "Cultural", "Diplomatic", "Domination"]
    VIC_JA = {"Scientific": "科学", "Cultural": "文化", "Diplomatic": "外交", "Domination": "制覇", "Neutral": "中立"}

    def policy_rows(lang):
        out = []
        for br in policies:
            era = br.get("era", "")
            title = f"{br['name']} <span style='color:var(--ink-dim);font-size:.85rem'>({era})</span>" if lang == "en" else f"{ja(br['name'])} <span style='color:var(--ink-dim);font-size:.85rem'>（{ja(era)}〜）</span>"
            out.append(f'<h3 style="margin:22px 0 8px;">{title}</h3>')
            rows = [[("<b>Adopting the branch</b>" if lang == "en" else "<b>系統の採用時</b>"), "—", ul(uq(br.get("uniques"), lang))]]
            for pol in br.get("policies", []):
                done = pol["name"].endswith("Complete")
                nm = ("<b>Branch complete</b>" if lang == "en" else "<b>系統の完成時</b>") if done else e(pol["name"] if lang == "en" else ja(pol["name"]))
                req = ", ".join(e(r if lang == "en" else ja(r)) for r in pol.get("requires", [])) or "—"
                rows.append([nm, "—" if done else req, ul(uq(pol.get("uniques"), lang))])
            out.append(tbl(["Policy", "Requires", "Effect"] if lang == "en" else ["制度", "前提", "効果"], rows))
        return "\n".join(out)

    def policy_ai(lang):
        rows = []
        for br in policies:
            pr = br.get("priorities", {})
            top = max(VIC, key=lambda v: pr.get(v, 0))
            rows.append([e(br["name"] if lang == "en" else ja(br["name"]))] + [(f"<b>{pr.get(v, 0)}</b>" if v == top and pr.get(v, 0) > 0 else str(pr.get(v, 0))) for v in VIC])
        return tbl(["Branch"] + VIC if lang == "en" else ["系統"] + [VIC_JA[v] for v in VIC], rows)

    def policy_calc(lang):
        d = {x["name"]: x.get("policyCostModifier", 1) for x in diffs}
        cfg = {"diff": d, "speed": {"Quick": 0.67, "Standard": 1.0, "Epic": 1.5, "Marathon": 3.0},
               "map": {"Tiny": 0.1, "Small": 0.1, "Medium": 0.1, "Large": 0.075, "Huge": 0.05}}
        return f'<script>window.UNCIV_POLICY_CFG = {json.dumps(cfg)};</script>'

    wonders = [x for x in buildings if x.get("isWonder")]
    nwonders = [x for x in buildings if x.get("isNationalWonder")]

    def bcost(x):
        if "cost" in x:
            return x["cost"]
        c = col_of.get(x.get("requiredTech"))
        return (c["wonderCost"] if (x.get("isWonder") or x.get("isNationalWonder")) else c["buildingCost"]) if c else 0

    def wonder_rows(lang):
        out = []
        for era in era_order:
            ws = [w for w in wonders if era_of.get(w.get("requiredTech")) == era]
            if not ws:
                continue
            out.append(f'<h3 style="margin:22px 0 8px;">{e(era if lang == "en" else ja(era))}</h3>')
            rows = []
            for w in sorted(ws, key=lambda w: (bcost(w), w["name"])):
                rows.append([f"<b>{e(w['name'] if lang == 'en' else ja(w['name']))}</b>", e(w["requiredTech"] if lang == "en" else ja(w["requiredTech"])), bcost(w), ul(stats(w, lang) + uq(w.get("uniques"), lang))])
            out.append(tbl(["Wonder", "Tech", "Cost", "Effects"] if lang == "en" else ["遺産", "技術", "コスト", "効果"], rows))
        return "\n".join(out)

    def nwonder_rows(lang):
        rows = []
        for w in sorted(nwonders, key=lambda w: (era_order.index(era_of[w["requiredTech"]]) if w.get("requiredTech") in era_of else -1, w["name"])):
            tech = w.get("requiredTech")
            rows.append([f"<b>{e(w['name'] if lang == 'en' else ja(w['name']))}</b>",
                         e((tech if lang == "en" else ja(tech)) if tech else "—"),
                         e((w.get("requiredBuilding") if lang == "en" else ja(w.get("requiredBuilding", ""))) or "—"),
                         bcost(w) or "—", ul(stats(w, lang) + uq(w.get("uniques"), lang))])
        return tbl(["National wonder", "Tech", "Needs (in city)", "Cost", "Effects"] if lang == "en" else ["国家遺産", "技術", "必要な建物", "コスト", "効果"], rows)

    def tech_rows(lang):
        out = []
        unlock = {}
        for u in units:
            if u.get("requiredTech") and u.get("uniqueTo") != "Barbarians":
                unlock.setdefault(u["requiredTech"], []).append(("unit", u["name"], u.get("uniqueTo")))
        for b in buildings:
            if b.get("requiredTech"):
                kind = "wonder" if b.get("isWonder") else ("national" if b.get("isNationalWonder") else "building")
                unlock.setdefault(b["requiredTech"], []).append((kind, b["name"], b.get("uniqueTo")))
        for i in imps:
            if i.get("techRequired"):
                unlock.setdefault(i["techRequired"], []).append(("improvement", i["name"], i.get("uniqueTo")))
        for r in ress:
            if r.get("revealedBy"):
                unlock.setdefault(r["revealedBy"], []).append(("resource", r["name"], None))
        lab = {"en": {"unit": "Units", "building": "Buildings", "wonder": "Wonders", "national": "National wonders", "improvement": "Improvements", "resource": "Reveals"},
               "ja": {"unit": "ユニット", "building": "建物", "wonder": "遺産", "national": "国家遺産", "improvement": "タイル整備", "resource": "資源の発見"}}[lang]
        for col_i, col in enumerate(techs):
            pass
        for era in era_order:
            cols = [c for c in techs if c["era"] == era]
            out.append(f'<h3 style="margin:22px 0 8px;">{e(era if lang == "en" else ja(era))}</h3>')
            rows = []
            for c in cols:
                for t in sorted(c["techs"], key=lambda t: t["row"]):
                    groups = []
                    for kind in ("unit", "building", "wonder", "national", "improvement", "resource"):
                        items = [(n if lang == "en" else ja(n)) + ((" *" ) if ut else "") for k, n, ut in unlock.get(t["name"], []) if k == kind and ut != "Barbarians"]
                        if items:
                            groups.append(f"<b>{lab[kind]}:</b> " + e(", ".join(items) if lang == "en" else "、".join(items)))
                    pre = ", ".join(t.get("prerequisites", [])) if lang == "en" else "、".join(ja(x) for x in t.get("prerequisites", []))
                    rows.append([f"<b>{e(t['name'] if lang == 'en' else ja(t['name']))}</b>", t.get("cost", c["techCost"]), e(pre) or "—", "<br>".join(groups) or "—"])
            out.append(tbl(["Tech", "Base cost", "Requires", "Unlocks"] if lang == "en" else ["技術", "基本コスト", "前提技術", "解禁されるもの"], rows))
        return "\n".join(out)

    BTYPES = [("Pantheon", "Pantheon beliefs", "パンテオンの信仰"), ("Founder", "Founder beliefs", "創始者の信仰"), ("Follower", "Follower beliefs", "信者の信仰"), ("Enhancer", "Enhancer beliefs", "強化の信仰")]

    def belief_rows(lang):
        out = []
        for key, en_t, ja_t in BTYPES:
            bs = [b for b in beliefs if b["type"] == key]
            out.append(f'<h3 style="margin:22px 0 8px;">{en_t if lang == "en" else ja_t} ({len(bs)})</h3>')
            rows = [[f"<b>{e(b['name'] if lang == 'en' else ja(b['name']))}</b>", ul(uq(b.get("uniques"), lang))] for b in bs]
            out.append(tbl(["Belief", "Effect"] if lang == "en" else ["信仰", "効果"], rows))
        return "\n".join(out)

    regular = [b for b in buildings if not b.get("isWonder") and not b.get("isNationalWonder") and not b.get("uniqueTo")]

    def building_rows(lang):
        out = []
        for era in [None] + era_order:
            bs = [b for b in regular if era_of.get(b.get("requiredTech")) == era]
            if not bs:
                continue
            title = era if era else "No tech required"
            title_ja = ja(era) if era else "技術不要"
            out.append(f'<h3 style="margin:22px 0 8px;">{e(title if lang == "en" else title_ja)}</h3>')
            rows = []
            for b in sorted(bs, key=lambda b: (bcost(b), b["name"])):
                req = b.get("requiredBuilding")
                tech = b.get("requiredTech")
                rows.append([f"<b>{e(b['name'] if lang == 'en' else ja(b['name']))}</b>", e((tech if lang == "en" else ja(tech)) if tech else "—"),
                             e((req if lang == "en" else ja(req)) if req else "—"), bcost(b) or "—", b.get("maintenance", 0) or "—",
                             ul(stats(b, lang) + uq(b.get("uniques"), lang))])
            out.append(tbl(["Building", "Tech", "Requires", "Cost", "Upkeep", "Effects"] if lang == "en" else ["建物", "技術", "必要な建物", "コスト", "維持費", "効果"], rows))
        return "\n".join(out)

    # ---------- promotions ----------
    def promo_rows(lang):
        groups = {}
        for pr in promos:
            if not pr.get("unitTypes"):
                continue
            key = tuple(pr["unitTypes"])
            groups.setdefault(key, []).append(pr)
        rows = []
        for pr in promos:
            if not pr.get("unitTypes"):
                continue
            nm = pr["name"] if lang == "en" else ja(pr["name"])
            req = (", " if lang == "en" else "、").join((x if lang == "en" else ja(x)) for x in pr.get("prerequisites", [])) or "—"
            types = (", " if lang == "en" else "、").join((x if lang == "en" else ja(x)) for x in pr["unitTypes"])
            rows.append([f"<b>{e(nm)}</b>", e(req), e(types), ul(uq(pr.get("uniques"), lang))])
        return tbl(["Promotion", "Requires", "Unit types", "Effect"] if lang == "en" else ["昇進", "前提", "ユニットの種類", "効果"], rows)

    # ---------- terrain / resources / improvements ----------
    terrains = load("Terrains.json")
    YK = ["food", "production", "gold", "science", "culture", "faith", "happiness"]

    def yields(x, lang):
        out = []
        for k in YK:
            v = x.get(k)
            if v:
                out.append((f"{v:+g} {k.capitalize()}") if lang == "en" else f"{ja(k.capitalize())}{v:+g}")
        return ", ".join(out) if lang == "en" else "、".join(out)

    def terr_rows(lang, kinds):
        rows = []
        for t in terrains:
            if t["type"] not in kinds:
                continue
            mv = "—" if t.get("impassable") else str(t.get("movementCost", 1))
            df = f"{round(t.get('defenceBonus', 0) * 100):+d}%" if t.get("defenceBonus") else "—"
            notes = [u for u in t.get("uniques", []) if any(k in u for k in ("Rough terrain", "Fresh water", "damage", "Strength for cities", "Grants", "Rejuvenation", "cut down", "Nullifies", "Only [", "yield without"))]
            rows.append([f"<b>{e(t['name'] if lang == 'en' else ja(t['name']))}</b>", e(yields(t, lang)) or "—",
                         ("Impassable" if lang == "en" else "通行不可") if t.get("impassable") else mv, df, ul(uq(notes, lang))])
        return tbl(["Terrain", "Yields", "Move cost", "Defense", "Notes"] if lang == "en" else ["地形", "産出", "移動コスト", "防御", "特徴"], rows)

    def res_rows(lang):
        rows = []
        order = {"Bonus": 0, "Strategic": 1, "Luxury": 2}
        for r in sorted(ress, key=lambda r: (order.get(r["resourceType"], 9), r["name"])):
            imp = r.get("improvement")
            on = (", " if lang == "en" else "、").join((x if lang == "en" else ja(x)) for x in r.get("terrainsCanBeFoundOn", []))
            rv = r.get("revealedBy")
            rows.append([f"<b>{e(r['name'] if lang == 'en' else ja(r['name']))}</b>", e(r["resourceType"] if lang == "en" else ja(r["resourceType"] + " resource") if (r["resourceType"] + " resource") in tr.exact else r["resourceType"]),
                         e(yields(r, lang)) or "—", e((imp if lang == "en" else ja(imp)) if imp else "—"),
                         e(yields(r.get("improvementStats", {}), lang)) or "—", e((rv if lang == "en" else ja(rv)) if rv else "—"), e(on)])
        return tbl(["Resource", "Type", "Yields", "Improvement", "Extra when improved", "Revealed by", "Found on"] if lang == "en"
                   else ["資源", "種類", "産出", "タイル整備", "整備後の追加", "発見に必要な技術", "出現する地形"], rows)

    def imp_rows(lang):
        rows = []
        for i in imps:
            if not i.get("turnsToBuild") and not i.get("techRequired"):
                continue
            if i.get("uniqueTo"):
                continue
            tech = i.get("techRequired")
            rows.append([f"<b>{e(i['name'] if lang == 'en' else ja(i['name']))}</b>", e((tech if lang == "en" else ja(tech)) if tech else "—"),
                         i.get("turnsToBuild", "—"), e(yields(i, lang)) or "—", ul(uq([u for u in i.get("uniques", []) if "Pillaging" not in u and "Automation" not in u], lang))])
        return tbl(["Improvement", "Tech", "Turns", "Yields", "Notes"] if lang == "en" else ["タイル整備", "技術", "ターン", "産出", "特徴"], rows)

    # ---------- city-states ----------
    cstypes = load("CityStateTypes.json")
    quests = load("Quests.json")

    def cs_rows(lang):
        rows = []
        for c in cstypes:
            rows.append([f"<b>{e(c['name'] if lang == 'en' else ja(c['name']))}</b>", ul(uq(c.get("friendBonusUniques"), lang)), ul(uq(c.get("allyBonusUniques"), lang))])
        return tbl(["Type", "Friend bonus", "Ally bonus"] if lang == "en" else ["種類", "友好時のボーナス", "同盟時のボーナス"], rows)

    def quest_rows(lang):
        rows = []
        for q in quests:
            inf = q.get("influence")
            dur = q.get("duration")
            glob = q.get("type") == "Global"
            rows.append([f"<b>{e(q['name'] if lang == 'en' else ja(q['name']))}</b>", e(clean_en(q.get("description", "")) if lang == "en" else (tr.sentence(q.get("description", "")) or ja(q.get("description", "")) or clean_en(q.get("description", "")))),
                         inf if inf is not None else "40", dur or "—", ("Contest (best civ wins)" if lang == "en" else "競争（最上位の文明が獲得）") if glob else "—"])
        return tbl(["Quest", "What it asks", "Influence", "Turns", "Kind"] if lang == "en" else ["クエスト", "内容", "影響力", "期限（ターン）", "形式"], rows)

    # ---------- great people ----------
    specialists = load("Specialists.json")

    def gp_rows(lang):
        rows = []
        for n in ("Great Scientist", "Great Engineer", "Great Merchant", "Great Artist", "Great Prophet", "Great General", "Great Admiral"):
            x = raw_unit[n]
            grp = next((re.search(r"\[([^\]]+)\]", u).group(1) for u in x["uniques"] if u.startswith("Is part of Great Person group")), "")
            abil = [u for u in x["uniques"] if not any(k in u for k in ("Is part of", "gets a name", "Great Person -", "Unbuildable", "Uncapturable", "Religious Unit", "Only available", "Sight"))]
            rows.append([f"<b>{e(n if lang == 'en' else ja(n))}</b>", e(grp if lang == "en" else ja(grp)), ul(uq(abil, lang))])
        return tbl(["Great person", "Point pool", "What it can do"] if lang == "en" else ["偉人", "ポイントの枠", "できること"], rows)

    def spec_rows(lang):
        rows = []
        for sp in specialists:
            rows.append([f"<b>{e(sp['name'] if lang == 'en' else ja(sp['name']))}</b>", e(yields(sp, lang)), e(", ".join(f"+{v} {k}" for k, v in sp.get("greatPersonPoints", {}).items()) if lang == "en" else "、".join(f"{ja(k)}+{v}" for k, v in sp.get("greatPersonPoints", {}).items()))])
        return tbl(["Specialist", "Yields", "Great person points"] if lang == "en" else ["専門家", "産出", "偉人ポイント"], rows)

    def gp_src_rows(lang):
        rows = []
        for b in buildings:
            if not b.get("greatPersonPoints") or b.get("uniqueTo"):
                continue
            kind = ("World wonder" if lang == "en" else "世界遺産") if b.get("isWonder") else (("National wonder" if lang == "en" else "国家遺産") if b.get("isNationalWonder") else ("Building" if lang == "en" else "建物"))
            pts = ", ".join(f"+{v} {k}" for k, v in b["greatPersonPoints"].items()) if lang == "en" else "、".join(f"{ja(k)}+{v}" for k, v in b["greatPersonPoints"].items())
            slots = ", ".join(f"{v} {k}" for k, v in (b.get("specialistSlots") or {}).items()) if lang == "en" else "、".join(f"{ja(k)}{v}" for k, v in (b.get("specialistSlots") or {}).items())
            rows.append([f"<b>{e(b['name'] if lang == 'en' else ja(b['name']))}</b>", kind, e(pts), e(slots) or "—"])
        rows.sort(key=lambda r: r[1])
        return tbl(["Source", "Kind", "Points per turn", "Specialist slots"] if lang == "en" else ["入手元", "種類", "毎ターンのポイント", "専門家の枠"], rows)

    # ---------- growth ----------
    import math
    def food_needed(p):
        return 15 + 8 * (p - 1) + math.floor((p - 1) ** 1.5)

    def growth_rows(lang):
        rows = []
        total = 0
        for p in range(1, 31):
            f = food_needed(p)
            total += f
            rows.append([f"{p} → {p + 1}", f, total, int(f * 0.67), int(f * 1.5), int(f * 3)])
        return tbl(["Population", "Food (Standard)", "Total from size 1", "Quick", "Epic", "Marathon"] if lang == "en"
                   else ["人口", "必要な食料（標準）", "人口1からの累計", "クイック", "エピック", "マラソン"], rows)

    speeds, eras, ruins, victories = (load(f) for f in ("Speeds.json", "Eras.json", "Ruins.json", "VictoryTypes.json"))
    SPJ = {"Quick": "クイック", "Standard": "スタンダード", "Epic": "エピック", "Marathon": "マラソン"}

    def speed_rows(lang):
        keys = [("modifier", "Growth & great people", "成長・偉人"), ("productionCostModifier", "Production", "生産"), ("scienceCostModifier", "Research", "研究"),
                ("cultureCostModifier", "Culture (policies)", "文化（社会制度）"), ("goldCostModifier", "Gold purchases", "ゴールドでの購入"), ("faithCostModifier", "Faith purchases", "信仰力での購入"),
                ("improvementBuildLengthModifier", "Worker build time", "タイル整備の時間"), ("goldenAgeLengthModifier", "Golden age length", "黄金時代の長さ")]
        rows = []
        for sp in speeds:
            maxt = sp["turns"][-1]["untilTurn"] if sp.get("turns") else "—"
            rows.append([f"<b>{sp['name'] if lang == 'en' else SPJ.get(sp['name'], sp['name'])}</b>"] + [f"{round(sp.get(k, 1) * 100)}%" for k, _, _ in keys] + [maxt])
        return tbl((["Speed"] + [a for _, a, _ in keys] + ["Max turns"]) if lang == "en" else (["速度"] + [b for _, _, b in keys] + ["最大ターン"]), rows)

    def era_rows(lang):
        rows = []
        for er in eras:
            u = er.get("startingMilitaryUnit", "")
            rows.append([f"<b>{e(er['name'] if lang == 'en' else ja(er['name']))}</b>", er.get("startingSettlerCount", 1), er.get("startingWorkerCount", 0),
                         f"{er.get('startingMilitaryUnitCount', 0)} × {e(u if lang == 'en' else ja(u))}", er.get("settlerPopulation", 1)])
        return tbl(["Starting era", "Settlers", "Workers", "Military units", "Starting city size"] if lang == "en" else ["開始時代", "開拓者", "労働者", "軍事ユニット", "都市の初期人口"], rows)

    def ruin_rows(lang):
        rows = []
        for r in ruins:
            rows.append([f"<b>{e(r['name'] if lang == 'en' else (ja(r['name']) if r['name'] in tr.exact else r['name']))}</b>", ul(uq([u for u in r.get("uniques", []) if "sound" not in u], lang))])
        return tbl(["Ruin result", "Effect and conditions"] if lang == "en" else ["遺跡の結果", "効果と条件"], rows)

    def victory_rows(lang):
        rows = []
        VJ = {"Scientific": "科学", "Cultural": "文化", "Domination": "制覇", "Diplomatic": "外交", "Time": "時間"}
        for v in victories:
            ms = v.get("milestones", [])
            ms_t = [clean_en(m) if lang == "en" else (tr.sentence(m) if "[" in m else tr.exact.get(m)) or clean_en(m) for m in ms]
            rows.append([f"<b>{v['name'] if lang == 'en' else VJ.get(v['name'], v['name'])}</b>", ul(ms_t)])
        return tbl(["Victory", "Milestones (in order)"] if lang == "en" else ["勝利", "達成条件（順番に）"], rows)

    PAGES["uniq"] = PAGES["civs"]
    PAGES["policyai"] = PAGES["policies"]
    PAGES["policycalc"] = PAGES["policies"]
    PAGES["nwonders"] = PAGES["wonders"]
    for k in ("features", "naturalwonders", "resources", "improvements"):
        PAGES[k] = PAGES["terrain"]
    PAGES["quests"] = PAGES["citystates"]
    PAGES["eras"] = PAGES["speeds"]
    PAGES["specialists"] = PAGES["greatpeople"]
    PAGES["gpsources"] = PAGES["greatpeople"]
    for key, fn in (("civs", civ_rows), ("units", unit_rows), ("uniq", uniq_rows), ("diff", diff_rows),
                    ("policies", policy_rows), ("policyai", policy_ai), ("policycalc", policy_calc),
                    ("wonders", wonder_rows), ("nwonders", nwonder_rows), ("techs", tech_rows), ("beliefs", belief_rows), ("buildings", building_rows),
                    ("promotions", promo_rows), ("terrain", lambda l: terr_rows(l, ("Land", "Water"))), ("features", lambda l: terr_rows(l, ("TerrainFeature",))),
                    ("naturalwonders", lambda l: terr_rows(l, ("NaturalWonder",))), ("resources", res_rows), ("improvements", imp_rows),
                    ("citystates", cs_rows), ("quests", quest_rows), ("greatpeople", gp_rows), ("specialists", spec_rows), ("gpsources", gp_src_rows),
                    ("growth", growth_rows), ("speeds", speed_rows), ("eras", era_rows), ("ruins", ruin_rows), ("victory", victory_rows)):
        marker = "UNCIV-" + key.upper()
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
    print(f"civs={len(civs)} units={len(ulist)} policies={len(policies)} wonders={len(wonders)}+{len(nwonders)} techs={sum(len(c['techs']) for c in techs)} beliefs={len(beliefs)} untranslated={len(tr.missing)}")
    for m in sorted(tr.missing)[:40]:
        print("  missing:", m)


if __name__ == "__main__":
    main()
