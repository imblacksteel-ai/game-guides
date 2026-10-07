#!/usr/bin/env python3
"""
内部リンクを自動で張る（冪等）。英日のみ。
  1. 各記事ページ（/games/<slug>/<page>/）の </main> 直前に、同じゲームの他の記事一覧を
     <!-- RELATED:START --> 〜 <!-- RELATED:END --> として書き込む。
  2. トップページ（/ と /ja/）の <!-- LATEST:START --> 〜 <!-- LATEST:END --> に、新しい記事12件を書き込む
     （公開日は git の最初のコミット日）。
記事名は各ページの <h1>。ページを追加・改名したら、seo_inject.py / set_indexing.py の後に実行する。

使い方: python3 scripts/update_internal_links.py
"""
import html
import os
import re
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOMAIN = "https://kouryakulab.com/"
GAME = {"kancolle": ("KanColle", "艦これ"), "haran-suisekai": ("Wild Water World", "波乱水世界"), "srwdd": ("Super Robot Wars DD", "スパロボDD"),
        "deresute": ("Deresute", "デレステ"), "gakumas": ("Gakuen Idolmaster", "学マス"), "mindustry": ("Mindustry", "Mindustry"),
        "shattered-pixel-dungeon": ("Shattered Pixel Dungeon", "Shattered Pixel Dungeon"), "unciv": ("Unciv", "Unciv"),
        "endless-sky": ("Endless Sky", "Endless Sky")}


def first_commit(path):
    out = subprocess.run(["git", "-C", ROOT, "log", "--follow", "--format=%cs", "--", path], capture_output=True, text=True).stdout.split()
    return out[-1] if out else "9999-99-99"


def h1(path):
    s = open(path, encoding="utf-8").read()
    m = re.search(r"<h1[^>]*>(.*?)</h1>", s, re.S)
    return html.unescape(re.sub(r"<[^>]+>", "", m.group(1))).strip() if m else ""


def main():
    sm = open(os.path.join(ROOT, "sitemap.xml"), encoding="utf-8").read()
    urls = re.findall(r"<loc>([^<]+)</loc>", sm)
    pages = []  # (lang, slug, url_path, file, title)
    for u in urls:
        p = u[len(DOMAIN):]
        m = re.match(r"(ja/)?games/([^/]+)/([^/]+)/$", p)
        if not m:
            continue
        lang = "ja" if m.group(1) else "en"
        f = os.path.join(ROOT, p, "index.html")
        if os.path.exists(f):
            pages.append((lang, m.group(2), "/" + p, f, h1(f)))

    # 1. related links per game
    n = 0
    for lang, slug, path, f, _ in pages:
        sib = [(pp, t) for (l2, s2, pp, _, t) in pages if l2 == lang and s2 == slug and pp != path]
        if not sib:
            continue
        name = GAME.get(slug, (slug, slug))[0 if lang == "en" else 1]
        hub = f"/games/{slug}/" if lang == "en" else f"/ja/games/{slug}/"
        title = f"More {name} guides" if lang == "en" else f"{name}のほかの攻略記事"
        links = " · ".join(f'<a href="{pp}">{html.escape(t)}</a>' for pp, t in sorted(sib, key=lambda x: x[1]))
        hub_t = (f"{name} guide home" if lang == "en" else f"{name} 攻略トップ")
        block = (f'<!-- RELATED:START -->\n  <div class="panel" style="margin-top:28px;">\n    <h3 style="font-size:.95rem;margin:0 0 8px;">{html.escape(title)}</h3>\n'
                 f'    <p style="font-size:.88rem;line-height:1.9;margin:0;"><a href="{hub}"><b>{html.escape(hub_t)}</b></a> · {links}</p>\n  </div>\n<!-- RELATED:END -->\n')
        s = open(f, encoding="utf-8").read()
        if "<!-- RELATED:START -->" in s:
            s2 = re.sub(r"<!-- RELATED:START -->.*?<!-- RELATED:END -->\n", lambda m: block, s, flags=re.S)
        else:
            i = s.rfind("</main>")
            if i < 0:
                continue
            s2 = s[:i] + block + s[i:]
        if s2 != s:
            open(f, "w", encoding="utf-8").write(s2); n += 1

    # 2. latest on the home pages
    for lang, home in (("en", "index.html"), ("ja", "ja/index.html")):
        lst = sorted([(first_commit(os.path.relpath(f, ROOT)), pp, slug, t) for (l2, slug, pp, f, t) in pages if l2 == lang], reverse=True)[:12]
        cards = "\n".join(
            f'    <a class="card" href="{pp}">\n      <span class="tag">{html.escape(GAME.get(slug, (slug, slug))[0 if lang == "en" else 1])}</span>\n'
            f'      <h3>{html.escape(t)}</h3>\n      <p>{d}</p>\n    </a>' for d, pp, slug, t in lst)
        title = "Latest Guides" if lang == "en" else "新着記事"
        block = (f'<!-- LATEST:START -->\n  <h2 class="section-title" style="margin-top:34px;">{title}</h2>\n  <div class="grid">\n{cards}\n  </div>\n<!-- LATEST:END -->\n')
        hp = os.path.join(ROOT, home)
        s = open(hp, encoding="utf-8").read()
        if "<!-- LATEST:START -->" in s:
            s = re.sub(r"<!-- LATEST:START -->.*?<!-- LATEST:END -->\n", lambda m: block, s, flags=re.S)
        else:
            s = s.replace("</main>", block + "</main>", 1)
        open(hp, "w", encoding="utf-8").write(s)
    print(f"related blocks written: {n}; latest: 12 each on / and /ja/")


if __name__ == "__main__":
    main()
