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
    check("const APP_VERSION = 'v1.8'" in js, 'APP_VERSION 이 v1.8 이 아닙니다')
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
    check('renderHiraPage' in js and '비거래처 심평원(HIRA) 사전조회' in js, '비거래처 사전조회 화면이 없습니다')
    # 메뉴 순서: 거래처 등록/관리 → 거래처 상세정보 → 월별 실적 → 처방 셋팅 → 처방전 입력 → 약 검색 → 주문 → 원장 → 설정
    order_ids = re.findall(r"\n       id: '([a-z]+)',", js)
    expect_order = ['clients', 'clientinfo', 'perf', 'guide', 'prescription', 'drug', 'turnover', 'ledger', 'docs']
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
        check("const APP_VERSION = 'v1.8'" in code, 'Code.gs 버전이 v1.8 이 아닙니다')
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
                 'rxCodeNorm_', 'rxCodeKey_', 'rxDedupeRows_']
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
