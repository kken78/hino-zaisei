#!/usr/bin/env python3
"""tools/build_links.py の検査（標準ライブラリのみ。材料のリポジトリは使わない）。

  python3 tools/test_build_links.py
"""
import copy, pathlib, sys, tempfile, types, unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import build_links as bl  # noqa: E402


def sp(sid, role, text, date=None):
    mid, d, _ = sid.split('_')
    return {'sid': sid, 'meetingId': mid, 'role': role, 'text': text,
            'date': date or f'{d[:4]}-{d[4:6]}-{d[6:]}'}


class FakeCouncil:
    """check と cue_stages が使う形だけを持つ会議録。"""

    def __init__(self, speeches, gian=None):
        self.speech = {s['sid']: s for s in speeches}
        self.by_meeting = {}
        for s in speeches:
            self.by_meeting.setdefault(s['meetingId'], []).append(s)
        for v in self.by_meeting.values():
            v.sort(key=lambda s: s['sid'])
        self.pos = {m: {s['sid']: i for i, s in enumerate(v)} for m, v in self.by_meeting.items()}
        self.gian = gian or {}
        self.proc = {}

    def text(self, sid):
        return self.speech[sid]['text'].replace('\n', '')

    def segs(self, mid):
        return []


class TestFindRefs(unittest.TestCase):
    def test_page_and_bango(self):
        t = '決算審査意見書の９ページのまとめの②のほうに記載されています。'
        _, refs = bl.find_refs(t)
        kinds = {(r[0], r[1]) for r in refs}
        self.assertIn(('page', 9), kinds)
        self.assertIn(('bango', '②'), kinds)
        page = [r for r in refs if r[0] == 'page'][0]
        self.assertEqual(page[3], '意見書の９ページ')

    def test_other_doc_cuts_window(self):
        t = '決算審査意見書には書かれていないが、決算書の142ページに各基金の現在高がある。'
        _, refs = bl.find_refs(t)
        self.assertEqual([r for r in refs if r[0] == 'page'], [])

    def test_nearest_anchor_wins(self):
        t = '意見書について。' + 'あ' * 50 + 'まず、決算審査意見書の３ページの上の表を見て下さい。'
        _, refs = bl.find_refs(t)
        page = [r for r in refs if r[0] == 'page'][0]
        self.assertEqual(page[1], 3)
        self.assertLess(page[4], 5)

    def test_far_maru(self):
        t = '①として、道路の質疑です。' + 'い' * 30 + '監査委員さんのご指摘もある。'
        _, refs = bl.find_refs(t)
        self.assertEqual([(r[0], r[1]) for r in refs], [('bango_far', '①')])

    def test_page_after_next_sentence(self):
        t = '各会計の決算意見書の中で、11ページでございます。⑦のほうで、いわゆる６町クラウドのご指摘'
        _, refs = bl.find_refs(t)
        self.assertEqual({(r[0], r[1]) for r in refs}, {('page', 11), ('bango', '⑦')})


class TestDoubts(unittest.TestCase):
    def test_hito(self):
        t = '監査委員である西澤正治議員を除く全委員が出席しました。'
        a, _ = bl.find_refs(t)
        self.assertTrue(any('人や役' in d for d in bl.doubts(t, a)))

    def test_other_ikensho(self):
        t = '官製談合事件の再発防止等に係る意見書、私も手元に持っています。'
        a, _ = bl.find_refs(t)
        self.assertTrue(any('別の意見書' in d for d in bl.doubts(t, a)))

    def test_ctx_clears_doubt(self):
        t = '意見書に係る部分のご質問を頂いたところでございます。'
        a, _ = bl.find_refs(t)
        self.assertTrue(bl.doubts(t, a))
        self.assertFalse(bl.doubts(t, a, ctx='令和３年度日野町一般会計の決算の意見書についてお尋ねをいたします。'))

    def test_kessan_ikensho_ok(self):
        t = '決算審査意見書にもその旨が記されている。'
        a, _ = bl.find_refs(t)
        self.assertEqual(bl.doubts(t, a), [])


class TestPages(unittest.TestCase):
    def test_insatsu(self):
        ik = bl.Iken.__new__(bl.Iken)
        ik.rows = {
            'd/matome/ippan/1': {'doc': 'd', 'bubun': 'matome', 'kaikei': 'ippan', 'n': '1', 'bango': '',
                                 'page': '2', 'line_from': '3', 'line_to': '7'},
        }
        text = '表紙\n1\n\fまとめ\n意見の文\n2\n\f続きの文\n3\n'
        ik._pages('d', text)
        r = ik.rows['d/matome/ippan/1']
        self.assertEqual((r['ins_from'], r['ins_to']), (2, 3))

    def test_page_mismatch_stops(self):
        ik = bl.Iken.__new__(bl.Iken)
        ik.rows = {'k': {'key': 'k', 'doc': 'd', 'page': '1', 'line_from': '3', 'line_to': '3'}}
        with self.assertRaises(SystemExit):
            ik._pages('d', 'a\n1\n\fb\n2\n')


class TestCueStages(unittest.TestCase):
    def test_cues(self):
        m = '0000000001'
        ss = [
            sp(f'{m}_20220901_0001', '議長', '日程第３ 議第43号から日程第22 議第62号まで…町当局の提案理由の説明を求めます。副町長。'),
            sp(f'{m}_20220901_0002', '副町長', '提案議案の説明'),
            sp(f'{m}_20220901_0003', '議長', '続いて、会計管理者の説明を求めます。'),
            sp(f'{m}_20220901_0004', '会計管理者', '決算の説明'),
            sp(f'{m}_20220901_0005', '議長', '暫時休憩します。'),
            sp(f'{m}_20220901_0006', '産業建設主監', '水道事業会計決算'),
            sp(f'{m}_20220901_0007', '議長', '監査委員より決算審査の報告を求めます。'),
            sp(f'{m}_20220901_0008', '代表監査委員', '審査の結果'),
            sp(f'{m}_20220901_0009', '議長', '以上で監査委員の決算審査の報告を終わります。'),
        ]
        c = FakeCouncil(ss)
        st = bl.cue_stages(c, m)
        got = {k: (v[0]['sid'][-4:], v[1]['sid'][-4:]) for k, v in st.items()}
        self.assertEqual(got, {'teian': ('0002', '0002'), 'setsumei': ('0004', '0006'), 'kansa': ('0008', '0008')})

    def test_no_cue(self):
        m = '0000000001'
        c = FakeCouncil([sp(f'{m}_20220901_0001', '議長', '開会します。')])
        self.assertIsNone(bl.cue_stages(c, m))


def row(**kw):
    base = {c: '' for c in bl.YARITORI_COLS}
    base.update(status='candidate')
    base.update(kw)
    return base


class TestYaritoriOf(unittest.TestCase):
    def test_groups(self):
        m = '0000000006'
        ss = [
            sp(f'{m}_20250911_0001', '2番', '質問。意見書の３ページ'),
            sp(f'{m}_20250911_0002', '議長', '総務主監。'),
            sp(f'{m}_20250911_0003', '総務主監', '答弁'),
            sp(f'{m}_20250911_0004', '議長', '税務課長。'),
            sp(f'{m}_20250911_0005', '税務課長', '答弁'),
            sp(f'{m}_20250911_0006', '2番', '再質問'),
            sp(f'{m}_20250911_0007', '総務主監', '答弁'),
            sp(f'{m}_20250911_0008', '3番', '次の議員'),
        ]
        c = FakeCouncil(ss)
        g = bl.yaritori_of(c, m, ss[0]['sid'], ss[6]['sid'])
        got = [(q['sid'][-4:], [a['sid'][-4:] for a in ans]) for q, ans in g]
        self.assertEqual(got, [('0001', ['0003', '0005']), ('0006', ['0007'])])


class TestMidashi(unittest.TestCase):
    def test_midashi(self):
        ik = bl.Iken.__new__(bl.Iken)
        ik.rows = {}
        text = ('表紙\n1\n\f１．一般会計\n１．決算の概要\n93.6\n2\n\f２．歳入決算について\n本文\n3\n'
                '\f表の続き\n99.0\n4\n')
        ik._pages('kessan-r6-ikensho', text)
        self.assertEqual(ik.midashi(6, 2), '１．一般会計／１．決算の概要')
        self.assertEqual(ik.midashi(6, 3), '１．決算の概要／２．歳入決算について')  # 20字を超えるので章を除く
        self.assertEqual(ik.midashi(6, 4), '１．一般会計／２．歳入決算について')
        self.assertEqual(ik.midashi(6, 9), '')


class TestMerge(unittest.TestCase):
    def test_keep_human(self):
        key, tool = bl.YARITORI_KEY, bl.YARITORI_TOOL
        old = [
            row(sid_q='s1', kyoshutsu='q', hikikata='go', konkyo='意見書', iken='doc/matome/ippan/2', status='candidate'),
            row(sid_q='s2', kyoshutsu='a', hikikata='bango', konkyo='⑦', iken='doc/matome/ippan/8', status='confirmed',
                reviewer='kken78', date_kakunin='2026-11-13', note='確かめた'),
            row(sid_q='s3', kyoshutsu='q', hikikata='go', konkyo='監査委員', status='rejected', reviewer='kken78',
                date_kakunin='2026-11-13', note='人を指す'),
            row(sid_q='s4', kyoshutsu='q', hikikata='go', konkyo='意見書', status='candidate', note='古い候補'),
        ]
        new = [
            row(sid_q='s1', kyoshutsu='q', hikikata='go', konkyo='意見書', iken='', note='新しい注記'),
            row(sid_q='s2', kyoshutsu='a', hikikata='bango', konkyo='⑦', iken='doc/matome/ippan/8', note='道具の注記'),
            row(sid_q='s5', kyoshutsu='q', hikikata='page', konkyo='3ページ'),
        ]
        out = bl.merge(copy.deepcopy(new), old, key, tool, 'test')
        by = {r['sid_q']: r for r in out}
        self.assertEqual(by['s1']['iken'], 'doc/matome/ippan/2')   # 人が書いた値を保つ
        self.assertEqual(by['s1']['note'], '新しい注記')            # 候補の注記は作り直す
        self.assertEqual(by['s2']['note'], '確かめた')              # 人の印の行はそのまま
        self.assertEqual(by['s3']['status'], 'rejected')            # 道具が作らなくなった人の行も残す
        self.assertNotIn('s4', by)                                  # 道具が作らなくなった候補は消す
        self.assertIn('s5', by)

    def test_idempotent(self):
        new = [row(sid_q='s1', kyoshutsu='q', hikikata='go', konkyo='意見書')]
        once = bl.merge(copy.deepcopy(new), [], bl.YARITORI_KEY, bl.YARITORI_TOOL, 'a')
        twice = bl.merge(copy.deepcopy(new), once, bl.YARITORI_KEY, bl.YARITORI_TOOL, 'b')
        self.assertEqual(once, twice)


class TestCheck(unittest.TestCase):
    """正しい表で合わないものが0件になり、誤りを1つずつ入れると見つかることを確かめる。"""

    def setUp(self):
        self.saved = dict(bl.NENDO)
        bl.NENDO.clear()
        bl.NENDO[6] = ('0000000006', '0000000012')
        sep, dec = bl.NENDO[6]
        self.q = f'{sep}_20250911_0001'
        self.a1, self.a2 = f'{sep}_20250911_0003', f'{sep}_20250911_0004'
        ss = [
            sp(f'{sep}_20250901_0001', '代表監査委員', '審査の結果'),
            sp(self.q, '8番', '決算審査意見書の３ページの表と、⑦のほう'),
            sp(f'{sep}_20250911_0002', '議長', '厚生主監。'),
            sp(self.a1, '厚生主監', '監査委員さんの意見書の20ページの中段'),
            sp(self.a2, '総務主監', 'お答えします'),
            sp(f'{sep}_20250911_0005', '9番', '次の質問'),
            sp(f'{dec}_20251201_0001', '9番', '委員長報告。決算審査意見書'),
            sp(f'{dec}_20251201_0002', '議長', '起立多数であります。'),
        ]
        self.c = FakeCouncil(ss, gian={sep: {'agenda': [{'no': '議第68号', 'kind': '決算'}]}})
        self.ik = types.SimpleNamespace(rows={
            'kessan-r6-ikensho/matome/kaigo/1': {'doc': 'kessan-r6-ikensho', 'bango': '', 'ins_from': 20, 'ins_to': 20},
            'kessan-r6-ikensho/matome/ippan/8': {'doc': 'kessan-r6-ikensho', 'bango': '⑦', 'ins_from': 10, 'ins_to': 10},
        }, on_page=lambda nd, pg: [k for k, r in self.ik.rows.items() if r['ins_from'] <= pg <= r['ins_to']])

        def nr(dankai, n, mid, a, b, date, gian='議第68号', kekka='', hoho=''):
            r = {c: '' for c in bl.NAGARE_COLS}
            r.update(nendo='2024', doc='kessan-r6-ikensho', dankai=dankai, n=str(n), meeting=mid, date=date,
                     sid_from=a, sid_to=b, gian=gian, kekka=kekka, hoho=hoho, status='candidate')
            return r
        self.nagare = [
            nr('kansa', 1, sep, f'{sep}_20250901_0001', f'{sep}_20250901_0001', '2025-09-01'),
            nr('shitsugi', 1, sep, self.q, f'{sep}_20250911_0005', '2025-09-11'),
            nr('hokoku', 1, dec, f'{dec}_20251201_0001', f'{dec}_20251201_0001', '2025-12-01'),
            nr('saiketsu', 1, dec, f'{dec}_20251201_0002', f'{dec}_20251201_0002', '2025-12-01', kekka='認定', hoho='起立多数'),
        ]
        common = dict(nendo='2024', doc='kessan-r6-ikensho', sid_q=self.q, sid_a=f'{self.a1};{self.a2}',
                      role_q='8番', role_a='厚生主監;総務主監')
        self.yaritori = [
            row(**common, hikikata='page', kyoshutsu='q', konkyo='意見書の３ページ', insatsu_page='3', basho='hyo'),
            row(**common, hikikata='bango', kyoshutsu='q', konkyo='⑦', insatsu_page='10',
                iken='kessan-r6-ikensho/matome/ippan/8', basho='iken'),
            row(**common, hikikata='page', kyoshutsu='a', konkyo='意見書の20ページ', insatsu_page='20',
                iken='kessan-r6-ikensho/matome/kaigo/1', basho='iken'),
            row(nendo='2024', doc='kessan-r6-ikensho', sid_q=f'{dec}_20251201_0001', role_q='9番', hikikata='go',
                kyoshutsu='q', konkyo='決算審査意見書', basho='fumei', note='段階：委員長報告'),
        ]

    def tearDown(self):
        bl.NENDO.clear()
        bl.NENDO.update(self.saved)

    def run_check(self, nagare=None, yaritori=None):
        errs = []
        bl.check(self.c, self.ik, nagare or self.nagare, bl.NAGARE_COLS, yaritori or self.yaritori,
                 bl.YARITORI_COLS, errs)
        return errs

    def test_ok(self):
        self.assertEqual(self.run_check(), [])

    def bad_n(self, i, **kw):
        n = copy.deepcopy(self.nagare)
        n[i].update(kw)
        return self.run_check(nagare=n)

    def bad_y(self, i, **kw):
        y = copy.deepcopy(self.yaritori)
        y[i].update(kw)
        return self.run_check(yaritori=y)

    def test_errors(self):
        sep = bl.NENDO[6][0]
        cases = {
            'sid が会議録に無い': self.bad_n(1, sid_to=f'{sep}_20250911_0009'),
            '前後（from が to より後）': self.bad_n(1, sid_from=f'{sep}_20250911_0005', sid_to=self.q),
            '段階の前後': self.bad_n(0, dankai='hokoku'),
            'date': self.bad_n(1, date='2025-09-12'),
            '議案': self.bad_n(1, gian='議第99号'),
            '採決の kekka': self.bad_n(3, kekka=''),
            'status': self.bad_n(0, status='ok'),
            'confirmed の reviewer': self.bad_n(0, status='confirmed'),
            'sid_q が会議録に無い': self.bad_y(0, sid_q=f'{sep}_20250911_0009'),
            '範囲の外': self.bad_y(0, sid_q=f'{sep}_20250901_0001', role_q='代表監査委員'),
            'role_q': self.bad_y(0, role_q='7番'),
            'sid_a の抜け': self.bad_y(0, sid_a=self.a1, role_a='厚生主監'),
            'role_a': self.bad_y(0, role_a='総務主監;厚生主監'),
            '委員長報告の sid_a': self.bad_y(3, sid_a=self.a1, role_a='厚生主監'),
            'iken のキー': self.bad_y(1, iken='kessan-r6-ikensho/matome/kaigo/9'),
            'doc の年度': self.bad_y(1, doc='kessan-r5-ikensho'),
            'konkyo が発言に無い': self.bad_y(0, konkyo='意見書の21ページ'),
            '挙げた側が違う': self.bad_y(2, kyoshutsu='q'),
            'insatsu_page とページ': self.bad_y(0, insatsu_page='4'),
            'ページが行にかからない': self.bad_y(2, iken='kessan-r6-ikensho/matome/ippan/8'),
            '番号の insatsu_page': self.bad_y(1, insatsu_page='11'),
            '番号が konkyo に無い': self.bad_y(1, iken='kessan-r6-ikensho/matome/kaigo/1', insatsu_page='20'),
            'hyo に意見の行': self.bad_y(2, basho='hyo', iken=''),
            'iken で basho が hyo': self.bad_y(1, basho='hyo'),
            'go の basho': self.bad_y(3, basho='hyo'),
            'hikikata': self.bad_y(3, hikikata='x'),
            'kyoshutsu': self.bad_y(3, kyoshutsu='a'),
            'rejected の note': self.bad_y(0, status='rejected', reviewer='kken78', date_kakunin='2026-11-13'),
            'キーの重複': self.run_check(yaritori=self.yaritori + [copy.deepcopy(self.yaritori[0])]),
        }
        for name, errs in cases.items():
            with self.subTest(name):
                self.assertTrue(errs, name)


class TestTsv(unittest.TestCase):
    def test_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            p = pathlib.Path(d) / 'a.tsv'
            rows = [row(sid_q='s1', kyoshutsu='q', hikikata='go', konkyo='意見書')]
            bl.write_tsv(p, bl.YARITORI_COLS, rows)
            got, head = bl.read_tsv(p)
            self.assertEqual(head, bl.YARITORI_COLS)
            self.assertEqual(got, rows)

    def test_tab_in_value_stops(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(SystemExit):
                bl.write_tsv(pathlib.Path(d) / 'a.tsv', ['a'], [{'a': 'x\ty'}])


if __name__ == '__main__':
    unittest.main(verbosity=1)
