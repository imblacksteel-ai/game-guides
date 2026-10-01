"""
英日のみの新ページを作るときの共通部品（2026/09以降の新ページ用）。

    from page_helpers import head_from, footer
    head = head_from("games/kancolle/index.html", "en", "games/foo/", "タイトル", "説明", css="foo.css")
    ... head + "</head>\\n<body>..." + footer("en", "免責文", [(url, 表示名), ...]) ...

head_from は既存ページの <head> を土台に、タイトル・説明・CSS・canonical・hreflang（en/ja/x-default）を
差し替え、`<meta name="available-langs" content="en,ja">` を入れる。OGP/JSON-LD は外すので、
書き出した後に scripts/seo_inject.py → scripts/set_indexing.py を実行すること。
"""
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOMAIN = "https://kouryakulab.com"


def head_from(src, lang, url_path, title, desc, css=None):
    s = open(os.path.join(ROOT, src), encoding="utf-8").read()
    head = s.split("</head>")[0]
    head = re.sub(r'<meta property="og:type".*?</script>\n', "", head, count=1, flags=re.S)
    head = re.sub(r'<meta name="description" content="[^"]*">', lambda m: f'<meta name="description" content="{desc}">', head)
    head = re.sub(r"<title>.*?</title>", lambda m: f"<title>{title}</title>", head)
    if css:
        head = re.sub(r'<link rel="stylesheet" href="/assets/games/[^"]+">',
                      f'<link rel="stylesheet" href="/assets/games/{css}">', head)
    head = re.sub(r'<link rel="alternate" hreflang="[^"]+" href="[^"]*">\n', "", head)
    head = head.replace('<meta name="available-langs" content="en,ja">\n', "")
    en, ja = f"{DOMAIN}/{url_path}", f"{DOMAIN}/ja/{url_path}"
    canon = en if lang == "en" else ja
    head = re.sub(r'<link rel="canonical" href="[^"]*">\n', lambda m:
                  f'<link rel="canonical" href="{canon}">\n<link rel="alternate" hreflang="en" href="{en}">\n'
                  f'<link rel="alternate" hreflang="ja" href="{ja}">\n<link rel="alternate" hreflang="x-default" href="{en}">\n', head)
    head = head.replace('<meta name="viewport"', '<meta name="available-langs" content="en,ja">\n<meta name="viewport"', 1)
    return head


def footer(lang, disc, sources):
    if lang == "en":
        links = ('<a href="/about/">About</a> · <a href="/authors/">Authors</a> · <a href="/editorial-policy/">Editorial Policy</a> · '
                 '<a href="/contact/">Contact</a> · <a href="/terms/">Terms of Use</a> · <a href="/privacy/">Privacy Policy</a>')
    else:
        links = ('<a href="/ja/about/">サイトについて</a> · <a href="/ja/authors/">執筆者について</a> · <a href="/ja/editorial-policy/">編集方針</a> · '
                 '<a href="/ja/contact/">お問い合わせ</a> · <a href="/ja/terms/">利用規約</a> · <a href="/ja/privacy/">プライバシーポリシー</a>')
    src = "\n".join(f'      <a href="{u}" target="_blank" rel="noopener">{n}</a>' for u, n in sources)
    return f'''<footer>
  <div class="wrap">
    <div class="disclaimer">{disc}</div>
    <div class="sources">
      {"Sources:" if lang == "en" else "情報源："}
{src}
    </div>
  </div>
  <nav class="wrap site-links" aria-label="{"Site links" if lang == "en" else "サイトリンク"}">{links}</nav>
</footer>'''


def add_to_sitemap(url_path):
    """英日2URLの組を sitemap.xml の末尾に追加する（既にあれば何もしない）。"""
    p = os.path.join(ROOT, "sitemap.xml")
    s = open(p, encoding="utf-8").read()
    en, ja = f"{DOMAIN}/{url_path}", f"{DOMAIN}/ja/{url_path}"
    if f"<loc>{en}</loc>" in s:
        return False
    blk = (f"\n  <url>\n    <loc>{en}</loc>\n"
           f'    <xhtml:link rel="alternate" hreflang="en" href="{en}"/>\n'
           f'    <xhtml:link rel="alternate" hreflang="ja" href="{ja}"/>\n'
           f'    <xhtml:link rel="alternate" hreflang="x-default" href="{en}"/>\n'
           f"  </url>\n  <url><loc>{ja}</loc></url>\n")
    open(p, "w", encoding="utf-8").write(s.replace("\n</urlset>", blk + "\n</urlset>"))
    return True
