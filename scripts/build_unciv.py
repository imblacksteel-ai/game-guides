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
}
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
    PARAM_OVERRIDE = {"Land": "地上", "Water": "水上"}

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

    def uniq_rows(lang):
        rows = []
        for u in ulist:
            b = base.get(u["replaces"]) if u["unique_to"] else None
            if not b:
                continue
            def d(k):
                v = u[k] - b[k]
                return "±0" if v == 0 else (f"+{v}" if v > 0 else str(v))
            if lang == "en":
                cells = [f"<b>{e(u['name'])}</b>", e(u["unique_to"]), e(b["name"]), d("strength"), d("ranged"), d("move"), d("cost")]
            else:
                cells = [f"<b>{e(u['name_ja'])}</b>", e(u["unique_to_ja"]), e(b["name_ja"]), d("strength"), d("ranged"), d("move"), d("cost")]
            rows.append("<tr>" + "".join(f"<td>{c}</td>" for c in cells) + "</tr>")
        head = ("<th>Unique unit</th><th>Civilization</th><th>Replaces</th><th>Strength</th><th>Ranged</th><th>Move</th><th>Cost</th>" if lang == "en"
                else "<th>固有ユニット</th><th>文明</th><th>置き換え対象</th><th>戦闘力</th><th>遠隔</th><th>移動</th><th>コスト</th>")
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

    PAGES["uniq"] = PAGES["civs"]
    for key, fn in (("civs", civ_rows), ("units", unit_rows), ("uniq", uniq_rows), ("diff", diff_rows)):
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
    print(f"civs={len(civs)} units={len(ulist)} untranslated={len(tr.missing)}")
    for m in sorted(tr.missing)[:40]:
        print("  missing:", m)


if __name__ == "__main__":
    main()
