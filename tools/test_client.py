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
    m = re.search(r'\n   function %s\(' % re.escape(name), js)
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

    # 2) v1.6 요소
    check("const APP_VERSION = 'v1.7'" in js, 'APP_VERSION 이 v1.7 이 아닙니다')
    check('id: \'drug\'' in js and 'renderDrugPage' in js, '약 검색 메뉴가 없습니다')
    check("id: 'guide'" in js and 'renderGuidePage' in js, '처방 셋팅 메뉴가 없습니다')
    check('guideTabBar_' in js and 'switchGuideTab' in js, '경구제/주사제 탭이 없습니다')
    check("'💊 경구제 셋팅 (원외처방)'" in js or '경구제 셋팅 (원외처방)' in js, '경구제 셋팅 탭이 없습니다')
    check('주사제 셋팅 (원내 주사·수액)' in js, '주사제 셋팅 탭이 없습니다')
    check('renderInjectPanelHtml_' in js and 'renderInjectBody' in js, '주사제 셋팅 화면이 없습니다')
    check('runInjectRecommend' in js and 'loadInjectGuide' in js, '주사제 셋팅 조회가 없습니다')
    check('injectSendToOrder' in js and 'copyInjectSet' in js, '주사제 → 매출/세팅 연결이 없습니다')
    check('경구제 전용' in js and '주사제 전용' in js, '제형 전용 배지가 없습니다')
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

    # 2-c) v1.7 — 비거래처 사전조회(심평원 HIRA)
    check("id: 'hira'" in js and 'renderHiraPage' in js, '비거래처 사전조회 메뉴가 없습니다')
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
        check('v1.7' in code, 'Code.gs 버전이 v1.7 이 아닙니다')
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

    # 5) 순수 함수 실행 (QuickJS)
    try:
        import quickjs
        ctx = quickjs.Context()
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
                 'guideRxTargetBadge_', 'guideHospitalBarHtml_', 'guideSetHospital', 'rxOpenFromGuide',
                 'rxApplyGuideRecNow', 'rxOpenGuideFromRx']
        blocks = [extract_fn(js, n) for n in names]
        if any(b is None for b in blocks):
            check(False, '가이드→처방전 함수를 추출하지 못했습니다: %s' % [n for n, b in zip(names, blocks) if b is None])
        else:
            ctx = quickjs.Context()
            ctx.eval('''
            var STATE = {
              guideRec: { picks: [
                { 보험코드: 'E100', 품목명: '베아셋정', 규격: '', 제약사: '대웅바이오', 약가: 1063, 수수료율: 54, 성분: '아세트아미노펜' },
                { 보험코드: 'E200', 품목명: '아토타틴정10mg', 규격: '', 제약사: '(주)일화', 약가: 1971, 수수료율: 34, 성분: '아토르바스타틴' }
              ] },
              guideData: null, guideProductCache: {}, guidePending: [], rxGuideCodes: [],
              rxRows: [], rxClient: '', rxFrequent: [], products: [],
              rxDirty: false, rxMonth: '2026-11', clients: [],
              guideDept: '', guideTab: 'oral'
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
    except ImportError:
        pass

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
