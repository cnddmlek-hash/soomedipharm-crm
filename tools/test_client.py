#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
클라이언트(index.html) 정적 검사 + 순수 함수 실행 검사
--------------------------------------------------------------------
1) 스크립트 문법(esprima)
2) v1.4 필수 요소(버전·메뉴·회원가입 예시·신규 함수) 확인
3) onclick 등에서 부르는 함수가 실제로 정의되어 있는지 확인
4) 화면이 runServer('함수명')으로 부르는 서버 함수가 Code.gs 공개 목록에 있는지 확인
5) Date/STATE 만 있으면 도는 순수 함수(생일 D-day 등)는 QuickJS 로 실제 실행

사용: python3 tools/test_client.py
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(HERE)
INDEX = os.path.join(PROJECT, 'index.html')
CODEGS = os.path.abspath(os.path.join(PROJECT, '..', '..', 'downloads', 'Code.gs'))

fails = []
checks = 0


def check(cond, label):
    global checks
    checks += 1
    if not cond:
        fails.append(label)



def extract_fn(js, name):
    """`   function name(...) { ... }` 블록을 중괄호 깊이로 잘라 냅니다 (QuickJS 실행용)."""
    m = re.search(r'\n   (?:async )?function %s\(' % re.escape(name), js)
    if not m:
        return None
    start = m.start() + 1
    i = js.index('{', m.start())
    depth = 0
    while i < len(js):
        ch = js[i]
        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                return js[start:i + 1]
        i += 1
    return None


def extract_maker_map(js):
    """index.html 의 /* MAKER_MAP_START */ … /* MAKER_MAP_END */ 안의 선언을 그대로 꺼냅니다."""
    m = re.search(r'/\* MAKER_MAP_START \*/\n(.*?)\n\s*/\* MAKER_MAP_END \*/', js, re.S)
    return m.group(1) if m else None


def load_maker_ctx(ctx, js):
    """makerOf_ 가 쓰는 '예전 자사 표기 판정 + 앱 내장 제약사 목록' 을 실행 문맥에 넣습니다."""
    block = extract_maker_map(js)
    if not block:
        return False
    ctx.eval("const LEGACY_MAKER_LABELS = ['자사(휴온스·페이서)', '자사(페이서)', '자사'];")
    ctx.eval("const DISTRIBUTOR_LABEL = '페이서써플라이(주)';")
    ctx.eval(block)
    for name in ['isLegacyMakerLabel_', 'builtinMakerOf_']:
        fn = extract_fn(js, name)
        if fn is None:
            return False
        ctx.eval(fn)
    return True



ING_FUNCS = ['ingKoSyl_', 'ingKoAscii_', 'ingKoIsVowelAt_', 'ingKoTranslit_', 'ingKoKey_', 'ingKoWord_',
             'ingKoBaseToken_', 'ingKoTokenKo_', 'ingKoOf_', 'ingLabel_', 'ingText_']
ING_CONSTS = ['ING_KO_SALT_', 'ING_KO_FORM_', 'ING_KO_ONSET_', 'ING_KO_CODA_', 'ING_KO_VOWELS_',
              'ING_KO_O_IDX_', 'ING_KO_V_IDX_', 'ING_KO_C_IDX_']


def load_ing_ctx(ctx, js):
    """v1.22 — 영문 성분명 → 한글 발음 병기(사전·음차 함수)를 QuickJS 문맥에 넣습니다."""
    m = re.search(r'/\* ING_KO_START \*/\n(.*?)\n\s*/\* ING_KO_END \*/', js, re.S)
    if not m:
        return False
    ctx.eval(m.group(1))
    for name in ING_CONSTS:
        mm = re.search(r'\n   const %s = (.*?);\n' % name, js, re.S)
        if not mm:
            return False
        ctx.eval('const %s = %s;' % (name, mm.group(1)))
    for name in ING_FUNCS:
        block = extract_fn(js, name)
        if block is None:
            return False
        ctx.eval(block)
    ctx.eval("if (typeof esc !== 'function') {"
             " function esc(s) { return String(s == null ? '' : s)"
             ".replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;'); } }")
    return True


def ing_dict(js):
    """index.html 에 심은 성분 사전(영문 → 한글)을 dict 로."""
    m = re.search(r'/\* ING_KO_START \*/\n(.*?)\n\s*/\* ING_KO_END \*/', js, re.S)
    if not m:
        return {}
    out = {}
    for k, v in re.findall(r'"((?:[^"\\]|\\.)*)"\s*:\s*"((?:[^"\\]|\\.)*)"', m.group(1)):
        out[k] = v
    return out

def main():
    html = open(INDEX, encoding='utf-8').read()
    scripts = re.findall(r'<script>(.*?)</script>', html, re.S)
    check(len(scripts) >= 1, '인라인 스크립트를 찾지 못했습니다')
    js = scripts[0] if scripts else ''

    # 1) 문법
    try:
        import esprima
        try:
            esprima.parseScript(js)
            check(True, '')
        except Exception as e:  # noqa: BLE001
            check(False, '스크립트 문법 오류: %s' % e)
    except ImportError:
        print('(esprima 없음 — 문법 검사 생략: pip install esprima)')

    # 2) v1.14 요소
    check("const APP_VERSION = 'v1.23'" in js, 'APP_VERSION 이 v1.23 이 아닙니다')
    check('<title>수메디팜 미니 CRM v1.23</title>' in html, '브라우저 탭 제목의 버전이 v1.23 이 아닙니다')
    check('ver-chip">v1.23' in html and 'ver-chip dark">v1.23' in html, '로그인 화면·상단 바의 버전 칩이 v1.23 이 아닙니다')
    check('id: \'drug\'' in js and 'renderDrugPage' in js, '약 검색 메뉴가 없습니다')
    check("id: 'guide'" in js and 'renderGuidePage' in js, '처방 셋팅 메뉴가 없습니다')
    # v1.11 — 🧭 처방 셋팅은 경구제 전용 · 💉 주사제 셋팅은 💉 주사제 주문 메뉴 안 탭
    check('guideTabBar_' not in js and 'switchGuideTab' not in js and 'guideTab:' not in js,
          '처방 셋팅에 경구제/주사제 2탭 전환이 남아 있습니다')
    check('orderTabBar_' in js and 'switchOrderTab' in js and "orderTab: 'entry'" in js,
          '주사제 주문 메뉴의 두 탭(주문(매출) 등록 / 주사제 셋팅)이 없습니다')
    check('💳 주문(매출) 등록' in js, '주문(매출) 등록 탭 이름이 없습니다')
    check('주사제 셋팅 (프로토콜·배합금기)' in js, '주사제 셋팅 탭 이름이 없습니다')
    check('renderInjectPanelHtml_' in js and 'renderInjectBody' in js, '주사제 셋팅 화면이 없습니다')
    check('runInjectRecommend' in js and 'loadInjectGuide' in js, '주사제 셋팅 조회가 없습니다')
    check('injectSendToOrder' in js and 'copyInjectSet' in js, '주사제 → 매출/세팅 연결이 없습니다')
    check('경구제(원외처방) 전용' in js and '💉 주사제 셋팅' in js, '제형 전용 배지가 없습니다')
    check('function openInjectSetting' in js, '경구 화면 → 주사제 셋팅 탭 이동 함수가 없습니다')
    check("form: '경구'" in js, '경구 추천에 form:경구 가 없습니다')
    check('guideOralOnlyRec_' in js, '경구 전용 안전장치가 없습니다')
    check('guideRateLiftHtml_' in js and '상한1평균수수료율' in js and '요율향상' in js, '최소 제약사 요율 향상 안내가 없습니다')
    check('guideMakerChipsHtml_' in js, '제약사별 품목 배지가 없습니다')
    check('guideFindProduct_' in js and 'guideCacheProduct_' in js, '가이드 품목 캐시가 없습니다')
    check('setGuideMaxMakers' in js and 'guideMaxMakers' in js, '최소 제약사 개수 선택이 없습니다')
    check("maxMakers: STATE.guideMaxMakers" in js, '최소 제약사 상한이 서버로 전달되지 않습니다')
    check('injCautionsHtml_' in js and 'renderInjectProtocols' in js and 'renderInjectCards' in js, '주사 프로토콜·배합금기 화면이 없습니다')
    check('injWarnHtml_' in js and 'toggleInjPick' in js, '배합금기 자동 경고가 없습니다')
    check('loadCoverageNotes' in js and 'renderCoverageCard' in js, '급여·삭감 가이드 카드가 없습니다')
    check('onInjectProtoQuery' in js, '프로토콜 검색이 없습니다')
    check('pendingOrderProduct' in js, '주문 등록 자동 채우기가 없습니다')
    check('serverAtLeast_' in js and 'versionNum_' in js, '서버 버전 비교가 없습니다')
    check('id="rg-name" autocomplete="name" placeholder="홍길동"' in html, '회원가입 이름 예시가 홍길동이 아닙니다')
    check('renderDashSearchCard' in js and 'onDashSearch' in js, '대시보드 바로 검색이 없습니다')
    check('birthday-banner' in js and 'renderBirthdayBanner' in js, '생일 알림 배너가 없습니다')
    check('kpicSearch' in js and 'kpicDrugDetail' in js, '약학정보원 연계 호출이 없습니다')
    check('drugAutoLink' in js and 'renderAutoLink' in js and 'loadAutoLink' in js, '약학정보원 자동 연동 화면이 없습니다')
    check('checkKpicHealth' in js and 'kpicHealth' in js, '약학정보원 연동 점검이 없습니다')
    check("id=\\\"drug-autolink\\\"" in js or "'<div id=\"drug-autolink\"></div>'" in js, '약학정보원 자동 연동 자리가 없습니다')
    check('getDeptGuide' in js and 'recommendRegimen' in js, '처방 셋팅/추천 호출이 없습니다')
    check('saveClientProfile' in js and 'submitClientProfile' in js, '원장 정보 저장이 없습니다')
    check('loadBirthdaySettings' in js and 'installBirthdayTrigger' in js, '생일 알림 설정이 없습니다')
    check('applyGuidePending' in js, '처방전으로 보내기 연결이 없습니다')

    # 2-d) v1.22 — 영문 성분명 한글 발음 병기
    check('/* ING_KO_START */' in js and '/* ING_KO_END */' in js, '성분 한글 발음 사전 구역이 없습니다')
    _dict = ing_dict(js)
    check(len(_dict) >= 600, '성분 한글 발음 사전이 너무 작습니다: %d개' % len(_dict))
    for en, ko in [('amlodipine', '암로디핀'), ('acetylcysteine', '아세틸시스테인'),
                   ('acebrophylline', '아세브로필린'), ('ambroxol', '암브록솔'),
                   ('atorvastatin', '아토르바스타틴'), ('rosuvastatin', '로수바스타틴'),
                   ('rabeprazole', '라베프라졸'), ('esomeprazole', '에소메프라졸'),
                   ('rebamipide', '레바미피드'), ('mosapride', '모사프리드'),
                   ('metformin', '메트포르민'), ('losartan', '로사르탄'),
                   ('valsartan', '발사르탄'), ('telmisartan', '텔미사르탄'),
                   ('sitagliptin', '시타글립틴'), ('dapagliflozin', '다파글리플로진'),
                   ('empagliflozin', '엠파글리플로진'), ('celecoxib', '셀레콕시브'),
                   ('loxoprofen', '록소프로펜'), ('aceclofenac', '아세클로페낙'),
                   ('acetaminophen', '아세트아미노펜'), ('pregabalin', '프레가발린'),
                   ('gabapentin', '가바펜틴'), ('levofloxacin', '레보플록사신'),
                   ('cefaclor', '세파클러'), ('choline alfoscerate', '콜린알포세레이트')]:
        check(_dict.get(en) == ko, '성분 사전 %s → %s 가 아닙니다(%s)' % (en, ko, _dict.get(en)))
    # 화면 적용 — 한글 발음 병기를 거치는 자리
    for label, needle in [
        ('처방 셋팅 제약사 성분 칩', "ingLabel_(g.성분명) + ' <small>' + fmtNum(g.품목수)"),
        ('처방 셋팅 성분 품목 표 제목', "'<div class=\"card-title\"><span>💊 ' + ingLabel_(g.성분명)"),
        ('처방 셋팅 성분 검색 그룹 머리', "ingLabel_(g.성분명 || key)"),
        ('담은 품목 목록 성분 열', "(r.성분 ? ingLabel_(r.성분) : '-')"),
        ('주사제 셋팅 카테고리 성분', "ingLabel_(g.성분명) + '</strong>"),
        ('약 검색 성분 묶음', "ingLabel_(g.성분명 || '성분 미등록')"),
        ('약학정보원 상세 성분', "it.성분한글 ? esc(it.성분한글) : ingLabel_(it.성분명)"),
        ('타사단가표 성분', "(p.성분명 ? ingLabel_(p.성분명) : '-')"),
    ]:
        check(needle in js, '%s 에 한글 발음 병기가 없습니다' % label)
    check('function ingLabel_' in js and 'function ingText_' in js and 'function ingKoOf_' in js,
          '한글 발음 병기 함수(ingLabel_·ingText_·ingKoOf_)가 없습니다')
    check('.ing-ko' in html, '한글 발음 표시용 CSS(.ing-ko)가 없습니다')
    check('guideMakerKoQ' in js and 'koFilter' in js, '한글 발음으로 제약사 성분을 거르는 처리가 없습니다')

    try:
        import quickjs
        ctx22 = quickjs.Context()
        check(load_ing_ctx(ctx22, js), '성분 한글 발음 함수를 실행 문맥에 넣지 못했습니다')

        def q22(expr):
            v = ctx22.eval(expr)
            return v.decode() if isinstance(v, bytes) else v

        def ing22(name):
            return q22('ingKoOf_(%s)' % json.dumps(name, ensure_ascii=False))

        cases = [
            ('Acebrophylline 100mg', '아세브로필린'),
            ('Acetylcysteine 200mg', '아세틸시스테인'),
            ('Ambroxol HCl 30mg', '암브록솔'),
            ('Amlodipine Besylate 5mg', '암로디핀'),
            ('Acetaminophen 325mg+Tramadol hydrochloride 37.5mg', '아세트아미노펜+트라마돌'),
            ('Valsartan 80mg+Hydrochlorothiazide 12.5mg', '발사르탄+히드로클로로티아지드'),
            ('Atorvastatin calcium trihydrate 10.85mg (10mg as atorvastatin)', '아토르바스타틴'),
            ('S-amlodipine besylate 2.5mg', '에스암로디핀'),
            ('라베프라졸 10mg', ''),
            ('글루타치온', ''),
            ('중 Hyaluronate 20mg', '히알루론산'),
            ('Ezetimibe 10mg+Rosuvastatin calcium 10.4mg (Rosuvastatin으로서 10mg)', '에제티미브+로수바스타틴'),
        ]
        for name, want in cases:
            got = ing22(name)
            check(got == want, '성분 한글 발음 %r → %r (기대 %r)' % (name, got, want))
        check(ing22('Xyzabepine 10mg') != '', '사전에 없는 영문 성분이 빈 발음으로 나옵니다')

        label = q22('ingLabel_("Acebrophylline 100mg")')
        check('Acebrophylline 100mg' in label and '(아세브로필린)' in label and 'ing-ko' in label,
              '성분 표시 형식이 영문+(한글) 이 아닙니다: %s' % label)
        label_ko = q22('ingLabel_("라베프라졸 10mg")')
        check(label_ko == '라베프라졸 10mg', '한글 성분명에 괄호가 겹쳐 붙었습니다: %s' % label_ko)
        txt = q22('ingText_("Acetylcysteine 200mg")')
        check(txt == 'Acetylcysteine 200mg (아세틸시스테인)', '출력물용 글자 형식이 다릅니다: %s' % txt)
    except ImportError:
        print('(quickjs 없음 — 성분 한글 발음 실행 검사 생략: pip install quickjs)')

    # 2-e) v1.23 — 인쇄/PDF 합계 행: 연회색 배경 + 진한 글자색 (어두운 배경에 검은 글자 금지)
    def lum_(hexcolor):
        """#rrggbb 의 상대 밝기(0=검정, 1=흰색)"""
        h = hexcolor.strip().lstrip('#')
        if len(h) == 3:
            h = ''.join(c * 2 for c in h)
        r, g, b = (int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4))
        return 0.2126 * r + 0.7152 * g + 0.0722 * b

    def print_rules_(doc):
        """@media print 안의 #print-area 규칙을 (선택자, 본문) 으로 뽑습니다."""
        block = re.search(r'/\* ---------------- Print / PDF A4 Styles ---------------- \*/([\s\S]*?)</style>', doc)
        out = []
        if not block:
            return out
        body = re.sub(r'/\*[\s\S]*?\*/', ' ', block.group(1))   # 주석 제거 후 선택자 비교
        for m in re.finditer(r'([^{}]+)\{([^{}]*)\}', body):
            sel = ' '.join(m.group(1).split())
            if sel.startswith('#print-area'):
                out.append((sel, m.group(2)))
        return out

    _doc23 = open(INDEX, encoding='utf-8').read()
    _rules23 = print_rules_(_doc23)
    check(bool(_rules23), '인쇄용 CSS(#print-area) 규칙을 찾지 못했습니다')
    _tot23 = next((body for sel, body in _rules23 if sel == '#print-area .tot'), '')
    _totcell23 = next((body for sel, body in _rules23 if sel == '#print-area .tot > td'), '')
    check(bool(_tot23) and bool(_totcell23), '합계 행(.tot / .tot > td) 인쇄 스타일이 없습니다')
    _bg23 = re.search(r'background:\s*(#[0-9a-fA-F]{3,6})', _tot23)
    _fg23 = re.search(r'(?<!-)color:\s*(#[0-9a-fA-F]{3,6})', _tot23)
    check(bool(_bg23), '합계 행 인쇄 배경색이 없습니다')
    check(bool(_fg23), '합계 행 인쇄 글자색이 없습니다')
    if _bg23 and _fg23:
        check(lum_(_bg23.group(1)) >= 0.85, '합계 행 배경이 연한 색이 아닙니다: %s' % _bg23.group(1))
        check(lum_(_bg23.group(1)) - lum_(_fg23.group(1)) >= 0.7,
              '합계 행 배경과 글자색 대비가 부족합니다: %s / %s' % (_bg23.group(1), _fg23.group(1)))
        check(lum_(_fg23.group(1)) <= 0.15, '합계 행 글자색이 진한 색이 아닙니다: %s' % _fg23.group(1))
    check('border-top: 2px solid #334155' in _tot23 or 'border-top: 2px solid #334155' in _totcell23,
          '합계 행 위쪽 구분선(2px #334155)이 없습니다')
    check('color: #0f172a' in _totcell23 or 'color: #0f172a' in _tot23, '합계 행 글자색(#0f172a)이 없습니다')
    check('font-weight: 700' in _totcell23 or 'font-weight: bold' in _totcell23, '합계 행 굵은 글씨가 없습니다')
    check('print-color-adjust: exact' in _tot23 and 'print-color-adjust: exact' in _totcell23,
          '합계 행 배경이 인쇄되도록 하는 print-color-adjust: exact 가 없습니다')
    check('color-scheme: only light' in _doc23, '인쇄 영역의 color-scheme: only light(기기 다크모드 차단)가 없습니다')
    _th23 = next((body for sel, body in _rules23 if sel == '#print-area table.data th'), '')
    check('background: #1e3a5f' in _th23 and 'color: #fff' in _th23,
          '표 머리글(thead)이 어두운 배경 + 흰 글씨가 아닙니다')
    # 인쇄 규칙 어디에도 '어두운 배경 + 어두운 글자' 조합이 없어야 합니다
    for sel, body in _rules23:
        b = re.search(r'background(?:-color)?:\s*(#[0-9a-fA-F]{3,6})', body)
        f = re.search(r'(?<!-)color:\s*(#[0-9a-fA-F]{3,6})', body)
        if b and f:
            check(not (lum_(b.group(1)) < 0.5 and lum_(f.group(1)) < 0.35),
                  '인쇄 규칙이 어두운 배경에 어두운 글자를 씁니다: %s' % sel)
    # 합계 행이 들어가는 출력물 전부에 합계 클래스가 붙어 있는지
    for label, needle in [
        ('처방 내역(내부용·원장님용)', "'<tr class=\"tot\"><td colspan=\"5\" class=\"center\">합계 ('"),
        ('거래명세서', "'<tr class=\"tot\"><td colspan=\"5\" class=\"center\">합 계</td>"),
        ('거래원장 기간 합계', "'<tr class=\"tot\"><td colspan=\"3\" class=\"center\">기간 합계 / 기말잔액</td>"),
        ('회전일 현황표', "'<tr class=\"tot\"><td colspan=\"5\">합계</td>"),
    ]:
        check(needle in js, '%s 출력물의 합계 행에 합계 클래스(tot)가 없습니다' % label)
    for m in re.finditer(r'<tr class="tot"[^>]*>', js):
        check('style=' not in m.group(0), '합계 행에 인라인 스타일이 붙어 인쇄 색상 규칙을 덮습니다: %s' % m.group(0))
    # 서비스워커 캐시·배포 사본
    _sw = open(os.path.join(PROJECT, 'sw.js'), encoding='utf-8').read()
    check("'soomedipharm-crm-v18'" in _sw, '서비스워커 캐시가 v18 이 아닙니다')
    _dl = os.path.abspath(os.path.join(PROJECT, '..', '..', 'downloads', 'Index.html'))
    if os.path.exists(_dl):
        import hashlib
        def md5_(p):
            return hashlib.md5(open(p, 'rb').read()).hexdigest()
        check(md5_(_dl) == md5_(INDEX), 'downloads/Index.html 이 projects/soomedipharm-crm/index.html 과 다릅니다')

    # 2-c) v1.7 — 비거래처 사전조회(심평원 HIRA)
    check('renderHiraPage' in js and '비거래처 심평원(HIRA) 사전조회' in js, '비거래처 사전조회 화면이 없습니다')
    # 메뉴 순서 (v1.14): 공지사항·게시판 → 거래처 등록/관리 → 거래처 상세정보 → 월별 실적 → 처방 셋팅 → 처방전 입력
    #   → 주사제 주문 → 수금 등록 → 약 검색 → 주문 → 원장 → 설정
    order_ids = re.findall(r"\n       id: '([a-z]+)',", js)
    expect_order = ['board', 'clients', 'clientinfo', 'perf', 'guide', 'prescription', 'order', 'collection', 'drug', 'turnover', 'ledger', 'docs']
    check(order_ids[:len(expect_order)] == expect_order, '사이드바 메뉴 순서가 다릅니다: %s' % order_ids)
    check(not re.search(r"label: '\s*\d+\.", js), '메뉴 이름 앞에 숫자가 붙었습니다')
    check('loadHiraModule' in js and 'hiraBase' in js, '사전조회 초기 로딩이 없습니다')
    check("runServer('getHiraPrevisitBriefing'" in js, 'getHiraPrevisitBriefing 호출이 없습니다')
    check('hiraSearch' in js and 'hiraPickDept' in js and 'hiraPickHospital' in js, '병원·진료과 선택 흐름이 없습니다')
    check('hiraKeyGuideHtml_' in js and 'HIRA_API_KEY' in js, 'HIRA_API_KEY 안내가 없습니다')
    check("runServer('checkHiraApi'" in js and 'hiraCheckApi' in js, '심평원 연동 점검이 없습니다')
    check('hiraRegisterClient' in js and 'openClientModal' in js, '거래처 등록 연결이 없습니다')
    check('hiraClientMatch_' in js, '이미 등록된 거래처 판별이 없습니다')
    check('hiraOpenGuide' in js and 'hiraCopyBriefing' in js, '처방 셋팅·복사 연결이 없습니다')
    check('방문 전 영업 브리핑' in js, '브리핑 카드 제목이 없습니다')
    check('TOP 30' in js and 'hiraToggleMore' in js, 'TOP 30 펼치기가 없습니다')
    check('고요율 추천 품목' in js and '비급여·주사 타깃' in js, '추천·주사 타깃 섹션이 없습니다')
    check('예상 추천' in js or '공개하지 않습니다' in js, '예상 추천 고지가 없습니다')
    check('심평원 신고' in js and '평가등급' in js, '진료과목·평가등급 표시가 없습니다')

    # 2-b) 요율등급 3단계 (v1.6) — MASTER 전용 화면 요소
    check('RATE_TIER_CHOICES' in js, '요율등급 선택지가 없습니다')
    check('1단계 (-1%p)' in js and '2단계 (-2%p)' in js and '3단계 (-3%p)' in js,
          '요율등급 1·2·3단계 표기가 없습니다')
    check('function userSetTier' in js, 'userSetTier 함수가 없습니다')
    check("runServer('updateUserTier'" in js, 'updateUserTier 호출이 없습니다')
    check('tierOptionsHtml_' in js, '등급 선택지 생성 함수가 없습니다')
    users_fn = re.search(r'function usersSectionHtml_\(\)\s*\{(.*?)\n   \}', js, re.S)
    check(bool(users_fn), 'usersSectionHtml_ 를 찾지 못했습니다')
    if users_fn:
        body = users_fn.group(1)
        check('tierCell' in body and 'userSetTier' in body, '사용자 목록에 등급 선택기가 없습니다')
        check('요율등급' in body, '사용자 목록에 요율등급 열이 없습니다')
        check('차감 없음' in body, 'MASTER 행의 차감 없음 표기가 없습니다')

    # 3) 정의된 함수 목록
    defined = set(re.findall(r'function\s+([A-Za-z_$][\w$]*)\s*\(', js))
    defined |= set(re.findall(r'const\s+([A-Za-z_$][\w$]*)\s*=\s*function', js))
    builtin = {'event', 'confirm', 'alert', 'if', 'for', 'while', 'return', 'document', 'window'}

    called = set()
    for attr in re.findall(r'on(?:click|input|change|keydown|focus|submit)="([^"]+)"', html):
        for name in re.findall(r'(?<![.\w$])([A-Za-z_$][\w$]*)\s*\(', attr):
            called.add(name)
    unknown = sorted(n for n in called if n not in defined and n not in builtin)
    check(not unknown, '정의되지 않은 함수 호출: %s' % ', '.join(unknown))

    # 4) 서버 함수 목록 대조
    if os.path.exists(CODEGS):
        code = open(CODEGS, encoding='utf-8').read()
        reg = re.search(r'function apiFunctions_\(\)\s*\{(.*?)\n\}', code, re.S)
        api = set(re.findall(r'(\w+)\s*:\s*\w+', reg.group(1))) if reg else set()
        used = set(re.findall(r"runServer\('([A-Za-z_$][\w$]*)'", js))
        missing = sorted(u for u in used if u not in api)
        check(not missing, 'Code.gs 에 없는 서버 함수 호출: %s' % ', '.join(missing))
        mver = re.search(r"const APP_VERSION = '(v1\.\d+)'", code)
        check(bool(mver) and int(mver.group(1).split('.')[1]) >= 15,
              'Code.gs 버전이 v1.15 이상이 아닙니다: %s' % (mver.group(1) if mver else '없음'))
        check(re.search(r'getHiraPrevisitBriefing\s*:\s*getHiraPrevisitBriefing', code) is not None,
              'Code.gs apiFunctions_ 에 getHiraPrevisitBriefing 이 없습니다')
        check(re.search(r'checkHiraApi\s*:\s*checkHiraApi', code) is not None,
              'Code.gs apiFunctions_ 에 checkHiraApi 가 없습니다')
        for name in ['nextClientCode_', 'hiraCall_', 'hiraHospitalExtras_', 'buildHiraBriefing_',
                     'hiraMapDeptsToGuide_', 'hiraNonPayTagsOf_', 'hiraAuthMessage_', 'HIRA_SERVICES_']:
            check(name in code, 'Code.gs 에 %s 가 없습니다' % name)
        check('/hospInfoServicev2/getHospBasisList' in code, '병원정보서비스 엔드포인트가 없습니다')
        check('/MadmDtlInfoService2.8/getDgsbjtInfo2.8' in code, '진료과목정보 엔드포인트가 없습니다')
        check('/nonPaymentDamtInfoService/getNonPaymentItemHospDtlList' in code, '비급여 엔드포인트가 없습니다')
        check('/hospAsmInfoService1/getHospAsmInfo1' in code, '병원평가 엔드포인트가 없습니다')
        check("'S' + (next <= 999" in code, '거래처코드 Sxxx 채번 규칙이 없습니다')
        check(re.search(r'updateUserTier\s*:\s*updateUserTier', code) is not None,
              'Code.gs apiFunctions_ 에 updateUserTier 가 없습니다')
        for name in ['rateCutPercent_', 'applyRateCut_', 'normalizeTier_', 'productsForUser_', 'setUserTierCell_']:
            check(name in code, 'Code.gs 에 %s 가 없습니다' % name)
        for name in ['getInjectGuide', 'getInjectProtocols', 'getCoverageNotes', 'getDeptGuide', 'recommendRegimen', 'looksParenteral_', 'dosageFormOf_',
                     'recommendMinMakers_', 'evalMakerSet_', 'cmpMakerEval_', 'betterPick_',
                     'nameStem_', 'similarNameHits_', 'drugAutoLink', 'injectProtocolMatches_', 'kpicHealth']:
            check(name in code, 'Code.gs 에 %s 가 없습니다' % name)
    else:
        print('(Code.gs 없음 — 서버 함수 대조 생략)')

    # 4-b) 가이드 → 처방전 연결 (v1.7 버그 수정)
    check('STATE.rxGuideCodes' in js and 'rxGuideCodes: []' in js, '가이드 품목 유지 목록(rxGuideCodes)이 없습니다')
    rec_fn = re.search(r'function renderGuideRecommend\(\)\s*\{(.*?)\n   \}', js, re.S)
    check(bool(rec_fn) and 'forEach(guideCacheProduct_)' in rec_fn.group(1), '추천 렌더에서 품목 캐시가 없습니다')
    send_fn = re.search(r'function guideSendToRx\(\)\s*\{(.*?)\n   \}', js, re.S)
    check(bool(send_fn) and 'guideCacheProduct_' in send_fn.group(1), '보내기 시점 캐시가 없습니다')
    check(bool(send_fn) and 'rxGuideCodes' in send_fn.group(1), '보내기 시점 유지목록 기록이 없습니다')
    add_fn = re.search(r'function guideAddItem\(code\)\s*\{(.*?)\n   \}', js, re.S)
    check(bool(add_fn) and 'guideFindProduct_' in add_fn.group(1), '+담기 시점 품목 조회가 없습니다')
    # v1.7 보수 — + 담기 토글 / 담은 것만 보내기 / 보내기 버튼 문구
    check(bool(add_fn) and 'state.guidepending' in add_fn.group(1).lower() and 'filter' in add_fn.group(1),
          '+담기가 토글(다시 누르면 빼기)이 아닙니다')
    check('guideSendBtnLabel_' in js and '담은 ' in js and '개 처방전으로 보내기' in js,
          '보내기 버튼 문구가 담은 개수로 바뀌지 않습니다')
    check('전체 ' in js and 'guideSendBtnLabel_' in js, '담은 것이 없을 때 전체 개수 표시가 없습니다')
    check('✓ 담김' in js and 'data-guide-code' in js, '이미 담은 품목의 ✓ 담김 표시가 없습니다')
    check('guideSyncPendingUI_' in js and "getElementById('guide-send-rx')" in js,
          '담기 클릭 시 버튼/행 즉시 갱신이 없습니다')
    check(bool(send_fn) and 'picked.length' in send_fn.group(1) and 'const picked' in send_fn.group(1),
          '보내기가 담은 품목(picked)을 우선하지 않습니다')
    lrx = re.search(r'async function loadRxData\(opts\)\s*\{(.*?)\n   \}', js, re.S)
    check(bool(lrx) and 'applyGuidePending()' in lrx.group(1), '처방전 목록 로드 후 가이드 품목 재적용이 없습니다')
    ap = re.search(r'function applyGuidePending\(\)\s*\{(.*?)\n   \}', js, re.S)
    check(bool(ap) and 'rxGuideCodes' in ap.group(1), 'applyGuidePending 이 유지목록을 쓰지 않습니다')
    check(bool(ap) and 'if (!STATE.rxClient) return 0' in ap.group(1), '병원 미선택 시 보류 처리가 없습니다')

    # 4-c) 처방전 ↔ 처방 셋팅 병원 연결 (v1.7 UX)
    check('rxOpenGuideFromRx' in js and '🎯 처방 셋팅에서 가져오기' in js, '처방전 화면에서 처방 셋팅으로 가는 버튼이 없습니다')
    check('rxApplyGuideRecNow' in js and '품목 바로 담기' in js, '추천을 현재 병원에 바로 담는 버튼이 없습니다')
    check('guideHospitalBarHtml_' in js and 'guideSetHospital' in js, '처방 셋팅의 담을 병원 선택기가 없습니다')
    check('guideRxTargetBadge_' in js and '담을 병원' in js, '처방 셋팅의 담을 병원 배지가 없습니다')
    check('rxOpenFromGuide' in js, '처방 셋팅 → 처방전 이동 버튼이 없습니다')

    # 4-d) 사이드바 '거래처 상세정보' 메뉴 (v1.7)
    check("id: 'clientinfo'" in js and 'renderClientInfoPage' in js, '거래처 상세정보 메뉴가 없습니다')
    check("label: '거래처 상세정보'" in js, '메뉴 이름이 거래처 상세정보가 아닙니다')
    check('setClientInfoTab' in js and 'clientInfoTab' in js, '내 거래처/심평원 탭 전환이 없습니다')
    check('renderClientInfoList' in js and 'clientInfoHira' in js, '내 거래처 목록·심평원 바로가기가 없습니다')
    check('loadHiraBase_' in js, '심평원 진료과 목록 로딩이 없습니다')
    check('원장님 성함·생일·취향' in js, '원장님 정보 안내가 없습니다')

    # 4-e) 보험코드 앞자리 0 보존 · 중복 방지 (v1.7 보수)
    check('function rxCodeNorm_' in js and 'function rxCodeKey_' in js, '보험코드 정규화 헬퍼가 없습니다')
    check('function rxDedupeRows_' in js and 'rxDedupeRows_(rows)' in js, '처방 목록 중복 정리가 없습니다')
    check('function rxCacheNormalize_' in js, '사이트 캐시 보험코드 정규화가 없습니다')
    check("'지난 ' + fmtNum(r.지난수량)" in js, '수량 입력칸 안내문(지난 N개)이 없습니다')
    check("placeholder=\"' + (r.지난수량 ? String(r.지난수량) : '0') + '\"" not in js,
          '수량 입력칸이 지난 수량을 실제 값처럼 보이게 표시합니다')

    # 4-f) 월별 실적 — 직납(거래내역) + 예상 처방(처방내역) 합산 (v1.8)
    check('예상 총매출' in js and '예상 처방금액' in js and '예상 수수료' in js,
          '월별 실적에 예상 표기(예상 총매출·예상 처방금액·예상 수수료)가 없습니다')
    check('익익월' in js, '처방 실적 예상 안내(익익월 정산) 문구가 없습니다')
    check('직납 매출 (확정)' in js or '직납 매출(확정)' in js, '직납 매출 확정 표기가 없습니다')
    check('function perfCell_' in js and 'function perfSumRows' in js, '실적 셀 정리 함수가 없습니다')
    check('setPerfMatrixMetric' in js and 'perfMatrixValue_' in js, '담당자×월 기준 전환이 없습니다')
    check('perfRxNote_' in js, '처방 예상 안내 함수가 없습니다')
    perf_fn = re.search(r'function renderPerfPage\(container\)\s*\{(.*?)\n   \}', js, re.S)
    check(bool(perf_fn), 'renderPerfPage 를 찾지 못했습니다')
    if perf_fn:
        body = perf_fn.group(1)
        check(body.count('table-wrap') >= 4, '월별 실적 표가 table-wrap 으로 감싸지지 않았습니다')
        check('예상 총매출' in body and '예상 처방금액' in body and '예상 수수료' in body,
              '월별 실적 표에 예상 항목 열이 없습니다')
        check('직납 매출' in body and '수금' in body, '직납·수금 열이 없습니다')
        check('perf-note' in body, '예상 안내 문구(perf-note)가 화면에 없습니다')

    # 5) 순수 함수 실행 (QuickJS)
    try:
        import quickjs
        ctx = quickjs.Context()
        load_ing_ctx(ctx, js)
        fn = re.search(r'(function birthDday_\(.*?\n   \})', js, re.S)
        if fn:
            ctx.eval('var STATE = { today: "2026-11-27" };')
            ctx.eval(fn.group(1))
            got = {
                'today': ctx.eval('birthDday_("11-27")'),
                'tomorrow': ctx.eval('birthDday_("11-28")'),
                'nextYear': ctx.eval('birthDday_("11-26")'),
                'full': ctx.eval('birthDday_("1991-11-28")'),
                'bad': ctx.eval('String(birthDday_("생일없음"))'),
            }
            check(got['today'] == 0, 'birthDday_ 오늘 계산 오류: %s' % got['today'])
            check(got['tomorrow'] == 1, 'birthDday_ 내일 계산 오류: %s' % got['tomorrow'])
            check(got['nextYear'] == 364, 'birthDday_ 지난 생일 계산 오류: %s' % got['nextYear'])
            check(got['full'] == 1, 'birthDday_ 연도 포함 계산 오류: %s' % got['full'])
            check(got['bad'] == 'null', 'birthDday_ 잘못된 값 처리 오류: %s' % got['bad'])
        else:
            check(False, 'birthDday_ 함수를 추출하지 못했습니다')
    except ImportError:
        print('(quickjs 없음 — 순수 함수 실행 검사 생략: pip install quickjs)')

    # 6) 가이드 → 처방전 연결 실행 검사 (이엘파마 경구 품목이 STATE.products 에 없어도 유지되는지)
    try:
        import quickjs
        names = ['guideCacheProduct_', 'guideFindProduct_', 'guideAddItem', 'guideSendToRx', 'applyGuidePending',
                 'guidePendingSet_', 'guidePendingCount_', 'guideSendBtnLabel_', 'guideSyncPendingUI_',
                 'guideRxTargetBadge_', 'guideHospitalBarHtml_', 'guideSetHospital', 'rxOpenFromGuide',
                 'rxApplyGuideRecNow', 'rxOpenGuideFromRx',
                 'rxCodeNorm_', 'rxCodeKey_', 'rxDedupeRows_',
                 'makerFromName_', 'makerOf_']
        blocks = [extract_fn(js, n) for n in names]
        if any(b is None for b in blocks):
            check(False, '가이드→처방전 함수를 추출하지 못했습니다: %s' % [n for n, b in zip(names, blocks) if b is None])
        else:
            ctx = quickjs.Context()
            load_ing_ctx(ctx, js)
            check(load_maker_ctx(ctx, js), '앱 내장 제약사 목록을 실행 문맥에 넣지 못했습니다')
            ctx.eval('''
            var STATE = {
              guideRec: { picks: [
                { 보험코드: 'E100', 품목명: '베아셋정', 규격: '', 제약사: '대웅바이오', 약가: 1063, 수수료율: 54, 성분: '아세트아미노펜' },
                { 보험코드: 'E200', 품목명: '아토타틴정10mg', 규격: '', 제약사: '(주)일화', 약가: 1971, 수수료율: 34, 성분: '아토르바스타틴' }
              ] },
              guideData: null, guideProductCache: {}, guidePending: [], rxGuideCodes: [],
              rxRows: [], rxClient: '', rxFrequent: [], products: [],
              rxDirty: false, rxMonth: '2026-11', clients: [],
              guideDept: ''
            };
            STATE.clients = [
              { 거래처코드: 'S001', 거래처명: '수아의원', 사용여부: 'Y' },
              { 거래처코드: 'S002', 거래처명: '장편한내과의원', 사용여부: 'Y' }
            ];
            var __toasts = [], __menus = [], __renders = 0, __sums = 0, __menus2 = 0;
            function findClient(code) {
              code = String(code || '');
              for (var i = 0; i < STATE.clients.length; i++) if (STATE.clients[i].거래처코드 === code) return STATE.clients[i];
              return null;
            }
            function renderActiveMenu() { __menus2++; }
            function showToast(m) { __toasts.push(String(m)); }
            function switchMenu(id) { __menus.push(String(id)); }
            function renderRxRows() { __renders++; }
            function updateRxSummary() { __sums++; }
            function esc(s) { return String(s == null ? '' : s); }
            ''')
            for b in blocks:
                ctx.eval(b)

            # (A) 추천에서 '처방전 입력으로 보내기' → 병원 선택 후 서버 목록이 0건이어도 유지
            ctx.eval("guideSendToRx();")
            check(ctx.eval("__menus.join(',')").decode() if isinstance(ctx.eval("__menus.join(',')"), bytes) else ctx.eval("__menus.join(',')") == 'prescription', '보내기가 처방전 화면으로 이동하지 않음')
            ctx.eval("STATE.rxClient = 'S001'; STATE.rxRows = [];")   # 서버가 저장·빠른 품목 0건을 돌려준 상황
            ctx.eval("applyGuidePending();")
            got = ctx.eval("[STATE.rxRows.length, (STATE.rxRows[0]||{}).보험코드, (STATE.rxRows[0]||{}).품목명, (STATE.rxRows[0]||{}).수량, String((STATE.rxRows[0]||{}).saved)].join('|')")
            got = got.decode() if isinstance(got, bytes) else got
            check(got == '2|E100|베아셋정||false', '병원 선택 후 가이드 품목이 유지되지 않음: %s' % got)
            check(ctx.eval("Object.keys(STATE.guideProductCache).length") == 2, '추천 품목이 보험코드로 캐시되지 않음')

            # (B) 캐시가 비어 있어도 +담기/보내기 시점에 되찾아 담는지
            ctx.eval("STATE.guideProductCache = {}; STATE.rxRows = []; STATE.guidePending = []; STATE.rxGuideCodes = []; guideAddItem('E200');")
            ctx.eval("applyGuidePending();")
            got2 = ctx.eval("[STATE.rxRows.length, (STATE.rxRows[0]||{}).보험코드].join('|')")
            got2 = got2.decode() if isinstance(got2, bytes) else got2
            check(got2 == '1|E200', '+담기 품목이 처방전 목록에 안 들어감: %s' % got2)

            # (C) 병원 미선택이면 보류 — 목록을 비우지 않음
            ctx.eval("STATE.rxClient = ''; STATE.rxRows = []; STATE.guidePending = ['E100'];")
            ctx.eval("applyGuidePending();")
            hold = ctx.eval("[STATE.rxRows.length, STATE.guidePending.join(',')].join('|')")
            hold = hold.decode() if isinstance(hold, bytes) else hold
            check(hold == '0|E100', '병원 미선택 시 품목이 사라짐: %s' % hold)

            # (D) 처방전에서 병원을 고른 채 처방 셋팅으로 → 담을 병원 배지/선택기, 추천 한 번에 담기
            ctx.eval("STATE.rxClient = 'S001'; STATE.guidePending = []; STATE.rxGuideCodes = []; STATE.rxRows = [];")
            badge = ctx.eval('guideRxTargetBadge_()')
            badge = badge.decode() if isinstance(badge, bytes) else badge
            check('수아의원' in badge, '처방 셋팅 배지에 병원명이 없습니다: %s' % badge)
            bar = ctx.eval('guideHospitalBarHtml_()')
            bar = bar.decode() if isinstance(bar, bytes) else bar
            check('수아의원' in bar and 'selected' in bar, '병원 선택기에서 현재 병원이 선택돼 있지 않습니다')
            ctx.eval("rxApplyGuideRecNow();")
            got3 = ctx.eval("[STATE.rxRows.length, (STATE.rxRows[0]||{}).보험코드].join('|')")
            got3 = got3.decode() if isinstance(got3, bytes) else got3
            check(got3 == '2|E100', '추천 바로 담기가 현재 병원에 안 들어감: %s' % got3)
            ctx.eval("STATE.rxClient = ''; rxOpenGuideFromRx();")
            no_client_toast = ctx.eval('__toasts[__toasts.length - 1]')
            no_client_toast = no_client_toast.decode() if isinstance(no_client_toast, bytes) else no_client_toast
            check('병원을 선택' in no_client_toast, '병원 없이 셋팅 이동 시 안내가 없습니다: %s' % no_client_toast)
            ctx.eval("guideSetHospital('S002');")
            check(ctx.eval('STATE.rxClient').decode() if isinstance(ctx.eval('STATE.rxClient'), bytes) else ctx.eval('STATE.rxClient') == 'S002',
                  '처방 셋팅에서 병원 선택이 처방전 선택으로 이어지지 않습니다')

            # (E) 제보된 버그 — 추천 28개 중 3개만 ＋ 담기 후 보내면, 28개가 아니라 담은 3개만
            def q(v):
                return v.decode() if isinstance(v, bytes) else v

            ctx.eval("""
              (function () {
                var picks = [];
                for (var i = 1; i <= 28; i++) {
                  picks.push({ 보험코드: 'T' + (100 + i), 품목명: '테스트정' + i, 규격: '', 제약사: '테스트제약' + (i % 7),
                               약가: 1000 + i, 수수료율: 50, 성분: '성분' + i });
                }
                STATE.guideRec = { picks: picks, mode: 'maxrate', maxMakers: 3,
                                   summary: { 추천품목수: 28, 제약사수: 7, 평균수수료율: 50, 성분수: 28 } };
                STATE.guideProductCache = {};
                STATE.rxClient = 'S001';
                STATE.guidePending = []; STATE.rxGuideCodes = []; STATE.rxRows = [];
              })();
            """)
            empty_label = q(ctx.eval("guideSendBtnLabel_(STATE.guideRec)"))
            check('전체 28개 처방전으로 보내기' in empty_label, '담은 것이 없을 때 보내기 버튼 문구가 다릅니다: %s' % empty_label)

            ctx.eval("guideAddItem('T101'); guideAddItem('T102'); guideAddItem('T103');")
            check(q(ctx.eval("STATE.guidePending.join(',')")) == 'T101,T102,T103',
                  '3개 ＋ 담기 결과가 다릅니다: %s' % q(ctx.eval("STATE.guidePending.join(',')")))
            three_label = q(ctx.eval("guideSendBtnLabel_(STATE.guideRec)"))
            check('담은 3개 처방전으로 보내기' in three_label, '담은 3개일 때 버튼 문구가 다릅니다: %s' % three_label)

            # 같은 ＋를 다시 누르면 빠지고, 한 번 더 누르면 다시 담긴다(토글)
            ctx.eval("guideAddItem('T102');")
            check(q(ctx.eval("STATE.guidePending.join(',')")) == 'T101,T103',
                  '＋를 다시 눌러도 빠지지 않습니다(토글 아님): %s' % q(ctx.eval("STATE.guidePending.join(',')")))
            check(q(ctx.eval("STATE.rxGuideCodes.join(',')")) == 'T101,T103',
                  '뺀 품목이 유지목록(rxGuideCodes)에 남았습니다: %s' % q(ctx.eval("STATE.rxGuideCodes.join(',')")))
            ctx.eval("guideAddItem('T102');")
            check(int(ctx.eval("guidePendingCount_()")) == 3, '다시 담은 뒤 담은 개수가 3이 아닙니다')

            # 보내기 — 28개가 아니라 담은 3개만 유지되고 처방전 목록에도 3개만
            ctx.eval("guideSendToRx();")
            sent = q(ctx.eval("[STATE.guidePending.length, STATE.guidePending.slice().sort().join(','), STATE.rxGuideCodes.length, STATE.rxRows.length].join('|')"))
            check(sent == '3|T101,T102,T103|3|0', '담은 3개만 보내지지 않았습니다: %s' % sent)
            check(q(ctx.eval("__menus[__menus.length - 1]")) == 'prescription', '보내기가 처방전 화면으로 이동하지 않음')
            ctx.eval("applyGuidePending();")
            rows3 = q(ctx.eval("STATE.rxRows.map(function (r) { return r.보험코드; }).sort().join(',')"))
            check(rows3 == 'T101,T102,T103', '처방전 목록에 담은 3개만 들어가지 않았습니다: %s' % rows3)

            # ＋로 담은 것이 하나도 없으면 예전처럼 추천 전체(28개)를 보냅니다
            ctx.eval("STATE.guidePending = []; STATE.rxGuideCodes = []; STATE.rxRows = []; guideSendToRx();")
            allsent = q(ctx.eval("[STATE.guidePending.length, STATE.rxGuideCodes.length].join('|')"))
            check(allsent == '28|28', '담은 것이 없을 때 전체 보내기가 깨졌습니다: %s' % allsent)
    except ImportError:
        pass

    # 7) 보험코드 정규화·중복 정리 실행 검사 (v1.7 보수)
    try:
        import quickjs
        ctx = quickjs.Context()
        load_ing_ctx(ctx, js)
        ctx.eval('var STATE = { rxMonth: "2026-11" };')
        ctx.eval('var __CACHE = { products: {}, byClient: {} };')
        ctx.eval('function rxCacheRead() { return JSON.parse(JSON.stringify(__CACHE)); }')
        for name in ['rxCodeNorm_', 'rxCodeKey_', 'rxDedupeRows_', 'rxBuildRows_']:
            block = extract_fn(js, name)
            check(block is not None, '%s 를 추출하지 못했습니다' % name)
            if block:
                ctx.eval(block)
        got = ctx.eval('''
          [ rxCodeNorm_("73001620"), rxCodeNorm_("073001620"), rxCodeNorm_(73001620),
            rxCodeNorm_("01291"), rxCodeNorm_("M2094163"),
            rxCodeKey_("073001620") === rxCodeKey_("73001620"),
            rxCodeKey_("073001620") === rxCodeKey_("073001480") ].join("|")
        ''')
        got = got.decode() if isinstance(got, bytes) else got
        check(got == '073001620|073001620|073001620|01291|M2094163|true|false',
              '보험코드 정규화 결과가 다릅니다: %s' % got)
        dedup = ctx.eval('''
          (function () {
            var rows = rxDedupeRows_([
              { 보험코드: "073001620", 품목명: "건피드정", 수량: 5 },
              { 보험코드: "73001620", 품목명: "건피드정", 수량: 9 },
              { 보험코드: "073001480", 품목명: "라베건정10mg", 수량: 3 },
              { 보험코드: "73001480", 품목명: "라베건정10mg", 수량: 3 }
            ]);
            return [rows.length, rows.map(function (r) { return r.보험코드; }).join(",")].join("|");
          })()
        ''')
        dedup = dedup.decode() if isinstance(dedup, bytes) else dedup
        check(dedup == '2|073001620,073001480', '보험코드 표기 차이 중복이 남습니다: %s' % dedup)

        # 현장 상황: 시트는 73001620(숫자), 사이트 캐시는 073001620 → 4줄이 아니라 2줄
        built = ctx.eval('''
          (function () {
            var saved = { rows: [
              { 보험코드: 73001620, 품목명: '건피드정', 규격: '', 제약사: '건일바이오팜㈜', 약가: 119, 수수료율: 52, 수량: 10000, 처방ID: 'RX1' },
              { 보험코드: 73001480, 품목명: '라베건정10mg', 규격: '', 제약사: '건일바이오팜㈜', 약가: 454, 수수료율: 58, 수량: 10000, 처방ID: 'RX2' }
            ] };
            var quick = { items: [
              { 보험코드: '073001620', 품목명: '건피드정', 규격: '', 제약사: '건일바이오팜㈜', 약가: 119, 수수료율: 52, 최근수량: 10000, 최근월: '2026-11' },
              { 보험코드: '073001480', 품목명: '라베건정10mg', 규격: '', 제약사: '건일바이오팜㈜', 약가: 454, 수수료율: 58, 최근수량: 10000, 최근월: '2026-11' }
            ] };
            __CACHE.byClient['C0001'] = {
              '073001620': { lastQty: 10000, lastMonth: '2026-11', at: 2 },
              '073001480': { lastQty: 10000, lastMonth: '2026-11', at: 1 }
            };
            __CACHE.products['073001620'] = { 보험코드: '073001620', 품목명: '건피드정', 약가: 119, 수수료율: 52, at: 2 };
            __CACHE.products['073001480'] = { 보험코드: '073001480', 품목명: '라베건정10mg', 약가: 454, 수수료율: 58, at: 1 };
            var rows = rxBuildRows_(saved, quick, 'C0001', {});
            return [rows.length, rows.map(function (r) { return r.보험코드 + ':' + (r.saved ? 'saved' : 'no') + ':' + r.수량; }).join(',')].join('|');
          })()
        ''')
        built = built.decode() if isinstance(built, bytes) else built
        check(built == '2|073001620:saved:10000,073001480:saved:10000',
              '현장 상황에서 처방 목록이 두 줄로 정리되지 않았습니다: %s' % built)

        # 수량 입력칸: 지난 수량을 실제 입력값처럼 보이지 않게 ('지난 10,000' 안내)
        rowfn = extract_fn(js, 'renderRxRows')
        check(rowfn is not None, 'renderRxRows 를 추출하지 못했습니다')
        if rowfn:
            q = quickjs.Context()
            load_ing_ctx(q, js)
            q.eval('''
            var STATE = { rxClient: 'C0001', rxRows: [
              { 보험코드: '073001620', 품목명: '건피드정', 규격: '', 제약사: '건일바이오팜㈜',
                약가: 119, 수수료율: 52, 수량: '', 지난수량: 10000, 지난월: '2026-11', saved: false }
            ] };
            var __html = '';
            var document = { getElementById: function () { return { set innerHTML(v) { __html = v; } }; } };
            function esc(s) { return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;'); }
            function fmtNum(n) { return String(Math.round(Number(n || 0))).replace(/\\B(?=(\\d{3})+(?!\\d))/g, ','); }
            ''')
            q.eval(rowfn)
            q.eval('renderRxRows();')
            html = q.eval('__html')
            html = html.decode() if isinstance(html, bytes) else html
            check('placeholder="지난 10,000"' in html, '수량칸 안내가 지난 10,000 이 아닙니다: %s' % html[:200])
            check('value=""' in html, '수량칸이 빈 값으로 그려지지 않습니다')
            check('073001620' in html, '보험코드가 표시되지 않습니다')
    except ImportError:
        print('(quickjs 없음 — 보험코드 정규화 실행 검사 생략: pip install quickjs)')

    # 8) 월별 실적 셀 정리·합산 실행 검사 (직납 + 예상 처방)
    try:
        import quickjs
        ctx = quickjs.Context()
        load_ing_ctx(ctx, js)

        def q(v):
            return v.decode() if isinstance(v, bytes) else v

        ctx.eval('function fmtNum(n) { return String(Math.round(Number(n || 0))); }')
        for name in ['perfCell_', 'perfSumRows']:
            block = extract_fn(js, name)
            check(block is not None, '%s 를 추출하지 못했습니다' % name)
            if block:
                ctx.eval(block)
        # 예전 서버(처방 항목 없음) 응답 — 직납=매출합계, 예상 처방 0으로 채워야 함
        old = q(ctx.eval("JSON.stringify(perfCell_({ month: '2026-11', 매출합계: 1000000, 매출공급가: 909091, 매출건수: 2, 수금합계: 400000, 수금건수: 1 }))"))
        check('"직납매출":1000000' in old and '"예상처방금액":0' in old and '"예상총매출":1000000' in old,
              '예전 서버 응답에서 직납/예상 처방 채우기가 틀립니다: %s' % old)
        # 새 서버 응답 — 직납·예상 처방·예상 총매출이 각각 유지
        new = q(ctx.eval(
            "JSON.stringify(perfCell_({ month: '2026-11', 매출합계: 1000000, 직납매출: 1000000,"
            " 처방금액: 20000, 예상처방금액: 20000, 예상수수료: 11000, 총매출: 1020000, 예상총매출: 1020000,"
            " 총건수: 3, 수금합계: 400000 }))"))
        check('"직납매출":1000000' in new and '"예상처방금액":20000' in new and '"예상총매출":1020000' in new,
              '직납/예상 처방/예상 총매출이 유지되지 않습니다: %s' % new)
        # 담당자 두 명 합산 — 직납·예상 처방·예상 총매출·수금·미수금
        summed = q(ctx.eval(
            "JSON.stringify(perfSumRows(["
            "{ 담당자: 'A', 거래처수: 2, 미수금: 600000, 전월총매출: 0,"
            "  당월: { 직납매출: 1000000, 직납공급가: 909091, 직납건수: 1, 처방금액: 20000, 예상처방금액: 20000,"
            "          처방건수: 2, 예상수수료: 11000, 총매출: 1020000, 예상총매출: 1020000, 총건수: 3,"
            "          수금합계: 400000, 수금건수: 1 } },"
            "{ 담당자: 'B', 거래처수: 1, 미수금: 0, 전월총매출: 0,"
            "  당월: { 직납매출: 0, 처방금액: 2000, 예상처방금액: 2000, 처방건수: 1, 예상수수료: 800,"
            "          총매출: 2000, 예상총매출: 2000, 총건수: 1, 수금합계: 0 } }"
            "]))"))
        d = json.loads(summed)
        check(d['직납매출'] == 1000000, '합산 직납 오류: %s' % d['직납매출'])
        check(d['예상처방금액'] == 22000, '합산 예상 처방 오류: %s' % d['예상처방금액'])
        check(d['예상총매출'] == 1022000, '합산 예상 총매출 오류: %s' % d['예상총매출'])
        check(d['예상수수료'] == 11800, '합산 예상 수수료 오류: %s' % d['예상수수료'])
        check(d['수금합계'] == 400000 and d['미수금'] == 600000, '합산 수금·미수금 오류')
        check(d['전월총매출'] == 0 and d['전월대비'] is None, '전월 없을 때 전월비가 null 이 아닙니다')
    except ImportError:
        pass

    # 9) 월별 실적 화면 렌더 실행 검사 — 예상 표기·열 구성·서버 재배포 안내
    try:
        import quickjs
        names = ['perfCell_', 'perfAmt_', 'perfDeltaHtml', 'perfSumRows', 'perfMatrixMetric_',
                 'perfMatrixValue_', 'perfRxNote_', 'renderPerfPage', 'versionNum_', 'serverAtLeast_']
        blocks = [extract_fn(js, n) for n in names]
        missing = [n for n, b in zip(names, blocks) if b is None]
        check(not missing, '월별 실적 렌더 함수를 추출하지 못했습니다: %s' % missing)
        if not missing:
            def q(v):
                return v.decode() if isinstance(v, bytes) else v

            def render(server_version, metric):
                ctx = quickjs.Context()
                load_ing_ctx(ctx, js)
                ctx.eval("""
                var STATE = {
                  perfManager: '', perfShowClients: true, perfMatrixMetric: '%s',
                  serverVersion: '%s', perfData: null
                };
                var __html = '';
                var container = { set innerHTML(v) { __html = v; } };
                function esc(s) { return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;'); }
                function fmtNum(n) { return String(Math.round(Number(n || 0))).replace(/\\B(?=(\\d{3})+(?!\\d))/g, ','); }
                function renderActiveMenu() {}
                function togglePerfClients() {}
                function loadPerfModule() {}
                function changePerfMonth(v) {}
                function setPerfMonths(v) {}
                function setPerfManager(v) {}
                function setPerfMatrixMetric(v) {}
                """ % (metric, server_version))
                for b in blocks:
                    ctx.eval(b)
                ctx.eval("""
                STATE.perfData = {
                  targetMonth: '2026-11', monthEnd: '2026-11-30', isMaster: true,
                  months: ['2026-09', '2026-10', '2026-11'],
                  rxNote: '처방 실적은 익익월 정산 확정 전 입력 기준 예상치입니다.',
                  managers: [
                    { 담당자: '최충의', 거래처수: 3, 미수금: 600000, 전월총매출: 0, 전월대비: null,
                      당월: { 직납매출: 1000000, 직납공급가: 909091, 직납건수: 1, 처방금액: 20000,
                              예상처방금액: 20000, 처방건수: 2, 예상수수료: 11000,
                              총매출: 1020000, 예상총매출: 1020000, 총건수: 3, 수금합계: 400000, 수금건수: 1 },
                      series: [
                        { month: '2026-09', 직납매출: 0, 예상처방금액: 0, 예상총매출: 0, 예상수수료: 0, 수금합계: 0 },
                        { month: '2026-10', 직납매출: 500000, 예상처방금액: 0, 예상총매출: 500000, 예상수수료: 0, 수금합계: 0 },
                        { month: '2026-11', 직납매출: 1000000, 직납공급가: 909091, 직납건수: 1, 예상처방금액: 20000,
                          처방건수: 2, 예상수수료: 11000, 예상총매출: 1020000, 총건수: 3, 수금합계: 400000, 수금건수: 1 }
                      ] }
                  ],
                  totals: {
                    거래처수: 3, 미수금: 600000, 전월매출: 0, 전월총매출: 0, 전월대비: null,
                    당월: { 직납매출: 1000000, 직납공급가: 909091, 직납건수: 1, 예상처방금액: 20000,
                            처방건수: 2, 예상수수료: 11000, 예상총매출: 1020000, 총건수: 3,
                            수금합계: 400000, 수금건수: 1 },
                    series: [
                      { month: '2026-09', 직납매출: 0, 예상처방금액: 0, 예상총매출: 0, 예상수수료: 0, 수금합계: 0 },
                      { month: '2026-10', 직납매출: 500000, 예상처방금액: 0, 예상총매출: 500000, 예상수수료: 0, 수금합계: 0 },
                      { month: '2026-11', 직납매출: 1000000, 예상처방금액: 20000, 예상수수료: 11000, 예상총매출: 1020000, 수금합계: 400000 }
                    ]
                  },
                  clients: [
                    { 거래처코드: 'S001', 거래처명: '푸른정의원', 담당자: '최충의', 미수금: 600000,
                      직납매출: 1000000, 직납건수: 1, 예상처방금액: 20000, 처방건수: 2, 예상수수료: 11000,
                      예상총매출: 1020000, 총건수: 3, 수금합계: 400000, 수금건수: 1 }
                  ]
                };
                renderPerfPage(container);
                """)
                return q(ctx.eval('__html'))

            html_new = render('v1.8', 'total')
            for label in ['예상 총매출', '예상 처방금액', '예상 수수료', '직납 매출', '당월 수금 / 미수금',
                          '익익월', '1,020,000', '20,000', '11,000', 'table-wrap', 'perf-note']:
                check(label in html_new, '월별 실적 화면에 %s 가 없습니다' % label)
            check(html_new.count('table-wrap') >= 4, '월별 실적 표가 모두 table-wrap 으로 감싸지지 않았습니다')
            check('⚠️ 시트 서버' not in html_new, '서버가 최신인데 재배포 안내가 나옵니다')
            check('푸른정의원' in html_new, '병원별 표에 거래처가 없습니다')
            check('onchange="setPerfMatrixMetric' in html_new, '담당자×월 기준 선택기가 없습니다')
            check('담당자 × 월 예상 총매출' in html_new, '담당자×월 표 제목이 없습니다')

            html_old = render('v1.7', 'rx')
            check('⚠️ 시트 서버' in html_old and '재배포' in html_old,
                  '시트 서버가 예전일 때 재배포 안내가 없습니다')
            html_master = render('v1.8', 'direct')
            check('담당자 × 월 직납 매출(확정)' in html_master, '담당자×월 기준(직납) 표시가 없습니다')
    except ImportError:
        pass

    # 10) v1.10 — 매출(주사제 주문) / 수금 등록 화면 완전 분리
    check("id: 'order'" in js and 'renderOrderPage' in js and 'loadOrderModule' in js,
          '💉 주사제 주문 단독 메뉴가 없습니다')
    check("label: '주사제 주문'" in js, '메뉴 이름이 주사제 주문이 아닙니다')
    check("shortLabel: '주사주문'" in js, '모바일 메뉴 짧은 이름(주사주문)이 없습니다')
    check("id: 'collection'" in js and 'renderCollectionPage' in js and 'loadCollectionModule' in js,
          '💰 수금 등록 단독 메뉴가 없습니다')
    check("label: '수금 등록'" in js, '메뉴 이름이 수금 등록이 아닙니다')
    check("shortLabel: '수금'" in js, '모바일 메뉴 짧은 이름(수금)이 없습니다')
    check(order_ids[:len(expect_order)][-1] == 'docs', '사이드바 맨 마지막이 (마스터) 이메일 발송이력 · 설정이 아닙니다')
    # 매출·수금을 한 폼에 섮는 구분 드롭다운이 남아 있지 않은지
    check('tx-type' not in js and '매출 · 수금 등록' not in js and '매출·수금 등록' not in js,
          '매출·수금을 섮는 구분 드롭다운(또는 합쳐진 메뉴)이 남아 있습니다')
    check('toggleTxFields' not in js and 'sale-only' not in js and 'collect-only' not in js,
          '한 화면 안의 매출/수금 칸 숨기기(sale-only·collect-only)가 남아 있습니다')

    # 10-a) 💰 수금 등록 화면 — 품목·수량·부가세 칸 없이 날짜·거래처·입금액·비고만
    ce = re.search(r'function renderCollectionEntry\(el\)\s*\{(.*?)\n   \}', js, re.S)
    check(bool(ce), 'renderCollectionEntry 를 찾지 못했습니다')
    if ce:
        ce_body = ce.group(1)
        for bad in ['품목', '수량', '부가세', '단가', '보험코드', 'tx-qty', 'tx-price', 'tx-vat', 'tx-supply', 'tx-prodname', 'tx-inscode', 'tx-type']:
            check(bad not in ce_body, '수금 등록 화면에 %s 관련 칸이 남아 있습니다' % bad)
        for need in ['col-date', 'col-client-ac', 'col-amount', 'col-paytype', 'col-memo',
                     "recentTxTableHtml_('수금')", '최근 등록 수금 내역']:
            check(need in ce_body, '수금 등록 화면에 %s 가 없습니다' % need)
    check('function renderCollectionClientStrip' in js and '미수금' in js, '수금 화면 거래처 잔고(미수금) 표시가 없습니다')
    check("runServer('getClientDetail'" in js and 'loadCollectionBalance_' in js, '거래처 잔고 조회가 없습니다')
    check('fillCollectionBalance' in js and '미수금 전액 채우기' in js, '미수금 전액 채우기가 없습니다')

    # 10-b) 💉 주사제 주문 화면 — 수량·단가·공급가/부가세·합계 + 최근 매출 내역
    oe = re.search(r'function renderOrderEntry\(el\)\s*\{(.*?)\n   \}', js, re.S)
    check(bool(oe), 'renderOrderEntry 를 찾지 못했습니다')
    if oe:
        oe_body = oe.group(1)
        for need in ['tx-date', 'tx-client-ac', 'tx-product-ac', 'tx-prodname', 'tx-qty', 'tx-price',
                     'tx-supply', 'tx-vat', 'tx-total', 'tx-memo', "recentTxTableHtml_('매출')", '최근 등록 매출 내역']:
            check(need in oe_body, '주사제 주문 화면에 %s 가 없습니다' % need)
        check('수금' not in oe_body, '주사제 주문 화면에 수금 입력이 남아 있습니다')

    # 10-c) 주문·수금 → 서버 전송값이 Code.gs addTransaction 형식 그대로인지 (실행 검사)
    try:
        import quickjs
        ctx = quickjs.Context()
        load_ing_ctx(ctx, js)

        def qz(v):
            return v.decode() if isinstance(v, bytes) else v

        blocks = [extract_fn(js, n) for n in ['orderTxPayload_', 'collectionTxPayload_']]
        missing = [n for n, b in zip(['orderTxPayload_', 'collectionTxPayload_'], blocks) if b is None]
        check(not missing, '전송값 함수를 추출하지 못했습니다: %s' % missing)
        if not missing:
            for b in blocks:
                ctx.eval(b)
            cl = "{ 거래처코드: 'S001', 거래처명: '수아의원' }"
            sale = json.loads(qz(ctx.eval(
                "JSON.stringify(orderTxPayload_(%s, { 날짜: '2026-11-28', 보험코드: '642100120', 품목명: ' 아다셀주 ', "
                "수량: '3', 단가: '10000', 공급가액: '30000', 부가세: '3000', 합계금액: '33000', 수금유형: '어음', 비고: ' 납품 ' }))" % cl)))
            check(sale['구분'] == '매출', '주문 전송값 구분이 매출이 아닙니다: %s' % sale['구분'])
            check(sale['품목명'] == '아다셀주' and sale['수량'] == 3 and sale['단가'] == 10000,
                  '주문 전송값 품목·수량·단가가 다릅니다: %s' % sale)
            check(sale['공급가액'] == 30000 and sale['부가세'] == 3000 and sale['합계금액'] == 33000,
                  '주문 전송값 금액이 다릅니다: %s' % sale)
            check(sale['수금유형'] == '' and sale['비고'] == '납품', '주문 전송값의 수금유형·비고가 다릅니다: %s' % sale)
            check(sale['거래처코드'] == 'S001' and sale['거래처명'] == '수아의원', '주문 전송값 거래처가 다릅니다')

            coll = json.loads(qz(ctx.eval(
                "JSON.stringify(collectionTxPayload_(%s, { 날짜: '2026-11-28', 입금액: '500000', 수금유형: '어음', 비고: '만기 12/31' }))" % cl)))
            check(coll['구분'] == '수금', '수금 전송값 구분이 수금이 아닙니다: %s' % coll['구분'])
            check(coll['합계금액'] == 500000 and coll['공급가액'] == 500000 and coll['부가세'] == 0,
                  '수금 전송값 금액(합계=공급가, 부가세 0)이 Code.gs 형식과 다릅니다: %s' % coll)
            check(coll['품목명'] == '' and coll['수량'] == 0 and coll['단가'] == 0 and coll['보험코드'] == '',
                  '수금 전송값에 품목·수량이 섮여 있습니다: %s' % coll)
            check(coll['수금유형'] == '어음' and coll['비고'] == '만기 12/31', '수금 전송값 수금유형·비고가 다릅니다: %s' % coll)
            check(coll['거래처코드'] == 'S001', '수금 전송값 거래처가 다릅니다')
            # 수금유형을 고르지 않으면 기존 서버 기본값(계좌)
            coll2 = json.loads(qz(ctx.eval(
                "JSON.stringify(collectionTxPayload_(%s, { 날짜: '2026-11-28', 입금액: 1000 }))" % cl)))
            check(coll2['수금유형'] == '계좌', '수금유형 기본값이 계좌가 아닙니다: %s' % coll2['수금유형'])
    except ImportError:
        print('(quickjs 없음 — 주문/수금 전송값 실행 검사 생략: pip install quickjs)')

    # 10-d) 두 등록 함수가 각각 addTransaction 으로 보내는지 · 버튼이 정의된 함수를 부르는지
    for name, kind in [('submitOrderTx', '매출'), ('submitCollectionTx', '수금')]:
        fn = re.search(r'async function %s\(\)\s*\{(.*?)\n   \}' % name, js, re.S)
        check(bool(fn) and "runServer('addTransaction'" in fn.group(1),
              '%s 가 addTransaction 으로 등록하지 않습니다' % name)
    check('onclick="submitOrderTx()"' in js, '주문 화면 등록 버튼이 submitOrderTx 를 부르지 않습니다')
    check('onclick="submitCollectionTx()"' in js, '수금 화면 등록 버튼이 submitCollectionTx 를 부르지 않습니다')
    check('function collectionFromDetail' in js and "switchMenu('collection')" in js,
          '거래처 상세 → 수금 등록 이동이 없습니다')
    tv = re.search(r'function renderTurnoverPage\(container\)\s*\{(.*?)\n   \}', js, re.S)
    check(bool(tv), 'renderTurnoverPage 를 찾지 못했습니다')
    if tv:
        check('매출 / 수금 등록' not in tv.group(1), '주문 · 회전일 관리에 매출/수금 탭이 남아 있습니다')
        check('회전일 대시보드' in tv.group(1) and '제품마스터' in tv.group(1),
              '주문 · 회전일 관리에 회전일 대시보드·제품마스터 탭이 남아 있지 않습니다')
    for name in ['orderFromDetail', 'injectSendToOrder']:
        body_fn = re.search(r'function %s\([^)]*\)\s*\{(.*?)\n   \}' % name, js, re.S)
        check(bool(body_fn) and "switchMenu('order')" in body_fn.group(1),
              '%s 가 주사제 주문 메뉴로 이동하지 않습니다' % name)
    check('recentTxTableHtml_' in js and 'recent-tx-box' in js, '최근 등록 내역 박스가 없습니다')
    check('function renderRecentTxBox_' in js and 'function recentTxTableHtml_' in js, '최근 내역 렌더 함수가 없습니다')

    # 10-e) 모바일 하단 바 — 항목 11개라 가로 스크롤 · 글씨 짜부라짐 방지
    page = open(INDEX, encoding='utf-8').read()   # html 은 위쪽 실행 검사에서 덮어써졌을 수 있음
    nav_i = page.find('.mobile-nav {')
    mnav_block = page[nav_i:nav_i + 900] if nav_i >= 0 else ''
    check(nav_i >= 0 and 'overflow-x: auto' in mnav_block, '모바일 하단 바(.mobile-nav)에 가로 스크롤이 없습니다')
    btn_i = page.find('.mnav-btn {')
    mb_block = page[btn_i:btn_i + 400] if btn_i >= 0 else ''
    check(btn_i >= 0 and ('flex: 1 0 auto' in mb_block or 'flex-shrink: 0' in mb_block) and 'min-width' in mb_block,
          '모바일 메뉴 항목이 찌그러지지 않게 flex-shrink/최소폭 설정이 없습니다')
    check('scrollIntoView' in js and "querySelector('.mnav-btn.active')" in js,
          '하단 바에서 지금 메뉴가 보이게 맞추는 처리가 없습니다')

    # 10-f) 두 화면을 실제로 그려 보기 — 템플릿·필터·버튼 연결 확인
    try:
        import quickjs
        names = ['renderOrderEntry', 'renderCollectionEntry', 'recentTxTableHtml_',
                 'clientAcItems', 'collectionClientAcItems_', 'activeClients', 'productAcItems']
        blocks = [extract_fn(js, n) for n in names]
        missing = [n for n, b in zip(names, blocks) if b is None]
        check(not missing, '화면 렌더 함수를 추출하지 못했습니다: %s' % missing)
        if not missing:
            ctx = quickjs.Context()
            load_ing_ctx(ctx, js)
            ctx.eval("""
              var STATE = { today: '2026-11-28', orderClientCode: '', collectionClientCode: '',
                            collectionBalances: {}, pendingOrderProduct: null, products: [],
                            clients: [{ 거래처코드: 'S001', 거래처명: '수아의원', 사용여부: 'Y',
                                        유통구분: '직납', 진료과: '내과', 담당자: '최충의' }],
                            recentTxs: [
                              { _rowIndex: 5, 날짜: '2026-11-28', 구분: '매출', 거래처명: '수아의원',
                                품목명: '아다셀주', 수량: 3, 합계금액: 33000, 비고: '' },
                              { _rowIndex: 6, 날짜: '2026-11-27', 구분: '수금', 거래처명: '수아의원',
                                수금유형: '어음', 합계금액: 500000, 비고: '만기 12/31' }
                            ] };
              var __el = { innerHTML: '' };
              var document = { getElementById: function () { return null; } };
              function esc(s) { return String(s == null ? '' : s); }
              function fmtNum(n) { return String(Math.round(Number(n || 0))); }
              function createAutocomplete() { return null; }
              function showToast() {}
              function renderActiveMenu() {}
            """)
            for b in blocks:
                ctx.eval(b)

            def qh(v):
                return v.decode() if isinstance(v, bytes) else v

            ctx.eval('renderOrderEntry(__el);')
            sale_html = qh(ctx.eval('__el.innerHTML'))
            for need in ['tx-date', 'tx-client-ac', 'tx-product-ac', 'tx-prodname', 'tx-qty', 'tx-price',
                         'tx-supply', 'tx-vat', 'tx-total', 'tx-memo', 'submitOrderTx()', '최근 등록 매출 내역']:
                check(need in sale_html, '그린 주사제 주문 화면에 %s 가 없습니다' % need)
            check('col-amount' not in sale_html and 'submitCollectionTx' not in sale_html,
                  '주사제 주문 화면에 수금 칸이 섞여 있습니다')
            check('아다셀주' in sale_html, '주사제 주문 화면 최근 매출 내역이 비어 있습니다')
            check('만기 12/31' not in sale_html, '주사제 주문 화면에 수금 건이 섞여 나옵니다')

            ctx.eval('renderCollectionEntry(__el);')
            col_html = qh(ctx.eval('__el.innerHTML'))
            for need in ['col-date', 'col-client-ac', 'col-paytype', 'col-amount', 'col-memo',
                         'submitCollectionTx()', '최근 등록 수금 내역']:
                check(need in col_html, '그린 수금 화면에 %s 가 없습니다' % need)
            for bad in ['tx-qty', 'tx-vat', 'tx-product-ac', 'tx-prodname', 'tx-supply']:
                check(bad not in col_html, '수금 화면에 %s 칸이 남아 있습니다' % bad)
            check('만기 12/31' in col_html, '수금 화면 최근 수금 내역이 비어 있습니다')
            check('아다셀주' not in col_html, '수금 화면에 매출 건이 섞여 나옵니다')
    except ImportError:
        print('(quickjs 없음 — 화면 렌더 실행 검사 생략: pip install quickjs)')

    # 10-g) v1.11 — 💉 주사제 셋팅을 💉 주사제 주문 메뉴 안 탭으로 이동, 🧭 처방 셋팅은 경구제 전용
    rp = re.search(r'function renderOrderPage\(container\)\s*\{(.*?)\n   \}', js, re.S)
    check(bool(rp), 'renderOrderPage 를 찾지 못했습니다')
    if rp:
        rp_body = rp.group(1)
        check('orderTabBar_()' in rp_body, '주사제 주문 화면에 탭 바가 없습니다')
        check("STATE.orderTab === 'inject' ? 'inject' : 'entry'" in rp_body, '주사제 주문 탭 상태 처리가 없습니다')
        check('renderInjectPanelHtml_()' in rp_body, '주사제 주문 주사제 셋팅 탭이 주사제 셋팅 화면을 그리지 않습니다')
        check('renderOrderEntry(body)' in rp_body, '주사제 주문 매출 등록 탭이 폼을 그리지 않습니다')
    gp = re.search(r'function renderGuidePage\(container\)\s*\{(.*?)\n   \}', js, re.S)
    check(bool(gp), 'renderGuidePage 를 찾지 못했습니다')
    if gp:
        gp_body = gp.group(1)
        check('renderInjectPanelHtml_' not in gp_body and 'inj' not in re.findall(r"renderInject\w+", gp_body),
              '처방 셋팅 화면에 주사제 셋팅이 남아 있습니다')
        check('renderGuideOralHtml_()' in gp_body, '처방 셋팅 화면이 경구제 전용 화면을 그리지 않습니다')
        check('guideHospitalBarHtml_()' in gp_body, '처방 셋팅 담을 병원 줄이 없습니다')
    lm = re.search(r'async function loadGuideModule\(\)\s*\{(.*?)\n   \}', js, re.S)
    if lm:
        check('loadInject' not in lm.group(1), '처방 셋팅 진입에서 주사제 자료를 불러오고 있습니다')
        check('loadCoverageNotes' in lm.group(1), '처방 셋팅이 급여·삭감 가이드를 불러오지 않습니다')
    om = re.search(r'async function loadOrderModule\(\)\s*\{(.*?)\n   \}', js, re.S)
    if om:
        check('injData' in om.group(1) and 'injProto' in om.group(1), '주사제 주문 진입에서 주사제 셋팅 자료를 불러오지 않습니다')

    # 두 탭을 실제로 그려 보기 (quickjs)
    try:
        import quickjs
        ctx = quickjs.Context()
        load_ing_ctx(ctx, js)
        ctx.eval('''
          var STATE = { orderTab: 'entry', orderClientCode: '', injPay: '', injMode: 'maxrate',
                        guideIngQ: '', guideIngKey: '', guideIngData: null, guideIngOpen: {},
                        guideIngLoading: false, guidePick: {},
                        injLimit: 20, injCat: '', injQuery: '', injProtoQuery: '', injData: null,
                        injProto: null, injSelected: {}, clients: [], guideDept: '', coverage: null };
          var document = { getElementById: function () { return null; } };
          function esc(s) { return String(s == null ? '' : s); }
          function fmtNum(n) { return String(Math.round(Number(n || 0))); }
          function payTypeBadge() { return ''; }
          function findClient() { return null; }
          function guideMakerOptionsHtml_() { return ''; }
          function renderGuideMakerBar() {}
          function renderGuideMakerResult() {}
          function loadInjectGuide() {} function loadInjectProtocols() {}
          function loadCoverageNotes() {} function renderGuideDeptChips() {} function renderGuideBody() {}
          function v14NoticeHtml_() { return ''; }
          function renderActiveMenu() {}
          function renderGuidePicked() {}      // v1.21 — 담은 품목 목록은 별도 검사에서 그립니다
        ''')
        names = ['orderTabBar_', 'orderInjectStripHtml_', 'injCautionsHtml_', 'renderInjectPanelHtml_',
                 'renderInjectBody', 'renderInjectRecommend', 'renderInjectProtocols', 'renderInjectCards',
                 'renderOrderPage', 'renderGuidePage', 'renderGuideOralHtml_', 'guideHospitalBarHtml_',
                 'guideIngSearchCardHtml_', 'renderGuideIngResult', 'guideIngResultHtml_',
                 'guideIngGroupHtml_', 'guideIngGroupKey_']
        blocks = [extract_fn(js, n) for n in names]
        missing = [n for n, b in zip(names, blocks) if b is None]
        check(not missing, '탭 렌더 함수를 추출하지 못했습니다: %s' % missing)
        if not missing:
            for b in blocks:
                ctx.eval(b)

            def qh2(v):
                return v.decode() if isinstance(v, bytes) else v

            ctx.eval('var __c = { innerHTML: "" }; renderOrderPage(__c);')
            entry_html = qh2(ctx.eval('__c.innerHTML'))
            check('💳 주문(매출) 등록' in entry_html and '💉 주사제 셋팅 (프로토콜·배합금기)' in entry_html,
                  '주사제 주문 화면에 두 탭 버튼이 없습니다')
            check('id="turnover-body"' in entry_html, '주문(매출) 등록 탭이 폼 자리를 그리지 않습니다')
            check('inj-protocol' not in entry_html, '주문(매출) 등록 탭에 주사제 셋팅이 섞여 있습니다')
            check('subtab active" onclick="switchOrderTab(\'entry\')' in entry_html,
                  '주문(매출) 등록 탭이 기본 선택이 아닙니다')

            ctx.eval("STATE.orderTab = 'inject'; renderOrderPage(__c);")
            inj_html = qh2(ctx.eval('__c.innerHTML'))
            for need in ['inj-cautions', 'inj-protocol', 'inj-recommend', 'inj-body', 'inj-cards']:
                check(need in inj_html, '주사제 셋팅 탭에 %s 가 없습니다' % need)
            check('id="turnover-body"' not in inj_html, '주사제 셋팅 탭에 매출 등록 폼이 남아 있습니다')
            check('subtab active" onclick="switchOrderTab(\'inject\')' in inj_html,
                  '주사제 셋팅 탭이 선택 상태로 그려지지 않습니다')

            ctx.eval("STATE.orderTab = 'entry'; var __g = { innerHTML: '' }; renderGuidePage(__g);")
            guide_html = qh2(ctx.eval('__g.innerHTML'))
            check('진료과 선택' in guide_html and '경구제(원외처방) 전용' in guide_html,
                  '처방 셋팅이 경구제 전용 화면이 아닙니다')
            check('inj-protocol' not in guide_html and 'inj-cautions' not in guide_html,
                  '처방 셋팅 화면에 주사제 셋팅이 섞여 있습니다')
            check('switchGuideTab' not in guide_html and '2탭' not in guide_html, '처방 셋팅에 탭 전환 바가 남아 있습니다')
    except ImportError:
        print('(quickjs 없음 — 주사제 주문 두 탭 실행 검사 생략: pip install quickjs)')

    # 10-a) 접기·펼치기
    check('function toggleInjCautions' in js and 'injCautionsOpen' in js, '배합금기 접기/펼치기가 없습니다')
    check('function toggleCoverageGuide' in js and 'coverageOpen' in js, '급여·삭감 가이드 접기/펼치기가 없습니다')
    check('function toggleInjProtoGroup' in js and 'injProtoOpen' in js and 'function setInjProtoAll' in js,
          '프로토콜 목적별 아코디언이 없습니다')
    check('collapse-caret' in js and '펼치기 ▼' in js and '접기 ▲' in js, '접기/펼치기 버튼 표기가 없습니다')
    check('injWarnHtml_' in js and '선택한 조합에 배합·혼합 주의' in js,
          '품목 체크 시 배합금기 경고 배너가 없습니다')
    check('검색어와 맞는 그룹을 펼쳤습니다' in js, '프로토콜 검색 자동 펼침 표시가 없습니다')

    # 10-b) 접기·펼치기 실행 검사 (기본은 접힘 · 1줄 요약)
    try:
        import quickjs
        ctx = quickjs.Context()
        load_ing_ctx(ctx, js)
        ctx.eval('function esc(s) { return String(s == null ? "" : s); }')
        ctx.eval('function fmtNum(n) { return String(Math.round(Number(n || 0))); }')
        ctx.eval('function payTypeBadge() { return ""; }')
        ctx.eval('function injectSendToOrder() {}')
        ctx.eval('''
          var STATE = { injCautionsOpen: false, injProtoOpen: {}, injProtoQuery: '', coverageOpen: false,
                        coverage: null, coverageCat: '', injProto: null };
          var __els = {};
          var document = { getElementById: function (id) {
            if (!__els[id]) __els[id] = { _html: '', set innerHTML(v) { this._html = v; }, get innerHTML() { return this._html; } };
            return __els[id];
          } };
        ''')
        for name in ['injCautionsHtml_', 'toggleInjCautions', 'renderCoverageCard', 'toggleCoverageGuide',
                     'renderInjectProtocols', 'toggleInjProtoGroup', 'setInjProtoAll', 'renderInjectCards']:
            block = extract_fn(js, name)
            check(block is not None, '%s 를 추출하지 못했습니다' % name)
            if block:
                ctx.eval(block)

        def qv(v):
            return v.decode() if isinstance(v, bytes) else v

        ctx.eval('''
          STATE.injProto = {
            cautions: [
              { 케이스: '태반주사(자하거추출물)', 주의: '정맥 믹스 금지 — 허가사항 확인', 출처: '실무 기준' },
              { 케이스: '푸르설티아민(마늘주사) + 알칼리성 주사제', 주의: '같은 백 혼합 금지', 출처: '실무 기준' },
              { 케이스: '글루타치온 + 고용량 비타민C', 주의: '투여일 나누기', 출처: 'RNT p14' }
            ],
            protocols: [
              { 분류: '수액 기본', 케이스: '생리식염수 고르기', 성분: '염화나트륨 0.9%', 참고제품: '중외', 출처: 'a', 우리제품: [] },
              { 분류: '수액 기본', 케이스: '5% 포도당 고르기', 성분: '포도당', 참고제품: '중외', 출처: 'a', 우리제품: [] },
              { 분류: '통증·해열', 케이스: '감기 몸살', 성분: '아세트아미노펜', 참고제품: '아세트', 출처: 'b', 우리제품: [] }
            ],
            cards: []
          };
        ''')
        closed = qv(ctx.eval('injCautionsHtml_()'))
        check('펼치기 ▼' in closed, '배합금기가 기본으로 펼쳐져 있습니다')
        check('(3건)' in closed, '배합금기 건수가 제목에 없습니다')
        check('태반주사(자하거추출물)' in closed, '접힌 상태의 1줄 요약이 없습니다')
        check('정맥 믹스 금지' not in closed, '접힌 상태인데 배합금기 상세가 그대로 보입니다')
        opened = qv(ctx.eval('STATE.injCautionsOpen = true; injCautionsHtml_()'))
        check('정맥 믹스 금지' in opened and '접기 ▲' in opened, '배합금기를 펼치면 상세가 나오지 않습니다')

        ctx.eval('''
          STATE.coverage = {
            items: [
              { 구분: '당뇨', 항목: 'HbA1c 기준', 내용: '당뇨 1·2·3제 기준 확인', 근거: '고시' },
              { 구분: '용량', 항목: '상한 초과', 내용: '1일 상한 초과 시 삭감', 근거: '고시' }
            ],
            categories: [ { 구분: '당뇨', 개수: 1 }, { 구분: '용량', 개수: 1 } ]
          };
          STATE.coverageOpen = false; STATE.coverageCat = '';
          renderCoverageCard();
        ''')
        cov_closed = qv(ctx.eval('__els["guide-coverage"].innerHTML'))
        check('펼치기 ▼' in cov_closed and '당뇨' in cov_closed, '급여·삭감 가이드가 접힌 상태로 안 나옵니다')
        check('HbA1c' not in cov_closed, '접힌 급여 가이드에 표 내용이 그대로 보입니다')
        ctx.eval('toggleCoverageGuide();')
        cov_open = qv(ctx.eval('__els["guide-coverage"].innerHTML'))
        check('HbA1c' in cov_open and '접기 ▲' in cov_open, '급여·삭감 가이드를 펼치면 표가 나오지 않습니다')

        # 프로토콜 — 기본은 그룹 헤더만, 검색하면 매칭 그룹 자동 펼침
        ctx.eval('STATE.injProtoQuery = ""; STATE.injProtoOpen = {}; renderInjectProtocols();')
        p_closed = qv(ctx.eval('__els["inj-protocol"].innerHTML'))
        check('수액 기본' in p_closed and '통증·해열' in p_closed, '프로토콜 그룹 헤더가 없습니다')
        check('생리식염수 고르기' not in p_closed, '기본 상태에서 프로토콜이 전부 펼쳐져 있습니다')
        check(p_closed.count('펼치기 ▼') == 2, '접힌 그룹마다 펼치기 버튼이 없습니다: %d' % p_closed.count('펼치기 ▼'))
        ctx.eval('toggleInjProtoGroup("통증·해열");')
        p_one = qv(ctx.eval('__els["inj-protocol"].innerHTML'))
        check('감기 몸살' in p_one, '그룹을 눌러도 펼쳐지지 않습니다')
        check('생리식염수 고르기' not in p_one, '다른 그룹까지 같이 펼쳐졌습니다')
        ctx.eval('STATE.injProtoQuery = "숙취"; STATE.injProtoOpen = {}; renderInjectProtocols();')
        p_search = qv(ctx.eval('__els["inj-protocol"].innerHTML'))
        check('감기 몸살' in p_search and '생리식염수 고르기' in p_search,
              '검색어가 있을 때 매칭 그룹이 자동으로 펼쳐지지 않습니다')
        ctx.eval('STATE.injProtoQuery = ""; STATE.injProtoOpen = {}; renderInjectProtocols();')
        p_back = qv(ctx.eval('__els["inj-protocol"].innerHTML'))
        check('감기 몸살' not in p_back, '검색어를 비우면 다시 접힌 상태로 돌아가지 않습니다')
        ctx.eval('setInjProtoAll(true);')
        p_all = qv(ctx.eval('__els["inj-protocol"].innerHTML'))
        check('감기 몸살' in p_all and '생리식염수 고르기' in p_all, '모두 펼치기가 동작하지 않습니다')
        ctx.eval('setInjProtoAll(false);')
        p_none = qv(ctx.eval('__els["inj-protocol"].innerHTML'))
        check('감기 몸살' not in p_none, '모두 접기가 동작하지 않습니다')
    except ImportError:
        print('(quickjs 없음 — 접기·펼치기 실행 검사 생략: pip install quickjs)')

    # 11) v1.12 — 선택 담기 · 금액 '원' · 거래원장 회전일 · 원장님 안내용 출력/PDF
    raw = open(INDEX, encoding='utf-8').read()   # html 은 위쪽 실행 검사에서 바뀔 수 있어 다시 읽음
    check('function fmtWon' in js, "금액 '원' 표기 헬퍼(fmtWon)가 없습니다")
    check('makerOf_' in js and 'makerCellHtml_' in js, '제약사 공통 표기 헬퍼가 없습니다')
    # v1.15 — 제약사 칸에는 실제 제조사. 페이서(써플라이)는 취급 도매상으로만 표기합니다.
    check("const LEGACY_MAKER_LABELS = ['자사(휴온스·페이서)', '자사(페이서)', '자사'];" in js,
          '예전 자사(페이서) 표기를 제약사로 쓰지 않는 규칙이 없습니다')
    check("const DISTRIBUTOR_LABEL = '페이서써플라이(주)';" in js, '취급 도매상(페이서써플라이) 표기가 없습니다')
    check('PRODUCT_MAKER_BY_CODE_' in js and 'builtinMakerOf_' in js, '앱 내장 제약사(실제 제조사) 목록이 없습니다')
    # 2026-11-28 — 이엘파마품목에서 주사제로 넘어오는 2품목도 '제약사 미확인'이 아니어야 합니다
    for code, maker in [('648508321', '하이알플렉스주'), ('648507821', '하이알원샷주')]:
        check('"%s": "신풍제약(이엘파마)"' % code in js, '앱 내장 제약사 목록에 %s(%s)이 없습니다' % (maker, code))
    check('<th>보험코드</th><th>제품명</th><th>성분</th><th>제약사</th>' in js, '제품마스터 목록에 제약사 열이 없습니다')
    check("'<td>' + makerCellHtml_(p, 'inject') + '</td>'" in js, '제품마스터 목록 행에 제약사 값이 없습니다')
    check('return SELF_MAKER_LABEL' not in js and 'const SELF_MAKER_LABEL' not in js,
          '아직 자사(페이서)를 제약사 기본값으로 씁니다')
    # 11-a) 처방 셋팅 — 품목 체크 + 선택 항목 담기
    for need in ['guidePick', 'guideAddSelected', 'guideToggleProduct', 'guideToggleIngredient',
                 'guideBulkAddLabel_', 'guidePickCodes_', 'guideSyncPickUI_', 'data-guide-pick']:
        check(need in js, '처방 셋팅 선택 담기에 %s 가 없습니다' % need)
    check('💊 선택 항목 담기' in js, '처방 셋팅에 선택 항목 담기 버튼이 없습니다')
    check('data-guide-ing' in js and 'data-guide-codes' in js, '성분 체크가 품목 체크와 함께 움직이지 않습니다')
    check("'✓ 담김'" in js and 'guideAddItem' in js, '개별 + 담기(✓ 담김)가 남아 있지 않습니다')
    # 11-b) 주사제 셋팅 — 선택 항목 매출 등록 (여러 품목 한 번에)
    for need in ['pendingOrderProducts', 'pendingOrderCardHtml_', 'submitPendingOrderProducts',
                 'injectSendSelectedToOrder', 'injBulkOrderLabel_', 'mergePendingOrderProducts_',
                 'pendingOrderRowAmount_', 'changePendingOrderQty']:
        check(need in js, '주사제 셋팅 일괄 매출 등록에 %s 가 없습니다' % need)
    check('🛒 선택 항목 매출 등록' in js, '주사제 셋팅에 선택 항목 매출 등록 버튼이 없습니다')
    check('💾 선택 품목 매출 일괄 등록' in js, '담은 품목 일괄 등록 버튼이 없습니다')
    check('🛒 주사제 셋팅에서 담은 품목' in js, '주문 화면에 담은 품목 카드가 없습니다')
    check('🛒 매출 등록' in js, '개별 매출 등록 버튼이 남아 있지 않습니다')
    # 11-c) 금액 '원' — 금액 열에 '원'이 빠진 곳이 없는지 (핵심 화면)
    for label, pattern in [
        ('거래원장 이월잔액', "fmtNum(d.carryOver) + '원"),
        ('거래명세서 단가', "fmtNum(s.단가) + '원"),
        ('월별 실적 합계 수금', "fmtNum(sum.수금합계) + '원"),
        ('처방 요약 처방금액', "fmtNum(b.처방금액) + '원"),
        ('처방 상세 예상수수료', "fmtNum(r.예상수수료) + '원"),
    ]:
        check(pattern in js, '금액 원 표기가 빠졌습니다: %s' % label)
    check("const main = has ? fmtNum(v) + '원'" in js, '월별 실적 금액 셀에 원 표기가 없습니다')
    # 11-d) 거래원장 · 명세서 — 회전일 함께 표기
    for need in ['ledgerTurnoverHtml_', 'loadLedgerTurnover_', 'ledgerTurnoverText_', 'ledgerTurnover']:
        check(need in js, '거래원장 회전일 표기에 %s 가 없습니다' % need)
    check("'회전일 ' + (days >= 999" in js, '회전일 표기 문구가 없습니다')
    check('경고기준 ' in js, '회전일 경고기준 표기가 없습니다')
    # 11-e) 출력/PDF — 처방 셋팅 · 주사제 셋팅(원장님 안내용) + 처방전 입력
    for need in ['printGuideSheet', 'printInjectSheet', 'printRxSheet', 'printDocHtml_',
                 'guidePrintRows_', 'injectPrintRows_', 'rxPrintRows_', 'printStamp_']:
        check(need in js, '출력/PDF 기능에 %s 가 없습니다' % need)
    check('🖨️ 원장님 안내용 출력 / PDF' in js, '원장님 안내용 출력 버튼이 없습니다')
    # v1.13 — 처방전 입력 출력을 원장님용 / 내부용 두 가지로 분리
    check('🖨️ 원장님용 출력 / PDF' in js, '처방전 입력 원장님용 출력 버튼이 없습니다')
    check('🖨️ 내부용 출력 / PDF' in js, '처방전 입력 내부용 출력 버튼이 없습니다')
    check("printRxSheet(\\'owner\\')" in js and "printRxSheet(\\'internal\\')" in js,
          '처방전 출력 버튼이 원장님용/내부용을 구분해 부르지 않습니다')
    check('🖨️ 출력 / PDF 저장' not in js, '처방전 입력에 예전 단일 출력 버튼(출력 / PDF 저장)이 남아 있습니다')
    for fn_name in ['printGuideSheet', 'printInjectSheet']:
        body = re.search(r'function %s\(\)\s*\{(.*?)\n   \}' % fn_name, js, re.S)
        check(bool(body), '%s 를 찾지 못했습니다' % fn_name)
        if body:
            check('수수료율' not in body.group(1) and '예상수수료' not in body.group(1),
                  '%s 출력물에 내부 수수료율이 들어갑니다' % fn_name)
    rx_body = re.search(r'function printRxSheet\([^)]*\)\s*\{(.*?)\n   \}', js, re.S)
    check(bool(rx_body) and '예상수수료' in rx_body.group(1), '처방전 내부용 출력물에 예상수수료가 없습니다')
    check(bool(rx_body) and "owner ? ''" in rx_body.group(1), '처방전 원장님용에서 수수료 열을 빼는 분기가 없습니다')
    check('#print-area thead' in raw and 'page-break-inside: avoid' in raw, '인쇄용 페이지 나눔 스타일이 없습니다')
    check('window.print()' in js, 'window.print() 호출이 없습니다')

    # 12) v1.12 실행 검사 — 금액 '원' · 제약사 · 선택 담기 · 일괄 매출 · 회전일 · 출력물
    try:
        import quickjs

        def q12(v):
            return v.decode() if isinstance(v, bytes) else v

        def load(ctx, names, label):
            blocks = []
            for n in names:
                b = extract_fn(js, n)
                check(b is not None, '%s: %s 를 추출하지 못했습니다' % (label, n))
                blocks.append(b)
            if any(b is None for b in blocks):
                return False
            for b in blocks:
                ctx.eval(b)
            return True

        # (A) 금액 '원' · 제약사 표기 규칙
        ctx = quickjs.Context()
        load_ing_ctx(ctx, js)
        ctx.eval('var STATE = { products: [], guideProductCache: {}, settings: { 부가세율: "10" } };')
        check(load_maker_ctx(ctx, js), '앱 내장 제약사 목록·판정 함수를 실행 문맥에 넣지 못했습니다')
        ctx.eval('function esc(s) { return String(s == null ? "" : s); }')
        if load(ctx, ['fmtNum', 'fmtWon', 'rxCodeNorm_', 'rxCodeKey_', 'makerFromName_', 'makerOf_',
                      'makerCellHtml_', 'perfAmt_', 'pendingOrderRowAmount_'], '금액/제약사'):
            check(q12(ctx.eval('fmtWon(1234567)')) == '1,234,567원', "fmtWon 천단위 오류: %s" % q12(ctx.eval('fmtWon(1234567)')))
            check(q12(ctx.eval('fmtWon(0)')) == '0원', "0원 표기 오류: %s" % q12(ctx.eval('fmtWon(0)')))
            check(q12(ctx.eval('fmtWon("-")')) == '-', '대시(-)는 그대로 두어야 합니다')
            check(q12(ctx.eval('fmtWon("12,000원")')) == '12,000원', "'원'이 중복됩니다")
            check('1,020,000원' in q12(ctx.eval('perfAmt_(1020000, 3)')), '월별 실적 금액에 원이 없습니다')
            check('0원' in q12(ctx.eval('perfAmt_(0)')), '금액 0 이 0원으로 표기되지 않습니다')
            check(q12(ctx.eval("makerOf_({ 품목명: '베아셋정', 제약사: '대웅바이오' })")) == '대웅바이오',
                  '제약사 값이 그대로 표기되지 않습니다')
            check(q12(ctx.eval("makerOf_({ 품목명: '아다셀주' }, 'inject')")) == '제약사 미확인',
                  '제약사를 모를 때 자사(페이서)로 채우면 안 됩니다')
            check(q12(ctx.eval("makerOf_({ 품목명: '코러스세프트리악손나트륨주/1g', 보험코드: '647202372' }, 'inject')")) == '한국코러스',
                  '앱 내장 목록에서 실제 제조사를 찾지 못합니다')
            check(q12(ctx.eval("makerOf_({ 품목명: '코러스세프트리악손나트륨주/1g', 보험코드: '647202372', 제약사: '자사(페이서)' }, 'inject')")) == '한국코러스',
                  '예전 자사(페이서) 값이 실제 제조사를 가립니다')
            check(q12(ctx.eval("makerOf_({ 품목명: '스카이지플러스겔/15g', 보험코드: '02627' }, 'inject')")) == '성지메디칼',
                  '도매 리스트의 기타제조사 항목이 실제 제조사로 채워지지 않습니다')
            check(q12(ctx.eval("makerOf_({ 품목명: '대웅바이오 베아셋정' })")) == '대웅바이오',
                  '품목명 앞 제약사명을 살리지 못합니다')
            check(q12(ctx.eval("makerOf_({ 품목명: '베아셋정' })")) == '제약사 미확인',
                  '제약사 미상일 때 - 대신 안내가 없습니다')
            amt = json.loads(q12(ctx.eval('JSON.stringify(pendingOrderRowAmount_({ 수량: 3, 기준단가: 10000 }))')))
            check(amt['공급가액'] == 30000 and amt['부가세'] == 3000 and amt['합계'] == 33000,
                  '담은 품목 금액 계산이 다릅니다: %s' % amt)

        # (B) 처방 셋팅 — 성분 체크 + 선택 항목 담기
        c2 = quickjs.Context()
        load_ing_ctx(c2, js)
        c2.eval('''
          var STATE = {
            guideData: { dept: '내과', items: [
              { 영문키: 'k1', 성분명: '아세트아미노펜', 우리제품: [
                { 보험코드: '073001620', 품목명: '베아셋정', 제약사: '대웅바이오', 약가: 1063, 수수료율: 54 },
                { 보험코드: '073001480', 품목명: '아토타틴정', 제약사: '(주)일화', 약가: 1971, 수수료율: 34 } ] },
              { 영문키: 'k2', 성분명: '아토르바스타틴', 우리제품: [
                { 보험코드: 'E300', 품목명: '아토르정', 제약사: '한미약품', 약가: 500, 수수료율: 20 } ] }
            ] },
            guideSelected: {}, guidePick: {}, guidePending: [], rxGuideCodes: [],
            rxClient: '', guideProductCache: {}, guideRec: null, products: [], rxFrequent: [], clients: []
          };
          var __toasts = [];
          function showToast(m) { __toasts.push(String(m)); }
          function findClient() { return null; }
          var document = { querySelectorAll: function () { return []; }, getElementById: function () { return null; } };
        ''')
        c2.eval('function esc(s) { return String(s == null ? "" : s); }')
        if load(c2, ['rxCodeNorm_', 'rxCodeKey_', 'guideCacheProduct_', 'guideFindProduct_',
                     'guideCodesOfIngredient_', 'guidePickCodes_', 'guidePickCount_',
                     'guideBulkAddLabel_', 'guidePendingSet_', 'guidePendingCount_',
                     'guideSyncPickUI_', 'guideSyncPendingUI_', 'guideToggleIngredient', 'guideToggleProduct',
                     'guideAddSelected', 'renderGuidePicked'], '처방 셋팅 선택 담기'):
            check('073001620,073001480' in q12(c2.eval('guideCodesOfIngredient_(STATE.guideData.items[0])')),
                  '성분 체크가 제품 보험코드를 함께 기억하지 않습니다')
            c2.eval("guideToggleIngredient('k1', true);")
            check(int(c2.eval('guidePickCount_()')) == 2, '성분 체크로 2개 품목이 체크되지 않았습니다')
            check('(2)' in q12(c2.eval('guideBulkAddLabel_()')), '선택 항목 담기 버튼에 개수가 없습니다')
            c2.eval('guideAddSelected();')
            check(q12(c2.eval('STATE.guidePending.join(",")')) == '073001620,073001480',
                  '선택 항목 담기 결과가 다릅니다: %s' % q12(c2.eval('STATE.guidePending.join(",")')))
            check(int(c2.eval('STATE.rxGuideCodes.length')) == 2, '담은 품목이 처방전 유지목록에 없습니다')
            c2.eval("guideToggleIngredient('k1', false); guideToggleProduct('E300', true); guideAddSelected();")
            check(q12(c2.eval('STATE.guidePending.join(",")')) == '073001620,073001480,E300',
                  '두 번째 선택 담기가 합쳐지지 않았습니다: %s' % q12(c2.eval('STATE.guidePending.join(",")')))
            c2.eval('guideAddSelected();')
            check(int(c2.eval('STATE.guidePending.length')) == 3, '같은 품목이 중복으로 담겼습니다')

        # (C) 주사제 셋팅 — 체크한 품목을 한 번에 매출 등록으로
        c3 = quickjs.Context()
        load_ing_ctx(c3, js)
        c3.eval('''
          var STATE = {
            injData: { picks: [
              { 보험코드: 'A1', 품목명: '아다셀주', 규격: '1mL', 카테고리: '수액', 성분: '아다셀',
                급여구분: '급여', 약가: 10000, 수수료율: 40, 제약사: '한국코러스' },
              { 보험코드: 'A2', 품목명: '리도카인주', 규격: '2%', 카테고리: '통증', 성분: '리도카인',
                급여구분: '급여', 약가: 5000, 수수료율: 30, 제약사: '중외제약' },
              { 보험코드: 'A3', 품목명: '비타민C주', 규격: '10mL', 카테고리: '영양', 성분: '아스코르빈산',
                급여구분: '비급여', 약가: 8000, 수수료율: 50 }
            ], items: [] },
            injSelected: { A1: true, A2: true }, pendingOrderProducts: [], orderTab: 'inject',
            orderClientCode: '', guideProductCache: {}, products: [], clients: []
          };
          var __menus = [], __toasts = [];
          function showToast(m) { __toasts.push(String(m)); }
          function switchMenu(id) { __menus.push(String(id)); }
        ''')
        check(load_maker_ctx(c3, js), '앱 내장 제약사 목록을 실행 문맥에 넣지 못했습니다')
        c3.eval('function esc(s) { return String(s == null ? "" : s); }')
        if load(c3, ['rxCodeNorm_', 'rxCodeKey_', 'makerFromName_', 'makerOf_', 'injPickedProducts_',
                     'mergePendingOrderProducts_', 'injBulkOrderLabel_', 'injectSendSelectedToOrder'],
                '주사제 선택 매출'):
            check('(2)' in q12(c3.eval('injBulkOrderLabel_()')), '주사제 선택 매출 버튼에 개수가 없습니다')
            c3.eval('injectSendSelectedToOrder();')
            check(int(c3.eval('STATE.pendingOrderProducts.length')) == 2,
                  '선택 항목 매출 등록이 담은 품목을 모두 담지 않았습니다')
            check(q12(c3.eval('STATE.orderTab')) == 'entry', '매출 등록은 주문(매출) 등록 탭으로 가야 합니다')
            check(q12(c3.eval('__menus[__menus.length - 1]')) == 'order', '주사제 주문 메뉴로 이동하지 않았습니다')
            check(q12(c3.eval("STATE.pendingOrderProducts.map(function (r) { return r.제약사; }).join(',')")) == '한국코러스,중외제약',
                  '담은 품목에 실제 제조사가 없습니다')
            c3.eval('injectSendSelectedToOrder();')
            check(int(c3.eval('STATE.pendingOrderProducts.length')) == 2, '같은 품목이 중복으로 담겼습니다')

        # (D) 거래원장 — 회전일 표기
        c4 = quickjs.Context()
        load_ing_ctx(c4, js)
        c4.eval('var STATE = { ledgerTurnover: null };')
        c4.eval('function esc(s) { return String(s == null ? "" : s); }')
        if load(c4, ['fmtNum', 'ledgerTurnoverText_', 'ledgerTurnoverHtml_'], '거래원장 회전일'):
            c4.eval("""
              STATE.ledgerTurnover = { 거래처코드: 'S001', 회전일: 30, 경고여부: false, 회전일경고기준: 100 };
              var __d = { client: { 거래처코드: 'S001', 거래처명: '푸른정의원', 유통구분: '직납', 진료과: '내과', 담당자: '최충의' }, endingBalance: 1234567 };
            """)
            strip = q12(c4.eval('ledgerTurnoverHtml_(__d)'))
            check('회전일 30일' in strip, '거래원장 상단에 회전일이 없습니다: %s' % strip[:300])
            check('경고기준 100일' in strip, '거래원장 상단에 회전일 경고기준이 없습니다')
            check('1,234,567원' in strip, '거래원장 상단 기말잔액에 원 표기가 없습니다')
            check('미수 관리 필요' not in strip, '정상 거래처에 경고가 나옵니다')
            c4.eval("STATE.ledgerTurnover = { 회전일: 120, 경고여부: true, 회전일경고기준: 100 };")
            warn = q12(c4.eval('ledgerTurnoverHtml_(__d)'))
            check('⚠️' in warn and '미수 관리 필요' in warn, '회전일 경고 상태가 표시되지 않습니다')
            check('회전일 120일' in warn, '경고 회전일 숫자가 없습니다')
            c4.eval('STATE.ledgerTurnover = null;')
            none = q12(c4.eval('ledgerTurnoverHtml_(__d)'))
            check('회전일 확인 중' in none, '회전일을 못 받았을 때 안내가 없습니다')

        # (E) 출력물 — 원장님 안내용(수수료율 제외) · 처방전(수수료 포함)
        c5 = quickjs.Context()
        load_ing_ctx(c5, js)
        c5.eval('''
          var STATE = {
            settings: { 회사명: '수메디팜', 담당자명: '최충의', 담당자연락처: '010-2227-8668', 부가세율: '10' },
            guideData: { dept: '내과', items: [
              { 영문키: 'k1', 성분명: '아세트아미노펜', 우리제품: [
                { 보험코드: '073001620', 품목명: '베아셋정', 규격: '10정', 제약사: '대웅바이오', 약가: 1063, 수수료율: 54 } ] } ] },
            guideSelected: {}, guidePick: { '073001620': true }, guideRec: null, guideProductCache: {},
            injData: { picks: [
              { 보험코드: 'A1', 품목명: '아다셀주', 규격: '1mL', 카테고리: '수액', 성분: '아다셀',
                급여구분: '급여', 약가: 10000, 수수료율: 40, 제약사: '한국코러스' } ] },
            injSelected: {}, injProto: null, orderClientCode: '',
            rxClient: 'S001', rxMonth: '2026-11', rxDate: '2026-11-28',
            rxRows: [ { 품목명: '베아셋정', 보험코드: '073001620', 규격: '10정', 제약사: '대웅바이오',
                        약가: 1063, 수수료율: 54, 수량: 10 } ],
            rxSaved: null, products: [], clients: []
          };
          var __printed = '', __printCalls = 0;
          var document = { querySelectorAll: function () { return []; },
            getElementById: function () { return { set innerHTML(v) { __printed = v; } }; } };
          var window = { print: function () { __printCalls++; } };
          function showToast(m) {}
          function findClient(code) { return { 거래처코드: 'S001', 거래처명: '푸른정의원' }; }
        ''')
        check(load_maker_ctx(c5, js), '앱 내장 제약사 목록을 실행 문맥에 넣지 못했습니다')
        c5.eval('function esc(s) { return String(s == null ? "" : s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/"/g, "&quot;"); }')
        names5 = ['fmtNum', 'rxCodeNorm_', 'rxCodeKey_', 'makerFromName_', 'makerOf_', 'makerCellHtml_',
                  'guidePickCodes_', 'guidePickedList_', 'guideCacheProduct_', 'guideFindProduct_', 'printItemRows_',
                  'guidePrintRows_', 'injectPrintRows_', 'injPickedProducts_', 'rxPrintRows_',
                  'printStamp_', 'printDocHtml_', 'printArea_', 'printGuideSheet', 'printInjectSheet',
                  'printRxSheet']
        if load(c5, names5, '출력물'):
            c5.eval('printGuideSheet();')
            ghtml = q12(c5.eval('__printed'))
            check('처방 셋팅 안내' in ghtml, '처방 셋팅 출력물 제목이 없습니다')
            check('수메디팜' in ghtml and '출력일시' in ghtml, '출력물에 수메디팜 헤더·출력일시가 없습니다')
            check('대웅바이오' in ghtml, '처방 셋팅 출력물에 제약사가 없습니다')
            check('1,063원' in ghtml, '처방 셋팅 출력물 약가에 원이 없습니다')
            check('수수료율' not in ghtml and '54%' not in ghtml, '원장님 안내용 출력물에 내부 수수료율이 들어갑니다')
            check(int(c5.eval('__printCalls')) >= 1, 'window.print() 가 호출되지 않았습니다')
            c5.eval('printInjectSheet();')
            ihtml = q12(c5.eval('__printed'))
            check('주사·수액 셋팅 안내' in ihtml, '주사제 셋팅 출력물 제목이 없습니다')
            check('한국코러스' in ihtml, '주사제 셋팅 출력물에 실제 제조사가 없습니다')
            check('수수료율' not in ihtml and '40%' not in ihtml, '주사제 안내용 출력물에 내부 수수료율이 들어갑니다')
            # v1.13 — 내부용: 수수료율·예상수수료 포함
            c5.eval("printRxSheet('internal');")
            rhtml = q12(c5.eval('__printed'))
            check('처방 내역' in rhtml and '푸른정의원' in rhtml, '처방전 내부용 출력물에 병원 정보가 없습니다')
            check('2026-11' in rhtml, '처방전 내부용 출력물에 기준월이 없습니다')
            check('10,630원' in rhtml, '입력한 수량이 내부용 출력물 처방금액에 반영되지 않았습니다')
            check('수수료율' in rhtml and '54%' in rhtml, '처방전 내부용 출력물에 수수료율이 없습니다')
            check('5,740원' in rhtml, '예상수수료(54%)가 내부용 출력물에 없습니다')
            check('대웅바이오' in rhtml, '처방전 내부용 출력물에 제약사가 없습니다')
            # v1.13 — 원장님용: 수수료율·예상수수료·요율등급 완전 제외
            c5.eval("printRxSheet('owner');")
            ohtml = q12(c5.eval('__printed'))
            check('처방 품목 내역서' in ohtml, '원장님용 출력물 제목(처방 품목 내역서)이 없습니다')
            check('푸른정의원' in ohtml and '2026-11' in ohtml and '2026-11-28' in ohtml,
                  '원장님용 출력물에 병원·기준월·처방일이 없습니다')
            check('수메디팜' in ohtml and '출력일시' in ohtml, '원장님용 출력물에 수메디팜 헤더·출력일시가 없습니다')
            check('베아셋정' in ohtml and '073001620' in ohtml and '대웅바이오' in ohtml,
                  '원장님용 출력물에 품목명·보험코드·제약사가 없습니다')
            check('1,063원' in ohtml and '10개' in ohtml and '10,630원' in ohtml,
                  '원장님용 출력물에 기준단가·수량·처방금액이 없습니다')
            check('합계 (1품목)' in ohtml and '10개' in ohtml, '원장님용 출력물 합계행(품목수·수량)이 없습니다')
            check('수수료' not in ohtml, '원장님용 출력물에 수수료 관련 문구가 남아 있습니다')
            check('54%' not in ohtml and '5,740원' not in ohtml, '원장님용 출력물에 수수료율·예상수수료가 들어갑니다')
            check('예상수수료' not in ohtml and '요율등급' not in ohtml, '원장님용 출력물에 내부 영업 수치가 들어갑니다')
        # (F) 처방 셋팅 · 주사제 셋팅 화면에 제약사·선택 담기 버튼이 실제로 그려지는지
        c6 = quickjs.Context()
        load_ing_ctx(c6, js)
        c6.eval('''
          var STATE = {
            guideData: { dept: '내과', stats: { 매칭성분: 1, 성분수: 1 }, items: [
              { 영문키: 'k1', 성분명: '아세트아미노펜', 처방포인트: '공복', 우리제품: [
                { 보험코드: '073001620', 품목명: '베아셋정', 규격: '10정', 제약사: '대웅바이오', 약가: 1063, 수수료율: 54 } ], 경구제수: 1, 주사제수: 0 }
            ] },
            guideSelected: {}, guidePick: {}, guideMode: 'maxrate', guideMaxMakers: 3,
            guideRec: null, guideDept: '내과', guideProductCache: {}, products: [], clients: [],
            injData: { mode: 'maxrate', summary: { 추천품목수: 1, 카테고리수: 1, 평균수수료율: 40, 수수료액합계: 4000, 평균약가: 10000, 후보수: 1, 급여수: 1, 비급여수: 0 },
                       picks: [ { 보험코드: 'A1', 품목명: '아다셀주', 규격: '1mL', 카테고리: '수액', 성분: '아다셀', 급여구분: '급여', 약가: 10000, 수수료율: 40, 수수료액: 4000, 제약사: '한국코러스' } ],
                       items: [], categories: [] },
            injSelected: {}, injProto: null, orderClientCode: ''
          };
          var __els = {};
          var document = {
            querySelectorAll: function () { return []; },
            getElementById: function (id) {
              if (!__els[id]) __els[id] = { _h: '', textContent: '', style: {}, set innerHTML(v) { this._h = v; }, get innerHTML() { return this._h; } };
              return __els[id];
            }
          };
          function esc(s) { return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/"/g, '&quot;'); }
          function payTypeBadge(v) { return v ? '<span>' + v + '</span>' : ''; }
        ''')
        check(load_maker_ctx(c6, js), '앱 내장 제약사 목록을 실행 문맥에 넣지 못했습니다')
        names6 = ['fmtNum', 'rxCodeNorm_', 'rxCodeKey_', 'makerFromName_', 'makerOf_', 'makerCellHtml_',
                  'guideCodesOfIngredient_', 'guidePickCodes_', 'guidePickCount_', 'guideBulkAddLabel_',
                  'guidePendingSet_',
                  'guidePendingCount_', 'guideSendBtnLabel_', 'guideCacheProduct_', 'guideFindProduct_',
                  'guideRxTargetBadge_', 'renderGuideRecommend', 'renderGuideBody',
                  'injPickedProducts_', 'injBulkOrderLabel_', 'injWarnHtml_', 'injectPickTable_',
                  'renderInjectRecommend']
        if load(c6, names6, '셋팅 화면'):
            c6.eval('renderGuideBody();')
            gbody = q12(c6.eval('__els["guide-body"].innerHTML'))
            check('data-guide-pick' in gbody, '처방 셋팅 표에 품목 체크박스가 없습니다')
            check('대웅바이오' in gbody, '처방 셋팅 표에 제약사가 없습니다: %s' % gbody[:400])
            check('💊 선택 항목 담기' in gbody, '처방 셋팅에 선택 항목 담기 버튼이 없습니다')
            check('🖨️ 원장님 안내용 출력 / PDF' in gbody, '처방 셋팅에 원장님 안내용 출력 버튼이 없습니다')
            c6.eval('renderInjectRecommend();')
            ibody = q12(c6.eval('__els["inj-recommend"].innerHTML'))
            check('<th>제약사</th>' in ibody, '주사제 셋팅 표에 제약사 열이 없습니다')
            check('한국코러스' in ibody, '주사제 셋팅 표에 실제 제조사가 없습니다')
            check('페이서써플라이' in ibody, '주사제 셋팅 표에 취급 도매상 안내가 없습니다')
            check('🛒 선택 항목 매출 등록' in ibody, '주사제 셋팅에 선택 항목 매출 등록 버튼이 없습니다')
    except ImportError:
        print('(quickjs 없음 — v1.12 실행 검사 생략: pip install quickjs)')

    # 13) v1.16~v1.17 — 📢 공지사항 · 게시판 (한 화면 위아래: 위 공지 / 아래 소통 게시판, v1.17 게시물 목록 위 / 글쓰기 입력란 아래)
    check("id: 'board'" in js and 'renderBoardPage' in js and 'loadBoardModule' in js,
          '📢 공지사항 · 게시판 메뉴가 없습니다')
    check("label: '공지사항 · 게시판'" in js and "shortLabel: '공지'" in js,
          '메뉴 이름이 공지사항 · 게시판이 아닙니다')
    check("activeMenu: 'board'" in js, '로그인 후 첫 진입 화면이 공지사항이 아닙니다')
    check("STATE.activeMenu = 'board';" in js, '로그아웃 후 기본 메뉴가 공지사항이 아닙니다')
    check("icon: '📢'" in js, '공지사항 메뉴 아이콘이 없습니다')
    # v1.16 — 탭 전환 없이 한 화면 위아래
    check('boardTabBar_' not in js and 'switchBoardTab' not in js and 'boardTab:' not in js,
          '게시판에 공지/자유 탭 전환이 남아 있습니다(한 화면 위아래로 바뀌어야 함)')
    check('💬 자유 게시판' not in js, '아래 영역이 아직 자유 게시판 탭 이름입니다')
    check('💬 소통 · 특이사항 게시판' in js and '📌 공지사항' in js,
          '한 화면의 위 공지사항 · 아래 소통 · 특이사항 게시판 제목이 없습니다')
    for need in ['boardPageHtml_', 'boardNoticeCardHtml_', 'boardFreeCardHtml_', 'boardSectionHeadHtml_',
                 'boardToolbarHtml_', 'onBoardSearch', 'setBoardCategory', 'toggleBoardNoticeFold',
                 'toggleBoardNoticeMore', 'boardFiltered_', 'boardListHtml_', 'boardItemHtml_',
                 'boardComposerHtml_', 'focusBoardComposer', 'openBoardComposer', 'openBoardEdit',
                 'submitBoardPost', 'cancelBoardComposer', 'toggleBoardPin', 'boardDeletePost',
                 'toggleBoardPost', 'boardPreview_']:
        check(need in js, '공지사항·게시판에 %s 가 없습니다' % need)
    check("'미지급 사유'" in js and "'특별 수수료율'" in js and "'일반 공지'" in js,
          '공지사항 카테고리(미지급 사유·특별 수수료율·일반 공지)가 없습니다')
    check("BOARD_FREE_CATS = ['전체', '소통', '특이사항', '정보공유', '질문']" in js,
          '소통 게시판 말머리(소통·특이사항·정보공유·질문)가 없습니다')
    check('-search"' in js and '-list"' in js and "onBoardSearch(" in js,
          '위·아래 두 영역의 검색창·목록 자리가 없습니다')
    check('제목·내용·작성자 검색' in js, '게시판 검색 안내가 없습니다')
    check("runServer('boardList'" in js and "runServer('boardCreate'" in js and
          "runServer('boardUpdate'" in js and "runServer('boardDelete'" in js,
          '게시판 서버 호출이 빠졌습니다')
    check('공지 작성은 MASTER만' in js, 'STAFF 에게 공지 작성 불가 안내가 없습니다')
    check('boardDraft' in js and 'boardEditNo' in js, '게시판 작성/수정 상태가 없습니다')
    check('data-board-no' in js, '게시판 글 카드 식별자가 없습니다')
    check('data-board-section' in js and 'board-notice-list' in js and 'board-free-list' in js,
          '한 화면 두 영역(공지·소통)의 자리가 없습니다')
    # v1.17 — 소통 게시판 카드 안은 위에서부터 [게시물 목록] → [글쓰기 입력란]
    free_fn = extract_fn(js, 'boardFreeCardHtml_') or ''
    check(bool(free_fn) and 'board-free-list' in free_fn and 'boardComposerHtml_' in free_fn and
          free_fn.index('board-free-list') < free_fn.index('boardComposerHtml_'),
          '소통 게시판이 게시물 목록 → 글쓰기 입력란 순서가 아닙니다')
    check('title="아래 글쓰기 입력란으로"' in js or '아래 글쓰기 입력란으로' in js,
          '✏️ 새 글 버튼이 아래 글쓰기 입력란으로 안내하지 않습니다')
    check('아래 입력란에 첫 글을 남겨 보세요' in js,
          '글이 없을 때 아래 입력란 안내가 없습니다')
    check('BOARD_NOTICE_SHOW' in js and '＋ 공지 ' in js, '공지 영역 컴팩트 표시(더 보기)가 없습니다')
    # 메뉴가 실제로 가장 첫 번째인지
    first_menu = re.search(r"const APP_MENUS = \[\s*\{\s*\n\s*id: '([a-z]+)'", js)
    check(bool(first_menu) and first_menu.group(1) == 'board', 'APP_MENUS 첫 메뉴가 board 가 아닙니다')

    # 13-a) 화면을 실제로 그려 보기 — 한 화면에 위(공지) · 아래(소통)가 동시에, STAFF·MASTER 모두 글쓰기
    try:
        import quickjs

        def q13(v):
            return v.decode() if isinstance(v, bytes) else v

        names13 = ['boardSectionKind_', 'boardItems_', 'boardCatOf_', 'boardQueryOf_', 'boardOpenMap_',
                   'boardDraftOf_', 'boardFindItem_', 'boardErrorHtml_', 'boardPageHtml_',
                   'boardSectionHeadHtml_', 'boardNoticeCardHtml_', 'boardFreeCardHtml_',
                   'boardCatsOf_', 'boardCatCount_', 'boardToolbarHtml_', 'onBoardSearch',
                   'setBoardCategory', 'toggleBoardNoticeFold', 'toggleBoardNoticeMore',
                   'boardFiltered_', 'boardListHtml_', 'boardPreview_', 'boardItemHtml_',
                   'toggleBoardPost', 'boardComposerHtml_', 'focusBoardComposer',
                   'openBoardComposer', 'openBoardEdit', 'cancelBoardComposer', 'submitBoardPost',
                   'renderBoardList_']
        blocks13 = [extract_fn(js, n) for n in names13]
        missing13 = [n for n, b in zip(names13, blocks13) if b is None]
        check(not missing13, '게시판 렌더 함수를 추출하지 못했습니다: %s' % missing13)
        if not missing13:
            NOTICE_PINNED = {
                '번호': 3, '구분': '공지', '카테고리': '미지급 사유',
                '제목': '이엘파마 소액처 기준', '내용': '국제약품 소액처 정산 가능\n라온파마 직전 3개월',
                '작성자아이디': 'master', '작성자명': '마스터', '고정여부': 'Y',
                '작성일시': '2026-11-28 09:10:00', '수정일시': '',
                '수정가능': True, '삭제가능': True, '고정가능': True,
            }
            NOTICE_NEW = {
                '번호': 4, '구분': '공지', '카테고리': '특별 수수료율',
                '제목': '<b>2026.12 EDI</b> 캠페인', '내용': '371품목 추가 수수료',
                '작성자아이디': 'master', '작성자명': '마스터', '고정여부': 'N',
                '작성일시': '2026-11-28 09:07:00', '수정일시': '2026-11-28 09:30:00',
                '수정가능': True, '삭제가능': True, '고정가능': True,
            }
            NOTICE_OLD = {
                '번호': 1, '구분': '공지', '카테고리': '일반 공지', '제목': '게시판 사용 안내',
                '내용': '직원 모두 소통 게시판에 글을 남길 수 있습니다.', '작성자아이디': 'master',
                '작성자명': '마스터', '고정여부': 'N', '작성일시': '2026-11-27 09:00:00',
                '수정일시': '', '수정가능': True, '삭제가능': True, '고정가능': True,
            }
            FREE_MINE = {
                '번호': 5, '구분': '자유', '카테고리': '특이사항', '제목': '수아의원 단가 문의',
                '내용': '이번 달 단가 확인 부탁드립니다.', '작성자아이디': 'choi', '작성자명': '최충의',
                '고정여부': 'N', '작성일시': '2026-11-28 10:00:00', '수정일시': '',
                '수정가능': True, '삭제가능': True, '고정가능': False,
            }
            FREE_OTHER = {
                '번호': 2, '구분': '자유', '카테고리': '정보공유', '제목': '타사 단가표 공유',
                '내용': '받은 자료 올려 둡니다.', '작성자아이디': 'gii4', '작성자명': '정아름',
                '고정여부': 'N', '작성일시': '2026-11-27 15:00:00', '수정일시': '',
                '수정가능': False, '삭제가능': False, '고정가능': False,
            }

            def items_for(is_master, extra=()):
                out = []
                base = [FREE_OTHER, FREE_MINE, NOTICE_NEW, NOTICE_PINNED] + list(extra)
                for it in base:
                    r = dict(it)
                    if not is_master:
                        if r['구분'] == '공지':
                            r.update({'수정가능': False, '삭제가능': False, '고정가능': False})
                        elif r['작성자아이디'] != 'choi':
                            r.update({'수정가능': False, '삭제가능': False, '고정가능': False})
                    out.append(r)
                return out

            def build_ctx(is_master, items):
                c = quickjs.Context()
                load_ing_ctx(c, js)
                counts = {'공지': 0, '자유': 0}
                for it in items:
                    counts[it['구분']] = counts.get(it['구분'], 0) + 1
                c.eval("""
                var STATE = {
                  boardNoticeCat: '', boardNoticeQuery: '', boardNoticeOpen: {}, boardNoticeMore: false,
                  boardNoticeFolded: false, boardFreeCat: '', boardFreeQuery: '', boardFreeOpen: {},
                  boardDraft: null, boardEditNo: 0, boardSaving: false, boardError: '',
                  isMaster: %s, user: { 아이디: 'choi', 담당자명: '최충의' },
                  boardData: { items: %s, total: %d, counts: %s,
                               categories: { '공지': [{ 카테고리: '미지급 사유', 개수: 1 },
                                                      { 카테고리: '특별 수수료율', 개수: 1 }],
                                             '자유': [{ 카테고리: '특이사항', 개수: 1 }, { 카테고리: '정보공유', 개수: 1 }] },
                               isMaster: %s, me: { 아이디: 'choi', 담당자명: '최충의' } }
                };
                var __toasts = [], __els = {}, __calls = [], __renders = 0, __focus = [], __scroll = [];
                function showToast(m) { __toasts.push(String(m)); }
                function esc(s) { return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;')
                  .replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;'); }
                function fmtNum(n) { return String(Math.round(Number(n || 0))); }
                function renderActiveMenu() { __renders++; }
                function loadBoardModule() { __calls.push({ fn: 'loadBoardModule', args: [] }); }
                function runServer(fn, args) { __calls.push({ fn: fn, args: args }); return __RESULT[fn] || { success: true }; }
                var __RESULT = {};
                var window = { confirm: function () { return true; } };
                var document = { getElementById: function (id) {
                  if (!__els[id]) __els[id] = { _h: '', value: '',
                    focus: function (o) { __focus.push({ id: id, opts: o || null }); },
                    scrollIntoView: function (o) { __scroll.push({ id: id, opts: o || null }); },
                    set innerHTML(v) { this._h = v; }, get innerHTML() { return this._h; } };
                  return __els[id];
                } };
                """ % ('true' if is_master else 'false', json.dumps(items, ensure_ascii=False),
                       len(items), json.dumps(counts, ensure_ascii=False),
                       'true' if is_master else 'false'))
                c.eval("const BOARD_NOTICE_CATS = ['전체', '미지급 사유', '특별 수수료율', '일반 공지'];"
                       " const BOARD_FREE_CATS = ['전체', '소통', '특이사항', '정보공유', '질문'];"
                       " const BOARD_NOTICE_SHOW = 4; const BOARD_CONTENT_MAX = 45000;")
                for b in blocks13:
                    c.eval(b)
                return c

            def section_html(html, sec):
                """data-board-section="sec" 카드만 잘라 냅니다."""
                head = 'data-board-section="%s"' % sec
                if head not in html:
                    return ''
                rest = html.split(head, 1)[1]
                other = 'data-board-section="'
                return rest.split(other, 1)[0]

            # (A) MASTER — 한 화면에 위 공지 · 아래 소통 게시판이 동시에
            cm = build_ctx(True, items_for(True))
            page_m = q13(cm.eval('boardPageHtml_()'))
            check('data-board-section="notice"' in page_m and 'data-board-section="free"' in page_m,
                  '한 화면에 공지·소통 두 영역이 함께 그려지지 않았습니다')
            check(page_m.index('📌 공지사항') < page_m.index('💬 소통 · 특이사항 게시판'),
                  '공지사항이 소통 게시판보다 위에 있지 않습니다')
            check(page_m.count('data-board-no') == 4, '두 영역의 글이 한 화면에 다 그려지지 않았습니다')
            top = section_html(page_m, 'notice')
            bottom = section_html(page_m, 'free')
            check('data-board-no="3"' in top and 'data-board-no="4"' in top and 'data-board-no="5"' not in top,
                  '위 공지 영역에 공지만 그려지지 않았습니다')
            check('data-board-no="5"' in bottom and 'data-board-no="2"' in bottom and 'data-board-no="3"' not in bottom,
                  '아래 소통 영역에 소통 글만 그려지지 않았습니다')
            check('📌 공지사항' in top and '💬 소통 · 특이사항 게시판' in bottom,
                  '위아래 영역 제목이 없습니다')
            check(top.index('data-board-no="3"') < top.index('data-board-no="4"'), '고정 글이 맨 위가 아닙니다')
            for label in ['📌', '미지급 사유', '이엘파마 소액처 기준', '마스터', '2026-11-28 09:10',
                          '펼치기 ▼', '📌 해제', '✏️', '🗑️']:
                check(label in top, 'MASTER 공지 카드에 %s 가 없습니다' % label)
            check('수정 2026-11-28 09:30' in top, '수정일시가 표시되지 않습니다')
            check('&lt;b&gt;2026.12 EDI&lt;/b&gt;' in top, '제목이 이스케이프되지 않았습니다(XSS)')
            check('white-space:pre-wrap' not in top, '접힌 글의 본문 상자가 그대로 그려집니다')
            check('371품목 추가 수수료' in top, '미리보기 본문이 없습니다')
            check('공지 접기 ▲' in top, '공지 영역 접기 버튼이 없습니다')

            # 펼치기 — 본문 줄바꿈 유지
            cm.eval('toggleBoardPost(3);')
            page_open = q13(cm.eval('boardPageHtml_()'))
            check('라온파마 직전 3개월' in page_open, '펼쳐도 본문이 나오지 않습니다')
            check('white-space:pre-wrap' in page_open, '본문 줄바꿈 처리가 없습니다')
            check('접기 ▲' in section_html(page_open, 'notice'), '펼친 글의 접기 버튼이 없습니다')
            cm.eval('toggleBoardPost(3);')

            # (B) 위 공지 툴바 — 카테고리 칩·검색·MASTER 공지 쓰기
            bar_m = q13(cm.eval('boardToolbarHtml_("notice")'))
            for label in ['🔍 제목·내용·작성자 검색', '✏️ 공지 쓰기', '미지급 사유 1', '특별 수수료율 1',
                          '전체 2', '일반 공지 0']:
                check(label in bar_m, 'MASTER 공지 툴바에 %s 가 없습니다' % label)
            check('onclick="setBoardCategory(\'notice\', \'미지급 사유\')"' in bar_m, '카테고리 필터 버튼이 없습니다')
            check('id="board-notice-search"' in top, '위 공지 검색창이 없습니다')
            check('id="board-free-search"' in bottom, '아래 소통 게시판 검색창이 없습니다')

            # (C) 아래 소통 게시판 — 늘 열린 글쓰기 폼(MASTER) + 말머리 4종
            check('💬 소통 · 특이사항 남기기' in bottom, '아래 게시판 글쓰기 폼이 없습니다')
            for label in ['board-free-cat', 'board-free-title', 'board-free-content',
                          "submitBoardPost('free')", '소통', '특이사항', '정보공유', '질문']:
                check(label in bottom, '소통 게시판 글쓰기 폼에 %s 가 없습니다' % label)
            check('💾 저장' in bottom, '저장 버튼이 없습니다')
            bar_free = q13(cm.eval('boardToolbarHtml_("free")'))
            for label in ['🔍 제목·내용·작성자 검색', '특이사항 1', '정보공유 1', '전체 2']:
                check(label in bar_free, '소통 게시판 툴바에 %s 가 없습니다' % label)

            # (C-2) v1.17 — 화면 위에서부터 공지사항 → 게시물 목록 → 글쓰기 입력란
            check(page_m.index('data-board-section="free"') < page_m.index('board-free-list')
                  < page_m.index('board-free-composer'),
                  '소통 게시판이 게시물 목록 → 글쓰기 입력란 순서가 아닙니다')
            check(bottom.index('data-board-no="5"') < bottom.index('board-free-composer')
                  and bottom.index('💬 소통 · 특이사항 게시판') < bottom.index('board-free-list'),
                  '게시물이 글쓰기 입력란보다 위에 있지 않습니다')
            check(page_m.index('📌 공지사항') < page_m.index('💬 소통 · 특이사항 게시판')
                  < page_m.index('board-free-composer'),
                  '공지사항 → 게시물 → 글쓰기 입력란 순서가 아닙니다')
            check('아래 글쓰기 입력란으로' in bar_free, '✏️ 새 글 버튼이 아래 입력란으로 안내하지 않습니다')

            # ✏️ 새 글 — 아래 입력란으로 부드럽게 내려가 제목칸에 포커스
            cm.eval('__focus.length = 0; __scroll.length = 0; focusBoardComposer("free");')
            scrolls = json.loads(q13(cm.eval('JSON.stringify(__scroll)')))
            focuses = json.loads(q13(cm.eval('JSON.stringify(__focus)')))
            check(any(v['id'] == 'board-free-composer' and (v.get('opts') or {}).get('behavior') == 'smooth'
                      for v in scrolls),
                  '✏️ 새 글이 아래 글쓰기 입력란으로 부드럽게 내려가지 않습니다: %s' % scrolls)
            check(any(v['id'] == 'board-free-title' for v in focuses),
                  '✏️ 새 글이 글쓰기 제목칸에 포커스를 주지 않습니다: %s' % focuses)

            # ✏️ 수정 — 그 글을 아래 입력란으로 불러오고 역시 부드럽게 내려간다
            cm.eval('__focus.length = 0; __scroll.length = 0; openBoardEdit(5);')
            check(int(cm.eval('STATE.boardEditNo')) == 5, '✏️ 를 눌러도 수정 상태가 아닙니다')
            scrolls_e = json.loads(q13(cm.eval('JSON.stringify(__scroll)')))
            focuses_e = json.loads(q13(cm.eval('JSON.stringify(__focus)')))
            check(any(v['id'] == 'board-free-composer' for v in scrolls_e),
                  '✏️ 수정이 아래 글쓰기 입력란으로 내려가지 않습니다: %s' % scrolls_e)
            check(any(v['id'] == 'board-free-title' for v in focuses_e), '수정 시 제목칸 포커스가 없습니다')
            check('✏️ 글 수정 (#' in section_html(q13(cm.eval('boardPageHtml_()')), 'free'),
                  '수정 폼이 게시물 목록 아래에 그려지지 않았습니다')
            cm.eval('STATE.boardDraft = null; STATE.boardEditNo = 0;')

            # 검색·말머리 거르기 (두 영역이 서로 영향 없이)
            cm.eval("STATE.boardNoticeQuery = 'EDI';")
            top_q = section_html(q13(cm.eval('boardPageHtml_()')), 'notice')
            check(top_q.count('data-board-no') == 1 and 'data-board-no="4"' in top_q, '공지 검색이 동작하지 않습니다')
            free_q = section_html(q13(cm.eval('boardPageHtml_()')), 'free')
            check(free_q.count('data-board-no') == 2, '공지 검색이 소통 게시판까지 걸렀습니다')
            cm.eval("STATE.boardNoticeQuery = ''; STATE.boardNoticeCat = '미지급 사유';")
            check(section_html(q13(cm.eval('boardPageHtml_()')), 'notice').count('data-board-no') == 1,
                  '공지 카테고리 필터가 동작하지 않습니다')
            cm.eval("STATE.boardNoticeCat = '일반 공지';")
            check('조건에 맞는 글이 없습니다' in section_html(q13(cm.eval('boardPageHtml_()')), 'notice'),
                  '조건에 맞는 글이 없을 때 안내가 없습니다')
            cm.eval("STATE.boardNoticeCat = '';")
            cm.eval("STATE.boardFreeQuery = '정아름';")
            check(section_html(q13(cm.eval('boardPageHtml_()')), 'free').count('data-board-no') == 1,
                  '소통 게시판 작성자 검색이 동작하지 않습니다')
            cm.eval("STATE.boardFreeQuery = ''; STATE.boardFreeCat = '특이사항';")
            free_cat = section_html(q13(cm.eval('boardPageHtml_()')), 'free')
            check(free_cat.count('data-board-no') == 1 and 'data-board-no="5"' in free_cat,
                  '소통 게시판 말머리 필터가 동작하지 않습니다')
            cm.eval("STATE.boardFreeCat = '';")

            # (D) MASTER 공지 쓰기 — 위 영역에만 폼이 열리고, 접혀 있었으면 펴집니다
            cm.eval('STATE.boardNoticeFolded = true; openBoardComposer("notice");')
            page_c = q13(cm.eval('boardPageHtml_()'))
            top_c = section_html(page_c, 'notice')
            check('📌 공지 쓰기' in top_c, 'MASTER 공지 작성 폼이 없습니다')
            for label in ['board-notice-cat', 'board-notice-title', 'board-notice-content',
                          "submitBoardPost('notice')"]:
                check(label in top_c, '공지 작성 폼에 %s 가 없습니다' % label)
            check(cm.eval('STATE.boardNoticeFolded') is False or cm.eval('STATE.boardNoticeFolded') == 0,
                  '공지 쓰기를 열어도 접힌 공지 영역이 펴지지 않았습니다')
            check('value="일반 공지" selected' in top_c, '공지 기본 말머리가 일반 공지가 아닙니다')
            cm.eval("STATE.boardDraft = null; STATE.boardEditNo = 0;")

            # 접기/펼치기 — 접어도 아래 게시판은 그대로
            cm.eval('toggleBoardNoticeFold();')
            page_fold = q13(cm.eval('boardPageHtml_()'))
            top_fold = section_html(page_fold, 'notice')
            check('data-board-no' not in top_fold and '공지 펼치기 ▼' in top_fold, '공지 영역 접기가 동작하지 않습니다')
            check(section_html(page_fold, 'free').count('data-board-no') == 2, '공지를 접으면 아래 게시판도 사라집니다')
            cm.eval('toggleBoardNoticeFold();')
            check('data-board-no' in section_html(q13(cm.eval('boardPageHtml_()')), 'notice'),
                  '공지 영역 다시 펼치기가 동작하지 않습니다')

            # (E) STAFF — 아래 글쓰기 폼은 보이고, 위 공지 작성·수정·삭제는 없다
            cs = build_ctx(False, items_for(False))
            page_s = q13(cs.eval('boardPageHtml_()'))
            top_s = section_html(page_s, 'notice')
            bottom_s = section_html(page_s, 'free')
            check('data-board-section="notice"' in page_s and 'data-board-section="free"' in page_s,
                  'STAFF 화면에 두 영역이 함께 그려지지 않았습니다')
            check('💬 소통 · 특이사항 남기기' in bottom_s and 'board-free-title' in bottom_s,
                  'STAFF 에게 소통 게시판 글쓰기 폼이 보이지 않습니다')
            check("submitBoardPost('free')" in bottom_s, 'STAFF 소통 글 저장 버튼이 없습니다')
            check('🗑️' not in top_s and '📌 해제' not in top_s and '✏️' not in top_s,
                  'STAFF 공지 카드에 관리 버튼이 보입니다')
            bar_s = q13(cs.eval('boardToolbarHtml_("notice")'))
            check('공지 작성은 MASTER만' in bar_s and '✏️ 공지 쓰기' not in bar_s,
                  'STAFF 에게 공지 작성 버튼이 보입니다')
            cs.eval('openBoardComposer("notice");')
            check(q13(cs.eval('__toasts[__toasts.length - 1]')).find('MASTER') != -1,
                  'STAFF 가 공지를 쓰려 하면 안내가 없습니다')
            check(cs.eval('STATE.boardDraft === null'), 'STAFF 인데 공지 작성 폼이 열렸습니다')
            check('📌 공지 쓰기' not in q13(cs.eval('boardPageHtml_()')), 'STAFF 화면에 공지 작성 폼이 그려졌습니다')

            # STAFF — 소통 글: 내 글만 수정·삭제
            card_mine = bottom_s.split('data-board-no="5"')[1].split('data-board-no=')[0]
            check('✏️' in card_mine and '🗑️' in card_mine, '내 소통 글에 수정·삭제 버튼이 없습니다')
            card_other = bottom_s.split('data-board-no="2"')[1]
            check('✏️' not in card_other and '🗑️' not in card_other, '남의 소통 글에 수정·삭제 버튼이 보입니다')

            # STAFF — 소통 글 저장은 그대로 boardCreate(자유)
            cs.eval("openBoardComposer('free');")
            check(q13(cs.eval('STATE.boardDraft.구분')) == '자유', '소통 게시판 작성 구분이 자유가 아닙니다')
            check(q13(cs.eval('STATE.boardDraft.카테고리')) == '소통', '소통 게시판 기본 말머리가 소통이 아닙니다')
            cs.eval("document.getElementById('board-free-title'); document.getElementById('board-free-content');"
                    " document.getElementById('board-free-cat');"
                    " __els['board-free-title'].value = '오후 방문 결과'; __els['board-free-content'].value = '수아의원 방문 완료'; "
                    "__els['board-free-cat'].value = '특이사항';")
            cs.eval("submitBoardPost('free');")
            for _ in range(40):
                try:
                    if not cs.execute_pending_job():
                        break
                except Exception:  # noqa: BLE001
                    break
            calls_s = json.loads(q13(cs.eval('JSON.stringify(__calls)')))
            creates = [c for c in calls_s if c['fn'] == 'boardCreate']
            check(len(creates) == 1, 'STAFF 소통 글 저장이 서버로 가지 않았습니다: %s' % calls_s)
            if creates:
                arg = creates[0]['args'][0]
                check(arg['구분'] == '자유' and arg['카테고리'] == '특이사항',
                      '소통 글 저장 값이 다릅니다: %s' % arg)
                check(arg['제목'] == '오후 방문 결과' and arg['내용'] == '수아의원 방문 완료',
                      '소통 글 제목·내용이 서버로 전달되지 않았습니다: %s' % arg)
            check(q13(cs.eval('__toasts[__toasts.length - 1]')) == '올렸습니다.', '소통 글 저장 안내가 없습니다')

            # (F) 공지가 많으면 위 영역은 컴팩트하게, 더 보기로 펼침
            extra = []
            for k in range(5):
                extra.append({'번호': 10 + k, '구분': '공지', '카테고리': '일반 공지',
                              '제목': '공지 %d' % (k + 1), '내용': '내용 %d' % (k + 1),
                              '작성자아이디': 'master', '작성자명': '마스터', '고정여부': 'N',
                              '작성일시': '2026-11-27 09:%02d:00' % (10 + k), '수정일시': '',
                              '수정가능': True, '삭제가능': True, '고정가능': True})
            c_many = build_ctx(True, items_for(True, extra))
            many_top = section_html(q13(c_many.eval('boardPageHtml_()')), 'notice')
            check(many_top.count('data-board-no') == 4, '공지 영역이 기본 4건으로 접히지 않았습니다')
            check('＋ 공지 3건 더 보기' in many_top, '공지 더 보기 버튼이 없습니다')
            c_many.eval('toggleBoardNoticeMore();')
            many_all = section_html(q13(c_many.eval('boardPageHtml_()')), 'notice')
            check(many_all.count('data-board-no') == 7, '공지 더 보기가 동작하지 않습니다')
            check('공지 접기 ▲' in many_all, '공지 더 보기 접기가 없습니다')

            # (G) 서버 오류(재배포 전) 안내 · 불러오는 중
            c = build_ctx(True, items_for(True))
            c.eval("STATE.boardError = 'SERVER_HINT'; STATE.boardData = null;")
            err_html = q13(c.eval('boardPageHtml_()'))
            check('SERVER_HINT' in err_html and '불러오는 중' in err_html,
                  '게시판 서버 오류 안내가 없습니다')
            check('data-board-section="free"' in err_html, '오류가 나도 아래 소통 게시판 자리가 없습니다')
    except ImportError:
        print('(quickjs 없음 — 공지사항·게시판 실행 검사 생략: pip install quickjs)')

    # 14) v1.14 — 처방 셋팅 성분 검색 (여러 제약사 품목 비교·선택)
    check('guide-ing-q' in js and 'onGuideIngQuery' in js, '처방 셋팅에 성분 검색창이 없습니다')
    check('guideIngSearchCardHtml_' in js and '🔎 성분 · 제약사 검색' in js,
          '처방 셋팅 성분 검색 카드가 없습니다')
    check("runServer('searchGuideIngredients'" in js, '성분 검색 서버 호출이 없습니다')
    for need in ['loadGuideIngSearch', 'guideIngResultHtml_', 'guideIngGroupHtml_',
                 'toggleGuideIngGroup', 'guideIngSelectAll', 'guideOpenIngredient',
                 'clearGuideIngSearch', 'renderGuideIngResult']:
        check(need in js, '성분 검색에 %s 가 없습니다' % need)
    check("+' 외 ' + (it.경구제수 - 3) + ' 보기" in js or "외 ' + (it.경구제수 - 3) + ' 보기" in js,
          '성분 줄의 [외 N 보기] 버튼이 없습니다')
    check('guideOpenIngredient' in js and '성분키: key' in js, '성분키로 펼치는 요청이 없습니다')
    check('data-guide-pick' in js and 'guideToggleProduct' in js, '검색 품목 체크가 선택 담기에 연결되지 않습니다')
    check('guide-ing-bulk-add' in js, '검색 결과에서 바로 담는 버튼이 없습니다')
    check('최고 ' in js and '최저 ' in js, '성분별 수수료율·약가 요약이 없습니다')
    if os.path.exists(CODEGS):
        check(re.search(r'searchGuideIngredients\s*:\s*searchGuideIngredients',
                        open(CODEGS, encoding='utf-8').read()) is not None,
              'Code.gs apiFunctions_ 에 searchGuideIngredients 가 없습니다')

    # 14-a) 성분 검색 화면·선택 담기 실행 검사
    try:
        import quickjs

        def q14(v):
            return v.decode() if isinstance(v, bytes) else v

        names14 = ['guideIngGroupKey_', 'guideIngGroupHtml_', 'guideIngResultHtml_', 'renderGuideIngResult',
                   'toggleGuideIngGroup', 'guideIngSelectAll', 'onGuideIngQuery', 'clearGuideIngSearch',
                   'guideOpenIngredient', 'loadGuideIngSearch', 'guideIngSearchCardHtml_',
                   'rxCodeNorm_', 'rxCodeKey_', 'guideCacheProduct_', 'guideFindProduct_',
                   'guidePickCodes_', 'guidePickCount_', 'guideBulkAddLabel_', 'guidePendingSet_',
                   'guidePendingCount_', 'guideSendBtnLabel_', 'guideToggleProduct', 'guideAddSelected',
                   'guideSyncPickUI_', 'guideSyncPendingUI_', 'guideAddItem', 'guidePrintRows_',
                   'printItemRows_', 'makerOf_', 'makerFromName_', 'guideCodesOfIngredient_',
                   'guideIngItemsTableHtml_',
                   'renderGuidePicked', 'guidePickedList_', 'guidePickedRow_', 'guidePickedCardHtml_']
        blocks14 = [extract_fn(js, n) for n in names14]
        missing14 = [n for n, b in zip(names14, blocks14) if b is None]
        check(not missing14, '성분 검색 함수를 추출하지 못했습니다: %s' % missing14)
        if not missing14:
            def drain(c, limit=40):
                for _ in range(limit):
                    try:
                        if not c.execute_pending_job():
                            break
                    except Exception:  # noqa: BLE001
                        break

            def new_ctx():
                c = quickjs.Context()
                load_ing_ctx(c, js)
                c.eval("""
                var STATE = {
                  guideIngQ: '', guideIngKey: '', guideIngData: null, guideIngOpen: {},
                  guideIngLoading: false, guidePick: {}, guidePending: [], rxGuideCodes: [],
                  rxClient: '', guideProductCache: {}, guideData: null, guideRec: null,
                  guideDept: '', guideSelected: {}, products: [], clients: [],
                  guideMaxMakers: 3, guideMode: 'maxrate'
                };
                var __toasts = [], __els = {}, __calls = [];
                function showToast(m) { __toasts.push(String(m)); }
                function esc(s) { return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;')
                  .replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;'); }
                function fmtNum(n) { return String(Math.round(Number(n || 0))).replace(/\\B(?=(\\d{3})+(?!\\d))/g, ','); }
                function findClient(code) { return code ? { 거래처코드: code, 거래처명: '푸른정의원' } : null; }
                function renderActiveMenu() {}
                function switchMenu() {}
                function v14ErrorText_(e) { return String((e && e.message) || e); }
                var document = { querySelectorAll: function () { return []; },
                  getElementById: function (id) {
                    if (!__els[id]) __els[id] = { _h: '', value: '', focus: function () {},
                      scrollIntoView: function () {},
                      set innerHTML(v) { this._h = v; }, get innerHTML() { return this._h; } };
                    return __els[id];
                  } };
                function runServer(fn, args) { __calls.push({ fn: fn, args: args }); return __RESULT[fn]; }
                var __RESULT = {};
                """)
                check(load_maker_ctx(c, js), '앱 내장 제약사 목록을 실행 문맥에 넣지 못했습니다')
                for b in blocks14:
                    c.eval(b)
                return c

            ATOR = {
                '성분키': 'atorvastatin', '성분명': '아토르바스타틴', '분류': '고지혈증치료제',
                '품목수': 3, '제약사수': 3, '최고수수료율': 57, '최저약가': 345, '잘림': False,
                'items': [
                    {'표': '경구', '보험코드': '621804250', '품목명': '아토브정10/10mg', '규격': '10정',
                     '제약사': '한국파비스제약', '약가': 1254, '수수료율': 57, '급여구분': '급여', '성분': '아토르바스타틴'},
                    {'표': '경구', '보험코드': '640902490', '품목명': '아토타틴정10mg', '규격': '10정',
                     '제약사': '(주)일화', '약가': 1971, '수수료율': 34, '급여구분': '급여', '성분': '아토르바스타틴'},
                    {'표': '경구', '보험코드': '628800340', '품목명': '휴스타정10mg', '규격': '10정',
                     '제약사': '휴비스트제약', '약가': 345, '수수료율': 42, '급여구분': '급여', '성분': '아토르바스타틴'},
                ],
            }
            ROSU = {
                '성분키': 'rosuvastatin', '성분명': '로수바스타틴', '분류': '고지혈증치료제',
                '품목수': 1, '제약사수': 1, '최고수수료율': 40, '최저약가': 500, '잘림': False,
                'items': [
                    {'표': '경구', '보험코드': '641601230', '품목명': '로수정10mg', '규격': '10정',
                     '제약사': '한화제약㈜', '약가': 500, '수수료율': 40, '급여구분': '급여', '성분': '로수바스타틴'},
                ],
            }

            # (A) 성분 하나 = 여러 제약사 품목 표
            c = new_ctx()
            c.eval('STATE.guideIngData = %s; STATE.guideIngOpen = { atorvastatin: true, rosuvastatin: false };'
                   % json.dumps({'q': '아토르', 'total성분': 2, 'total품목': 4, 'shown성분': 2,
                                 'groups': [ATOR, ROSU]}, ensure_ascii=False))
            html = q14(c.eval('guideIngResultHtml_()'))
            check('성분 2개 · 품목 4개' in html, '성분·품목 합계가 없습니다: %s' % html[:200])
            check('💊 아토르바스타틴' in html and '제약사 3곳 · 3품목' in html,
                  '성분 헤더(제약사 수·품목 수)가 없습니다')
            check('최고 57%' in html and '최저 345원' in html, '성분별 요약(최고 요율·최저 약가)이 없습니다')
            for label in ['한국파비스제약', '(주)일화', '휴비스트제약', '아토브정10/10mg', '621804250',
                          '1,254원', '57%', '+ 담기', 'data-guide-pick']:
                check(label in html, '성분 표에 %s 가 없습니다' % label)
            check(html.count('data-guide-pick') == 3, '펼친 성분의 품목만 그려지지 않았습니다')
            check('로수정10mg' not in html, '접힌 성분의 품목이 그려졌습니다')
            check('외 ' in js, '외 N 표기가 없습니다')

            # (B) 접기/펼치기
            c.eval("toggleGuideIngGroup('atorvastatin');")
            folded = q14(c.eval('__els["guide-ing-result"].innerHTML'))
            check('아토브정10/10mg' not in folded and '펼치기 ▼' in folded, '성분 접기가 동작하지 않습니다')
            c.eval("toggleGuideIngGroup('atorvastatin');")
            check('아토브정10/10mg' in q14(c.eval('__els["guide-ing-result"].innerHTML')),
                  '다시 펼치기가 동작하지 않습니다')

            # (C) 체크 → 선택 담기 → 담은 목록·처방전 유지목록
            c.eval("guideToggleProduct('621804250', true);")
            check(int(c.eval('guidePickCount_()')) == 1, '품목 체크가 선택 담기에 반영되지 않습니다')
            check('(1)' in q14(c.eval('guideBulkAddLabel_()')), '담기 버튼 개수가 없습니다')
            c.eval('guideIngSelectAll(true);')
            check(int(c.eval('guidePickCount_()')) == 4, '결과 전체 체크가 동작하지 않습니다')
            c.eval("STATE.rxClient = 'S001'; guideAddSelected();")
            check(int(c.eval('STATE.guidePending.length')) == 4, '선택 항목이 담기지 않았습니다')
            check(int(c.eval('STATE.rxGuideCodes.length')) == 4, '처방전 유지목록에 들어가지 않았습니다')
            toast = q14(c.eval('__toasts[__toasts.length - 1]'))
            check('4개 품목을 담았습니다' in toast, '담기 안내가 없습니다: %s' % toast)
            check('푸른정의원' in toast, '담을 병원 안내가 없습니다')
            c.eval('guideIngSelectAll(false);')
            check(int(c.eval('guidePickCount_()')) == 0, '체크 해제가 동작하지 않습니다')

            # (D) 검색 결과에서 고른 품목이 원장님 안내용 출력 대상에 들어간다
            c.eval("STATE.guideIngData.groups.forEach(function (g) { (g.items || []).forEach(guideCacheProduct_); });")
            c.eval("STATE.guidePending = []; STATE.rxGuideCodes = [];")   # v1.21 — 담은 목록이 비었을 때의 출력 대상
            c.eval("guideToggleProduct('640902490', true);")
            rows = json.loads(q14(c.eval('JSON.stringify(guidePrintRows_())')))
            check(len(rows) == 1 and rows[0]['보험코드'] == '640902490',
                  '검색에서 고른 품목이 출력 대상이 아닙니다: %s' % rows)
            check(rows[0]['제약사'] == '(주)일화', '출력물 제약사가 다릅니다: %s' % rows[0]['제약사'])
            check(rows[0]['성분'] == '아토르바스타틴', '출력물 성분이 다릅니다: %s' % rows[0]['성분'])

            # (E) 검색어 입력 → 서버 검색 호출 (입력란 값은 그대로 유지)
            c2 = new_ctx()
            c2.eval("__RESULT['searchGuideIngredients'] = %s;"
                    % json.dumps({'q': '아토르', '성분키': '', 'total성분': 1, 'total품목': 3,
                                  'shown성분': 1, 'groups': [ATOR]}, ensure_ascii=False))
            c2.eval("STATE.guideIngQ = '아토르'; loadGuideIngSearch();")
            drain(c2)
            calls = json.loads(q14(c2.eval('JSON.stringify(__calls)')))
            check(len(calls) == 1 and calls[0]['fn'] == 'searchGuideIngredients',
                  '성분 검색 서버 호출이 없습니다: %s' % calls)
            check(calls[0]['args'][0]['q'] == '아토르' and calls[0]['args'][0]['성분키'] == '',
                  '검색어가 서버로 전달되지 않았습니다: %s' % calls[0]['args'][0])
            check(int(c2.eval('STATE.guideIngData.total성분')) == 1, '검색 결과가 저장되지 않았습니다')
            check(int(c2.eval('Object.keys(STATE.guideProductCache).length')) == 3,
                  '검색 품목이 캐시되지 않았습니다')
            check('로수' not in q14(c2.eval('STATE.guideIngQ')), '검색어가 바뀌었습니다')
            check(int(c2.eval('STATE.guideIngOpen.atorvastatin ? 1 : 0')) == 1,
                  '검색 결과 성분이 자동으로 펼쳐지지 않았습니다')

            # (F) 성분 줄 '외 N 보기' → 성분키로 그 성분 전체 조회
            c3 = new_ctx()
            c3.eval("__RESULT['searchGuideIngredients'] = %s;"
                    % json.dumps({'q': '', '성분키': 'atorvastatin', 'total성분': 1, 'total품목': 3,
                                  'shown성분': 1, 'groups': [ATOR]}, ensure_ascii=False))
            c3.eval("guideOpenIngredient('atorvastatin', '아토르바스타틴');")
            drain(c3)
            calls3 = json.loads(q14(c3.eval('JSON.stringify(__calls)')))
            check(calls3[0]['args'][0]['성분키'] == 'atorvastatin' and calls3[0]['args'][0]['q'] == '',
                  '성분키 조회가 아닙니다: %s' % calls3[0]['args'][0])
            check(q14(c3.eval('STATE.guideIngQ')) == '아토르바스타틴', '검색창에 성분명이 안 들어갔습니다')
            check(q14(c3.eval('__els["guide-ing-q"].value')) == '아토르바스타틴',
                  '검색창 입력칸이 갱신되지 않았습니다')
            check(int(c3.eval('STATE.guideIngOpen.atorvastatin ? 1 : 0')) == 1, '성분이 펼쳐지지 않았습니다')

            # (G) 지우기·빈 검색어
            c3.eval('clearGuideIngSearch();')
            check(q14(c3.eval('STATE.guideIngQ')) == '' and c3.eval('STATE.guideIngData === null'),
                  '지우기가 동작하지 않습니다')
            hint = q14(c3.eval('guideIngResultHtml_()'))
            check('로수바스타틴' in hint and '💊 선택 항목 담기' in hint, '검색 안내 문구가 없습니다')
            c4 = new_ctx()
            c4.eval("STATE.guideIngData = { q: '없는약', groups: [], total성분: 0, total품목: 0 };")
            empty = q14(c4.eval('guideIngResultHtml_()'))
            check('맞는 경구제가 없습니다' in empty, '검색 결과 없음 안내가 없습니다')
    except ImportError:
        print('(quickjs 없음 — 성분 검색 실행 검사 생략: pip install quickjs)')

    # 15) v1.20 — 👀 비회원 맛보기 (메뉴 미리보기: 들어가기는 되고 기능은 잠금)
    doc15 = open(INDEX, encoding='utf-8').read()   # 앞선 실행 검사에서 html 이 조각으로 바뀌었을 수 있어 다시 읽습니다
    check('id="guest-btn"' in doc15 and 'enterGuestPreview()' in doc15,
          '로그인 화면에 👀 비회원 맛보기 버튼이 없습니다')
    check('👀 비회원 맛보기 (메뉴 미리보기)' in doc15,
          '비회원 맛보기 버튼 이름이 다릅니다')
    check('guestMode: false' in js, 'STATE.guestMode 가 없습니다')
    check("const GUEST_DEPT = '내과'" in js and 'GUEST_INTERNAL_RX_' in js,
          '비회원 공개 자료(내과)가 없습니다')
    check('내과 다처방 순위와 메뉴 구성을 둘러볼 수 있습니다' in js, '비회원 모드 안내 문구가 없습니다')
    check('🔒 승인된 회원 전용 기능입니다' in js, '잠긴 메뉴 안내 문구가 없습니다')
    check('🔒 비회원 미리보기 화면 — 실제 데이터·수수료율·입력·검색·저장 기능은 회원 가입 승인 후 이용 가능합니다' in js,
          '미리보기 상단 배너 문구가 요청과 다릅니다')
    check('🔒 회원 가입 승인 후 이용 가능합니다' in js, '미리보기 잠금 안내 문구가 없습니다')
    for need in ['enterGuestPreview', 'exitGuestPreview', 'renderGuestPreview',
                 'guestBannerHtml_', 'guestRankHtml_', 'guestNavHtml_',
                 'guestLockedNotice', 'guestGroups_', 'setGuestUi_',
                 'guestPreviewBannerHtml_', 'guestPreviewLocked', 'guestPreviewPageHtml_',
                 'guestPreviewBody_', 'renderGuestMenuPage', 'gpCard_']:
        check('function %s' % need in js, '비회원 맛보기에 %s 가 없습니다' % need)

    # 15-0) 메뉴마다 미리보기 분기가 있는지 (MASTER 전용은 잠금)
    menu_block = js[js.index('const APP_MENUS = ['):]
    menu_block = menu_block[:menu_block.index('\n   ];')]
    menu_entries = re.findall(r"\{\s*\n\s*id: '([a-z]+)',(.*?)\n     \}", menu_block, re.S)
    preview_body = extract_fn(js, 'guestPreviewBody_') or ''
    check(len(menu_entries) >= 11, 'APP_MENUS 를 읽지 못했습니다: %d' % len(menu_entries))
    for mid, entry in menu_entries:
        if 'masterOnly: true' in entry:
            continue
        check("menuId === '%s'" % mid in preview_body,
              '%s 메뉴의 비회원 미리보기 화면이 없습니다' % mid)

    # 15-a) 서버 호출 차단 · 잠긴 메뉴 차단이 함수 맨 앞에 있는지
    run_block = extract_fn(js, 'runServer') or ''
    check('STATE.guestMode' in run_block[:400] and 'Promise.reject' in run_block[:500],
          'runServer 에 비회원 모드 서버 호출 차단이 없습니다')
    switch_block = extract_fn(js, 'switchMenu') or ''
    check('STATE.guestMode' in switch_block[:400] and switch_block.find('STATE.guestMode') < switch_block.find('APP_MENUS'),
          'switchMenu 에 비회원 모드 분기가 없습니다')
    check('renderGuestMenuPage(menuId)' in switch_block,
          'switchMenu 가 비회원 모드에서 메뉴 미리보기를 열지 않습니다')
    check("!canUseMenu(guestMenu)" in switch_block,
          'switchMenu 가 비회원 모드에서 MASTER 전용 메뉴를 막지 않습니다')
    active_block = extract_fn(js, 'renderActiveMenu') or ''
    check('STATE.guestMode' in active_block and 'renderGuestPreview' in active_block,
          'renderActiveMenu 에 비회원 모드 차단이 없습니다')
    check('if (STATE.guestMode) return;' in (extract_fn(js, 'renderBirthdayBanner') or ''),
          '비회원 모드에서 생일 배너가 막히지 않았습니다')
    check('STATE.guestMode) { guestLockedNotice(); return; }' in (extract_fn(js, 'refreshBootstrap') or ''),
          '비회원 모드에서 데이터 새로고침이 막히지 않았습니다')
    check('STATE.guestMode = false;' in (extract_fn(js, 'clearLocalSession') or ''),
          '로그아웃·복귀 시 비회원 모드가 초기화되지 않습니다')

    # 15-b) 공개 자료는 내과 25성분 · 질환군/순위/성분명/대표제품만 (시트 사본과 대조)
    guest_m = re.search(r'/\* GUEST_RX_START \*/(.*?)/\* GUEST_RX_END \*/', js, re.S)
    check(bool(guest_m), '비회원 공개 자료 블록 표시가 없습니다')
    rows_js = []
    gblock = guest_m.group(1) if guest_m else ''
    if gblock:
        rows_js = re.findall(
            r"\{ 질환군: '([^']*)', 순위: (\d+), 성분명: '([^']*)', 대표제품: '([^']*)' \}", gblock)
        check(len(rows_js) == 25, '비회원 내과 성분 건수가 25건이 아닙니다: %d' % len(rows_js))
        for bad in ['수수료', '우리제품', '기준단가', '시장가', '처방포인트', '보험코드']:
            check(bad not in gblock, '비회원 공개 자료에 %s 가 들어 있습니다' % bad)
        try:
            import json as _json
            fx = _json.load(open(os.path.join(HERE, 'fixtures', 'sheets.json'), encoding='utf-8'))
            fx_rows = [[str(r[1]).strip(), str(r[2]).strip(), str(r[3]).strip(), str(r[5]).strip()]
                       for r in fx['진료과성분'][1:] if r and r[0] == '내과']
            js_rows = [[a.strip(), b.strip(), c.strip(), d.strip()] for a, b, c, d in rows_js]
            check(js_rows == fx_rows, '비회원 내과 성분이 시트(진료과성분)와 다릅니다')
        except (KeyError, ValueError, OSError) as e:  # noqa: BLE001
            check(False, '비회원 공개 자료를 시트 사본과 대조하지 못했습니다: %s' % e)

    # 15-c) 화면·메뉴 실행 검사 (QuickJS)
    try:
        import quickjs
        import json as _json

        def q15(v):
            return v.decode() if isinstance(v, bytes) else v

        def gp_open_controls(h):
            """미리보기 HTML 안에서 잠기지 않은 입력칸·버튼 (배너 🔑 로그인 버튼만 허용)."""
            bad = []
            for m in re.finditer(r'<(input|select|textarea)\b([^>]*)>', h):
                if 'disabled' not in m.group(2):
                    bad.append(m.group(0))
            for m in re.finditer(r'<button\b([^>]*)>', h):
                attrs = m.group(1)
                if 'disabled' in attrs:
                    continue
                if 'onclick="exitGuestPreview()"' in attrs:
                    continue
                bad.append('<button' + attrs + '>')
            return bad

        guest_notice = ''
        nm = re.search(r"const GUEST_NOTICE = '([^']*)';", js)
        if nm:
            guest_notice = nm.group(1)
        guest_rows = [{'질환군': a, '순위': int(b), '성분명': c, '대표제품': d}
                      for a, b, c, d in rows_js]

        names15 = ['guestGroups_', 'guestBannerHtml_', 'guestRankHtml_', 'guestNavHtml_',
                   'guestLockedNotice', 'renderGuestPreview', 'setGuestUi_',
                   'enterGuestPreview', 'exitGuestPreview', 'clearLocalSession',
                   'buildNavMenus', 'canUseMenu', 'switchMenu', 'renderActiveMenu', 'runServer',
                   'guestPreviewBannerHtml_', 'guestPreviewLocked', 'guestPreviewPageHtml_',
                   'guestPreviewBody_', 'renderGuestMenuPage', 'gpInput_', 'gpSelect_',
                   'gpArea_', 'gpBtn_', 'gpTable_', 'gpKpi_', 'gpForm_', 'gpCard_']
        blocks15 = [extract_fn(js, n) for n in names15]
        missing15 = [n for n, b in zip(names15, blocks15) if b is None]
        check(not missing15, '비회원 맛보기 함수를 추출하지 못했습니다: %s' % missing15)

        # 메뉴 미리보기에서 확인할 메뉴 (MASTER 전용 docs 는 제외)
        guest_menu_ids = ['board', 'clients', 'clientinfo', 'perf', 'guide', 'prescription',
                          'order', 'collection', 'drug', 'turnover', 'ledger']
        guest_menu_labels = {
            'board': '공지사항 · 게시판', 'clients': '거래처 등록/관리', 'clientinfo': '거래처 상세정보',
            'perf': '월별 실적', 'guide': '처방 셋팅', 'prescription': '처방전 입력',
            'order': '주사제 주문', 'collection': '수금 등록', 'drug': '약 검색 · 금기',
            'turnover': '주문 · 회전일 관리', 'ledger': '거래원장 · 명세서'}

        if not missing15 and guest_rows:
            c = quickjs.Context()
            load_ing_ctx(c, js)
            c.eval("""
            var STATE = { guestMode: false, activeMenu: 'board', authToken: '', user: null,
              isMaster: false, clients: [], products: [], turnoverData: null, ledgerData: null,
              detailData: null, pastOrders: null, orderClientCode: '', collectionClientCode: '',
              collectionBalances: {}, mailLogs: [] };
            var __toasts = [], __els = {}, __fetch = 0, __loginShown = 0;
            function showToast(m) { __toasts.push(String(m)); }
            function showLoader() {}
            function serverError_(m) { return new Error(m); }
            function getServerUrl() { return 'https://example.invalid/exec'; }
            function fetch() { __fetch++; return Promise.resolve({}); }
            function destroyAutocompletes() {}
            function esc(s) { return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;')
              .replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;'); }
            function fmtNum(n) { return String(Math.round(Number(n || 0))); }
            function clsList() { return { _s: {}, add: function (c) { this._s[c] = 1; },
              remove: function (c) { delete this._s[c]; },
              contains: function (c) { return !!this._s[c]; },
              toggle: function (c, v) { if (v === undefined) v = !this._s[c];
                if (v) this._s[c] = 1; else delete this._s[c]; return !!this._s[c]; } }; }
            function mkEl(id) { return { id: id, _h: '', value: '', textContent: '', style: {},
              classList: clsList(), focus: function () {}, scrollIntoView: function () {},
              querySelector: function () { return null; },
              set innerHTML(v) { this._h = v; }, get innerHTML() { return this._h; } }; }
            var document = { title: '', body: { classList: clsList() },
              getElementById: function (id) { if (!__els[id]) __els[id] = mkEl(id); return __els[id]; } };
            var window = { scrollTo: function () {}, _pinUnlocked: false };
            var sessionStorage = { getItem: function () { return ''; }, setItem: function () {}, removeItem: function () {} };
            var APP_MENUS = [
              { id: 'board', label: '공지사항 · 게시판', shortLabel: '공지', icon: '📢' },
              { id: 'clients', label: '거래처 등록/관리', shortLabel: '거래처', icon: '🏥' },
              { id: 'clientinfo', label: '거래처 상세정보', shortLabel: '상세', icon: '🏥' },
              { id: 'perf', label: '월별 실적', shortLabel: '실적', icon: '📈' },
              { id: 'guide', label: '처방 셋팅', shortLabel: '셋팅', icon: '🧭' },
              { id: 'prescription', label: '처방전 입력', shortLabel: '처방전', icon: '💊' },
              { id: 'order', label: '주사제 주문', shortLabel: '주사주문', icon: '💉' },
              { id: 'collection', label: '수금 등록', shortLabel: '수금', icon: '💰' },
              { id: 'drug', label: '약 검색 · 금기', shortLabel: '약검색', icon: '🔎' },
              { id: 'turnover', label: '주문 · 회전일 관리', shortLabel: '주문', icon: '📊' },
              { id: 'ledger', label: '거래원장 · 명세서', shortLabel: '원장', icon: '📑' },
              { id: 'docs', label: '발송이력 · 설정', shortLabel: '설정', icon: '✉️', masterOnly: true }
            ];
            """)
            c.eval("const GUEST_MENU_ID = 'guest';")
            c.eval("const GUEST_DEPT = '내과';")
            c.eval("const GUEST_NOTICE = " + _json.dumps(guest_notice, ensure_ascii=False) + ";")
            c.eval("const GUEST_LOCK_MSG = '🔒 승인된 회원 전용 기능입니다';")
            c.eval("const GUEST_PREVIEW_NOTICE = '🔒 비회원 미리보기 화면 — 실제 데이터·수수료율·입력·검색·저장 기능은 회원 가입 승인 후 이용 가능합니다';")
            c.eval("const GUEST_PREVIEW_LOCK_MSG = '🔒 회원 가입 승인 후 이용 가능합니다';")
            c.eval("const GUEST_MASTER_MSG = '🔒 MASTER 전용 메뉴입니다 — 마스터 계정에서만 열 수 있습니다';")
            c.eval("const GUEST_PREVIEW_ROW = '회원 가입 승인 후 실제 자료가 표시됩니다';")
            c.eval("const GUEST_INTERNAL_RX_ = " + _json.dumps(guest_rows, ensure_ascii=False) + ";")
            for b in blocks15:
                c.eval(b)
            c.eval("function showLoginScreen(m) { __loginShown++; document.getElementById('login-error').textContent = m || ''; "
                   "document.getElementById('login-overlay').classList.remove('hidden'); }")

            # (A) 진입 — 서버 호출 0, 배너 + 내과 순위
            check(c.eval('enterGuestPreview() ? 1 : 0') == 1, '비회원 맛보기 진입이 실패했습니다')
            check(c.eval('STATE.guestMode ? 1 : 0') == 1, 'STATE.guestMode 가 켜지지 않았습니다')
            check(int(c.eval('__fetch')) == 0, '비회원 진입에서 서버(fetch)를 호출했습니다')
            page = q15(c.eval("__els['main-content'].innerHTML"))
            for need in ['비회원 맛보기 모드', '내과 다처방 성분 순위', '고혈압·이상지질혈증', '당뇨병',
                         '소화기·위염', '간·담도', '통풍·골다공증', '암로디핀', '노바스크정', '메트포르민',
                         '로그인 / 회원가입', '25성분']:
                check(need in page, '비회원 화면에 %s 가 없습니다' % need)
            check(page.count('<input') == 0, '비회원 화면에 입력칸(검색창)이 있습니다')
            for bad in ['%', '담기', 'PDF', 'data-guide', 'onclick="guide',
                        'onclick="loadGuide', 'onclick="openInject', 'onclick="printGuide',
                        'data-board-no', '거래처코드']:
                check(bad not in page, '비회원 화면에 내부 기능/자료(%s)가 노출됩니다' % bad)

            # (B) 사이드바 · 모바일 하단 바 — 내과 순위 + 메뉴 미리보기(들어가기 가능) + MASTER 전용 잠금
            side = q15(c.eval("__els['sidebar-nav'].innerHTML"))
            mob = q15(c.eval("__els['mobile-nav'].innerHTML"))
            check('내과 다처방 순위' in side and '메뉴 미리보기' in side, '사이드바 미리보기 안내가 없습니다')
            check(side.count('guest-locked') == 1 and mob.count('guest-locked') == 1,
                  'MASTER 전용 메뉴만 잠금 표시여야 합니다 (잠금 %d/%d)'
                  % (side.count('guest-locked'), mob.count('guest-locked')))
            for mid in guest_menu_ids:
                check("switchMenu('%s')" % mid in side, '사이드바에 %s 미리보기 메뉴가 없습니다' % mid)
                check("switchMenu('%s')" % mid in mob, '모바일 메뉴에 %s 미리보기 메뉴가 없습니다' % mid)
            check("switchMenu('docs')" not in side and "switchMenu('docs')" not in mob,
                  'MASTER 전용 메뉴가 미리보기로 열립니다')
            check('🔒 발송이력 · 설정' in side, 'MASTER 전용 메뉴 잠금 표시가 없습니다')
            check("switchMenu('guest')" in side, '사이드바 맛보기 메뉴 연결이 없습니다')

            # (C) 모든 메뉴를 눌러 미리보기 화면으로 이동 — 전환 후에도 서버 0건 · 자료·수수료율 없음 · 기능 잠금
            prev = q15(c.eval("__els['main-content'].innerHTML"))
            for mid in guest_menu_ids:
                c.eval("switchMenu('%s');" % mid)
                check(q15(c.eval('STATE.activeMenu')) == mid, '%s 메뉴로 화면 전환이 안 됩니다' % mid)
                p = q15(c.eval("__els['main-content'].innerHTML"))
                check(p != prev, '%s 메뉴를 눌러도 화면이 바뀌지 않습니다' % mid)
                check('비회원 미리보기 화면' in p, '%s 미리보기에 잠금 배너가 없습니다' % mid)
                check('로그인 / 회원가입' in p, '%s 미리보기에 🔑 로그인 버튼이 없습니다' % mid)
                check(guest_menu_labels[mid] in p, '%s 미리보기에 메뉴 이름이 없습니다' % mid)
                check('👀 미리보기' in p, '%s 미리보기에 미리보기 표시가 없습니다' % mid)
                check('🔒' in p, '%s 미리보기에 잠금 표시가 없습니다' % mid)
                open_ctl = gp_open_controls(p)
                check(not open_ctl, '%s 미리보기에 잠기지 않은 입력·버튼이 있습니다: %s' % (mid, open_ctl[:2]))
                handlers = set(re.findall(r'onclick="([^"]+)"', p))
                check(handlers <= {'exitGuestPreview()', 'guestPreviewLocked()'},
                      '%s 미리보기에 실제 기능 연결이 남아 있습니다: %s' % (mid, handlers))
                ptext = re.sub(r'<[^>]+>', ' ', p)   # 태그·style 은 빼고 화면에 보이는 글자만 검사
                check(not re.search(r'\d+(?:\.\d+)?\s*%', ptext),
                      '%s 미리보기에 수수료율(%%) 표시가 있습니다' % mid)
                check(not re.search(r'\d{1,3}(,\d{3})+', ptext), '%s 미리보기에 실제 금액으로 보이는 숫자가 있습니다' % mid)
                check(not re.search(r'S\d{3}', p), '%s 미리보기에 거래처코드로 보이는 값이 있습니다' % mid)
                prev = p
                nav_now = q15(c.eval("__els['sidebar-nav'].innerHTML"))
                check('guest-preview-nav active' in nav_now, '%s 메뉴가 사이드바에서 선택 표시되지 않습니다' % mid)
            check(int(c.eval('__fetch')) == 0, '메뉴 미리보기를 도는 동안 서버(fetch)를 호출했습니다')

            # (D) MASTER 전용 메뉴는 맛보기에서 열리지 않는다
            before = q15(c.eval("__els['main-content'].innerHTML"))
            c.eval("switchMenu('docs');")
            check(q15(c.eval('STATE.activeMenu')) != 'docs', 'MASTER 전용 메뉴가 비회원 모드에서 열렸습니다')
            check(q15(c.eval('__toasts[__toasts.length - 1]')).startswith('🔒 MASTER 전용'),
                  'MASTER 전용 메뉴 잠금 안내가 없습니다')
            check(q15(c.eval("__els['main-content'].innerHTML")) == before,
                  'MASTER 전용 메뉴가 화면을 바꿨습니다')

            # (E) 잠금 안내 · renderActiveMenu · 내과 순위 복귀
            c.eval("guestPreviewLocked();")
            check(q15(c.eval('__toasts[__toasts.length - 1]')) == '🔒 회원 가입 승인 후 이용 가능합니다',
                  '미리보기 잠금 안내 토스트가 다릅니다')
            c.eval("guestLockedNotice();")
            check(q15(c.eval('__toasts[__toasts.length - 1]')) == '🔒 승인된 회원 전용 기능입니다',
                  '잠금 안내 토스트가 다릅니다')
            c.eval("STATE.activeMenu = 'perf'; renderActiveMenu();")
            check('📈 월별 실적' in q15(c.eval("__els['main-content'].innerHTML")),
                  'renderActiveMenu 가 고른 메뉴 미리보기를 그리지 않습니다')
            c.eval("switchMenu('guest');")
            check('25성분' in q15(c.eval("__els['main-content'].innerHTML")),
                  '내과 다처방 순위로 돌아오지 못합니다')

            # (F) 비회원 모드에서는 서버 호출이 막힌다
            c.eval("runServer('getBootstrapData', []);")
            check(int(c.eval('__fetch')) == 0, '비회원 모드인데 runServer 가 서버를 호출했습니다')

            # (G) 🔑 로그인 / 회원가입 → 비회원 상태 초기화 + 로그인 화면 + 정상 메뉴 복구
            c.eval('exitGuestPreview();')
            check(c.eval('STATE.guestMode ? 1 : 0') == 0, '복귀 후 guestMode 가 남아 있습니다')
            check(int(c.eval('__loginShown')) == 1, '복귀 시 로그인 화면이 뜨지 않았습니다')
            check(int(c.eval('__els["main-content"].innerHTML.length')) == 0, '복귀 후 맛보기 화면이 남아 있습니다')
            side2 = q15(c.eval("__els['sidebar-nav'].innerHTML"))
            check('guest-locked' not in side2 and 'guest-preview-nav' not in side2 and '공지사항 · 게시판' in side2,
                  '복귀 후 정상 메뉴로 돌아오지 않았습니다')
            check(q15(c.eval("__els['guest-login-btn'].style.display")) == 'none',
                  '복귀 후 모바일 로그인 버튼이 남아 있습니다')
    except ImportError:
        print('(quickjs 없음 — 비회원 맛보기 실행 검사 생략: pip install quickjs)')

    # 15-d) v1.18 — 메뉴판 맨 위 브랜드 영역에서 담당자 개인 이름 빼기
    brand_block = extract_fn(js, 'updateUserUi') or ''
    check('담당자명' not in brand_block.split("brand-sub")[1].split(';')[0]
          if 'brand-sub' in brand_block else False,
          '메뉴판 맨 위 브랜드 부제에 담당자명이 남아 있습니다')
    try:
        import quickjs

        def q15b(v):
            return v.decode() if isinstance(v, bytes) else v

        names15b = ['updateUserUi', 'setGuestUi_']
        blocks15b = [extract_fn(js, n) for n in names15b]
        if all(blocks15b):
            c = quickjs.Context()
            load_ing_ctx(c, js)
            c.eval("""
            var APP_VERSION = 'v1.21';
            var STATE = { guestMode: false, isMaster: false,
              user: { 아이디: 'choi', 담당자명: '최충의' },
              settings: { 회사명: '수메디팜', 담당자명: '최충의' } };
            var __els = {};
            function esc(s) { return String(s == null ? '' : s); }
            function clsList() { return { _s: {}, toggle: function (c, v) { this._s[c] = v; } }; }
            function mkEl(id) { return { id: id, _h: '', value: '', textContent: '', style: {},
              classList: clsList(), set innerHTML(v) { this._h = v; }, get innerHTML() { return this._h; } }; }
            var document = { title: '', body: { classList: clsList() },
              getElementById: function (id) { if (!__els[id]) __els[id] = mkEl(id); return __els[id]; } };
            """)
            for b in blocks15b:
                c.eval(b)
            c.eval('updateUserUi();')
            sub = q15b(c.eval("__els['brand-sub'].textContent"))
            check(sub == '수메디팜 · v1.21', '메뉴판 브랜드 부제가 회사명·버전이 아닙니다: %s' % sub)
            check('최충의' not in sub, '메뉴판 맨 위에 개인 이름이 남아 있습니다: %s' % sub)
            check(q15b(c.eval("__els['m-user'].style.display")) == 'none',
                  '모바일 상단 바에 개인 이름 칩이 남아 있습니다')
            check(q15b(c.eval("__els['sidebar-user'].innerHTML")).find('최충의') != -1,
                  '사이드바 하단 계정 표시에서 사용자 이름이 사라졌습니다')
    except ImportError:
        print('(quickjs 없음 — 메뉴판 브랜드 이름 검사 생략: pip install quickjs)')

    # 16) v1.21 — 🛒 처방 셋팅 '담은 품목 목록' (검색 결과 바로 아래 · 심평원 급여 가이드 위)
    check("'<div id=\"guide-picked\"></div>'" in js,
          '처방 셋팅에 담은 품목 목록 자리(#guide-picked)가 없습니다')
    oral_fn = extract_fn(js, 'renderGuideOralHtml_') or ''
    check(oral_fn != '', 'renderGuideOralHtml_ 를 찾지 못했습니다')
    if oral_fn:
        check(oral_fn.index('guideIngSearchCardHtml_()') < oral_fn.index('guide-picked')
              < oral_fn.index('guide-coverage') < oral_fn.index('guide-body'),
              '담은 품목 목록이 검색 결과와 심평원 급여 가이드 사이에 있지 않습니다')
    for need in ['guidePickedList_', 'guidePickedRow_', 'guidePickedCardHtml_', 'renderGuidePicked',
                 'guideRemovePicked', 'guideClearPicked', 'guideSendPickedToRx']:
        check('function %s' % need in js, 'v1.21 담은 품목 목록에 %s 가 없습니다' % need)
    for need in ['🛒 담은 품목 목록', '전체 비우기', '💊 처방전 입력으로 보내기',
                 '원장님 안내용 출력 / PDF', '✕ 빼기', '총 ']:
        check(need in js, 'v1.21 담은 품목 목록 카드에 %s 가 없습니다' % need)
    # 검색·담기·체크 어느 경로에서도 카드가 다시 그려지는지 (스크롤 유지를 위해 목록만 갱신)
    for fn_name, label in [('guideSyncPickUI_', '체크'), ('guideSyncPendingUI_', '담기'),
                           ('toggleGuideAll', '전체 선택')]:
        body = extract_fn(js, fn_name) or ''
        check('renderGuidePicked()' in body, '%s 시 담은 품목 목록이 갱신되지 않습니다' % label)
    check('renderGuidePicked()' in (extract_fn(js, 'renderGuidePage') or ''),
          '처방 셋팅 화면을 그릴 때 담은 품목 목록이 그려지지 않습니다')
    # 비회원 미리보기에는 담은 품목 목록을 내보내지 않습니다 (기능·수수료율 잠금 유지)
    gp_body16 = extract_fn(js, 'guestPreviewBody_') or ''
    check('guide-picked' not in gp_body16 and '담은 품목 목록' not in gp_body16,
          '비회원 미리보기에 담은 품목 목록이 노출됩니다')
    # 출력/PDF 도 담은 목록(체크 + 담기) 그대로
    gpr = extract_fn(js, 'guidePrintRows_') or ''
    check('guidePickedList_()' in gpr, '원장님 안내용 출력이 담은 품목 목록을 쓰지 않습니다')

    # 16-a) 담은 품목 목록 실행 검사 — 표시 · 빼기 · 전체 비우기 · 처방전 전송
    try:
        import quickjs
        import json as _json16

        def q16(v):
            return v.decode() if isinstance(v, bytes) else v

        names16 = ['guidePickedList_', 'guidePickedRow_', 'guidePickedCardHtml_', 'renderGuidePicked',
                   'guideRemovePicked', 'guideClearPicked', 'guideSendPickedToRx',
                   'guideToggleProduct', 'guideToggleIngredient', 'guideSyncPickUI_', 'guideSyncPendingUI_',
                   'guideAddSelected', 'guideAddItem', 'guideCacheProduct_', 'guideFindProduct_',
                   'guidePendingSet_', 'guidePendingCount_', 'guideSendBtnLabel_', 'guidePickCodes_',
                   'guidePickCount_', 'guideBulkAddLabel_', 'guideCodesOfIngredient_', 'applyGuidePending',
                   'rxCodeNorm_', 'rxCodeKey_', 'makerOf_', 'makerFromName_', 'rxDedupeRows_']
        blocks16 = [extract_fn(js, n) for n in names16]
        missing16 = [n for n, b in zip(names16, blocks16) if b is None]
        check(not missing16, 'v1.21 담은 품목 목록 함수를 추출하지 못했습니다: %s' % missing16)

        ATOR16 = {
            '성분키': 'atorvastatin', '성분명': '아토르바스타틴', '분류': '고지혈증치료제',
            '품목수': 2, '제약사수': 2, '최고수수료율': 57, '최저약가': 1254, '잘림': False,
            'items': [
                {'표': '경구', '보험코드': '621804250', '품목명': '아토브정10/10mg', '규격': '10정',
                 '제약사': '한국파비스제약', '약가': 1254, '수수료율': 57, '급여구분': '급여', '성분': '아토르바스타틴'},
                {'표': '경구', '보험코드': '640902490', '품목명': '아토타틴정10mg', '규격': '10정',
                 '제약사': '(주)일화', '약가': 1971, '수수료율': 34, '급여구분': '급여', '성분': '아토르바스타틴'},
            ],
        }
        ROSU16 = {
            '성분키': 'rosuvastatin', '성분명': '로수바스타틴', '분류': '고지혈증치료제',
            '품목수': 1, '제약사수': 1, '최고수수료율': 40, '최저약가': 500, '잘림': False,
            'items': [
                {'표': '경구', '보험코드': '641601230', '품목명': '로수정10mg', '규격': '10정',
                 '제약사': '한화제약㈜', '약가': 500, '수수료율': 40, '급여구분': '급여', '성분': '로수바스타틴'},
            ],
        }

        if not missing16:
            c = quickjs.Context()
            load_ing_ctx(c, js)
            c.eval("""
            var STATE = {
              guideIngQ: '아토르', guideIngKey: '', guideIngOpen: {}, guideIngLoading: false,
              guideIngData: null, guidePick: {}, guidePending: [], rxGuideCodes: [],
              rxClient: 'S001', rxRows: [], rxDirty: false,
              guideProductCache: {}, guideData: null, guideRec: null, guideSelected: {},
              products: [], rxFrequent: [], clients: [], guideDept: '', guideMode: 'maxrate',
              guideMaxMakers: 3, guideMaker: '', guideMakerQ: '', guideMakerData: null
            };
            var __toasts = [], __menus = [], __els = {}, __renders = 0, __sums = 0;
            function showToast(m) { __toasts.push(String(m)); }
            function esc(s) { return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;')
              .replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;'); }
            function fmtNum(n) { return String(Math.round(Number(n || 0))).replace(/\\B(?=(\\d{3})+(?!\\d))/g, ','); }
            function findClient(code) {
              if (String(code) === 'S001') return { 거래처코드: 'S001', 거래처명: '푸른정의원' };
              return null;
            }
            function switchMenu(id) { __menus.push(String(id)); }
            function renderActiveMenu() {}
            function renderRxRows() { __renders++; }
            function updateRxSummary() { __sums++; }
            var document = { querySelectorAll: function () { return []; },
              getElementById: function (id) {
                if (!__els[id]) __els[id] = { _h: '', value: '', title: '', className: '', classList: { add: function () {}, remove: function () {} },
                  set innerHTML(v) { this._h = v; }, get innerHTML() { return this._h || ''; } };
                return __els[id];
              } };
            """)
            check(load_maker_ctx(c, js), '앱 내장 제약사 목록을 실행 문맥에 넣지 못했습니다')
            for b in blocks16:
                c.eval(b)

            def card():
                return q16(c.eval("(__els['guide-picked'] || {}).innerHTML || ''"))

            # (A) 성분을 펼쳐 체크 → 아래 담은 품목 목록에 성분·품목·제약사·보험코드·약가·요율이 산다
            c.eval('STATE.guideIngData = ' + _json16.dumps(
                {'q': '아토르', 'total성분': 1, 'total품목': 2, 'shown성분': 1, 'groups': [ATOR16]},
                ensure_ascii=False) + '; '
                # 실제 화면(loadGuideIngSearch)처럼 검색 결과를 보험코드로 기억해 둡니다
                'STATE.guideIngData.groups.forEach(function (g) { (g.items || []).forEach(guideCacheProduct_); });'
                'renderGuidePicked();')
            empty = card()
            check('🛒 담은 품목 목록' in empty and '총 0개' in empty,
                  '처음 화면에 담은 품목 목록(0개)이 없습니다: %s' % empty[:200])
            check('아직 담은 품목이 없습니다' in empty, '담은 품목이 없을 때 안내가 없습니다')
            c.eval("guideToggleProduct('621804250', true);")
            html1 = card()
            for need in ['아토르바스타틴', '아토브정10/10mg', '한국파비스제약', '621804250', '1,254원', '57%',
                         '총 1개', '✕ 빼기', 'guideRemovePicked', '전체 비우기',
                         '💊 처방전 입력으로 보내기 (1)', '🖨️ 원장님 안내용 출력 / PDF']:
                check(need in html1, '담은 목록에 %s 가 없습니다' % need)
            check('guideSendPickedToRx' in html1, '담은 목록에서 처방전 전송 버튼이 연결되지 않았습니다')
            check(int(c.eval('guidePickedList_().length')) == 1, '체크한 품목이 담은 목록에 들어가지 않았습니다')

            # (B) 다른 성분·다른 화면으로 옮겨 다녀도 담은 목록은 그대로
            c.eval("STATE.guideMaker = '한화제약'; STATE.guideMakerQ = '한화제약'; STATE.guideIngData = null; renderGuidePicked();")
            keep = card()
            check('아토브정10/10mg' in keep and '총 1개' in keep,
                  '제약사 필터로 옮기면 담은 목록이 사라집니다: %s' % keep[:200])
            c.eval('STATE.guideIngData = ' + _json16.dumps(
                {'q': '로수', 'total성분': 1, 'total품목': 1, 'shown성분': 1, 'groups': [ROSU16]},
                ensure_ascii=False) + "; STATE.guideMaker = ''; "
                "STATE.guideIngData.groups.forEach(function (g) { (g.items || []).forEach(guideCacheProduct_); });"
                "guideToggleProduct('641601230', true);")
            two = card()
            check('아토브정10/10mg' in two and '로수정10mg' in two and '총 2개' in two,
                  '검색을 옮겨 담아도 이전 품목이 남지 않습니다: %s' % two[:300])
            check('1,754원' in two, '담은 목록 약가 합계가 다릅니다: %s' % two[:300])
            c.eval('guideAddSelected();')
            check('총 2개' in card(), '선택 항목 담기 뒤 담은 목록이 중복으로 늘었습니다')
            check(int(c.eval('guidePickedList_().length')) == 2, '담은 목록 중복 제거가 안 됩니다')

            # (C) ✕ 빼기 — 담은 목록·체크에서 함께 빠지고 위 품목 표의 체크도 풀린다
            c.eval("guideRemovePicked('621804250');")
            removed = card()
            check('아토브정10/10mg' not in removed and '로수정10mg' in removed and '총 1개' in removed,
                  '✕ 빼기가 담은 목록에서 지우지 못했습니다: %s' % removed[:300])
            check(c.eval("STATE.guidePick['621804250'] ? 1 : 0") == 0, '✕ 빼기가 체크를 풀지 않았습니다')
            check(q16(c.eval('__toasts[__toasts.length - 1]')).find('뺐습니다') != -1, '✕ 빼기 안내가 없습니다')

            # (D) 전체 비우기
            c.eval('guideClearPicked();')
            cleared = card()
            check('총 0개' in cleared and '아직 담은 품목이 없습니다' in cleared,
                  '전체 비우기가 담은 목록을 비우지 못했습니다: %s' % cleared[:200])
            check(int(c.eval('STATE.guidePending.length')) == 0 and int(c.eval('guidePickCount_()')) == 0,
                  '전체 비우기 뒤에도 담은 품목·체크가 남아 있습니다 ')

            # (E) 💊 처방전 입력으로 보내기 — 담은 목록 그대로 처방전 화면으로
            c.eval("guideToggleProduct('640902490', true); guideToggleProduct('641601230', true);")
            c.eval('guideSendPickedToRx();')
            sent = _json16.loads(q16(c.eval("JSON.stringify([__menus[__menus.length - 1], STATE.guidePending.slice().sort(), STATE.rxGuideCodes.slice().sort()])")))
            check(sent == ['prescription', ['640902490', '641601230'], ['640902490', '641601230']],
                  '담은 목록이 처방전 화면으로 그대로 넘어가지 않았습니다: %s' % sent)
            check(q16(c.eval('__toasts[__toasts.length - 1]')).find('푸른정의원') != -1,
                  '담을 병원 안내가 없습니다: %s' % q16(c.eval('__toasts[__toasts.length - 1]')))
            c.eval('applyGuidePending();')
            got16 = q16(c.eval("STATE.rxRows.map(function (r) { return r.보험코드; }).sort().join(',')"))
            check(got16 == '640902490,641601230', '담은 목록이 처방전 목록에 들어가지 않았습니다: %s' % got16)

            # (F) 담은 것이 없으면 보내지 않고 안내만
            c.eval('STATE.guidePending = []; STATE.guidePick = {}; STATE.rxGuideCodes = [];')
            before_menus = int(c.eval('__menus.length'))
            c.eval('guideSendPickedToRx();')
            check(int(c.eval('__menus.length')) == before_menus, '담은 것이 없는데 화면을 옮겼습니다')
            check(q16(c.eval('__toasts[__toasts.length - 1]')).find('담은 품목이 없습니다') != -1,
                  '담은 것이 없을 때 안내가 없습니다')
    except ImportError:
        print('(quickjs 없음 — v1.21 담은 품목 목록 실행 검사 생략: pip install quickjs)')

    # 17) v1.21 — 🏭 제약사를 고르면 성분 칩은 기본 10개만 (너무 많다는 요청)
    check('const LIMIT = 10;' in js and 'const LIMIT = 60;' not in js,
          '제약사 성분 칩이 기본 10개로 줄지 않았습니다')
    check("'개 더 보기 ▼'" in js, '성분 더 보기 버튼 문구가 없습니다')

    try:
        import quickjs
        import json as _json17

        def q17(v):
            return v.decode() if isinstance(v, bytes) else v

        names17 = ['guideMakerResultHtml_', 'guideMakerTableHtml_', 'guideMakerKeyOf_', 'toggleGuideMakerMore',
                   'renderGuideMakerResult']
        blocks17 = [extract_fn(js, n) for n in names17]
        missing17 = [n for n, b in zip(names17, blocks17) if b is None]
        check(not missing17, '제약사 성분 칩 함수를 추출하지 못했습니다: %s' % missing17)
        if not missing17:
            c = quickjs.Context()
            load_ing_ctx(c, js)
            ings = [{'성분키': 'k%02d' % i, '성분명': '성분%02d' % i, '품목수': i + 1} for i in range(25)]
            c.eval("""
            var STATE = { guideMaker: '한화제약', guideMakerQ: '한화제약', guideMakerMore: false,
              guideMakerKey: '', guideMakerGroup: null, guideMakerIngLoading: false,
              guideMakerData: null };
            function esc(s) { return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;')
              .replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;'); }
            function fmtNum(n) { return String(Math.round(Number(n || 0))).replace(/\\B(?=(\\d{3})+(?!\\d))/g, ','); }
            var __els17 = {};
            var document = { getElementById: function (id) { return __els17[id] || null; } };
            """)
            for b in blocks17:
                c.eval(b)
            c.eval('STATE.guideMakerData = ' + _json17.dumps(
                {'maker': '한화제약', 'q': '', '성분목록': ings, 'total성분': 25, 'total품목': 325},
                ensure_ascii=False) + ';')
            folded17 = q17(c.eval('guideMakerResultHtml_()'))
            check(folded17.count('data-guide-maker-ing') == 10,
                  '제약사 성분 칩이 10개가 아닙니다: %d' % folded17.count('data-guide-maker-ing'))
            check('성분15' not in folded17 and '성분09' in folded17, '처음부터 10개를 넘겨 그립니다')
            check('15개 더 보기 ▼' in folded17, '남은 성분 더 보기 버튼이 없습니다: %s' % folded17[-300:])
            check('10개</b>만 먼저 보여 줍니다' in folded17, '성분 10개만 보인다는 안내가 없습니다')
            c.eval('toggleGuideMakerMore();')
            opened17 = q17(c.eval('guideMakerResultHtml_()'))
            check(opened17.count('data-guide-maker-ing') == 25,
                  '더 보기를 눌러도 전체 성분이 안 나옵니다: %d' % opened17.count('data-guide-maker-ing'))
            check('접기 ▲' in opened17, '더 보기 뒤 접기 버튼이 없습니다')
            # 성분이 10개 이하면 더 보기 버튼 없음
            c.eval('STATE.guideMakerMore = false; STATE.guideMakerData.성분목록 = STATE.guideMakerData.성분목록.slice(0, 4);')
            few17 = q17(c.eval('guideMakerResultHtml_()'))
            check(few17.count('data-guide-maker-ing') == 4 and '더 보기' not in few17,
                  '성분이 10개 이하일 때 더 보기 버튼이 뜹니다')
    except ImportError:
        print('(quickjs 없음 — 제약사 성분 칩 검사 생략: pip install quickjs)')

    print('=' * 62)
    if fails:
        print('클라이언트 검사: %d개 중 %d개 실패' % (checks, len(fails)))
        for f in fails:
            print('  ✗ %s' % f)
    else:
        print('클라이언트 검사: %d개 모두 통과' % checks)
    print('=' * 62)
    return 0 if not fails else 1


if __name__ == '__main__':
    sys.exit(main())
