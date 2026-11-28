# -*- coding: utf-8 -*-
"""원본 구글 독스(1dYL_...)에 보안 패치 코드를 적용한다.

이 독스는 앱 연결의 Drive 파일 범위(drive.file)에 없어서 본문 전체 교체(docs write/update)가
404 로 막히지만, find-replace 는 동작한다. 그래서 '바뀐 부분만' find-replace 로 바꾼다.
  · D = 독스의 현재 본문 텍스트, N = 패치된 Code.gs (LF)
  · 두 텍스트의 diff 에서 '코드가 바뀐 구간'만 골라, find 문자열이 독스 안에서
    유일해질 때까지 앞쪽 문맥을 늘려서 find/replace 쌍을 만든다.

사용: python3 apply_doc_patch.py --dry-run | --apply
"""
import difflib
import json
import os
import subprocess
import sys
import tempfile

DOC_ID = '1dYL_QmCIYx23Nv_2feFFxdns4aDTkgftksKWJD8PeOM'
DOC_TEXT = '/workspace/downloads/old_doc_text.txt'
NEW_TEXT = '/workspace/downloads/Code.gs.lf.txt'


def build_ops(doc, new):
    d = doc.split('\n')
    n = new.split('\n')
    sm = difflib.SequenceMatcher(None, d, n, autojunk=False)
    ops = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == 'equal':
            continue
        old_lines, new_lines = d[i1:i2], n[j1:j2]
        # 줄바꿈(빈 줄)만 다른 구간은 건드리지 않는다(독스 기존 모양 유지)
        if all(not x.strip() for x in old_lines) and all(not x.strip() for x in new_lines):
            continue
        # 첫 줄 BOM 차이는 의미 없음 — 건너뛴다
        if old_lines == ['/**'] and new_lines and new_lines[0].startswith('\ufeff'):
            continue
        # find 문자열이 독스에서 유일해질 때까지 앞 문맥을 늘린다
        start = i1
        while True:
            find_lines = d[start:i2]
            prefix = d[start:i1]
            repl_lines = prefix + new_lines
            find = '\n'.join(find_lines)
            if find.strip() and doc.count(find) == 1 and len(find) > 0:
                break
            if start == 0:
                raise SystemExit('유일한 find 문자열을 만들지 못했습니다: %r' % find_lines[:2])
            start -= 1
        ops.append({
            'tag': tag,
            'doc_lines': (i1, i2),
            'find': find,
            'replace': '\n'.join(repl_lines),
        })
    return ops


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else '--dry-run'
    doc = open(DOC_TEXT, encoding='utf-8').read()
    new = open(NEW_TEXT, encoding='utf-8').read()

    ops = build_ops(doc, new)
    print('작업 수:', len(ops))
    cur = doc
    for idx, op in enumerate(ops, 1):
        find, repl = op['find'], op['replace']
        if cur.count(find) != 1:
            raise SystemExit('미리보기 실패 — find 가 유일하지 않습니다 (#%d, %d회)' % (idx, cur.count(find)))
        cur = cur.replace(find, repl, 1)
        print('#%d [%s] find %d자 / replace %d자 · 바뀐 첫 줄: %r' %
              (idx, op['tag'], len(find), len(repl), find.split('\n')[0][:70]))

    expected = cur
    print('예상 본문 길이:', len(expected))

    if mode == '--dry-run':
        open('/workspace/downloads/doc_expected_text.txt', 'w', encoding='utf-8', newline='').write(expected)
        print('미리보기 저장 → downloads/doc_expected_text.txt')
        return 0

    cur = doc
    for idx, op in enumerate(ops, 1):
        ws_path = 'downloads/tmp_repl_%02d.txt' % idx
        with open('/workspace/' + ws_path, 'w', encoding='utf-8', newline='') as f:
            f.write(op['replace'])
        cmd = ['gog', 'docs', 'find-replace', DOC_ID, op['find'],
               '--content-file', ws_path, '--match-case', '--first']
        out = subprocess.run(cmd, capture_output=True, text=True, cwd='/workspace')
        os.unlink('/workspace/' + ws_path)
        payload = out.stdout
        try:
            result = json.loads(payload)
        except Exception:
            print('#%d 응답 해석 실패', idx, payload[:300])
            return 2
        data = result.get('data') or {}
        if not result.get('ok') or data.get('replacements') != 1:
            print('#%d 실패:', idx, json.dumps(result, ensure_ascii=False)[:400])
            return 3
        cur = cur.replace(op['find'], op['replace'], 1)
        print('#%d 적용 완료 (replacements=%s)' % (idx, data.get('replacements')))

    if cur != expected:
        print('경고: 로컬 계산 결과와 예상 본문이 다릅니다.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
