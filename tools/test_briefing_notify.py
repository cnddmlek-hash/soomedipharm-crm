#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
v1.28 — 브리핑 신규 구독 알림 메일(Code.gs) QuickJS 테스트
--------------------------------------------------------------------
구글 Apps Script 없이 실제 Code.gs 를 모의 시트 환경(mock_apps_script.js) 위에서 돌려
subscribeBriefing 이 저장 직후 관리자 알림 메일을 보내는지 확인합니다.

  1) 신규 구독 → 알림 1건(제목·본문 항목·수신자 = 설정 «알림이메일»)
  2) «알림이메일» 이 비면 스크립트 실행 사용자 메일, 그것도 없으면 cnddmlek@gmail.com
  3) 재구독(해지 → 구독) → '재구독 신청' 제목·'재구독 여부: 재구독'
  4) 메일 실패(할당량 초과 등) → 구독은 성공(created true, notified false, 시트에 저장)
  5) 이미 구독 중인 주소의 정보 갱신 → 알림 없음
  6) 같은 주소 연속 신청(60초 중복 방지) → 알림 없음
  7) notifyBriefingSubscribe_ 는 실패해도 throw 하지 않고 {sent:false, error} 반환

사용:
    python3 tools/test_briefing_notify.py [--codegs 경로]
필요: pip install quickjs
"""
import argparse
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(HERE)

FIXTURES = {
    '설정': [
        ['설정키', '설정값', '설명'],
        ['회사명', '수메디팜', '인쇄물·PDF·이메일에 표시되는 회사명'],
        ['담당자명', '최충의', '영업 담당자'],
        ['알림이메일', 'admin@clinic.test', '신규 구독 알림을 받을 주소'],
    ],
    '뉴스레터구독자': [
        ['구독일시', '병원명', '원장성함', '이메일', '상태', '비고'],
    ],
    '거래처': [
        ['거래처코드', '거래처명', '사용여부'],
    ],
    '사용자': [
        ['아이디', '비밀번호', '담당자명', '권한', '사용여부', '이메일', '요율등급'],
    ],
}

EXT_JS = r"""
var __OWNER_EMAIL = 'owner@example.com';
Session.getEffectiveUser = function () {
  return { getEmail: function () { return __OWNER_EMAIL; } };
};

var __GMAIL = [];
var __GMAIL_FAIL = false;
GmailApp = {
  sendEmail: function (to, subject, body, options) {
    if (__GMAIL_FAIL) throw new Error('Service invoked too many times for one day: email.');
    __GMAIL.push({
      to: String(to || ''),
      subject: String(subject || ''),
      body: String(body || ''),
      name: String((options && options.name) || '')
    });
    return {};
  }
};
"""

CASES_JS = r"""
var __RESULT = { passed: 0, failed: 0, cases: [] };
function __t(name, fn) {
  try { fn(); __RESULT.passed++; __RESULT.cases.push({ name: name, ok: true }); }
  catch (e) { __RESULT.failed++; __RESULT.cases.push({ name: name, ok: false, err: String((e && e.message) || e) }); }
}
function __ok(cond, msg) { if (!cond) throw new Error(msg || '조건이 거짓'); }
function __eq(a, b, msg) { if (String(a) !== String(b)) throw new Error((msg || '') + ' 기대=' + b + ' 실제=' + a); }
function __has(text, needle, msg) {
  if (String(text).indexOf(needle) === -1) throw new Error((msg || '') + ' "' + needle + '" 없음');
}

function __reset() {
  __GMAIL = [];
  __GMAIL_FAIL = false;
  __CACHE = {};
  __OWNER_EMAIL = 'owner@example.com';
  __setSetting('알림이메일', 'admin@clinic.test');
}
function __setSetting(k, v) {
  var sh = __SHEET_OBJS['설정'];
  for (var i = 1; i < sh.values.length; i++) {
    if (String(sh.values[i][0]) === k) { sh.values[i][1] = v; return; }
  }
  sh.values.push([k, v, '테스트']);
}
function __newsletterSheet() { return getOrCreateNewsletterSheet_(); }
function __newsletterRows() {
  var sh = __SHEET_OBJS['뉴스레터구독자'];
  return sh.values.slice(1).filter(function (r) { return String(r[3] || '').trim(); });
}
function __clearNewsletter() {
  var sh = __newsletterSheet();
  sh.values = [sh.values[0].slice()];
}
function __addRow(email, status, clinic, doctor) {
  var sh = __newsletterSheet();
  sh.appendRow(['2026-11-01 09:00:00', clinic || '기존의원', doctor || '기존원장', email, status, '테스트']);
}

var PAY = {
  clinicName: '서울연세내과의원',
  doctorName: '김철수',
  email: 'doctor@seoul-yonsei.test',
  source: '홈페이지-브리핑',
  consent: true
};

// ---------- 1. 신규 구독 알림 ----------
__t('신규 구독 → 관리자 알림 1건(제목·본문·수신자)', function () {
  __reset(); __clearNewsletter();
  var r = subscribeBriefing(PAY);
  __ok(r.success, 'success');
  __ok(r.created, 'created');
  __eq(r.notified, true, 'notified');
  __eq(__GMAIL.length, 1, '알림 메일 수');
  var m = __GMAIL[0];
  __eq(m.to, 'admin@clinic.test', '수신자(설정 알림이메일)');
  __eq(m.subject, '[수메디팜 홈페이지] 새 브리핑 구독 신청 — 서울연세내과의원 (김철수 원장님)', '제목');
  __has(m.body, '신청 일시: ', '신청 일시');
  __has(m.body, '병원명: 서울연세내과의원', '병원명');
  __has(m.body, '원장님 성함: 김철수', '원장님 성함');
  __has(m.body, '이메일: doctor@seoul-yonsei.test', '이메일');
  __has(m.body, '출처: 홈페이지-브리핑', '출처');
  __has(m.body, '재구독 여부: 신규 구독', '재구독 여부');
  __eq(m.name, '수메디팜', '보내는 사람 이름');
  __eq(__newsletterRows().length, 1, '시트 행');
});

// ---------- 2. 받는 사람 대체 순서 ----------
__t('«알림이메일» 이 비면 스크립트 실행 사용자 메일로', function () {
  __reset(); __clearNewsletter();
  __setSetting('알림이메일', '');
  var r = subscribeBriefing(PAY);
  __eq(r.notified, true, 'notified');
  __eq(__GMAIL[0].to, 'owner@example.com', '수신자');
});

__t('사용자 메일도 없으면 기본 주소(cnddmlek@gmail.com)', function () {
  __reset(); __clearNewsletter();
  __setSetting('알림이메일', '');
  __OWNER_EMAIL = '';
  var r = subscribeBriefing(PAY);
  __eq(r.notified, true, 'notified');
  __eq(__GMAIL[0].to, 'cnddmlek@gmail.com', '수신자');
});

// ---------- 3. 재구독 ----------
__t('재구독(해지 → 구독) → 재구독 신청 제목·본문', function () {
  __reset(); __clearNewsletter();
  __addRow('doctor@seoul-yonsei.test', '해지');
  var r = subscribeBriefing(PAY);
  __ok(r.success && r.updated && r.resubscribed, 'updated/resubscribed');
  __eq(r.notified, true, 'notified');
  __eq(__GMAIL.length, 1, '알림 메일 수');
  __eq(__GMAIL[0].subject, '[수메디팜 홈페이지] 브리핑 재구독 신청 — 서울연세내과의원 (김철수 원장님)', '제목');
  __has(__GMAIL[0].body, '재구독 여부: 재구독 (해지 → 구독)', '재구독 여부');
  __eq(__newsletterRows().length, 1, '행이 늘지 않음');
});

// ---------- 4. 메일 실패 ----------
__t('메일 실패해도 구독 접수는 성공(created·저장 유지)', function () {
  __reset(); __clearNewsletter();
  __GMAIL_FAIL = true;
  var r = subscribeBriefing(PAY);
  __ok(r.success, 'success 는 true');
  __ok(r.created, 'created 는 true');
  __eq(r.notified, false, 'notified');
  __eq(__GMAIL.length, 0, '메일 0건');
  __eq(__newsletterRows().length, 1, '시트에는 저장됨');
  __has(r.message, '구독 신청이 접수되었습니다', '응답 안내 문구');
  __GMAIL_FAIL = false;
  var r2 = subscribeBriefing({ clinicName: '마포튼튼약국', doctorName: '박영희', email: 'park@mapo.test', source: '홈페이지', consent: true });
  __eq(r2.notified, true, '다음 신청은 정상 알림');
});

__t('notifyBriefingSubscribe_ 는 실패해도 throw 하지 않음', function () {
  __reset();
  __GMAIL_FAIL = true;
  var out = null;
  try { out = notifyBriefingSubscribe_({ clinicName: '가', doctorName: '나', email: 'a@b.test', source: '홈페이지' }); }
  catch (e) { throw new Error('예외가 밖으로 나옴: ' + e.message); }
  __eq(out.sent, false, 'sent');
  __ok(String(out.error || '').length > 0, 'error 문구');
  __GMAIL_FAIL = false;
});

// ---------- 5. 알림이 필요 없는 경우 ----------
__t('이미 구독 중인 주소의 정보 갱신 → 알림 없음', function () {
  __reset(); __clearNewsletter();
  __addRow('doctor@seoul-yonsei.test', '구독');
  var r = subscribeBriefing(PAY);
  __ok(r.success && r.updated, 'updated');
  __eq(r.resubscribed, false, 'resubscribed');
  __eq(r.notified, undefined, 'notified 없음');
  __eq(__GMAIL.length, 0, '알림 메일 0건');
});

__t('같은 주소 연속 신청(60초 중복) → 알림 없음', function () {
  __reset(); __clearNewsletter();
  subscribeBriefing(PAY);
  __eq(__GMAIL.length, 1, '첫 신청 알림 1건');
  var r2 = subscribeBriefing(PAY);
  __ok(r2.duplicate, 'duplicate');
  __eq(__GMAIL.length, 1, '두 번째는 알림 없음');
});

// ---------- 6. 검증 실패 시 메일 없음 ----------
__t('입력 검증 실패(동의 없음) → 저장·알림 없음', function () {
  __reset(); __clearNewsletter();
  var threw = '';
  try { subscribeBriefing({ clinicName: '서울연세내과의원', doctorName: '김철수', email: 'x@y.test', consent: false }); }
  catch (e) { threw = String(e.message || e); }
  __has(threw, '동의', '안내 문구');
  __eq(__GMAIL.length, 0, '알림 메일 0건');
  __eq(__newsletterRows().length, 0, '시트 행 없음');
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
    mock = io.open(os.path.join(HERE, 'mock_apps_script.js'), encoding='utf-8').read()

    ctx = quickjs.Context()

    try:
        ctx.eval('(function(){' + src + '\n})')
    except Exception as e:  # noqa: BLE001
        sys.exit('문법 오류: %s' % e)
    print('✔ 문법 검사 통과 — %s' % os.path.basename(path))

    ctx.eval('var __FIXTURES_JSON = ' + json.dumps(json.dumps(FIXTURES, ensure_ascii=False)) + ';')
    ctx.eval('var __KPIC_JSON = "{}"; var __HIRA_JSON = "{}";')
    ctx.eval(mock)
    ctx.eval(src)
    ctx.eval(EXT_JS)
    result = json.loads(ctx.eval(CASES_JS))

    for c in result['cases']:
        mark = '✔' if c['ok'] else '✘'
        print('%s %s%s' % (mark, c['name'], '' if c['ok'] else '  → ' + c.get('err', '')))
    print('\n통과 %d / 실패 %d' % (result['passed'], result['failed']))
    sys.exit(0 if result['failed'] == 0 else 1)


if __name__ == '__main__':
    main()
