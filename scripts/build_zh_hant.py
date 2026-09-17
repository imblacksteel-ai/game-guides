#!/usr/bin/env python3
"""
簡体字版 zh/ から繁体字版 zh-hant/ を生成する。

OpenCC の s2twp（台湾の語彙まで変換: 服务器→伺服器、概率→機率 など）を使う。
単純な字形変換ではなく語彙も置き換わるため、機械翻訳より誤りが少なく、事実の
数値や構造は簡体字版と完全に一致する。

注意点（変換してはいけないもの）:
  - ゲーム内の日本語表記（class="jp" / class="romaji" の要素、および文中の
    カナを含む語）。簡体→繁体の変換は日本語の漢字も書き換えてしまう（装備→裝備）。
  - OGP/JSON-LDは変換せず削除し、scripts/seo_inject.py に再生成させる
    （og:locale を zh_TW にし、代替ロケールの並びも他言語と揃えるため）。

公式の繁体中文タイトルが確認できたゲームだけ名称を置き換える（AGENTS.mdの規則）。

依存: pip install opencc（サイト自体の依存ではないので一時venvで可）
  python3 -m venv /tmp/occ && /tmp/occ/bin/pip install opencc
  /tmp/occ/bin/python scripts/build_zh_hant.py
"""
import glob
import os
import re

import opencc

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC, DST = "zh", "zh-hant"
DOMAIN = "https://kouryakulab.com"

# 公式の繁体中文タイトルが確認できたものだけ。確認できないものは英語名のまま。
#   超級機器人大戰DD: 公式台港澳版 https://srw-dd-tw.suparobo.jp/
OFFICIAL_TITLES = {
    "Super Robot Wars DD": "超級機器人大戰DD",
}

# s2twp が拾わない台湾の慣用表現
PHRASES = {
    "本地化": "在地化",
    "伙伴": "夥伴",
}

# 繁体字圏にだけ当てはまる事実の上書き（変換後の文に対して適用）。
# スパロボDDは台港澳向けの公式繁体中文版がある（srw-dd-tw.suparobo.jp、2019.08.21配信）ため、
# 簡体字版の「公式中文版なし／日本語のみ」をそのまま変換すると誤りになる。
# 置換元が見つからない場合はエラーで止める（簡体字版の文面が変わったら見直すこと）。
OVERRIDES = {
    "games/srwdd/index.html": [
        ("沒有官方中文/英文版——本頁用簡明的語言整理了抽卡、前期攻略和連鎖系統。",
         "台灣、香港、澳門有官方繁體中文版——本頁整理了抽卡、前期攻略和連鎖系統。"),
        ('<div class="v tag-mono">僅日語</div>',
         '<div class="v tag-mono">日語／繁體中文</div>'),
        ("與系列大多數主機作品不同，本作至今沒有官方在地化版本，即便系列其他作品已有。這個頁面是為已經在玩日文版、但想要一份清晰參考資料的玩家準備的。",
         "除日文版外，台灣、香港、澳門另有官方繁體中文版。本頁內容以日文版為準整理，繁體中文版遊戲內的部分名稱譯法可能與本頁不同。"),
        ("所涉遊戲沒有官方英文/中文在地化版本。",
         "內容以日文版為準整理，繁體中文版遊戲內的名稱譯法可能與本頁不同。"),
    ],
    "index.html": [
        ("抽卡目標、新手上路指南、連鎖系統傷害加成表與核心術語——沒有官方在地化的高達/EVA聯動RPG。",
         "抽卡目標、新手上路指南、連鎖系統傷害加成表與核心術語——高達/EVA聯動戰術RPG（台港澳有官方繁中版）。"),
    ],
}

JP_ELEMENT = re.compile(r'<(\w+)\b[^>]*\bclass="(?:jp|romaji)"[^>]*>.*?</\1>', re.S)
# カナを1文字以上含む連続した日本語表記（前後の漢字・長音・中黒・英数字を含めて保護）
JP_RUN = re.compile(r"[々一-鿿ー・0-9A-Za-z]*"
                    r"[぀-ヿ]"
                    r"[぀-ヿ々一-鿿ー・0-9A-Za-z]*")

converter = opencc.OpenCC("s2twp")


def convert_text(text):
    kept = []

    # プレースホルダーは私用領域の文字にする。OpenCCはC文字列で処理するため
    # NUL(\x00)を使うとそこで文字列が切れ、本文が欠落する。
    def hold(m):
        kept.append(m.group(0))
        return f"\ue000{len(kept) - 1}\ue001"

    text = JP_ELEMENT.sub(hold, text)
    text = JP_RUN.sub(hold, text)
    text = converter.convert(text)
    for src, dst in PHRASES.items():
        text = text.replace(src, dst)
    return re.sub("\ue000(\\d+)\ue001", lambda m: kept[int(m.group(1))], text)


def build(src_path):
    rel = os.path.relpath(src_path, os.path.join(ROOT, SRC))
    dst_path = os.path.join(ROOT, DST, rel)
    h = open(src_path, encoding="utf-8").read()

    # OGP / Twitter / JSON-LD は seo_inject.py で再生成する
    h = re.sub(r'<meta property="og:type".*?</script>\n', "", h, count=1, flags=re.S)

    h = convert_text(h)
    for en, zh in OFFICIAL_TITLES.items():
        h = h.replace(en, zh)

    for old, new in OVERRIDES.get(rel.replace(os.sep, "/"), []):
        if old not in h:
            raise SystemExit(f"override source text not found in {rel}: {old[:40]}")
        h = h.replace(old, new)

    h = h.replace('<html lang="zh-Hans">', '<html lang="zh-Hant">')
    h = h.replace(f"{DOMAIN}/zh/", f"{DOMAIN}/{DST}/")
    h = h.replace('"/zh/', f'"/{DST}/')

    # hreflang: 簡体字の行は上のURL置換で /zh-hant/ になってしまうので /zh/ に戻す。
    # 繁体字の行は、簡体字版にまだ無い場合だけ直後に足す（二重登録を防ぐ）。
    has_hant = 'hreflang="zh-Hant"' in h

    def hreflang(m):
        path = m.group(1)
        line = f'<link rel="alternate" hreflang="zh" href="{DOMAIN}/zh/{path}">'
        if not has_hant:
            line += f'\n<link rel="alternate" hreflang="zh-Hant" href="{DOMAIN}/{DST}/{path}">'
        return line

    h = re.sub(rf'<link rel="alternate" hreflang="zh" href="{re.escape(DOMAIN)}/{DST}/([^"]*)">', hreflang, h)

    os.makedirs(os.path.dirname(dst_path), exist_ok=True)
    open(dst_path, "w", encoding="utf-8").write(h)
    return os.path.relpath(dst_path, ROOT)


def main():
    pages = sorted(glob.glob(os.path.join(ROOT, SRC, "**", "index.html"), recursive=True))
    for p in pages:
        print("wrote", build(p))
    print(f"{len(pages)} pages")


if __name__ == "__main__":
    main()
