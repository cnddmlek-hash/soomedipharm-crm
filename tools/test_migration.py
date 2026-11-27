#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
시트 스키마·이관 데이터 검사
--------------------------------------------------------------------
· Code.gs 의 SHEET_HEADERS 와 실제 시트 머리글이 어긋나지 않는지
· v1.4 로 새로 넣는 자료(타사단가표·성분사전·진료과성분·시장자료·제품 성분명)가
  업로드 가능한 상태인지(빈 값·중복·숫자 형식) 확인

사용:
    python3 tools/test_migration.py                      # fixtures 로 검사
    python3 tools/test_migration.py --data-dir ../../work/v14   # 실제 적재분 검사
"""
import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(HERE)
CODEGS = os.path.abspath(os.path.join(PROJECT, '..', '..', 'downloads', 'Code.gs'))

BASE_HEADERS = {
    '거래처': ['거래처코드', '거래처명', '유통구분', '사업유형', '진료과', '담당자', '연락처', '이메일', '주소', '회전일경고기준', '사용여부', '메모'],
    '제품마스터': ['보험코드', '제품명', '규격', '기준단가', '수수료율', '급여구분', '시장가'],
    '사용자': ['아이디', '비밀번호', '담당자명', '권한', '사용여부'],
}
V14_TABS = {'타사단가표', '시장자료', '성분사전', '진료과성분'}

fails = []
checks = 0


def check(cond, label):
    global checks
    checks += 1
    if not cond:
        fails.append(label)


def num(v):
    try:
        return float(str(v).replace(',', '').strip() or 0)
    except ValueError:
        return None


def parse_headers(code):
    block = re.search(r"const SHEET_HEADERS = \{(.*?)\n\};", code, re.S).group(1)
    out = {}
    for name, body in re.findall(r"'([^']+)':\s*\[(.*?)\]", block, re.S):
        out[name] = re.findall(r"'([^']+)'", body)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--data-dir', default=os.path.join(HERE, 'fixtures'))
    args = ap.parse_args()
    d = os.path.abspath(args.data_dir)

    # ---------------- 1. Code.gs 머리글 정의
    code = open(CODEGS, encoding='utf-8').read() if os.path.exists(CODEGS) else ''
    if code:
        heads = parse_headers(code)
        for name, base in BASE_HEADERS.items():
            got = heads.get(name, [])
            check(got[:len(base)] == base, '%s 기존 열 순서가 바뀌었습니다: %s' % (name, got[:len(base)]))
        check(heads.get('거래처', [])[-3:] == ['원장성함', '원장생일', '취향/특이사항'], '거래처 v1.4 열이 뒤에 붙지 않았습니다')
        check(heads.get('제품마스터', [])[-2:] == ['성분명', '성분키'], '제품마스터 성분 열이 없습니다')
        check(heads.get('사용자', [])[-2:] == ['이메일', '요율등급'], '사용자 이메일·요율등급 열 순서가 다릅니다: %s' % heads.get('사용자'))

        # v1.6 요율등급 — 서버 상수·기본값
        check("const RATE_TIER_CUTS = { '1단계': 1, '2단계': 2, '3단계': 3 }" in code, 'RATE_TIER_CUTS 정의가 다릅니다')
        check("const DEFAULT_STAFF_TIER = '2단계'" in code, '기존 STAFF 기본 등급이 2단계가 아닙니다')
        check("const NEW_SIGNUP_TIER = '3단계'" in code, '신규 가입 기본 등급이 3단계가 아닙니다')
        for name in ['rateCutPercent_', 'applyRateCut_', 'publicUser_', 'updateUserTier', 'setUserTierCell_', 'productRateMap_']:
            check(name in code, 'Code.gs 에 %s 가 없습니다' % name)
        check(re.search(r'updateUserTier\s*:\s*updateUserTier', code) is not None, 'updateUserTier 가 apiFunctions_ 에 없습니다')
        for tab in V14_TABS:
            check(tab in heads and len(heads[tab]) >= 6, '%s 탭 머리글이 없습니다' % tab)
        check(heads.get('진료과성분', [])[-1] == '처방포인트', '진료과성분 처방포인트 열이 없습니다')
        check(heads.get('주사프로토콜', [])[:7] == ['구분', '분류', '케이스', '참고제품(예시)', '성분', '성분키', '상대성분키'],
              '주사프로토콜 머리글이 다릅니다: %s' % heads.get('주사프로토콜'))
        check(heads.get('주사프로토콜', [])[-2:] == ['출처', '중요'], '주사프로토콜 출처·중요 열이 없습니다')
        check(heads.get('급여가이드') == ['구분', '항목', '내용', '근거', '중요'], '급여가이드 머리글이 다릅니다')

    # ---------------- 2-b. v1.5 제형 구분 (경구제 / 주사·수액)
    if code:
        for name in ['looksParenteral_', 'dosageFormOf_', 'productsOfForm_', 'productIndexByIngredient_',
                     'injectCategoryOf_', 'injectPicks_', 'getInjectGuide']:
            check(name in code, 'Code.gs 에 %s 가 없습니다' % name)
        check("const APP_VERSION = 'v1.7'" in code, 'Code.gs 버전이 v1.7 이 아닙니다')
        check(re.search(r'getInjectGuide\s*:\s*getInjectGuide', code) is not None, 'getInjectGuide 가 apiFunctions_ 에 없습니다')

    # ---------------- 2-f. v1.7 거래처코드 Sxxx 채번 · 심평원 연동
    if code:
        check('function nextClientCode_' in code, 'nextClientCode_ 가 없습니다')
        check(re.search(r"return 'S' \+ \(next <= 999", code) is not None, 'Sxxx/S1000 채번 규칙이 다릅니다')
        check('nextClientCode_(allRaw' in code, 'saveClient 가 nextClientCode_ 를 쓰지 않습니다')
        sc = re.search(r'function saveClient\(payload, token\)\s*\{(.*?)\n\}', code, re.S)
        check(bool(sc), 'saveClient 를 찾지 못했습니다')
        if sc:
            check('/^C(' not in sc.group(1) and "C0001" not in sc.group(1), 'saveClient 에 옛 C0001 채번이 남아 있습니다')
        for name in ['getHiraPrevisitBriefing', 'checkHiraApi', 'hiraCall_', 'hiraSearchHospitals_',
                     'hiraHospitalExtras_', 'hiraMapDeptsToGuide_', 'buildHiraBriefing_', 'hiraNonPayTagsOf_']:
            check(name in code, 'Code.gs 에 %s 가 없습니다' % name)
        check('apis.data.go.kr/B551182' in code, '심평원 API 주소가 없습니다')
        check(re.search(r'getHiraPrevisitBriefing\s*:\s*getHiraPrevisitBriefing', code) is not None,
              'getHiraPrevisitBriefing 이 apiFunctions_ 에 없습니다')

    # ---------------- 2-d. v1.5.1 최소 제약사 — 상한 안에서 요율 최대화
    if code:
        for name in ['recommendMinMakers_', 'evalMakerSet_', 'cmpMakerEval_', 'betterPick_',
                     'MINMAKER_EPS_', 'MINMAKER_MAX_ITER_']:
            check(name in code, 'Code.gs 에 %s 가 없습니다' % name)
        check('상한1평균수수료율' in code and '요율향상' in code, 'Code.gs 에 상한 1곳 비교 요약이 없습니다')

    # ---------------- 2-g. v1.7 보수 — 보험코드 앞자리 0 보존 · 중복 방지
    if code:
        for name in ['normalizeInsuranceCode_', 'insuranceCodeKey_', 'normalizeMonth_']:
            check(name in code, 'Code.gs 에 %s 가 없습니다' % name)
        sp = re.search(r'function savePrescriptions\(payload, token\)\s*\{(.*?)\n\}', code, re.S)
        check(bool(sp), 'savePrescriptions 를 찾지 못했습니다')
        if sp:
            body = sp.group(1)
            check("textCols: ['기준월', '보험코드']" in body,
                  '처방 저장이 기준월·보험코드를 텍스트 서식으로 쓰지 않습니다')
            check('insuranceCodeKey_' in body and 'normalizeMonth_' in body,
                  '처방 저장이 정규화 키로 기존 줄을 찾지 않습니다')
            check("String(it['보험코드'] || '').trim()" not in body,
                  '처방 저장이 보험코드를 정규화하지 않고 그대로 쿳니다')
        wr = re.search(r'function writeRowByHeaders_\(sheet, dataObj, rowIndex, opts\)\s*\{(.*?)\n\}', code, re.S)
        check(bool(wr) and 'setNumberFormat' in wr.group(1), 'writeRowByHeaders_ 에 텍스트 서식 처리가 없습니다')
        qk = re.search(r'function getPrescriptionQuickItems\(clientCode, token\)\s*\{(.*?)\n\}', code, re.S)
        check(bool(qk) and 'insuranceCodeKey_' in qk.group(1), '빠른 입력 목록이 보험코드를 정규화하지 않습니다')
        gp = re.search(r'function getPrescriptions\(month, clientCode, token\)\s*\{(.*?)\n\}', code, re.S)
        check(bool(gp) and 'insuranceCodeKey_' in gp.group(1), '처방 조회가 보험코드 중복을 합치지 않습니다')

    # ---------------- 2-c. v1.5 제형 구분 (경구제 / 주사·수액) — fixtures 기준
    # ---------------- 3. 자료 파일
    def load(name):
        p = os.path.join(d, name)
        if not os.path.exists(p):
            return None
        return json.load(open(p, encoding='utf-8'))

    # ---------------- 3-b. v1.5 제형 구분 (경상제/주사) — fixtures 기준
    fx = load('sheets.json')
    # ---------------- 2-e. v1.6 요율등급 — 기존 STAFF 2단계 · MASTER 공란
    if isinstance(fx, dict) and '사용자' in fx:
        ut = fx['사용자']
        if ut and '요율등급' in ut[0]:
            hi = ut[0].index('요율등급')
            tiers = {}
            for r in ut[1:]:
                tier = str(r[hi]).strip() if len(r) > hi else ''
                tiers.setdefault(str(r[ut[0].index('권한')]).strip().upper(), []).append(tier)
            check(tiers.get('MASTER') == [''], 'MASTER 계정의 요율등급은 공란이어야 합니다: %s' % tiers.get('MASTER'))
            bad = [t for t in tiers.get('STAFF', []) if t not in ('1단계', '2단계', '3단계')]
            check(not bad, 'STAFF 요율등급 값이 이상합니다: %s' % bad)
            check(tiers.get('STAFF', []).count('2단계') >= 1, '기존 STAFF 가 2단계가 아닙니다: %s' % tiers.get('STAFF'))
        else:
            check(False, 'fixtures 사용자 탭에 요율등급 열이 없습니다')

    # ---------------- 3-a. v1.7 거래처코드 Sxxx · 심평원 fixture
    if isinstance(fx, dict) and '거래처' in fx:
        g = fx['거래처']
        if g and '거래처코드' in g[0]:
            ci = g[0].index('거래처코드')
            codes = [str(r[ci]).strip() if len(r) > ci else '' for r in g[1:]]
            bad = [c for c in codes if not re.fullmatch(r'S\d{3,}', c)]
            check(not bad, 'Sxxx 형식이 아닌 거래처코드: %s' % bad[:5])
            check(len(set(codes)) == len(codes), '거래처코드 중복')
            check(codes == sorted(codes, key=lambda x: int(x[1:])), '거래처코드가 행 순서대로가 아닙니다')
    # ---------------- 3-c. 보험코드 앞자리 0 — fixtures 가 텍스트로 들어 있는지
    if isinstance(fx, dict) and '이엘파마품목' in fx:
        el2 = fx['이엘파마품목']
        ci = el2[0].index('보험코드')
        codes = [r[ci] for r in el2[1:] if len(r) > ci and str(r[ci]).strip()]
        str_codes = [c for c in codes if isinstance(c, str)]
        check(len(str_codes) == len(codes), '이엘파마품목 보험코드에 숫자로 굳은 값이 있습니다')
        zeros = [c for c in str_codes if c.startswith('0')]
        check(len(zeros) >= 5, '앞자리 0 보험코드가 fixtures 에 부족합니다: %d' % len(zeros))
        bad_len = [c for c in str_codes if c.isdigit() and len(c) != 9]
        check(not bad_len, '9자리가 아닌 이엘파마 보험코드: %s' % bad_len[:5])
    if isinstance(fx, dict) and '처방내역' in fx and len(fx['처방내역']) > 1:
        hr = fx['처방내역'][0]
        ci = hr.index('보험코드')
        mi = hr.index('기준월')
        for r in fx['처방내역'][1:]:
            code_v = r[ci]
            check(isinstance(code_v, str) and code_v.isdigit() and len(code_v) == 9,
                  '처방내역 보험코드가 9자리 텍스트가 아닙니다: %s' % code_v)
            check(re.fullmatch(r'\d{4}-\d{2}', str(r[mi])) is not None,
                  '처방내역 기준월이 YYYY-MM 이 아닙니다: %s' % r[mi])

    hira_path = os.path.join(d, 'hira.json')
    if os.path.exists(hira_path):
        hf = json.load(open(hira_path, encoding='utf-8'))
        hosp = hf.get('hospitals') or []
        check(len(hosp) >= 4, 'hira fixture 병원이 부족합니다: %d' % len(hosp))
        yk = {h.get('ykiho') for h in hosp}
        check(len(yk) == len(hosp) and all(yk), 'hira fixture 요양기호 누락/중복')
        for key in ('dgsbjt', 'asm', 'nonpay'):
            for y in (hf.get(key) or {}):
                check(y in yk, 'hira fixture %s 의 요양기호가 병원목록에 없습니다: %s' % (key, y))
        check(any('글루타치온' in str(x.get('npayKorNm') or '') for x in (hf.get('nonpay') or {}).get('YKI_HOSP_DONGNAE', [])),
              'hira fixture 에 백옥주사(글루타치온) 비급여 항목이 없습니다')
        check(any(x.get('asmGrd09') for x in (hf.get('asm') or {}).get('YKI_INT_DONGNAE', [])),
              'hira fixture 에 약품목수 평가등급이 없습니다')

    if isinstance(fx, dict) and '제품마스터' in fx and '이엘파마품목' in fx:
        def tab_rows(tab):
            t = fx[tab]
            return [dict(zip(t[0], r)) for r in t[1:]]
        PAREN_WORD = re.compile(r'(주사|수액|앰플|바이알|프리필드|PFS|펜주|점적|관류액)', re.I)
        PAREN_TAIL = re.compile(r'주(?:$|[\s/\d(),])')

        def looks_paren(name):
            s = str(name or '').strip()
            if not s:
                return False
            return bool(PAREN_WORD.search(s) or PAREN_TAIL.search(s))

        pm = tab_rows('제품마스터')
        el = tab_rows('이엘파마품목')
        pm_paren = [r for r in pm if looks_paren(r.get('제품명'))]
        el_paren = [r for r in el if looks_paren(r.get('품목명'))]
        check(len(pm) >= 200, '제품마스터가 부족합니다: %d' % len(pm))
        check(len(pm_paren) >= len(pm) * 0.7,
              '제품마스터 중 주사·수액으로 안 보이는 품목이 너무 많습니다: %d/%d' % (len(pm) - len(pm_paren), len(pm)))
        check(len(el_paren) <= max(1, int(len(el) * 0.05)),
              '이엘파마(경구) 목록의 주사제 이름이 너무 많습니다: %d/%d %s' %
              (len(el_paren), len(el), [r.get('품목명') for r in el_paren[:3]]))
        check(len(el) >= 50, '이엘파마 품목이 부족합니다: %d' % len(el))

        # 최소 제약사 추천이 성립하려면 경구 품목에 제약사가 있어야 하고,
        # 같은 성분을 여러 제약사가 파는 성분이 있어야 상한 비교가 의미 있습니다.
        no_maker = [r.get('품목명') for r in el if not str(r.get('제약사') or '').strip()]
        check(not no_maker, '제약사가 빈 경구 품목: %s' % ', '.join(no_maker[:5]))
        ing_makers = {}
        for r in el:
            key = str(r.get('성분명') or '').strip()
            if not key:
                continue
            ing_makers.setdefault(key, set()).add(str(r.get('제약사') or '').strip())
        multi = [k for k, v in ing_makers.items() if len(v) > 1]
        check(len(multi) >= 5, '같은 성분을 여러 제약사가 파는 성분이 %d개뿐입니다' % len(multi))

        # 주사프로토콜 · 급여가이드 · 치과 가이드
        if '주사프로토콜' in fx:
            pr = tab_rows('주사프로토콜')
            cautions = [r for r in pr if r.get('구분') == '주의']
            protos = [r for r in pr if r.get('구분') == '프로토콜']
            cards = [r for r in pr if r.get('구분') == '제품']
            check(len(cautions) >= 10, '배합금기 주의 항목이 부족합니다: %d' % len(cautions))
            check(len(protos) >= 25, '프로토콜이 부족합니다: %d' % len(protos))
            check(len(cards) >= 12, '제품 카드가 부족합니다: %d' % len(cards))
            bare = [r.get('케이스') for r in cautions if not str(r.get('성분키') or '').strip()]
            check(not bare, '배합금기 규칙에 성분키가 없는 행: %s' % bare[:3])
            check(any('acetaminophen' in str(r.get('상대성분키') or '') for r in cautions),
                  'NAC+아세트아미노펜 배합금기 규칙이 없습니다')
            check(all(str(r.get('출처') or '').strip() for r in pr), '출처 없는 프로토콜 행이 있습니다')
            check(any('참고' in str(r.get('참고제품(예시)') or '') for r in protos),
                  '참고제품(예시) 표기가 없습니다')
        else:
            check(False, '주사프로토콜 탭이 fixtures 에 없습니다')

        if '급여가이드' in fx:
            cov = tab_rows('급여가이드')
            groups = {r.get('구분') for r in cov}
            check(len(groups) >= 6, '급여가이드 구분이 부족합니다: %s' % groups)
            check(all(str(r.get('근거') or '').strip() for r in cov), '근거 없는 급여가이드 항목이 있습니다')
            check(any('HbA1c' in str(r.get('내용') or '') for r in cov), '당뇨 1·2·3제 기준이 없습니다')
        else:
            check(False, '급여가이드 탭이 fixtures 에 없습니다')

        dg_fx = fx['진료과성분']
        check(dg_fx[0][-1] == '처방포인트', '진료과성분 처방포인트 열이 없습니다(fixtures)')
        dental = [r for r in tab_rows('진료과성분') if r.get('진료과') == '치과']
        check(len(dental) >= 18, '치과 가이드 행이 부족합니다: %d' % len(dental))
        check(len({r.get('질환군') for r in dental}) >= 6, '치과 케이스가 부족합니다')
        check(all(str(r.get('처방포인트') or '').strip() for r in dental), '치과 처방포인트가 빈 행이 있습니다')
        check(any('amoxicillin' in str(r.get('영문키') or '') for r in dental), '치과 아목시실린 행이 없습니다')

    def load(name):
        p = os.path.join(d, name)
        if not os.path.exists(p):
            return None
        return json.load(open(p, encoding='utf-8'))

    prod = load('products_ingredient.json')
    ing = load('ingredients.json')
    dept = load('dept_guide.json')
    tp = None
    for cand in ['tp_all.json', 'tp_huons.json', 'sheets.json']:
        obj = load(cand)
        if obj is None:
            continue
        if isinstance(obj, dict) and '타사단가표' in obj:
            rows = obj['타사단가표']
            head = rows[0]
            tp = [dict(zip(head, r)) for r in rows[1:]]
        elif isinstance(obj, list) and obj and isinstance(obj[0], dict):
            tp = obj
        if tp:
            break
    market = load('market.json')
    if market is None:
        fx = load('sheets.json')
        if isinstance(fx, dict) and '시장자료' in fx:
            rows = fx['시장자료']
            market = [dict(zip(rows[0], r)) for r in rows[1:]]

    # 제품 성분
    if prod:
        check(len(prod) >= 200, '제품 성분표가 너무 적습니다: %d' % len(prod))
        named = [r for r in prod if r.get('성분명')]
        check(len(named) >= len(prod) * 0.95, '성분명이 비어 있는 제품이 너무 많습니다: %d/%d' % (len(prod) - len(named), len(prod)))
        bad_key = [r['name'] for r in named if not r.get('성분키')]
        check(not bad_key, '성분키가 빈 제품: %s' % ', '.join(bad_key[:5]))

    # 성분사전
    if ing:
        keys = [r['영문키'] for r in ing]
        check(len(keys) == len(set(keys)), '성분사전 영문키 중복 %d건' % (len(keys) - len(set(keys))))
        check(all(r.get('성분명') for r in ing), '성분명이 빈 성분사전 행이 있습니다')
        keyset = set(keys)
        if prod:
            missing = sorted({r['성분키'] for r in prod if r.get('성분키') and r['성분키'] not in keyset})
            check(not missing, '성분사전에 없는 제품 성분키: %s' % ', '.join(missing[:6]))
        if dept:
            dmissing = sorted({r['영문키'] for r in dept if r.get('영문키') and r['영문키'] not in keyset})
            check(not dmissing, '성분사전에 없는 진료과 성분: %s' % ', '.join(dmissing[:6]))

    # 진료과성분
    if dept:
        by_dept = {}
        for r in dept:
            by_dept.setdefault(r['진료과'], []).append(r)
        check(len(by_dept) >= 8, '진료과가 %d개뿐입니다' % len(by_dept))
        thin = [k for k, v in by_dept.items() if len(v) < 10]
        check(not thin, '성분이 10개 미만인 진료과: %s' % ', '.join(thin))
        for name, rows in by_dept.items():
            groups = {}
            for r in rows:
                groups.setdefault(r['질환군'], []).append(int(r['순위']))
            for g, ranks in groups.items():
                check(sorted(ranks) == list(range(1, len(ranks) + 1)), '%s/%s 순위가 1부터 연속이 아닙니다' % (name, g))

    # 타사단가표
    if tp:
        check(len(tp) >= 20, '단가표 행이 너무 적습니다: %d' % len(tp))
        bad_price = [r for r in tp if r.get('단가') not in ('', None) and num(r.get('단가')) is None]
        check(not bad_price, '단가가 숫자가 아닌 행 %d개' % len(bad_price))
        zero = [r for r in tp if str(r.get('단가')) == '0']
        check(not zero, '단가 0원 행 %d개 (미확인 값은 빈칸으로)' % len(zero))
        unique = set()
        dup = []
        for r in tp:
            k = (r.get('제약사'), r.get('제품명'), r.get('규격'), r.get('수량조건'))
            if k in unique:
                dup.append(k)
            unique.add(k)
        check(not dup, '단가표 중복 행 %d개: %s' % (len(dup), dup[:2]))
        # 제품별 계단 존재
        products = {}
        for r in tp:
            products.setdefault((r.get('제약사'), r.get('제품명')), 0)
            products[(r.get('제약사'), r.get('제품명'))] += 1
        check(all(v >= 1 for v in products.values()), '계단이 없는 제품이 있습니다')
        check(all(r.get('성분키') for r in tp if r.get('성분명') and '확인 필요' not in r.get('성분명', '')), '성분명은 있는데 성분키가 빈 행이 있습니다')

    # 시장자료
    if market:
        check(len(market) >= 20, '시장자료 행이 너무 적습니다: %d' % len(market))
        bad = [r for r in market if r.get('2024년') not in ('', None) and num(r.get('2024년')) is None]
        check(not bad, '시장자료 숫자 형식 오류 %d개' % len(bad))
        check(any('GLP-1' in str(r.get('계열')) for r in market), 'GLP-1 자료가 없습니다')

    print('=' * 62)
    print('시트/이관 검사 (%s)' % d)
    if fails:
        print('  %d개 중 %d개 실패' % (checks, len(fails)))
        for f in fails:
            print('  ✗ %s' % f)
    else:
        print('  %d개 모두 통과' % checks)
    print('=' * 62)
    return 0 if not fails else 1


if __name__ == '__main__':
    sys.exit(main())
