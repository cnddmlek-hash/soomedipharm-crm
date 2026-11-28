# -*- coding: utf-8 -*-
"""Code.gs v1.19 보안 보수 패치 (비밀번호 SHA-256 해시 + 로그인 5회 실패 잠금)

사용: python3 tools/patch_security.py <원본 Code.gs> <출력 경로>
원본은 그대로 두고, 패치된 전체 코드를 새 파일로 씁니다.
"""
import sys

SRC = sys.argv[1]
OUT = sys.argv[2]

with open(SRC, encoding='utf-8') as f:
    text = f.read()

if '\r\n' in text:
    NL = '\r\n'
else:
    NL = '\n'


def r(old, new, count=1):
    """\n 으로 쓴 문자열을 파일의 줄바꿈에 맞춰 치환"""
    global text
    o = old.replace('\n', NL)
    n = new.replace('\n', NL)
    found = text.count(o)
    if found != count:
        raise SystemExit('치환 실패(%d/%d): %r' % (found, count, old[:80]))
    text = text.replace(o, n)


# ---------------------------------------------------------------- A. 헤더 이력
r("""* ----------------------------------------------------------------------------
* v1.15 변경점 (2026-11-28) — 제품마스터 '제약사' = 실제 제조사 (페이서는 도매상)""",
  """* ----------------------------------------------------------------------------
* v1.19 보안 보수 (2026-11-28) — 비밀번호 해시 저장 + 로그인 5회 실패 잠금
*  1) 비밀번호를 평문 대신 SHA-256 해시로 저장합니다 — 'sha256$<salt>$<hex>'
*     · salt = 계정마다 다른 임의 16바이트(hex 32자), 해시 = SHA-256(salt + ':' + 비밀번호)
*     · Utilities.computeDigest(Utilities.DigestAlgorithm.SHA_256, ...) 사용
*     · 신규 가입(registerUser) · 비밀번호 변경(changePassword) · 기본 계정 생성 모두 해시로 기록
*     · 예전 평문 계정은 **로그인에 성공하는 순간** 시트의 비밀번호 칸이 해시로 자동 전환됩니다.
*  2) 로그인 5회 연속 실패 → 5분(300초) 잠금 (CacheService.getScriptCache)
*     · 아이디(trim·소문자)별로 실패 횟수·잠금 상태를 따로 셉니다.
*     · 잠금 중에는 '로그인 5회 실패로 5분간 잠금되었습니다. 잠시 후 다시 시도해 주세요.' 만 반환
*     · 로그인 성공 시 실패 카운트를 0으로 초기화합니다.
*  3) 연결 확인(?action=ping) 응답에 security 항목이 생깁니다 — 새 코드가 배포됐는지 확인용
* ----------------------------------------------------------------------------
* v1.15 변경점 (2026-11-28) — 제품마스터 '제약사' = 실제 제조사 (페이서는 도매상)""")

# ------------------------------------------------- B. 기본 계정도 해시로 기록
r("""  const userSheet = ss.getSheetByName(SHEET_NAMES.USERS);
  if (userSheet.getLastRow() <= 1) {
    userSheet.getRange(2, 1, DEFAULT_USERS.length, 5).setValues(DEFAULT_USERS);
  }""",
  """  const userSheet = ss.getSheetByName(SHEET_NAMES.USERS);
  if (userSheet.getLastRow() <= 1) {
    userSheet.getRange(2, 1, DEFAULT_USERS.length, 5).setValues(defaultUserRows_());
    markPasswordColumnAsText_(userSheet);
  }""")

r("""      sheet.getRange(2, 1, DEFAULT_USERS.length, 5).setValues(DEFAULT_USERS);""",
  """      sheet.getRange(2, 1, DEFAULT_USERS.length, 5).setValues(defaultUserRows_());
      markPasswordColumnAsText_(sheet);""")

# ------------------------------------------------------- C. 해시·잠금 헬퍼 삽입
HELPERS = """// ----------------------------------------------------------------------------
// 3-A-2. 비밀번호 해시(SHA-256 + 계정별 salt) · 로그인 실패 잠금
//   · 저장 형식: sha256$<salt>$<hex>   (평문과 확실히 구분되는 접두사)
//   · 예전 평문 비밀번호도 계속 로그인되며, 성공하는 순간 해시로 바뀝니다.
// ----------------------------------------------------------------------------
const PW_HASH_PREFIX = 'sha256$';
const LOGIN_MAX_FAILS = 5;              // 연속 실패 허용 횟수
const LOGIN_LOCK_SECONDS = 300;         // 5분 잠금
const LOGIN_FAIL_WINDOW_SECONDS = 600;  // 실패 카운트 유지 시간(마지막 실패 후 10분)
const CACHE_LOGIN_FAIL_PREFIX = 'crm_login_fail_';
const CACHE_LOGIN_LOCK_PREFIX = 'crm_login_lock_';


/** 바이트 배열 → 소문자 hex */
function bytesToHex_(bytes) {
  const arr = bytes || [];
  let out = '';
  for (let i = 0; i < arr.length; i++) {
    let b = Number(arr[i]);
    if (b < 0) b += 256;                 // computeDigest 는 부호 있는 바이트를 돌려줍니다.
    out += (b < 16 ? '0' : '') + b.toString(16);
  }
  return out;
}


/** 문자열 → SHA-256 hex (UTF-8) */
function sha256Hex_(text) {
  const digest = Utilities.computeDigest(
    Utilities.DigestAlgorithm.SHA_256,
    String(text === null || text === undefined ? '' : text),
    Utilities.Charset.UTF_8
  );
  return bytesToHex_(digest);
}


/** 계정별 salt — 임의 16바이트를 hex 32자로 */
function makePasswordSalt_() {
  let raw = '';
  try { raw = String(Utilities.getUuid() || '').replace(/-/g, '').toLowerCase(); } catch (e) { raw = ''; }
  let salt = raw.replace(/[^0-9a-f]/g, '');
  if (salt.length < 32) {
    salt += sha256Hex_(raw + ':' + String(Date.now()) + ':' + String(Math.random()));
  }
  return salt.slice(0, 32);
}


/** 비밀번호 → 저장용 해시 문자열 ('sha256$salt$hex') */
function hashPassword_(pw, salt) {
  const s = salt || makePasswordSalt_();
  const plain = String(pw === null || pw === undefined ? '' : pw).trim();
  return PW_HASH_PREFIX + s + '$' + sha256Hex_(s + ':' + plain);
}


/** 시트에 저장된 값이 해시 형식인지 */
function isPasswordHash_(stored) {
  const s = String(stored === null || stored === undefined ? '' : stored).trim();
  if (s.indexOf(PW_HASH_PREFIX) !== 0) return false;
  const parts = s.split('$');
  return parts.length === 3 && parts[1] !== '' && parts[2] !== '';
}


/**
* 입력 비밀번호가 저장값과 맞는지 — 해시/평문 모두 지원
*  · 해시: 같은 salt 로 다시 계산해 비교
*  · 평문(예전 계정): trim 한 값끼리 비교 (예전 로그인과 같은 규칙)
*/
function verifyPassword_(pw, stored) {
  const s = String(stored === null || stored === undefined ? '' : stored).trim();
  if (!s) return false;
  const plain = String(pw === null || pw === undefined ? '' : pw).trim();
  if (!plain) return false;
  if (isPasswordHash_(s)) {
    const parts = s.split('$');
    return hashPassword_(plain, parts[1]) === s;
  }
  return s === plain;
}


/** 비밀번호 열을 텍스트 서식('@')으로 — 앞자리 0·해시 문자열이 숫자로 바뀌지 않게 */
function markPasswordColumnAsText_(sheet) {
  try {
    if (!sheet) return;
    const col = headerIndex_(sheet, '비밀번호', 2);
    if (sheet.getLastRow() >= 2) sheet.getRange(2, col, sheet.getLastRow() - 1, 1).setNumberFormat('@');
  } catch (e) { /* 서식 지정 실패는 로그인을 막지 않습니다. */ }
}


/** 기본 계정(DEFAULT_USERS)을 해시 비밀번호로 바꾼 사본 — 시트에는 해시만 들어갑니다. */
function defaultUserRows_() {
  return DEFAULT_USERS.map(function (row) {
    const copy = row.slice();
    copy[1] = hashPassword_(copy[1]);
    return copy;
  });
}


/** 아이디 정규화 — trim + 소문자 (실패 카운트 키) */
function normalizeLoginId_(id) {
  return String(id === null || id === undefined ? '' : id).trim().toLowerCase();
}


/** 남은 잠금 시간(ms). 잠겨 있지 않으면 0 */
function loginLockRemainingMs_(loginKey) {
  try {
    const cache = CacheService.getScriptCache();
    const raw = cache.get(CACHE_LOGIN_LOCK_PREFIX + loginKey);
    if (!raw) return 0;
    const left = Number(raw) - Date.now();
    return left > 0 ? left : 0;
  } catch (e) {
    return 0;   // 캐시를 못 쓰는 환경에서는 잠금 없이 통과시킵니다.
  }
}


/**
* 로그인 실패 1회 기록 → 이번까지의 연속 실패 횟수
*  5회에 닿으면 5분 잠금을 걸고, 실패 카운트는 지웁니다.
*/
function registerLoginFailure_(loginKey) {
  try {
    const cache = CacheService.getScriptCache();
    const failKey = CACHE_LOGIN_FAIL_PREFIX + loginKey;
    const fails = (Number(cache.get(failKey)) || 0) + 1;
    if (fails >= LOGIN_MAX_FAILS) {
      cache.put(CACHE_LOGIN_LOCK_PREFIX + loginKey, String(Date.now() + LOGIN_LOCK_SECONDS * 1000), LOGIN_LOCK_SECONDS);
      cache.remove(failKey);
      return fails;
    }
    cache.put(failKey, String(fails), LOGIN_FAIL_WINDOW_SECONDS);
    return fails;
  } catch (e) {
    return 0;
  }
}


/** 로그인 성공 — 실패 카운트·잠금 초기화 */
function clearLoginFailures_(loginKey) {
  try {
    const cache = CacheService.getScriptCache();
    cache.remove(CACHE_LOGIN_FAIL_PREFIX + loginKey);
    cache.remove(CACHE_LOGIN_LOCK_PREFIX + loginKey);
  } catch (e) { /* 무시 */ }
}


/** 잠금 안내 문장 (남은 시간을 분 단위로) */
function loginLockMessage_(leftMs) {
  const minutes = Math.max(1, Math.ceil((Number(leftMs) || 0) / 60000));
  return '로그인 ' + LOGIN_MAX_FAILS + '회 실패로 ' + minutes + '분간 잠금되었습니다. 잠시 후 다시 시도해 주세요.';
}


/** 평문으로 남아 있는 비밀번호를 해시로 바꿔 시트에 기록 (실패해도 로그인은 계속) */
function migratePasswordToHash_(userId, plainPw) {
  try {
    if (!userId || isPasswordHash_(String(plainPw || ''))) return false;
    setPasswordCell_(userId, hashPassword_(plainPw));
    return true;
  } catch (e) {
    return false;
  }
}


"""

r("""/**
* 로그인 + 부트스트랩 데이터 동시 반환
*/
function login(id, pw) {""",
  HELPERS + """/**
* 로그인 + 부트스트랩 데이터 동시 반환
*/
function login(id, pw) {""")

# ------------------------------------------------------------ D. login 본문 교체
r("""  const loginId = String(id || '').trim();
  const loginPw = String(pw || '').trim();
  if (!loginId || !loginPw) {
    return { success: false, message: '아이디와 비밀번호를 모두 입력해 주세요.' };
  }
""",
  """  const loginId = String(id || '').trim();
  const loginPw = String(pw || '').trim();
  if (!loginId || !loginPw) {
    return { success: false, message: '아이디와 비밀번호를 모두 입력해 주세요.' };
  }

  // 0) 잠금 확인 — 5회 연속 실패한 아이디는 5분 동안 아예 비교하지 않습니다.
  const loginKey = normalizeLoginId_(loginId);
  const lockedMs = loginLockRemainingMs_(loginKey);
  if (lockedMs > 0) {
    return {
      success: false,
      locked: true,
      retryAfterSeconds: Math.ceil(lockedMs / 1000),
      message: loginLockMessage_(lockedMs)
    };
  }
""")

r("""  if (!found || found.비밀번호 !== loginPw) {
    return { success: false, message: '아이디 또는 비밀번호가 올바르지 않습니다.' };
  }
  if (found.사용여부 === 'N') {
    return { success: false, message: '관리자 승인 대기 중인 계정입니다. 마스터 승인 후 로그인할 수 있습니다.' };
  }
""",
  """  if (!found || !verifyPassword_(loginPw, found.비밀번호)) {
    // 실패 횟수 누적 — 5회째에 5분 잠금
    const fails = registerLoginFailure_(loginKey);
    if (fails >= LOGIN_MAX_FAILS) {
      return {
        success: false,
        locked: true,
        retryAfterSeconds: LOGIN_LOCK_SECONDS,
        message: loginLockMessage_(LOGIN_LOCK_SECONDS * 1000)
      };
    }
    return { success: false, message: '아이디 또는 비밀번호가 올바르지 않습니다.' };
  }

  // 비밀번호가 맞았으니 실패 카운트는 초기화
  clearLoginFailures_(loginKey);

  // 예전 평문 계정 → 지금 로그인한 비밀번호의 해시로 자동 전환 (마이그레이션)
  if (!isPasswordHash_(found.비밀번호)) {
    migratePasswordToHash_(found.아이디, loginPw);
  }

  if (found.사용여부 === 'N') {
    return { success: false, message: '관리자 승인 대기 중인 계정입니다. 마스터 승인 후 로그인할 수 있습니다.' };
  }
""")

# ------------------------------------------------------ E. changePassword 해시
r("""    if (String(found.비밀번호).trim() !== curPw) {
      return { success: false, message: '현재 비밀번호가 일치하지 않습니다.' };
    }
    setPasswordCell_(found.아이디, nextPw.trim());""",
  """    if (!verifyPassword_(curPw, found.비밀번호)) {
      return { success: false, message: '현재 비밀번호가 일치하지 않습니다.' };
    }
    setPasswordCell_(found.아이디, hashPassword_(nextPw.trim()));""")

# ---------------------------------------------------------------- F. registerUser
r("""    const sheet = getSheet_(SHEET_NAMES.USERS);
    ensureTrailingHeaders_(sheet, ['요율등급']);   // v1.6 — 등급 열이 없으면 만듭니다.
    writeRowByHeaders_(sheet, {
      '아이디': id,
      '비밀번호': pw.trim(),""",
  """    const sheet = getSheet_(SHEET_NAMES.USERS);
    ensureTrailingHeaders_(sheet, ['요율등급']);   // v1.6 — 등급 열이 없으면 만듭니다.
    const pwHash = hashPassword_(pw.trim());        // 평문이 아니라 해시로 저장
    writeRowByHeaders_(sheet, {
      '아이디': id,
      '비밀번호': pwHash,""")

r("""    // 등록 직후 비밀번호 셀을 텍스트 서식('@')으로 다시 기록 — 앞자리 0 보존
    setPasswordCell_(id, pw.trim());""",
  """    // 등록 직후 비밀번호 셀을 텍스트 서식('@')으로 다시 기록 — 해시 문자열이 숫자로 바뀌지 않게
    setPasswordCell_(id, pwHash);""")

# ------------------------------------------------------------- G. ping 보안 표식
r("""    spreadsheet: ssName,
    sheets: sheetNames,
    api: 'post+jsonp'
  };""",
  """    spreadsheet: ssName,
    sheets: sheetNames,
    api: 'post+jsonp',
    // v1.19 보안 보수 적용 표식 — 배포가 반영됐는지 확인용
    security: 'sha256+lockout' + LOGIN_MAX_FAILS + 'x' + LOGIN_LOCK_SECONDS
  };""")

with open(OUT, 'w', encoding='utf-8', newline='') as f:
    f.write(text)

print('패치 완료 →', OUT)
print('남은 평문 비교(loginPw !==) 흔적:', text.count('!== loginPw'))
print('hashPassword_ 호출 수:', text.count('hashPassword_('))
