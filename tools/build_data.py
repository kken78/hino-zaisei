#!/usr/bin/env python3
"""当初予算の附表「主な事業」（令和3〜8年度）の材料を検算し、画面が読む data.js を作る（標準ライブラリのみ）。

材料（inputs.lock.json に、リポジトリ・コミット・パス・sha256 を記録）:
  shiga-hino-plans  data/fuhyo/fuhyo-r<n>.json          附表の事業（書式は PLAN_SCHEMA.md §9）。n は 3〜8
                    data/audit_log/fuhyo-r<n>.tsv       附表の検収の台帳
                    data/source_issues/fuhyo-r<n>.tsv   段3（文章の点検）の指摘と判断
                    data/sources_index.tsv              原典の台帳（fuhyo-r<n> の行の url を使う）
                    data/plans/jisshi.json              実施計画（事業名を引く）
  hino-ronten       links/fuhyo.tsv                     附表（令和8年度）と実施計画の事業の対応（書式は LINK_SCHEMA.md）
                    links/fuhyo-years.tsv               附表の事業の年度をまたぐ対応（LINK_SCHEMA.md「年度の台帳」）
  hino-town-docs    data/sources.tsv                    町の公開資料の台帳（yosan-r<n>-gaiyou の行で、当初予算の概要の
                                                        url・bytes・sha256 を確かめる）
                    data/struct/hosei-kai.tsv・hosei-shiryo.tsv・hosei-kan.tsv・hosei-kaikei.tsv・hosei-maru.tsv
                                                        補正予算の回・回と資料・款の表・会計の額・主な内容の行（DOCS_SCHEMA.md §13.6）
                    data/struct/kessan-kai.tsv・kessan-gaku.tsv  決算の回と額（§13.7）
                    data/struct/zaisei-shihyo.tsv・zaisei-ichi.tsv  財政指標と値の位置（§13.8）
                    data/struct/audit/hosei-r<n>.tsv・kessan.tsv・zaisei.tsv  構造化の層の検収の台帳（§13.10）
                    data/struct/issues/yosan-r5-hosei-02.tsv など4つ  補正予算の原典の誤りの記録（§13.11。HOSEI_ISSUES）
                    data/struct/kessan-uchiwake.tsv・issues/kessan-r3-gaiyou.tsv  決算の内訳（§13.7）と原典の誤りの記録
                    data/struct/kansa-kekka.tsv・kansa-jiko.tsv・audit/kansa.tsv  監査の結果の報告・事項と検収の台帳（§13.15）
                    data/text/kansa-*.txt                 監査の結果の文字の層（結果の文。台帳の check が ok の80本）
                    data/text/zaisei-r<n>-shiryoshu/01.tsv  財政状況資料集の総括表の文字（注釈 ※4・※6 の字を確かめる。令和3〜6年度）
このリポジトリ   data/totals-r<n>.json                 当初予算の会計ごとの予算規模（原典から転記した正本）

材料は、このリポジトリと同じフォルダにある各リポジトリ（例 ../shiga-hino-plans）から読む。
別の場所にあるときは --src <フォルダ> で、各リポジトリを置いたフォルダを指定する。

検算:
  1. inputs.lock.json の sha256 と、いまのファイルが一致する
  2. 附表: 年度ごとに事業数が決まった数（EXPECTED_ITEMS）で、key が重複しない（項目の形も PLAN_SCHEMA §9 に合う）。
     柱の番号と名前が6年で同じ。年度ごとの予算額の合計を数え、報告に出す
  3. 検収の台帳: 全行の列が合い、checked が ✓ か空、✓ の reviewer が auto:pdftext・auto:ai か人。
     ✓ でない行の note が PLAN_SCHEMA §11.3 の理由の表にある。照合の状況（§11.2 の N・M・a・b・c・U・F・X）を数える
     段3の台帳: status が決まった語彙のどれか。未判断の件数を数える
  4. 対応の台帳（links/fuhyo.tsv。令和8年度。LINK_SCHEMA §5・§11 に合わせた5つ）
     a. 全行: from が fh:fuhyo-r8/<key>、to が node:jisshi/<key> か none:jisshi、method が fuhyo、
        status が confirmed か rejected（candidate が残っていれば判定の途中として止める）
     b. confirmed の行の from: 附表にその key があり、事業名を §4 で正規化した値が context と同じ
     c. confirmed の node の行: jisshi.json にその key の事業があり、その name が to_label と同じ
     d. confirmed の none の行: to_label が「記載なし」
     e. 附表の各事業が、confirmed の node が1行以上か、confirmed の none が1行だけ
  5. 年度の台帳（links/fuhyo-years.tsv）
     a. 全行: from・to が fh:fuhyo-r<n>/<key> で from の年度が to の年度より前、method が name か manual、
        status が confirmed か rejected（candidate が残っていれば止める）
     b. confirmed の行: 両端の事業が附表にあり、from の事業名を正規化した値が context と同じ、to の事業名が to_label と同じ
     c. 1つの事業から同じ年度への confirmed は1行だけ。同じ年度から1つの事業への confirmed も1行だけ。
        つないで束ねた1本の中に、同じ年度の事業が2つ無い
  6. data/totals-r<n>.json: 単位が千円で、会計ごとの和が合計と一致し、出典の title・url・bytes・sha256 が
     hino-town-docs の台帳の yosan-r<n>-gaiyou の行と一致し、pdf_page・printed_page がある
  7. 構造化の層（hino-town-docs data/struct/。KOZO_YEARS の年度。DESIGN.md ADR-4・ADR-6）。検算は年度ごとに同じものを通す
     a. hino-town-docs の材料が1つの commit。使う行（款の行・会計の額・決算の額・財政指標の値）が、検収の台帳に
        同じ照合キー（§13.10）であり、✓ で、要人確認が残っていない
     b. 回: 会計ごとに prev をたどると、年度の回が1本につながる
     c. 款の表: 回ごとに、款・区分の和＝合計、内訳の和＝親の行、歳入合計＝歳出合計（目的別）＝歳出合計（性質別）、
        2つめの列＋今回補正額＝補正後予算額（総額と一般財源）、当初予算額が回で同じ、回のつながり（前の回の補正後予算額＝
        次の回の2つめの列）
     d. 会計の額: 会計の和＝合計、2つめの列＋今回補正額＝補正後予算額、会計ごとのつながり、当初予算額が資料で同じ。
        特別会計・企業会計の回が、その会計の補正のある資料と1対1に対応する。金額が空の主な内容の行の回（繰越明許費のみ）は、
        その行が検収済みで、説明に「繰越明許費のみ」があり、会計の額の今回補正額が 0
        c・d で合わない値は、原典の誤りの記録で「原典のまま持つ」とされた行のものだけなら通し、年度ごとに件数を表示する
     e. 当初予算: 一般会計の最初の回の補正前の額、特別会計の表の当初の合計、企業会計の表の支出の当初の和（収益的＋資本的）が、
        data/totals-r<n>.json の一般会計・特別会計・企業会計の額と同じ。表の無い区分は、その区分の回も無いこと
     f. 決算（その年度の決算審査意見書の行がある年度だけ。ある年度は出す会計のすべてにそろう）: 決算審査意見書の円の額で、歳入総額−歳出総額＝歳入歳出差引額（介護保険特別会計は勘定ごと）
     g. 財政指標: 載せる9指標が10年そろう（抜けた年度は表示して止める）。財政比較分析表の当該団体の値＝総括表の値
  8. 決算と監査（令和3〜7年度。DESIGN.md ADR-8）
     a. 決算の内訳: 使う行がすべて検収済み。出典が kessan-r<n>-gaiyou だけで、単位が万円。外側の輪の和＝内側の輪の和（歳入・性質別の歳出）
     b. 健全化判断比率: 使う値がすべて検収済み。各年度の総括表に注釈 ※4・※6 の字がある
     c. 監査の結果: 台帳の kansa の行（check が ok か image）ごとに1件。ok の行は報告の表にあり、報告と事項の行が台帳に同じ値であること。
        検収済みでない行のある報告は、題と PDF だけにする（値を使わない）。結果の文は data/text の kekka_from〜kekka_to の行で、
        つないだ字が文字の層の字と同じ。団体の監査は「イ．指摘事項」の後ろの字が shiteki と同じ
どれかが合わなければ data.js を書かずに終了コード 1 で止まる。
"""
import argparse, hashlib, json, pathlib, re, sys, unicodedata

ROOT = pathlib.Path(__file__).resolve().parent.parent
YEARS = [3, 4, 5, 6, 7, 8]                       # 令和の年度
EXPECTED_ITEMS = {3: 155, 4: 166, 5: 168, 6: 177, 7: 184, 8: 181}
LINK_YEAR = 8                                     # 実施計画と突き合わせた附表の年度（links/fuhyo.tsv）
PLAN_ID = 'jisshi'
ISSUE_STATUS = {'未判断', 'ダッシュボードで対応', '原典どおり掲載(注記)', '原典どおり掲載', '対象外'}  # check_source_issues.py
# 検収の台帳の note と、画面の理由の対応（shiga-hino-plans の tools/audit_display.py、PLAN_SCHEMA §11.3）
REASON_MISMATCH = '人の確認で食い違いが見つかり、直している'
REASON_HOLD = '人が確かめたが、判断を保留している'
REASON_H1 = 'AI 2回の照合の結果がそろわない、または確信が高くない'
H2_REASONS = {
    '出典が4ページ以上(集計した値)': '原典の複数のページにわたる値を、数えたり集計したりした値',
    '数値でない': '数値でない項目（名前・年度など）',
    '出典の PDF がない': '原典の PDF が無い資料から引いた値',
    '出典ページがない、または PDF の範囲にない': '原典のページを特定できない値',
    '出典の PDF やページがない': '原典の PDF またはページを特定できない値',
}
NOT_YET = 'まだ照合していない'
REASON_ORDER = [REASON_MISMATCH, REASON_HOLD, REASON_H1, *dict.fromkeys(H2_REASONS.values()), NOT_YET]
HUMAN_SEEN = {REASON_MISMATCH, REASON_HOLD}       # 人がすでに見た理由（「人が確かめます」を添えない）
MACHINE = {'auto:pdftext': 'a', 'auto:ai': 'b'}

ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
ap.add_argument('--src', default=str(ROOT.parent), help='材料のリポジトリを置いたフォルダ（既定はこのリポジトリの親）')
args = ap.parse_args()
SRC = pathlib.Path(args.src).resolve()

errors = []


def fail_now():
    print('\n'.join(errors))
    print(f'検算 NG（{len(errors)}件）。data.js は書き出していません。')
    sys.exit(1)


# 1. lock --------------------------------------------------------------------
lock = json.loads((ROOT / 'inputs.lock.json').read_text(encoding='utf-8'))
files = {}
for ent in lock['inputs']:
    repo_dir = ent['repo'].split('/')[-1]
    p = SRC / repo_dir / ent['path']
    tag = f"{repo_dir}/{ent['path']}"
    if not p.is_file():
        errors.append(f'lock: {tag} がない（{p}）')
        continue
    b = p.read_bytes()
    h = hashlib.sha256(b).hexdigest()
    if h != ent['sha256']:
        errors.append(f"lock: {tag} の sha256 が違う（lock {ent['sha256'][:12]}… / いま {h[:12]}…。"
                      f"lock の commit は {ent['commit'][:7]}）")
    files[tag] = b.decode('utf-8')
if errors:
    fail_now()

FUHYO = {y: f'shiga-hino-plans/data/fuhyo/fuhyo-r{y}.json' for y in YEARS}
AUDIT = {y: f'shiga-hino-plans/data/audit_log/fuhyo-r{y}.tsv' for y in YEARS}
ISSUES = {y: f'shiga-hino-plans/data/source_issues/fuhyo-r{y}.tsv' for y in YEARS}
SINDEX = 'shiga-hino-plans/data/sources_index.tsv'
JISSHI = f'shiga-hino-plans/data/plans/{PLAN_ID}.json'
LINKS = 'hino-ronten/links/fuhyo.tsv'
LINKS_Y = 'hino-ronten/links/fuhyo-years.tsv'
TOWN = 'hino-town-docs/data/sources.tsv'
for tag in (*FUHYO.values(), *AUDIT.values(), *ISSUES.values(), SINDEX, JISSHI, LINKS, LINKS_Y, TOWN):
    if tag not in files:
        errors.append(f'lock: {tag} が inputs.lock.json に載っていない')
if errors:
    fail_now()


def read_tsv(text, skip_comments=False):
    lines = [l for l in text.split('\n') if l != '']
    if skip_comments:
        lines = [lines[0]] + [l for l in lines[1:] if not l.startswith('#')]
    head = lines[0].split('\t')
    rows = []
    for n, l in enumerate(lines[1:], 2):
        cells = l.split('\t')
        if len(cells) != len(head):
            errors.append(f'列の数が違う（{len(cells)}／見出し {len(head)}）: {l[:80]}')
            continue
        rows.append(dict(zip(head, cells)))
    return head, rows


def norm(s):  # LINK_SCHEMA §4
    s = unicodedata.normalize('NFKC', s)
    s = re.sub(r'\n[0-9]+-[0-9]+', '', s)
    s = re.sub(r'-[0-9]+-', '', s)
    return re.sub(r'\s', '', s)


# 2. 附表 -----------------------------------------------------------------------
FIELDS = {'key': str, 'kubun': list, 'kan': str, 'name': str, 'desc': str,
          'details': list, 'amount': int, 'dept': list, 'page': int}
# 任意の項目。読みの注（PLAN_SCHEMA §9 の sic。原典の誤字の箇所と正しい読み）。画面には出さず、本文は原典のまま。
OPTIONAL_FIELDS = {'sic'}
fuhyo = {}       # 年度 → JSON
items = {}       # 年度 → [(柱, 事業)]
F = {}           # 年度 → {key: 事業}
pillar_names = None
for y in YEARS:
    d = json.loads(files[FUHYO[y]])
    fuhyo[y] = d
    if d.get('id') != f'fuhyo-r{y}':
        errors.append(f"附表 r{y}: id が {d.get('id')!r}")
    fy = d.get('fiscal_year', {})
    if fy.get('label') != f'令和{y}年度' or fy.get('year') != 2018 + y:
        errors.append(f'附表 r{y}: fiscal_year が違う: {fy}')
    names = []
    its = []
    for p in d['pillars']:
        if not isinstance(p.get('no'), int) or not isinstance(p.get('name'), str):
            errors.append(f'附表 r{y}: 柱の no・name の形が違う: {p.get("no")!r}')
        names.append((p.get('no'), p.get('name')))
        for it in p['items']:
            if set(it) - OPTIONAL_FIELDS != set(FIELDS):
                errors.append(f"附表 r{y}: {it.get('key')} の項目が違う: {sorted((set(it) - OPTIONAL_FIELDS) ^ set(FIELDS))}")
                continue
            if 'sic' in it and not (isinstance(it['sic'], list) and all(
                    isinstance(x, dict) and isinstance(x.get('text'), str) and x.get('field') in ('name', 'desc', 'details')
                    for x in it['sic'])):
                errors.append(f"附表 r{y}: {it['key']} の sic の形が違う")
            for k, t in FIELDS.items():
                if not isinstance(it[k], t) or (t is int and isinstance(it[k], bool)):
                    errors.append(f"附表 r{y}: {it['key']} の {k} の型が違う")
            if not re.fullmatch(r'b[0-9]{3,}', it['key']):
                errors.append(f"附表 r{y}: key の形が違う: {it['key']}")
            if any(k not in ('新規', '拡充') for k in it['kubun']):
                errors.append(f"附表 r{y}: {it['key']} の kubun に新規・拡充以外がある: {it['kubun']}")
            if not it['dept']:
                errors.append(f"附表 r{y}: {it['key']} の dept が空")
            its.append((p, it))
    if len(its) != EXPECTED_ITEMS[y]:
        errors.append(f'附表 r{y}: 事業が {len(its)}件（{EXPECTED_ITEMS[y]}件のはず）')
    seen = {}
    for _, it in its:
        seen[it['key']] = seen.get(it['key'], 0) + 1
    dup = [k for k, c in seen.items() if c > 1]
    if dup:
        errors.append(f'附表 r{y}: key が重複: {dup}')
    if pillar_names is None:
        pillar_names = names
    elif names != pillar_names:
        errors.append(f'附表 r{y}: 柱の番号と名前が令和{YEARS[0]}年度と違う: {names}')
    items[y] = its
    F[y] = {it['key']: it for _, it in its}
if errors:
    fail_now()

# 原典の台帳
_, srows = read_tsv(files[SINDEX])
srow = {}
for y in YEARS:
    rs = [r for r in srows if r['id'] == f'fuhyo-r{y}' and r['file'] == fuhyo[y]['source']['file']]
    if len(rs) != 1 or not rs[0]['url'].startswith('https://'):
        errors.append(f"原典の台帳: id=fuhyo-r{y}・file={fuhyo[y]['source']['file']} の行が {len(rs)}行（1行で url があるはず）")
        continue
    srow[y] = rs[0]
if errors:
    fail_now()


# 3. 検収の台帳と段3の台帳 -----------------------------------------------------------
def reason(note):
    """✓ でない行の理由（PLAN_SCHEMA §11.3 の対応表）。表に無い note は None。"""
    mis, hold = ' / 不一致:' in note, ' / 保留:' in note
    if mis and hold:
        return None
    if mis:
        return REASON_MISMATCH
    if hold:
        return REASON_HOLD
    if note.startswith('要人確認:H1'):
        return REASON_H1
    if note.startswith('要人確認:H2 '):
        return H2_REASONS.get(note[len('要人確認:H2 '):].split(' / ')[0])
    if note == '':
        return NOT_YET
    return None


audit = {}
issues = {}
for y in YEARS:
    ahead, arows = read_tsv(files[AUDIT[y]], skip_comments=True)
    for col in ('key', 'checked', 'reviewer', 'date', 'note', 'label'):
        if col not in ahead:
            errors.append(f'検収の台帳 r{y}: {col} の列がない')
    if errors:
        fail_now()
    if not arows:
        errors.append(f'検収の台帳 r{y}: 行がない')
    s = {'n': len(arows), 'm': 0, 'a': 0, 'b': 0, 'c': 0, 'u': 0, 'f': 0, 'x': 0}
    reasons = dict.fromkeys(REASON_ORDER, 0)
    dates = []
    keys = set()
    for r in arows:
        if r['key'] in keys:
            errors.append(f"検収の台帳 r{y}: key が重複: {r['key']}")
        keys.add(r['key'])
        if r['date']:
            dates.append(r['date'])
        if r['checked'] not in ('✓', ''):
            errors.append(f"検収の台帳 r{y}: checked が ✓ でも空でもない行: {r['checked']!r} {r['label']}")
            continue
        ok = r['checked'] == '✓'
        rv = r['reviewer']
        if ok:
            s['m'] += 1
            if rv.startswith('auto:'):
                if rv not in MACHINE:
                    errors.append(f"検収の台帳 r{y}: PLAN_SCHEMA §11.2 に無い機械の照合: reviewer={rv!r}")
                else:
                    s[MACHINE[rv]] += 1
            else:
                s['c'] += 1
        else:
            s['u'] += 1
            rs = reason(r['note'])
            if rs is None:
                errors.append(f"検収の台帳 r{y}: PLAN_SCHEMA §11.3 の表に無い note: {r['note']!r}")
            else:
                reasons[rs] += 1
        if r['note'].startswith('要人確認:H4'):
            s['f'] += 1
            if ok and not rv.startswith('auto:'):
                s['x'] += 1
    s['reasons'] = [[k, v, k not in HUMAN_SEEN] for k, v in reasons.items() if v]  # [理由, 件数, 人が確かめます]
    s['last'] = max(dates) if dates else ''
    audit[y] = s

    ihead, irows = read_tsv(files[ISSUES[y]])
    if 'status' not in ihead:
        errors.append(f'段3の台帳 r{y}: status の列がない')
        continue
    by = {}
    for r in irows:
        if r['status'] not in ISSUE_STATUS:
            errors.append(f"段3の台帳 r{y}: status が決まった語彙にない: {r['status']!r}（No.{r.get('no')}）")
        by[r['status']] = by.get(r['status'], 0) + 1
    issues[y] = {'rows': len(irows), 'pending': by.get('未判断', 0),
                 'by_status': [[k, v] for k, v in sorted(by.items(), key=lambda kv: -kv[1])]}
if errors:
    fail_now()

# 4. 実施計画と対応の台帳（令和8年度） ---------------------------------------------------
jisshi = json.loads(files[JISSHI])


def walk(o):
    if isinstance(o, dict):
        if o.get('type') == 'programs':
            yield o
        for v in o.values():
            yield from walk(v)
    elif isinstance(o, list):
        for v in o:
            yield from walk(v)


E = {}
for b in walk(jisshi):
    for g in b.get('groups', []):
        its = list(g.get('items', []))
        for s in g.get('subgroups', []):
            its += s.get('items', [])
        for it in its:
            k = it.get('key')
            if not k:
                errors.append(f"実施計画: key の無い事業がある: {it.get('name')}")
            elif k in E:
                errors.append(f'実施計画: key が重複: {k}')
            else:
                E[k] = it['name']
if not E:
    errors.append('実施計画: programs の事業が見つからない')

FL = F[LINK_YEAR]
_, lrows = read_tsv(files[LINKS])
node_of = {k: [] for k in FL}
none_of = {k: 0 for k in FL}
for r in lrows:
    tag = f"links: {r['from']} → {r['to']}"
    mf = re.fullmatch(rf'fh:fuhyo-r{LINK_YEAR}/(b[0-9]{{3,}})', r['from'])
    mn = re.fullmatch(rf'node:{PLAN_ID}/(e[0-9]{{3,}})', r['to'])
    is_none = r['to'] == f'none:{PLAN_ID}'
    if not mf or not (mn or is_none) or r['method'] != 'fuhyo':  # a
        errors.append(f'{tag}: from・to・method の形が違う')
        continue
    if r['status'] == 'candidate':
        errors.append(f'{tag}: candidate のまま（判定の途中）')
        continue
    if r['status'] not in ('confirmed', 'rejected'):
        errors.append(f"{tag}: status が {r['status']!r}")
        continue
    if r['status'] != 'confirmed':
        continue
    fk = mf.group(1)
    if fk not in FL:  # b
        errors.append(f'{tag}: 附表に {fk} がない')
        continue
    if norm(FL[fk]['name']) != r['context']:
        errors.append(f"{tag}: 附表の事業名「{FL[fk]['name']}」が context「{r['context']}」と合わない")
    if mn:  # c
        ek = mn.group(1)
        if ek not in E:
            errors.append(f'{tag}: 実施計画に {ek} がない')
        elif E[ek] != r['to_label']:
            errors.append(f"{tag}: 実施計画の事業名「{E[ek]}」が to_label「{r['to_label']}」と違う")
        else:
            node_of[fk].append(ek)
    else:  # d
        if r['to_label'] != '記載なし':
            errors.append(f"{tag}: to_label が「記載なし」でない（{r['to_label']}）")
        else:
            none_of[fk] += 1
for k in FL:  # e
    n, z = len(node_of[k]), none_of[k]
    if not ((n >= 1 and z == 0) or (n == 0 and z == 1)):
        errors.append(f'links: {k}（{FL[k]["name"]}）の confirmed が node {n}行・記載なし {z}行')

# 5. 年度の台帳 -------------------------------------------------------------------
_, yrows = read_tsv(files[LINKS_Y])
FH = re.compile(r'fh:fuhyo-r([3-8])/(b[0-9]{3,})')
edges = []                       # (from_year, from_key, to_year, to_key)
out_of = {}                      # (from_year, from_key, to_year) → 件数
in_of = {}                       # (to_year, to_key, from_year) → 件数
ny = {'name': 0, 'manual': 0, 'rejected': 0}
for r in yrows:
    tag = f"years: {r['from']} → {r['to']}"
    mf, mt = FH.fullmatch(r['from']), FH.fullmatch(r['to'])
    if not mf or not mt or r['method'] not in ('name', 'manual'):  # a
        errors.append(f'{tag}: from・to・method の形が違う')
        continue
    fy, fk, ty, tk = int(mf.group(1)), mf.group(2), int(mt.group(1)), mt.group(2)
    if fy >= ty:
        errors.append(f'{tag}: from の年度が to の年度より前でない')
        continue
    if r['status'] == 'candidate':
        errors.append(f'{tag}: candidate のまま（判定の途中）')
        continue
    if r['status'] not in ('confirmed', 'rejected'):
        errors.append(f"{tag}: status が {r['status']!r}")
        continue
    if r['status'] != 'confirmed':
        ny['rejected'] += 1
        continue
    if fk not in F[fy] or tk not in F[ty]:  # b
        errors.append(f'{tag}: 附表に無い事業がある')
        continue
    if norm(F[fy][fk]['name']) != r['context']:
        errors.append(f"{tag}: from の事業名「{F[fy][fk]['name']}」が context「{r['context']}」と合わない")
    if F[ty][tk]['name'] != r['to_label']:
        errors.append(f"{tag}: to の事業名「{F[ty][tk]['name']}」が to_label「{r['to_label']}」と違う")
    ny[r['method']] += 1
    edges.append((fy, fk, ty, tk))
    out_of[(fy, fk, ty)] = out_of.get((fy, fk, ty), 0) + 1
    in_of[(ty, tk, fy)] = in_of.get((ty, tk, fy), 0) + 1
for (fy, fk, ty), c in out_of.items():  # c
    if c > 1:
        errors.append(f'years: fh:fuhyo-r{fy}/{fk} から令和{ty}年度への confirmed が {c}行')
for (ty, tk, fy), c in in_of.items():
    if c > 1:
        errors.append(f'years: 令和{fy}年度から fh:fuhyo-r{ty}/{tk} への confirmed が {c}行')

# 束ねる（同じ事業の年度をまたぐつながり）
parent = {(y, k): (y, k) for y in YEARS for k in F[y]}


def find(x):
    while parent[x] != x:
        parent[x] = parent[parent[x]]
        x = parent[x]
    return x


for fy, fk, ty, tk in edges:
    parent[find((fy, fk))] = find((ty, tk))
groups = {}
for x in parent:
    groups.setdefault(find(x), []).append(x)
chains = []
for g in sorted(groups.values(), key=lambda g: min(g)):
    g = sorted(g)
    ys = [y for y, _ in g]
    if len(set(ys)) != len(ys):
        errors.append('years: 束ねた1本に同じ年度の事業が2つある: ' + ', '.join(f'fh:fuhyo-r{y}/{k}' for y, k in g))
    chains.append(g)
chain_of = {x: i for i, g in enumerate(chains) for x in g}

# 6. 当初予算の総額（このリポジトリの data/totals-r<n>.json。原典から転記した正本） -------------
_, trows = read_tsv(files[TOWN])
town = {r['id']: r for r in trows}
totals = {}
for y in YEARS:
    t = json.loads((ROOT / f'data/totals-r{y}.json').read_text(encoding='utf-8'))
    if t.get('unit') != '千円':
        errors.append(f"totals r{y}: unit が千円でない（{t.get('unit')!r}）")
    acc = sum(a['amount'] for a in t['accounts'])
    if acc != t['total']['amount']:
        errors.append(f"totals r{y}: 会計ごとの和 {acc:,} ≠ 合計 {t['total']['amount']:,}")
    src = t['source']
    if not isinstance(src.get('pdf_page'), int) or not isinstance(src.get('printed_page'), int):
        errors.append(f'totals r{y}: 出典の pdf_page・printed_page の形が違う')
    tr = town.get(src.get('docs_id', ''))
    if tr is None:
        errors.append(f"totals r{y}: hino-town-docs の台帳に {src.get('docs_id')!r} の行がない")
    else:
        if tr['id'] != f'yosan-r{y}-gaiyou':
            errors.append(f"totals r{y}: docs_id が yosan-r{y}-gaiyou でない（{tr['id']}）")
        for k in ('title', 'url', 'sha256'):
            if src.get(k) != tr[k]:
                errors.append(f"totals r{y}: 出典の {k} が hino-town-docs の台帳と違う（{src.get(k)} / {tr[k]}）")
        if str(src.get('bytes')) != tr['bytes']:
            errors.append(f"totals r{y}: 出典の bytes が hino-town-docs の台帳と違う（{src.get('bytes')} / {tr['bytes']}）")
    totals[y] = t

if errors:
    fail_now()

# 7. 構造化の層（hino-town-docs data/struct/。DOCS_SCHEMA.md §13。DESIGN.md ADR-4） -----------------
TD = 'hino-town-docs/data/struct/'
KOZO_YEARS = [3, 4, 5, 6, 7, 8]
# 原典の誤りの記録（§13.11）のうち補正予算のもの。「原典のまま持つ」の行だけ、検算で合わなくても通す
HOSEI_ISSUES = ['issues/yosan-r5-hosei-02.tsv', 'issues/yosan-r6-hosei-09.tsv', 'issues/yosan-r7-hosei-09.tsv',
                'issues/yosan-r8-hosei-06-tsuika.tsv']
HOSEI_AUDIT = [f'audit/hosei-r{y}.tsv' for y in KOZO_YEARS]
KZ = {n: TD + n for n in (
    'hosei-kai.tsv', 'hosei-shiryo.tsv', 'hosei-kan.tsv', 'hosei-kaikei.tsv', 'hosei-maru.tsv', 'kessan-kai.tsv',
    'kessan-gaku.tsv', 'zaisei-shihyo.tsv', 'zaisei-ichi.tsv', *HOSEI_AUDIT, 'audit/kessan.tsv', 'audit/zaisei.tsv',
    *HOSEI_ISSUES, 'kessan-uchiwake.tsv', 'issues/kessan-r3-gaiyou.tsv', 'kansa-kekka.tsv', 'kansa-jiko.tsv',
    'audit/kansa.tsv')}
for tag in KZ.values():
    if tag not in files:
        errors.append(f'lock: {tag} が inputs.lock.json に載っていない')
if errors:
    fail_now()
TDC = {e['commit'] for e in lock['inputs'] if e['repo'] == 'kken78/hino-town-docs'}
if len(TDC) != 1:
    errors.append(f'lock: hino-town-docs の commit が1つでない（{sorted(TDC)}）。CI はリポジトリごとに commit を1つだけ取り出す')
    fail_now()
TD_COMMIT = TDC.pop()
K = {n: read_tsv(files[t])[1] for n, t in KZ.items()}
if errors:
    fail_now()
AMT9 = ['tosho', 'tosho_ippan', 'mae', 'mae_ippan', 'hosei', 'hosei_ippan', 'hoseigo', 'hoseigo_ippan', 'taitosho']
AMT8 = AMT9[:8]
C4 = ['tosho', 'mae', 'hosei', 'hoseigo']
# 会計の並びは補正予算の概要の特別会計の表・企業会計の表の順（令和3・4年度は簡易水道・農業集落排水事業の特別会計がある。DOCS_SCHEMA §13.3・§13.12）
ACC_ORDER = ['ippan', 'kokuho', 'kansui', 'noshu', 'kaigo', 'koki', 'nishiyama', 'suido', 'gesuido']
ACC_NAME = {'ippan': '一般会計', 'kokuho': '国民健康保険特別会計', 'kansui': '簡易水道特別会計', 'noshu': '農業集落排水事業特別会計',
            'kaigo': '介護保険特別会計', 'koki': '後期高齢者医療特別会計',
            'nishiyama': '西山財産区会計', 'suido': '水道事業会計', 'gesuido': '下水道事業会計'}
TOKU, KIGYO = ['kokuho', 'kansui', 'noshu', 'kaigo', 'koki', 'nishiyama'], ['suido', 'gesuido']
KESSAN_KEYS = {
    'ippan': ['sainyu', 'saishutsu', 'sashihiki', 'jisshitsu'], 'kokuho': ['sainyu', 'saishutsu', 'sashihiki', 'jisshitsu'],
    'koki': ['sainyu', 'saishutsu', 'sashihiki', 'jisshitsu'], 'nishiyama': ['sainyu', 'saishutsu', 'sashihiki', 'jisshitsu'],
    'kansui': ['sainyu', 'saishutsu', 'sashihiki', 'jisshitsu'], 'noshu': ['sainyu', 'saishutsu', 'sashihiki', 'jisshitsu'],
    'kaigo': [f'{k}-{s}' for s in ('hoken', 'service') for k in ('sainyu', 'saishutsu', 'sashihiki', 'jisshitsu')],
    'suido': ['shueki-shunyu', 'shueki-shishutsu', 'shihon-shunyu', 'shihon-shishutsu'],
    'gesuido': ['shueki-shunyu', 'shueki-shishutsu', 'shihon-shunyu', 'shihon-shishutsu'],
}
KESSAN_LABEL = {'sainyu': '歳入総額', 'saishutsu': '歳出総額', 'sashihiki': '歳入歳出差引額', 'jisshitsu': '実質収支額',
                'shueki-shunyu': '収益的収入', 'shueki-shishutsu': '収益的支出', 'shihon-shunyu': '資本的収入',
                'shihon-shishutsu': '資本的支出'}
KIGYO_COLS = [('shunyu', 'shueki'), ('shishutsu', 'shueki'), ('shunyu', 'shihon'), ('shishutsu', 'shihon')]
SHIHYO = ['zaiseiryoku', 'keijo', 'jisshitsu-kosaihi', 'shorai-futan', 'jisshitsu-hiritsu', 'chihosai', 'zaicho', 'gensai', 'tokutei']
HIKAKU = {'zaiseiryoku': 'zaiseiryoku', 'keijo': 'keijo', 'jisshitsu-kosaihi': 'jisshitsu-kosaihi', 'shorai-futan': 'shorai-futan'}
SOKI = ['jisshitsu-kosaihi', 'shorai-futan']
ZY = ['h27', 'h28', 'h29', 'h30', 'r1', 'r2', 'r3', 'r4', 'r5', 'r6']


def ival(v):
    return int(v) if v != '' else 0


def row_key(*a):  # DOCS_SCHEMA §13.10（hino-town-docs tools/kozo.py の row_key と同じ作り方）
    return hashlib.sha256('\x1f'.join(a).encode('utf-8')).hexdigest()[:16]


LEDGER = {}
for n in (*HOSEI_AUDIT, 'audit/kessan.tsv', 'audit/zaisei.tsv', 'audit/kansa.tsv'):
    for r in K[n]:
        LEDGER[r['key']] = (n, r)
kz_used = {}   # (台帳, 区切り) → {'n','a'(auto:pdftext),'k'(auto:check),'b'(auto:ai),'c'(人)}。区切りは年度（r6 など）か zaisei
KZ_BUCKET = ''


def audited(table, row, cols, vals, unit, source):
    """構造化の表の1行が、検収の台帳に同じ照合キーであり、✓ で、要人確認が残っていないか。"""
    k = row_key(table, row, ','.join(cols), '|'.join(vals), unit, source)
    hit = LEDGER.get(k)
    if hit is None:
        errors.append(f'検収の台帳: {table} {row} の行が台帳に無い（値か出典が台帳と違う。key {k}）')
        return
    n, r = hit
    if r['checked'] != '✓' or r['note'].startswith('要人確認'):
        errors.append(f"検収の台帳: {table} {row} が検収済みでない（checked={r['checked']!r} note={r['note'][:30]!r}）")
        return
    s = kz_used.setdefault((n, KZ_BUCKET), {'n': 0, 'a': 0, 'k': 0, 'b': 0, 'c': 0})
    s['n'] += 1
    rv = r['reviewer']
    s[{'auto:pdftext': 'a', 'auto:check': 'k', 'auto:ai': 'b'}.get(rv, 'c')] += 1


town_kz = {r['id']: r for r in trows}


def doc_ref(doc, page):
    t = town_kz.get(doc)
    if t is None or not t['url'].startswith('https://'):
        errors.append(f'構造化の層: 資料 {doc} が hino-town-docs の台帳に無いか url が無い')
        return {'doc': doc, 'title': doc, 'url': '', 'page': page}
    return {'doc': doc, 'title': t['title'], 'url': t['url'], 'page': page}


# 原典の誤りの記録で「原典のまま持つ」とされた行（回のつながりの検算で合わなくても通す）
# 行（<回の id>/<行の key>）→ 記録のファイル。年度の検算で通した値の数を、記録のファイルごとに数える
ISSUE_ROWS = {}
for n in HOSEI_ISSUES:
    for r in K[n]:
        if r['status'] not in ('未判断', '原典のまま持つ', '対象外'):
            errors.append(f"原典の誤りの記録: {n} no.{r['no']} の status が決まった語彙にない（{r['status']!r}）")
        if r['status'] == '原典のまま持つ':
            for w in re.findall(r'r[0-9]+-[a-z]+-[0-9]{2}/[a-z0-9-]+', r['where']):
                ISSUE_ROWS[w] = n
issue_used = {}   # 記録のファイル → 通した値の数（年度の処理の中で数える）


def by_issue(*rows):
    """検算で合わなかった値が、原典の誤りの記録で「原典のまま持つ」とされた行のものなら、数えて True を返す。"""
    hit = [ISSUE_ROWS[r] for r in rows if r in ISSUE_ROWS]
    if not hit:
        return False
    issue_used[hit[0]] = issue_used.get(hit[0], 0) + 1
    return True

kz_report = []
kozo_years = []
for y in YEARS:
    if y not in KOZO_YEARS:
        continue
    fy = 2018 + y
    KZ_BUCKET = f'r{y}'
    issue_used = {}
    kais = {r['id']: r for r in K['hosei-kai.tsv'] if r['fiscal_year'] == str(fy)}
    if not kais:
        errors.append(f'構造化の層 r{y}: 補正予算の回が無い')
        continue
    # 会計ごとに prev をたどった順
    order = {}
    for acc in sorted({r['kaikei'] for r in kais.values()}):
        rs = [r for r in kais.values() if r['kaikei'] == acc]
        heads = [r['id'] for r in rs if r['prev'] == '']
        nxt = {}
        for r in rs:
            if r['prev']:
                if r['prev'] not in kais or kais[r['prev']]['kaikei'] != acc:
                    errors.append(f"構造化の層: {r['id']} の prev {r['prev']} が同じ年度・会計の回でない")
                if r['prev'] in nxt:
                    errors.append(f"構造化の層: {r['prev']} を前の回とする回が2つある")
                nxt[r['prev']] = r['id']
        if len(heads) != 1:
            errors.append(f'構造化の層 r{y} {acc}: 年度の最初の回が {len(heads)}つ')
            continue
        seq, cur = [], heads[0]
        while cur and cur not in seq:
            seq.append(cur)
            cur = nxt.get(cur)
        if len(seq) != len(rs):
            errors.append(f'構造化の層 r{y} {acc}: prev をたどって {len(seq)}回（回は {len(rs)}）')
        order[acc] = seq
        if acc not in ACC_ORDER:
            errors.append(f'構造化の層 r{y}: 画面で扱わない会計 {acc}')
    if 'ippan' not in order:
        errors.append(f'構造化の層 r{y}: 一般会計の回が無い')
        fail_now()
    shiryo = {}
    for r in K['hosei-shiryo.tsv']:
        if r['kai'] in kais:
            shiryo.setdefault(r['kai'], []).append(r)
    # 款の表
    kan = {}
    for r in K['hosei-kan.tsv']:
        if r['kai'] in kais:
            kan.setdefault(r['kai'], {})[r['key']] = r
            if r['unit'] != '千円':
                errors.append(f"款の表: {r['kai']}/{r['key']} の unit が千円でない")
            audited('hosei-kan', f"{r['kai']}/{r['key']}", AMT9, [r[c] for c in AMT9], r['unit'], f"{r['doc']} p.{r['page']}")
    n_kan = sum(len(v) for v in kan.values())
    for kid in order['ippan']:
        d = kan.get(kid)
        if not d or not all(k in d for k in ('in-total', 'out-total', 'sei-total')):
            errors.append(f'款の表: {kid} に合計の行が無い')
            continue
        for c in AMT8:
            v = lambda k: ival(d[k][c])
            top_in = [k for k in d if re.fullmatch(r'in-[0-9]{2}', k)]
            top_out = [k for k in d if re.fullmatch(r'out-[0-9]{2}', k)]
            top_sei = [k for k in d if re.fullmatch(r'sei-[0-9]+', k)]
            # 合わない値が原典の誤りの記録の行（§13.11 で「原典のまま持つ」）のものだけなら通し、数える
            if sum(map(v, top_in)) != v('in-total') and not by_issue(f'{kid}/in-total'):
                errors.append(f'款の表: {kid} の {c} で款の和 ≠ 歳入合計')
            if sum(map(v, top_out)) != v('out-total') and not by_issue(f'{kid}/out-total'):
                errors.append(f'款の表: {kid} の {c} で款の和 ≠ 歳出合計（目的別）')
            if sum(map(v, top_sei)) != v('sei-total') and not by_issue(f'{kid}/sei-total'):
                errors.append(f'款の表: {kid} の {c} で区分の和 ≠ 歳出合計（性質別）')
            if not (v('in-total') == v('out-total') == v('sei-total')) and not by_issue(
                    *(f'{kid}/{k}' for k, o in (('in-total', 'out-total'), ('out-total', 'in-total'), ('sei-total', 'out-total'))
                      if v(k) != v(o))):
                errors.append(f'款の表: {kid} の {c} で歳入合計・歳出合計（目的別）・歳出合計（性質別）が同じでない')
            for p in top_in + top_sei:
                ch = [k for k in d if re.fullmatch(re.escape(p) + r'-[0-9]+', k)]
                if ch and sum(map(v, ch)) != v(p) and not by_issue(f'{kid}/{p}'):
                    errors.append(f'款の表: {kid} の {c} で {p} の内訳の和が合わない')
        for k, r in d.items():
            for a, b, h in (('mae', 'hosei', 'hoseigo'), ('mae_ippan', 'hosei_ippan', 'hoseigo_ippan')):
                if ival(r[a]) + ival(r[b]) != ival(r[h]) and not by_issue(f'{kid}/{k}'):
                    errors.append(f'款の表: {kid}/{k} で {a}＋{b} ≠ {h}')
            if r['tosho'] != d['in-total']['tosho'] and k == 'out-total':
                errors.append(f'款の表: {kid} の当初予算額が歳入と歳出で違う')
    for a, b in zip(order['ippan'], order['ippan'][1:]):
        for k, r in kan.get(b, {}).items():
            p = kan.get(a, {}).get(k)
            for c, h in (('mae', 'hoseigo'), ('mae_ippan', 'hoseigo_ippan')):
                pv = ival(p[h]) if p else 0
                if pv != ival(r[c]) and not by_issue(f'{b}/{k}'):
                    errors.append(f'款の表: 回のつながり {a} → {b} の {k} の {c}（{pv:,} / {ival(r[c]):,}）')
    toshos = {kan[k]['in-total']['tosho'] for k in order['ippan'] if k in kan}
    if len(toshos) != 1:
        errors.append(f'款の表: 当初予算額が回で違う: {toshos}')
    # 会計の額
    kk = [r for r in K['hosei-kaikei.tsv'] if r['kai'] in kais]
    for r in kk:
        if r['unit'] != '千円':
            errors.append(f"会計の額: {r['kai']}/{r['key']} の unit が千円でない")
        if ival(r['mae']) + ival(r['hosei']) != ival(r['hoseigo']):
            errors.append(f"会計の額: {r['kai']}/{r['key']} で mae＋hosei ≠ hoseigo")
        audited('hosei-kaikei', f"{r['kai']}/{r['key']}", C4, [r[c] for c in C4], r['unit'], f"{r['doc']} p.{r['page']}")
    grp = {}
    for r in kk:
        grp.setdefault((r['kai'], r['table'], r['flow'], r['part']), []).append(r)
    for g, rs in grp.items():
        tot = [r for r in rs if r['kaikei'] == '']
        if len(tot) != 1:
            errors.append(f'会計の額: {g} の合計の行が {len(tot)}行')
            continue
        for c in C4:
            if sum(ival(r[c]) for r in rs if r['kaikei']) != ival(tot[0][c]):
                errors.append(f'会計の額: {g} の {c} で会計の和 ≠ 合計')
    acc_rows = {}   # (kaikei, flow, part) → [行]（一般会計の回の順）
    for r in kk:
        if r['kai'] not in order['ippan']:
            errors.append(f"会計の額: {r['kai']} が一般会計の回でない")
            continue
        acc_rows.setdefault((r['kaikei'] or '合計:' + r['table'], r['flow'], r['part']), []).append(r)
    for g, rs in acc_rows.items():
        rs.sort(key=lambda r: order['ippan'].index(r['kai']))
        for a, b in zip(rs, rs[1:]):
            if a['hoseigo'] != b['mae'] and not by_issue(f"{b['kai']}/{b['key']}"):
                errors.append(f"会計の額: {g} のつながり {a['kai']} → {b['kai']}（{a['hoseigo']} / {b['mae']}）")
        if len({r['tosho'] for r in rs}) != 1 and not by_issue(
                *(f"{r['kai']}/{r['key']}" for r in rs if r['tosho'] != rs[0]['tosho'])):
            errors.append(f'会計の額: {g} の当初予算額が資料で違う')
    # 当初予算（data/totals-r<n>.json）との一致
    T = {a['name']: a['amount'] for a in totals[y]['accounts']}
    first = kan[order['ippan'][0]]['in-total']
    chk = [('一般会計', ival(first['mae']), '一般会計の最初の回の歳入合計の2つめの列')]
    tt = acc_rows.get(('合計:toku', '', ''))
    if tt:
        chk.append(('特別会計', ival(tt[0]['tosho']), '特別会計の表の合計の当初予算額'))
    ks = [acc_rows.get(('合計:kigyo', 'shishutsu', p)) for p in ('shueki', 'shihon')]
    if all(ks):
        chk.append(('企業会計', ival(ks[0][0]['tosho']) + ival(ks[1][0]['tosho']), '企業会計の表の支出の当初予算額（収益的＋資本的）'))
    # 特別会計の表・企業会計の表は、その会計の補正のある資料にだけ付く（§13.12）。表の無い年度は、その会計の回も無いことを確かめ、
    # 会計ごとの行を出さない（令和8年度の企業会計。取り込んだ回までに企業会計の補正が無い）
    no_table = []
    for name, part, accs in (('特別会計', 'toku', TOKU), ('企業会計', 'kigyo', KIGYO)):
        if any(c[0] == name for c in chk):
            continue
        if any(a in order for a in accs):
            errors.append(f'構造化の層 r{y}: {name}の回があるのに{name}の表が無い')
        no_table.append(part)
    if not tt and not all(ks):
        errors.append(f'構造化の層 r{y}: 特別会計・企業会計の表がどちらも無く、当初予算と突き合わせられない')
    for name, v, what in chk:
        if T.get(name) != v:
            errors.append(f'当初予算: {what} {v:,} ≠ data/totals-r{y}.json の{name} {T.get(name)}')
    # 決算（決算審査意見書。円）
    kgaku = {}
    for r in K['kessan-gaku.tsv']:
        kgaku.setdefault(r['kai'], {})[r['key']] = r
    ikensho = f'kessan-r{y}-ikensho'
    # 決算は、その年度の決算審査意見書の行があるときだけ出す。ある年度は、出す会計のすべてに意見書の行がそろうこと
    has_kessan = any(r['doc'] == ikensho for r in K['kessan-gaku.tsv'] if r['kai'].startswith(f'r{y}-'))

    def kessan_of(acc):
        if not has_kessan:
            return None
        d = kgaku.get(f'r{y}-{acc}', {})
        out = []
        for key in KESSAN_KEYS[acc]:
            r = d.get(key)
            if r is None:
                errors.append(f'決算: r{y}-{acc}/{key} が無い')
                continue
            if r['doc'] != ikensho or r['unit'] != '円':
                errors.append(f"決算: r{y}-{acc}/{key} の出典が {ikensho}（円）でない（{r['doc']}・{r['unit']}）")
            audited('kessan-gaku', f'r{y}-{acc}/{key}', ['value'], [r['value']], r['unit'], f"{r['doc']} p.{r['page']}")
            base, _, kanjo = key.partition('-') if acc == 'kaigo' else (key, '', '')
            out.append({'key': key, 'label': KESSAN_LABEL[base if acc == 'kaigo' else key],
                        'kanjo': {'hoken': '保険事業勘定', 'service': '介護サービス事業勘定'}.get(kanjo, ''),
                        'yen': ival(r['value']), 'ref': doc_ref(r['doc'], int(r['page']))})
        sfx = [('', )] if acc != 'kaigo' else [('-hoken',), ('-service',)]
        if acc not in KIGYO:
            for (s,) in sfx:
                g = {o['key']: o['yen'] for o in out}
                if g.get('sainyu' + s, 0) - g.get('saishutsu' + s, 0) != g.get('sashihiki' + s):
                    errors.append(f'決算: r{y}-{acc} で歳入総額−歳出総額 ≠ 歳入歳出差引額（{s or "総額"}）')
        return out

    maru = {}
    for r in K['hosei-maru.tsv']:
        if r['kai'] in kais:
            maru.setdefault(r['kai'], []).append(r)

    def steps_of(acc):
        """特別会計・企業会計の回ごとの行（会計の額の表から）。"""
        res = []
        accs = order.get(acc, [])
        kid_doc = {}
        for kid in accs:
            ds = {r['doc'] for r in shiryo.get(kid, []) if r['part'] in ('toku', 'kigyo')}
            if len(ds) != 1:
                errors.append(f'回と資料: {kid} の特別会計・企業会計の表の資料が {len(ds)}つ')
                continue
            kid_doc[ds.pop()] = kid
        cols = [('', '')] if acc in TOKU else KIGYO_COLS
        for ik in order['ippan']:
            rs = {(r['flow'], r['part']): r for r in kk if r['kai'] == ik and r['kaikei'] == acc}
            if not rs:
                continue
            doc = next(iter(rs.values()))['doc']
            hosei = [ival(rs[c]['hosei']) for c in cols if c in rs]
            kid = kid_doc.pop(doc, None)
            if kid is None:
                if any(hosei):
                    errors.append(f'会計の額: {acc} は {doc} で補正があるのに、その会計の回が無い')
                continue
            step = {'kai': kid, 'gou': int(kais[kid]['gou']), 'title': kais[kid]['title'],
                    'ref': doc_ref(doc, int(rs[cols[0]]['page'])),
                    'v': [[ival(rs[c]['hosei']), ival(rs[c]['hoseigo'])] for c in cols]}
            # 繰越明許費だけを定める回（主な内容の行の金額が「－千円」。DOCS_SCHEMA §13.6・§13.10）。
            # 主な内容の行が検収済みで、説明に「繰越明許費のみ」があり、会計の額の表の今回補正額が 0 であることを確かめ、原典の「－」を添える
            empty = [m for m in maru.get(kid, []) if m['kind'] == 'toku' and m['amount'] == '']
            if empty:
                m = empty[0]
                audited('hosei-maru', f"{kid}/{m['key']}", ['name', 'amount'], [m['name'], m['amount']], m['unit'],
                        f"{m['doc']} p.{m['page']}")
                if len(empty) != 1 or '繰越明許費のみ' not in m['desc'] or any(hosei):
                    errors.append(f"主な内容の行: {kid}/{m['key']} の金額が空だが、繰越明許費のみの回と確かめられない")
                step['hosei_raw'] = '－'
                step['hosei_desc'] = m['desc'].rstrip('。')
            if kais[kid]['prev'] == '' and int(kais[kid]['gou']) > 1:
                step['no_prev'] = True   # 号の前の回が回の表に無い（議案はあるが資料の無い回。§13.6）
            res.append(step)
        for doc, kid in kid_doc.items():
            errors.append(f'会計の額: {kid}（{doc}）の行が会計の額の表に無い')
        tosho = None
        for c in cols:
            rr = acc_rows.get((acc, c[0], c[1]))
            if rr:
                tosho = (tosho or []) + [ival(rr[0]['tosho'])]
        if tosho is None or len(tosho) != len(cols):
            errors.append(f'会計の額: {acc} の当初予算額が無い')
        return tosho, res

    accounts = []
    # 一般会計
    st = []
    for kid in order['ippan']:
        r = kan[kid]['in-total']
        pg = [s for s in shiryo.get(kid, []) if s['part'] == 'kan']
        if len(pg) != 1:
            errors.append(f'回と資料: {kid} の款の表のページが {len(pg)}つ')
            continue
        st.append({'kai': kid, 'gou': int(kais[kid]['gou']), 'title': kais[kid]['title'],
                   'label_hosei': kais[kid]['label_hosei'], 'ref': doc_ref(r['doc'], int(r['page'])),
                   'v': [[ival(r['hosei']), ival(r['hoseigo'])]], 'ippan': [ival(r['hosei_ippan']), ival(r['hoseigo_ippan'])],
                   'taitosho': r['taitosho']})
    accounts.append({'kaikei': 'ippan', 'name': ACC_NAME['ippan'], 'kind': 'ippan',
                     'tosho': [ival(first['tosho'])], 'tosho_ippan': ival(first['tosho_ippan']),
                     'steps': st, 'kessan': kessan_of('ippan')})
    in_table = {r['kaikei'] for r in kk if r['kaikei']}
    for acc in TOKU + KIGYO:
        if acc not in in_table and acc not in order:
            continue          # その年度の補正予算の概要の表に無い会計（令和5年度からの簡易水道・農業集落排水事業、令和8年度の企業会計）
        tosho, st = steps_of(acc)
        accounts.append({'kaikei': acc, 'name': ACC_NAME[acc], 'kind': 'toku' if acc in TOKU else 'kigyo',
                         'tosho': tosho, 'steps': st, 'kessan': kessan_of(acc)})
    n_steps = sum(len(a['steps']) for a in accounts)
    if n_steps != len(kais):
        errors.append(f'構造化の層 r{y}: 画面の回 {n_steps} ≠ 回の表の回 {len(kais)}')
    n_issue = sum(issue_used.values())
    yo = {'fy': y, 'label': f'令和{y}年度', 'accounts': accounts,
          'totals_src': {k: totals[y]['source'][k] for k in ('title', 'url', 'pdf_page', 'printed_page')},
          'n_kai': len(kais), 'n_kan': n_kan, 'n_kaikei': len(kk), 'n_issue': n_issue,
          'kessan_doc': doc_ref(ikensho, 0) if has_kessan else None,
          'issues': [{'file': 'data/struct/' + n, 'n': c} for n, c in sorted(issue_used.items())]}
    if no_table:
        yo['no_table'] = no_table
    if not has_kessan:
        # 決算の無い年度（年度の途中）は、取り込んだ最後の回の資料の題と日付を添える（日付は hino-town-docs の台帳の date）
        last_doc = max({s['doc'] for k in kais for s in shiryo.get(k, []) if s['part'] != 'kaiken'},
                       key=lambda d: (town_kz[d]['date'], d))
        t = town_kz[last_doc]
        yo['upto'] = {'doc': last_doc, 'title': t['title'], 'url': t['url'], 'date': t['date'],
                      'kai': sorted(k for k in kais if any(s['doc'] == last_doc for s in shiryo.get(k, [])))}
    kozo_years.append(yo)
    kz_report.append(f'令和{y}年度: 補正予算の回 {len(kais)}（' + '・'.join(f'{ACC_NAME[a]} {len(order[a])}' for a in ACC_ORDER if a in order) +
                     f'）、款の行 {n_kan}行・会計の額 {len(kk)}行、原典の誤りの記録により通した値 {n_issue}個、' +
                     ('決算あり' if has_kessan else f"決算なし（取り込んだ最後の資料 {yo['upto']['doc']}）") +
                     ('、表の無い会計の区分 ' + '・'.join(no_table) if no_table else ''))

# 財政指標
KZ_BUCKET = 'zaisei'
ZS = {r['key']: r for r in K['zaisei-shihyo.tsv']}
ichi = {(r['key'], r['year']): r for r in K['zaisei-ichi.tsv'] if r['col'] == ''}


def zrow(key):
    r = ZS.get(key)
    if r is None:
        errors.append(f'財政指標: {key} が無い')
        return None
    vals = []
    for yy in ZY:
        if yy not in r:
            errors.append(f'財政指標: {key} に年度の列 {yy} が無い')
            continue
        i = ichi.get((key, yy))
        if i is None:
            errors.append(f'財政指標: {key}/{yy} の値の位置が zaisei-ichi に無い')
            continue
        audited('zaisei-shihyo', f'{key}/{yy}', [yy], [r[yy]], r['unit'], f"{i['doc']} {i['sheet']}!{i['cell']}")
        vals.append(r[yy])
    return {'key': key, 'name': r['name'].strip().replace('　', ''), 'unit': r['unit'], 'v': vals,
            'docs': [ichi[(key, yy)]['doc'] for yy in ZY if (key, yy) in ichi]}


shihyo = []
for key in SHIHYO:
    o = zrow(key)
    if o is None:
        continue
    miss = [yy for yy, v in zip(ZY, o['v']) if v == '']
    if miss:
        errors.append(f"財政指標: {key}（{o['name']}）の年度が抜けている: {'・'.join(miss)}")
    if any(not re.fullmatch(r'-?[0-9]+(\.[0-9]+)?', v) for v in o['v'] if v):
        errors.append(f'財政指標: {key} に数でない値がある: {o["v"]}')
    cmp_ = []
    if key in HIKAKU:
        tk = zrow(f'hikaku-{HIKAKU[key]}-tokai')
        if tk and any(float(a) != float(b) for a, b in zip(o['v'], tk['v'])):
            errors.append(f'財政指標: {key} の総括表の値と財政比較分析表の当該団体の値が違う')
        for it, lb in (('zenkoku', '全国平均'), ('ken', '滋賀県平均'), ('juni', '類似団体内順位')):
            c = zrow(f'hikaku-{HIKAKU[key]}-{it}')
            if c:
                cmp_.append({'kind': 'hikaku', 'label': lb, 'unit': c['unit'], 'v': c['v']})
    if key in SOKI:
        c = zrow(f'soki-{key}')
        if c:
            cmp_.append({'kind': 'soki', 'label': '早期健全化基準', 'unit': c['unit'], 'v': c['v']})
    o['cmp'] = cmp_
    shihyo.append(o)
zdocs = {}
for yy in ZY:
    d = f'zaisei-{yy}-shiryoshu'
    zdocs[yy] = doc_ref(d, 0)

# 8. 決算と監査（DESIGN.md ADR-8）。年度は令和3〜7年度。3つの節（決算の内訳・健全化判断比率・監査の結果）を年度でそろえる -----
KK_YEARS = [3, 4, 5, 6, 7]
TXT = 'hino-town-docs/data/text/'


def ledger_state(table, row, cols, vals, unit, bucket):
    """監査の結果の行を検収の台帳で引く。出典（source）は表に無いので台帳の行から取り、照合キーを作り直して確かめる。
    'ok'（検収済み）か 'pending'（要人確認が残る・✓ でない）を返す。台帳に無い・値が違うときは誤り。"""
    hit = [r for n, r in LEDGER.values() if r['table'] == table and r['row'] == row]
    if len(hit) != 1:
        errors.append(f'検収の台帳: {table} {row} の行が {len(hit)}行')
        return None
    r = hit[0]
    if r['cols'] != ','.join(cols) or r['value'] != '|'.join(vals) or r['unit'] != unit:
        errors.append(f'検収の台帳: {table} {row} の値が台帳と違う（台帳 {r["value"][:40]!r}）')
        return None
    if row_key(table, row, r['cols'], r['value'], r['unit'], r['source']) != r['key']:
        errors.append(f'検収の台帳: {table} {row} の照合キーが作り直したものと違う')
        return None
    if r['checked'] != '✓' or r['note'].startswith('要人確認'):
        return 'pending'
    s = kz_used.setdefault(('audit/kansa.tsv', bucket), {'n': 0, 'a': 0, 'k': 0, 'b': 0, 'c': 0})
    s['n'] += 1
    s[{'auto:pdftext': 'a', 'auto:check': 'k', 'auto:ai': 'b'}.get(r['reviewer'], 'c')] += 1
    return 'ok'


# 8a. 決算の内訳（一般会計。決算の概要の円グラフの項目。単位は原典の万円のまま）
UW_GROUPS = ['sainyu', 'sainyu-naka', 'seishitsu', 'seishitsu-naka', 'mokuteki']
uw_issue = {}
for r in K['issues/kessan-r3-gaiyou.tsv']:
    if r['status'] == '原典のまま持つ':
        for w in re.findall(r'r[0-9]+-ippan/u[0-9]{3}', r['where']):
            uw_issue[w] = {'issue': r['issue'], 'file': 'data/struct/issues/kessan-r3-gaiyou.tsv', 'no': r['no']}
uchiwake = {}
for y in KK_YEARS:
    KZ_BUCKET = f'kk-r{y}'
    rs = [r for r in K['kessan-uchiwake.tsv'] if r['kai'] == f'r{y}-ippan']
    if not rs:
        continue          # 決算の概要の無い年度（令和7年度）。図を出さず、無いことを画面に書く
    doc = {r['doc'] for r in rs}
    if doc != {f'kessan-r{y}-gaiyou'}:
        errors.append(f'決算の内訳 r{y}: 出典が kessan-r{y}-gaiyou だけでない（{sorted(doc)}）')
    g = {}
    for r in rs:
        if r['unit'] != '万円' or r['group'] not in UW_GROUPS:
            errors.append(f"決算の内訳: {r['kai']}/{r['key']} の unit か group が違う（{r['unit']}・{r['group']}）")
            continue
        if not re.fullmatch(r'[0-9]+', r['value']) or (r['ratio'] and not re.fullmatch(r'[0-9]+(\.[0-9]+)?', r['ratio'])):
            errors.append(f"決算の内訳: {r['kai']}/{r['key']} の value か ratio の形が違う")
            continue
        audited('kessan-uchiwake', f"{r['kai']}/{r['key']}", ['name', 'value'], [r['name'], r['value']], r['unit'],
                f"{r['doc']} p.{r['page']}")
        o = {'key': r['key'], 'name': r['name'], 'value': int(r['value']), 'ratio': r['ratio'], 'page': int(r['page'])}
        iss = uw_issue.get(f"{r['kai']}/{r['key']}")
        if iss:
            o['raw'] = r['raw']
            o['issue'] = iss
        g.setdefault(r['group'], []).append(o)
    # 検算：外側の輪の和＝内側の輪の和（歳入、性質別の歳出）。目的別の歳出しかない年度は内側の輪が無い
    sides = []
    for outer, inner in (('sainyu', 'sainyu-naka'), ('seishitsu', 'seishitsu-naka'), ('mokuteki', None)):
        if outer not in g:
            continue
        so = sum(o['value'] for o in g[outer])
        if inner:
            if inner not in g:
                errors.append(f'決算の内訳 r{y}: {outer} はあるが {inner} が無い')
            elif sum(o['value'] for o in g[inner]) != so:
                errors.append(f'決算の内訳 r{y}: {outer} の和 {so:,} ≠ {inner} の和 {sum(o["value"] for o in g[inner]):,}')
        sides.append(outer)
    if 'sainyu' not in g or not ({'seishitsu', 'mokuteki'} & set(g)):
        errors.append(f'決算の内訳 r{y}: 歳入か歳出の内訳が無い')
    uchiwake[str(y)] = {'groups': g, 'ref': {**doc_ref(f'kessan-r{y}-gaiyou', 0), 'bytes': int(town_kz[f'kessan-r{y}-gaiyou']['bytes'])}}

# 8b. 健全化判断比率と資金不足比率（総括表の値と、シート03 の基準。選んだ年度の値だけ）
KZ_KEYS = [('jisshitsu-akaji', True), ('renketsu-akaji', True), ('jisshitsu-kosaihi', True), ('shorai-futan', True),
           ('shikin-fusoku', False)]
# 総括表の注釈の字（各年度の資料の総括表にあることを確かめて載せる）
KZ_NOTE4 = '※4：資金不足比率欄には、資金が不足している会計のみ記載している。'
KZ_NOTE6 = '（その他、数値のない欄については、すべてハイフン（－）としている）'
kz_years = [f'r{y}' for y in KK_YEARS if f'r{y}' in ZY]


def zcell(key, yy):
    r = ZS.get(key)
    i = ichi.get((key, yy))
    if r is None or i is None or yy not in r:
        errors.append(f'健全化判断比率: {key}/{yy} が無いか値の位置が無い')
        return ''
    audited('zaisei-shihyo', f'{key}/{yy}', [yy], [r[yy]], r['unit'], f"{i['doc']} {i['sheet']}!{i['cell']}")
    if r['unit'] != '％':
        errors.append(f'健全化判断比率: {key} の unit が ％ でない')
    if r[yy] not in ('', '-') and not re.fullmatch(r'[0-9]+(\.[0-9]+)?', r[yy]):
        errors.append(f'健全化判断比率: {key}/{yy} の値の形が違う（{r[yy]!r}）')
    return r[yy]


kz_items = []
for key, has_kijun in KZ_KEYS:
    o = {'key': key, 'name': ZS[key]['name'].strip().replace('　', '').replace(' (※4)', ''), 'v': {}, 'soki': {}, 'saisei': {}}
    for yy in kz_years:
        KZ_BUCKET = f'kk-kenzenka-{yy}'
        o['v'][yy] = zcell(key, yy)
        if has_kijun:
            o['soki'][yy] = zcell(f'soki-{key}', yy)
            o['saisei'][yy] = zcell(f'saisei-{key}', yy)
    kz_items.append(o)
for yy in kz_years:
    t = files.get(f'{TXT}zaisei-{yy}-shiryoshu/01.tsv')
    if t is None:
        errors.append(f'lock: {TXT}zaisei-{yy}-shiryoshu/01.tsv が inputs.lock.json に載っていない')
    elif KZ_NOTE4 not in t or KZ_NOTE6 not in t:
        errors.append(f'健全化判断比率: zaisei-{yy}-shiryoshu の総括表に注釈 ※4・※6 の字が無い')
kenzenka = {'years': kz_years, 'items': kz_items,
            'docs': {yy: {**zdocs[yy], 'bytes': int(town_kz[f'zaisei-{yy}-shiryoshu']['bytes'])} for yy in kz_years},
            'note4': KZ_NOTE4, 'note6': KZ_NOTE6.strip('（）')}

# 8c. 監査の結果（DOCS_SCHEMA §13.15）。報告の表・事項の表・検収の台帳・台帳の title と url・文字の層の結果の文
SHURUI = {'teiki': '課の定期監査', 'dantai': '団体の監査'}
ZEN = str.maketrans('０１２３４５６７８９', '0123456789')
KEKKA_HEAD = re.compile(r'^\s*[６6][．.]\s*監\s*査\s*の\s*結\s*果\s*')
SHITEKI_HEAD = re.compile(r'^イ[．.]\s*指摘事項$')
kekka_by = {r['doc']: r for r in K['kansa-kekka.tsv']}
jiko_by = {}
for r in K['kansa-jiko.tsv']:
    jiko_by.setdefault(r['doc'], []).append(r)


def ksort(y, title, kansa_bi=''):
    """並べるための日付の数（YYYYMMDD）。監査の日の字から読み、無ければ台帳の題の月（日は 0）。読めなければ None。"""
    m = re.match(r'令和([0-9]+)年([0-9]+)月([0-9]+)日', kansa_bi.translate(ZEN))
    if m:
        return (2018 + int(m.group(1))) * 10000 + int(m.group(2)) * 100 + int(m.group(3))
    m = re.match(r'([0-9]+)月', title.split(' ', 1)[1] if ' ' in title else '')
    if m:
        mo = int(m.group(1))
        return (2018 + y + (1 if mo <= 3 else 0)) * 10000 + mo * 100
    return None


def paragraphs(lines):
    """文字の層の行の折り返しをつなぐ。行の前後の空白を除き、つなぎ目に空白を入れない（字は直さない）。
    行が「。」で終わるところと、「ア．」「イ．」などの見出しの行の前後で段落を分ける。"""
    out, cur = [], ''
    for raw in lines:
        s = raw.replace('\f', '').strip()
        if not s:
            continue
        mk = re.match(r'^[アイウエ][．.]', s)
        if mk and cur:
            out.append(cur)
            cur = ''
        cur += s
        if s.endswith('。') or mk:
            out.append(cur)
            cur = ''
    if cur:
        out.append(cur)
    return out


nows = lambda s: re.sub(r'\s', '', s)
kansa = []
kansa_n = {}
for y in KK_YEARS:
    srows = [r for r in trows if r['category'] == 'kansa' and r['fiscal_year'] == str(2018 + y)]
    KZ_BUCKET = f'kk-kansa-r{y}'
    cnt = {'n': len(srows), 'full': 0, 'image': 0, 'pending': 0, 'teiki': 0, 'dantai': 0}
    for s in sorted(srows, key=lambda r: r['id']):
        if not re.fullmatch(rf'kansa-r{y}-[0-9]{{2}}', s['id']) or not s['url'].startswith('https://') or s['format'] != 'pdf':
            errors.append(f"監査の結果: 台帳の {s['id']} の id・url・format の形が違う")
            continue
        head, _, rest = s['title'].partition(' ')
        if head != f'令和{y}年度監査等の結果' or not rest:
            errors.append(f"監査の結果: 台帳の {s['id']} の題が「令和{y}年度監査等の結果 <月と対象>」の形でない（{s['title']}）")
        o = {'doc': s['id'], 'fy': y, 'title_rest': rest, 'url': s['url'], 'bytes': int(s['bytes'])}
        k = kekka_by.get(s['id'])
        if s['check'] == 'image':
            if k is not None:
                errors.append(f"監査の結果: {s['id']} は台帳の check が image なのに報告の表に行がある")
            o['mode'] = 'image'
        elif s['check'] == 'ok':
            if k is None:
                errors.append(f"監査の結果: {s['id']} は台帳の check が ok なのに報告の表に行が無い")
                continue
            if k['shurui'] not in SHURUI:
                errors.append(f"監査の結果: {s['id']} の shurui が決まった語彙にない（{k['shurui']!r}）")
                continue
            cols = ['shurui', 'kokuji', 'kohyo_bi', 'kansa_bi', 'taisho', 'shiteki', 'kekka_from', 'kekka_to']
            st = [ledger_state('kansa-kekka', s['id'], cols, [k[c] for c in cols], '', KZ_BUCKET)]
            js = sorted(jiko_by.get(s['id'], []), key=lambda r: int(r['n']))
            if [int(r['n']) for r in js] != list(range(1, len(js) + 1)) or not js:
                errors.append(f"監査の結果: {s['id']} の事項の n が1からの連番でない")
            for r in js:
                st.append(ledger_state('kansa-jiko', f"{s['id']}/{r['n']}", ['jiko', 'komoku', 'gaku', 'gaku_raw'],
                                       [r['jiko'], r['komoku'], r['gaku'], r['gaku_raw']], '円' if r['gaku'] else '', KZ_BUCKET))
            if None in st:
                continue
            if 'pending' in st:
                # 照合の済んでいない値は使わない。題と PDF だけの行にする
                o['mode'] = 'pending'
            else:
                o['mode'] = 'full'
                o.update({'shurui': k['shurui'], 'kokuji': k['kokuji'], 'kohyo_bi': k['kohyo_bi'], 'kansa_bi': k['kansa_bi'],
                          'taisho': k['taisho'] or rest})
                if not k['taisho']:
                    o['taisho_title'] = True     # 対象を読めなかった本は、台帳の題の字を対象として出す
                o['jiko'] = [{'jiko': r['jiko'], 'komoku': r['komoku'], 'gaku': int(r['gaku']) if r['gaku'] else None} for r in js]
                for j, r in zip(o['jiko'], js):
                    if (k['shurui'] == 'dantai') != (j['gaku'] is not None):
                        errors.append(f"監査の結果: {s['id']}/{r['n']} の額の有無が報告の種類と合わない")
                # 結果の文（data/text の kekka_from〜kekka_to の行）
                t = files.get(f"{TXT}{s['id']}.txt")
                if t is None:
                    errors.append(f"lock: {TXT}{s['id']}.txt が inputs.lock.json に載っていない")
                    continue
                L = t.split('\n')
                a, b = int(k['kekka_from']), int(k['kekka_to'])
                if not (1 <= a <= b <= len(L)):
                    errors.append(f"監査の結果: {s['id']} の kekka_from・kekka_to が文字の層の行の範囲に無い")
                    continue
                seg = L[a - 1:b]
                if KEKKA_HEAD.match(seg[0].replace('\f', '')):
                    seg[0] = KEKKA_HEAD.sub('', seg[0].replace('\f', ''))   # 見出しと本文の始まりが同じ行の本は、見出しの字を除く
                    o['head_cut'] = True
                if k['shurui'] == 'dantai':
                    # 団体の監査は「イ．指摘事項」の行で分け、後ろは報告の表の shiteki と同じ字であることを確かめて、指摘事項として出す
                    hs = [i for i, l in enumerate(seg) if SHITEKI_HEAD.match(l.replace('\f', '').strip())]
                    if len(hs) != 1 or nows(''.join(seg[hs[0] + 1:]).replace('\f', '')) != nows(k['shiteki']):
                        errors.append(f"監査の結果: {s['id']} の結果の文の「イ．指摘事項」の後ろが shiteki と同じでない")
                        continue
                    seg = seg[:hs[0]]
                    o['shiteki'] = k['shiteki']
                o['kekka'] = paragraphs(seg)
                if not o['kekka'] or nows(''.join(o['kekka'])) != nows(''.join(seg).replace('\f', '')):
                    errors.append(f"監査の結果: {s['id']} の結果の文をつないだ字が文字の層の字と違う")
                cnt[k['shurui']] += 1
        else:
            errors.append(f"監査の結果: 台帳の {s['id']} の check が ok でも image でもない（{s['check']!r}）")
            continue
        cnt[o['mode']] += 1
        o['ord'] = ksort(y, s['title'], o.get('kansa_bi', ''))
        kansa.append(o)
    kansa_n[str(y)] = cnt
miss = set(kekka_by) - {o['doc'] for o in kansa}
if miss:
    errors.append(f'監査の結果: 報告の表にあって、画面の年度の台帳の行に無い本: {sorted(miss)}')
kk = {
    'years': KK_YEARS, 'uchiwake': uchiwake, 'kenzenka': kenzenka,
    'kansa': {'reports': kansa, 'n': kansa_n},
}
if errors:
    fail_now()
kk['audit'] = {b: {'file': 'data/struct/' + n, **s} for (n, b), s in sorted(kz_used.items()) if b.startswith('kk-')}
for yo in kozo_years:   # 年度ごとの、使った行の検収（補正予算の台帳と決算の台帳）
    b = f"r{yo['fy']}"
    yo['audit'] = {('hosei' if n.startswith('audit/hosei-') else 'kessan'): {'file': 'data/struct/' + n, **s}
                   for (n, bb), s in sorted(kz_used.items()) if bb == b}
kozo = {
    'commit': TD_COMMIT, 'years': kozo_years,
    'shihyo': {'years': ZY, 'items': shihyo, 'docs': [zdocs[yy] for yy in ZY]},
    'audit': {'zaisei': {'file': 'data/struct/audit/zaisei.tsv', **kz_used[('audit/zaisei.tsv', 'zaisei')]}},
}

# 書き出し -----------------------------------------------------------------------
out_items = []
for y in YEARS:
    for p, it in items[y]:
        o = {
            'fy': y, 'key': it['key'], 'pillar': p['no'], 'kubun': it['kubun'], 'kan': it['kan'],
            'name': it['name'], 'desc': it['desc'], 'details': it['details'], 'amount': it['amount'],
            'dept': it['dept'], 'page': it['page'], 'chain': chain_of[(y, it['key'])],
        }
        if y == LINK_YEAR:
            o['jisshi'] = [{'key': ek, 'name': E[ek]} for ek in sorted(node_of[it['key']])]
        out_items.append(o)
years = []
for y in YEARS:
    d, s, t = fuhyo[y], srow[y], totals[y]
    years.append({
        'fy': y, 'label': d['fiscal_year']['label'], 'year': d['fiscal_year']['year'],
        'source': {'id': f'fuhyo-r{y}', 'file': d['source']['file'], 'page_id': d['source'].get('page_id', ''),
                   'label': s['label'], 'url': s['url'], 'fetched': s['fetched']},
        'audit': audit[y], 'issues': issues[y],
        'totals': {'source': {k: t['source'][k] for k in ('title', 'url', 'pdf_page', 'printed_page', 'fetched')},
                   'accounts': t['accounts'], 'total': t['total']['amount']},
    })
meta = {
    'years': years,
    'pillars': [{'no': no, 'name': name} for no, name in pillar_names],
    'inputs': sorted({(e['repo'], e['commit']) for e in lock['inputs']}),
    'plan': {'id': PLAN_ID, 'name': jisshi['meta']['name'], 'fy': LINK_YEAR},
    'chains': {'n': len(chains), 'name': ny['name'], 'manual': ny['manual']},
    'kozo': kozo,
    'kk': kk,
}
meta['inputs'] = [{'repo': r, 'commit': c} for r, c in meta['inputs']]
js = ['/* tools/build_data.py で生成。直接編集しない。材料と版は inputs.lock.json にある。 */',
      'const BUDGET = ' + json.dumps(meta, ensure_ascii=False)[:-1] + ', "items": [']
js += [json.dumps(o, ensure_ascii=False) + (',' if i < len(out_items) - 1 else '') for i, o in enumerate(out_items)]
js += [']};', '']
(ROOT / 'data.js').write_text('\n'.join(js), encoding='utf-8')

# 報告 ---------------------------------------------------------------------------
fmt = lambda n: f'{n:,}'
print(f'材料: {len(lock["inputs"])}ファイルとも sha256 が inputs.lock.json と一致')
print('附表（事業数・予算額の合計・新規・拡充）:')
for y in YEARS:
    its = [it for _, it in items[y]]
    print(f"  令和{y}年度: {len(its)}件・{fmt(sum(it['amount'] for it in its))}千円"
          f"（新規 {sum(1 for it in its if '新規' in it['kubun'])}・拡充 {sum(1 for it in its if '拡充' in it['kubun'])}）")
print(f'  合計: {len(out_items)}件')
print('柱ごとの予算額（千円）:')
for no, name in pillar_names:
    print(f"  柱{no} {name}: " + '・'.join(f"R{y} {fmt(sum(it['amount'] for p, it in items[y] if p['no'] == no))}" for y in YEARS))
print('検収の台帳（照合の対象／済み／人の抜き取り 済み／対象）と段3の未判断:')
for y in YEARS:
    s, i = audit[y], issues[y]
    print(f"  令和{y}年度: {s['n']}行／{s['m']}行（プログラム {s['a']}・AI {s['b']}・人 {s['c']}）／抜き取り {s['x']}／{s['f']}"
          f"、段3 未判断 {i['pending']}／{i['rows']}件、記録の最終日 {s['last']}")
nc = sum(1 for r in lrows if r['status'] == 'confirmed')
nr = sum(1 for r in lrows if r['status'] == 'rejected')
print(f'対応の台帳（令和{LINK_YEAR}年度）: confirmed {nc}行（実施計画の事業 {sum(len(v) for v in node_of.values())}行・'
      f'記載なし {sum(none_of.values())}行）、rejected {nr}行、candidate 0行')
print(f'  実施計画の事業に対応 {sum(1 for v in node_of.values() if v)}事業、記載なし {sum(1 for v in none_of.values() if v)}事業')
print(f"年度の台帳: confirmed {len(edges)}行（名前の一致 {ny['name']}・手でつないだ {ny['manual']}）、rejected {ny['rejected']}行。"
      f"束ねた事業 {len(chains)}本（6年とも載る {sum(1 for g in chains if len(g) == len(YEARS))}本・1年だけ {sum(1 for g in chains if len(g) == 1)}本）")
print('当初予算の総額（data/totals-r<n>.json、千円）:')
for y in YEARS:
    t = totals[y]
    print(f"  令和{y}年度: " + '・'.join(f"{a['name']} {fmt(a['amount'])}" for a in t['accounts'])
          + f" ＝ 合計 {fmt(t['total']['amount'])}（{t['source']['title']} {t['source']['printed_page']}ページ）")
print('構造化の層（hino-town-docs data/struct/）:')
for x in kz_report:
    print('  ' + x)
print('  財政指標: ' + '・'.join(o['name'] for o in shihyo) + f'（{len(shihyo)}指標×{len(ZY)}年度、抜け 0）')
print('  使った行の検収（台帳ごと。行数／プログラムの照合・機械の検算・AI・人）: ' + '、'.join(
    f"{n}（{b}） {s['n']}行／{s['a']}・{s['k']}・{s['b']}・{s['c']}" for (n, b), s in sorted(kz_used.items())))
print('決算と監査（令和3〜7年度）:')
print('  決算の内訳（一般会計）: ' + '、'.join(f"令和{y}年度 " + ('・'.join(f"{g} {len(v)}項目 {fmt(sum(o['value'] for o in v))}万円" for g, v in kk['uchiwake'][str(y)]['groups'].items()) if str(y) in kk['uchiwake'] else 'なし') for y in KK_YEARS))
print('  健全化判断比率: ' + '、'.join(f"{o['name']} " + '・'.join(f"{yy} {o['v'][yy] or '空'}" for yy in kz_years) for o in kz_items))
for y in KK_YEARS:
    c = kansa_n[str(y)]
    print(f"  監査の結果 令和{y}年度: 台帳 {c['n']}本 ＝ 内容を出す {c['full']}本（課の定期監査 {c['teiki']}・団体の監査 {c['dantai']}）＋ 照合が済んでいないため題と PDF だけ {c['pending']}本 ＋ 画像の PDF {c['image']}本")
print('  使った行の検収: ' + '、'.join(f"{b} {s['n']}行／{s['a']}・{s['k']}・{s['b']}・{s['c']}" for b, s in kk['audit'].items()))
print('検算 OK。data.js を書き出しました。')
