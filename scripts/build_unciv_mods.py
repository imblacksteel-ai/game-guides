#!/usr/bin/env python3
"""
Unciv の人気MOD一覧を GitHub から取得し、英日ページの <!-- UNCIV-MODS --> マーカー間に書き込む（冪等）。

ゲーム内のMODブラウザは GitHub のトピック "unciv-mod*" を検索している（core/.../logic/github/Github.kt）。
カテゴリは android/assets/jsons/ModCategories.json のトピック（unciv-mod-rulesets など）。
ここでは topic:unciv-mod をスター数順に上位 LIMIT 件取得し、カテゴリ・スター数・最終更新日・説明（リポジトリの説明文）を表にする。
説明文は作者が書いたものなので、英語のまま「リポジトリの説明」として載せる（日本語版も英語のまま）。

使い方: python3 scripts/build_unciv_mods.py   （gh CLI が認証済みなら gh api を使う。なければ未認証のAPI）
"""
import datetime
import html
import json
import os
import re
import subprocess
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGES = {"en": "games/unciv/mods/index.html", "ja": "ja/games/unciv/mods/index.html"}
LIMIT = 40
CATS = {"unciv-mod-rulesets": ("Ruleset", "ルールセット"), "unciv-mod-expansions": ("Expansion", "拡張"), "unciv-mod-graphics": ("Graphics", "グラフィック"),
        "unciv-mod-audio": ("Audio", "音楽・音声"), "unciv-mod-maps": ("Maps", "マップ"), "unciv-mod-fun": ("Fun", "おふざけ"), "unciv-mod-modsofmods": ("Mod of a mod", "MODのMOD")}


def search():
    q = f"search/repositories?q=topic:unciv-mod&sort=stars&order=desc&per_page={LIMIT}"
    try:
        out = subprocess.run(["gh", "api", q], capture_output=True, text=True, check=True).stdout
        return json.loads(out)["items"]
    except Exception:
        req = urllib.request.Request("https://api.github.com/" + q, headers={"User-Agent": "kouryakulab-build", "Accept": "application/vnd.github+json"})
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read().decode())["items"]


def main():
    items = search()
    today = datetime.date.today().isoformat()
    e = html.escape
    for lang, rel in PAGES.items():
        rows = []
        for i, it in enumerate(items, 1):
            cats = [CATS[t][0 if lang == "en" else 1] for t in it.get("topics", []) if t in CATS]
            desc = (it.get("description") or "").strip()
            if len(desc) > 140:
                desc = desc[:137].rstrip() + "…"
            name = it["name"].replace("-", " ").replace("_", " ")
            rows.append(f'<tr><td>{i}</td><td><a href="{e(it["html_url"])}" target="_blank" rel="noopener"><b>{e(name)}</b></a><br>'
                        f'<span style="color:var(--ink-dim);font-size:.82rem">{e(it["owner"]["login"])}</span></td>'
                        f'<td>{e(", ".join(cats) if lang == "en" else "、".join(cats)) or "—"}</td><td>{it["stargazers_count"]}</td>'
                        f'<td>{it["pushed_at"][:10]}</td><td style="font-size:.88rem">{e(desc) or "—"}</td></tr>')
        head = ("<th>#</th><th>Mod</th><th>Category</th><th>Stars</th><th>Last updated</th><th>Description (from the repository)</th>" if lang == "en"
                else "<th>#</th><th>MOD</th><th>カテゴリ</th><th>スター</th><th>最終更新</th><th>説明（リポジトリの英語の説明文）</th>")
        cap = (f"Top {len(items)} mods tagged “unciv-mod” on GitHub by stars, checked {today}." if lang == "en"
               else f"GitHubで「unciv-mod」タグが付いたMODのスター数上位{len(items)}件（{today}確認）。")
        block = (f'<!-- UNCIV-MODS -->\n<p style="color:var(--ink-dim);font-size:.9rem;margin:0 0 8px;">{cap}</p>\n'
                 f'<div class="table-scroll"><table class="glossary"><thead><tr>{head}</tr></thead><tbody>\n' + "\n".join(rows) + "\n</tbody></table></div>\n<!-- /UNCIV-MODS -->")
        p = os.path.join(ROOT, rel)
        if not os.path.exists(p):
            print("skip (no page yet):", rel); continue
        s = open(p, encoding="utf-8").read()
        s2, n = re.subn(r"<!-- UNCIV-MODS -->.*?<!-- /UNCIV-MODS -->", lambda m: block, s, flags=re.S)
        if n != 1:
            sys.exit(f"marker not found once in {rel}")
        open(p, "w", encoding="utf-8").write(s2)
        print("wrote", rel)


if __name__ == "__main__":
    main()
