#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
v1.30 — 고시문·삭감통보서 Gemini AI 분석(Code.gs) QuickJS 테스트
--------------------------------------------------------------------
구글 Apps Script 없이 실제 Code.gs 를 QuickJS 위에서 돌려 아래를 확인합니다.

  1) geminiKey_ — 설정 시트 GEMINI_API_KEY 읽기·공백 제거, 시트를 못 읽어도 빈 문자열
  2) Gemini 성공 응답 파싱 — 문서 종류·요약·코드·날짜·초안·사유, 분석엔진 'gemini',
     요청 URL(gemini-2.5-flash)·inline_data·responseMimeType, 프롬프트(병원·품목·환자정보 빈칸)
  3) JSON 펜스(```json)·앞뒤 잡설·후행 쉼표가 있어도 파싱
  4) Gemini 429 / 연결 실패 / 빈 응답 / 깨진 JSON → 무료 Drive OCR 자동 fallback
     (analysisEngine 'ocr-fallback', 실패 사유 geminiError·안내 문구)
  5) 키 미설정 시 기존 OCR 동작 그대로 (analysisEngine 'ocr', Gemini 호출 없음)
  6) 초안이 비었을 때 규칙 기반 초안으로 대체, 삭감 초안에 [환자 상병/진료내역 기재] 보존
  7) getBootstrapData(geminiConfigured) · saveSettings 응답에서 키 마스킹 · apiStatus_

사용:
    python3 tools/test_gemini_notice.py [--codegs 경로]
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

# Code.gs 를 읽은 뒤 덮어쓰는 모의 (설정 시트 · Gemini 호출)
STUB_JS = r"""
// ---- 설정 시트 모의 -------------------------------------------------------
var __SETTINGS = {};
getSettingsMap_ = function () {
  if (__SETTINGS.__throw) throw new Error('설정 시트를 읽지 못했습니다(테스트)');
  var o = {};
  for (var k in __SETTINGS) { if (k !== '__throw') o[k] = __SETTINGS[k]; }
  return o;
};

// ---- Gemini 호출 모의 -----------------------------------------------------
var __GEMINI = { mode: 'ok', status: 200, reply: '', calls: [] };
var __ORIG_FETCH = UrlFetchApp.fetch;
UrlFetchApp.fetch = function (url, opts) {
  if (String(url).indexOf('generativelanguage.googleapis.com') !== -1) {
    var body = {};
    try { body = JSON.parse((opts && opts.payload) || '{}'); } catch (e) { body = {}; }
    __GEMINI.calls.push({
      url: String(url),
      method: String((opts && opts.method) || ''),
      contentType: String((opts && opts.contentType) || ''),
      body: body
    });
    if (__GEMINI.mode === 'throw') throw new Error('주소를 가져올 수 없습니다. (연결 시간 초과)');
    if (__GEMINI.mode === 'http') {
      return new __Resp(__GEMINI.status, { error: { message: 'Quota exceeded', status: 'RESOURCE_EXHAUSTED' } });
    }
    if (__GEMINI.mode === 'empty') return new __Resp(200, { candidates: [{ finishReason: 'SAFETY' }] });
    return new __Resp(200, { candidates: [{ content: { parts: [{ text: __GEMINI.reply }] }, finishReason: 'STOP' }] });
  }
  return __ORIG_FETCH(url, opts);
};

// ---- 부트스트랩/설정 저장용 모의 -----------------------------------------
getClients = function () { return []; };
productsForUser_ = function () { return []; };
elpharmaCount_ = function () { return 0; };
publicUser_ = function (u) { return { 아이디: (u && u.아이디) || '' }; };
isMaster_ = function () { return true; };
formatDate_ = function () { return '2026-11-29'; };
currentMonth_ = function () { return '2026-11'; };
Session.getActiveUser = function () { return { getEmail: function () { return 'test@example.com'; } }; };

function GridSheet(rows) { this.rows = rows; }
GridSheet.prototype.getLastRow = function () { return this.rows.length; };
GridSheet.prototype.getLastColumn = function () {
  var max = 0, i;
  for (i = 0; i < this.rows.length; i++) if (this.rows[i].length > max) max = this.rows[i].length;
  return max;
};
GridSheet.prototype.appendRow = function (vals) { this.rows.push(vals.slice()); };
GridSheet.prototype.getRange = function (r, c, nr, nc) {
  var sh = this;
  nr = nr || 1; nc = nc || 1;
  function rowOf(ri) {
    while (sh.rows.length <= ri) sh.rows.push([]);
    var row = sh.rows[ri];
    while (row.length <= (c - 1 + nc)) row.push('');
    return row;
  }
  var api = {
    getValues: function () {
      var out = [], i, j, row, line;
      for (i = 0; i < nr; i++) {
        row = rowOf(r - 1 + i);
        line = [];
        for (j = 0; j < nc; j++) line.push(row[c - 1 + j] === undefined ? '' : row[c - 1 + j]);
        out.push(line);
      }
      return out;
    },
    setValues: function (vals) {
      var i, j, row;
      for (i = 0; i < vals.length; i++) {
        row = rowOf(r - 1 + i);
        for (j = 0; j < vals[i].length; j++) row[c - 1 + j] = vals[i][j];
      }
      return api;
    },
    setValue: function (v) { rowOf(r - 1)[c - 1] = v; return api; },
    setNumberFormat: function () { return api; }
  };
  return api;
};

var __SHEET = null;
getSheet_ = function () {
  if (!__SHEET) {
    __SHEET = new GridSheet([
      ['설정키', '설정값', '메모'],
      ['회사명', '수메디팜', '인쇄물·PDF·이메일에 표시되는 회사명'],
      ['GEMINI_API_KEY', 'AIzaSyTEST-KEY', 'Gemini 키']
    ]);
  }
  return __SHEET;
};
withLock_ = function (fn) { return fn(); };
requireMaster_ = function () { return { 아이디: 'master' }; };
"""

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

var CUT_TEXT =
  '건강보험심사평가원\n' +
  '심사결과통보서 (요양기관용)\n' +
  '요양기관명: 서울연세내과의원\n' +
  '접수번호: 2026-11-12345\n' +
  '통보일: 2026.11.20\n' +
  '1. 삭감(조정) 내역\n' +
  '   - 조정코드: 0231 / 삭감사유: 약제 투여 기준(1일 1회)을 초과하여 처방된 건으로 확인되어 1회분을 삭감 조정함.\n' +
  '   - 대상 품목: 케토롤락 트로메타민 주 30mg (보험코드 645001230)\n' +
  '   - 불인정 금액: 12,340원\n' +
  '2. 조정 사유 요약\n' +
  '   - 요양급여의 적용기준 및 방법에 관한 세부사항(보건복지부 고시)에 따라 1일 1회만 인정됨.\n' +
  '3. 이의신청은 통보일로부터 90일 이내에 가능합니다.';

var GEMINI_CUT = {
  docKind: '삭감통보서',
  summaryLines: [
    '케토롤락 트로메타민 주 30mg 1회분이 투여 기준 초과로 삭감 조정되었습니다.',
    '조정코드 0231, 불인정 금액 12,340원입니다.',
    '이의신청은 통보일로부터 90일 이내에 가능합니다.'
  ],
  codes: ['조정코드 0231', '보험코드 645001230'],
  dates: ['통보일 2026-11-20'],
  appealDraft: '[이의신청 / 재심사조정청구 사유서 초안]\n\n■ 청구기관: 서울연세내과의원\n' +
    '■ 대상 품목: 케토롤락 트로메타민 주 30mg\n■ 관련 고시·문서번호: 조정코드 0231\n' +
    '■ 통보(조정) 내용 요지\n - 1일 1회 기준 초과로 1회분 삭감\n\n■ 이의신청 사유\n' +
    ' 1. 해당 약제는 요양급여의 적용기준에 따라 투여되었습니다.\n' +
    ' 2. [환자 상병/진료내역 기재] — 상병명·처방일자·투여량을 적어 주세요.\n' +
    ' 3. 따라서 해당 조정 처분은 재검토되어 주시기를 요청드립니다.\n\n' +
    '■ 첨부서류: 진료기록부 사본, 처방전·투약기록\n■ 작성일: 2026-11-29',
  reasonNote: '투여 기준(1일 1회) 초과 처방으로 1회분이 삭감 조정되었습니다.'
};

var GEMINI_GOSI = {
  docKind: '고시·공지',
  summaryLines: ['약제급여목록 개정에 따라 리투아민 주사제의 급여 기준이 정비되었습니다.', '적용 대상 상병이 한정됩니다.'],
  codes: ['제2026-312호'],
  dates: ['시행일 2026-12-01'],
  appealDraft: '[고시·공지 요약 및 이의신청 근거 메모 초안]\n\n■ 확인 병원: [병원명 기재]\n■ 관련 품목: [품목명 기재]\n■ 고시·문서번호: 제2026-312호',
  reasonNote: '급여 기준 정비 고시입니다.'
};

function __resetGemini(reply) {
  __GEMINI.mode = 'ok';
  __GEMINI.status = 200;
  __GEMINI.reply = typeof reply === 'string' ? reply : JSON.stringify(reply || GEMINI_CUT);
  __GEMINI.calls = [];
  __FETCH.mode = 'ok';
  __FETCH.ocrText = CUT_TEXT;
  __FETCH.calls = [];
}

// ---------------------------------------------------------------- 1. 키 읽기
__t('geminiKey_ — 설정 값 읽기 · 공백 제거 · 시트 오류는 빈 문자열', function () {
  __SETTINGS = { GEMINI_API_KEY: '  AIza-1234  ' };
  __eq(geminiKey_(), 'AIza-1234');
  __SETTINGS = {};
  __eq(geminiKey_(), '');
  __SETTINGS = { __throw: true };
  __eq(geminiKey_(), '');
  __SETTINGS = {};
});

// ---------------------------------------------------------------- 2. Gemini 성공
__SETTINGS = { GEMINI_API_KEY: 'AIza-1234' };

__t('analyze(Gemini) — 삭감통보서: 요약·코드·날짜·초안·사유 · analysisEngine=gemini', function () {
  __resetGemini(GEMINI_CUT);
  var r = analyzeNoticeOrCutDoc({
    fileName: 'cut.jpg', mimeType: 'image/jpeg', base64: 'aGVsbG8=',
    docType: 'auto', clientName: '서울연세내과의원', itemName: '케토롤락 주'
  }, 'tok');
  __eq(r.analysisEngine, 'gemini');
  __ok(r.success && r.ocrOk, 'success/ocrOk');
  __eq(r.docKind, '삭감통보서');
  __eq(r.docKindKey, 'cut');
  __eq(r.summaryLines.length, 3);
  __has(r.codes, '조정코드 0231');
  __has(r.dates, '통보일 2026-11-20');
  __ok(r.appealDraft.indexOf('[이의신청 / 재심사조정청구 사유서 초안]') === 0, '초안 제목');
  __ok(r.appealDraft.indexOf('[환자 상병/진료내역 기재]') !== -1, '환자정보 빈칸 유지');
  __ok(r.reasonNote.indexOf('삭감') !== -1, 'reasonNote: ' + r.reasonNote);
  __ok(r.message.indexOf('🤖 Gemini AI') === 0, '안내: ' + r.message);
  __ok(!r.geminiError, 'geminiError 없음');
  // Gemini 성공 시 무료 드라이브 OCR(업로드/삭제)은 부르지 않음
  __eq(__FETCH.calls.length, 0);
});

__t('analyze(Gemini) — 요청 URL·inline_data·responseMimeType·프롬프트 내용', function () {
  __resetGemini(GEMINI_CUT);
  analyzeNoticeOrCutDoc({
    fileName: 'cut.jpg', mimeType: 'image/jpeg', base64: 'aGVsbG8=',
    docType: 'auto', clientName: '서울연세내과의원', itemName: '케토롤락 주'
  }, 'tok');
  __eq(__GEMINI.calls.length, 1);
  var c = __GEMINI.calls[0];
  __ok(c.url.indexOf('models/gemini-2.5-flash:generateContent') !== -1, '모델 URL: ' + c.url);
  __ok(c.url.indexOf('key=AIza-1234') !== -1, '키 전달');
  __eq(c.method.toLowerCase(), 'post');
  __ok(/application\/json/.test(c.contentType), 'contentType');
  __eq(c.body.generationConfig.responseMimeType, 'application/json');
  __ok(c.body.generationConfig.temperature <= 0.3, 'temperature 낮게');
  var parts = c.body.contents[0].parts;
  __eq(parts[1].inline_data.mime_type, 'image/jpeg');
  __eq(parts[1].inline_data.data, 'aGVsbG8=');
  var prompt = parts[0].text;
  __ok(prompt.indexOf('이의신청') !== -1, '프롬프트: 이의신청');
  __ok(prompt.indexOf('summaryLines') !== -1 && prompt.indexOf('appealDraft') !== -1, 'JSON 형식 안내');
  __ok(prompt.indexOf('[환자 상병/진료내역 기재]') !== -1, '환자정보 빈칸 지시');
  __ok(prompt.indexOf('서울연세내과의원') !== -1, '거래처명 반영');
  __ok(prompt.indexOf('케토롤락 주') !== -1, '품목명 반영');
});

__t('analyze(Gemini) — 종류를 삭감통보서로 고르면 그 종류 우선', function () {
  __resetGemini(GEMINI_GOSI);
  var r = analyzeNoticeOrCutDoc({ fileName: 'x.pdf', mimeType: 'application/pdf', base64: 'aGVsbG8=', docType: 'cut' }, 'tok');
  __eq(r.docKind, '삭감통보서');
  __eq(r.docKindKey, 'cut');
  var prompt = __GEMINI.calls[0].body.contents[0].parts[0].text;
  __ok(prompt.indexOf('삭감통보서]로 지정') !== -1, '종류 지시: ' + prompt.slice(0, 80));
});

__t('JSON 펜스(```json) · 앞뒤 잡설 · 후행 쉼표도 파싱', function () {
  __resetGemini('```json\n' + JSON.stringify(GEMINI_GOSI) + '\n```');
  var r = analyzeNoticeOrCutDoc({ fileName: 'gosi.jpg', mimeType: 'image/jpeg', base64: 'aGVsbG8=' }, 'tok');
  __eq(r.analysisEngine, 'gemini');
  __eq(r.docKind, '고시·공지');
  __has(r.codes, '제2026-312호');

  __resetGemini('분석 결과입니다:\n{"docKind": "고시·공지", "summaryLines": ["가", "나",], }\n감사합니다.');
  var r2 = analyzeNoticeOrCutDoc({ fileName: 'gosi.jpg', mimeType: 'image/jpeg', base64: 'aGVsbG8=' }, 'tok');
  __eq(r2.analysisEngine, 'gemini');
  __eq(r2.summaryLines.length, 2);
});

__t('Gemini 초안이 비면 규칙 기반 초안으로 대체 (병원·품목 반영)', function () {
  __resetGemini({ docKind: '삭감통보서', summaryLines: ['삭감 사유 요약'], codes: ['조정코드 0231'], dates: ['통보일 2026-11-20'], appealDraft: '', reasonNote: '사유' });
  var r = analyzeNoticeOrCutDoc({ fileName: 'c.jpg', mimeType: 'image/jpeg', base64: 'aGVsbG8=', clientName: '서울연세내과의원', itemName: '케토롤락 주' }, 'tok');
  __eq(r.analysisEngine, 'gemini');
  __ok(r.appealDraft.indexOf('[이의신청 / 재심사조정청구 사유서 초안]') === 0, '초안 제목: ' + r.appealDraft.slice(0, 40));
  __ok(r.appealDraft.indexOf('서울연세내과의원') !== -1, '병원명');
  __ok(r.appealDraft.indexOf('케토롤락 주') !== -1, '품목명');
  __ok(r.appealDraft.indexOf('[환자 상병/진료내역 기재]') !== -1, '환자정보 빈칸');
});

__t('Gemini 초안에 환자정보 빈칸이 없으면 안내 한 줄을 덧붙임', function () {
  var d = JSON.parse(JSON.stringify(GEMINI_CUT));
  d.appealDraft = '[이의신청 / 재심사조정청구 사유서 초안]\n■ 청구기관: 서울연세내과의원';
  __resetGemini(d);
  var r = analyzeNoticeOrCutDoc({ fileName: 'c.jpg', mimeType: 'image/jpeg', base64: 'aGVsbG8=' }, 'tok');
  __ok(r.appealDraft.indexOf('[환자 상병/진료내역 기재]') !== -1, '빈칸 안내: ' + r.appealDraft);
});

// ---------------------------------------------------------------- 3. fallback
__t('Gemini 429(할당량 초과) → Drive OCR 자동 fallback · 실패 사유 안내', function () {
  __resetGemini(GEMINI_CUT);
  __GEMINI.mode = 'http';
  __GEMINI.status = 429;
  var r = analyzeNoticeOrCutDoc({ fileName: 'cut.jpg', mimeType: 'image/jpeg', base64: 'aGVsbG8=', clientName: '서울연세내과의원' }, 'tok');
  __eq(r.analysisEngine, 'ocr-fallback');
  __ok(r.success && r.ocrOk, 'OCR 결과는 성공');
  __eq(r.docKind, '삭감통보서');
  __has(r.codes, '조정코드 0231');
  __ok(r.appealDraft.indexOf('[이의신청 / 재심사조정청구 사유서 초안]') === 0, '초안 제목');
  __ok(/HTTP 429/.test(r.geminiError), 'geminiError: ' + r.geminiError);
  __ok(r.message.indexOf('(Gemini AI 분석을 쓰지 못해 무료 OCR 로 읽었습니다') === 0, '안내: ' + r.message);
  __ok(__FETCH.calls.some(function (c) { return /upload\/drive\/v3\/files/.test(c.url); }), '드라이브 OCR 호출');
});

__t('Gemini 연결 실패(타임아웃) → fallback', function () {
  __resetGemini(GEMINI_CUT);
  __GEMINI.mode = 'throw';
  var r = analyzeNoticeOrCutDoc({ fileName: 'cut.jpg', mimeType: 'image/jpeg', base64: 'aGVsbG8=' }, 'tok');
  __eq(r.analysisEngine, 'ocr-fallback');
  __ok(r.ocrOk, 'OCR 성공');
  __ok(/시간 초과/.test(r.geminiError), 'geminiError: ' + r.geminiError);
});

__t('Gemini 빈 응답 · 깨진 JSON → fallback', function () {
  __resetGemini(GEMINI_CUT);
  __GEMINI.mode = 'empty';
  var r1 = analyzeNoticeOrCutDoc({ fileName: 'cut.jpg', mimeType: 'image/jpeg', base64: 'aGVsbG8=' }, 'tok');
  __eq(r1.analysisEngine, 'ocr-fallback');

  __resetGemini('이미지가 흐려서 읽을 수 없습니다.');
  var r2 = analyzeNoticeOrCutDoc({ fileName: 'cut.jpg', mimeType: 'image/jpeg', base64: 'aGVsbG8=' }, 'tok');
  __eq(r2.analysisEngine, 'ocr-fallback');
  __ok(/Gemini/.test(r2.geminiError) || r2.geminiError.length > 0, 'geminiError: ' + r2.geminiError);
});

__t('Gemini·OCR 둘 다 실패해도 success:true · 안내 (예외 아님)', function () {
  __resetGemini(GEMINI_CUT);
  __GEMINI.mode = 'http';
  __GEMINI.status = 500;
  __FETCH.mode = 'upload_fail';
  var r = analyzeNoticeOrCutDoc({ fileName: 'cut.jpg', mimeType: 'image/jpeg', base64: 'aGVsbG8=' }, 'tok');
  __ok(r.success, 'success');
  __eq(r.ocrOk, false);
  __eq(r.analysisEngine, 'ocr-fallback');
  __ok(/글자를 읽지 못했습니다/.test(r.message), '안내: ' + r.message);
  __ok(/Gemini 분석도 실패/.test(r.message), 'Gemini 실패 안내: ' + r.message);
});

// ---------------------------------------------------------------- 4. 키 없음
__t('키 미설정 → 기존 OCR 동작 (analysisEngine=ocr, Gemini 호출 없음)', function () {
  __SETTINGS = {};
  __resetGemini(GEMINI_CUT);
  var before = __GEMINI.calls.length;
  var r = analyzeNoticeOrCutDoc({ fileName: 'cut.jpg', mimeType: 'image/jpeg', base64: 'aGVsbG8=' }, 'tok');
  __eq(r.analysisEngine, 'ocr');
  __eq(__GEMINI.calls.length, before);
  __ok(r.ocrOk, 'OCR 성공');
  __eq(r.docKind, '삭감통보서');
  __ok(/코드/.test(r.message), '안내: ' + r.message);
  __SETTINGS = { GEMINI_API_KEY: 'AIza-1234' };
});

// ---------------------------------------------------------------- 5. 설정·상태
__t('getBootstrapData — geminiConfigured · settings 에 키 원문 없음', function () {
  __SETTINGS = { GEMINI_API_KEY: 'AIza-1234', HIRA_API_KEY: 'hira-1', 접근PIN: '1234', 회사명: '수메디팜' };
  var b = buildBootstrapPayload_({ 아이디: 'master', 담당자명: '마스터', 권한: 'MASTER' });
  __eq(b.geminiConfigured, true);
  __eq(b.hiraConfigured, true);
  __ok(b.settings['GEMINI_API_KEY'] === undefined, 'GEMINI 키 노출됨');
  __ok(b.settings['HIRA_API_KEY'] === undefined, 'HIRA 키 노출됨');
  __ok(b.settings['접근PIN'] === undefined, 'PIN 노출됨');
  __eq(b.settings['회사명'], '수메디팜');

  __SETTINGS = {};
  var b2 = buildBootstrapPayload_({ 아이디: 'master' });
  __eq(b2.geminiConfigured, false);
});

__t('saveSettings — 저장 후에도 GEMINI_API_KEY 를 돌려주지 않음', function () {
  __SETTINGS = { GEMINI_API_KEY: 'AIza-1234', HIRA_API_KEY: 'hira-1', 접근PIN: '1234', 회사명: '수메디팜' };
  __SHEET = null;
  var res = saveSettings({ '회사명': '수메디팜' }, 'tok');
  __eq(res.success, true);
  __ok(res.settings['GEMINI_API_KEY'] === undefined, 'GEMINI 키 노출됨: ' + JSON.stringify(res.settings));
  __ok(res.settings['HIRA_API_KEY'] === undefined, 'HIRA 키 노출됨');
  __ok(res.settings['접근PIN'] === undefined, 'PIN 노출됨');
});

__t('apiStatus_ — geminiConfigured · geminiReader 표식', function () {
  __SETTINGS = { GEMINI_API_KEY: 'AIza-1234' };
  var s = apiStatus_();
  __eq(s.geminiConfigured, true);
  __ok(s.geminiReader.indexOf('gemini-2.5-flash') !== -1, 'geminiReader: ' + s.geminiReader);
  __eq(s.noticeReader, 'analyze+v1.28');
  __SETTINGS = {};
  __eq(apiStatus_().geminiConfigured, false);
});

__t('DEFAULT_SETTINGS 에 GEMINI_API_KEY 기본값이 있음', function () {
  var hit = null;
  DEFAULT_SETTINGS.forEach(function (x) { if (x[0] === 'GEMINI_API_KEY') hit = x; });
  __ok(hit, '기본 설정 없음');
  __eq(hit[1], '');
  __ok(hit[2].indexOf('aistudio.google.com') !== -1, '발급 안내: ' + hit[2]);
});

__t('apiFunctions_ 등록은 그대로 (analyzeNoticeOrCutDoc)', function () {
  var map = apiFunctions_();
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
    ctx.eval(STUB_JS)
    result = json.loads(ctx.eval(CASES_JS))

    for c in result['cases']:
        mark = '✔' if c['ok'] else '✘'
        print('%s %s%s' % (mark, c['name'], '' if c['ok'] else '  → ' + c.get('err', '')))
    print('\n통과 %d / 실패 %d' % (result['passed'], result['failed']))
    sys.exit(0 if result['failed'] == 0 else 1)


if __name__ == '__main__':
    main()
