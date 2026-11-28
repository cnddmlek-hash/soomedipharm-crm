#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
v1.27 — 사업자등록증 등록·자동인식(Code.gs) QuickJS 테스트
--------------------------------------------------------------------
구글 Apps Script 없이 실제 Code.gs 를 QuickJS 위에서 돌려 아래를 확인합니다.

  1) parseBizCertText_ — 개인의원 / 법인병원 / 줄바꿈 주소 / 하이픈 없는 번호 /
     한 줄로 붙은 OCR / 빈 문서
  2) writeRowByHeaders_ 가 시트 1행에 없는 '사업자등록번호'·'사업자등록증URL' 헤더를
     오른쪽 끝에 자동으로 만들고 값을 기록하는지 (가짜 시트)
  3) uploadAndParseBizCert — 드라이브 저장 + OCR 성공 경로, OCR 실패 경로(저장은 성공),
     크기 초과 안내, 로그인 토큰 없음 안내 (가짜 Drive/UrlFetch/Utilities)

사용:
    python3 tools/test_bizcert_ocr.py [--codegs 경로] [--verbose]
필요: pip install quickjs
"""
import argparse
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(HERE)

# ---------------------------------------------------------------------------
# QuickJS 에 넣을 모의 환경 (Code.gs 보다 먼저 실행)
# ---------------------------------------------------------------------------
MOCK_JS = r"""
// ---- 바이트/문자열 도우미 -------------------------------------------------
function __utf8Bytes(str) {
  var out = [], i, c;
  for (i = 0; i < str.length; i++) {
    c = str.charCodeAt(i);
    if (c < 0x80) out.push(c);
    else if (c < 0x800) { out.push(0xC0 | (c >> 6), 0x80 | (c & 0x3F)); }
    else if (c < 0xD800 || c >= 0xE000) { out.push(0xE0 | (c >> 12), 0x80 | ((c >> 6) & 0x3F), 0x80 | (c & 0x3F)); }
    else { i++; c = 0x10000 + (((c & 0x3FF) << 10) | (str.charCodeAt(i) & 0x3FF)); out.push(0xF0 | (c >> 18), 0x80 | ((c >> 12) & 0x3F), 0x80 | ((c >> 6) & 0x3F), 0x80 | (c & 0x3F)); }
  }
  return out;
}

var __B64 = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/';
function __b64decode(str) {
  var clean = String(str || '').replace(/[^A-Za-z0-9+/=]/g, ''), out = [], i, n, b1, b2, b3, b4;
  for (i = 0; i < clean.length; i += 4) {
    b1 = __B64.indexOf(clean.charAt(i));
    b2 = __B64.indexOf(clean.charAt(i + 1));
    b3 = __B64.indexOf(clean.charAt(i + 2));
    b4 = __B64.indexOf(clean.charAt(i + 3));
    if (b1 < 0 || b2 < 0) break;
    out.push((b1 << 2) | (b2 >> 4));
    if (b3 >= 0) out.push(((b2 & 15) << 4) | (b3 >> 2));
    if (b4 >= 0) out.push(((b3 & 3) << 6) | b4);
  }
  return out;
}

function __Blob(bytes, mime, name) {
  if (typeof bytes === 'string') bytes = __utf8Bytes(bytes);
  if (bytes && bytes.__text !== undefined) { this.text = bytes.__text; bytes = __utf8Bytes(bytes.__text); }
  this.bytes = Array.prototype.slice.call(bytes || []);
  this.mime = mime || ''; this.name = name || '';
}
__Blob.prototype.getBytes = function () { return this.bytes.slice(); };
__Blob.prototype.getDataAsString = function () { return this.text !== undefined ? this.text : '[]'; };
__Blob.prototype.getBlob = function () { return this; };

var Utilities = {
  base64Decode: function (s) { return __b64decode(s); },
  newBlob: function (bytes, mime, name) { return new __Blob(bytes, mime, name); },
  getUuid: function () { return '12345678-1234-1234-1234-123456789abc'; },
  formatDate: function (d, tz, fmt) { return '20261129_101500'; }
};

// ---- 가짜 드라이브 -------------------------------------------------------
var __DRIVE_CALLS = { created: [], folders: [], deleted: [] };
function __File(id, name, url) { this.id = id; this.name = name; this.url = url || ('https://drive.google.com/file/d/' + id + '/view'); }
__File.prototype.getId = function () { return this.id; };
__File.prototype.getName = function () { return this.name; };
__File.prototype.getUrl = function () { return this.url; };
__File.prototype.setTrashed = function () { __DRIVE_CALLS.deleted.push(this.id); return this; };

function __Folder(name) { this.name = name; }
__Folder.prototype.getFoldersByName = function (n) {
  var hits = __DRIVE_CALLS.folders.filter(function (f) { return f.name === n; });
  var i = 0;
  return { hasNext: function () { return i < hits.length; }, next: function () { return hits[i++]; } };
};
__Folder.prototype.createFolder = function (n) { var f = new __Folder(n); __DRIVE_CALLS.folders.push(f); return f; };
__Folder.prototype.createFile = function (blob) {
  var id = 'file_' + (__DRIVE_CALLS.created.length + 1);
  var file = new __File(id, blob.name);
  __DRIVE_CALLS.created.push({ id: id, name: blob.name, mime: blob.mime, size: blob.bytes.length });
  return file;
};

var __ROOT = new __Folder('(root)');
var __SS_ID = 'sheet123';
var SpreadsheetApp = { getActiveSpreadsheet: function () { return { getId: function () { return __SS_ID; }, getName: function () { return '테스트시트'; } }; } };
var DriveApp = {
  getFileById: function (id) { return new __File(id, 'x'); },
  getFoldersByName: function (n) { return __ROOT.getFoldersByName(n); },
  createFolder: function (n) { var f = new __Folder(n); __DRIVE_CALLS.folders.push(f); return f; }
};
// 스프레드시트 파일의 부모 폴더 → 부모에서 '수메디팜_사업자등록증' 폴더를 찾거나 만든다
__File.prototype.getParents = function () { var i = 0, self = this; return { hasNext: function () { return i < 1; }, next: function () { i++; return __ROOT; } }; };

var ScriptApp = { getOAuthToken: function () { return 'fake-oauth-token'; } };
var Session = { getScriptTimeZone: function () { return 'Asia/Seoul'; } };

// ---- 가짜 UrlFetch (드라이브 업로드 / 내보내기 / 삭제) ---------------------
var __FETCH = { mode: 'ok', ocrText: '', calls: [] };
function __Resp(code, bodyObj, text) {
  this.code = code; this.body = bodyObj; this.text = text;
}
__Resp.prototype.getResponseCode = function () { return this.code; };
__Resp.prototype.getContentText = function () { return this.text !== undefined ? this.text : JSON.stringify(this.body || {}); };
__Resp.prototype.getContent = function () { return { __text: this.text || '' }; };

var UrlFetchApp = {
  fetch: function (url, opts) {
    __FETCH.calls.push({ url: url, method: (opts && opts.method) || 'get', contentType: (opts && opts.contentType) || '' });
    if (/upload\/drive\/v3\/files/.test(url)) {
      if (__FETCH.mode === 'upload_fail') return new __Resp(500, { error: { message: '변환 실패(테스트)' } }, JSON.stringify({ error: { message: '변환 실패(테스트)' } }));
      return new __Resp(200, { id: 'tempdoc1' });
    }
    if (/\/export\?mimeType=text%2Fplain/.test(url)) return new __Resp(200, null, __FETCH.ocrText);
    if ((opts && String(opts.method).toLowerCase() === 'delete')) return new __Resp(204, null, '');
    return new __Resp(200, {});
  }
};

// 로그인 모의(requireUser_ 교체)는 Code.gs 를 읽은 뒤에 덮어씁니다 — LOGIN_STUB_JS 참고

// ---- 가짜 시트 ------------------------------------------------------------
function FakeSheet(rows) { this.rows = rows; }
FakeSheet.prototype.getLastColumn = function () {
  var max = 0;
  this.rows.forEach(function (r) { if (r.length > max) max = r.length; });
  return max;
};
FakeSheet.prototype.getLastRow = function () { return this.rows.length; };
FakeSheet.prototype.getRange = function (r, c, nr, nc) {
  var sh = this;
  nr = nr || 1; nc = nc || 1;
  function cell(ri, ci) {
    while (sh.rows.length <= ri) sh.rows.push([]);
    var row = sh.rows[ri];
    while (row.length <= ci) row.push('');
    return row;
  }
  var api = {
    getValues: function () {
      var out = [];
      for (var i = 0; i < nr; i++) {
        var line = [];
        for (var j = 0; j < nc; j++) line.push(cell(r - 1 + i, c - 1 + j)[c - 1 + j] || '');
        out.push(line);
      }
      return out;
    },
    setValues: function (vals) {
      for (var i = 0; i < vals.length; i++) for (var j = 0; j < vals[i].length; j++) cell(r - 1 + i, c - 1 + j)[c - 1 + j] = vals[i][j];
      return api;
    },
    setNumberFormat: function () { return api; },
    setFontWeight: function () { return api; },
    setBackground: function () { return api; },
    setFontColor: function () { return api; }
  };
  return api;
};
FakeSheet.prototype.appendRow = function (vals) { this.rows.push(vals.slice()); };
"""

LOGIN_STUB_JS = r"""
// 실제 requireUser_ 대신 테스트용 — 토큰이 없으면 실제와 같은 문구로 거부
function requireUser_(token) {
  if (!token) throw new Error('로그인이 필요합니다. 다시 로그인해 주세요.');
  return { 아이디: 'master', 담당자명: '마스터', 권한: 'MASTER' };
}
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

// ---------- 1. 텍스트 파싱 ----------
__t('개인의원: 번호·상호·대표자·주소·사업유형', function () {
  var p = parseBizCertText_('사 업 자 등 록 증\n(일반과세자)\n등록번호 : 123-45-67890\n상호(법인명) : 서울연세내과의원\n성명(대표자) : 김철수\n개업연월일 : 2015년 3월 2일\n사업장 소재지 : 서울특별시 서대문구 신촌로 123, 2층\n본점소재지 : 서울특별시 서대문구 신촌로 123, 2층\n사업의 종류 : 업태 : 보건업\n종목 : 의원');
  __eq(p.사업자등록번호, '123-45-67890');
  __eq(p.거래처명, '서울연세내과의원');
  __eq(p.원장성함, '김철수');
  __eq(p.주소, '서울특별시 서대문구 신촌로 123, 2층');
  __eq(p.사업유형, '개인');
  __eq(p.과세유형, '일반과세자');
  __eq(p.업태, '보건업');
});

__t('법인병원: 법인사업자 → 법인, 하이픈 없는 번호 정규화', function () {
  var p = parseBizCertText_('사업자등록증\n법인사업자\n등록번호 : 2345678901\n법인명(단독사업자) : 수메디팜 주식회사\n성명(대표자) : 홍길동\n사업장 소재지 : 서울특별시 강남구 테헤란로 123');
  __eq(p.사업자등록번호, '234-56-78901');
  __eq(p.거래처명, '수메디팜 주식회사');
  __eq(p.원장성함, '홍길동');
  __eq(p.사업유형, '법인');
});

__t('줄바꿈 주소: 두 줄을 이어 붙이고 개업연월일 앞에서 끊김', function () {
  var p = parseBizCertText_('상 호 : 마포튼튼약국\n성 명 : 박영희\n사업장 소재지 :\n서울특별시 마포구 양화로 45\n3층 301호\n개업연월일 : 2021년 5월 1일');
  __eq(p.주소, '서울특별시 마포구 양화로 45 3층 301호');
  __eq(p.거래처명, '마포튼튼약국');
});

__t('한 줄로 붙은 OCR 결과도 각 칸 앞에서 끊김', function () {
  var p = parseBizCertText_('법인명(단독사업자) : (주)건강약국  성명(대표자) : 최영수  사업장소재지 : 인천광역시 남동구 인주대로 100 사업의 종류 : 업태 : 도매업 종목 : 의약품 도매');
  __eq(p.거래처명, '(주)건강약국');
  __eq(p.원장성함, '최영수');
  __eq(p.주소, '인천광역시 남동구 인주대로 100');
});

__t('성명 옆에 생년월일이 붙은 한 줄 · 업태에 콜론이 없어도 끊김', function () {
  var p = parseBizCertText_('사 업 자 등 록 증\n( 일반과세자 )\n등록번호 : 332-29-01979\n상 호 : 테스트팜\n성 명 : 홍길동 생 년 월 일 : 1990 년 01 월 01 일\n개 업 연 월 일 : 2020 년 10 월 27 일\n사 업 장 소 재 지 : 부산광역시 강서구 예시로 29, 5층 506호(예시동, 예시프라자)\n사 업 의 종 류 : 업태 도매 및 소매업 종목 의약품 중개업\n발 급 사 유 : 기관제출');
  __eq(p.원장성함, '홍길동');
  __eq(p.거래처명, '테스트팜');
  __eq(p.사업자등록번호, '332-29-01979');
  __eq(p.주소, '부산광역시 강서구 예시로 29, 5층 506호(예시동, 예시프라자)');
  __eq(p.업태, '도매 및 소매업');
  __eq(p.종목, '의약품 중개업');
  __eq(p.사업유형, '개인');
});

__t('대표자 라벨만 있는 문서 · 간이과세자 → 개인', function () {
  var p = parseBizCertText_('사업자등록번호 9876543210\n상 호 : 강남정형외과의원\n대 표 자 : 이순신\n주 소 : 부산광역시 해운대구 센텀중앙로 90\n간이과세자');
  __eq(p.원장성함, '이순신');
  __eq(p.사업자등록번호, '987-65-43210');
  __eq(p.사업유형, '개인');
  __eq(p.주소, '부산광역시 해운대구 센텀중앙로 90');
});

__t('빈 문서 → 모두 빈 값', function () {
  var p = parseBizCertText_('');
  __eq(p.사업자등록번호, ''); __eq(p.거래처명, ''); __eq(p.주소, '');
});

// ---------- 2. 헤더 자동 추가 ----------
__t('시트 1행에 없는 헤더는 오른쪽 끝에 자동으로 생기고 값이 기록됨', function () {
  var sh = new FakeSheet([['거래처코드', '거래처명', '주소'], ['S001', '기존의원', '서울']]);
  writeRowByHeaders_(sh, { '거래처코드': 'S002', '거래처명': '새의원', '주소': '부산', '사업자등록번호': '123-45-67890', '사업자등록증URL': 'https://drive.google.com/x' }, null);
  __eq(sh.rows[0][3], '사업자등록번호');
  __eq(sh.rows[0][4], '사업자등록증URL');
  __eq(sh.rows[2][0], 'S002');
  __eq(sh.rows[2][3], '123-45-67890');
  __eq(sh.rows[2][4], 'https://drive.google.com/x');
  __eq(sh.rows[1][1], '기존의원');   // 기존 행은 그대로
});

__t('이미 있는 헤더는 다시 만들지 않음', function () {
  var sh = new FakeSheet([['거래처코드', '사업자등록번호'], ['S001', '111-11-11111']]);
  writeRowByHeaders_(sh, { '거래처코드': 'S002', '사업자등록번호': '222-22-22222' }, null);
  __eq(sh.rows[0].length, 2);
  __eq(sh.rows[2][1], '222-22-22222');
});

// ---------- 3. 업로드 + OCR ----------
__FETCH.mode = 'ok';
__FETCH.ocrText = '등록번호 : 123-45-67890\n상호(법인명) : 서울연세내과의원\n성명(대표자) : 김철수\n사업장 소재지 : 서울특별시 서대문구 신촌로 123';
var UP = null;
__t('업로드 성공: 드라이브 저장 + OCR 성공 + 임시문서 삭제', function () {
  __DRIVE_CALLS.created = []; __DRIVE_CALLS.deleted = []; __FETCH.calls = [];
  UP = uploadAndParseBizCert({ fileName: 'biz.jpg', mimeType: 'image/jpeg', base64: 'aGVsbG8=', clientName: '서울연세내과의원' }, 'tok');
  __ok(UP.success, 'success 여야 함');
  __ok(UP.ocrOk, 'ocrOk 여야 함');
  __eq(UP.parsed.사업자등록번호, '123-45-67890');
  __eq(UP.parsed.거래처명, '서울연세내과의원');
  __ok(/^사업자등록증_서울연세내과의원_20261129_101500_biz\.jpg$/.test(UP.fileName), '파일명 형식: ' + UP.fileName);
  __ok(UP.fileUrl.indexOf('https://drive.google.com/') === 0, 'fileUrl');
  __ok(UP.fileId, 'fileId');
  __eq(__DRIVE_CALLS.created.length, 1);
  __eq(__DRIVE_CALLS.created[0].mime, 'image/jpeg');
  __ok(__FETCH.calls.some(function (c) { return c.method === 'delete'; }), '임시 문서 삭제 호출');
  __ok(__FETCH.calls.some(function (c) { return /multipart\/related/.test(c.contentType); }), '멀티파트 업로드');
  __ok(UP.rawTextPreview.indexOf('등록번호') !== -1, 'rawTextPreview');
});

__t('OCR 실패: 파일 저장은 성공(ocrOk:false) + 안내 문구', function () {
  __FETCH.mode = 'upload_fail';
  __DRIVE_CALLS.created = [];
  var r = uploadAndParseBizCert({ fileName: 'biz.pdf', mimeType: 'application/pdf', base64: 'aGVsbG8=', clientName: '' }, 'tok');
  __ok(r.success, '파일 저장은 성공이어야 함');
  __eq(r.ocrOk, false);
  __ok(r.fileUrl, 'fileUrl 은 있어야 함');
  __ok(/자동 인식은 실패했습니다/.test(r.message), '안내 문구: ' + r.message);
  __eq(__DRIVE_CALLS.created[0].name.indexOf('사업자등록증_미지정_'), 0);
  __FETCH.mode = 'ok';
});

__t('8MB 초과 파일은 안내 에러(저장하지 않음)', function () {
  var big = 'A'.repeat(Math.ceil((8 * 1024 * 1024) * 4 / 3) + 8);   // 디코딩하면 8MB 초과
  var threw = '';
  try { uploadAndParseBizCert({ fileName: 'big.jpg', mimeType: 'image/jpeg', base64: big }, 'tok'); }
  catch (e) { threw = String(e.message || e); }
  __ok(/너무 큽니다/.test(threw), '안내: ' + threw);
});

__t('로그인 토큰 없으면 거부', function () {
  var threw = '';
  try { uploadAndParseBizCert({ fileName: 'a.jpg', base64: 'aGVsbG8=' }, ''); }
  catch (e) { threw = String(e.message || e); }
  __ok(/로그인이 필요합니다/.test(threw), '안내: ' + threw);
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
    ap.add_argument('--verbose', action='store_true')
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
