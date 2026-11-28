#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
v1.28 — 고시문·삭감통보서 자동 읽기(Code.gs) QuickJS 테스트
--------------------------------------------------------------------
구글 Apps Script 없이 실제 Code.gs 를 QuickJS 위에서 돌려 아래를 확인합니다.

  1) parseNoticeOrCutText_ — 문서 종류 판별(고시·공지 / 삭감통보서), 사용자가 고른 종류 우선,
     핵심 요약 3~5줄, 문서번호·조정코드·보험코드, 시행일·통보일 정규화, 빈 문서
  2) noticeAppealDraft_ — 이의신청 사유서 초안 / 고시 검토 메모 초안 문구와 빈칸
  3) analyzeNoticeOrCutDoc — OCR 성공(고시·삭감), OCR 실패(성공 응답 + 안내), 크기 초과,
     빈 파일, 미로그인 거부, 잘못된 형식, apiFunctions_ 등록

사용:
    python3 tools/test_notice_doc.py [--codegs 경로]
필요: pip install quickjs
"""
import argparse
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from test_bizcert_ocr import MOCK_JS, LOGIN_STUB_JS  # noqa: E402  (모의 Apps Script 환경 재사용)

CASES_JS = r"""
var __RESULT = { passed: 0, failed: 0, cases: [] };
function __t(name, fn) {
  try { fn(); __RESULT.passed++; __RESULT.cases.push({ name: name, ok: true }); }
  catch (e) { __RESULT.failed++; __RESULT.cases.push({ name: name, ok: false, err: String((e && e.message) || e) }); }
}
function __eq(actual, expected, msg) {
  if (String(actual) !== String(expected)) throw new Error((msg || '') + ' 기대=' + expected + ' 실제=' + actual);
}
function __ok(cond, msg) { if (!cond) throw new Error(msg || '조건이 거짓'); }
function __has(arr, needle, msg) {
  for (var i = 0; i < (arr || []).length; i++) { if (String(arr[i]).indexOf(needle) !== -1) return; }
  throw new Error((msg || '') + ' "' + needle + '" 없음 → ' + JSON.stringify(arr));
}

// ---------------------------------------------------------------- 시험용 문서
var GOSI_TEXT =
  '보건복지부 고시 제2026-312호\n' +
  '요양급여의 적용기준 및 방법에 관한 세부사항 일부개정\n' +
  '\n' +
  '1. 개정 사유\n' +
  '  약제급여목록 및 급여상한금액표 개정에 따라 약제의 급여 기준을 정비하고자 함.\n' +
  '\n' +
  '2. 주요 내용\n' +
  '  가. 리투아민 성분 주사제는 다음 상병에 한하여 급여를 인정함: [상병코드 기재]\n' +
  '  나. 수액제 세트(3종)의 산정 기준을 1일 1회로 명확히 함.\n' +
  '\n' +
  '3. 시행일: 2026.12.1부터 시행\n' +
  '\n' +
  '4. 문의: 보건복지부 보험약제과 (044-202-0000) 제2026-312호';

var CUT_TEXT =
  '건강보험심사평가원\n' +
  '심사결과통보서 (요양기관용)\n' +
  '\n' +
  '요양기관명: 서울연세내과의원\n' +
  '접수번호: 2026-11-12345\n' +
  '통보일: 2026.11.20\n' +
  '\n' +
  '1. 삭감(조정) 내역\n' +
  '   - 조정코드: 0231 / 삭감사유: 약제 투여 기준(1일 1회)을 초과하여 처방된 건으로 확인되어 1회분을 삭감 조정함.\n' +
  '   - 대상 품목: 케토롤락 트로메타민 주 30mg (보험코드 645001230)\n' +
  '   - 불인정 금액: 12,340원\n' +
  '2. 조정 사유 요약\n' +
  '   - 요양급여의 적용기준 및 방법에 관한 세부사항(보건복지부 고시)에 따라 1일 1회만 인정됨.\n' +
  '3. 이의신청은 통보일로부터 90일 이내에 가능합니다.';

// ---------------------------------------------------------------- 1. 종류 판별
__t('고시문 → 고시·공지 · 문서번호 · 시행일', function () {
  var p = parseNoticeOrCutText_(GOSI_TEXT, 'auto');
  __eq(p.docKind, '고시·공지');
  __eq(p.docKindKey, 'notice');
  __has(p.codes, '제2026-312호', '문서번호');
  __has(p.dates, '시행일 2026-12-01', '시행일');
  __ok(p.summaryLines.length >= 3 && p.summaryLines.length <= 5, '요약 3~5줄: ' + p.summaryLines.length);
  __ok(/급여|개정|산정/.test(p.summaryLines.join(' ')), '요약에 핵심 낱말');
});

__t('삭감통보서 → 삭감통보서 · 조정코드 · 통보일 · 삭감사유 요약', function () {
  var p = parseNoticeOrCutText_(CUT_TEXT, 'auto');
  __eq(p.docKind, '삭감통보서');
  __eq(p.docKindKey, 'cut');
  __has(p.codes, '조정코드 0231', '조정코드');
  __has(p.codes, '보험코드 645001230', '보험코드');
  __has(p.dates, '통보일 2026-11-20', '통보일');
  __ok(p.summaryLines.length >= 2, '요약 줄: ' + p.summaryLines.length);
  __has(p.summaryLines, '삭감', '삭감 사유 문장');
});

__t('사용자가 고른 종류가 자동 판별보다 우선', function () {
  var p1 = parseNoticeOrCutText_(CUT_TEXT, 'notice');
  __eq(p1.docKind, '고시·공지');
  __eq(p1.detectedKind, '삭감통보서');           // 읽힌 문서는 삭감통보서로 판별됨을 함께 알려 줌
  var p2 = parseNoticeOrCutText_(GOSI_TEXT, 'cut');
  __eq(p2.docKind, '삭감통보서');
  __eq(p2.detectedKind, '고시·공지');
});

__t('키워드가 없는 문서 → 종류 미확인, 앞쪽 문장으로 요약', function () {
  var p = parseNoticeOrCutText_('안내문\n이 문서는 보관용으로 출력해 두시기 바랍니다.\n문의는 담당자에게 연락해 주세요.', 'auto');
  __eq(p.docKind, '');
  __eq(p.docKindKey, '');
  __ok(p.summaryLines.length >= 1, '요약: ' + JSON.stringify(p.summaryLines));
});

__t('빈 문서 → 모두 빈 값', function () {
  var p = parseNoticeOrCutText_('   \n  ', 'auto');
  __eq(p.docKind, '');
  __eq(p.summaryLines.length, 0);
  __eq(p.codes.length, 0);
  __eq(p.dates.length, 0);
  var p2 = parseNoticeOrCutText_(null, 'auto');
  __eq(p2.summaryLines.length, 0);
});

__t('요약은 최대 5줄까지만', function () {
  var big = GOSI_TEXT + '\n' + CUT_TEXT + '\n' + CUT_TEXT;
  var p = parseNoticeOrCutText_(big, 'auto');
  __ok(p.summaryLines.length <= 5, '5줄 이하: ' + p.summaryLines.length);
});

__t('날짜 표기 여러 형태를 YYYY-MM-DD 로 · 접수번호 긴 숫자는 날짜로 보지 않음', function () {
  var p = parseNoticeOrCutText_('시행일: 2026.12.1\n적용일: 2026-12-01\n공고일: 2026년 12월 1일\n접수번호: 2026-11-12345', 'notice');
  __has(p.dates, '시행일 2026-12-01', '시행일');
  __has(p.dates, '적용일 2026-12-01', '적용일');
  __has(p.dates, '공고일 2026-12-01', '공고일');
  for (var i = 0; i < p.dates.length; i++) {
    __ok(String(p.dates[i]).indexOf('2026-11-12') === -1, '접수번호를 날짜로 오인: ' + p.dates[i]);
  }
});

// ---------------------------------------------------------------- 2. 초안 문구
__t('삭감통보서 초안 — 이의신청 제목 · 병원명 · 품목명 · 빈칸', function () {
  var p = parseNoticeOrCutText_(CUT_TEXT, 'auto');
  var d = noticeAppealDraft_(p, { clientName: '서울연세내과의원', itemName: '케토롤락 주' });
  __ok(d.indexOf('[이의신청 / 재심사조정청구 사유서 초안]') === 0, '제목: ' + d.slice(0, 40));
  __ok(d.indexOf('서울연세내과의원') !== -1, '병원명');
  __ok(d.indexOf('케토롤락 주') !== -1, '품목명');
  __ok(d.indexOf('조정코드 0231') !== -1, '조정코드');
  __ok(d.indexOf('[환자 상병/진료내역 기재]') !== -1, '확인 빈칸');
  __ok(d.indexOf('작성일: ') !== -1, '작성일');
  __ok(d.indexOf('※') !== -1, '참고 안내');
});

__t('고시문 초안 — 고시 요약·검토 메모 제목', function () {
  var p = parseNoticeOrCutText_(GOSI_TEXT, 'auto');
  var d = noticeAppealDraft_(p, { clientName: '', itemName: '' });
  __ok(d.indexOf('[고시·공지 요약 및 이의신청 근거 메모 초안]') === 0, '제목: ' + d.slice(0, 40));
  __ok(d.indexOf('[병원명 기재]') !== -1, '병원명 빈칸');
  __ok(d.indexOf('[품목명 기재]') !== -1, '품목명 빈칸');
  __ok(d.indexOf('제2026-312호') !== -1, '문서번호');
  __ok(d.indexOf('시행일 2026-12-01') !== -1, '시행일');
});

__t('종류 미확인 초안 — 일반 요약 메모', function () {
  var p = parseNoticeOrCutText_('보관용 안내문입니다. 출력해 두시기 바랍니다.', 'auto');
  var d = noticeAppealDraft_(p, {});
  __ok(d.indexOf('[문서 요약 메모 초안]') === 0, '제목: ' + d.slice(0, 30));
});

// ---------------------------------------------------------------- 3. 서버 함수
__FETCH.mode = 'ok';
__FETCH.ocrText = CUT_TEXT;
var __CUT = null;

__t('analyze: 삭감통보서 OCR 성공 · 임시문서 삭제 · 파일 미보관', function () {
  __DRIVE_CALLS.created = []; __DRIVE_CALLS.deleted = []; __FETCH.calls = [];
  __CUT = analyzeNoticeOrCutDoc({
    fileName: 'cut.jpg', mimeType: 'image/jpeg', base64: 'aGVsbG8=',
    docType: 'auto', clientName: '서울연세내과의원', itemName: '케토롤락 주'
  }, 'tok');
  __ok(__CUT.success, 'success');
  __ok(__CUT.ocrOk, 'ocrOk');
  __eq(__CUT.docKind, '삭감통보서');
  __has(__CUT.codes, '조정코드 0231');
  __has(__CUT.dates, '통보일 2026-11-20');
  __ok(__CUT.summaryLines.length >= 2, '요약 줄');
  __ok(__CUT.appealDraft.indexOf('[이의신청 / 재심사조정청구 사유서 초안]') === 0, '초안 제목');
  __ok(__CUT.rawTextPreview.indexOf('심사결과통보서') !== -1, 'rawTextPreview');
  __ok(/코드/.test(__CUT.message), '안내 문구: ' + __CUT.message);
  __eq(__DRIVE_CALLS.created.length, 0);                 // v1.28 — 파일을 따로 저장하지 않음
  __ok(__FETCH.calls.some(function (c) { return c.method === 'delete'; }), '임시 문서 삭제');
});

__t('analyze: 고시문 OCR 성공 (PDF)', function () {
  __FETCH.ocrText = GOSI_TEXT;
  var r = analyzeNoticeOrCutDoc({ fileName: 'gosi.pdf', mimeType: 'application/pdf', base64: 'aGVsbG8=', docType: 'auto' }, 'tok');
  __ok(r.success && r.ocrOk, 'success/ocrOk');
  __eq(r.docKind, '고시·공지');
  __has(r.codes, '제2026-312호');
  __has(r.dates, '시행일 2026-12-01');
  __ok(r.appealDraft.indexOf('[고시·공지 요약 및 이의신청 근거 메모 초안]') === 0, '초안 제목');
  __ok(r.message.indexOf('고시·공지') === 0, '안내 문구: ' + r.message);
});

__t('analyze: mimeType 없으면 파일 확장자로 판단', function () {
  __FETCH.ocrText = GOSI_TEXT;
  var r = analyzeNoticeOrCutDoc({ fileName: 'scan.PDF', base64: 'aGVsbG8=' }, 'tok');
  __ok(r.success && r.ocrOk, 'success');
});

__t('analyze: OCR 실패 → success:true · ocrOk:false · 안내', function () {
  __FETCH.mode = 'upload_fail';
  var r = analyzeNoticeOrCutDoc({ fileName: 'blur.jpg', mimeType: 'image/jpeg', base64: 'aGVsbG8=' }, 'tok');
  __ok(r.success, 'success 는 true');
  __eq(r.ocrOk, false);
  __eq(r.docKind, '');
  __eq(r.appealDraft, '');
  __ok(/글자를 읽지 못했습니다/.test(r.message), '안내: ' + r.message);
  __FETCH.mode = 'ok';
});

__t('analyze: 글자는 읽었지만 핵심이 없으면 안내 문구', function () {
  __FETCH.ocrText = '   ';
  var r = analyzeNoticeOrCutDoc({ fileName: 'blank.jpg', mimeType: 'image/jpeg', base64: 'aGVsbG8=' }, 'tok');
  __ok(r.success, 'success');
  __eq(r.summaryLines.length, 0);
  __ok(/핵심 내용을 찾지 못했습니다/.test(r.message), '안내: ' + r.message);
});

__t('analyze: 8MB 초과 파일은 안내 에러', function () {
  var big = 'A'.repeat(Math.ceil((8 * 1024 * 1024) * 4 / 3) + 8);
  var threw = '';
  try { analyzeNoticeOrCutDoc({ fileName: 'big.jpg', mimeType: 'image/jpeg', base64: big }, 'tok'); }
  catch (e) { threw = String(e.message || e); }
  __ok(/너무 큽니다/.test(threw), '안내: ' + threw);
});

__t('analyze: 빈 파일 · 잘못된 형식은 안내 에러', function () {
  var t1 = '', t2 = '';
  try { analyzeNoticeOrCutDoc({ fileName: 'a.jpg', base64: '  ' }, 'tok'); } catch (e) { t1 = String(e.message || e); }
  __ok(/비어 있습니다/.test(t1), '빈 파일: ' + t1);
  try { analyzeNoticeOrCutDoc({ fileName: 'a.txt', mimeType: 'text/plain', base64: 'aGVsbG8=' }, 'tok'); } catch (e) { t2 = String(e.message || e); }
  __ok(/사진\(JPG·PNG\) 또는 PDF/.test(t2), '형식: ' + t2);
});

__t('analyze: 로그인 토큰 없으면 거부', function () {
  var threw = '';
  try { analyzeNoticeOrCutDoc({ fileName: 'a.jpg', base64: 'aGVsbG8=' }, ''); }
  catch (e) { threw = String(e.message || e); }
  __ok(/로그인이 필요합니다/.test(threw), '안내: ' + threw);
});

__t('apiFunctions_ 에 analyzeNoticeOrCutDoc 등록', function () {
  var map = apiFunctions_();
  __ok(typeof map.analyzeNoticeOrCutDoc === 'function', '등록되지 않음');
  __ok(map.analyzeNoticeOrCutDoc === analyzeNoticeOrCutDoc, '같은 함수여야 함');
});

JSON.stringify(__RESULT);
"""


def find_codegs(explicit):
    cands = [explicit] if explicit else [
        os.path.join(PROJECT, '..', '..', 'downloads', 'Code.gs_v1.19_보안수정.txt'),
        os.path.join(PROJECT, '..', '..', 'downloads', 'Code.gs'),
        os.path.join(HERE, 'Code.gs'),
    ]
    for p in cands:
        if p and os.path.exists(p):
            return os.path.abspath(p)
    sys.exit('Code.gs 를 찾지 못했습니다. --codegs 경로를 지정해 주세요.')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--codegs', default=None)
    args = ap.parse_args()

    try:
        import quickjs
    except ImportError:
        sys.exit('quickjs 가 필요합니다: pip install quickjs')

    path = find_codegs(args.codegs)
    src = io.open(path, encoding='utf-8-sig').read()
    ctx = quickjs.Context()

    # 1) 문법 검사
    try:
        ctx.eval('(function(){' + src + '\n})')
    except Exception as e:  # noqa: BLE001
        sys.exit('문법 오류: %s' % e)
    print('✔ 문법 검사 통과 — %s' % os.path.basename(path))

    # 2) 모의 환경 + 실제 Code.gs + 테스트
    ctx.eval(MOCK_JS)
    ctx.eval(src)
    ctx.eval(LOGIN_STUB_JS)
    result = json.loads(ctx.eval(CASES_JS))

    for c in result['cases']:
        mark = '✔' if c['ok'] else '✘'
        print('%s %s%s' % (mark, c['name'], '' if c['ok'] else '  → ' + c.get('err', '')))
    print('\n통과 %d / 실패 %d' % (result['passed'], result['failed']))
    sys.exit(0 if result['failed'] == 0 else 1)


if __name__ == '__main__':
    main()
