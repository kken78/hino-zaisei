# 当初予算 主な事業（令和3〜8年度）（日野町データポータル・非公式）

https://kken78.github.io/hino-budget/

滋賀県日野町の令和3〜8年度の「当初予算の概要」の附表「令和○年度に取り組む主な事業」に載った事業（6年分で1,031件）を、年度ごとに柱・款・担当課ごとの件数と予算額、事業の一覧で見るページです。柱ごとの事業費の6年分の推移と、同じ事業の年度をまたいだ予算額の推移も示します。附表に載った事業だけを集計したもので、町の予算の全体ではありません。参考として、各年度の当初予算の総額と会計ごとの額（「当初予算の概要」の「予算の規模」の表）を付記しています。

あわせて、令和3〜8年度の補正予算の回ごとの額と、令和3〜7年度の決算の額（「補正予算と決算」の画面。令和8年度は取り込んだ回まで）と、平成27〜令和6年度の財政指標（財政状況資料集の総括表）を載せています。どちらも hino-town-docs の構造化の層（DOCS_SCHEMA.md §13）で、検収の済んだ行だけを使います。

出典：日野町の各年度の「予算」のページ（例 [令和8年度予算](https://www.town.shiga-hino.lg.jp/0000008534.html)）の「当初予算の概要」の附表（PDF）。年度の中の動きは、令和3〜8年度の各回の「補正予算の概要」（PDF）と、令和3〜7年度の「決算審査意見書」（PDF）。財政指標の推移は、各年度の「財政状況資料集」（Excel）。年度ごとの URL は `data.js` と画面の「データについて」にあります。

## ファイル

| ファイル | 中身 |
|---|---|
| `index.html` | 画面。`data.js` を読むだけで、外部の CSS・JavaScript・フォントは読み込まない |
| `DESIGN.md` | 画面の設計の決定（ADR） |
| `inputs.lock.json` | 材料のファイルごとの、リポジトリ・コミット・パス・sha256（3リポジトリ・44ファイル） |
| `data/totals-r3.json` 〜 `data/totals-r8.json` | 各年度の当初予算の会計ごとの予算規模（千円）。各年度の「当初予算の概要」の「予算の規模」の表から転記した正本で、出典の URL・バイト数・sha256・ページ・取得日と、hino-town-docs の台帳の id（`docs_id`）も持つ |
| `data.js` | 材料から作る画面用のファイル。直接編集しない |
| `tools/build_data.py` | 材料を検算して `data.js` を作る（標準ライブラリのみ） |
| `og.png`・`assets/og.svg` | OGP 画像（1200×630）と、その編集元 |
| `tools/watch.py`・`data/watch.tsv` | 町の予算のページの巡回（下の「町のページの巡回」）と、使っている原典12件（各年度の当初予算の概要・附表）の URL・bytes・sha256 |

附表の材料はこのリポジトリに置かず、次の3つのリポジトリから読みます。

| リポジトリ | ファイル | 中身 |
|---|---|---|
| [shiga-hino-plans](https://github.com/kken78/shiga-hino-plans) | `data/fuhyo/fuhyo-r3.json` 〜 `fuhyo-r8.json` | 附表の事業（書式は PLAN_SCHEMA.md §9） |
| | `data/audit_log/fuhyo-r3.tsv` 〜 `fuhyo-r8.tsv` | 附表を原典の PDF と照らした検収の台帳 |
| | `data/source_issues/fuhyo-r3.tsv` 〜 `fuhyo-r8.tsv` | 段3（文章の点検）の指摘と、その判断 |
| | `data/sources_index.tsv` | 原典の台帳（fuhyo-r3〜r8 の行の PDF の URL を使う） |
| | `data/plans/jisshi.json` | 第6次日野町総合計画 実施計画（事業名を引く） |
| [hino-ronten](https://github.com/kken78/hino-ronten) | `links/fuhyo.tsv` | 令和8年度の附表の事業と実施計画の事業の対応の台帳（書式は LINK_SCHEMA.md） |
| | `links/fuhyo-years.tsv` | 附表の事業の年度をまたぐ対応の台帳（LINK_SCHEMA.md「年度の台帳」、DESIGN.md ADR-33） |
| [hino-town-docs](https://github.com/kken78/hino-town-docs) | `data/sources.tsv` | 町の公開資料の台帳（`yosan-r3-gaiyou` 〜 `yosan-r8-gaiyou` の行で、当初予算の概要の URL・バイト数・sha256 を確かめる。補正予算の概要・決算審査意見書・財政状況資料集の題と URL を引く） |
| | `data/struct/hosei-kai.tsv`・`hosei-shiryo.tsv` | 補正予算の回（年度・会計・号、前の回）と、回と資料のページの対応（書式は DOCS_SCHEMA.md §13.6） |
| | `data/struct/hosei-kan.tsv` | 補正予算の款の表の行（歳入合計の行を使い、款の和などの検算に全部の行を使う） |
| | `data/struct/hosei-kaikei.tsv` | 補正予算の特別会計の表・企業会計の表の会計ごとの額 |
| | `data/struct/hosei-maru.tsv` | 補正予算の主な内容の行（特別会計の金額が「－千円」の、繰越明許費だけを定める回を確かめる） |
| | `data/struct/kessan-kai.tsv`・`kessan-gaku.tsv` | 決算の回と額（§13.7。令和3〜7年度の決算審査意見書の円の額を使う） |
| | `data/struct/zaisei-shihyo.tsv`・`zaisei-ichi.tsv` | 財政指標の値（平成27〜令和6年度）と、値の原典の中の位置（§13.8） |
| | `data/struct/audit/hosei-r3.tsv` 〜 `hosei-r8.tsv`・`kessan.tsv`・`zaisei.tsv` | 構造化の層の検収の台帳（§13.10）。使う行がすべて検収済みであることを確かめる |
| | `data/struct/issues/yosan-r5-hosei-02.tsv`・`yosan-r6-hosei-09.tsv`・`yosan-r7-hosei-09.tsv`・`yosan-r8-hosei-06-tsuika.tsv` | 補正予算の原典の誤りの記録（§13.11）。検算で合わない値を、ここに「原典のまま持つ」とされた行のものに限って通す（DESIGN.md ADR-6） |

## 共通の部品

`index.html` の共通の見出し・分野のナビ・ページの一覧・フッターと、その CSS は、[hino-portal](https://github.com/kken78/hino-portal) の `shared/` の正本の写しで、`<!-- portal-shared:〈名前〉 start/end -->` で囲んでいます（DESIGN.md ADR-1）。正本と同じかと文字の大きさ（hino-portal DESIGN.md 5.2、DESIGN.md ADR-3）は `python3 ../hino-portal/shared/check.py --fonts index.html` で、幅 360px と 1024px での文字の実寸と横のはみ出しは `node ../hino-portal/shared/check_mobile.mjs index.html`（Playwright が要る。置き方は hino-portal の shared/README.md）で確かめ、GitHub Actions（`check.yml`）でも確かめます。

## 作り直し方

1. このリポジトリと同じフォルダに、shiga-hino-plans・hino-ronten・hino-town-docs を置く（例 `~/GitHub/hino-budget` と `~/GitHub/shiga-hino-plans`・`~/GitHub/hino-ronten`・`~/GitHub/hino-town-docs`）。
   各リポジトリは `inputs.lock.json` の commit の版にする（`git -C ../shiga-hino-plans checkout <commit>` など）。別の場所に置いたときは、次の手順で `--src <フォルダ>` を付ける。
2. `python3 tools/build_data.py` を実行する。次の検算がすべて合ったときだけ `data.js` が書き出される。合わなければ、合わない行を表示して終了コード 1 で止まる。
   - 材料の sha256 が `inputs.lock.json` と一致する
   - 附表：年度ごとの事業数が 155・166・168・177・184・181 件で、key が重複しない。柱の番号と名前が6年で同じ。年度ごとの予算額の合計を数えて表示する
   - 検収の台帳：全行の checked が ✓ か空で、✓ でない行の note が PLAN_SCHEMA §11.3 の理由の表にある。照合の状況（対象・済み・内訳・済んでいないものと理由・人の抜き取り）を、shiga-hino-plans の計画ページと同じ数え方（PLAN_SCHEMA §11.2）で数える
   - 段3の台帳：status が決まった語彙（未判断・ダッシュボードで対応・原典どおり掲載・原典どおり掲載(注記)・対象外）のどれか。未判断の件数を数える
   - 対応の台帳 `links/fuhyo.tsv`（令和8年度。hino-ronten の LINK_SCHEMA.md §5・§11 に合わせた5つ）
     - 全行の from が `fh:fuhyo-r8/<key>`、to が `node:jisshi/<key>` か `none:jisshi`、method が fuhyo、status が confirmed か rejected（candidate が残っていれば止める）
     - confirmed の行の from が附表にあり、事業名を LINK_SCHEMA §4 で正規化した値が context と同じ
     - confirmed の node の行の事業が jisshi.json にあり、事業名が to_label と同じ
     - confirmed の none の行の to_label が「記載なし」
     - 附表の各事業が、confirmed の node が1行以上か、confirmed の none が1行だけ
   - 年度の台帳 `links/fuhyo-years.tsv`
     - 全行の from・to が `fh:fuhyo-r<n>/<key>` で、from の年度が to の年度より前。method が name か manual、status が confirmed か rejected（candidate が残っていれば止める）
     - confirmed の行の両端が附表にあり、from の事業名を正規化した値が context と同じ、to の事業名が to_label と同じ
     - 1つの事業から同じ年度へのつながりは1つだけ、同じ年度から1つの事業へのつながりも1つだけ。つないで束ねた1本の中に、同じ年度の事業が2つ無い
   - `data/totals-r<n>.json`：単位が千円で、会計ごとの和が合計と一致し、出典の title・url・bytes・sha256 が hino-town-docs の台帳の `yosan-r<n>-gaiyou` の行と一致し、pdf_page・printed_page がある
   - 構造化の層（hino-town-docs `data/struct/`。補正予算と決算の画面は `KOZO_YEARS` の年度、いまは令和3〜8年度。検算は年度ごとに同じものを通す）
     - 使う行（款の行・会計の額・決算の額・財政指標の値）が、検収の台帳に同じ照合キー（DOCS_SCHEMA.md §13.10）であり、✓ で、要人確認が残っていない
     - 補正予算の款の表：回ごとに、款の和＝歳入合計・歳出合計（目的別）、内訳の和＝親の行、2つめの列＋今回補正額＝補正後予算額（総額と一般財源）、歳入合計＝歳出合計（目的別）＝歳出合計（性質別）、回のつながり（前の回の補正後予算額＝次の回の2つめの列）
     - 会計の額：会計の和＝合計、2つめの列＋今回補正額＝補正後予算額、会計ごとの回のつながり、当初予算額が資料の間で同じ
     - 款の表と会計の額の検算で合わない値は、原典の誤りの記録で「原典のまま持つ」とされた行のものだけなら通し、年度ごとに件数を表示する（DESIGN.md ADR-6）
     - 繰越明許費だけを定める回（主な内容の行の金額が空）：主な内容の行が検収済みで、説明に「繰越明許費のみ」があり、会計の額の表の今回補正額が 0
     - 当初予算との一致：一般会計の最初の回の補正前の額（款の表の歳入合計の2つめの列）と、会計の額の表の当初予算額（特別会計の合計、企業会計の支出の収益的と資本的の和）が、`data/totals-r<n>.json` の一般会計・特別会計・企業会計の額と同じ。特別会計の表・企業会計の表の無い年度（令和8年度の企業会計）は、その会計の回も無いことを確かめ、会計ごとの行を出さない
     - 決算：その年度の決算審査意見書の行がある年度（令和3〜7年度）だけ。出す会計のすべてに行がそろい、会計ごとに、歳入総額−歳出総額＝歳入歳出差引額（介護保険特別会計は勘定ごと）
     - 財政指標：載せる9つの指標が10年そろう（抜けた年度があれば表示して止める）。財政比較分析表の当該団体の値が総括表の値と同じ（4指標）
3. 実行すると、年度ごとの事業数と予算額の合計、柱ごとの予算額、検収の状況、年度の台帳の件数、当初予算の総額、構造化の層の行数と検算の結果を表示する。

材料を新しい版にするときは、各リポジトリを `git pull` し、`inputs.lock.json` の各ファイルの commit（`git -C <リポジトリ> rev-parse HEAD`）と sha256（`shasum -a 256 <ファイル>`）を書き換えてから、手順2を行う。`inputs.lock.json` と `data.js` は同じコミットで直す。

### 検収の状況を出し直すとき

令和3〜7年度の附表の段4（人の抜き取り）と段3の指摘の判断は、2026年11月6日に済み、同じ日に lock を上げて画面の「原典との照合」を出し直しました（5年度とも、抜き取りが対象と同じ数、段3の未判断 0件）。shiga-hino-plans の検収が進んだときは、次の手順で出し直します。

1. `git -C ../shiga-hino-plans pull` で、判断を取り込んだ版にする。`python3 ../shiga-hino-plans/tools/audit_autocheck.py fuhyo-r3 --status`（r4〜r7 も同じ）が「完了」になっていることを見る。
2. `inputs.lock.json` の shiga-hino-plans の行（20ファイル）の commit と sha256 を書き換える。附表の JSON を直していれば `data/fuhyo/fuhyo-r<n>.json` の sha256 も変わる。附表の JSON の任意の項目 `sic`（読みの注。PLAN_SCHEMA §9）は `tools/build_data.py` が形だけ確かめて読み飛ばし、画面には出さない。
3. `python3 tools/build_data.py` を実行する。検収の台帳の表示で、人の抜き取りの「済み」が対象と同じ数になり、段3の未判断が 0 になることを確かめる。附表の JSON が直っていれば、事業数・予算額の合計も変わるので、`tools/build_data.py` の `EXPECTED_ITEMS` を原典で確かめた数に直す。
4. `inputs.lock.json` と `data.js` を同じコミットにして、作業ブランチから PR を作る。

「補正予算と決算」の画面の決算の額は、決算審査意見書のある年度（令和3〜7年度）だけを載せます。原典（決算審査意見書）の円の値だけを `data.js` に持ち、画面で千円に四捨五入して表示します（「表示のための換算。原典は円」と注記し、円の値を添える）。決算の事業ごとの数字は町のサイトに無いので、事業の単位の決算は出しません。

画面に載せるのは、各年度の附表の事業の key・柱・区分・款・事業名・概要・内訳・予算額（千円）・担当課・原典のページ、年度の台帳でつながる他の年度の事業、令和8年度については対応の台帳で confirmed の実施計画の事業（e番号と事業名）です。原典の文字は直しません（誤字と思われる箇所も含めそのまま）。担当課が2つ以上ある事業は、担当課別の表では「複数の課」の行に数えます（課ごとの金額の内訳が附表に無いため）。増減は、負の値に「△」を付け、正の値に印を付けません。表のセルでは「△」と数だけを書き、列の見出しに「△ は減」と書きます。カードと文では、向きを文言（増・減・同額・増減なし）でも示します。前の年度が無いなど、値の無いセルは空けます。色は付けません（hino-portal DESIGN.md 3.3）。

## 町のページの巡回

毎月1日の朝と、当初予算が出る2〜4月は毎週月曜の朝（JST）に、GitHub Actions（`.github/workflows/watch.yml`）が町の「予算」のページ（町政情報 > 行財政運営 > 予算）を巡回し、見つけたものを Issue にします。道具は `tools/watch.py`（標準ライブラリだけ。取得は1秒に1件以内。約30秒）です。

| 見つけるもの | 確かめ方 |
|---|---|
| 新しい年度の予算のページ | 「予算」の分類のページにある「令和○年度予算」のうち、`data/watch.tsv` に無い年度。そのページの PDF のリンク（当初予算の概要・附表など）も Issue に載せる |
| 差し替え | `data/watch.tsv` の12件の PDF に HEAD を送り、Content-Length が bytes と同じで Last-Modified が取得日より後でなければ変更なし。それ以外は GET して sha256 を比べる |
| 取れない | 404 など。または、年度のページからその PDF へのリンクが無くなった |

巡回は見つけるだけで、`data/totals-r<n>.json`・`data.js`・`inputs.lock.json` は変えません。Issue の本文の「次にやること」に、転記と検収の手順（附表は shiga-hino-plans、年度の対応は hino-ronten、予算の規模はこのリポジトリ）があります。新しい年度を取り込んだら、`data/watch.tsv` にその年度の2行（fuhyo・gaiyou。hino-town-docs の台帳の bytes・sha256・fetched を写す）を足します。巡回そのものに失敗したときは、ワークフローが失敗して「巡回に失敗した」Issue ができます。同じ内容の Issue が開いていれば作りません。手元では `python3 tools/watch.py` で確かめられます。定期実行は60日間コミットが無いと止まるため、`.github/workflows/keepalive.yml` が毎月1日に有効化し直します。

## ライセンス

コードは MIT License（[LICENSE](LICENSE)）。`data.js` の構造は CC BY 4.0（表示は https://github.com/kken78/hino-budget ）。転記した文字と数字は日野町の公表資料によるもので、このリポジトリのライセンスの対象外。
