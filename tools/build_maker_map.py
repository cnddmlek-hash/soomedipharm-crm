#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
제품마스터 제약사(실제 제조사) 목록을 index.html 에 심습니다.
--------------------------------------------------------------------
· 페이서써플라이(주)는 취급 도매상이고, '제약사' 칸에는 실제 제조사가 들어갑니다.
· 시트 서버(Apps Script)가 아직 v1.14 이하일 때도 화면에 실제 제조사가 뜨도록
  앱 안에 같은 목록을 넣어 둡니다(서버가 v1.15 이상이면 서버 값이 먼저 쓰입니다).

사용:
    python3 tools/build_maker_map.py                 # tools/product_makers.json → index.html
    python3 tools/build_maker_map.py --check         # 파일과 index.html 이 같은지만 확인
"""
import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(HERE)
INDEX = os.path.join(PROJECT, 'index.html')
DATA = os.path.join(HERE, 'product_makers.json')

START = '/* MAKER_MAP_START */'
END = '/* MAKER_MAP_END */'


def js_block(mapping):
    """{코드: 제약사} → JS 객체 리터럴 (한 줄에 6개씩)"""
    items = ['%s: %s' % (json.dumps(k, ensure_ascii=False), json.dumps(v, ensure_ascii=False))
             for k, v in mapping.items()]
    lines = []
    for i in range(0, len(items), 6):
        lines.append('     ' + ', '.join(items[i:i + 6]))
    body = ',\n'.join(lines)
    return (START + '\n' +
            '   const PRODUCT_MAKER_BY_CODE_ = {\n' + body + '\n   };\n' +
            '   ' + END)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--data', default=DATA, help='보험코드 → 제약사 JSON')
    ap.add_argument('--index', default=INDEX, help='index.html 경로')
    ap.add_argument('--check', action='store_true', help='고치지 않고 같은지만 확인')
    args = ap.parse_args()

    mapping = json.load(open(args.data, encoding='utf-8'))
    mapping = {str(k): str(v).strip() for k, v in mapping.items() if str(v).strip()}
    html = open(args.index, encoding='utf-8').read()

    new_block = js_block(mapping)
    pattern = re.compile(re.escape(START) + r'.*?' + re.escape(END), re.S)
    if not pattern.search(html):
        sys.exit('index.html 에 %s … %s 구역이 없습니다.' % (START, END))

    updated = pattern.sub(lambda m: new_block, html, count=1)
    if args.check:
        same = updated == html
        print('제약사 목록 %d개 — index.html 과 %s' % (len(mapping), '같습니다' if same else '다릅니다'))
        return 0 if same else 1

    if updated == html:
        print('변경 없음 — 제약사 목록 %d개가 이미 반영되어 있습니다.' % len(mapping))
        return 0
    open(args.index, 'w', encoding='utf-8').write(updated)
    print('index.html 반영 완료 — 제약사 %d개 (실제 제조사)' % len(mapping))
    return 0


if __name__ == '__main__':
    sys.exit(main())
