# AGENTS.md — 攻略ラボ (kouryakulab.com)

このリポジトリで作業するAIエージェント（Claude Code含む）向けの運用ルール。
目的は2つ：①作業品質の一貫性、②**無駄なトークン消費を減らすこと**。
新しいセッションはまずこのファイルを読み、下記のルールに従うこと。ゼロから調べ直さない。

## プロジェクト概要

- 静的HTMLのゲーム攻略・ツールサイト。GitHub Pages（`imblacksteel-ai/game-guides`）でホスト。
- カスタムドメイン: `kouryakulab.com`（Cloudflare DNS → GitHub Pages、HTTPS強制化済み）。
- 7言語対応: 英語(既定/ルート) / 日本語 `/ja/` / 韓国語 `/ko/` / 中国語簡体字 `/zh/` / ドイツ語 `/de/` / フランス語 `/fr/` / アラビア語 `/ar/`（RTL）。
- ビルドツールなし。素のHTML/CSS/JSのみ。npm等は使っていない。

**インフラはセットアップ済み。以下を再実行しない：**
- ドメイン購入・Cloudflare DNS設定・GitHub Pagesのカスタムドメイン登録・HTTPS証明書発行
- `gh auth login` （認証済み。`gh auth status`で確認できる場合はそれで十分）

## ディレクトリ構成

```
/index.html                          英語版トップ（正本）
/games/<slug>/index.html             英語版ゲーム攻略ページ
/ja/, /ko/, /zh/, /de/, /fr/, /ar/    各言語版（同じ構造をミラー）
/assets/site.css                     トップページ共通CSS（全言語共有・1ファイルのみ編集）
/assets/lang-switch.js               言語切替メニュー（全言語共有・1ファイルのみ編集）
/assets/games/<slug>.css             ゲームごとの専用CSS（テーマは自由、構造クラスは統一）
CNAME, robots.txt, sitemap.xml       ドメイン・SEO設定
```

## 新しいゲームを追加する時の手順（この順で。飛ばさない）

1. `games/haran-suisekai/index.html` を**テンプレートとして**読む。クラス名・hreflang構成・言語切替の埋め込み方法をそのまま踏襲する。
2. 攻略情報はWeb検索で集める。ただし**同じゲームを再調査しない** — 一度集めた事実は該当ページのHTML内に残っているので、追記・修正時はまずそのページをReadする。
3. 英語版を先に正本として書く（事実の翻訳元）。他言語はそこから翻訳する。
4. 7言語ぶんのファイルを新規作成する必要がある場合のみforkサブエージェントを使う（2言語ずつ束ねるなど）。**1〜2ファイルの軽微な修正・誤字修正・追記にforkは使わない** — 自分で直接Editする。
5. 各言語ページの`<head>`にhreflangブロックを追加する（7言語 + x-default、既存ページのブロックをコピーしてcanonicalだけ差し替え）。
6. `sitemap.xml`に新ページのURLを追記する（hreflang alternate込み、既存の`games/haran-suisekai`のブロックをコピーしてURLだけ差し替え）。
7. `assets/og/og-<slug>.svg`をゲームのテーマ色で作り、`rsvg-convert -w 1200 -h 630 assets/og/og-<slug>.svg -o assets/og/og-<slug>.png`でOG画像を生成する（`assets/og/og-haran-suisekai.svg`が参考例）。
8. `python3 scripts/seo_inject.py`を実行する。favicon・preconnect・OGP/Twitterタグ・JSON-LDを全ページに自動挿入する（冪等なので既存ページは自動でスキップされる）。**このタグ群を手で書かない。**
9. 全言語ぶん揃ってから一括でgit commit・push（言語ごとに小分けでコミットしない）。

## SEO設定（実装済み・新ページにも自動適用される）

- **hreflang**：各ページの`<head>`に7言語+x-defaultの`<link rel="alternate" hreflang="...">`を設置済み。新ページも手順5参照。
- **canonical / meta description**：全ページに設定済み。新ページ作成時に必ず書くこと（`scripts/seo_inject.py`はこれらを既存の値から読み取って他のタグを組み立てるので、無いとスクリプトがエラーになる）。
- **OGP / Twitter Card**：`scripts/seo_inject.py`が自動生成する。手動で書かない。
- **JSON-LD構造化データ**：hubページ=`WebSite`、ゲームガイド=`Article`+`BreadcrumbList`。`scripts/seo_inject.py`が生成する。
- **OG画像**：ゲームごとに`assets/og/og-<slug>.png`（1200x630）が必要。無いと`og-hub.png`に自動フォールバックする（`scripts/seo_inject.py`実行時に警告が出る）。
- **favicon**：`assets/favicon.svg`ほかをサイト共通で使用。ゲームごとに変える必要はない。
- **sitemap.xml / robots.txt**：ルート直下に設置済み。新ページ追加時は`sitemap.xml`にURLを追記する（手順6）。
- **フォントpreconnect**：`scripts/seo_inject.py`が自動挿入する。

新しいゲームを追加した後の確認コマンド（このAGENTS.mdのやり方に沿っていれば全部pass するはず）:
```bash
python3 scripts/seo_inject.py   # 未挿入ページにOGP/JSON-LD/favicon/preconnectを追加
git diff --stat                 # 想定した言語数ぶんのファイルが変更されているか確認
```

## トークン節約ルール

- **同じ情報を二度調べない。** ゲーム事実・デザイン方針・インフラ設定は既存ファイルとこのAGENTS.mdに書いてある。WebFetch/WebSearchは新規ゲームの新規情報を集める時だけ使う。
- **全文書き直しよりEdit。** 既存ページの文言修正・誤字・1セクション追加は`Write`で全体を再生成せず`Edit`で差分適用する。
- **fork/subagentは「並列化して初めて得する量」の時だけ。** 目安：3ファイル以上の独立した翻訳・生成作業が同時に走る場合のみ。1〜2ファイルの修正は自分で直接やる方が速く安い。
- **スクリーンショット・ブラウザ確認ループを作らない。** 静的HTMLの構造確認は`python3`でのタグバランスチェックや`curl`のHTTPステータス確認で十分。見た目の最終確認はartifactのプレビューで1回だけ。
- **CSSはトークン化された共通ファイルを編集する。** `site.css`や`lang-switch.js`を7言語ぶん個別にコピーしない。ゲーム専用CSS（`assets/games/<slug>.css`）だけがゲームごとに独立している。
- **hreflangブロックは使い回す。** 7言語+x-defaultのURLリストは機械的に生成できるので、1ページ分作ったら他はcanonicalの差し替えだけで済ませる。
- **GitHub Pagesのビルド確認は`gh api .../pages/builds/latest`のポーリングで十分。** 無闇に`sleep`を連打しない、`ScheduleWakeup`で数分単位に間隔を空ける。

## 翻訳の一貫性ルール

- ブランド名 `Kouryaku Lab` は全言語で英語表記のまま（ロゴ的な固有名詞として統一）。日本語版のみ「攻略ラボ」を使う（もともとの正式名）。
- ゲームの国際版タイトルが確認できる場合はそれを正本にする（例: 波乱水世界 → 英語圏では "Wild Water World"）。確認できない言語では英語の国際版タイトルをそのまま流用し、存在しないローカライズ名を創作しない。
- キャラクター名は「二つ名＋名前」構造。ラテン文字圏（EN/DE/FR）は名前部分を英語のまま維持し二つ名だけ翻訳。非ラテン文字圏（JA/KO/ZH/AR）は二つ名を翻訳し名前部分を音訳。表記ゆれを避けるため、同じキャラが複数箇所（リセマラ表・ランキング表・キャラカード）に出る場合は同一訳語で統一する。
- 事実（配信日・OS対応・ガチャ手順など）は翻訳元から追加・誇張・削除しない。

## 避けるべきこと

- ドメイン購入・AdSense申請など決済/本人確認が絡む操作を代行しない（本人にお願いする）。
- `.claude/`はコミットしない（`.gitignore`済み）。
- 既存の言語ディレクトリ構造・URL規則（`/xx/games/<slug>/`）を変更しない。変えるとhreflangとsitemapが壊れる。
