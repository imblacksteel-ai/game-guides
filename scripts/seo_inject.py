#!/usr/bin/env python3
"""
kouryakulab.com 向けSEO/OGPメタデータ一括挿入スクリプト。

やること（新規ページに対してのみ。既に挿入済みのページはスキップされ、何度実行しても安全）:
  - favicon / apple-touch-icon の <link>
  - Google Fonts への <link rel="preconnect"> の除去（フォントは assets/fonts/ で自前ホスト）
  - Open Graph / Twitter Card メタタグ（7言語分の og:locale:alternate 込み）
  - JSON-LD構造化データ（hub/privacyページ = WebSite、ゲームガイド = Article + BreadcrumbList）
  - フッターへの横断リンク行（About / Authors / Editorial Policy / Contact / Terms of Use /
    Privacy Policy。各ページは自分自身をリンク一覧から除外する）
  - Google AdSenseの広告コード（全ページ、<head>の先頭付近）
  - Google Analytics (gtag.js)のトラッキングコード（全ページ、<head>の先頭付近）
  - hero内「更新日」ファクトタイル（ゲームガイドページのみ）
  - フッター「他の攻略ガイド」相互リンク（ゲームガイドページのみ、自分自身は除外）

対象ページは自動検出（ルート・ja/・ko/・zh/・de/・fr/・ar/ 配下の
index.html、games/<slug>/index.html、privacy/index.html を全て走査）。
新しいゲームを追加した時は、7言語ぶんのHTMLを作った後にこのスクリプトを実行するだけでよい。

OG画像について:
  ゲームガイドは assets/og/og-<slug>.png（1200x630）を参照する。
  無ければ assets/og/og-hub.png にフォールスクし、その旨を警告表示する。
  新しいゲームを追加したら、assets/og/og-<slug>.svg を作って
      rsvg-convert -w 1200 -h 630 assets/og/og-<slug>.svg -o assets/og/og-<slug>.png
  で生成してから再実行すると、専用OG画像が使われるようになる。

使い方: python3 scripts/seo_inject.py
"""
import re
import json
import os
import glob

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOMAIN = "https://kouryakulab.com"

LOCALE = {
    "en": "en_US", "ja": "ja_JP", "ko": "ko_KR", "zh-Hans": "zh_CN",
    "de": "de_DE", "fr": "fr_FR", "ar": "ar_AR",
}
LANG_DIRS = ["", "ja", "ko", "zh", "de", "fr", "ar"]  # "" = ルート(英語)

ADSENSE_CLIENT = "ca-pub-2939651190150074"
GA_MEASUREMENT_ID = "G-2DMV4KX041"

PRIVACY_LABEL = {
    "en": "Privacy Policy", "ja": "プライバシーポリシー", "ko": "개인정보처리방침",
    "zh-Hans": "隐私政策", "de": "Datenschutzerklärung", "fr": "Politique de confidentialité",
    "ar": "سياسة الخصوصية",
}

ABOUT_LABEL = {
    "en": "About", "ja": "サイトについて", "ko": "사이트 소개",
    "zh-Hans": "关于本站", "de": "Über uns", "fr": "À propos",
    "ar": "حول الموقع",
}

AUTHORS_LABEL = {
    "en": "Authors", "ja": "執筆者について", "ko": "필자 소개",
    "zh-Hans": "作者信息", "de": "Autoren", "fr": "Auteurs",
    "ar": "الكتّاب",
}

EDITORIAL_POLICY_LABEL = {
    "en": "Editorial Policy", "ja": "編集方針", "ko": "편집 방침",
    "zh-Hans": "编辑方针", "de": "Redaktionelle Richtlinien", "fr": "Charte éditoriale",
    "ar": "السياسة التحريرية",
}

CONTACT_LABEL = {
    "en": "Contact", "ja": "お問い合わせ", "ko": "문의하기",
    "zh-Hans": "联系我们", "de": "Kontakt", "fr": "Contact",
    "ar": "تواصل معنا",
}

TERMS_LABEL = {
    "en": "Terms of Use", "ja": "利用規約", "ko": "이용약관",
    "zh-Hans": "使用条款", "de": "Nutzungsbedingungen", "fr": "Conditions d'utilisation",
    "ar": "شروط الاستخدام",
}

SITE_LINKS_ARIA = {
    "en": "Site links", "ja": "サイトリンク", "ko": "사이트 링크",
    "zh-Hans": "网站链接", "de": "Website-Links", "fr": "Liens du site",
    "ar": "روابط الموقع",
}

# フッターの横断リンク行に表示する順番。各ページは自分自身をこの中から除外して表示する。
SITE_LINK_ORDER = ["about", "authors", "editorial-policy", "contact", "terms", "privacy"]
SITE_LINK_LABELS = {
    "about": ABOUT_LABEL,
    "authors": AUTHORS_LABEL,
    "editorial-policy": EDITORIAL_POLICY_LABEL,
    "contact": CONTACT_LABEL,
    "terms": TERMS_LABEL,
    "privacy": PRIVACY_LABEL,
}

UPDATED_LABEL = {
    "en": "Updated", "ja": "更新日", "ko": "업데이트",
    "zh-Hans": "更新时间", "de": "Aktualisiert", "fr": "Mis à jour",
    "ar": "آخر تحديث",
}
UPDATED_VALUE = "2026.09"

MORE_GUIDES_LABEL = {
    "en": "More Guides", "ja": "他の攻略ガイド", "ko": "다른 공략 가이드",
    "zh-Hans": "更多攻略指南", "de": "Weitere Guides", "fr": "Plus de guides",
    "ar": "المزيد من الأدلة",
}

# slug -> {lang: display name}. 新しいゲームを追加したらここに1行足す。
GAME_NAMES = {
    "haran-suisekai": {
        "en": "Wild Water World", "ja": "波乱水世界", "ko": "Wild Water World",
        "zh-Hans": "Wild Water World", "de": "Wild Water World", "fr": "Wild Water World",
        "ar": "Wild Water World",
    },
    "kancolle": {
        "en": "KanColle", "ja": "艦これ", "ko": "KanColle",
        "zh-Hans": "KanColle", "de": "KanColle", "fr": "KanColle", "ar": "KanColle",
    },
    "srwdd": {
        "en": "Super Robot Wars DD", "ja": "スパロボDD", "ko": "Super Robot Wars DD",
        "zh-Hans": "Super Robot Wars DD", "de": "Super Robot Wars DD", "fr": "Super Robot Wars DD",
        "ar": "Super Robot Wars DD",
    },
    "deresute": {
        "en": "Deresute (CGSS)", "ja": "デレステ", "ko": "Deresute (CGSS)",
        "zh-Hans": "Deresute (CGSS)", "de": "Deresute (CGSS)", "fr": "Deresute (CGSS)",
        "ar": "Deresute (CGSS)",
    },
}


def esc(s):
    return s.replace("&", "&amp;").replace('"', "&quot;")


def find_pages():
    pages = []
    for d in LANG_DIRS:
        base = os.path.join(ROOT, d)
        hub = os.path.join(base, "index.html")
        if os.path.isfile(hub):
            pages.append(hub)
        pages += sorted(glob.glob(os.path.join(base, "games", "*", "index.html")))
        pages += sorted(glob.glob(os.path.join(base, "games", "*", "*", "index.html")))
        privacy = os.path.join(base, "privacy", "index.html")
        if os.path.isfile(privacy):
            pages.append(privacy)
        for slug in ("about", "authors", "editorial-policy", "contact", "terms"):
            p = os.path.join(base, slug, "index.html")
            if os.path.isfile(p):
                pages.append(p)
    return pages


def process(path):
    rel = os.path.relpath(path, ROOT).replace(os.sep, "/")
    content = open(path, encoding="utf-8").read()

    lang = re.search(r'<html lang="([^"]+)"', content).group(1)
    title = re.search(r"<title>(.*?)</title>", content, re.S).group(1).strip()
    desc = re.search(r'<meta name="description" content="([^"]*)"', content).group(1)
    canonical = re.search(r'<link rel="canonical" href="([^"]+)"', content).group(1)

    is_guide = "/games/" in rel or rel.startswith("games/")
    self_slug = None
    for slug in SITE_LINK_ORDER:
        if f"/{slug}/" in rel or rel.startswith(f"{slug}/"):
            self_slug = slug
            break
    # トップレベルのゲームガイド（games/<slug>/index.html）か、その下のクラスターページ（games/<slug>/<topic>/index.html）かを判定。
    # クラスターページには More Guides / Updated タイル は付けない（独自の「フルガイドに戻る」導線を手書きするため）。
    games_tail = rel.split("games/")[1] if is_guide else ""
    is_top_level_guide = is_guide and games_tail.count("/") == 1
    prefix_seg = rel.split("/")[0]
    prefix = f"/{prefix_seg}/" if prefix_seg in LANG_DIRS and prefix_seg != "" else "/"
    site_name = "攻略ラボ" if lang == "ja" else "Kouryaku Lab"
    og_locale = LOCALE.get(lang, "en_US")
    all_locales = [v for v in LOCALE.values() if v != og_locale]

    if is_guide:
        slug = rel.split("games/")[1].split("/")[0]
        og_image_file = os.path.join(ROOT, "assets", "og", f"og-{slug}.png")
        if os.path.isfile(og_image_file):
            og_image = f"{DOMAIN}/assets/og/og-{slug}.png"
        else:
            print(f"  ! assets/og/og-{slug}.png が無いので og-hub.png で代用: {rel}")
            og_image = f"{DOMAIN}/assets/og/og-hub.png"
        og_type = "article"
        theme_color = "#12414d"
        home_url = canonical.split("games/")[0]
    else:
        og_image = f"{DOMAIN}/assets/og/og-hub.png"
        og_type = "website"
        theme_color = "#2f6f4f"
        home_url = canonical

    changed = False

    # --- Google AdSense (as close to the top of <head> as possible) ---
    if "pagead2.googlesyndication.com" not in content:
        adsense = (
            f'<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client={ADSENSE_CLIENT}" '
            'crossorigin="anonymous"></script>\n'
        )
        content = re.sub(
            r'(<meta charset="UTF-8">\n)',
            r"\1" + adsense,
            content,
            count=1,
        )
        changed = True

    # --- Google Analytics (gtag.js) ---
    if GA_MEASUREMENT_ID not in content:
        ga = (
            f'<script async src="https://www.googletagmanager.com/gtag/js?id={GA_MEASUREMENT_ID}"></script>\n'
            "<script>\n"
            "  window.dataLayer = window.dataLayer || [];\n"
            "  function gtag(){dataLayer.push(arguments);}\n"
            "  gtag('js', new Date());\n"
            f"  gtag('config', '{GA_MEASUREMENT_ID}');\n"
            "</script>\n"
        )
        content = re.sub(
            r'(<meta charset="UTF-8">\n)',
            r"\1" + ga,
            content,
            count=1,
        )
        changed = True

    # --- favicon ---
    if 'rel="icon"' not in content:
        icons = (
            '<link rel="icon" href="/assets/favicon.svg" type="image/svg+xml">\n'
            '<link rel="icon" href="/assets/favicon-32.png" sizes="32x32" type="image/png">\n'
            '<link rel="apple-touch-icon" href="/assets/apple-touch-icon.png">\n'
        )
        content = content.replace('<meta name="viewport"', icons + '<meta name="viewport"', 1) \
            if '<link rel="preconnect"' not in content else content
        # viewport行の直後に挿入（存在しない場合はhead先頭付近を想定してcharsetの後ろに）
        if icons not in content:
            content = re.sub(
                r'(<meta name="viewport"[^>]*>\n)',
                r"\1" + icons,
                content,
                count=1,
            )
        changed = True

    # --- remove Google Fonts preconnect ---
    # Fonts are self-hosted under /assets/fonts/. A preconnect alone still opens a
    # connection to Google and sends the visitor's IP, so strip any left over.
    stripped = re.sub(
        r'<link rel="preconnect" href="https://fonts\.(?:googleapis|gstatic)\.com"[^>]*>\n',
        "",
        content,
    )
    if stripped != content:
        content = stripped
        changed = True

    # --- OGP / Twitter / JSON-LD ---
    if 'property="og:type"' not in content:
        og_block = (
            f'<meta property="og:type" content="{og_type}">\n'
            f'<meta property="og:site_name" content="{esc(site_name)}">\n'
            f'<meta property="og:locale" content="{og_locale}">\n'
            + "".join(f'<meta property="og:locale:alternate" content="{loc}">\n' for loc in all_locales)
            + f'<meta property="og:title" content="{esc(title)}">\n'
            f'<meta property="og:description" content="{esc(desc)}">\n'
            f'<meta property="og:url" content="{canonical}">\n'
            f'<meta property="og:image" content="{og_image}">\n'
            '<meta property="og:image:width" content="1200">\n'
            '<meta property="og:image:height" content="630">\n'
            '<meta name="twitter:card" content="summary_large_image">\n'
            f'<meta name="twitter:title" content="{esc(title)}">\n'
            f'<meta name="twitter:description" content="{esc(desc)}">\n'
            f'<meta name="twitter:image" content="{og_image}">\n'
            f'<meta name="theme-color" content="{theme_color}">'
        )

        if is_guide:
            graph = [
                {
                    "@type": "Article",
                    "headline": title,
                    "description": desc,
                    "inLanguage": lang,
                    "url": canonical,
                    "isPartOf": {"@type": "WebSite", "name": site_name, "url": home_url},
                },
                {
                    "@type": "BreadcrumbList",
                    "itemListElement": [
                        {"@type": "ListItem", "position": 1, "name": site_name, "item": home_url},
                        {"@type": "ListItem", "position": 2, "name": title, "item": canonical},
                    ],
                },
            ]
            ld = {"@context": "https://schema.org", "@graph": graph}
        else:
            ld = {
                "@context": "https://schema.org",
                "@type": "WebSite",
                "name": site_name,
                "url": canonical,
                "inLanguage": lang,
                "description": desc,
            }

        ld_block = f'<script type="application/ld+json">\n{json.dumps(ld, ensure_ascii=False, indent=2)}\n</script>'
        content = content.replace("</head>", og_block + "\n" + ld_block + "\n</head>")
        changed = True

    # --- "Updated" fact tile in the hero (top-level guide pages only) ---
    if is_top_level_guide and 'data-fact="updated"' not in content:
        updated_label = UPDATED_LABEL.get(lang, "Updated")
        fact_tile = f'        <div class="fact" data-fact="updated"><div class="k">{esc(updated_label)}</div><div class="v tag-mono">{UPDATED_VALUE}</div></div>\n'
        marker = '\n      </div>\n    </div>\n  </div>\n</div>\n\n<nav class="tabs">'
        assert marker in content, f"fact-strip closing marker not found in {rel}"
        content = content.replace(marker, "\n" + fact_tile + marker.lstrip("\n"), 1)
        changed = True

    # --- "More Guides" cross-links to the other games (top-level guide pages only) ---
    if is_top_level_guide and "more-guides" not in content:
        slug_self = rel.split("games/")[1].split("/")[0]
        links = []
        for other_slug, names in GAME_NAMES.items():
            if other_slug == slug_self:
                continue
            name = names.get(lang, names["en"])
            links.append(f'<a href="{prefix}games/{other_slug}/">{esc(name)}</a>')
        more_guides_label = MORE_GUIDES_LABEL.get(lang, "More Guides")
        more_guides_block = (
            '  <div class="wrap more-guides">\n'
            f'    <h3>{esc(more_guides_label)}</h3>\n'
            '    <div class="more-guides-links">\n      ' + "\n      ".join(links) + "\n    </div>\n  </div>\n"
        )
        content = content.replace("<footer>\n  <div class=\"wrap\">\n", "<footer>\n" + more_guides_block + "  <div class=\"wrap\">\n", 1)
        changed = True

    # --- footer site-links nav (About / Authors / Editorial Policy / Contact / Terms / Privacy Policy,
    #     excluding whichever of those the current page itself is) ---
    if "site-links" not in content:
        link_htmls = []
        for slug in SITE_LINK_ORDER:
            if slug == self_slug:
                continue
            label = SITE_LINK_LABELS[slug].get(lang, SITE_LINK_LABELS[slug]["en"])
            link_htmls.append(f'<a href="{prefix}{slug}/">{esc(label)}</a>')
        aria_label = SITE_LINKS_ARIA.get(lang, "Site links")
        block = f'  <nav class="wrap site-links" aria-label="{esc(aria_label)}">' + " · ".join(link_htmls) + "</nav>\n"
        # 旧バージョン（class="wrap privacy-wrap"）が残っていれば削除してから差し替える
        content = re.sub(r'[ \t]*<div class="wrap privacy-wrap">.*?</div>\n?', "", content, flags=re.S)
        content = content.replace("</footer>", block + "</footer>")
        changed = True

    if changed:
        open(path, "w", encoding="utf-8").write(content)
        print(f"OK: {rel}  (lang={lang}, type={'guide' if is_guide else 'hub'})")
    else:
        print(f"SKIP (already up to date): {rel}")


if __name__ == "__main__":
    for p in find_pages():
        process(p)
