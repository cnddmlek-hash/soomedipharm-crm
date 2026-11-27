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
        check(heads.get('사용자', [])[-1] == '이메일', '사용자 이메일 열이 없습니다')
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
        check("const APP_VERSION = 'v1.5'" in code, 'Code.gs 버전이 v1.5 가 아닙니다')
        check(re.search(r'getInjectGuide\s*:\s*getInjectGuide', code) is not None, 'getInjectGuide 가 apiFunctions_ 에 없습니다')

    # ---------------- 2-d. v1.5.1 최소 제약사 — 상한 안에서 요율 최대화
    if code:
        for name in ['recommendMinMakers_', 'evalMakerSet_', 'cmpMakerEval_', 'betterPick_',
                     'MINMAKER_EPS_', 'MINMAKER_MAX_ITER_']:
            check(name in code, 'Code.gs 에 %s 가 없습니다' % name)
        check('상한1평균수수료율' in code and '요율향상' in code, 'Code.gs 에 상한 1곳 비교 요약이 없습니다')

    # ---------------- 2-c. v1.5 제형 구분 (경구제 / 주사·수액) — fixtures 기준
    # ---------------- 3. 자료 파일
    def load(name):
        p = os.path.join(d, name)
        if not os.path.exists(p):
            return None
        return json.load(open(p, encoding='utf-8'))

    # ---------------- 3-b. v1.5 제형 구분 (경상제/주사) — fixtures 기준
    fx = load('sheets.json')
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
