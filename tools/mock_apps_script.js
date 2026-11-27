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
var __HIRA_JSON = (typeof __HIRA_JSON === 'undefined') ? '{}' : __HIRA_JSON;
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
    else if (u.indexOf('/B551182/') !== -1) {
      var hira = __hiraResponse_(u);
      return { getResponseCode: function () { return hira.code; }, getContentText: function () { return hira.body; } };
    }
    else return { getResponseCode: function () { return 404; }, getContentText: function () { return ''; } };
    return { getResponseCode: function () { return 200; }, getContentText: function () { return body; } };
  }
};

/* --------------------------------------------------------------------------
   심평원(HIRA) 공공데이터포털 모의 응답
   · fixtures/hira.json 의 병원·진료과목·비급여·평가 자료를 실제 API 응답 모양으로 돌려줍니다.
   · ServiceKey 가 fixture key 와 다르면 실제처럼 403 + OpenAPI_ServiceResponse 를 냅니다.
   -------------------------------------------------------------------------- */
var __HIRA = JSON.parse(__HIRA_JSON || '{}');
var __HIRA_CALLS = [];

function __hiraParam_(url, name) {
  var m = new RegExp('[?&]' + name + '=([^&]*)').exec(String(url));
  return m ? decodeURIComponent(m[1]) : '';
}

function __hiraJson_(items, total) {
  return JSON.stringify({
    response: {
      header: { resultCode: items.length ? '00' : '03', resultMsg: items.length ? 'NORMAL SERVICE.' : 'NODATA_ERROR' },
      body: { numOfRows: items.length, pageNo: 1, totalCount: total === undefined ? items.length : total, items: { item: items } }
    }
  });
}

function __hiraXmlEscape_(s) {
  return String(s === undefined || s === null ? '' : s)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

function __hiraXml_(items, total) {
  var rows = items.map(function (it) {
    var inner = Object.keys(it).map(function (k) {
      return '<' + k + '>' + __hiraXmlEscape_(it[k]) + '</' + k + '>';
    }).join('');
    return '<item>' + inner + '</item>';
  }).join('');
  return '<?xml version="1.0" encoding="UTF-8"?>' +
    '<response><header><resultCode>' + (items.length ? '00' : '03') + '</resultCode>' +
    '<resultMsg>' + (items.length ? 'NORMAL SERVICE.' : 'NODATA_ERROR') + '</resultMsg></header>' +
    '<body><numOfRows>' + items.length + '</numOfRows><pageNo>1</pageNo>' +
    '<totalCount>' + (total === undefined ? items.length : total) + '</totalCount>' +
    '<items>' + rows + '</items></body></response>';
}

function __hiraErrorBody_(xml) {
  if (xml) {
    return '<?xml version="1.0" encoding="UTF-8"?><OpenAPI_ServiceResponse>' +
      '<cmmMsgHeader><errMsg>SERVICE_KEY_IS_NOT_REGISTERED_ERROR</errMsg>' +
      '<returnAuthMsg>등록되지 않은 서비스키</returnAuthMsg>' +
      '<returnReasonCode>30</returnReasonCode></cmmMsgHeader></OpenAPI_ServiceResponse>';
  }
  return JSON.stringify({
    OpenAPI_ServiceResponse: {
      cmmMsgHeader: {
        errMsg: 'SERVICE_KEY_IS_NOT_REGISTERED_ERROR',
        returnAuthMsg: '등록되지 않은 서비스키',
        returnReasonCode: '30'
      }
    }
  });
}

function __hiraResponse_(url) {
  var u = String(url);
  var key = __hiraParam_(u, 'ServiceKey');
  var wantJson = __hiraParam_(u, '_type') === 'json';
  var isNonPay = u.indexOf('getNonPaymentItemHospDtlList') !== -1;
  __HIRA_CALLS.push(u);

  if (__HIRA.key && key !== __HIRA.key) {
    return { code: 403, body: __hiraErrorBody_(!wantJson || isNonPay) };
  }

  var ykiho = __hiraParam_(u, 'ykiho');
  var yadmNm = __hiraParam_(u, 'yadmNm');

  if (u.indexOf('getHospBasisList') !== -1) {
    var all = (__HIRA.hospitals || []);
    var hit = all.filter(function (h) { return !yadmNm || String(h.yadmNm).indexOf(yadmNm) !== -1; });
    return { code: 200, body: wantJson ? __hiraJson_(hit, hit.length) : __hiraXml_(hit, hit.length) };
  }
  if (u.indexOf('getDgsbjtInfo2.8') !== -1) {
    var dg = ((__HIRA.dgsbjt || {})[ykiho]) || [];
    return { code: 200, body: wantJson ? __hiraJson_(dg, dg.length) : __hiraXml_(dg, dg.length) };
  }
  if (u.indexOf('getSpcSbjtSdrInfo2.8') !== -1) {
    var sd = ((__HIRA.sdr || {})[ykiho]) || [];
    return { code: 200, body: wantJson ? __hiraJson_(sd, sd.length) : __hiraXml_(sd, sd.length) };
  }
  if (isNonPay) {
    var np = ((__HIRA.nonpay || {})[ykiho]) || [];
    return { code: 200, body: __hiraXml_(np, np.length) };   // 이 서비스는 XML 만 응답
  }
  if (u.indexOf('getHospAsmInfo1') !== -1) {
    var asm = ((__HIRA.asm || {})[ykiho]) || [];
    return { code: 200, body: wantJson ? __hiraJson_(asm, asm.length) : __hiraXml_(asm, asm.length) };
  }
  return { code: 404, body: '' };
}

/* --------------------------------------------------------------------------
   XmlService 모의 구현 — parseHiraXml_ 이 쓰는 만큼만 지원
   -------------------------------------------------------------------------- */
function __XmlEl_(name, children, text) {
  this._name = name;
  this._children = children || [];
  this._text = text || '';
}
__XmlEl_.prototype.getName = function () { return this._name; };
__XmlEl_.prototype.getText = function () { return this._text; };
__XmlEl_.prototype.getChild = function (name) {
  for (var i = 0; i < this._children.length; i++) {
    if (this._children[i]._name === name) return this._children[i];
  }
  return null;
};
__XmlEl_.prototype.getChildren = function (name) {
  if (name === undefined) return this._children.slice();
  return this._children.filter(function (c) { return c._name === name; });
};

function __parseXml_(source) {
  var s = String(source || '').replace(/<\?[\s\S]*?\?>/g, '').replace(/<!--[\s\S]*?-->/g, '');
  var i = 0;
  function parseEl() {
    var m = /^<([A-Za-z0-9_:.\-]+)[^>]*>/.exec(s.slice(i));
    if (!m) return null;
    i += m[0].length;
    var name = m[1];
    var children = [];
    var text = '';
    while (i < s.length) {
      if (s.slice(i, i + 2) === '</') {
        var end = s.indexOf('>', i);
        i = end === -1 ? s.length : end + 1;
        return new __XmlEl_(name, children, text.trim());
      }
      if (s[i] === '<') {
        var child = parseEl();
        if (!child) break;
        children.push(child);
        continue;
      }
      var next = s.indexOf('<', i);
      text += (next === -1) ? s.slice(i) : s.slice(i, next);
      i = next === -1 ? s.length : next;
    }
    return new __XmlEl_(name, children, text.trim());
  }
  while (i < s.length && s[i] !== '<') i++;
  return parseEl();
}

var XmlService = {
  parse: function (source) {
    var root = __parseXml_(source);
    return { getRootElement: function () { return root; } };
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
