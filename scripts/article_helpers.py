"""
分析記事（英日）を書くときの共通部品。page_helpers.head_from / footer と組み合わせて使う。

    from article_helpers import build_article
    build_article("games/kancolle/fatigue/", "en", meta, body_html, sources, css="kancolle.css",
                  base="games/kancolle/expedition-requirements/index.html")

meta = dict(title, desc, back, eyebrow, h1, sub, links=[(href, label), ...])
body_html は <main> の中身。分析記事の注記（analysis_note）を冒頭に入れること。
"""
import os
from page_helpers import ROOT, head_from, footer


def steps(items, indent="      "):
    return "\n".join(f'{indent}<li><span class="n">{i}</span><span>{x}</span></li>' for i, x in enumerate(items, 1))


def table(head, rows, cls="glossary"):
    h = "".join(f"<th>{x}</th>" for x in head)
    r = "\n".join("        <tr>" + "".join(f"<td>{c}</td>" for c in row) + "</tr>" for row in rows)
    return (f'    <div class="table-scroll">\n      <table class="{cls}">\n        <thead><tr>{h}</tr></thead>\n'
            f"        <tbody>\n{r}\n        </tbody>\n      </table>\n    </div>")


def section(num, title, inner, first=False):
    pad = "0" if first else "32px 0"
    return (f'  <section style="padding-block:{pad};">\n'
            f'    <div class="sec-head"><span class="sec-num tag-mono">{num:02d}</span><h2>{title}</h2></div>\n'
            f"{inner}\n  </section>\n")


def analysis_note(lang, what):
    if lang == "en":
        return (f'    <div class="callout"><b>An analysis-based guide:</b> this guide is based on our analysis of {what}. '
                "It describes what the data shows and is not a guarantee of results.</div>")
    return f'    <div class="callout"><b>分析に基づく記事です：</b>この記事は{what}を分析してまとめたもの。データ上の傾向を示すもので、結果を保証するものではない。</div>'


def faq(items):
    out = []
    for q, a in items:
        out.append(f'      <h3 style="font-size:.98rem;margin:0 0 6px;">{q}</h3>\n'
                   f'      <p style="color:var(--ink-dim);font-size:.93rem;margin:0 0 14px;">{a}</p>')
    return '    <div class="panel">\n' + "\n".join(out) + "\n    </div>"


def build_article(path, lang, meta, body, sources, css, base):
    head = head_from(base, lang, path, meta["title"], meta["desc"], css=css)
    disc = meta.get("disc") or (
        "This is an unofficial, fan-made, analysis-based guide. It is not a guarantee of results, and game updates may change any of it."
        if lang == "en" else
        "本ページは非公式のファンメイドで、分析に基づく記事です。結果を保証するものではなく、ゲームのアップデートで内容が変わる可能性があります。")
    links = "\n".join(f'      <a href="{h}">{n}</a>' for h, n in meta["links"])
    html = f'''{head}</head>
<body>

<div class="hero">
  <div class="wrap hero-inner">
    {meta["back"]}
    <div>
      <span class="eyebrow">{meta["eyebrow"]}</span>
      <h1>{meta["h1"]}</h1>
      <p class="sub">{meta["sub"]}</p>
    </div>
  </div>
</div>

<nav class="tabs">
  <div class="tabs-inner">
    <div class="tabs-links"></div>
    <nav id="lang-switch" aria-label="{"Language" if lang == "en" else "言語"}"></nav>
  </div>
</nav>

<main class="wrap" style="padding-block:36px 60px;">
{body}
  <div class="more-guides" style="border-bottom:none;">
    <h3>{"Continue reading" if lang == "en" else "続けて読む"}</h3>
    <div class="more-guides-links">
{links}
    </div>
  </div>

</main>

{footer(lang, disc, sources)}

<script src="/assets/lang-switch.js"></script>
</body>
</html>
'''
    out = os.path.join(ROOT, ("" if lang == "en" else "ja/") + path, "index.html")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    open(out, "w", encoding="utf-8").write(html)
    return out
