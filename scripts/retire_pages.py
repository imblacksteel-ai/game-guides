#!/usr/bin/env python3
"""
薄い記事を退役させる（冪等）。RETIRED の各ページを、全言語ディレクトリで
「noindex＋canonical＋meta refresh で移転先へ転送する短いページ」に置き換え、
sitemap から外し、他ページからのリンクを消す（タブ・cluster-link の行は削除、文中のリンクは移転先へ書き換え）。
GitHub Pages ではサーバー側のリダイレクトが使えないため、この方法にしている。

使い方: python3 scripts/retire_pages.py
"""
import glob
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LANGS = ["", "ja/", "ko/", "zh/", "zh-hant/", "de/", "fr/", "ar/"]
# 退役ページ: 移転先（同じ言語のプレフィックスが付く）
RETIRED = {
    "games/unciv/best-civ/": "games/unciv/civilizations/",         # 2026-10: 推測中心の選び方記事（Redditで「当たり前・的外れ」と指摘）
    "games/deresute/access/": "games/deresute/#access",             # 2026-10: 一般的な助言だけでハブの節と重複
    "games/srwdd/reroll/": "games/srwdd/#reroll",                   # 2026-10: ハブのリセマラ節と重複
    "games/srwdd/world-guide/": "games/srwdd/",                     # 2026-10: 出典の弱い推測が中心
}


def stub(target, lang):
    msg = "このページは統合されました。" if lang == "ja/" else "This page has moved."
    return f'''<!doctype html>
<html lang="{(lang.strip('/') or 'en')}">
<head>
<meta charset="UTF-8">
<meta name="robots" content="noindex, follow">
<link rel="canonical" href="https://kouryakulab.com/{target}">
<meta http-equiv="refresh" content="0; url=/{target}">
<title>{msg}</title>
</head>
<body>
<p><a href="/{target}">{msg}</a></p>
</body>
</html>
'''


def main():
    # 1. stubs
    for src, dst in RETIRED.items():
        for lang in LANGS:
            f = os.path.join(ROOT, lang + src, "index.html")
            if os.path.exists(f):
                open(f, "w", encoding="utf-8").write(stub(lang + dst, lang))
    # 2. sitemap
    p = os.path.join(ROOT, "sitemap.xml")
    s = open(p, encoding="utf-8").read()
    for src in RETIRED:
        s = re.sub(r"\s*<url>\s*<loc>https://kouryakulab\.com/(?:ja/)?" + re.escape(src) + r"</loc>.*?</url>", "", s, flags=re.S)
    open(p, "w", encoding="utf-8").write(s)
    # 3. links elsewhere
    n = 0
    for f in glob.glob(os.path.join(ROOT, "**", "*.html"), recursive=True):
        rel = os.path.relpath(f, ROOT)
        if any(rel.startswith(l + src) for src in RETIRED for l in LANGS):
            continue
        s = open(f, encoding="utf-8").read()
        s0 = s
        for src, dst in RETIRED.items():
            for lang in LANGS:
                href = "/" + lang + src
                # whole-line tab links and cluster-link paragraphs
                s = re.sub(r'\n[ \t]*<a href="' + re.escape(href) + r'"[^>]*>[^<]*</a>[ \t]*(?=\n)', "", s)
                s = re.sub(r'\n[ \t]*<p class="cluster-link"[^>]*><a href="' + re.escape(href) + r'".*?</p>[ \t]*(?=\n)', "", s)
                s = re.sub(r'\n[ \t]*<li><a href="' + re.escape(href) + r'".*?</li>[ \t]*(?=\n)', "", s)
                # related-block links " · <a href=...>...</a>"
                s = re.sub(r' · <a href="' + re.escape(href) + r'">[^<]*</a>', "", s)
                # remaining inline links -> target
                s = s.replace(f'href="{href}"', f'href="/{lang}{dst}"')
        if s != s0:
            open(f, "w", encoding="utf-8").write(s); n += 1
    print(f"stubs written, sitemap updated, links fixed in {n} files")


if __name__ == "__main__":
    main()
