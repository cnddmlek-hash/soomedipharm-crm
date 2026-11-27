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

    # 2) v1.4 요소
    check("const APP_VERSION = 'v1.4'" in js, 'APP_VERSION 이 v1.4 가 아닙니다')
    check("id: 'drug'" in js and 'renderDrugPage' in js, '약 검색 메뉴가 없습니다')
    check("id: 'guide'" in js and 'renderGuidePage' in js, '처방 가이드 메뉴가 없습니다')
    check('id="rg-name" autocomplete="name" placeholder="홍길동"' in html, '회원가입 이름 예시가 홍길동이 아닙니다')
    check('renderDashSearchCard' in js and 'onDashSearch' in js, '대시보드 바로 검색이 없습니다')
    check('birthday-banner' in js and 'renderBirthdayBanner' in js, '생일 알림 배너가 없습니다')
    check('kpicSearch' in js and 'kpicDrugDetail' in js, '약학정보원 연계 호출이 없습니다')
    check('getDeptGuide' in js and 'recommendRegimen' in js, '처방 가이드/추천 호출이 없습니다')
    check('saveClientProfile' in js and 'submitClientProfile' in js, '원장 정보 저장이 없습니다')
    check('loadBirthdaySettings' in js and 'installBirthdayTrigger' in js, '생일 알림 설정이 없습니다')
    check('applyGuidePending' in js, '처방전으로 보내기 연결이 없습니다')

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
        check('v1.4' in code, 'Code.gs 버전이 v1.4 가 아닙니다')
    else:
        print('(Code.gs 없음 — 서버 함수 대조 생략)')

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
