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

// ------------------------------------------------------------------ 5. 진료과 가이드 · 추천 (v1.5 경구제 전용)
function oralProductsFor_(key) {
  return readProductRows_().filter(function (p) {
    if (p.표 !== '경구') return false;
    return p.성분키 === key || String(p.성분키 || '').split('+').indexOf(key) !== -1;
  });
}
t('가이드: 치과 — 케이스별 성분·처방포인트', function () {
  var res = getDeptGuide('치과', TOKEN);
  ok(res.items.length >= 15, '치과 성분이 부족: ' + res.items.length);
  var groups = {};
  res.items.forEach(function (i) { groups[i.질환군] = 1; });
  ok(Object.keys(groups).length >= 6, '치과 케이스가 부족: ' + Object.keys(groups).length);
  ok(res.items.every(function (i) { return i.처방포인트; }), '처방포인트 없는 행 있음');
  ok(res.items.every(function (i) { return (i.우리제품 || []).every(function (p) { return p.표 === '경구'; }); }), '치과에 주사제 섞임');
  ok(res.items.some(function (i) { return i.영문키 === 'amoxicillin'; }), '아목시실린 없음');
});

t('가이드: 진료과 목록', function () {
  var res = getDeptGuide('', TOKEN);
  ok(res.depts.length >= 8, '진료과가 너무 적음');
  ok(typeof res.depts[0].진료과 === 'string' && res.depts[0].진료과.length > 0, '형식 오류');
  eq(res.form, '경구', '가이드 제형 표시 오류');
});
t('가이드: 내과 성분 + 우리 제품 매칭', function () {
  var res = getDeptGuide('내과', TOKEN);
  ok(res.items.length >= 10, '성분 수 부족');
  ok(res.items.some(function (i) { return i.우리제품 && i.우리제품.length > 0; }), '우리 제품 매칭 없음');
  ok(res.stats && res.stats.경구품목 > 0 && res.stats.주사품목 > 0, '제형 통계 없음');
});
t('가이드: 경구제 전용 — 주사·수액이 섞이지 않음', function () {
  var res = getDeptGuide('내과', TOKEN);
  var mixed = [];
  res.items.forEach(function (i) {
    (i.우리제품 || []).forEach(function (p) { if (p.표 !== '경구') mixed.push(p.품목명); });
  });
  ok(!mixed.length, '가이드에 주사·수액이 섞임: ' + mixed.slice(0, 3).join(', '));
  res.items.forEach(function (i) {
    ok(i.우리제품.length === Math.min(i.경구제수, 5), '경구제수 불일치');
    ok(typeof i.주사제수 === 'number', '주사제수 없음');
  });
});
t('가이드: 경구제가 없는 성분은 주사제수만 남음', function () {
  var res = getDeptGuide('이비인후과', TOKEN);
  var onlyInj = res.items.filter(function (i) { return i.경구제수 === 0 && i.주사제수 > 0; });
  ok(onlyInj.length > 0, '주사제만 있는 성분이 없음');
  ok(onlyInj.every(function (i) { return (i.우리제품 || []).length === 0; }), '경구제 없는데 제품이 있음');
});
t('추천: 최고요율 모드는 경구제 성분별 최고 수수료율', function () {
  var keys = ['amlodipine', 'rosuvastatin'].concat(
    readProductRows_().filter(function (p) { return p.표 === '경구' && p.성분키; })
      .map(function (p) { return p.성분키; }).filter(function (k, i, a) { return a.indexOf(k) === i; }).slice(0, 4));
  var res = recommendRegimen({ mode: 'maxrate', ingredients: keys }, TOKEN);
  eq(res.form, '경구', '추천 제형 표시 오류');
  ok(res.picks.length > 0, '추천 없음');
  keys.forEach(function (k) {
    var all = oralProductsFor_(k);
    if (!all.length) return;
    var best = Math.max.apply(null, all.map(function (p) { return Number(p.수수료율) || 0; }));
    var pick = res.picks.filter(function (x) { return x.성분키 === k; })[0];
    ok(pick, k + ' 추천 누락');
    eq(pick.수수료율, best, k + ' 최고요율 아님');
  });
});
t('추천: 경구제 전용 — 주사·수액이 섞이지 않음', function () {
  var keys = readProductRows_().filter(function (p) { return p.성분키; })
    .map(function (p) { return p.성분키; })
    .filter(function (k, i, a) { return a.indexOf(k) === i; }).slice(0, 10);
  ['maxrate', 'minmaker', 'perIngredient'].forEach(function (mode) {
    var res = recommendRegimen({ mode: mode, ingredients: keys }, TOKEN);
    res.picks.forEach(function (x) { eq(x.표, '경구', mode + ' 추천에 주사·수액 섞임: ' + x.품목명); });
  });
});
t('추천: 최소 제약사 상한을 사용자가 정함(1~10)', function () {
  var keys = readProductRows_().filter(function (p) { return p.표 === '경구' && p.성분키; })
    .map(function (p) { return p.성분키; })
    .filter(function (k, i, a) { return a.indexOf(k) === i; }).slice(0, 8);
  [1, 2, 3, 5].forEach(function (n) {
    var res = recommendRegimen({ mode: 'minmaker', ingredients: keys, maxMakers: n }, TOKEN);
    ok(res.summary.제약사수 <= n, n + '개 상한 초과: ' + res.summary.제약사수);
    eq(res.maxMakers, n, 'maxMakers 응답 오류');
    ok(res.summary.미포함성분 >= 0, '미포함성분 없음');
  });
  eq(recommendRegimen({ mode: 'minmaker', ingredients: keys, maxMakers: 1 }, TOKEN).summary.제약사수, 1, '1개 상한 오류');
});

t('추천: 최소 제약사 모드는 제약사 수를 줄임', function () {
  var keys = readProductRows_().filter(function (p) { return p.표 === '경구' && p.성분키; }).slice(0, 40)
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

// ------------------------------------------- 4-c. 최소 제약사 — 상한 안에서 요율 최대화 (v1.5.1)
/** 제보 사례 재현용 가짜 성분군 — 한국휴텍스제약(주) 1곳이 12개 성분을 다 덮지만 요율이 낮음 */
function minMakerCase_() {
  var spec = [
    ['amlodipine', '암로디핀', 50, [['한미약품', 55]]],
    ['losartan', '로사르탄', 50, [['한미약품', 60]]],
    ['telmisartan', '텔미사르탄', 50, []],
    ['rosuvastatin', '로수바스타틴', 50, [['아주약품', 55]]],
    ['atorvastatin', '아토르바스타틴', 50, []],
    ['ezetimibe', '에제티미브', 50, []],
    ['metformin', '메트포르민', 45, [['종근당', 50]]],
    ['gliclazide', '글리클라지드', 40, []],
    ['sitagliptin', '시타글립틴', 30, [['종근당', 45]]],
    ['empagliflozin', '엠파글리플로진', 40, []],
    ['dapagliflozin', '다파글리플로진', 45, []],
    ['rabeprazole', '라베프라졸', 45, [['대웅제약', 55]]]
  ];
  return spec.map(function (row, i) {
    var list = [{
      표: '경구', 품목명: '휴텍스' + row[1] + '정', 보험코드: 'H' + i, 성분키: row[0],
      제약사: '한국휴텍스제약(주)', 약가: 500, 수수료율: row[2], 규격: ''
    }];
    (row[3] || []).forEach(function (x, j) {
      list.push({
        표: '경구', 품목명: x[0] + row[1] + '정', 보험코드: 'X' + i + '-' + j, 성분키: row[0],
        제약사: x[0], 약가: 700, 수수료율: x[1], 규격: ''
      });
    });
    return { key: row[0], 성분한글: row[1], list: list };
  });
}
function minMakerRate_(picks) {
  var sum = 0;
  picks.forEach(function (x) { sum += Number(x.수수료율) || 0; });
  return picks.length ? sum / picks.length : 0;
}
function minMakerNames_(picks) {
  var m = {};
  picks.forEach(function (x) { m[x.제약사] = 1; });
  return Object.keys(m);
}

t('최소 제약사: 상한 5곳이 상한 1곳보다 높은 요율 제약사를 써서 평균 요율을 올림', function () {
  var groups = minMakerCase_();
  var one = recommendMinMakers_(groups, 1);
  var five = recommendMinMakers_(groups, 5);
  eq(one.length, 12, '상한 1곳이 12성분을 다 덮지 못함: ' + one.length);
  eq(five.length, 12, '상한 5곳에서 성분을 다 덮어야 함: ' + five.length);
  ok(minMakerRate_(five) > minMakerRate_(one) + 1,
    '상한 5곳 평균 요율이 오르지 않음: ' + minMakerRate_(five).toFixed(1) + '% vs ' + minMakerRate_(one).toFixed(1) + '%');
  var names = minMakerNames_(five);
  ok(names.length <= 5, '제약사 상한 초과: ' + names.length);
  ok(names.length > 1, '제약사가 1곳에 머묾: ' + names.join(','));
  var byKey = {};
  five.forEach(function (x) { byKey[x.성분키] = x; });
  eq(byKey['losartan'].수수료율, 60, '로사르탄 60% 품목 미적용');
  eq(byKey['losartan'].제약사, '한미약품', '로사르탄 제약사 오류');
  eq(byKey['sitagliptin'].수수료율, 45, '시타글립틴 45% 품목 미적용');
  ['telmisartan', 'atorvastatin', 'ezetimibe', 'gliclazide', 'empagliflozin', 'dapagliflozin'].forEach(function (k) {
    eq(byKey[k].제약사, '한국휴텍스제약(주)', k + ' 커버 제약사가 빠짐');
  });
});

t('최소 제약사: 요율이 같으면 상한이 남아도 제약사를 늘리지 않음', function () {
  var groups = [
    { key: 'a', 성분한글: 'A성분', list: [
      { 표: '경구', 품목명: '가정', 보험코드: 'A1', 성분키: 'a', 제약사: '가제약', 약가: 500, 수수료율: 50, 규격: '' },
      { 표: '경구', 품목명: '나정', 보험코드: 'A2', 성분키: 'a', 제약사: '나제약', 약가: 500, 수수료율: 50, 규격: '' }] },
    { key: 'b', 성분한글: 'B성분', list: [
      { 표: '경구', 품목명: '가정2', 보험코드: 'B1', 성분키: 'b', 제약사: '가제약', 약가: 400, 수수료율: 40, 규격: '' },
      { 표: '경구', 품목명: '나정2', 보험코드: 'B2', 성분키: 'b', 제약사: '나제약', 약가: 400, 수수료율: 40, 규격: '' }] }
  ];
  var res = recommendMinMakers_(groups, 5);
  eq(res.length, 2, '성분 수 오류');
  eq(minMakerNames_(res).length, 1, '요율이 같은데 제약사를 늘림: ' + minMakerNames_(res).join(','));
});

t('최소 제약사: 상한 1~10 어디서도 상한을 넘지 않고, 상한을 올리면 요율은 내려가지 않음', function () {
  var groups = minMakerCase_();
  var prev = -1;
  [1, 2, 3, 4, 5, 10].forEach(function (cap) {
    var res = recommendMinMakers_(groups, cap);
    ok(minMakerNames_(res).length <= cap, cap + '곳 상한 초과: ' + minMakerNames_(res).length);
    eq(JSON.stringify(recommendMinMakers_(groups, cap)), JSON.stringify(res), cap + '곳 결과가 매번 달라짐');
    var avg = minMakerRate_(res);
    ok(avg >= prev - 0.001, cap + '곳 평균 요율이 이전 상한보다 낮아짐');
    prev = avg;
  });
});

t('최소 제약사: 상한 안에서 요율보다 커버리지를 먼저 채움', function () {
  function g(key, name, list) { return { key: key, 성분한글: name, list: list }; }
  function p(maker, name, code, rate, key) {
    return { 표: '경구', 품목명: name, 보험코드: code, 성분키: key, 제약사: maker, 약가: 500, 수수료율: rate, 규격: '' };
  }
  var groups = [
    g('a', 'A성분', [p('가제약', '가A정', 'A1', 70, 'a'), p('나제약', '나A정', 'A2', 20, 'a')]),
    g('b', 'B성분', [p('가제약', '가B정', 'B1', 70, 'b'), p('나제약', '나B정', 'B2', 20, 'b')]),
    g('c', 'C성분', [p('나제약', '나C정', 'C2', 20, 'c')]),
    g('d', 'D성분', [p('나제약', '나D정', 'D2', 20, 'd')])
  ];
  var one = recommendMinMakers_(groups, 1);
  eq(one.length, 4, '상한 1곳에서 커버리지를 먼저 채우지 않음: ' + one.length);
  eq(minMakerNames_(one)[0], '나제약', '커버리지 우선 위반: ' + minMakerNames_(one).join(','));
  var two = recommendMinMakers_(groups, 2);
  eq(two.length, 4, '상한 2곳 커버리지 오류: ' + two.length);
  ok(minMakerRate_(two) > minMakerRate_(one), '상한 2곳에서 요율이 오르지 않음');
  var byKey = {};
  two.forEach(function (x) { byKey[x.성분키] = x; });
  eq(byKey['a'].제약사, '가제약', 'A성분 고요율 제약사 미적용');
  eq(byKey['c'].제약사, '나제약', 'C성분 커버 제약사가 빠짐');
});

t('최소 제약사(실데이터): 상한 5곳이 상한 1곳보다 평균 요율이 높고 제약사 수는 5 이하', function () {
  var keys = readProductRows_().filter(function (p) { return p.표 === '경구' && p.성분키; })
    .map(function (p) { return p.성분키; })
    .filter(function (k, i, a) { return a.indexOf(k) === i; });
  var r1 = recommendRegimen({ mode: 'minmaker', ingredients: keys, maxMakers: 1 }, TOKEN);
  var r5 = recommendRegimen({ mode: 'minmaker', ingredients: keys, maxMakers: 5 }, TOKEN);
  eq(r1.summary.제약사수, 1, '상한 1곳인데 제약사가 ' + r1.summary.제약사수 + '곳');
  ok(r5.summary.제약사수 <= 5, '제약사 상한 초과: ' + r5.summary.제약사수);
  ok(r5.summary.제약사수 > 1, '상한 5곳인데 1곳에 머묾');
  ok(r5.summary.추천품목수 >= r1.summary.추천품목수, '상한 5곳 커버리지가 더 적음');
  ok(r5.summary.평균수수료율 > r1.summary.평균수수료율,
    '상한 5곳 평균 요율이 오르지 않음: ' + r5.summary.평균수수료율 + '% vs ' + r1.summary.평균수수료율 + '%');
  eq(r5.summary.상한1평균수수료율, r1.summary.평균수수료율, '상한 1곳 비교값 오류');
  ok(r5.summary.요율향상 > 0, '요율향상 값이 없음: ' + r5.summary.요율향상);
  ok(r5.summary.수수료액합계 > 0, '수수료액 합계가 없음');
  var oneBy = {};
  r1.picks.forEach(function (x) { oneBy[x.성분키] = x; });
  var better = r5.picks.filter(function (x) {
    return oneBy[x.성분키] && (Number(x.수수료율) || 0) > (Number(oneBy[x.성분키].수수료율) || 0);
  });
  ok(better.length > 0, '타 제약사 높은 요율 품목이 하나도 반영되지 않음');
  ok(better.every(function (x) { return x.제약사 && oneBy[x.성분키].제약사 !== x.제약사; }), '같은 제약사에서 요율이 올랐다고 표시됨');
  eq(r5.summary.미포함성분, Math.max(0, keys.length - r5.picks.length), '미포함성분 계산 오류');
  ok(r5.summary.서로다른품목수 > 0 && r5.summary.서로다른품목수 <= r5.summary.추천품목수,
    '서로 다른 품목 수 계산 오류: ' + r5.summary.서로다른품목수);
});

// ------------------------------------------------------------------ 5-b. 제형 구분 · 주사제 셋팅
t('제형: …주/수액은 주사·수액, …정/캡슐은 경구', function () {
  ok(looksParenteral_('프리브로펜주208ml(백)'), '주 이름 미탐지');
  ok(looksParenteral_('리쥬비엘주'), '주 이름 미탐지 2');
  ok(looksParenteral_('포도당수액 500ml'), '수액 미탐지');
  ok(!looksParenteral_('베아셋정'), '정 이름 오탐');
  ok(!looksParenteral_('에바원정30mg'), '정 이름 오탐 2');
  eq(dosageFormOf_({ 표: '경구', 품목명: '베아셋정' }), '경구');
  eq(dosageFormOf_({ 표: '경구', 품목명: '메가주100ml' }), '주사·수액');
  eq(dosageFormOf_({ 표: '주사·수액', 품목명: '코러스세프트리악손나트륨주/1g' }), '주사·수액');
});
t('제형: 경구 목록에는 주사·수액 품목이 없음', function () {
  var all = readProductRows_();
  var oral = productsOfForm_(all, '경구');
  var inj = productsOfForm_(all, '주사·수액');
  ok(oral.length > 0 && inj.length > 0, '제형별 목록 없음');
  ok(oral.every(function (p) { return p.표 === '경구' && !looksParenteral_(p.품목명); }), '경구 목록에 주사 이름');
  ok(oral.length + inj.length === all.length, '제형 분류 누락');
});
t('주사 셋팅: 목록·카테고리·통계', function () {
  var res = getInjectGuide({}, TOKEN);
  eq(res.form, '주사·수액', '제형 표시 오류');
  ok(res.stats.전체 > 100, '주사 품목이 너무 적음: ' + res.stats.전체);
  ok(res.stats.급여 > 0 && res.stats.비급여 > 0, '급여/비급여 통계 없음');
  ok(res.categories.length >= 5, '카테고리가 너무 적음');
  ok(res.items.length > 0, '성분별 목록 없음');
  ok(res.picks.length > 0, '추천 없음');
  var sum = res.categories.reduce(function (a, c) { return a + c.개수; }, 0);
  eq(sum, res.stats.전체, '카테고리 합계 불일치');
});
t('주사 셋팅: 경구제는 들지 않음', function () {
  var res = getInjectGuide({}, TOKEN);
  res.picks.forEach(function (x) { ok(x.표 !== '경구', '경구제가 섞임: ' + x.품목명); });
  res.items.forEach(function (g) { g.제품.forEach(function (p) { ok(p.표 !== '경구', '경구제가 섞임'); }); });
});
t('주사 셋팅: 급여 필터', function () {
  var res = getInjectGuide({ 급여구분: '급여', limit: 30 }, TOKEN);
  ok(res.picks.length > 0, '추천 없음');
  ok(res.picks.every(function (x) { return x.급여구분 === '급여'; }), '급여 필터 안 됨');
  ok(res.summary.비급여수 === 0, '비급여 섞임');
});
t('주사 셋팅: 비급여 필터', function () {
  var res = getInjectGuide({ 급여구분: '비급여', limit: 30 }, TOKEN);
  ok(res.picks.length > 0, '추천 없음');
  ok(res.picks.every(function (x) { return x.급여구분 === '비급여'; }), '비급여 필터 안 됨');
});
t('주사 셋팅: 요율 최우선(maxrate) — 성분별 1품목·성분 중복 없음', function () {
  var res = getInjectGuide({ mode: 'maxrate', limit: 50 }, TOKEN);
  var seen = {};
  res.picks.forEach(function (x) {
    var k = x.성분키 || x.품목명;
    ok(!seen[k], '같은 성분 중복: ' + k);
    seen[k] = 1;
  });
  var inj = productsOfForm_(readProductRows_(), '주사·수액');
  res.picks.slice(0, 10).forEach(function (x) {
    var same = inj.filter(function (p) { return (p.성분키 || p.품목명) === (x.성분키 || x.품목명); });
    if (!same.length) return;
    var best = Math.max.apply(null, same.map(function (p) { return Number(p.수수료율) || 0; }));
    eq(x.수수료율, best, x.품목명 + ' 최고요율 아님');
  });
});
t('주사 셋팅: 수수료액 우선(margin) — 수수료액 내림차순', function () {
  var res = getInjectGuide({ mode: 'margin', limit: 20 }, TOKEN);
  ok(res.picks.length > 0, '추천 없음');
  for (var i = 1; i < res.picks.length; i++) {
    if (res.picks[i].수수료액 > res.picks[i - 1].수수료액) {
      throw new Error('수수료액 정렬 오류: ' + res.picks[i - 1].수수료액 + ' → ' + res.picks[i].수수료액);
    }
  }
  var top = res.picks[0];
  near(top.수수료액, top.약가 * top.수수료율 / 100, 0.05, '수수료액 계산 오류');
});
t('주사 셋팅: 카테고리 균형(category) — 카테고리 중복 없음', function () {
  var res = getInjectGuide({ mode: 'category', limit: 100 }, TOKEN);
  ok(res.picks.length > 0, '추천 없음');
  var seen = {};
  res.picks.forEach(function (x) {
    ok(!seen[x.카테고리], '카테고리 중복: ' + x.카테고리);
    seen[x.카테고리] = 1;
  });
  eq(res.picks.length, Math.min(res.summary.후보수, res.categories.length) === res.categories.length ? res.categories.length : res.picks.length);
});
t('주사 셋팅: 카테고리 필터 · 검색어', function () {
  var all = getInjectGuide({}, TOKEN);
  var cat = all.categories[0].카테고리;
  var res = getInjectGuide({ 카테고리: cat, limit: 30 }, TOKEN);
  ok(res.picks.length > 0, '카테고리 추천 없음: ' + cat);
  ok(res.picks.every(function (x) { return x.카테고리 === cat; }), '카테고리 필터 안 됨');
  res.categories.forEach(function (c) { ok(c.카테고리 === cat || c.개수 > 0, '카테고리 합계 이상'); });

  var q = getInjectGuide({ q: '세프트리악손' }, TOKEN);
  ok(q.summary.후보수 > 0, '검색 결과 없음');
  ok(q.items.some(function (g) { return g.제품.some(function (p) { return p.품목명.indexOf('세프트리악손') !== -1; }); }), '세프트리악손 미검색');
});
t('주사 셋팅: limit 적용 · 빈 결과', function () {
  var res = getInjectGuide({ limit: 5 }, TOKEN);
  ok(res.picks.length <= 5, 'limit 미적용');
  var none = getInjectGuide({ q: '없는제품명zzz' }, TOKEN);
  eq(none.summary.후보수, 0);
  eq(none.picks.length, 0);
});
t('주사 셋팅: 권한 없는 토큰 거부', function () {
  throwsMatch(function () { getInjectGuide({}, 'bad-token'); }, '로그인');
});

// ------------------------------------------------------------------ 5-d. 주사 프로토콜 · 배합금기 · 급여가이드
t('프로토콜: 목록·카테고리·케이스', function () {
  var res = getInjectProtocols('', TOKEN);
  ok(res.cautions.length >= 10, '배합주의가 너무 적음: ' + res.cautions.length);
  ok(res.protocols.length >= 20, '프로토콜이 너무 적음: ' + res.protocols.length);
  ok(res.cards.length >= 10, '제품 카드가 너무 적음: ' + res.cards.length);
  ok(res.categories.length >= 5, '분류가 너무 적음');
  ok(res.protocols[0].기대효과 || res.protocols[0].수액, '프로토콜 내용 없음');
});
t('프로토콜: 배합금기 규칙(NAC·글루타치온)', function () {
  var res = getInjectProtocols('', TOKEN);
  var nac = res.rules.filter(function (r) { return r.keys.indexOf('acetylcysteine') !== -1; })[0];
  ok(nac, 'NAC 규칙 없음');
  ok(nac.with.indexOf('acetaminophen') !== -1, 'NAC+아세트아미노펜 상대성분 없음');
  ok(nac.중요, 'NAC 규칙 중요 표시 없음');
  var gsh = res.rules.filter(function (r) { return r.keys.indexOf('glutathione') !== -1 && r.with.length; })[0];
  ok(gsh, '글루타치온 배합금기 규칙 없음');
  ok(gsh.with.some(function (k) { return /selenium|trace|amino/.test(k); }), '글루타치온 상대성분 이상: ' + gsh.with.join(','));
});
t('프로토콜: 참고제품은 예시로만, 우리 제품은 성분 매칭', function () {
  var res = getInjectProtocols('글루타치온', TOKEN);
  ok(res.protocols.length > 0, '글루타치온 프로토콜 없음');
  var hit = res.protocols.filter(function (p) { return p.우리제품 && p.우리제품.length; })[0];
  ok(hit, '글루타치온 성분 매칭 제품 없음');
  ok(hit.우리제품[0].보험코드 && hit.우리제품[0].품목명, '제품 필드 없음');
  ok(hit.참고제품.indexOf('참고') !== -1, '참고제품 표기 없음');
});
t('프로토콜: 검색어 필터', function () {
  var res = getInjectProtocols('신데렐라', TOKEN);
  ok(res.protocols.length > 0, '신데렐라 프로토콜 없음');
  res.protocols.forEach(function (p) { ok(p.케이스.indexOf('신데렐라') !== -1, '검색 필터 안 됨'); });
  var none = getInjectProtocols('없는케이스zzz', TOKEN);
  eq(none.protocols.length + none.cautions.length + none.cards.length, 0);
});
t('프로토콜: 권한 없는 토큰 거부', function () {
  throwsMatch(function () { getInjectProtocols('', 'bad-token'); }, '로그인');
});
t('급여가이드: 분류·항목·근거', function () {
  var res = getCoverageNotes('', TOKEN);
  ok(res.categories.length >= 6, '급여가이드 분류가 적음: ' + res.categories.length);
  ok(res.items.length >= 20, '급여가이드 항목이 적음');
  ok(res.items.every(function (x) { return x.근거; }), '근거 없는 항목 있음');
  var dm = getCoverageNotes('당뇨병용제', TOKEN);
  ok(dm.items.length >= 6, '당뇨 항목 부족');
  ok(dm.items.every(function (x) { return x.구분 === '당뇨병용제'; }), '분류 필터 안 됨');
  ok(dm.items.some(function (x) { return x.내용.indexOf('HbA1c') !== -1; }), '당뇨 내용 없음');
});
t('급여가이드: 권한 없는 토큰 거부', function () {
  throwsMatch(function () { getCoverageNotes('', 'bad-token'); }, '로그인');
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

// ------------------------------------------------------------------ 6-b. 제형 접미사 제거 · 유사 이름 정밀도 (v1.5.1)
t('어간: 제형·단위를 떼고 핵심 글자만', function () {
  eq(nameStem_('안티옥시주사'), '안티옥시');
  eq(nameStem_('코러스세프트리악손나트륨주/1g'), '코러스세프트리악손나트륨');
  eq(nameStem_('아주/아이델라주/5ml/10V'), '아이델라');
  eq(nameStem_('아모잘탄엑스큐정5/100/10/10mg'), '아모잘탄엑스큐');
  eq(nameStem_('치옥트산(알파리포산)'), '치옥트산');
});
t('유사이름: 안티옥시주사 — "주"만 겹치는 항생제는 제외', function () {
  var res = searchProductsV14('안티옥시주사', {}, TOKEN);
  eq(res.total, 0);
  eq(res.similar.length, 0, '엉뚱한 유사 제품: ' + res.similar.map(function (s) { return s.name; }).join(', '));
});
t('유사이름: 어간이 겹치지 않으면 후보 아님(직접 확인)', function () {
  var prods = [
    { 품목명: '코러스세프트리악손나트륨주/1g', 보험코드: '647202372', 표: '주사·수액' },
    { 품목명: '삼성레보플록사신주/100ml', 보험코드: '645100110', 표: '주사·수액' },
    { 품목명: '안티옥시주', 보험코드: '670607021', 표: '주사·수액' }
  ];
  var hits = similarNameHits_('안티옥시주사', prods, 8);
  eq(hits.length, 1, '안티옥시주만 남아야 함: ' + hits.map(function (h) { return h.name; }).join(', '));
  eq(hits[0].name, '안티옥시주');
});
t('유사이름: 정상 오타·초성 검색은 유지', function () {
  ok(similarNameHits_('세프트락손', readProductRows_(), 8).length > 0, '오타 추천 사라짐');
  ok(similarNameHits_('ㅅㅍㅌㄹㅇㅅ', readProductRows_(), 8).length > 0, '초성 추천 사라짐');
});

// ------------------------------------------------------------------ 6-c. 약 검색 자동 연동 (약학정보원 + 우리 제품·프로토콜)
t('자동연동: 안티옥시주사 → 성분 티옥트산 · 치옥트산 프로토콜', function () {
  var res = drugAutoLink('안티옥시주사', {}, TOKEN);
  eq(res.query, '안티옥시주사');
  ok(res.kpic.items.length >= 1, '약학정보원 결과 없음: ' + (res.kpic.error || ''));
  eq(res.kpic.items[0].name, '안티옥시주사');
  ok(res.성분.length >= 1, '성분 묶음 없음');
  var g = res.성분[0];
  eq(g.key, 'thioctic acid');
  eq(g.성분한글, '티옥트산');
  ok(g.표기.some(function (m) { return m.indexOf('치옥트산') !== -1; }), '치옥트산 동의어 없음: ' + g.표기.join('|'));
  ok(g.프로토콜.length >= 1, '관련 수액 프로토콜 없음');
  ok(g.프로토콜.some(function (r) { return r.성분.indexOf('치옥트산') !== -1; }), '치옥트산 프로토콜 없음');
  ok(g.금기 && g.금기.임부 !== undefined, '금기 요약 없음');
});
t('자동연동: 시트 프로토콜만으로도 안티옥시주를 찾음', function () {
  var res = drugAutoLink('안티옥시주', {}, TOKEN);
  ok(res.프로토콜.length >= 1, '주사프로토콜 시트에서 못 찾음');
  ok(res.프로토콜.some(function (r) { return r.참고제품.indexOf('안티옥시') !== -1; }), '참고제품 매칭 없음');
});
t('자동연동: 권한 없는 토큰 거부', function () {
  throwsMatch(function () { drugAutoLink('안티옥시주사', {}, 'bad-token'); }, '로그인');
});
t('연동 점검: 약학정보원 연결 상태', function () {
  var res = kpicHealth(TOKEN);
  ok(res.ok, '연결 실패: ' + (res.error || ''));
  ok(res.items >= 0, '응답 형식 오류');
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

// ------------------------------------------------------------------ 10. 요율 등급 3단계 차등 (v1.6)
function prodByCode_(list, code) {
  return list.filter(function (x) { return String(x.보험코드) === String(code); })[0] || null;
}
function rateMapFrom_(list) {
  var map = {};
  (list || []).forEach(function (x) { map[String(x.보험코드 || '')] = Number(x.수수료율) || 0; });
  return map;
}

// 테스트 순서를 위해 현재 등급을 바꾸는 헬퍼 (MASTER 토큰 사용)
function setTier_(id, tier) {
  var res = updateUserTier(id, tier, TOKEN);
  ok(res && res.success, '등급 변경 실패: ' + (res && res.message));
  return res;
}

t('요율등급: MASTER 는 원본 요율 그대로', function () {
  var raw = getProductsRaw_();
  var mine = getProducts(TOKEN);
  eq(raw.length, mine.length);
  var diff = raw.filter(function (p, i) { return Number(mine[i].수수료율) !== Number(p.수수료율); });
  eq(diff.length, 0, 'MASTER 요율이 원본과 다름');
});

t('요율등급: STAFF 기본 2단계 = 원본 -2%p', function () {
  setTier_('choi', '2단계');
  var raw = getProductsRaw_();
  var staff = getProducts(STAFF_TOKEN);
  eq(raw.length, staff.length);
  var bad = [];
  raw.forEach(function (p, i) {
    var want = Math.max(0, Number(p.수수료율) - 2);
    if (Number(staff[i].수수료율) !== want) bad.push(p.제품명 + ':' + staff[i].수수료율 + '≠' + want);
  });
  eq(bad.length, 0, '2단계 차감 오류 ' + bad.slice(0, 3).join(', '));
});

t('요율등급: 1단계(-1%p) · 3단계(-3%p) 즉시 반영', function () {
  var raw = getProductsRaw_();
  [['1단계', 1], ['3단계', 3]].forEach(function (pair) {
    setTier_('choi', pair[0]);
    var staff = login('choi', 'test');
    var mine = getProducts(staff.token);
    var p = prodByCode_(raw, '647202372') || raw[0];
    var got = prodByCode_(mine, p.보험코드);
    eq(got.수수료율, Math.max(0, Number(p.수수료율) - pair[1]), pair[0] + ' 차감 오류');
  });
  setTier_('choi', '2단계');
});

t('요율등급: 요율이 차감보다 낮으면 0% 로 막힘', function () {
  var pm = __SHEETS['제품마스터'], head = pm[0];
  var row = head.map(function () { return ''; });
  row[head.indexOf('보험코드')] = 'TESTLOW001';
  row[head.indexOf('제품명')] = '테스트저요율주';
  row[head.indexOf('규격')] = '1mL';
  row[head.indexOf('기준단가')] = 1000;
  row[head.indexOf('수수료율')] = 1;
  row[head.indexOf('급여구분')] = '급여';
  pm.push(row);
  try {
    setTier_('choi', '3단계');
    var got = prodByCode_(getProducts(STAFF_TOKEN), 'TESTLOW001');
    ok(got, '테스트 제품이 STAFF 목록에 없음');
    eq(got.수수료율, 0, '0% 하한 미적용');
    eq(prodByCode_(getProducts(TOKEN), 'TESTLOW001').수수료율, 1, 'MASTER 원본 훼손');
  } finally {
    pm.pop();
    setTier_('choi', '2단계');
  }
});

t('요율등급: STAFF 응답에 등급·차감률·원본요율 없음', function () {
  setTier_('choi', '2단계');
  var lg = login('choi', 'test');
  ok(!('요율등급' in lg.user), 'login.user 에 요율등급');
  var boot = getBootstrapData(lg.token);
  ok(!('요율등급' in boot.user), 'bootstrap.user 에 요율등급');
  ok(JSON.stringify(boot).indexOf('요율등급') === -1, '부트스트랩 응답 어딘가에 요율등급');
  ok(JSON.stringify(boot).indexOf('차감') === -1, '부트스트랩 응답에 차감 안내');
  eq(Object.keys(boot.user).sort().join(','), '권한,담당자명,아이디', 'bootstrap.user 필드');
  var prods = getProducts(lg.token);
  ok(prods.every(function (p) { return !('요율등급' in p) && !('원본수수료율' in p) && !('차감' in p); }), '제품 응답에 등급 필드');
});

t('요율등급: 검색·주사·추천·자동연동 경로도 차감된 요율만', function () {
  setTier_('choi', '2단계');
  var st = login('choi', 'test').token;
  // (1) 이엘파마 검색
  var ms = searchElpharmaProducts('정', 20, TOKEN);
  var ss = searchElpharmaProducts('정', 20, st);
  var mMap = rateMapFrom_(ms.items);
  var bad = ss.items.filter(function (x) {
    return mMap[x.보험코드] !== undefined && Number(x.수수료율) !== Math.max(0, mMap[x.보험코드] - 2);
  });
  eq(bad.length, 0, '이엘파마 검색 요율 미차감');
  ok(JSON.stringify(ss).indexOf('요율등급') === -1, '검색 응답에 요율등급');
  // (2) 주사제 셋팅
  var mi = getInjectGuide({ limit: 10 }, TOKEN);
  var si = getInjectGuide({ limit: 10 }, st);
  var iMap = rateMapFrom_(mi.picks);
  var ibad = si.picks.filter(function (x) {
    return iMap[x.보험코드] !== undefined && Number(x.수수료율) !== Math.max(0, iMap[x.보험코드] - 2);
  });
  eq(ibad.length, 0, '주사 셋팅 요율 미차감');
  // (3) 처방 세팅 추천
  var keys = {};
  ms.items.forEach(function (x) { if (x.성분명) keys[ingredientKey_(x.성분명)] = 1; });
  var keyList = Object.keys(keys).filter(Boolean).slice(0, 3);
  if (keyList.length) {
    var mr = recommendRegimen({ mode: 'maxrate', ingredients: keyList }, TOKEN);
    var sr = recommendRegimen({ mode: 'maxrate', ingredients: keyList }, st);
    eq(mr.picks.length, sr.picks.length, '추천 품목 수가 다름');
    if (mr.picks.length) {
      near(sr.summary.평균수수료율, Math.max(0, mr.summary.평균수수료율 - 2), 0.11, '추천 평균 요율 미차감');
    }
  }
  // (4) 약 검색 자동연동
  var ma = drugAutoLink('안티옥시', {}, TOKEN);
  var sa = drugAutoLink('안티옥시', {}, st);
  var aMap = rateMapFrom_(ma.우리제품);
  var abad = sa.우리제품.filter(function (x) {
    return aMap[x.보험코드] !== undefined && Number(x.수수료율) !== Math.max(0, aMap[x.보험코드] - 2);
  });
  eq(abad.length, 0, '자동연동 요율 미차감');
});

t('요율등급: STAFF 는 사용자 목록(등급)을 볼 수 없음', function () {
  throwsMatch(function () { getUsersList(STAFF_TOKEN); }, '마스터');
  throwsMatch(function () { updateUserTier('jung', '1단계', STAFF_TOKEN); }, '마스터');
});

t('요율등급: MASTER 만 등급 변경 가능 · 잘못된 값은 거부', function () {
  var bad = updateUserTier('jung', '4단계', TOKEN);
  ok(!bad.success, '없는 등급이 통과됨');
  var master = updateUserTier('master', '1단계', TOKEN);
  ok(!master.success, 'MASTER 계정 등급이 바뀜');
  var noUser = updateUserTier('없는아이디', '1단계', TOKEN);
  ok(!noUser.success, '없는 계정 변경이 통과됨');
  var good = setTier_('jung', '1단계');
  eq(good.요율등급, '1단계');
  eq(findUserById_('jung').요율등급, '1단계');
  setTier_('jung', '2단계');
});

t('요율등급: MASTER 사용자 목록에 등급·차감 정보가 보임', function () {
  var res = getUsersList(TOKEN);
  ok(res.users.every(function (u) { return '요율등급' in u; }), '등급 필드 없음');
  var staff = res.users.filter(function (u) { return u.권한 === 'STAFF'; });
  ok(staff.length > 0, 'STAFF 없음');
  ok(staff.every(function (u) { return ['1단계', '2단계', '3단계'].indexOf(u.요율등급) !== -1; }), 'STAFF 등급 값 이상');
  ok(staff.every(function (u) { return u.요율차감 === { '1단계': 1, '2단계': 2, '3단계': 3 }[u.요율등급]; }), 'STAFF 차감률 불일치');
  var master = res.users.filter(function (u) { return u.권한 === 'MASTER'; })[0];
  eq(master.요율등급, '', 'MASTER 에 등급이 붙음');
  eq(master.요율차감, 0, 'MASTER 차감률');
  eq(res.tiers.length, 3, '등급 목록이 3개가 아님');
});

t('요율등급: 신규 가입 신청은 3단계 기본', function () {
  var reg = registerUser('newtier99', '1234', '신규사원');
  ok(reg.success, '가입 실패: ' + reg.message);
  eq(findUserById_('newtier99').요율등급, '3단계', '신규 가입 기본 등급');
  var row = getUsersList(TOKEN).users.filter(function (u) { return u.아이디 === 'newtier99'; })[0];
  eq(row.요율등급, '3단계');
  eq(row.사용여부, 'N');
  // 승인 후 로그인 → 요율은 원본-3%p
  toggleUserActive('newtier99', 'Y', TOKEN);
  var lg = login('newtier99', '1234');
  ok(lg.success, '승인 후 로그인 실패');
  var raw = getProductsRaw_();
  var mine = getProducts(lg.token);
  var p = prodByCode_(raw, '647202372') || raw[0];
  eq(prodByCode_(mine, p.보험코드).수수료율, Math.max(0, Number(p.수수료율) - 3), '신규 가입 3단계 차감 오류');
});

t('요율등급: 시트 등급이 비어 있으면 2단계로 계산', function () {
  var list = __SHEETS['사용자'], head = list[0];
  var idx = head.indexOf('요율등급');
  var row = list.filter(function (r) { return r[0] === 'jung'; })[0];
  var before = row[idx];
  row[idx] = '';
  try {
    var lg = login('jung', 'test');
    var raw = getProductsRaw_();
    var p = prodByCode_(raw, '647202372') || raw[0];
    eq(prodByCode_(getProducts(lg.token), p.보험코드).수수료율, Math.max(0, Number(p.수수료율) - 2), '빈 등급 기본값 오류');
  } finally {
    row[idx] = before;
  }
});

t('요율등급: 처방 저장은 원본 요율 · STAFF 조회는 차감', function () {
  var list = __SHEETS['거래처'], head = list[0];
  var iMgr = head.indexOf('담당자'), iCode = head.indexOf('거래처코드');
  var beforeMgr = list[1][iMgr];
  list[1][iMgr] = '최담당';
  var code = list[1][iCode];
  setTier_('choi', '2단계');
  var p = prodByCode_(getProductsRaw_(), '647202372') || getProductsRaw_()[0];
  try {
    var staffRate = Math.max(0, Number(p.수수료율) - 2);
    var save = savePrescriptions({
      기준월: currentMonth_(), 처방일: formatDate_(new Date()), 거래처코드: code,
      items: [{ 보험코드: p.보험코드, 품목명: p.제품명, 규격: p.규격, 약가: p.기준단가, 수량: 3, 수수료율: staffRate }]
    }, STAFF_TOKEN);
    ok(save.success, '처방 저장 실패');
    var sheetRow = getAllRowsAsObjects_('처방내역').filter(function (r) {
      return String(r['보험코드']) === String(p.보험코드) && String(r['기준월']) === currentMonth_();
    })[0];
    ok(sheetRow, '처방내역 행 없음');
    eq(sheetRow['수수료율'], p.수수료율, '시트에 원본 요율이 남지 않음');
    eq(sheetRow['예상수수료'], Math.round(sheetRow['처방금액'] * p.수수료율 / 100), '시트 예상수수료 불일치');
    var st = getPrescriptions(currentMonth_(), code, STAFF_TOKEN);
    var stRow = st.rows.filter(function (r) { return String(r.보험코드) === String(p.보험코드); })[0];
    eq(stRow.수수료율, staffRate, 'STAFF 조회 요율 미차감');
    eq(stRow.예상수수료, Math.round(stRow.처방금액 * staffRate / 100), 'STAFF 예상수수료 미차감');
    var ms = getPrescriptions(currentMonth_(), code, TOKEN);
    var msRow = ms.rows.filter(function (r) { return String(r.보험코드) === String(p.보험코드); })[0];
    eq(msRow.수수료율, p.수수료율, 'MASTER 조회 요율이 원본이 아님');
  } finally {
    list[1][iMgr] = beforeMgr;
  }
});

// ------------------------------------------------------------------ 결과
var PASSED = RESULTS.filter(function (r) { return r.ok; }).length;
var FAILED = RESULTS.length - PASSED;
__TEST_RESULT__ = JSON.stringify({ passed: PASSED, failed: FAILED, cases: RESULTS });
