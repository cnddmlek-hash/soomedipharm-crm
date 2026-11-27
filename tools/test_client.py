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

    # 2) v1.11 요소
    check("const APP_VERSION = 'v1.11'" in js, 'APP_VERSION 이 v1.11 이 아닙니다')
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

    # 2-c) v1.7 — 비거래처 사전조회(심평원 HIRA)
    check('renderHiraPage' in js and '비거래처 심평원(HIRA) 사전조회' in js, '비거래처 사전조회 화면이 없습니다')
    # 메뉴 순서: 거래처 등록/관리 → 거래처 상세정보 → 월별 실적 → 처방 셋팅 → 처방전 입력 → 주사제 주문 → 수금 등록 → 약 검색 → 주문 → 원장 → 설정
    order_ids = re.findall(r"\n       id: '([a-z]+)',", js)
    expect_order = ['clients', 'clientinfo', 'perf', 'guide', 'prescription', 'order', 'collection', 'drug', 'turnover', 'ledger', 'docs']
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
        ctx.eval('''
          var STATE = { orderTab: 'entry', orderClientCode: '', injPay: '', injMode: 'maxrate',
                        injLimit: 20, injCat: '', injQuery: '', injProtoQuery: '', injData: null,
                        injProto: null, injSelected: {}, clients: [], guideDept: '', coverage: null };
          var document = { getElementById: function () { return null; } };
          function esc(s) { return String(s == null ? '' : s); }
          function fmtNum(n) { return String(Math.round(Number(n || 0))); }
          function payTypeBadge() { return ''; }
          function findClient() { return null; }
          function loadInjectGuide() {} function loadInjectProtocols() {}
          function loadCoverageNotes() {} function renderGuideDeptChips() {} function renderGuideBody() {}
          function v14NoticeHtml_() { return ''; }
          function renderActiveMenu() {}
        ''')
        names = ['orderTabBar_', 'orderInjectStripHtml_', 'injCautionsHtml_', 'renderInjectPanelHtml_',
                 'renderInjectBody', 'renderInjectRecommend', 'renderInjectProtocols', 'renderInjectCards',
                 'renderOrderPage', 'renderGuidePage', 'renderGuideOralHtml_', 'guideHospitalBarHtml_']
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
