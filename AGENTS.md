# AGENTS.md — 攻略ラボ (kouryakulab.com)

このリポジトリで作業するAIエージェント（Claude Code含む）向けの運用ルール。
目的は2つ：①作業品質の一貫性、②**無駄なトークン消費を減らすこと**。
新しいセッションはまずこのファイルを読み、下記のルールに従うこと。ゼロから調べ直さない。

## プロジェクト概要

- 静的HTMLのゲーム攻略・ツールサイト。GitHub Pages（`imblacksteel-ai/game-guides`）でホスト。
- カスタムドメイン: `kouryakulab.com`（Cloudflare DNS → GitHub Pages、HTTPS強制化済み）。
- 8言語対応: 英語(既定/ルート) / 日本語 `/ja/` / 韓国語 `/ko/` / 中国語簡体字 `/zh/` / 中国語繁体字 `/zh-hant/` / ドイツ語 `/de/` / フランス語 `/fr/` / アラビア語 `/ar/`（RTL）。
- 繁体字 `/zh-hant/` は**手で書かない**。簡体字 `/zh/` から `scripts/build_zh_hant.py`（OpenCC s2twp、台湾語彙）で生成する。簡体字ページを追加・修正したら再生成する。hreflangは `zh-Hant`、og:localeは `zh_TW`。
- ビルドツールなし。素のHTML/CSS/JSのみ。npm等は使っていない。

**インフラはセットアップ済み。以下を再実行しない：**
- ドメイン購入・Cloudflare DNS設定・GitHub Pagesのカスタムドメイン登録・HTTPS証明書発行
- `gh auth login` （認証済み。`gh auth status`で確認できる場合はそれで十分）
- Google Search Console（ドメインプロパティ `kouryakulab.com`、2026/09/26登録）とサイトマップ送信。サイトマップを更新しても再送信は不要（Googleが定期的に読み直す）。ドメインプロパティでは送信欄に `https://kouryakulab.com/sitemap.xml` とフルURLで入れる。

## ディレクトリ構成

```
/index.html                          英語版トップ（正本）
/games/<slug>/index.html             英語版ゲーム攻略ページ
/ja/, /ko/, /zh/, /zh-hant/, /de/, /fr/, /ar/    各言語版（同じ構造をミラー。zh-hantはzhから自動生成）
/assets/site.css                     トップページ共通CSS（全言語共有・1ファイルのみ編集）
/assets/lang-switch.js               言語切替メニュー（全言語共有・1ファイルのみ編集）
/assets/tabs.js                      タブのスクロールスパイ（全言語・全ゲーム共有・1ファイルのみ編集）
/assets/games/<slug>.css             ゲームごとの専用CSS（テーマは自由、構造クラスは統一）
CNAME, robots.txt, sitemap.xml       ドメイン・SEO設定
```

## 新しいゲームを追加する時の手順（この順で。飛ばさない）

1. `games/haran-suisekai/index.html` を**テンプレートとして**読む。クラス名・hreflang構成・言語切替の埋め込み方法をそのまま踏襲する。タブ切り替え（スクロールスパイ）は body末尾で `<script src="/assets/lang-switch.js"></script>` の次に `<script src="/assets/tabs.js"></script>` を置くだけでよい。**このJSを毎回`<script>...</script>`にベタ書きしない**（過去に28ファイルへ複製してしまい、後から`/assets/tabs.js`に切り出した経緯がある）。ゲーム固有のJS（KanColleの計算機のような機能）が必要な場合は、`tabs.js`の読み込みタグの後に別の`<script>...</script>`ブロックを追加する。
2. 攻略情報はWeb検索で集める。ただし**同じゲームを再調査しない** — 一度集めた事実は該当ページのHTML内に残っているので、追記・修正時はまずそのページをReadする。
3. 英語版を先に正本として書く（事実の翻訳元）。他言語はそこから翻訳する。
4. 7言語ぶん（繁体字は5.の後に自動生成）のファイルを新規作成する必要がある場合のみforkサブエージェントを使う（2言語ずつ束ねるなど）。**1〜2ファイルの軽微な修正・誤字修正・追記にforkは使わない** — 自分で直接Editする。
5. 各言語ページの`<head>`にhreflangブロックを追加する（8言語 + x-default、既存ページのブロックをコピーしてcanonicalだけ差し替え）。
6. `sitemap.xml`に新ページのURLを追記する（hreflang alternate込み、既存の`games/haran-suisekai`のブロックをコピーしてURLだけ差し替え）。
7. `assets/og/og-<slug>.svg`をゲームのテーマ色で作り、`rsvg-convert -w 1200 -h 630 assets/og/og-<slug>.svg -o assets/og/og-<slug>.png`でOG画像を生成する（`assets/og/og-haran-suisekai.svg`が参考例）。
8. `python3 scripts/seo_inject.py`を実行し、続けて`python3 scripts/set_indexing.py`を実行する。favicon・OGP/Twitterタグ・JSON-LDを全ページに自動挿入する（冪等なので既存ページは自動でスキップされる）。**このタグ群を手で書かない。**
9. 全言語ぶん揃ってから一括でgit commit・push（言語ごとに小分けでコミットしない）。

## 英日の新ページを作るとき

- `scripts/page_helpers.py` の `head_from`（既存ページのheadを土台にタイトル・説明・CSS・hreflang・available-langsを差し替え）、`footer`、`add_to_sitemap` を使う。一時スクリプトで毎回書き直さない。
- 記事ページは `scripts/article_helpers.py` の `build_article`（`section`/`table`/`steps`/`faq`/`analysis_note`）で組む。艦これハブへのリンク追加は `scripts/add_hub_link.py <slug> "EN" "JA"`、タグ整合チェックは `scripts/check_tags.py <files>`。
- 艦これ英語SEO 30テーマ（2026-10）はすべて公開済み。事実は艦これ攻略Wiki（wikiwiki.jp/kancolle）で確認し、Wiki内で記述が食い違う値（例：1-5明石ドロップの司令部Lv 35/40）は断定せず両論併記する。
- 書き出した後は `python3 scripts/seo_inject.py` → `python3 scripts/set_indexing.py` の順に実行する。
- `.steps li` は横並び（flex）なので、本文に `<b>` などのタグを含む場合は `<li><span class="n">1</span><span>本文</span></li>` と本文を `<span>` で包む（包まないと太字部分が別の列に分かれて崩れる）。

## SEO設定（実装済み・新ページにも自動適用される）

- **hreflang**：各ページの`<head>`に8言語+x-defaultの`<link rel="alternate" hreflang="...">`を設置済み。新ページも手順5参照。
- **canonical / meta description**：全ページに設定済み。新ページ作成時に必ず書くこと（`scripts/seo_inject.py`はこれらを既存の値から読み取って他のタグを組み立てるので、無いとスクリプトがエラーになる）。
- **OGP / Twitter Card**：`scripts/seo_inject.py`が自動生成する。手動で書かない。
- **JSON-LD構造化データ**：hubページ=`WebSite`、ゲームガイド=`Article`+`BreadcrumbList`。`scripts/seo_inject.py`が生成する。
- **OG画像**：ゲームごとに`assets/og/og-<slug>.png`（1200x630）が必要。無いと`og-hub.png`に自動フォールバックする（`scripts/seo_inject.py`実行時に警告が出る）。
- **favicon**：`assets/favicon.svg`ほかをサイト共通で使用。ゲームごとに変える必要はない。
- **sitemap.xml / robots.txt**：ルート直下に設置済み。新ページ追加時は`sitemap.xml`にURLを追記する（手順6）。
- **Webフォント**：Google Fontsは使わず `assets/fonts/` で自前ホストしている（GDPR対策。Google Fontsへの接続は `preconnect` だけでも訪問者のIPが送られる）。各CSSは `@import url('/assets/fonts/fonts.css')` で読み込む。**`fonts.googleapis.com` を新たに参照しない。** `scripts/seo_inject.py` は残っているGoogle Fontsの `preconnect` を除去する。ウェイトの追加は `scripts/build_fonts.py` の `FAMILIES` を編集して再実行（OFLの条件により各フォントの `OFL.txt` を同梱すること）。

新しいゲームを追加した後の確認コマンド（このAGENTS.mdのやり方に沿っていれば全部pass するはず）:
```bash
python3 scripts/seo_inject.py   # 未挿入ページにOGP/JSON-LD/faviconを追加
git diff --stat                 # 想定した言語数ぶんのファイルが変更されているか確認
```

## 検索需要の調べ方（新機能・新ページを選ぶとき）

- 思いつきで作らず、Googleのサジェスト（`suggestqueries.google.com/complete/search?client=firefox&q=...`）で実際に検索されている語を確認する。タイトルはその語を含める。
- 2026年9月時点で需要が見えたが未対応のもの：艦これの**建造レシピ**（kancolle construction / ship recipes）、**遠征ごとの条件**（kancolle expedition requirements / b4 / a2 など）、**英語で遊ぶ方法**（kancolle english / english patch。ただしWikiのチュートリアルが上位を押さえている）。
- 英語圏の制空権計算はnoro6さんの `kc-web`（英語・中国語対応）が強く、正面から競合しない。

## トークン節約ルール

- **同じ情報を二度調べない。** ゲーム事実・デザイン方針・インフラ設定は既存ファイルとこのAGENTS.mdに書いてある。WebFetch/WebSearchは新規ゲームの新規情報を集める時だけ使う。
- **全文書き直しよりEdit。** 既存ページの文言修正・誤字・1セクション追加は`Write`で全体を再生成せず`Edit`で差分適用する。
- **fork/subagentは「並列化して初めて得する量」の時だけ。** 目安：3ファイル以上の独立した翻訳・生成作業が同時に走る場合のみ。1〜2ファイルの修正は自分で直接やる方が速く安い。
- **スクリーンショット・ブラウザ確認ループを作らない。** 静的HTMLの構造確認は`python3`でのタグバランスチェックや`curl`のHTTPステータス確認で十分。見た目の最終確認はartifactのプレビューで1回だけ。
- **CSS/共通JSはトークン化された共通ファイルを編集する。** `site.css`・`lang-switch.js`・`tabs.js`を言語ごとに個別にコピーしない。ゲーム専用CSSとゲーム固有の機能JS（計算機など）だけがゲームごとに独立している。
- **hreflangブロックは使い回す。** 8言語+x-defaultのURLリストは機械的に生成できるので、1ページ分作ったら他はcanonicalの差し替えだけで済ませる。
- **GitHub Pagesのビルド確認は`gh api .../pages/builds/latest`のポーリングで十分。** 無闇に`sleep`を連打しない、`ScheduleWakeup`で数分単位に間隔を空ける。

## ゲームデータ（数値）の扱い

- **攻略サイトから数値を手集めしない。** 艦これのFleet Builderで、調査エージェントが「運」の初期値と近代化改修の上限値を取り違え、8隻ぶん誤掲載した実例がある。ゲーム本体のマスターデータを正とする。
- 艦これの艦娘データは `assets/data/kancolle-ships.json`（全言語共有）。**手編集禁止**。`python3 scripts/build_kancolle_ships.py` で `kcwiki/kancolle-data` の `api_start2`（マスターデータ）から再生成し、`python3 scripts/verify_kancolle_stats.py` で照合する（exit 0 で全一致）。
- 対潜・索敵はマスターデータに存在しない（レベル成長で決まる）ため、この2項目だけWiki由来。Wikiデータはマスターデータと重複項目で99.7%一致を確認済みだが、重複項目は常にマスターデータを採用する。
- 経験値計算機のレベル表は `assets/data/kancolle-exp.json`（**手編集禁止**）。`python3 scripts/build_kancolle_exp.py` でKC3改（MITライセンス）の表から生成し、生成時に日本の攻略Wikiと1レベルずつ照合する（食い違えば書き出さずに止まる）。Wikiのケッコン後の表は「Lv100を0とした累計」なので、比べるのは1レベルごとの必要経験値。レベル上限は2026/05/29にLv188。
- 第二期（2018年）以降、基本経験値はマップ単位ではなく敵編成ごとに決まる。**マップを選ぶと経験値が出るようなプリセットは作らない**（不正確になる）。戦闘結果画面の「基本経験値」を入力してもらう。
- 艦娘データの `remodel_lv` / `remodel_to` はマスターデータの `api_afterlv` / `api_aftershipid` 由来。`remodel_to` は言語に依存しないよう日本語名で持ち、表示側で「英語名 (日本語名)」に変換する。
- Fleet BuilderのロジックとUIは `assets/games/kancolle-fleet-builder.js` に共有。各言語のHTMLは `window.FLEET_I18N` にUI文言だけを持つ。**JSや艦娘データを言語ごとのHTMLに埋め込まない。**
- 遠征条件一覧は `assets/data/kancolle-expeditions.json`（**手編集禁止**）。`python3 scripts/build_kancolle_expeditions.py` でKcanotify（編成条件・資源量。マスターデータに無い）とマスターデータ（名前・時間・隻数・海域・アイテム報酬）から生成し、`python3 scripts/render_kancolle_expeditions.py` で英日ページの表（`<!-- EXPED-TABLE -->` マーカー間）に書き込む。表はSEOのためHTMLに直接埋め込み、JSは絞り込みだけ。
- 建造ページ（`/games/kancolle/construction/`）の表と `assets/data/kancolle-construction.json` は `python3 scripts/build_kancolle_construction.py` で生成（**手編集禁止**）。建造時間はマスターデータ、建造可否はkcwikiのwikiデータで、日本の攻略Wiki（建造）の建造時間一覧表と1隻ずつ照合する。海外艦の秘書艦条件はスクリプト内の `SECRETARY`。定番レシピは攻略Wiki「建造レシピ」の報告値（自己申告なので「目安」と明記）。
- 東京急行（37/38）の条件は**ドラム缶**（大発動艇ではない）。過去に全言語で誤記していた。
- 新しいゲームを追加する前に、GitHubに抽出済みデータのリポジトリがあるか確認する（中国ゲームは中国語名で検索しないとヒットしない）。数値は事実なので掲載可、ただし画像・音声などのアセットや本文テキストの丸ごと転載はしない。

## AdSense 審査対応（2026/09 に「有用性の低いコンテンツ」で却下）

- **インデックス対象は英語・日本語のみ。** ko/zh/zh-hant/de/fr/ar は公開したまま `noindex, follow` にし、hreflang・sitemap・og:locale:alternate から外している。`python3 scripts/set_indexing.py`（冪等）が一括で処理する。この6言語には**AdSenseのタグも載せない**（2026/10/03に外した。seo_inject.py は NOINDEX_DIRS には挿入せず、set_indexing.py が残っていれば除去する）。新ページ追加時は手順8の `seo_inject.py` の後に必ず実行する。言語を戻すときは同スクリプトの `NOINDEX_DIRS` を編集する。
- **2026/09以降の新ページは英語・日本語の2言語だけで作る。** 他の6言語は作らない。`<head>` に `<meta name="available-langs" content="en,ja">` を入れると言語切替メニューが英日だけになる（`assets/lang-switch.js`）。hreflangは en/ja/x-default の3行、sitemapも英日の2URLだけ。
- **地域制限の回避手順・非公式APKの入手方法は載せない。** デレステの `/games/deresute/access/` は「動作が重い・落ちる時の対策」ページ（Namco ID登録＋クラッシュ対策）にしてある。
- **波乱水世界のTier表は複数の公開Tier表の集計。** 元データは `assets/data/www-tier-sources.json`（手で転記）、`python3 scripts/build_www_tier.py` で総合評価（SS=4…C=0の平均、一致度、3件未満は別枠）を計算してTier表ページに書き込む。新しいTier表を見つけたら sources に追加、配信前の暫定表・中国/台湾サーバー基準の表は excluded に理由付きで入れる。同一内容の表は1件として数える。ページ冒頭の「ひとことで言うと」は手書きなので、集計結果が変わったら合わせて直す。ゲーム本体（非公開の商用アプリ）の逆コンパイル・データ抽出はしない（2026/10時点で有志の抽出データも見つかっていない）。
- **ギフトコード（波乱水世界）は「最終確認日」を表示する運用。** 「1日以内に更新」「週1回チェック」のような実際にやっていない頻度は書かない。更新時は国内のまとめサイト2つ（こーどぴあ・あひるのゲーム部屋）と照合し、全言語のコード表（codesページとハブの両方）と最終確認日を書き換える。有効期限は「なし」ではなく「発表なし」。
- **一人称の体験談（「この編成でクリアした」「プレイしてみて」等）は書かない。** 運営者は掲載ゲームを実際にはプレイしていない（2026/10確認）。2-4攻略で架空の体験談を一度公開してしまい、データから導いた編成に差し替えた経緯がある。編成やおすすめをデータから導いた記事は「分析に基づく記事」と冒頭に明記し、根拠のデータと出典を示したうえで「結果を保証するものではない」と書く（定型：EN「An analysis-based guide: … it is not a guarantee …」／JA「分析に基づく記事です：… 保証するものではない」。編集方針ページの「分析に基づく記事について」と対応）。体験談を入れる場合は、本人が実際にプレイした記録だと確認できたものだけにする。
- **分析記事の語り口：** 「ゲームのプロではないが、データを読み込んでいるハイアマチュア」。根拠を示しながら話す（「Wikiの分岐表を読む限り」「データ上は」）、事実と自分の解釈を書き分ける、未確定は「まだ検証中らしい」と正直に書く。架空の体験談（「プレイしてみたら」）は書かない。運営者の方針として、30テーマ等の記事は確認なしで優先度順に作って公開してよい（2026/10/03）。
- **事実でない運営実態を書かない。** 「実プレイで検証」のような記述は削除済み。編集方針・執筆者ページには実際にやっていることだけを書く。
- 審査の再申請は本人が行う。サイト公開から日が浅い・流入が少ないことも却下要因になるため、コンテンツを厚くしてから時間を置いて再申請する方針。

## 学マス（学園アイドルマスター）

- `/games/gakumas/`（ハブ）と `/games/gakumas/rank-calculator/`（評価値計算機）。英日のみ。CSSは `assets/games/gakumas.css`（kancolle.cssの配色違い）。
- 評価値の式・定数は `assets/games/gakumas-rank-calculator.js` に集約。出典は surisuririsu/gakumas-tools（BSD-3）の `utils/produceRank.js`。通常難易度の係数2.3・順位点1700/900/500・スコア換算、ランク境界値は攻略Wiki等と一致を確認済み。レジェンドは評価値Wikiで主要な境目（2.1倍・中間6万/20万・最終60万/200万）だけ確認できている。
- 係数は整数で持つ（`2.3` のまま掛けると 3090×2.3=7106.999… で1ずれる）。
- 英語パッチ（非公式の改造）は扱わない。
- HIFはハブに式の解説だけ載せている（パラメータ×2＋スター性×7.5＋本戦評価点−2000、R1は約70万で減衰・140万で上限、R2は150万で減衰・240万で上限）。**計算機は未作成**：gakumas-toolsはR1スコアを1.2で割ってから換算するが、Wiki等は表示スコアのまま70万/140万と書いており未確定。R2のスター獲得1.5倍も未確認。確定したら作る。
- NIAはアイドル別・ステージ別の実測近似係数が必要で出典がgakumas-toolsのみのため見送り。
- 未対応の需要：サポカの評価。

## Mindustry（オープンソース）

- `/games/mindustry/`（ハブ：生産比率・英日アイテム名）と `/games/mindustry/production-calculator/`。英日のみ。CSSは `assets/games/mindustry.css`。
- 数値は `python3 scripts/build_mindustry_crafters.py` で本体の最新リリースタグの `Blocks.java` とbundle（英日の公式翻訳）から生成し、ページの表も書き込む（**手編集禁止**）。液体はソース上「毎ティック」なので×60、電力も×60で毎秒。GenericCrafterの既定craftTimeは80。
- ドリル（Drill / BurstDrill）も同じスクリプトで生成し、計算機ページの `<!-- MDT-DRILLS -->` に表を書き込む。通常ドリルは (drillTime + 50×硬度) / 倍率 ティック/個 × タイル数、ブーストは暖機も上がるため強度²倍。BurstDrillは硬度無関係・ブーストは強度倍。壁の鉱石（プラズマボーリング）は未対応。
- 書き方が想定外のブロックは推測で埋めずスキップしてログに出す。新バージョンでスキップが増えたらパーサーを直す。
- ハブの「生産比率」の文章は手書き（データから計算した値）。バージョン更新時は値が変わっていないか確認する。日本語のブロック名は公式翻訳に合わせる（例：Multi-Press＝マルチ圧縮機）。

## Shattered Pixel Dungeon（オープンソース）

- `/games/shattered-pixel-dungeon/`（英日）。CSSは `assets/games/spd.css`。
- 近接武器の表は `python3 scripts/build_spd_weapons.py` で最新リリースタグの各武器クラスの min/max/STRReq/defenseFactor の return 式を評価して生成（**手編集禁止**）。武器名は公式翻訳（items(_ja).properties）。ゲーム内の説明文はGPLのテキストなので転載しない（名前と数値だけ）。
- 職業表・筋力の説明・「数値の見方」は手書き（ソースで確認した事実：筋力不足1ごとに命中÷1.5・攻撃時間×1.2、余剰筋力は1回ごとに0〜余剰分、必要筋力は+1/+3/+6/+10…で1ずつ減る）。
- 杖と指輪は `/games/shattered-pixel-dungeon/wands-rings/`。`python3 scripts/build_spd_wands_rings.py` で生成（杖は min/max/initialCharges、指輪は statsInfo の Math.pow(B, level+1) から）。効果の一言説明はスクリプト内の WAND_NOTES / RING_NOTES に自前の文で書く（新しい杖・指輪が増えるとエラーで止まるので追記する）。本文中の日本語名は公式訳に合わせる（例：執念の指輪、魔力の矢の杖）。
- トリンケットは `/games/shattered-pixel-dungeon/trinkets/`。`python3 scripts/build_spd_trinkets.py` で各クラスの `static 関数(int level)` を+0〜+3で評価（return／if-else／switch の3形式のみ対応）。表示の変換と説明はスクリプト内の SPECS に手書き。新しいトリンケットが増えるとエラーで止まるので SPECS に追記する。
- 未対応の需要：artifacts（充填・レベルの仕組みが個別で複雑）。

## Unciv（オープンソース版シヴィライゼーション5）

- `/games/unciv/`（ハブ）、`/civilizations/`（全34文明）、`/units/`（全ユニット）、`/difficulty/`（難易度）、`/policies/`（社会制度＋コスト計算機）、`/wonders/`（遺産）、`/tech-tree/`（技術ツリー）、`/beliefs/`（信仰）、`/buildings/`（建物）、`/combat/`（戦闘の式＋ダメージ計算機）、`/growth-happiness/`（成長と幸福度）、`/great-people/`（偉人）、`/promotions/`（昇進）、`/terrain/`（地形・資源・整備）、`/city-states/`（都市国家）、`/opening/`（序盤：データからの分析記事）、`/victory/`（勝利条件）、`/game-speed/`（速度と開始時代）、`/best-civ/`（文明の選び方：能力の性質で分類した分析記事）、`/vs-civ5/`（シヴィ5との違い：公式ドキュメント docs/Other/Intentional-departures-from-Civ-V.md）。技術ツリーのページに研究コスト計算機（`assets/games/unciv-tech-cost.js`、定数は `window.UNCIV_TECH_CFG`）。英日のみ。CSSは `assets/games/unciv.css`（spd.cssの配色違い）、OG画像は `assets/og/og-unciv.png`。
- 表は `python3 scripts/build_unciv.py` で生成（**手編集禁止**）。yairm210/Unciv（MPL-2.0）の `COMMIT` 時点の `Civ V - Gods & Kings` の JSON（コメント・末尾カンマ入りなので strip() してから読む）と公式日本語訳 `Japanese.properties` から、`<!-- UNCIV-CIVS/UNIQ/UNITS/DIFF/POLICIES/POLICYAI/POLICYCALC/WONDERS/NWONDERS/TECHS/BELIEFS/BUILDINGS -->` マーカー間に書き込む。更新するときは `COMMIT`/`COMMIT_DATE` を差し替え、本文中の「2026-10-02」も合わせて直す。
- 日本語の能力文はUncivと同じテンプレート方式（[ ]を差し替え、条件<...>は本文の前）で公式訳から組み立てる。"Land"→「地上」など、パラメータの誤訳は `PARAM_OVERRIDE` で補正。訳が無いものは英語のまま残り、件数が表示される。
- 難易度の各項目の意味は本体のコードで確認済み：研究/ユニット/建物/社会制度コストは人間プレイヤーのみ（AIは `aiDifficultyLevel` の易しい設定）、`aiCityGrowthModifier` はAIの成長に必要な食料の倍率、`barbarianBonus` は対蛮族の戦闘ボーナス、`turnBarbariansCanEnterPlayerTiles` は蛮族が領土に入れるようになるターン。
- 本文（結論・読み取り）は手書き。データ更新で数値（例：固有ユニット49中24が同性能、AIの勝利志向 科学11/文化9/制覇9/外交5）が変わったら直す。
- 社会制度コスト計算機は `assets/games/unciv-policy-cost.js`（式は PolicyManager.getPolicyCultureCost：(25+(採用数×3)^2.01)×難易度×速度×(1+マップ補正×(都市数−1))、5の倍数に切り捨て。マップ補正 極小〜中0.1/大0.075/極大0.05）。定数は build_unciv.py が `window.UNCIV_POLICY_CFG` としてページに書く。選択肢の日本語は `data-l<小文字のキー>` 属性。
- 技術コストは TechManager.costOfTech で確認済み（難易度は人間のみ、マップ 中1.1/大1.2/極大1.3、1都市ごと+5%/3.75%/2.5%、既知文明の研究済み割合×0.3で割引）。遺産のコストは自前の cost が無ければ解禁技術の列の wonderCost（国家遺産も同じ）。信仰は他の宗教が持っているものは選べない（ReligionManager）。
- 戦闘の式は BattleDamage.kt / BattleConstants.kt（比率 s、m=(((s+3)/4)^4+1)/2、ダメージ=(24+12×乱数)×m（弱い側は1/m）×(1−減ったHP/300)、乱数はターン×タイル位置で固定、要塞化は1ターン+20%で最大+40%、地形は地形特徴の最大値が基本地形を置き換える）。計算機は `assets/games/unciv-combat.js`。
- 成長は CityPopulationManager（15+8(人口−1)+floor((人口−1)^1.5)、市民1人食料2）、不満の段階は GlobalUniques.json（−1〜−10で成長−75%、−10未満で成長停止・生産−50%・戦闘力−33%）。偉人は GreatPersonManager（100×速度で開始し2倍、科学者・技術者・商人・芸術家は「Great Person」グループで閾値を共有、将軍・提督は200から+50）。
- 文明ページの固有ユニット比較表の「追加の能力」は、ユニットの uniques と promotions（固有能力は UnitPromotions.json に隠し昇進として入っている）から置き換え対象との差分を取っている。
- MapSize.kt のコメントにあるシヴィ5のマップ寸法は引数の並びが紛らわしく、Uncivの方が小さいとは言い切れないので書かない。
- MODページ `/mods/` の人気MOD表は `python3 scripts/build_unciv_mods.py`（GitHub の topic:unciv-mod をスター順に40件、確認日を表示）。月1回程度更新する。説明文は作者の英文のまま。
- 未対応の需要：特になし（Uncivは主要な需要をひと通りカバー済み・2026/10）。マルチプレイは `/multiplayer/`（docs/Other/Multiplayer.md より。コミュニティのサーバーは名指しで勧めない）。文明ごとの個別ページは中身が薄くなりやすいので作らない（AdSenseの低品質判定対策）。

## Endless Sky（オープンソース、GPL-3.0）

- `/games/endless-sky/`（ハブ）、`/first-ship/`、`/making-money/`、`/ships/`、`/weapons/`、`/outfits/`（エンジン・電力・シールド・冷却）、`/licenses/`（免許）。英日のみ。CSSは `assets/games/endless-sky.css`、OG画像は `assets/og/og-endless-sky.png`。公式の日本語訳がないので、船・装備・星系名は日本語版でも英語のまま。
- 表は `python3 scripts/build_endless_sky.py` で生成（**手編集禁止**）。endless-sky/endless-sky の `COMMIT` 時点の `data/`（タブのインデントで階層を表す独自テキスト形式）を読み、`<!-- ES-SHIPS/WEAPONS/TRADE/STARTER/OUTFITS/LICENSES -->` に書き込む。銀河は開始時点の状態（イベントで変わる店・政府は反映しない）。ゲーム内の説明文（GPLのテキスト）は転載しない。
- ソースで確認済みの式：最高速度 60×推力/抵抗、加速 3600×推力/質量、旋回 60×turn/質量（ShipInfoDisplay.cpp）。価格 = 基準 − 100×erf(在庫/20000)（System.cpp、基準から±100程度）。依頼の報酬 = 固定額 +（ジャンプ数+1）× 積載量 × 倍率、積載量 = 貨物トン + 10×乗客、`payment` 単独は倍率150（MissionAction.cpp・Mission.cpp）。乗客の依頼は +2000。
- 武器のDPSは 60/reload × 1発のダメージ（サブミュニションは再帰で加算）、射程は velocity×lifetime。連射・誘導・爆発半径は未反映（本文に明記）。
- 免許はミッションの `set "license: X"` か、装備屋で売られる「X License」装備で得る。どちらも見つからない免許は「データ上に入手方法が見つからない」と書く（海軍・Gegno・Avgiなど。断定しない）。
- 未対応の需要：ストーリーの分岐、採掘（minables）。

## 翻訳の一貫性ルール

- **繁体字版の生成時の注意**：簡体→繁体変換は日本語の漢字も書き換える（装備→裝備）ため、`class="jp"`/`class="romaji"` の要素とカナを含む語は変換から保護している。ゲーム内の日本語表記はこれらのクラスで囲むこと。
- 繁体字変換では、カナに隣接する漢字も日本語として保護する。そのため**中国語の文を日本語の語に直接つなげない**（例：「进行ケッコンカッコカリ」は「进行」が簡体字のまま残る）。「」や括弧で区切ること。`build_zh_hant.py` は該当を検出するとエラーで止まる。
- **繁体字圏では事実が変わるゲームがある**：スパロボDDは台港澳向けの公式繁体中文版がある（公式名「超級機器人大戰DD」、srw-dd-tw.suparobo.jp）。簡体字版の「公式中文版なし」は繁体字版では誤りになるので、`build_zh_hant.py` の `OVERRIDES` で上書きしている。簡体字版の該当文を変えたら `OVERRIDES` も直す（見つからないとエラーで止まる）。

- ブランド名 `Kouryaku Lab` は全言語で英語表記のまま（ロゴ的な固有名詞として統一）。日本語版のみ「攻略ラボ」を使う（もともとの正式名）。
- ゲームの国際版タイトルが確認できる場合はそれを正本にする（例: 波乱水世界 → 英語圏では "Wild Water World"）。確認できない言語では英語の国際版タイトルをそのまま流用し、存在しないローカライズ名を創作しない。
- キャラクター名は「二つ名＋名前」構造。ラテン文字圏（EN/DE/FR）は名前部分を英語のまま維持し二つ名だけ翻訳。非ラテン文字圏（JA/KO/ZH/AR）は二つ名を翻訳し名前部分を音訳。表記ゆれを避けるため、同じキャラが複数箇所（リセマラ表・ランキング表・キャラカード）に出る場合は同一訳語で統一する。
- 事実（配信日・OS対応・ガチャ手順など）は翻訳元から追加・誇張・削除しない。

## 避けるべきこと

- ドメイン購入・AdSense申請など決済/本人確認が絡む操作を代行しない（本人にお願いする）。
- `.claude/`はコミットしない（`.gitignore`済み）。
- 既存の言語ディレクトリ構造・URL規則（`/xx/games/<slug>/`）を変更しない。変えるとhreflangとsitemapが壊れる。
