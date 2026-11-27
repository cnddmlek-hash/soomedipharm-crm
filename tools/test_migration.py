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

    # ---------------- 2. 자료 파일
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
