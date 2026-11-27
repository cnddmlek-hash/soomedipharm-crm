/* ============================================================================
   Code.gs v1.4 테스트 (mock_apps_script.js 위에서 실행)
   결과: __TEST_RESULT__ = {"passed":n,"failed":m,"cases":[{name, ok, err}]}
   ========================================================================== */
var RESULTS = [];
function t(name, fn) {
  try { fn(); RESULTS.push({ name: name, ok: true }); }
  catch (e) { RESULTS.push({ name: name, ok: false, err: String((e && e.message) || e) }); }
}
function ok(cond, msg) { if (!cond) throw new Error(msg || '조건이 거짓'); }
function eq(actual, expected, msg) {
  if (String(actual) !== String(expected)) throw new Error((msg || '') + ' 기대=' + expected + ' 실제=' + actual);
}
function near(actual, expected, tol, msg) {
  if (Math.abs(Number(actual) - Number(expected)) > (tol || 0.001)) throw new Error((msg || '') + ' 기대≈' + expected + ' 실제=' + actual);
}
function throwsMatch(fn, pattern, msg) {
  var err = null;
  try { fn(); } catch (e) { err = e; }
  if (!err) throw new Error((msg || '예외가 발생해야 함'));
  if (pattern && !new RegExp(pattern).test(String(err.message || err))) {
    throw new Error((msg || '예외 문구 불일치') + ' 실제=' + String(err.message || err));
  }
}

var LOGIN = login('master', 'test');
var TOKEN = LOGIN.token || 'no-token';
var STAFF = login('choi', 'test');
var STAFF_TOKEN = STAFF.token || 'no-token';

// --- 오늘/내일 날짜 도우미 (테스트 데이터에 생일을 심을 때 사용) ---
function mmdd_(offsetDays) {
  var d = new Date(Date.now() + offsetDays * 86400000);
  // +9h 보정 후 월·일만
  var t = new Date(d.getTime() + 9 * 3600 * 1000);
  var mm = t.getUTCMonth() + 1, dd = t.getUTCDate();
  return (mm < 10 ? '0' : '') + mm + '-' + (dd < 10 ? '0' : '') + dd;
}

// ------------------------------------------------------------------ 1. 성분키 정규화
t('로그인 성공(마스터)', function () { ok(LOGIN.success, '로그인 실패: ' + LOGIN.message); ok(TOKEN.length > 5, '토큰 없음'); });
t('로그인 실패(잘못된 비번)', function () { ok(!login('master', 'wrong').success, '실패해야 함'); });

t('성분키: Ceftriaxone Sodium Hydrate 1g', function () { eq(ingredientKey_('Ceftriaxone Sodium Hydrate 1g'), 'ceftriaxone'); });
t('성분키: 염이 붙은 조합 성분', function () {
  eq(ingredientKey_('Amlodipine Besylate 6.94mg|Losartan potassium 100mg'), 'amlodipine+losartan');
});
t('성분키: 전해질 수액은 이름 유지', function () {
  eq(ingredientKey_('Sodium chloride 0.9%'), 'sodium chloride');
  eq(ingredientKey_('Magnesium sulfate 2g'), 'magnesium');
});
t('성분키: 한글만 있으면 빈 값(사전 영문키 사용)', function () { eq(ingredientKey_('황산마그네슘'), ''); });
t('성분키: 단위·값 제거', function () { eq(ingredientKey_('Cefotaxime Sodium 1g'), 'cefotaxime'); });

// ------------------------------------------------------------------ 2. 통합 제품 목록
t('제품 목록: 제품마스터+이엘파마 모두 읽음', function () {
  var rows = readProductRows_();
  ok(rows.length > 200, '너무 적음: ' + rows.length);
  ok(rows.some(function (r) { return r.표 === '주사·수액'; }), '주사 제품 없음');
  ok(rows.some(function (r) { return r.표 === '경구'; }), '경구 제품 없음');
});
t('제품 목록: 수수료율이 숫자로 들어옴', function () {
  var rows = readProductRows_();
  ok(rows.some(function (r) { return r.수수료율 > 0; }), '수수료율 0만 있음');
});

// ------------------------------------------------------------------ 3. 통합 검색 · 동일 성분 묶음
t('검색: 세프트리악손 → 같은 성분으로 묶임', function () {
  var res = searchProductsV14('세프트리악손', {}, TOKEN);
  ok(res.total > 0, '검색 결과 없음');
  ok(res.groups.length > 0, '성분 묶음 없음');
  eq(res.groups[0].key, 'ceftriaxone');
  ok(res.groups[0].items.length >= 1, '묶인 품목 없음');
});
t('검색: 보험코드로도 찾힘', function () {
  var res = searchProductsV14('647202372', {}, TOKEN);
  ok(res.total > 0, '코드 검색 실패');
});
t('검색: scope=경구 는 경구만', function () {
  var res = searchProductsV14('정', { scope: '경구', limit: 40 }, TOKEN);
  ok(res.items.length > 0, '경구 결과 없음');
  ok(res.items.every(function (p) { return p.표 === '경구'; }), '주사 제품 섞임');
});
t('검색: 빈 검색어는 빈 결과', function () {
  var res = searchProductsV14('', {}, TOKEN);
  eq(res.total, 0); eq(res.groups.length, 0);
});
t('검색: 오타(세프트락손) → 연관 제품 추천', function () {
  var res = searchProductsV14('세프트락손', {}, TOKEN);
  ok(res.similar.length > 0, '비슷한 이름 제안이 없음');
});
t('검색: 초성(ㅅㅍㅌㄹㅇㅅ) → 연관 제품', function () {
  var res = searchProductsV14('ㅅㅍㅌㄹㅇㅅ', {}, TOKEN);
  ok(res.similar.length > 0, '초성 검색 제안 없음');
});
t('검색: 결과에 타사 단가표도 함께', function () {
  var res = searchProductsV14('마늘', {}, TOKEN);
  ok(res.thirdParty.length > 0, '타사 단가 매칭 없음');
});
t('검색: 성분 한글명이 붙음', function () {
  var res = getSameIngredientProducts('ceftriaxone', TOKEN);
  eq(res.성분한글, '세프트리악손');
  ok(res.items.length >= 1, '동일 성분 품목 없음');
  ok(res.금기 && res.금기.병용.length > 0, '성분사전 금기 요약 없음');
});

// ------------------------------------------------------------------ 4. 타사 단가표
t('단가표: 휴온스 비급여 마늘주사 계단', function () {
  var res = searchThirdPartyPrices('마늘', 30, TOKEN);
  ok(res.products.length > 0, '단가표 검색 실패');
  var p = res.products.filter(function (x) { return x.제품명.indexOf('비타메스') !== -1; })[0];
  ok(p, '비타메스 단가 없음');
  ok(p.tiers.length >= 2, '수량 조건이 1개뿐');
});
t('단가표: 성분키로도 검색', function () {
  var res = searchThirdPartyPrices('글루타치온', 30, TOKEN);
  ok(res.total > 0, '성분 검색 실패');
});
t('단가표: 빈 검색어는 전체 개수만', function () {
  var res = searchThirdPartyPrices('', 10, TOKEN);
  ok(res.all > 0, '단가표가 비어 있음');
  ok(res.products.length <= 10, 'limit 미적용');
});

// ------------------------------------------------------------------ 5. 진료과 가이드 · 추천
t('가이드: 진료과 목록', function () {
  var res = getDeptGuide('', TOKEN);
  ok(res.depts.length >= 8, '진료과가 너무 적음');
  ok(typeof res.depts[0].진료과 === 'string' && res.depts[0].진료과.length > 0, '형식 오류');
});
t('가이드: 내과 성분 + 우리 제품 매칭', function () {
  var res = getDeptGuide('내과', TOKEN);
  ok(res.items.length >= 10, '성분 수 부족');
  ok(res.items.some(function (i) { return i.우리제품 && i.우리제품.length > 0; }), '우리 제품 매칭 없음');
});
t('추천: 최고요율 모드는 성분별 최고 수수료율', function () {
  var keys = ['amlodipine', 'rosuvastatin'];
  var res = recommendRegimen({ mode: 'maxrate', ingredients: keys }, TOKEN);
  ok(res.picks.length > 0, '추천 없음');
  keys.forEach(function (k) {
    var all = readProductRows_().filter(function (p) { return p.성분키 === k; });
    if (!all.length) return;
    var best = Math.max.apply(null, all.map(function (p) { return Number(p.수수료율) || 0; }));
    var pick = res.picks.filter(function (x) { return x.성분키 === k; })[0];
    ok(pick, k + ' 추천 누락');
    eq(pick.수수료율, best, k + ' 최고요율 아님');
  });
});
t('추천: 최소 제약사 모드는 제약사 수를 줄임', function () {
  var keys = readProductRows_().filter(function (p) { return p.성분키; }).slice(0, 40)
    .map(function (p) { return p.성분키; })
    .filter(function (k, i, a) { return a.indexOf(k) === i; }).slice(0, 6);
  var max = recommendRegimen({ mode: 'maxrate', ingredients: keys }, TOKEN);
  var min = recommendRegimen({ mode: 'minmaker', ingredients: keys }, TOKEN);
  ok(min.picks.length > 0, '추천 없음');
  ok(min.summary.제약사수 <= max.summary.제약사수, '제약사 수가 줄지 않음');
});
t('추천: 성분 없이 호출하면 오류', function () {
  throwsMatch(function () { recommendRegimen({ mode: 'maxrate', ingredients: [] }, TOKEN); }, '성분');
});
t('추천: 권한 없는 토큰 거부', function () {
  throwsMatch(function () { recommendRegimen({ ingredients: ['aspirin'] }, 'bad-token'); }, '로그인');
});

// ------------------------------------------------------------------ 6. 약학정보원 연계
t('약학정보원: 검색 결과 매핑', function () {
  var res = kpicSearch('타이레놀', 5, TOKEN);
  ok(res.items.length > 0, '검색 결과 없음: ' + (res.error || ''));
  var it = res.items[0];
  ok(it.drugCode, '약 코드 없음');
  ok(it.name, '제품명 없음');
  ok('성분키' in it, '성분키 필드 없음');
  ok(it.url.indexOf('health.kr') !== -1, '상세 URL 없음');
});
t('약학정보원: 상세에서 금기(DUR) 가져옴', function () {
  var res = kpicDrugDetail('2020111100006', TOKEN);
  ok(res.금기, '금기 객체 없음');
  ok(res.금기.병용.length > 0, '병용금기 비어 있음');
  ok(res.금기.임부.length > 0, '임부금기 비어 있음');
  ok(res.효능.length > 0, '효능 비어 있음');
});
t('약학정보원: 상세에서 우리 제품 매칭', function () {
  var res = kpicDrugDetail('2020111100006', TOKEN);
  ok(Array.isArray(res.우리제품), '우리제품 배열 아님');
});

// ------------------------------------------------------------------ 7. 거래처 상세 · 생일
t('생일: MM-DD 파싱', function () {
  var b = parseBirthday_('04-08');
  eq(b.month, 4); eq(b.day, 8);
});
t('생일: YYYY-MM-DD 파싱', function () {
  var b = parseBirthday_('1991-04-08');
  eq(b.year, 1991); eq(b.month, 4); eq(b.day, 8);
});
t('생일: 잘못된 값은 null', function () {
  ok(parseBirthday_('생일없음') === null);
});
t('생일: D-day 계산(오늘/내일/연말 넘김)', function () {
  var today = new Date(2026, 11, 31); // 12/31
  eq(daysUntilBirthday_('12-31', today), 0);
  eq(daysUntilBirthday_('01-01', today), 1);
  eq(daysUntilBirthday_('12-30', today), 364);
});
t('생일: 내 거래처 D-1 목록 (내일 생일 심기)', function () {
  var list = __SHEETS['거래처'];
  var head = list[0];
  var iCode = head.indexOf('거래처코드'), iBirth = head.indexOf('원장생일'), iName = head.indexOf('원장성함');
  list[1][iBirth] = mmdd_(1);
  list[1][iName] = '김원장';
  list[2][iBirth] = mmdd_(2);
  var res = getDoctorBirthdays(1, TOKEN);
  ok(res.items.length >= 1, 'D-1 대상 없음');
  eq(res.items[0].dday, 1);
  eq(res.items[0].원장성함, '김원장');
});
t('거래처 상세 저장: 잘못된 생일은 거부', function () {
  var code = __SHEETS['거래처'][1][0];
  throwsMatch(function () { saveClientProfile({ 거래처코드: code, 원장생일: '13-99' }, TOKEN); }, '생일');
});
t('거래처 상세 저장: 값이 시트에 반영', function () {
  var code = __SHEETS['거래처'][1][0];
  var res = saveClientProfile({ 거래처코드: code, 원장성함: '박원장', 원장생일: '07-15', 취향: '커피, 등산' }, TOKEN);
  ok(res.success, '저장 실패');
  var c = res.clients.filter(function (x) { return x.거래처코드 === code; })[0];
  eq(c.원장성함, '박원장'); eq(c.원장생일, '07-15'); eq(c.취향, '커피, 등산');
});
t('거래처 상세 검색: 취향으로 찾기', function () {
  var res = searchClientsProfile('등산', TOKEN);
  ok(res.total >= 1, '취향 검색 실패');
});
t('거래처 상세 검색: 생일 가까운 순 정렬', function () {
  var res = searchClientsProfile('', TOKEN);
  var withBD = res.items.filter(function (x) { return x.생일까지 !== null; });
  ok(withBD.length >= 2, '생일 있는 거래처 부족');
  ok(withBD[0].생일까지 <= withBD[1].생일까지, '정렬 안 됨');
});

// ------------------------------------------------------------------ 8. 생일 알림 메일 · 트리거
t('생일 알림: 담당자 메일로 발송', function () {
  __MAILS.length = 0;
  // 이메일이 등록된 담당자를 골라 그 담당자의 거래처에 생일을 심습니다.
  var users = getUsersList(TOKEN).users.filter(function (u) { return u.이메일 && u.사용여부 !== 'N'; });
  ok(users.length > 0, '이메일이 등록된 사용자가 없습니다');
  var mgr = users[0].담당자명, mailTo = users[0].이메일;
  var list = __SHEETS['거래처'];
  var iBirth = list[0].indexOf('원장생일'), iMgr = list[0].indexOf('담당자');
  list[3][iBirth] = mmdd_(1);
  list[3][iMgr] = mgr;
  var res = checkDoctorBirthdaysDaily();
  ok(res.items >= 1, '대상 없음');
  ok(__MAILS.length >= 1, '메일 미발송 (건너뜀: ' + JSON.stringify(res.skipped) + ')');
  var mail = __MAILS.filter(function (m) { return m.to === mailTo; })[0];
  ok(mail, '담당자 주소로 발송되지 않음: ' + JSON.stringify(__MAILS.map(function (m) { return m.to; })));
  ok(mail.subject.indexOf('생일') !== -1, '제목에 생일 없음');
});
t('생일 알림: 같은 날 두 번 돌려도 중복 발송 안 함', function () {
  var before = __MAILS.length;
  checkDoctorBirthdaysDaily();
  eq(__MAILS.length, before, '중복 발송됨');
});
t('생일 알림: 트리거 설치/해제', function () {
  var st = installBirthdayTrigger(TOKEN);
  ok(st.installed, '설치 실패');
  eq(ScriptApp.getProjectTriggers().length, 1);
  var removed = removeBirthdayTrigger(TOKEN);
  eq(removed.removed, 1);
  ok(!getBirthdayTriggerStatus(TOKEN).installed, '해제 실패');
});
t('생일 알림: STAFF는 트리거 설치 불가', function () {
  throwsMatch(function () { installBirthdayTrigger(STAFF_TOKEN); }, '마스터');
});
t('사용자 이메일 저장: 형식 검사', function () {
  throwsMatch(function () { saveUserEmail('choi', 'not-an-email', TOKEN); }, '이메일');
});
t('사용자 이메일 저장: 정상 반영', function () {
  var res = saveUserEmail('choi', 'new@example.com', TOKEN);
  var u = res.users.filter(function (x) { return x.아이디 === 'choi'; })[0];
  eq(u.이메일, 'new@example.com');
});
t('사용자 목록: 이메일 필드 포함', function () {
  var res = getUsersList(TOKEN);
  ok('이메일' in res.users[0], '이메일 필드 없음');
});

// ------------------------------------------------------------------ 9. v1.4 상태 진단
t('진단: 시트별 적재 건수', function () {
  var st = getV14Status(TOKEN);
  ok(st.rows['타사단가표'] > 0, '단가표 없음');
  ok(st.rows['성분사전'] > 0, '성분사전 없음');
  ok(st.rows['진료과성분'] > 0, '진료과성분 없음');
});

// ------------------------------------------------------------------ 결과
var PASSED = RESULTS.filter(function (r) { return r.ok; }).length;
var FAILED = RESULTS.length - PASSED;
__TEST_RESULT__ = JSON.stringify({ passed: PASSED, failed: FAILED, cases: RESULTS });
