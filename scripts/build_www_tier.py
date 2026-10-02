#!/usr/bin/env python3
"""
波乱水世界（Wild Water World）の総合Tier表を assets/data/www-tier-sources.json から計算し、
英日ページの <!-- WWW-TIER:START --> 〜 <!-- WWW-TIER:END --> と <!-- WWW-SOURCES:START --> 〜 END に書き込む（冪等）。

集計方法（ページにも同じ説明を載せる）:
  - 評価を点数化: SS=4, S=3, A=2, B=1, C=0。そのキャラを載せている表だけで平均する（載っていない表は数えない）。
  - 総合Tier: 平均 3.5以上=SS, 2.5以上=S, 1.5以上=A, 0.5以上=B, それ未満=C。
  - 一致度: 評価の最大と最小の差が 1段階以内=高, 2段階=中, 3段階以上=低。
  - 2つ以下の表にしか載っていないキャラは「参考」として表の下にまとめる。

使い方: python3 scripts/build_www_tier.py
"""
import html
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "assets/data/www-tier-sources.json")
PAGES = {"en": "games/haran-suisekai/tier-list/index.html", "ja": "ja/games/haran-suisekai/tier-list/index.html"}
SCORE = {"SS": 4, "S": 3, "A": 2, "B": 1, "C": 0}
CLASS = {"tank": ("Tank", "タンク"), "mage": ("Mage", "メイジ"), "shooter": ("Shooter", "シューター"), "warrior": ("Warrior", "ウォリアー")}
MIN_SOURCES = 3

T = {
    "en": {"head": ["Hero", "Class", "Overall", "Avg", "Agreement"], "agree": {"high": "High", "mid": "Medium", "low": "Low"},
           "lists": "{n} lists", "minor": "Rated by only one or two lists", "src_head": ["#", "List", "Date", "Note"]},
    "ja": {"head": ["キャラ", "職業", "総合", "平均", "一致度"], "agree": {"high": "高", "mid": "中", "low": "低"},
           "lists": "{n}件", "minor": "1〜2件の表にしか載っていないキャラ", "src_head": ["#", "情報源", "日付", "備考"]},
}
NOTE_EN = {"2サイトの表が同一のため1件として数える": "Two sites publish an identical list, counted once", "5キャラのみ掲載": "Rates only 5 crew"}


def tier_of(avg):
    for t, cut in (("SS", 3.5), ("S", 2.5), ("A", 1.5), ("B", 0.5)):
        if avg >= cut:
            return t
    return "C"


def compute(d):
    ratings = {}
    for i, src in enumerate(d["sources"]):
        for tier, ids in src["tiers"].items():
            for cid in ids:
                if cid not in d["crew"]:
                    sys.exit(f"unknown crew id {cid} in {src['id']}")
                ratings.setdefault(cid, {})[i] = tier
    rows = []
    for cid, r in ratings.items():
        scores = [SCORE[t] for t in r.values()]
        avg = sum(scores) / len(scores)
        spread = max(scores) - min(scores)
        rows.append({"id": cid, "ratings": r, "avg": avg, "n": len(scores), "tier": tier_of(avg),
                     "agree": "high" if spread <= 1 else ("mid" if spread == 2 else "low")})
    rows.sort(key=lambda x: (-x["avg"], -x["n"], x["id"]))
    return rows


def badge(t):
    return f'<span class="tier tier-{t.lower() if t != "C" else "b"}">{t}</span>'


def render(lang, d, rows):
    t, i, e = T[lang], (0 if lang == "en" else 1), html.escape
    srcs = d["sources"]
    head = "".join(f"<th>{h}</th>" for h in t["head"]) + "".join(f'<th class="tag-mono">{k}</th>' for k in range(1, len(srcs) + 1))
    head += f'<th>{"What they do" if lang == "en" else "主な役割"}</th>'
    body = []
    for r in rows:
        if r["n"] < MIN_SOURCES:
            continue
        c = d["crew"][r["id"]]
        name, sub = (c["en"], c["ja"]) if lang == "en" else (c["ja"], c["en"])
        cls = CLASS[c["class"]][i] if c["class"] else "—"
        per = "".join(f'<td class="tag-mono">{r["ratings"].get(k, "·")}</td>' for k in range(len(srcs)))
        note = d["notes"].get(r["id"], ["", ""])[i] or "—"
        body.append(f'<tr><td><b>{e(name)}</b><br><span class="romaji">{e(sub)}</span></td><td>{cls}</td>'
                    f'<td>{badge(r["tier"])}</td><td class="tag-mono">{r["avg"]:.1f}<br><span class="build-note">{t["lists"].format(n=r["n"])}</span></td>'
                    f'<td>{t["agree"][r["agree"]]}</td>{per}<td>{e(note)}</td></tr>')
    table = f'<table class="codes tier-table">\n<thead><tr>{head}</tr></thead>\n<tbody>\n' + "\n".join(body) + "\n</tbody>\n</table>"
    minor = [r for r in rows if r["n"] < MIN_SOURCES]
    if minor:
        items = []
        for r in minor:
            c = d["crew"][r["id"]]
            nm = c["en"] if lang == "en" else c["ja"]
            vals = "/".join(r["ratings"][k] for k in sorted(r["ratings"]))
            items.append(f"{e(nm)} ({vals})" if lang == "en" else f"{e(nm)}（{vals}）")
        table += f'\n<p class="build-note" style="margin:10px 0 0;"><b>{t["minor"]}:</b> ' + ", ".join(items) + "</p>"

    srows = []
    for k, s in enumerate(srcs, 1):
        links = " ".join(f'<a href="{u}" target="_blank" rel="noopener">{"link" if lang == "en" else "リンク"}</a>' for u in s["urls"])
        note = s.get("note", "")
        if lang == "en":
            note = NOTE_EN.get(note, note)
        srows.append(f'<tr><td class="tag-mono">{k}</td><td>{e(s["name"])} {links}</td><td class="tag-mono">{s["date"]}</td><td>{e(note) or "—"}</td></tr>')
    sources = (f'<table class="codes">\n<thead><tr>{"".join(f"<th>{h}</th>" for h in t["src_head"])}</tr></thead>\n<tbody>\n'
               + "\n".join(srows) + "\n</tbody>\n</table>")
    return table, sources


def main():
    d = json.load(open(DATA, encoding="utf-8"))
    rows = compute(d)
    for lang, page in PAGES.items():
        path = os.path.join(ROOT, page)
        s = open(path, encoding="utf-8").read()
        table, sources = render(lang, d, rows)
        for marker, content in (("WWW-TIER", table), ("WWW-SOURCES", sources)):
            s, n = re.subn(rf"(<!-- {marker}:START -->\n).*?(<!-- {marker}:END -->)",
                           lambda m: m.group(1) + content + "\n" + m.group(2), s, flags=re.S)
            if n != 1:
                sys.exit(f"{marker} markers not found in {page}")
        open(path, "w", encoding="utf-8").write(s)
        print(f"rendered into {page}")
    for r in rows:
        print(f'  {r["tier"]:2} {r["avg"]:.2f} n={r["n"]} {r["agree"]:4} {r["id"]}')


if __name__ == "__main__":
    main()
