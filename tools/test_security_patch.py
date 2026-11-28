# -*- coding: utf-8 -*-
"""Code.gs v1.19 보안 보수(해시·잠금) 검증 — QuickJS + 모의 Apps Script 위에서 실행

사용: python3 tools/test_security_patch.py [Code.gs 경로]
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CODE = os.path.join(os.path.dirname(HERE), '..', '..', 'downloads', 'Code.gs')

SHA256_JS = r"""
/* ---- 테스트용 SHA-256 (mock: Apps Script computeDigest 대체) ---- */
function __sha256hex(bytes) {
  var K = [0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,
           0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,
           0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,
           0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,
           0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,
           0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,
           0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,
           0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2];
  var H = [0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19];
  function rotr(x, n) { return ((x >>> n) | (x << (32 - n))) >>> 0; }
  var msg = bytes.slice();
  var bitLen = msg.length * 8;
  msg.push(0x80);
  while (msg.length % 64 !== 56) msg.push(0);
  msg.push(0, 0, 0, 0);
  msg.push((bitLen >>> 24) & 255, (bitLen >>> 16) & 255, (bitLen >>> 8) & 255, bitLen & 255);
  for (var off = 0; off < msg.length; off += 64) {
    var w = [];
    for (var i = 0; i < 16; i++) {
      w[i] = ((msg[off + i * 4] << 24) | (msg[off + i * 4 + 1] << 16) | (msg[off + i * 4 + 2] << 8) | msg[off + i * 4 + 3]) >>> 0;
    }
    for (i = 16; i < 64; i++) {
      var s0 = (rotr(w[i - 15], 7) ^ rotr(w[i - 15], 18) ^ (w[i - 15] >>> 3)) >>> 0;
      var s1 = (rotr(w[i - 2], 17) ^ rotr(w[i - 2], 19) ^ (w[i - 2] >>> 10)) >>> 0;
      w[i] = (w[i - 16] + s0 + w[i - 7] + s1) >>> 0;
    }
    var a = H[0], b = H[1], c = H[2], d = H[3], e = H[4], f = H[5], g = H[6], h = H[7];
    for (i = 0; i < 64; i++) {
      var S1 = (rotr(e, 6) ^ rotr(e, 11) ^ rotr(e, 25)) >>> 0;
      var ch = ((e & f) ^ (~e & g)) >>> 0;
      var t1 = (h + S1 + ch + K[i] + w[i]) >>> 0;
      var S0 = (rotr(a, 2) ^ rotr(a, 13) ^ rotr(a, 22)) >>> 0;
      var maj = ((a & b) ^ (a & c) ^ (b & c)) >>> 0;
      var t2 = (S0 + maj) >>> 0;
      h = g; g = f; f = e; e = (d + t1) >>> 0; d = c; c = b; b = a; a = (t1 + t2) >>> 0;
    }
    H[0] = (H[0] + a) >>> 0; H[1] = (H[1] + b) >>> 0; H[2] = (H[2] + c) >>> 0; H[3] = (H[3] + d) >>> 0;
    H[4] = (H[4] + e) >>> 0; H[5] = (H[5] + f) >>> 0; H[6] = (H[6] + g) >>> 0; H[7] = (H[7] + h) >>> 0;
  }
  return H.map(function (x) { return ('00000000' + x.toString(16)).slice(-8); }).join('');
}

function __utf8Bytes(str) {
  var out = [], s = String(str);
  for (var i = 0; i < s.length; i++) {
    var c = s.charCodeAt(i);
    if (c < 0x80) out.push(c);
    else if (c < 0x800) { out.push(0xC0 | (c >> 6), 0x80 | (c & 63)); }
    else if (c >= 0xD800 && c <= 0xDBFF && i + 1 < s.length) {
      var c2 = s.charCodeAt(++i);
      var cp = 0x10000 + ((c - 0xD800) << 10) + (c2 - 0xDC00);
      out.push(0xF0 | (cp >> 18), 0x80 | ((cp >> 12) & 63), 0x80 | ((cp >> 6) & 63), 0x80 | (cp & 63));
    } else { out.push(0xE0 | (c >> 12), 0x80 | ((c >> 6) & 63), 0x80 | (c & 63)); }
  }
  return out;
}

Utilities.DigestAlgorithm = { SHA_256: 'SHA_256', MD5: 'MD5' };
Utilities.Charset = { UTF_8: 'UTF_8' };
Utilities.computeDigest = function (algo, text) {
  var hex = __sha256hex(__utf8Bytes(text));
  var bytes = [];
  for (var i = 0; i < hex.length; i += 2) {
    var b = parseInt(hex.substr(i, 2), 16);
    if (b > 127) b -= 256;          // Apps Script 는 부호 있는 바이트를 돌려줍니다.
    bytes.push(b);
  }
  return bytes;
};
if (typeof LockService === 'undefined') {
  var LockService = {
    getScriptLock: function () { return { waitLock: function () {}, releaseLock: function () {} }; }
  };
}
"""

TESTS_JS = r"""
var __RESULTS = [];
function ok(cond, name, extra) {
  __RESULTS.push({ name: name, ok: !!cond, err: cond ? '' : String(extra || '') });
}
function userRow_(id) {
  var sh = __SHEET_OBJS['사용자'];
  for (var i = 1; i < sh.values.length; i++) {
    if (String(sh.values[i][0]) === id) return sh.values[i];
  }
  return null;
}
function cacheClear_(prefix) {
  for (var k in __CACHE) if (k.indexOf(prefix) === 0) delete __CACHE[k];
}

/* 0) 로그인 응답을 가볍게 — 부트스트랩(시트 여러 개) 대신 스텁 */
buildBootstrapPayload_ = function (user) { return { user: user, stub: true }; };

/* 1) 해시 형식 */
var h1 = hashPassword_('1234');
ok(/^sha256\$[0-9a-f]{32}\$[0-9a-f]{64}$/.test(h1), '해시 형식 sha256$salt$hex', h1);
var h2 = hashPassword_('1234');
ok(h1 !== h2, '같은 비밀번호라도 salt 가 달라 해시가 다름');
ok(isPasswordHash_(h1) === true, 'isPasswordHash_ 해시 인식');
ok(isPasswordHash_('1234') === false, 'isPasswordHash_ 평문은 false');
ok(isPasswordHash_('sha256$abc') === false, 'isPasswordHash_ 형식 불완전 false');

/* 2) 검증 */
ok(verifyPassword_('1234', h1) === true, '해시 비밀번호 일치');
ok(verifyPassword_('12345', h1) === false, '해시 비밀번호 불일치');
ok(verifyPassword_('1234', '1234') === true, '평문 비밀번호 일치(구 계정)');
ok(verifyPassword_('9999', '1234') === false, '평문 비밀번호 불일치');
ok(verifyPassword_(' 1234 ', h1) === true, '앞뒤 공백은 무시(예전과 같은 규칙)');
ok(verifyPassword_('', h1) === false, '빈 비밀번호 거부');

/* 3) bytesToHex_ — 부호 있는 바이트 */
ok(bytesToHex_([0, 15, 16, 127, -1, -128]) === '000f107fff80', 'bytesToHex_ 부호 바이트 처리', bytesToHex_([0, 15, 16, 127, -1, -128]));
ok(sha256Hex_('abc') === 'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad', 'sha256Hex_ 표준값(abc)', sha256Hex_('abc'));
ok(sha256Hex_('한글') === __sha256hex(__utf8Bytes('한글')), 'sha256Hex_ 한글 UTF-8');

/* 4) 기본 계정 시드는 해시 */
var seeded = defaultUserRows_();
ok(seeded.length === DEFAULT_USERS.length && isPasswordHash_(seeded[0][1]) && seeded[0][0] === 'master', '기본 계정 비밀번호도 해시로 시드');
ok(verifyPassword_(DEFAULT_USERS[0][1], seeded[0][1]) === true, '시드 해시로 원래 비밀번호 로그인 가능');

/* 5) 평문 계정 로그인 → 자동 해시 전환 */
cacheClear_('crm_login_');
var rowBefore = userRow_('master')[1];
ok(!isPasswordHash_(String(rowBefore)), '픽스처 master 는 평문으로 시작', rowBefore);
var res1 = login('master', '1234');
ok(res1 && res1.success === true, '평문 계정 로그인 성공', JSON.stringify(res1).slice(0, 200));
ok(isPasswordHash_(String(userRow_('master')[1])), '로그인 성공 즉시 시트 비밀번호가 해시로 전환', String(userRow_('master')[1]));
var res2 = login('master', '1234');
ok(res2 && res2.success === true, '해시로 바뀐 뒤에도 같은 비밀번호로 로그인');
ok(isPasswordHash_(String(userRow_('master')[1])), '두 번째 로그인에서도 해시 유지');
var resBad = login('master', '0000');
ok(resBad && resBad.success === false && resBad.message.indexOf('올바르지 않습니다') !== -1, '틀린 비밀번호는 실패');

/* 6) 5회 실패 잠금 */
cacheClear_('crm_login_');
var lastMsg = '';
for (var i = 0; i < 5; i++) {
  var r5 = login('choi', 'wrong' + i);
  lastMsg = r5.message;
}
ok(lastMsg.indexOf('로그인 5회 실패로 5분간 잠금되었습니다') === 0, '5회째에 5분 잠금 안내', lastMsg);
var lockedTry = login('choi', 'abcd');           // 비밀번호는 맞지만 잠금 중
ok(lockedTry.success === false && lockedTry.locked === true, '잠금 중에는 맞는 비밀번호도 차단', JSON.stringify(lockedTry));
ok(String(lockedTry.message).indexOf('5분간 잠금') !== -1, '잠금 안내 문구', lockedTry.message);
var lockedUnknown = login('CHOi', 'abcd');       // 아이디 정규화(소문자·trim)도 같은 잠금
ok(lockedUnknown.success === false && lockedUnknown.locked === true, '아이디 대소문자·공백 정규화해서 같은 잠금', JSON.stringify(lockedUnknown));

/* 잠금 해제(시간 경과 흉내) 후에는 정상 로그인 */
cacheClear_('crm_login_lock_');
var afterUnlock = login('choi', 'abcd');
ok(afterUnlock && afterUnlock.success === true, '5분 경과(잠금 해제) 후 정상 로그인', JSON.stringify(afterUnlock).slice(0, 200));
ok(isPasswordHash_(String(userRow_('choi')[1])), 'choi 계정도 해시로 전환');

/* 7) 성공 시 실패 카운트 초기화 — 4회 실패 후 성공하면 다시 4회까지는 잠기지 않음 */
cacheClear_('crm_login_');
for (i = 0; i < 4; i++) login('master', 'nope');
var okAfter4 = login('master', '1234');
ok(okAfter4 && okAfter4.success === true, '4회 실패 후 성공 로그인');
for (i = 0; i < 4; i++) login('master', 'nope');
var stillOpen = login('master', '1234');
ok(stillOpen && stillOpen.success === true, '성공이 실패 카운트를 초기화함(다시 4회까지는 열려 있음)');
cacheClear_('crm_login_');
for (i = 0; i < 5; i++) login('master', 'nope');
var nowLocked = login('master', '1234');
ok(nowLocked.success === false && nowLocked.locked === true, '연속 5회 실패면 잠금');

/* 8) 비밀번호 변경 — 현재 비밀번호 검증(해시) + 새 비밀번호 해시 저장 */
cacheClear_('crm_login_');
var tok = login('master', '1234').token;
var chWrong = changePassword('0000', 'newpw1', tok);
ok(chWrong.success === false, '비밀번호 변경 — 현재 비밀번호 틀리면 거부');
var chOk = changePassword('1234', 'newpw1', tok);
ok(chOk.success === true, '비밀번호 변경 성공', JSON.stringify(chOk));
ok(isPasswordHash_(String(userRow_('master')[1])), '변경된 비밀번호도 해시로 저장');
ok(login('master', '1234').success === false, '예전 비밀번호로는 로그인 실패');
ok(login('master', 'newpw1').success === true, '새 비밀번호로 로그인 성공');

/* 9) 회원가입 — 해시 저장 + 승인 전 로그인 불가 */
var reg = registerUser('newbie', 'pass1234', '신규담당');
ok(reg && reg.success === true, '회원가입 신청 성공', JSON.stringify(reg));
var newRow = userRow_('newbie');
ok(newRow && isPasswordHash_(String(newRow[1])), '신규 가입 비밀번호 해시 저장', newRow ? String(newRow[1]) : 'no row');
ok(String(newRow[4]) === 'N', '신규 가입은 사용여부 N');
var pending = login('newbie', 'pass1234');
ok(pending.success === false && String(pending.message).indexOf('승인 대기') !== -1, '승인 전 로그인 차단 안내', JSON.stringify(pending));

/* 10) ping 응답의 보안 표식 */
var st = apiStatus_();
ok(st && String(st.security || '').indexOf('sha256+lockout5x300') === 0, 'ping security 표식', String(st.security));

__TEST_RESULT__ = JSON.stringify({
  passed: __RESULTS.filter(function (c) { return c.ok; }).length,
  failed: __RESULTS.filter(function (c) { return !c.ok; }).length,
  cases: __RESULTS
});
"""

FIXTURES = {
    '사용자': [
        ['아이디', '비밀번호', '담당자명', '권한', '사용여부', '이메일', '요율등급'],
        ['master', '1234', '마스터', 'MASTER', 'Y', '', ''],
        ['choi', 'abcd', '최충의', 'STAFF', 'Y', '', ''],
    ],
    '설정': [
        ['설정키', '설정값', '메모'],
        ['접근PIN', '', ''],
        ['담당자이메일', '', ''],
    ],
}


def main():
    import quickjs
    code_path = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else DEFAULT_CODE)
    ctx = quickjs.Context()
    ctx.eval('var __FIXTURES_JSON = %s;' % json.dumps(json.dumps(FIXTURES)))
    ctx.eval('var __KPIC_JSON = "{}";')
    ctx.eval('var __HIRA_JSON = "{}";')
    ctx.eval(open(os.path.join(HERE, 'mock_apps_script.js'), encoding='utf-8').read())
    try:
        ctx.eval(SHA256_JS)
        ctx.eval(open(code_path, encoding='utf-8').read())
        ctx.eval(TESTS_JS)
    except Exception as e:  # noqa: BLE001
        print('실행 실패:', e)
        raw = ctx.eval('typeof __TEST_RESULT__ === "string" ? __TEST_RESULT__ : ""')
        if raw:
            print(raw)
        return 2
    raw = ctx.eval('__TEST_RESULT__')
    if isinstance(raw, bytes):
        raw = raw.decode('utf-8')
    result = json.loads(raw)
    for case in result['cases']:
        print(('  ✓ ' if case['ok'] else '  ✗ ') + case['name'] + ('' if case['ok'] else '  → ' + case['err']))
    print('=' * 60)
    print('Code.gs 보안 패치 테스트: 통과 %d / 실패 %d' % (result['passed'], result['failed']))
    return 0 if result['failed'] == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
