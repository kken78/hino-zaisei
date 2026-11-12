#!/usr/bin/env python3
"""決算審査の流れと、決算審査の意見を引いた発言の、つなぎの表の候補を作る（標準ライブラリのみ。DESIGN.md ADR-9）。

作る表（data/links/）:
  kessan-nagare.tsv   決算の年度ごとの、議会での流れ（年度 × 段階。採決は採決ごとに1行）
  iken-yaritori.tsv   決算審査の意見書を踏まえた質疑のやりとり（やりとり1つ × 意見書の箇所1つ）
  inputs.json         読んだ材料の、リポジトリ・commit・パス・sha256

材料（読むだけ）:
  hino-town-docs       data/struct/kessan-iken.tsv           決算審査の意見の表（DOCS_SCHEMA.md §13.16）
                       data/text/kessan-r<n>-ikensho.txt      意見書の文字の層（行のページと印刷のページ番号を数える）
  hino-council-search  public/data/meetings.json・gian.json・proceedings.json・index/<年>.json

使い方:
  python3 tools/build_links.py [--src <フォルダ>] [--council <hino-council-search の場所>]
      候補を作り直す。人の印（status が confirmed・rejected の行）と、人が書いた値を保つ。
  python3 tools/build_links.py --check [...]
      表を書かずに確かめる。表が指す sid が会議録にあること、iken のキーが意見の表にあること、
      範囲の前後、列の値、材料の sha256 が inputs.json と同じことを確かめる。合わなければ終了コード 1。
"""
import argparse, hashlib, json, pathlib, re, subprocess, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
LINKS = ROOT / 'data' / 'links'
NAGARE = LINKS / 'kessan-nagare.tsv'
YARITORI = LINKS / 'iken-yaritori.tsv'
INPUTS = LINKS / 'inputs.json'

# 決算の年度（令和）→ 翌年度の9月定例会・12月定例会の会議の ID。
# 令和7年度の決算は、令和8年9月の定例会がまだ会議録に無いので持たない（作るときに確かめて表示する）。
NENDO = {
    3: ('0000006801', '0000006923'),
    4: ('0000007383', '0000007562'),
    5: ('0000008116', '0000008211'),
    6: ('0000008582', '0000008691'),
}
DANKAI = ['teian', 'setsumei', 'kansa', 'shitsugi', 'futaku', 'hokoku', 'toron', 'saiketsu']
DANKAI_JI = {'teian': '提案の説明', 'setsumei': '決算の説明', 'kansa': '監査委員の審査報告', 'shitsugi': '質疑',
             'futaku': '委員会への付託', 'hokoku': '委員長報告', 'toron': '討論', 'saiketsu': '採決'}
HIKIKATA = ['bango', 'page', 'go']
DANKAI_YARITORI = ('shitsugi', 'hokoku', 'toron')
STATUS = ['candidate', 'confirmed', 'rejected']

NAGARE_COLS = ['nendo', 'doc', 'dankai', 'n', 'meeting', 'date', 'sid_from', 'sid_to', 'gian', 'kekka', 'hoho',
               'status', 'reviewer', 'date_kakunin', 'note']
NAGARE_KEY = ('nendo', 'dankai', 'n')
NAGARE_TOOL = ['doc', 'meeting', 'date', 'sid_from', 'sid_to', 'gian', 'kekka', 'hoho']
YARITORI_COLS = ['nendo', 'doc', 'sid_q', 'sid_a', 'role_q', 'role_a', 'hikikata', 'kyoshutsu', 'konkyo',
                 'insatsu_page', 'iken', 'basho', 'status', 'reviewer', 'date_kakunin', 'note']
YARITORI_KEY = ('sid_q', 'kyoshutsu', 'hikikata', 'konkyo')
YARITORI_TOOL = ['nendo', 'doc', 'sid_a', 'role_q', 'role_a', 'insatsu_page', 'iken', 'basho']
BASHO = ['iken', 'hyo', 'fumei']
KYOSHUTSU = ['q', 'a']
MIDASHI_MAX = 20
GIIN = re.compile(r'[0-9０-９]+番')

CHAIR = {'議長', '副議長', '臨時議長', '新議長', '新副議長'}
KONKYO_MAX = 15

# 候補を拾う字（指示のとおり4つ）
KW = re.compile(r'意見書|監査委員|監査の|審査意見')
# 根拠の字として切り出す形（頭の「各会計」「決算」「審査」と後ろの「さん」を含める）
ANCHOR = re.compile(r'(?:各会計)?(?:決算(?:審査)?(?:の)?)?意見書|審査意見|監査委員(?:さん)?|監査の(?:指摘|意見|報告|結果)?')
# 話している意見書が、決算審査意見書であることが分かる字
KESSAN_IKENSHO = re.compile(r'決算(?:審査)?(?:の)?意見書|審査意見書|監査委員(?:さん)?(?:の|から(?:の)?|が)(?:出[^、。]{0,6})?意見書|監査委員(?:さん)?(?:の|から)[^。]{0,20}意見書')
# 「監査委員」が人や役を指す言い方
HITO = re.compile(r'監査委員(?:で(?:ある|あった|あります)|を除|をさせ|をして|に(?:選|就)|の(?:選任|任期|方|皆)|が決められ)|(?:議会選出|代表)の?監査委員')
# 「意見書」の後ろで、ページや番号を見る字の数
WINDOW = 200
NEAR = 60
# 別の資料の名前。ここから先のページは意見書のページとみなさない
OTHER_DOC = re.compile(r'決算書|補正予算|予算書|主要施策|決算資料|事項別明細|資料の|説明書|附属書類')
MARU = '①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳'
PAGE = re.compile(r'([0-9０-９]{1,3})ページ')
ZEN = str.maketrans('０１２３４５６７８９', '0123456789')


def die(msg):
    print(msg, file=sys.stderr)
    sys.exit(1)


def sha256(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


# ---------------------------------------------------------------- 材料

class Council:
    """hino-council-search の公開データを読む。"""

    def __init__(self, base):
        d = base / 'public' / 'data'
        self.base = base
        self.files = {}
        self.meetings = {m['id']: m for m in self._json(d, 'meetings.json')}
        self.gian = self._json(d, 'gian.json')
        self.proc = self._json(d, 'proceedings.json')
        self.speech = {}
        self.by_meeting = {}
        years = sorted({int(self.meetings[mid]['year']) for pair in NENDO.values() for mid in pair})
        for y in years:
            for s in self._json(d, f'index/{y}.json'):
                # 目次の PDF の発言（sid の真ん中が日付でないもの）は読まない
                if s['meetingId'] in {mid for pair in NENDO.values() for mid in pair} and SID.match(s['sid']):
                    self.speech[s['sid']] = s
                    self.by_meeting.setdefault(s['meetingId'], []).append(s)
        for mid in self.by_meeting:
            self.by_meeting[mid].sort(key=lambda s: s['sid'])
        self.pos = {mid: {s['sid']: i for i, s in enumerate(ss)} for mid, ss in self.by_meeting.items()}

    def _json(self, d, rel):
        p = d / rel
        if not p.exists():
            die(f'材料がありません: {p}')
        self.files['public/data/' + rel] = p
        return json.loads(p.read_text(encoding='utf-8'))

    def segs(self, mid):
        return self.proc.get(mid, {}).get('segments', [])

    def text(self, sid):
        return self.speech[sid]['text'].replace('\n', '')


class Iken:
    """hino-town-docs の決算審査の意見の表と、意見書の文字の層の、行ごとの印刷のページ番号。"""

    def __init__(self, base):
        self.base = base
        self.files = {}
        p = base / 'data' / 'struct' / 'kessan-iken.tsv'
        self.files['data/struct/kessan-iken.tsv'] = p
        if not p.exists():
            die(f'材料がありません: {p}')
        rows = read_tsv_rows(p)
        self.rows = {}
        for r in rows:
            r['key'] = f"{r['doc']}/{r['bubun']}/{r['kaikei']}/{r['n']}"
            self.rows[r['key']] = r
        self.insatsu = {}
        for n in NENDO:
            doc = f'kessan-r{n}-ikensho'
            tp = base / 'data' / 'text' / f'{doc}.txt'
            self.files[f'data/text/{doc}.txt'] = tp
            if not tp.exists():
                die(f'材料がありません: {tp}')
            self._pages(doc, tp.read_text(encoding='utf-8'))

    def _pages(self, doc, text):
        self.lines = getattr(self, 'lines', {})
        self.lines[doc] = text.split('\n')
        pages = text.split('\f')
        ins = []
        for pg in pages:
            ls = [l.strip() for l in pg.split('\n') if l.strip()]
            num = ''
            for l in ls[-3:]:
                if re.fullmatch(r'[0-9]{1,3}', l):
                    num = l
            ins.append(int(num) if num else None)
        self.ins = getattr(self, 'ins', {})
        self.ins[doc] = ins
        self.pages_text = getattr(self, 'pages_text', {})
        self.pages_text[doc] = pages
        lines = text.split('\n')
        starts, off = [], 0
        for l in lines:
            starts.append(off)
            off += len(l) + 1
        for r in self.rows.values():
            if r['doc'] != doc or not r['line_from']:
                continue
            a, b = int(r['line_from']), int(r['line_to'])
            la, lb = lines[a - 1], lines[b - 1]
            pa = text.count('\f', 0, starts[a - 1] + len(la) - len(la.lstrip('\f'))) + 1
            pb = text.count('\f', 0, starts[b - 1] + len(lb.rstrip())) + 1
            if str(pa) != r['page']:
                die(f"{r['key']}: 行 {a} のページ {pa} が表の page {r['page']} と違います")
            nums = [ins[p - 1] for p in range(pa, pb + 1) if ins[p - 1] is not None]
            r['ins_from'], r['ins_to'] = (min(nums), max(nums)) if nums else (None, None)

    def row_text(self, key):
        r = self.rows[key]
        if not r['line_from']:
            return ''
        ls = self.lines[r['doc']][int(r['line_from']) - 1:int(r['line_to'])]
        return norm(''.join(ls))

    def ippan_bango(self, nendo, maru):
        for r in self.rows.values():
            if (r['doc'] == f'kessan-r{nendo}-ikensho' and r['kaikei'] == 'ippan' and r['bubun'] == 'matome'
                    and r['bango'] == maru):
                return r['key']
        return ''

    def midashi(self, nendo, page):
        """印刷のページ page が意見書のどの章・節にあるかを、data/text の見出しの行の字で返す（読めなければ空）。

        見出しの行は、行の字（前後の空白を除く）が「<数字>．」か「（<数字>）」で始まり、その後ろが数字でなく、
        「令和」を含まない行。章は、そのうち「会計」で終わる行。印刷のページ番号が page の PDF のページ（1つに
        決まるとき）について、そのページの最後までで最後の章の見出しと、その章の見出しより後でそのページの
        始まりまでで最後の見出し（無ければ空）と、そのページの中の見出しを、原典の字のまま「／」でつなぐ。
        20字を超えれば章を除き、それでも超えれば空にする。
        """
        doc = f'kessan-r{nendo}-ikensho'
        ps = [i for i, x in enumerate(self.ins[doc]) if x == page]
        if len(ps) != 1:
            return ''
        P = ps[0]
        head = re.compile(r'^(?:[0-9０-９]+[．.]\s*[^0-9０-９.．\s]|[（(][0-9０-９]+[）)]\S)')
        def hs(pg):
            return [l.strip() for l in pg.split('\n') if head.match(l.strip()) and '令和' not in l]
        chap, sec = '', ''
        for pg in self.pages_text[doc][:P]:
            for h in hs(pg):
                if h.endswith('会計'):
                    chap, sec = h, ''
                else:
                    sec = h
        on = []
        for h in hs(self.pages_text[doc][P]):
            if h.endswith('会計'):
                chap, sec, on = h, '', []
            else:
                on.append(h)
        secs = ([sec] if sec else []) + on
        for parts in ([chap] + secs, secs):
            x = '／'.join(p for p in parts if p)
            if x and len(x) <= MIDASHI_MAX:
                return x
        return ''

    def on_page(self, nendo, page):
        return [k for k, r in self.rows.items()
                if r['doc'] == f'kessan-r{nendo}-ikensho' and r.get('ins_from') is not None
                and r['ins_from'] <= page <= r['ins_to']]


# ---------------------------------------------------------------- TSV

def read_tsv(p):
    lines = p.read_text(encoding='utf-8').split('\n')
    if lines and lines[-1] == '':
        lines.pop()
    head = lines[0].split('\t')
    out = []
    for i, l in enumerate(lines[1:], 2):
        v = l.split('\t')
        if len(v) != len(head):
            die(f'{p}: {i}行目の列の数が {len(v)}（見出しは {len(head)}）')
        out.append(dict(zip(head, v)))
    return out, head


def read_tsv_rows(p):
    return read_tsv(p)[0]


def write_tsv(p, cols, rows):
    out = ['\t'.join(cols)]
    for r in rows:
        vals = []
        for c in cols:
            v = str(r.get(c, ''))
            if '\t' in v or '\n' in v:
                die(f'{p.name}: 値にタブか改行があります: {c}={v!r}')
            vals.append(v)
        out.append('\t'.join(vals))
    p.write_text('\n'.join(out) + '\n', encoding='utf-8')


# ---------------------------------------------------------------- 流れの表

def kessan_bills(c, nendo):
    """9月の会議の gian.json で kind が決算の議案（決算の議第と、健全化判断比率・資金不足比率の報第）。"""
    sep = NENDO[nendo][0]
    return [a['no'] for a in c.gian[sep]['agenda'] if a['kind'] == '決算']


def gi_bills(c, nendo):
    return [b for b in kessan_bills(c, nendo) if b.startswith('議第')]


def join_bills(bills, order):
    return '・'.join(b for b in order if b in set(bills))


def first_day(c, mid):
    ss = c.by_meeting[mid]
    d0 = min(s['date'] for s in ss)
    return [s for s in ss if s['date'] == d0]


def cue_stages(c, mid):
    """場面の無い会議のために、議長の指名の文と発言者の役職で、提案の説明・決算の説明・監査委員の審査報告の範囲を決める。

    9月の会議の初日の発言を順に見る。
      提案の説明：「会計管理者の説明を求め」の議長の発言の前で、最後の「提案理由の説明を求め」の議長の発言の次の発言
      決算の説明：「会計管理者の説明を求め」の議長の発言の次の発言から、「決算審査の報告を求め」の議長の発言の前の、議長でない最後の発言まで
      監査委員の審査報告：「決算審査の報告を求め」の議長の発言の次の、役職に「監査委員」を含む発言から、その役職の続く発言まで
    """
    ss = first_day(c, mid)
    idx = {k: None for k in ('teian_req', 'kaikei_req', 'kansa_req')}
    for i, s in enumerate(ss):
        if s['role'] not in CHAIR:
            continue
        t = s['text'].replace('\n', '')
        if '会計管理者の説明を求め' in t and idx['kaikei_req'] is None:
            idx['kaikei_req'] = i
        if '決算審査の報告を求め' in t and idx['kansa_req'] is None:
            idx['kansa_req'] = i
    if idx['kaikei_req'] is None or idx['kansa_req'] is None:
        return None
    for i, s in enumerate(ss[:idx['kaikei_req']]):
        if s['role'] in CHAIR and '提案理由の説明を求め' in s['text'].replace('\n', ''):
            idx['teian_req'] = i
    if idx['teian_req'] is None:
        return None
    # 提案の説明：指名の次の、議長でない発言（いくつか続けば最後まで）
    out = {}
    j = idx['teian_req'] + 1
    while j < len(ss) and ss[j]['role'] in CHAIR:
        j += 1
    k = j
    while k + 1 < idx['kaikei_req'] and ss[k + 1]['role'] == ss[j]['role']:
        k += 1
    out['teian'] = (ss[j], ss[k], idx['teian_req'])
    # 決算の説明
    j = idx['kaikei_req'] + 1
    while ss[j]['role'] in CHAIR:
        j += 1
    k = idx['kansa_req'] - 1
    while ss[k]['role'] in CHAIR:
        k -= 1
    out['setsumei'] = (ss[j], ss[k], idx['kaikei_req'])
    # 監査委員の審査報告
    j = idx['kansa_req'] + 1
    while j < len(ss) and '監査委員' not in ss[j]['role']:
        if ss[j]['role'] not in CHAIR:
            return None
        j += 1
    if j >= len(ss):
        return None
    k = j
    while k + 1 < len(ss) and (ss[k + 1]['role'] == ss[j]['role']):
        k += 1
    out['kansa'] = (ss[j], ss[k], idx['kansa_req'])
    return out


def proc_stages(c, mid, bills):
    """proceedings.json の提案の説明の場面から、同じ3つの段階を取る。場面が無ければ None。"""
    props = [s for s in c.segs(mid) if s['kind'] == 'proposal' and set(s.get('bills', [])) & set(bills)]
    if not props:
        return None
    def sp(sid):
        return c.speech[sid]
    teian = [p for p in props if p.get('role') in ('町長', '副町長')]
    kansa = [p for p in props if '監査委員' in (p.get('role') or '')]
    mid_ = [p for p in props if p not in teian and p not in kansa]
    if not teian or not kansa or not mid_:
        return None
    return {
        'teian': (sp(teian[0]['from']), sp(teian[-1]['to']), None),
        'setsumei': (sp(mid_[0]['from']), sp(mid_[-1]['to']), None),
        'kansa': (sp(kansa[0]['from']), sp(kansa[-1]['to']), None),
    }


def build_nagare(c, log):
    rows = []
    agree = []
    for nendo, (sep, dec) in NENDO.items():
        doc = f'kessan-r{nendo}-ikensho'
        allb = kessan_bills(c, nendo)
        gib = gi_bills(c, nendo)
        if not gib:
            die(f'令和{nendo}年度：9月の会議 {sep} の gian.json に決算の議案がありません')
        order = allb

        def row(dankai, s_from, s_to, gian, note, n=1, kekka='', hoho=''):
            return {'nendo': str(2018 + nendo), 'doc': doc, 'dankai': dankai, 'n': str(n),
                    'meeting': s_from['meetingId'], 'date': s_from['date'], 'sid_from': s_from['sid'],
                    'sid_to': s_to['sid'], 'gian': gian, 'kekka': kekka, 'hoho': hoho,
                    'status': 'candidate', 'reviewer': '', 'date_kakunin': '', 'note': note}

        # 提案の説明・決算の説明・監査委員の審査報告
        ps = proc_stages(c, sep, allb)
        cs = cue_stages(c, sep)
        if ps and cs:
            same = all(ps[k][0]['sid'] == cs[k][0]['sid'] and ps[k][1]['sid'] == cs[k][1]['sid'] for k in ps)
            agree.append((nendo, same))
        if ps:
            for k in ('teian', 'setsumei', 'kansa'):
                a, b, _ = ps[k]
                rows.append(row(k, a, b, join_bills(allb, order), 'proceedings.json の提案の説明の場面（kind proposal）から'))
        elif cs:
            for k in ('teian', 'setsumei', 'kansa'):
                a, b, req = cs[k]
                chair = first_day(c, sep)[req]['sid']
                how = {'teian': '「提案理由の説明を求め」', 'setsumei': '「会計管理者の説明を求め」',
                       'kansa': '「決算審査の報告を求め」'}[k]
                rest = {'teian': 'の次の発言（' + a['role'] + '）',
                        'setsumei': 'の次の発言から、監査委員の報告を求める議長の発言の前の、議長でない最後の発言（' + b['role'] + '）まで',
                        'kansa': 'の次の、役職に「監査委員」を含む発言（' + a['role'] + '）'}[k]
                rows.append(row(k, a, b, join_bills(allb, order),
                                f'proceedings.json に場面が無い。議長の{how}の発言（{chair}）{rest}とした。'
                                '議案は会議の決算の議案のすべてとした'))
        else:
            die(f'令和{nendo}年度：提案の説明・決算の説明・監査委員の審査報告の範囲を決められません')

        # 質疑
        sh = [s for s in c.segs(sep) if s['kind'] == 'shitsugi' and set(s.get('bills', [])) & set(allb)]
        if not sh:
            die(f'令和{nendo}年度：質疑の場面がありません')
        a = c.speech[min(s['from'] for s in sh)]
        b = c.speech[max(s['to'] for s in sh)]
        qb = [x for s in sh for x in s['bills']]
        rows.append(row('shitsugi', a, b, join_bills(qb, order),
                        f'proceedings.json の質疑の場面のうち、決算の議案を含む{len(sh)}場面の最初から最後まで'
                        '（間にほかの議案だけの場面を含む）'))

        # 委員会への付託
        ss = c.by_meeting[sep]
        endq = c.pos[sep][b['sid']]
        fut = None
        for i in range(endq + 1, len(ss)):
            s = ss[i]
            t = s['text'].replace('\n', '')
            if s['role'] in CHAIR and '付託' in t and ('決算特別委員会' in t or '付託表' in t):
                fut = i
                break
        if fut is None or fut + 1 >= len(ss) or ss[fut + 1]['role'] not in CHAIR:
            die(f'令和{nendo}年度：委員会への付託の議長の発言を見つけられません')
        t = ss[fut]['text'].replace('\n', '')
        if '付託表' in t:
            how = '「付託表により…付託」の議長の発言と、次の議長の発言（決定）。付託表の中身は会議録に無いので、議案は決算の議第のすべてとした'
        else:
            how = '「決算特別委員会を設置し、これに付託」の議長の発言と、次の議長の発言（決定）。議案は決算の議第のすべてとした'
        rows.append(row('futaku', ss[fut], ss[fut + 1], join_bills(gib, order), 'proceedings.json に場面が無い。' + how))

        # 委員長報告
        rep = [s for s in c.segs(dec) if s['kind'] == 'report' and set(s.get('bills', [])) & set(gib)]
        if len(rep) != 1:
            die(f'令和{nendo}年度：12月の会議の決算の委員長報告の場面が {len(rep)} 件')
        r = rep[0]
        miss = [x for x in gib if x not in r['bills']]
        note = f"proceedings.json の委員長報告の場面（{r.get('committee', '')}）"
        if miss:
            note += '。場面の議案に ' + '・'.join(miss) + ' が無い（議長の発言は議第のすべてを一括議題としている）'
        rows.append(row('hokoku', c.speech[r['from']], c.speech[r['to']], join_bills(r['bills'], order), note))

        # 討論
        deb = [s for s in c.segs(dec) if s['kind'] == 'debate' and set(s.get('bills', [])) & set(gib)]
        if deb:
            a = c.speech[min(s['from'] for s in deb)]
            b = c.speech[max(s['to'] for s in deb)]
            st = '・'.join(f"{s['member']}（{s.get('stance', '')}）" for s in deb)
            rows.append(row('toron', a, b, join_bills([x for s in deb for x in s['bills']], order),
                            f'proceedings.json の討論の場面 {len(deb)} 件（{st}）の最初から最後まで'))
        else:
            ds = c.by_meeting[dec]
            i0 = c.pos[dec][r['to']]
            a = b = None
            for i in range(i0 + 1, len(ds)):
                t = ds[i]['text'].replace('\n', '')
                if ds[i]['role'] not in CHAIR:
                    break
                if a is None and '討論に入ります' in t:
                    a = ds[i]
                if a is not None and '討論を終わります' in t:
                    b = ds[i]
                    break
            if a is None or b is None:
                die(f'令和{nendo}年度：討論の範囲を決められません')
            rows.append(row('toron', a, b, '', '討論の発言は無い。proceedings.json に場面が無いので、議長の「討論に入ります」の発言から'
                                              '「討論を終わります」の発言までとした'))

        # 採決
        votes = [s for s in c.segs(dec) if s['kind'] == 'vote' and set(s.get('bills', [])) & set(gib)]
        if not votes:
            die(f'令和{nendo}年度：採決の場面がありません')
        got = set()
        for i, v in enumerate(votes, 1):
            sp = c.speech[v['sid']]
            got |= set(v['bills'])
            rows.append(row('saiketsu', sp, sp, join_bills(v['bills'], order),
                            'proceedings.json の採決の場面' + (f"（{v['basis']}）" if v.get('basis') else ''),
                            n=i, kekka=v.get('result') or '', hoho=v.get('method') or ''))
        miss = [x for x in gib if x not in got]
        if miss:
            die(f'令和{nendo}年度：採決の場面に無い決算の議案: {miss}')
        # gian.json の結果と同じか
        for x in gib:
            g = [a for a in c.gian[sep]['agenda'] if a['no'] == x][0]
            v = [v for v in votes if x in v['bills']][0]
            if g.get('result') != v.get('result') or g.get('method') != v.get('method') or g.get('decidedIn') != dec:
                die(f'令和{nendo}年度 {x}：gian.json の結果（{g.get("result")}・{g.get("method")}・{g.get("decidedIn")}）'
                    f'と採決の場面（{v.get("result")}・{v.get("method")}・{dec}）が違います')
    log['agree'] = agree
    return rows


# ---------------------------------------------------------------- 意見書を踏まえた質疑のやりとり

def konkyo_cut(t, a, b):
    s = t[a:b]
    return s if len(s) <= KONKYO_MAX else ''


def find_refs(t):
    """発言の字から、意見の番号（丸数字）と印刷のページを拾う。

    「意見書」「監査委員」などの根拠の字の後ろ WINDOW 字（別の資料の名前が出たらそこまで）の中の、
    丸数字と「Nページ」を拾う。同じ値が2回以上あれば、根拠の字に最も近いものを取る。
    根拠の字の後ろに無い丸数字も、離れた丸数字（bango_far）として返す。
    返り値: anchors（根拠の字の (始め, 終わり, 字)）, refs（(種類, 値, 字の位置, 根拠, 根拠からの距離, 字の終わり)）
    """
    anchors = [(m.start(), m.end(), m.group(0)) for m in ANCHOR.finditer(t)]
    best = {}
    for a, e, g in anchors:
        w = t[e:e + WINDOW]
        m = OTHER_DOC.search(w)
        if m:
            w = w[:m.start()]
        for m in PAGE.finditer(w):
            pos = e + m.start()
            page = int(m.group(1).translate(ZEN))
            ia = g.find('意見書')
            st = a + ia if ia >= 0 else a
            k = konkyo_cut(t, st, e + m.end()) or m.group(0)
            cur = ('page', page, pos, k, pos - e, e + m.end())
            if ('page', page) not in best or cur[4] < best[('page', page)][4]:
                best[('page', page)] = cur
        for m in re.finditer('[' + MARU + ']', w):
            pos = e + m.start()
            cur = ('bango', m.group(0), pos, m.group(0), pos - e, pos + 1)
            if ('bango', m.group(0)) not in best or cur[4] < best[('bango', m.group(0))][4]:
                best[('bango', m.group(0))] = cur
    refs = list(best.values())
    # 根拠の字の後ろに無い丸数字
    for m in re.finditer('[' + MARU + ']', t):
        if ('bango', m.group(0)) in best or any(r[0] == 'bango_far' and r[1] == m.group(0) for r in refs):
            continue
        d = min((abs(m.start() - x) for x, _, _ in anchors), default=None)
        refs.append(('bango_far', m.group(0), m.start(), m.group(0), d, m.start() + 1))
    refs.sort(key=lambda r: r[2])
    return anchors, refs


QUOTE = re.compile(r'「([^「」]{6,})」')
QUOTE_LEN = 10


def norm(x):
    return re.sub(r'[\s、。，．,.・「」]', '', x)


def quotes_after(t, start, stop):
    """start から stop までの字の中の「」の中の字（区切りの字を除いた最初の QUOTE_LEN 字）と、その位置。"""
    out = []
    for m in QUOTE.finditer(t, start, stop):
        q = norm(m.group(1))[:QUOTE_LEN]
        if len(q) >= 6:
            out.append((q, m.start(), m.group(1)))
    return out


def doubts(t, anchors, ctx=''):
    """候補が決算審査の意見を引いているか迷う理由（無ければ空のリスト）。ctx は答える相手の質疑の字。"""
    out = []
    kinds = []
    for a, e, g in anchors:
        if '意見書' in g or '審査意見' in g:
            kinds.append('ikensho')
        elif g.startswith('監査委員'):
            kinds.append('hito' if HITO.match(t, a) or HITO.search(t[max(0, a - 6):e + 8]) else 'kansa')
        else:
            kinds.append('kansa')
    if kinds and all(k == 'hito' for k in kinds):
        out.append('迷う：「監査委員」が人や役を指す言い方だけ')
    if 'ikensho' in kinds and not KESSAN_IKENSHO.search(t) and not KESSAN_IKENSHO.search(ctx) \
            and not any(k == 'kansa' for k in kinds):
        out.append('迷う：「意見書」の前後に決算・監査委員の字が無い（別の意見書の可能性）')
    return out


def ledger_parts(c, mid, sid):
    """議案質疑の台帳（proceedings.json の parts）で、その発言が入る (区切り, 部分, 位置, 種類)。"""
    out = []
    for s in c.segs(mid):
        if s['kind'] != 'shitsugi' or not (s['from'] <= sid <= s['to']):
            continue
        base = c.pos[mid][s['from']]
        rel = c.pos[mid][sid] - base
        for p in s.get('parts', []):
            for tr in p['turns']:
                if tr[0] == rel:
                    out.append((s, p, rel, 'q'))
            if rel in p.get('answers', []):
                out.append((s, p, rel, 'a'))
    return out


def yaritori_of(c, mid, a, b):
    """質疑の範囲を、議員の発言（質問）と、その直後に続く答弁者の発言（次の議員の発言の前まで。議長の発言を除く）
    の組に分ける。"""
    out = []
    for s in c.by_meeting[mid]:
        if not (a <= s['sid'] <= b) or s['role'] in CHAIR:
            continue
        if GIIN.fullmatch(s['role']):
            out.append([s, []])
        elif out:
            out[-1][1].append(s)
    return out


def is_hito_only(t, anchors):
    return bool(anchors) and all(g.startswith('監査委員') and (HITO.match(t, a) or HITO.search(t[max(0, a - 6):e + 8]))
                                 for a, e, g in anchors)


def place_rows(c, ik, nendo, who, sid, t, refs, dbt):
    """1つの発言の番号とページを、意見書の箇所の行（hikikata・kyoshutsu・konkyo・insatsu_page・iken・basho・notes）にする。"""
    out = []
    bango_rows = {}
    for kind, val, pos, k, dist, end in refs:
        if kind not in ('bango', 'bango_far'):
            continue
        key = ik.ippan_bango(nendo, val)
        note = list(dbt)
        if kind == 'bango_far':
            note.append(f'迷う：丸数字が「意見書」「監査」の字の後ろに無い（最も近い字から{dist}字）' if dist is not None
                        else '迷う：丸数字があるが「意見書」「監査」の字が無い')
        elif dist > NEAR:
            note.append(f'迷う：丸数字が「意見書」「監査」の字から{dist}字離れている')
        ins = ''
        if key:
            r = ik.rows[key]
            ins = str(r['ins_from'])
            if r['ins_from'] != r['ins_to']:
                note.append(f"意見の行は印刷のページ {r['ins_from']}〜{r['ins_to']} にまたがる")
        else:
            note.append(f'迷う：一般会計のまとめに番号 {val} の意見が無い')
        o = {'hikikata': 'bango', 'kyoshutsu': who, 'konkyo': k, 'insatsu_page': ins, 'iken': key,
             'basho': 'iken', 'notes': note, 'pos': pos, 'sid': sid}
        out.append(o)
        if key:
            bango_rows[key] = o
    pages = [r for r in refs if r[0] == 'page']
    for i, (kind, val, pos, k, dist, end) in enumerate(pages):
        keys = ik.on_page(nendo, val)
        hit = [bk for bk in bango_rows if bk in keys]
        if hit:
            bango_rows[hit[0]]['notes'].append(f'印刷のページ {val}（{k}）も同じ意見の行にかかる')
            continue
        note = list(dbt)
        if dist > NEAR:
            note.append(f'迷う：ページの字が「意見書」「監査」の字から{dist}字離れている')
        base = {'hikikata': 'page', 'kyoshutsu': who, 'konkyo': k, 'insatsu_page': str(val), 'pos': pos, 'sid': sid}
        if len(keys) == 1:
            out.append({**base, 'iken': keys[0], 'basho': 'iken', 'notes': note})
            continue
        if not keys:
            m = ik.midashi(nendo, val)
            note.append(('見出し：' + m) if m else '見出しの字を読めない')
            out.append({**base, 'iken': '', 'basho': 'hyo', 'notes': note})
            continue
        stop = min([p[2] for p in pages[i + 1:]] + [end + WINDOW])
        found = []
        for q, qpos, raw in quotes_after(t, end, stop):
            hits = [key for key in keys if q in ik.row_text(key)]
            if len(hits) == 1 and hits[0] not in [f[0] for f in found]:
                found.append((hits[0], q, qpos, raw))
        if not found:
            note.append(f'迷う：印刷のページ {val} にかかる意見の行が{len(keys)}行ある（' + '・'.join(keys) + '）')
            out.append({**base, 'iken': '', 'basho': 'iken', 'notes': note})
            continue
        for j, (key, q, qpos, raw) in enumerate(found):
            kk = k if j == 0 else (raw[:KONKYO_MAX] if raw[:KONKYO_MAX] in t else q)
            out.append({**base, 'konkyo': kk, 'iken': key, 'basho': 'iken', 'pos': pos if j == 0 else qpos,
                        'notes': note + [f'印刷のページ {val} にかかる意見の行{len(keys)}行のうち、'
                                         f'ページの字の後ろの「」の最初の{len(q)}字が意見の字にある行']})
    return out


def build_yaritori(c, ik, nagare, log):
    rows = []
    excluded = []
    stats = {'kw_chair': 0}
    for nendo, (sep, dec) in NENDO.items():
        doc = f'kessan-r{nendo}-ikensho'
        allb = set(kessan_bills(c, nendo))
        for r in nagare:
            if r['nendo'] != str(2018 + nendo) or r['dankai'] not in DANKAI_YARITORI:
                continue
            mid, a, b = r['meeting'], r['sid_from'], r['sid_to']
            stats['kw_chair'] += sum(1 for s in c.by_meeting[mid] if a <= s['sid'] <= b and s['role'] in CHAIR
                                     and KW.search(s['text'].replace('\n', '')))
            if r['dankai'] == 'shitsugi':
                groups = yaritori_of(c, mid, a, b)
            else:
                groups = [[s, []] for s in c.by_meeting[mid] if a <= s['sid'] <= b and s['role'] not in CHAIR]
            for q, ans in groups:
                speakers = [(q, 'q')] + [(x, 'a') for x in ans]
                kw = [(sp, who) for sp, who in speakers if KW.search(sp['text'].replace('\n', ''))]
                if not kw:
                    continue
                qtext = c.text(q['sid'])
                places, go_cands, hito = [], [], []
                other_doubt = False
                for sp, who in kw:
                    t = c.text(sp['sid'])
                    anchors, refs = find_refs(t)
                    if is_hito_only(t, anchors) and not refs:
                        hito.append(sp['sid'])
                        continue
                    dbt = [d for d in doubts(t, anchors, ctx=qtext if who == 'a' else '')
                           if '人や役' not in d]
                    dbt = ['迷う：別の意見書か（「意見書」の前後に決算・監査委員の字が無い）' if '別の意見書' in d else d
                           for d in dbt]
                    if dbt:
                        other_doubt = True
                    ps = place_rows(c, ik, nendo, who, sp['sid'], t, refs, dbt)
                    places += ps
                    if not ps:
                        a0 = next((x for x in anchors if '意見書' in x[2]), None) or next(
                            (x for x in anchors if not (x[2].startswith('監査委員') and HITO.search(t[max(0, x[0] - 6):x[1] + 8]))),
                            anchors[0] if anchors else None)
                        k = a0[2][-KONKYO_MAX:] if a0 else KW.search(t).group(0)
                        go_cands.append({'hikikata': 'go', 'kyoshutsu': who, 'konkyo': k, 'insatsu_page': '',
                                         'iken': '', 'basho': 'fumei', 'notes': list(dbt),
                                         'pos': a0[0] if a0 else 0, 'sid': sp['sid']})
                if not places and not go_cands:
                    for sid in hito:
                        excluded.append((sid, '「監査委員」が人や役を指す言い方だけで、意見書の箇所の字が無い'))
                    continue
                # 同じ箇所（同じ意見の行。意見の行が決まらないときは同じ印刷のページ）を2つ以上の発言が挙げていれば、
                # 先の行（質問の行が先）にまとめる
                merged = []
                for o in sorted(places, key=lambda o: (o['kyoshutsu'] != 'q', o['sid'], o['pos'])):
                    same = next((m for m in merged if (o['iken'] and m['iken'] == o['iken']) or
                                 (not o['iken'] and m['insatsu_page'] and m['insatsu_page'] == o['insatsu_page'])), None)
                    if same:
                        same['notes'].append(('答弁' if o['kyoshutsu'] == 'a' else '質問') +
                                             f"（{o['sid']}）も同じ箇所を挙げる（{o['konkyo']}）")
                        continue
                    merged.append(o)
                if not merged:
                    g = next((x for x in go_cands if x['kyoshutsu'] == 'q'), go_cands[0])
                    merged = [g]
                for o in merged:
                    notes = []
                    if r['dankai'] != 'shitsugi':
                        notes.append(f"段階：{DANKAI_JI[r['dankai']]}")
                    else:
                        lp = ledger_parts(c, mid, q['sid'])
                        lb = sorted({p['bill'] for _, p, _, _ in lp})
                        if lb and not (set(lb) & allb):
                            notes.append('質疑の台帳で決算の議案でない部分（' + '・'.join(lb) + '）の質問')
                    if o['kyoshutsu'] == 'a':
                        notes.append(f"答弁（{o['sid']}）が挙げた箇所")
                    for sid in hito:
                        notes.append(f'{sid} は「監査委員」が人を指す言い方だけ')
                    rows.append({
                        'nendo': str(2018 + nendo), 'doc': doc, 'sid_q': q['sid'],
                        'sid_a': ';'.join(x['sid'] for x in ans), 'role_q': q['role'],
                        'role_a': ';'.join(x['role'] for x in ans),
                        'hikikata': o['hikikata'], 'kyoshutsu': o['kyoshutsu'], 'konkyo': o['konkyo'],
                        'insatsu_page': o['insatsu_page'], 'iken': o['iken'], 'basho': o['basho'],
                        'status': 'candidate', 'reviewer': '', 'date_kakunin': '',
                        'note': '。'.join(dict.fromkeys(notes + o['notes'])),
                        '_pos': (0 if o['kyoshutsu'] == 'q' else 1, o['sid'], o['pos'])})
    rows.sort(key=lambda r: (r['nendo'], r['sid_q'], r.pop('_pos'), r['hikikata'], r['konkyo']))
    log.update(stats)
    log['excluded'] = excluded
    return rows


# ---------------------------------------------------------------- 人の印を保つ

def merge(new, old, key, tool_cols, label):
    """人の印と人が書いた値を保って、新しい候補と前の表を合わせる。

    - 前の表で status が confirmed・rejected の行は、そのまま残す（道具の値と違えば数えて表示する）
    - 前の表で candidate の行は、道具の行で置き換える。ただし道具の値が空の列に前の行の値があれば保つ（人が書いた値）
    - 道具が作らなくなった行は、confirmed・rejected なら残し、candidate なら消す
    """
    oldk = {tuple(r[k] for k in key): r for r in old}
    out, diff, kept_human, gone = [], [], 0, []
    newk = set()
    for r in new:
        k = tuple(r[c] for c in key)
        newk.add(k)
        o = oldk.get(k)
        if o and o['status'] in ('confirmed', 'rejected'):
            d = [c for c in tool_cols if o.get(c, '') != r.get(c, '') and not (r.get(c, '') == '' and o.get(c, ''))]
            if d:
                diff.append((k, d))
            out.append(o)
            continue
        if o:
            for c in tool_cols:
                if r.get(c, '') == '' and o.get(c, ''):
                    r[c] = o[c]
                    kept_human += 1
        out.append(r)
    for k, o in oldk.items():
        if k not in newk and o['status'] in ('confirmed', 'rejected'):
            out.append(o)
            gone.append(k)
    print(f'{label}: 人の印のある行 {sum(1 for r in out if r["status"] != "candidate")}、'
          f'候補の行で保った人の値 {kept_human}、道具の値と違う人の行 {len(diff)}、道具が作らなくなった人の行 {len(gone)}')
    for k, d in diff:
        print(f'  道具の値と違う: {k} {d}')
    for k in gone:
        print(f'  道具が作らなくなった: {k}')
    return out


# ---------------------------------------------------------------- 確かめる

SID = re.compile(r'^[0-9]{10}_[0-9]{8}_[0-9]{4}$')
DATE = re.compile(r'^[0-9]{4}-[0-9]{2}-[0-9]{2}$')


def check_common(rows, cols, head, key, label, errs):
    if head != cols:
        errs.append(f'{label}: 列が {head}（決まりは {cols}）')
        return
    seen = set()
    for r in rows:
        k = tuple(r[c] for c in key)
        if k in seen:
            errs.append(f'{label}: キーの重複 {k}')
        seen.add(k)
        st = r['status']
        if st not in STATUS:
            errs.append(f'{label} {k}: status が {st!r}')
        elif st == 'candidate':
            if r['reviewer'] or r['date_kakunin']:
                errs.append(f'{label} {k}: candidate なのに reviewer か date_kakunin がある')
        else:
            if not r['reviewer'] or not DATE.match(r['date_kakunin']):
                errs.append(f'{label} {k}: {st} なのに reviewer か date_kakunin（YYYY-MM-DD）が無い')
            if st == 'rejected' and not r['note']:
                errs.append(f'{label} {k}: rejected なのに note が空')


def check(c, ik, nagare, nh, yaritori, yh, errs):
    check_common(nagare, NAGARE_COLS, nh, NAGARE_KEY, 'kessan-nagare', errs)
    check_common(yaritori, YARITORI_COLS, yh, YARITORI_KEY, 'iken-yaritori', errs)
    if errs:
        return
    ranges = {}
    for r in nagare:
        k = (r['nendo'], r['dankai'], r['n'])
        if r['dankai'] not in DANKAI:
            errs.append(f'kessan-nagare {k}: dankai が {r["dankai"]!r}')
            continue
        nd = int(r['nendo']) - 2018
        if nd not in NENDO or r['doc'] != f'kessan-r{nd}-ikensho':
            errs.append(f'kessan-nagare {k}: nendo と doc が合わない')
            continue
        if r['meeting'] not in NENDO[nd]:
            errs.append(f'kessan-nagare {k}: 会議 {r["meeting"]} がその年度の9月・12月の会議でない')
        for col in ('sid_from', 'sid_to'):
            if not SID.match(r[col]) or r[col] not in c.speech:
                errs.append(f'kessan-nagare {k}: {col} {r[col]} が会議録に無い')
        if errs and errs[-1].startswith(f'kessan-nagare {k}'):
            continue
        a, b = c.speech[r['sid_from']], c.speech[r['sid_to']]
        if a['meetingId'] != r['meeting'] or b['meetingId'] != r['meeting']:
            errs.append(f'kessan-nagare {k}: sid の会議が meeting と違う')
        if r['sid_from'] > r['sid_to']:
            errs.append(f'kessan-nagare {k}: sid_from が sid_to より後')
        if a['date'] != r['date']:
            errs.append(f'kessan-nagare {k}: date {r["date"]} が sid_from の発言の日 {a["date"]} と違う')
        agenda = {x['no'] for x in c.gian.get(NENDO[nd][0], {}).get('agenda', [])}
        for g in [x for x in r['gian'].split('・') if x]:
            if g not in agenda:
                errs.append(f'kessan-nagare {k}: 議案 {g} が9月の会議の gian.json に無い')
        if r['dankai'] == 'saiketsu' and not r['kekka']:
            errs.append(f'kessan-nagare {k}: 採決の行の kekka が空')
        if r['dankai'] != 'saiketsu' and (r['kekka'] or r['hoho']):
            errs.append(f'kessan-nagare {k}: 採決でない行に kekka・hoho がある')
        if r['status'] != 'rejected':
            ranges.setdefault(r['nendo'], []).append((DANKAI.index(r['dankai']), int(r['n']), r['sid_from'], r['sid_to'], k))
    # 前後：段階の順に、範囲が重ならずに並ぶ
    for nendo, rs in ranges.items():
        rs.sort()
        for x, y in zip(rs, rs[1:]):
            if not x[3] < y[2]:
                errs.append(f'kessan-nagare: {x[4]} の範囲（〜{x[3]}）と {y[4]} の範囲（{y[2]}〜）の前後が正しくない')
    # 意見書を踏まえた質疑のやりとり
    rng = {}
    for r in nagare:
        if r['dankai'] in DANKAI_YARITORI and r['status'] != 'rejected':
            rng.setdefault(r['nendo'], []).append((r['dankai'], r['sid_from'], r['sid_to']))
    for r in yaritori:
        k = tuple(r[x] for x in YARITORI_KEY)
        if r['sid_q'] not in c.speech:
            errs.append(f'iken-yaritori {k}: sid_q が会議録に無い')
            continue
        q = c.speech[r['sid_q']]
        nd = int(r['nendo']) - 2018
        if nd not in NENDO or r['doc'] != f'kessan-r{nd}-ikensho':
            errs.append(f'iken-yaritori {k}: nendo と doc が合わない')
            continue
        if q['role'] != r['role_q']:
            errs.append(f'iken-yaritori {k}: role_q {r["role_q"]!r} が会議録の {q["role"]!r} と違う')
        dk = [d for d, a, b in rng.get(r['nendo'], []) if a <= r['sid_q'] <= b]
        if not dk:
            errs.append(f'iken-yaritori {k}: sid_q が流れの表のその年度の質疑・委員長報告・討論の範囲に無い')
            continue
        sa = [x for x in r['sid_a'].split(';') if x]
        ra = [x for x in r['role_a'].split(';') if x] if r['role_a'] else []
        if dk[0] == 'shitsugi':
            if not GIIN.fullmatch(q['role']):
                errs.append(f'iken-yaritori {k}: 質疑の sid_q が議員の発言でない')
            mid = q['meetingId']
            exp = []
            for s in c.by_meeting[mid][c.pos[mid][r['sid_q']] + 1:]:
                if s['role'] in CHAIR:
                    continue
                if GIIN.fullmatch(s['role']):
                    break
                exp.append(s['sid'])
            if sa != exp:
                errs.append(f'iken-yaritori {k}: sid_a が、質問の直後に続く答弁者の発言（{len(exp)}件）と違う')
        elif sa:
            errs.append(f'iken-yaritori {k}: 委員長報告・討論の行に sid_a がある')
        if len(ra) != len(sa) or any(x not in c.speech or c.speech[x]['role'] != y for x, y in zip(sa, ra)):
            errs.append(f'iken-yaritori {k}: role_a が sid_a の発言の役職と合わない')
        if r['hikikata'] not in HIKIKATA:
            errs.append(f'iken-yaritori {k}: hikikata が {r["hikikata"]!r}')
        if r['kyoshutsu'] not in KYOSHUTSU or (r['kyoshutsu'] == 'a' and not sa):
            errs.append(f'iken-yaritori {k}: kyoshutsu が {r["kyoshutsu"]!r}')
        if r['basho'] not in BASHO:
            errs.append(f'iken-yaritori {k}: basho が {r["basho"]!r}')
        if len(r['konkyo']) > KONKYO_MAX:
            errs.append(f'iken-yaritori {k}: konkyo が{KONKYO_MAX}字を超える')
        src = [r['sid_q']] if r['kyoshutsu'] == 'q' else [x for x in sa if x in c.speech]
        if not r['konkyo'] or not any(r['konkyo'] in c.text(x) for x in src):
            errs.append(f'iken-yaritori {k}: konkyo が、挙げた側の発言の字に無い')
        ins = r['insatsu_page']
        if r['hikikata'] == 'go':
            if ins or r['iken'] or r['basho'] != 'fumei':
                errs.append(f'iken-yaritori {k}: go の行に insatsu_page・iken があるか、basho が fumei でない')
        else:
            if r['basho'] == 'fumei':
                errs.append(f'iken-yaritori {k}: {r["hikikata"]} の行の basho が fumei')
            if r['hikikata'] == 'page':
                m = PAGE.search(r['konkyo'])
                if not ins or not m or int(m.group(1).translate(ZEN)) != int(ins):
                    if not (m is None and r['iken']):   # 2つめ以降の「」で当てた行は konkyo にページが無い
                        errs.append(f'iken-yaritori {k}: insatsu_page が konkyo のページと違う')
            if r['hikikata'] == 'bango' and r['iken'] and ins != str(ik.rows.get(r['iken'], {}).get('ins_from', '')):
                errs.append(f'iken-yaritori {k}: insatsu_page が意見の行の印刷のページと違う')
        if r['iken']:
            row = ik.rows.get(r['iken'])
            if row is None:
                errs.append(f'iken-yaritori {k}: iken {r["iken"]} が意見の表に無い')
            elif row['doc'] != r['doc']:
                errs.append(f'iken-yaritori {k}: iken {r["iken"]} がその年度の意見書でない')
            elif r['basho'] != 'iken':
                errs.append(f'iken-yaritori {k}: iken があるのに basho が iken でない')
            elif ins and not (row['ins_from'] <= int(ins) <= row['ins_to']):
                errs.append(f'iken-yaritori {k}: insatsu_page が意見の行の印刷のページ（{row["ins_from"]}〜{row["ins_to"]}）に無い')
            elif r['hikikata'] == 'bango' and (not row['bango'] or row['bango'] not in r['konkyo']):
                errs.append(f'iken-yaritori {k}: 番号 {row["bango"]} が konkyo に無い')
        if r['basho'] == 'hyo' and (r['iken'] or not ins or ik.on_page(nd, int(ins))):
            errs.append(f'iken-yaritori {k}: hyo の行のページに意見の行がかかるか、iken がある')


# ---------------------------------------------------------------- 材料の版

def git_head(p):
    try:
        return subprocess.run(['git', '-C', str(p), 'rev-parse', 'HEAD'], capture_output=True, text=True,
                              check=True).stdout.strip()
    except Exception:
        return ''


def inputs_now(docs, council, ik, c):
    out = []
    for repo, base, files in (('kken78/hino-town-docs', docs, ik.files), ('kken78/hino-council-search', council, c.files)):
        head = git_head(base)
        for rel, p in sorted(files.items()):
            out.append({'repo': repo, 'commit': head, 'path': rel, 'sha256': sha256(p)})
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--src', default=str(ROOT.parent), help='材料のリポジトリを置いたフォルダ（既定はこのリポジトリの親）')
    ap.add_argument('--council', default=None, help='hino-council-search の場所（既定は --src の下）')
    ap.add_argument('--check', action='store_true', help='表を書かずに確かめる')
    args = ap.parse_args(argv)
    src = pathlib.Path(args.src).resolve()
    docs = src / 'hino-town-docs'
    council = pathlib.Path(args.council).resolve() if args.council else src / 'hino-council-search'
    c = Council(council)
    ik = Iken(docs)

    # 令和7年度の決算：会議録にまだ無いことを確かめる
    r7 = [(mid, a['no']) for mid, g in c.gian.items() for a in g.get('agenda', [])
          if a.get('kind') == '決算' and '令和７年度日野町' in a.get('title', '')]
    print(f'令和7年度の決算の議案（gian.json）: {len(r7)} 件' + ('' if not r7 else f' {r7}'))

    errs = []
    if args.check:
        if not INPUTS.exists():
            die(f'{INPUTS} がありません')
        rec = json.loads(INPUTS.read_text(encoding='utf-8'))['inputs']
        now = {(x['repo'], x['path']): x['sha256'] for x in inputs_now(docs, council, ik, c)}
        for x in rec:
            got = now.get((x['repo'], x['path']))
            if got != x['sha256']:
                errs.append(f"材料の sha256 が inputs.json と違う: {x['repo']} {x['path']}")
        if set(now) != {(x['repo'], x['path']) for x in rec}:
            errs.append('読んだ材料のファイルが inputs.json の一覧と違う')
        nagare, nh = read_tsv(NAGARE)
        yaritori, yh = read_tsv(YARITORI)
        check(c, ik, nagare, nh, yaritori, yh, errs)
        if errs:
            for e in errs:
                print(e, file=sys.stderr)
            print(f'合わない {len(errs)} 件', file=sys.stderr)
            sys.exit(1)
        print(f'確かめた: 流れの表 {len(nagare)} 行、意見書を踏まえた質疑のやりとりの表 {len(yaritori)} 行。合わないもの 0 件')
        return

    log = {}
    nagare = build_nagare(c, log)
    for nendo, same in log['agree']:
        print(f'場面の無い会議のための決め方を、場面のある令和{nendo}年度で試した: '
              + ('proceedings.json の場面と同じ' if same else '違う'))
    if any(not s for _, s in log['agree']):
        die('場面の無い会議のための決め方が、場面のある年度で合いません')
    yaritori = build_yaritori(c, ik, nagare, log)
    print(f'候補を拾う字を含む議長の発言（候補にしない）: {log["kw_chair"]} 件')
    print(f'外した発言（表に入れない）: {len(log["excluded"])} 件')
    for sid, why in log['excluded']:
        print(f'  {sid}\t{why}')
    LINKS.mkdir(parents=True, exist_ok=True)
    old_n = read_tsv_rows(NAGARE) if NAGARE.exists() else []
    old_h = read_tsv_rows(YARITORI) if YARITORI.exists() else []
    nagare = merge(nagare, old_n, NAGARE_KEY, NAGARE_TOOL, 'kessan-nagare')
    yaritori = merge(yaritori, old_h, YARITORI_KEY, YARITORI_TOOL, 'iken-yaritori')
    nagare.sort(key=lambda r: (r['nendo'], DANKAI.index(r['dankai']), int(r['n'])))
    check(c, ik, nagare, NAGARE_COLS, yaritori, YARITORI_COLS, errs)
    if errs:
        for e in errs:
            print(e, file=sys.stderr)
        die(f'作った表が合いません（{len(errs)} 件）。書き出しません')
    write_tsv(NAGARE, NAGARE_COLS, nagare)
    write_tsv(YARITORI, YARITORI_COLS, yaritori)
    INPUTS.write_text(json.dumps({
        'note': 'tools/build_links.py が読んだ材料。画面に組み込むときに inputs.lock.json へ移す（DESIGN.md ADR-9）。',
        'inputs': inputs_now(docs, council, ik, c)}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'書いた: {NAGARE.relative_to(ROOT)} {len(nagare)} 行、{YARITORI.relative_to(ROOT)} {len(yaritori)} 行')


if __name__ == '__main__':
    main()
