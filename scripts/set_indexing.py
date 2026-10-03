#!/usr/bin/env python3
"""検索インデックス対象の言語を英語・日本語に絞る（冪等）。

2026/09 に AdSense で「有用性の低いコンテンツ」として却下された。短期間に8言語ぶん
翻訳ページを量産した点が薄いコンテンツと見られた可能性が高いため、英語・日本語以外の
言語版は公開したまま noindex にし、hreflang と sitemap.xml から外す。

- NOINDEX_DIRS 配下の全ページ: <meta name="robots" content="noindex, follow"> を付け、
  hreflang の alternate を全部外す（noindex ページの hreflang は無視されるため）。AdSense のタグも外す。
- それ以外のページ: NOINDEX_DIRS の言語の hreflang 行と og:locale:alternate を外す。
- sitemap.xml: NOINDEX_DIRS の URL と alternate を外す。

言語を戻すときは NOINDEX_DIRS から外して、ページの hreflang を手で戻す。
新しいページを追加したら scripts/seo_inject.py の後にこれを実行する。
"""
import glob
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOMAIN = "https://kouryakulab.com"

NOINDEX_DIRS = ["ko", "zh", "zh-hant", "de", "fr", "ar"]
NOINDEX_HREFLANGS = ["ko", "zh", "zh-Hant", "de", "fr", "ar"]
NOINDEX_LOCALES = ["ko_KR", "zh_CN", "zh_TW", "de_DE", "fr_FR", "ar_AR"]

ROBOTS = '<meta name="robots" content="noindex, follow">\n'
# 検索対象外の言語には AdSense を載せない（AdSense 審査で薄い翻訳ページに広告が付いて見えないように）。
ADSENSE_TAG = re.compile(r'<script async src="https://pagead2\.googlesyndication\.com/pagead/js/adsbygoogle\.js\?client=[^"]+" crossorigin="anonymous"></script>\n')
HREFLANG_ANY = re.compile(r'<link rel="alternate" hreflang="[^"]+" href="[^"]*">\n')
HREFLANG_DROP = re.compile(
    r'<link rel="alternate" hreflang="(?:%s)" href="[^"]*">\n' % "|".join(map(re.escape, NOINDEX_HREFLANGS))
)
LOCALE_DROP = re.compile(
    r'<meta property="og:locale:alternate" content="(?:%s)">\n' % "|".join(NOINDEX_LOCALES)
)


def process_page(path):
    rel = os.path.relpath(path, ROOT)
    h = orig = open(path, encoding="utf-8").read()
    if rel.split(os.sep)[0] in NOINDEX_DIRS:
        if ROBOTS not in h:
            h = h.replace('<meta name="viewport"', ROBOTS + '<meta name="viewport"', 1)
            if ROBOTS not in h:
                raise SystemExit(f"viewport meta not found in {rel}")
        h = HREFLANG_ANY.sub("", h)
        h = ADSENSE_TAG.sub("", h)
    else:
        h = HREFLANG_DROP.sub("", h)
    h = LOCALE_DROP.sub("", h)
    if h != orig:
        open(path, "w", encoding="utf-8").write(h)
        return True
    return False


def process_sitemap():
    path = os.path.join(ROOT, "sitemap.xml")
    s = orig = open(path, encoding="utf-8").read()
    dirs = "|".join(map(re.escape, NOINDEX_DIRS))
    s = re.sub(r'  <url><loc>%s/(?:%s)/[^<]*</loc></url>\n' % (re.escape(DOMAIN), dirs), "", s)
    s = re.sub(r'  <url>\n    <loc>%s/(?:%s)/.*?</url>\n' % (re.escape(DOMAIN), dirs), "", s, flags=re.S)
    s = re.sub(
        r'    <xhtml:link rel="alternate" hreflang="(?:%s)" href="[^"]*"/>\n' % "|".join(map(re.escape, NOINDEX_HREFLANGS)),
        "", s,
    )
    if s != orig:
        open(path, "w", encoding="utf-8").write(s)
        return True
    return False


def main():
    pages = [p for p in glob.glob(os.path.join(ROOT, "**", "index.html"), recursive=True) if "/.git/" not in p]
    changed = sum(process_page(p) for p in pages)
    print(f"pages updated: {changed}/{len(pages)}")
    print("sitemap updated" if process_sitemap() else "sitemap unchanged")


if __name__ == "__main__":
    main()
