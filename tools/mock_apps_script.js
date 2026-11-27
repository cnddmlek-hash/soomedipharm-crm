/* ============================================================================
   Apps Script 모의 환경 (테스트용)
   · 구글 시트/메일/속성/캐시/트리거/UrlFetch 를 메모리 객체로 흉내냅니다.
   · 실제 Code.gs 를 그대로 불러 실행하므로, 함수 로직을 그대로 검증합니다.
   ========================================================================== */
var __SHEETS = JSON.parse(__FIXTURES_JSON);
var __MAILS = [];
var __TRIGGERS = [];
var __PROPS = {};
var __CACHE = {};
var __KPIC = JSON.parse(__KPIC_JSON || '{}');
var __UI_ALERTS = [];

// v1.4에서 추가된 열이 테스트 데이터에 없으면 헤더에 붙여 줍니다.
(function ensureHeaders() {
  var add = {
    '거래처': ['원장성함', '원장생일', '취향/특이사항'],
    '제품마스터': ['성분명', '성분키'],
    '사용자': ['이메일', '요율등급']
  };
  Object.keys(add).forEach(function (name) {
    var t = __SHEETS[name];
    if (!t || !t.length) return;
    var head = t[0];
    add[name].forEach(function (h) {
      if (head.indexOf(h) === -1) {
        head.push(h);
        for (var i = 1; i < t.length; i++) while (t[i].length < head.length) t[i].push('');
      }
    });
  });
})();

function __padRow(row, n) { while (row.length < n) row.push(''); return row; }

function Range_(sheet, row, col, numRows, numCols) {
  this.sheet = sheet;
  this.row = row; this.col = col;
  this.numRows = numRows === undefined ? 1 : numRows;
  this.numCols = numCols === undefined ? 1 : numCols;
}
Range_.prototype.getValues = function () {
  var out = [];
  for (var r = 0; r < this.numRows; r++) {
    var line = [];
    for (var c = 0; c < this.numCols; c++) {
      var src = this.sheet.values[this.row - 1 + r];
      line.push(src ? (src[this.col - 1 + c] === undefined ? '' : src[this.col - 1 + c]) : '');
    }
    out.push(line);
  }
  return out;
};
Range_.prototype.getValue = function () { return this.getValues()[0][0]; };
Range_.prototype.setValue = function (v) {
  for (var r = 0; r < this.numRows; r++) {
    var idx = this.row - 1 + r;
    __padRow(this.sheet.values[idx] = this.sheet.values[idx] || [], this.col);
    this.sheet.values[idx][this.col - 1] = v;
  }
  return this;
};
Range_.prototype.setValues = function (vals) {
  for (var r = 0; r < vals.length; r++) {
    var idx = this.row - 1 + r;
    var target = this.sheet.values[idx] = this.sheet.values[idx] || [];
    for (var c = 0; c < vals[r].length; c++) target[this.col - 1 + c] = vals[r][c];
  }
  return this;
};
Range_.prototype.setNumberFormat = function () { return this; };
Range_.prototype.setBackground = function () { return this; };
Range_.prototype.setFontWeight = function () { return this; };

function Sheet_(name, values) {
  this.name = name;
  this.values = values || [];
}
Sheet_.prototype.getName = function () { return this.name; };
Sheet_.prototype.getLastRow = function () {
  var n = 0;
  for (var i = 0; i < this.values.length; i++) {
    var row = this.values[i] || [];
    for (var j = 0; j < row.length; j++) { if (String(row[j]) !== '') { n = i + 1; break; } }
  }
  return n;
};
Sheet_.prototype.getLastColumn = function () {
  var m = 0;
  for (var i = 0; i < this.values.length; i++) m = Math.max(m, (this.values[i] || []).length);
  return m;
};
Sheet_.prototype.getRange = function (row, col, numRows, numCols) {
  return new Range_(this, row, col, numRows, numCols);
};
Sheet_.prototype.appendRow = function (arr) { this.values.push(arr.slice()); };
Sheet_.prototype.deleteRow = function (i) { this.values.splice(i - 1, 1); };
Sheet_.prototype.setFrozenRows = function () { return this; };
Sheet_.prototype.getDataRange = function () {
  return new Range_(this, 1, 1, Math.max(1, this.getLastRow()), Math.max(1, this.getLastColumn()));
};

var __SHEET_OBJS = {};
Object.keys(__SHEETS).forEach(function (name) { __SHEET_OBJS[name] = new Sheet_(name, __SHEETS[name]); });

var SpreadsheetApp = {
  getActiveSpreadsheet: function () {
    return {
      getName: function () { return 'TEST_CRM'; },
      getSheetByName: function (n) { return __SHEET_OBJS[n] || null; },
      getSheets: function () { return Object.keys(__SHEET_OBJS).map(function (k) { return __SHEET_OBJS[k]; }); },
      insertSheet: function (n) { __SHEET_OBJS[n] = new Sheet_(n, []); return __SHEET_OBJS[n]; }
    };
  },
  getUi: function () {
    var menu = {
      addItem: function () { return menu; },
      addSeparator: function () { return menu; },
      addToUi: function () { return menu; }
    };
    return {
      createMenu: function () { return menu; },
      alert: function (msg) { __UI_ALERTS.push(String(msg)); }
    };
  }
};

var Session = {
  getScriptTimeZone: function () { return 'Asia/Seoul'; },
  getActiveUser: function () { return { getEmail: function () { return 'tester@example.com'; } }; }
};

function pad2_(n) { return (n < 10 ? '0' : '') + n; }

var Utilities = {
  formatDate: function (d, tz, fmt) {
    var date = (d instanceof Date) ? d : new Date(d);
    // Asia/Seoul 고정 오프셋(+9h)으로 변환
    var t = new Date(date.getTime() + 9 * 3600 * 1000);
    return String(fmt)
      .replace(/yyyy/g, String(t.getUTCFullYear()))
      .replace(/MM/g, pad2_(t.getUTCMonth() + 1))
      .replace(/dd/g, pad2_(t.getUTCDate()))
      .replace(/HH/g, pad2_(t.getUTCHours()))
      .replace(/mm/g, pad2_(t.getUTCMinutes()))
      .replace(/ss/g, pad2_(t.getUTCSeconds()));
  },
  getUuid: function () { return 'uuid-' + Math.random().toString(16).slice(2); },
  base64Encode: function (s) { return String(s).replace(/[^A-Za-z0-9]/g, '_').slice(0, 80); },
  newBlob: function (a, b) { return { a: a, b: b }; }
};

var PropertiesService = {
  getScriptProperties: function () {
    return {
      getProperty: function (k) { return __PROPS[k] === undefined ? null : __PROPS[k]; },
      setProperty: function (k, v) { __PROPS[k] = String(v); },
      deleteProperty: function (k) { delete __PROPS[k]; },
      getProperties: function () { return JSON.parse(JSON.stringify(__PROPS)); }
    };
  }
};

var CacheService = {
  getScriptCache: function () {
    return {
      get: function (k) { return __CACHE[k] === undefined ? null : __CACHE[k]; },
      put: function (k, v) { __CACHE[k] = String(v); },
      remove: function (k) { delete __CACHE[k]; }
    };
  }
};

var MailApp = {
  sendEmail: function (opt) {
    if (!opt || !opt.to) throw new Error('수신자 없음');
    __MAILS.push({ to: opt.to, subject: opt.subject, body: opt.body, name: opt.name });
    return {};
  }
};

var ScriptApp = {
  getProjectTriggers: function () { return __TRIGGERS.slice(); },
  newTrigger: function (fn) {
    var t = {
      fn: fn,
      getHandlerFunction: function () { return fn; },
      timeBased: function () { return t; },
      atHour: function () { return t; },
      everyDays: function () { return t; },
      create: function () { __TRIGGERS.push(t); return t; }
    };
    return t;
  },
  deleteTrigger: function (t) {
    var i = __TRIGGERS.indexOf(t);
    if (i >= 0) __TRIGGERS.splice(i, 1);
    else {
      for (var k = __TRIGGERS.length - 1; k >= 0; k--) {
        if (__TRIGGERS[k] === t || (t && __TRIGGERS[k].fn === t.fn)) { __TRIGGERS.splice(k, 1); break; }
      }
    }
  }
};

var UrlFetchApp = {
  fetch: function (url) {
    var body = '';
    var u = String(url);
    if (u.indexOf('api/searchDrug') !== -1) body = JSON.stringify(__kpicSearchResponse_(u));
    else if (u.indexOf('ajax_result_drug2') !== -1) body = JSON.stringify(__kpicDetailResponse_(u));
    else return { getResponseCode: function () { return 404; }, getContentText: function () { return ''; } };
    return { getResponseCode: function () { return 200; }, getContentText: function () { return body; } };
  }
};

/** 약학정보원 검색 모의 응답 — drugName 파라미터로 실제 검색처럼 걸러 줍니다 */
function __kpicSearchResponse_(url) {
  var all = (__KPIC.search && __KPIC.search.items) || [];
  var m = /[?&]drugName=([^&]*)/.exec(String(url));
  var q = m ? decodeURIComponent(m[1]).replace(/\s+/g, '') : '';
  if (!q) return { items: all, total: all.length };
  var hit = all.filter(function (it) {
    var n = String(it.drug_name || '').replace(/\s+/g, '');
    var ing = String(it.list_sunb_name || '').replace(/\s+/g, '').toLowerCase();
    return n.indexOf(q) !== -1 || (q.length >= 3 && ing.indexOf(q.toLowerCase()) !== -1);
  });
  if (!hit.length) return { items: all, total: (__KPIC.search && __KPIC.search.total) || all.length };
  return { items: hit, total: hit.length };
}

/** 약학정보원 상세 모의 응답 — drug_cd 로 골라 줍니다 */
function __kpicDetailResponse_(url) {
  var all = (__KPIC.detail && __KPIC.detail.length !== undefined) ? __KPIC.detail : (__KPIC.detail ? [__KPIC.detail] : []);
  var m = /[?&]drug_cd=([^&]*)/.exec(String(url));
  var code = m ? decodeURIComponent(m[1]) : '';
  if (!code) return all;
  var hit = all.filter(function (d) { return String(d.drug_code) === code; });
  return hit.length ? hit : all;
}

var ContentService = {
  MimeType: { JSON: 'json', JAVASCRIPT: 'js' },
  createTextOutput: function (s) {
    return { setMimeType: function () { return { getContent: function () { return s; } }; }, _s: s };
  }
};

var HtmlService = {
  XFrameOptionsMode: { ALLOWALL: 'ALLOWALL' },
  createHtmlOutputFromFile: function () {
    return {
      setTitle: function () { return this; },
      addMetaTag: function () { return this; },
      setXFrameOptionsMode: function () { return this; }
    };
  }
};

var LockService = {
  getScriptLock: function () {
    return { tryLock: function () { return true; }, releaseLock: function () {}, waitLock: function () {} };
  },
  getDocumentLock: function () { return this.getScriptLock(); }
};

var Logger = { log: function () {} };
