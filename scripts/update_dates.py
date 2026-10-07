#!/usr/bin/env python3
"""
sitemap.xml の各URLに <lastmod>（git の最終コミット日）を付け、英日ページの JSON-LD Article に
datePublished（最初のコミット日）と dateModified（最終コミット日）を入れる。冪等。
ページを更新してコミットした後に実行し、もう一度コミットする（日付は直前のコミットまでの履歴から取る）。

使い方: python3 scripts/update_dates.py
"""
import os
import re
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOMAIN = "https://kouryakulab.com/"


def git_dates(path):
    out = subprocess.run(["git", "-C", ROOT, "log", "--follow", "--format=%cs", "--", path], capture_output=True, text=True).stdout.split()
    return (out[-1], out[0]) if out else (None, None)


def file_of(url):
    p = url[len(DOMAIN):]
    return os.path.join(p, "index.html") if (p == "" or p.endswith("/")) else p


def main():
    sm_path = os.path.join(ROOT, "sitemap.xml")
    sm = open(sm_path, encoding="utf-8").read()
    sm = re.sub(r"\s*<lastmod>[^<]*</lastmod>", "", sm)

    def add(m):
        url = m.group(1)
        _, mod = git_dates(file_of(url))
        return m.group(0) + (f"\n    <lastmod>{mod}</lastmod>" if mod else "")
    sm = re.sub(r"<loc>([^<]+)</loc>", add, sm)
    open(sm_path, "w", encoding="utf-8").write(sm)

    n = 0
    for url in re.findall(r"<loc>([^<]+)</loc>", sm):
        f = os.path.join(ROOT, file_of(url))
        if not os.path.exists(f):
            continue
        pub, mod = git_dates(file_of(url))
        if not pub:
            continue
        s = open(f, encoding="utf-8").read()
        if '"@type": "Article"' not in s:
            continue
        s2 = re.sub(r'\n\s*"datePublished": "[^"]*",|\n\s*"dateModified": "[^"]*",', "", s)
        s2 = re.sub(r'("@type": "Article",)', lambda m: m.group(1) + f'\n      "datePublished": "{pub}",\n      "dateModified": "{mod}",', s2, count=1)
        if s2 != s:
            open(f, "w", encoding="utf-8").write(s2); n += 1
    print(f"sitemap lastmod: {sm.count('<lastmod>')} / Article dates updated: {n}")


if __name__ == "__main__":
    main()
