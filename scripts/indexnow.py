#!/usr/bin/env python3
"""
IndexNow（Bing・Yandex などに更新URLを即時通知）へ URL を送る。
キーはリポジトリ直下の <32桁hex>.txt（中身もキー）。Google は IndexNow を使わない（Google は sitemap と Search Console）。

使い方:
  python3 scripts/indexnow.py                 # sitemap.xml の全URLを送る
  python3 scripts/indexnow.py --since 2026-10-07   # lastmod がその日以降のURLだけ送る
  python3 scripts/indexnow.py URL [URL...]    # 指定URLだけ送る
"""
import glob
import json
import os
import re
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOST = "kouryakulab.com"


def key():
    for p in glob.glob(os.path.join(ROOT, "*.txt")):
        name = os.path.basename(p)[:-4]
        if re.fullmatch(r"[0-9a-f]{32}", name) and open(p).read().strip() == name:
            return name
    sys.exit("IndexNow key file not found")


def main():
    args = sys.argv[1:]
    sm = open(os.path.join(ROOT, "sitemap.xml"), encoding="utf-8").read()
    if args and args[0] == "--since":
        since = args[1]
        urls = [u for u, d in re.findall(r"<loc>([^<]+)</loc>\s*<lastmod>([^<]+)</lastmod>", sm) if d >= since]
    elif args:
        urls = args
    else:
        urls = re.findall(r"<loc>([^<]+)</loc>", sm)
    if not urls:
        print("nothing to submit"); return
    k = key()
    body = json.dumps({"host": HOST, "key": k, "keyLocation": f"https://{HOST}/{k}.txt", "urlList": urls[:10000]}).encode()
    req = urllib.request.Request("https://api.indexnow.org/indexnow", data=body, headers={"Content-Type": "application/json; charset=utf-8"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            print(f"submitted {len(urls)} URLs: HTTP {r.status}")
    except urllib.error.HTTPError as e:
        print(f"HTTP {e.code}: {e.read().decode()[:300]}"); sys.exit(1)


if __name__ == "__main__":
    main()
