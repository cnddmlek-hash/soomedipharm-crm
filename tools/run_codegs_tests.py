#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Code.gs 회귀 테스트 실행기
--------------------------------------------------------------------
구글 Apps Script 없이, 실제 Code.gs 를 QuickJS 위에서 모의 환경(mock_apps_script.js)
과 함께 실행해 v1.1~v1.4 기능을 검증합니다.

사용:
    python3 tools/run_codegs_tests.py                 # 기본(fixtures/sheets.json)
    python3 tools/run_codegs_tests.py --fixtures 경로  # 다른 시트 데이터로 실행
    python3 tools/run_codegs_tests.py --verbose        # 실패 케이스 메시지까지

준비물: pip install quickjs
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(HERE)


def load_engine():
    try:
        import quickjs  # type: ignore
        return quickjs
    except ImportError:
        sys.exit('quickjs 가 필요합니다: pip install quickjs')


def read(path):
    with open(path, encoding='utf-8') as f:
        return f.read()


def find_codegs():
    for cand in [
        os.path.join(PROJECT, '..', '..', 'downloads', 'Code.gs'),
        os.path.join(HERE, 'Code.gs'),
    ]:
        p = os.path.abspath(cand)
        if os.path.exists(p):
            return p
    sys.exit('Code.gs 를 찾지 못했습니다. downloads/Code.gs 경로를 확인해 주세요.')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--fixtures', default=os.path.join(HERE, 'fixtures', 'sheets.json'))
    ap.add_argument('--kpic', default=os.path.join(HERE, 'fixtures', 'kpic_search.json'))
    ap.add_argument('--kpic-detail', default=os.path.join(HERE, 'fixtures', 'kpic_detail.json'))
    ap.add_argument('--codegs', default=None)
    ap.add_argument('--verbose', action='store_true')
    args = ap.parse_args()

    quickjs = load_engine()
    codegs_path = args.codegs or find_codegs()

    fixtures = read(args.fixtures)
    kpic = {
        'search': json.loads(read(args.kpic)),
        'detail': json.loads(read(args.kpic_detail)),
    }

    ctx = quickjs.Context()
    ctx.eval('var __FIXTURES_JSON = ' + json.dumps(fixtures) + ';')
    ctx.eval('var __KPIC_JSON = ' + json.dumps(json.dumps(kpic)) + ';')

    # 모의 환경 → 실제 Code.gs → 테스트 순서로 같은 전역에서 실행
    for path in [os.path.join(HERE, 'mock_apps_script.js'), codegs_path, os.path.join(HERE, 'test_codegs.js')]:
        try:
            ctx.eval(read(path))
        except Exception as e:  # noqa: BLE001
            print('스크립트 실행 실패: %s\n%s' % (path, e))
            # 테스트 결과가 있으면 그대로 보여 줍니다.
            raw = ctx.get('__TEST_RESULT__') if hasattr(ctx, 'get') else None
            if raw:
                print(raw)
            return 2

    raw = ctx.eval('__TEST_RESULT__')
    if isinstance(raw, bytes):
        raw = raw.decode('utf-8')
    result = json.loads(raw)
    failed = [c for c in result['cases'] if not c['ok']]

    print('=' * 62)
    print('Code.gs 테스트: 통과 %d / 실패 %d' % (result['passed'], result['failed']))
    if failed:
        for case in failed:
            print('  ✗ %s — %s' % (case['name'], case.get('err', '')))
    elif args.verbose:
        for case in result['cases']:
            print('  ✓ %s' % case['name'])
    print('=' * 62)
    return 0 if result['failed'] == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
