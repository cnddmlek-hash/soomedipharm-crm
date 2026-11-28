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
t('제품 목록: 주사·수액 제약사 = 시트 실제 제조사 (자사(페이서) 아님)', function () {
  var inj = readProductRows_().filter(function (p) { return p.표 === '주사·수액'; });
  ok(inj.length >= 200, '주사·수액 품목이 부족함: ' + inj.length);
  var bad = inj.filter(function (p) { return !p.제약사 || p.제약사 === '자사(페이서)' || p.제약사 === '자사'; });
  ok(!bad.length, '제약사가 비었거나 자사(페이서)인 품목: ' +
    bad.slice(0, 5).map(function (p) { return p.품목명; }).join(', '));
  var makers = {};
  inj.forEach(function (p) { makers[p.제약사] = 1; });
  ok(Object.keys(makers).length >= 20, '제조사 종류가 너무 적음: ' + Object.keys(makers).length);
  var hit = inj.filter(function (p) { return p.보험코드 === '647202372'; })[0];
  ok(hit, '코러스세프트리악손나트륨주가 없음');
  eq(hit && hit.제약사, '한국코러스', '코러스세프트리악손나트륨주 제조사 오류');
  var bye = inj.filter(function (p) { return p.보험코드 === '690300461'; })[0];
  eq(bye && bye.제약사, '라이트팜텍', '본큐어주 제조사 오류');
});
t('제품 목록: 같은 성분 여러 제조사가 실제로 나뉨 (최소 제약사 모드 입력)', function () {
  var inj = productsOfForm_(readProductRows_(), '주사·수액');
  var byIng = {};
  inj.forEach(function (p) { if (p.성분키) (byIng[p.성분키] = byIng[p.성분키] || {})[p.제약사] = 1; });
  var multi = Object.keys(byIng).filter(function (k) { return Object.keys(byIng[k]).length > 1; });
  ok(multi.length >= 5, '같은 성분을 여러 제조사가 파는 성분이 ' + multi.length + '개뿐');
});
t('제품 목록: 제약사 값이 어디서도 자사(페이서)로 고정되지 않음', function () {
  var txt = readProductRows_().map(function (p) { return p.제약사; }).join('|');
  ok(txt.indexOf('자사(페이서)') === -1, '자사(페이서) 가 남아 있음');
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
t('주사 셋팅: 추천 품목·성분 목록에 실제 제조사(제약사)가 실림', function () {
  var res = getInjectGuide({ limit: 30 }, TOKEN);
  ok(res.picks.length > 0, '추천 없음');
  var bad = res.picks.filter(function (x) { return !x.제약사 || x.제약사 === '자사(페이서)'; });
  ok(!bad.length, '추천 품목에 제약사가 없음: ' + bad.slice(0, 3).map(function (x) { return x.품목명; }).join(', '));
  var itemBad = [];
  (res.items || []).forEach(function (g) {
    (g.제품 || []).forEach(function (x) { if (!x.제약사 || x.제약사 === '자사(페이서)') itemBad.push(x.품목명); });
  });
  ok(!itemBad.length, '성분 목록에 제약사가 없는 품목: ' + itemBad.slice(0, 3).join(', '));
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


// ------------------------------------------------------------------ 11. v1.7 — 거래처코드 Sxxx 채번
t('채번: S001 형식으로 이어짐 (3자리·999 초과는 S1000)', function () {
  eq(nextClientCode_([]), 'S001');
  eq(nextClientCode_(['S001', 'S009', 'S010']), 'S011');
  eq(nextClientCode_(['S999']), 'S1000');
  eq(nextClientCode_(['S1000', 'S002']), 'S1001');
});
t('채번: 옛 휴온스 코드·구 C코드는 건너뛰고 S 코드만 봄', function () {
  eq(nextClientCode_(['1095167', 'C0003', '9008881']), 'S001');
  eq(nextClientCode_(['1095167', 'S093']), 'S094');
});
t('거래처 저장: 신규 등록이 Sxxx 코드로 채번되고 시트에 남음', function () {
  var before = getClients(true, TOKEN).map(function (c) { return c.거래처코드; });
  var res = saveClient({ 거래처명: '테스트신규내과의원', 유통구분: '의원', 진료과: '내과' }, TOKEN);
  ok(res && res.success, '저장 실패');
  ok(/^S\d{3,}$/.test(res.code), 'Sxxx 형식이 아님: ' + res.code);
  eq(res.code, nextClientCode_(before), '채번이 기존 최대번호 다음이 아님');
  var saved = res.clients.filter(function (c) { return c.거래처코드 === res.code; })[0];
  ok(saved && saved.거래처명 === '테스트신규내과의원', '새 거래처가 목록에 없음');
});

// ------------------------------------------------------------------ 12. v1.7 — 심평원(HIRA) 비거래처 사전조회
function setHiraKey_(key) {
  saveSettings({ HIRA_API_KEY: key }, TOKEN);
  return String(getSettingsMap_()['HIRA_API_KEY'] || '');
}

t('HIRA 미설정: 안내·진료과 목록만 있고 먹통이 되지 않음', function () {
  setHiraKey_('');
  var r = getHiraPrevisitBriefing({ name: '테스트소아청소년과의원01' }, TOKEN);
  ok(r && r.configured === false, 'configured=false 여야 함');
  eq(r.mode, 'offline');
  ok(r.apiGuide && r.apiGuide.steps.length === 3, '키 발급 3단계 안내가 없음');
  ok(r.apiGuide.title.indexOf('HIRA_API_KEY') !== -1, '안내 제목에 HIRA_API_KEY 표기가 없음');
  ok(r.deptOptions.length >= 10, '진료과 목록이 부족함: ' + r.deptOptions.length);
  ok(r.warnings.join(' ').indexOf('HIRA_API_KEY') !== -1, '키 안내 문구가 없음');
});
t('HIRA 미설정: 이미 등록된 거래처면 중복 등록 방지 정보를 줌', function () {
  var r = getHiraPrevisitBriefing({ name: '테스트소아청소년과의원01' }, TOKEN);
  ok(r.registration && r.registration.exists, '등록된 거래처로 잡히지 않음');
  ok(/^S\d{3,}$/.test(r.registration.거래처코드), '거래처코드가 Sxxx 가 아님: ' + r.registration.거래처코드);
});
t('HIRA 미설정: 진료과만 골라도 다처방 TOP 30 · 추천 브리핑이 나옴', function () {
  setHiraKey_('');
  var r = getHiraPrevisitBriefing({ dept: '내과' }, TOKEN);
  eq(r.mode, 'offline');
  ok(r.briefing, '브리핑이 없음');
  eq(r.briefing.matchedDepts[0].진료과, '내과');
  eq(r.briefing.topIngredients.top10.length, 10);
  ok(r.briefing.topIngredients.all.length <= 30, 'TOP 30 을 넘음');
  ok(r.briefing.topIngredients.all.length >= 10, '성분이 너무 적음');
  ok(r.briefing.basis.indexOf('공개하지 않습니다') !== -1, '예상 추천 고지 문구가 없음');
  var first = r.briefing.topIngredients.top10[0];
  ok(first.성분명 && first.질환군, '성분·질환군(병명)이 없음');
  ok(Array.isArray(first.우리제품) && first.우리제품.length >= 1, '우리 제품 매칭이 없음');
  ok(r.briefing.injectTargets.length >= 1, '진료과 기반 주사 타깃이 없음');
});
t('HIRA 진료과 매핑: 분과·일반의도 우리 가이드 과로 붙음', function () {
  var m = hiraMapDeptsToGuide_(['소화기내과', '일반의', '이비인후과', '비뇨기과']);
  var names = m.map(function (x) { return x.진료과; });
  ok(names.indexOf('내과') !== -1, '소화기내과 → 내과 실패');
  ok(names.indexOf('가정의학과') !== -1, '일반의 → 가정의학과 실패');
  ok(names.indexOf('이비인후과') !== -1, '이비인후과 실패');
  ok(names.indexOf('비뇨의학과') !== -1, '비뇨기과 → 비뇨의학과 실패');
});

t('HIRA 키 설정: 병원명+지역으로 검색되고 진료과목·평가등급이 붙음', function () {
  setHiraKey_('TEST_HIRA_KEY');
  var r = getHiraPrevisitBriefing({ name: '부산동래한내과', region: '부산 동래구' }, TOKEN);
  eq(r.configured, true);
  eq(r.mode, 'live');
  eq(r.hospitals.length, 1, '지역 필터 결과 건수');
  ok(r.hospital && r.hospital.요양기관명 === '부산동래한내과의원', '병원 선택 오류');
  eq(r.hospital.종별, '의원');
  eq(r.hospital.전문의수, 2);
  eq(r.hira.진료과목[0].과목, '내과');
  eq(r.hira.평가.length, 4, '평가등급 4종이 아님');
  ok(r.briefing && r.briefing.topIngredients.top10.length === 10, '진료과목 → 브리핑 연결 실패');
});
t('HIRA 검색: 지역을 안 넣으면 다른 지역 동명 병원도 함께 보임', function () {
  var r = getHiraPrevisitBriefing({ name: '부산동래한내과' }, TOKEN);
  eq(r.hospitals.length, 3, '전체 후보 건수');
  var r2 = getHiraPrevisitBriefing({ name: '부산동래한내과', region: '대전' }, TOKEN);
  eq(r2.hospitals.length, 3, '지역 미스면 전체를 보여 줘야 함');
  ok(r2.warnings.join(' ').indexOf('대전') !== -1, '지역 미스 안내가 없음');
});
t('HIRA 병원급: 비급여 항목·가격과 주사 타깃·평가등급 연결', function () {
  var r = getHiraPrevisitBriefing({ name: '부산동래한병원' }, TOKEN);
  eq(r.mode, 'live');
  eq(r.hira.비급여.length, 4, '비급여 건수');
  var first = r.hira.비급여.filter(function (x) { return x.항목.indexOf('글루타치온') !== -1; })[0];
  ok(first && first.금액 === 30000, '비급여 금액 파싱 오류');
  ok(r.briefing, '브리핑 없음');
  var tags = r.briefing.nonPayMatched.map(function (x) { return x.tag; }).join(' ');
  ok(tags.indexOf('백옥') !== -1, '백옥주사 태그가 안 붙음: ' + tags);
  ok(tags.indexOf('도수') !== -1, '도수치료 태그가 안 붙음: ' + tags);
  var tgt = r.briefing.injectTargets[0];
  ok(tgt && tgt.케이스, '주사 타깃이 없음');
  ok(tgt.우리제품.length >= 1, '주사 타깃에 우리 제품이 없음');
  ok(r.briefing.grades.length === 4, '평가등급이 브리핑에 없음');
});
t('HIRA: 잘못된 인증키는 예외 없이 안내 문구로 돌려줌', function () {
  setHiraKey_('BAD_KEY');
  var r = getHiraPrevisitBriefing({ name: '서울의료원' }, TOKEN);
  ok(r && r.configured === true, 'configured 는 true');
  eq(r.mode, 'offline');
  ok(!r.hospital, '병원이 잡히면 안 됨');
  ok(r.warnings.join(' ').indexOf('인증키') !== -1, '인증키 안내가 없음: ' + r.warnings.join(' | '));
});
t('HIRA: XML 응답도 해석 (비급여 서비스는 XML 만 응답)', function () {
  setHiraKey_('TEST_HIRA_KEY');
  var res = hiraCall_(HIRA_SERVICES_.HOSP, { yadmNm: '부산동래한병원' }, { xml: true, noCache: true });
  ok(res.ok, 'XML 호출 실패: ' + res.message);
  eq(res.items.length, 1);
  eq(res.totalCount, 1);
  eq(res.items[0].ykiho, 'YKI_HOSP_DONGNAE');
});
t('HIRA: 연동 점검은 4개 서비스를 실제로 확인', function () {
  var r = checkHiraApi(TOKEN);
  ok(r.configured, '키 미설정으로 나옴');
  eq(r.services.length, 4, '점검 항목 수');
  ok(r.ok, '연동 점검이 실패로 나옴: ' + JSON.stringify(r.services));
});
t('HIRA: 같은 병원을 다시 보면 캐시를 써서 호출을 아끼고, 응답은 같음', function () {
  setHiraKey_('TEST_HIRA_KEY');
  var a = getHiraPrevisitBriefing({ name: '부산동래한내과', region: '부산 동래구' }, TOKEN);
  var calls1 = __HIRA_CALLS.length;
  var b = getHiraPrevisitBriefing({ name: '부산동래한내과', region: '부산 동래구' }, TOKEN);
  var calls2 = __HIRA_CALLS.length;
  eq(calls2, calls1, '캐시가 안 먹혀 API 를 다시 부름');
  eq(a.hospital.요양기관명, b.hospital.요양기관명);
  eq(a.hira.평가.length, b.hira.평가.length);
});
t('HIRA: STAFF 에게는 차감된 요율만 (등급·원본요율 비노출)', function () {
  setHiraKey_('');
  var m = getHiraPrevisitBriefing({ dept: '내과' }, TOKEN);
  var s = getHiraPrevisitBriefing({ dept: '내과' }, STAFF_TOKEN);
  ok(m.briefing.highRatePicks.length >= 5, 'MASTER 추천 품목 부족');
  eq(s.briefing.highRatePicks.length, m.briefing.highRatePicks.length);
  var md = {};
  m.briefing.highRatePicks.forEach(function (p) { md[p.보험코드] = p.수수료율; });
  var checked = 0;
  s.briefing.highRatePicks.forEach(function (p) {
    if (md[p.보험코드] === undefined) return;
    eq(p.수수료율, Math.max(0, md[p.보험코드] - 2), 'STAFF 요율 차감 오류 (' + p.품목명 + ')');
    checked++;
  });
  ok(checked >= 5, '비교한 품목이 부족함');
  var txt = JSON.stringify(s);
  ['요율등급', '요율차감', '원본요율'].forEach(function (k) {
    ok(txt.indexOf(k) === -1, 'STAFF 응답에 ' + k + ' 가 들어 있음');
  });
});
t('HIRA: 로그인 토큰이 없으면 거부', function () {
  throwsMatch(function () { getHiraPrevisitBriefing({ name: '부산동래한병원' }, ''); }, '로그인');
});

// ------------------------------------------------------------------ 13. v1.8 — 보험코드 앞자리 0 보존 · 중복 방지
/** 처방내역 시트에 행을 직접 추가 (시트가 숫자·날짜로 바꿔 버린 예전 상태 재현용) */
function addRxRow_(obj) {
  var head = __SHEETS['처방내역'][0];
  var row = head.map(function (h) { return obj[h] === undefined ? '' : obj[h]; });
  __SHEETS['처방내역'].push(row);
  return row;
}
function rxSheetRow_(prescriptionId) {
  var list = __SHEETS['처방내역'], iId = list[0].indexOf('처방ID');
  for (var i = 1; i < list.length; i++) {
    if (String(list[i][iId]) === String(prescriptionId)) return { row: list[i], rowNo: i + 1 };
  }
  return null;
}
function rxRowsOfCode_(codeKey) {
  return getAllRowsAsObjects_('처방내역').filter(function (r) {
    return (insuranceCodeKey_(r['보험코드']) || String(r['보험코드'] || '')) === codeKey;
  });
}

t('보험코드: 앞자리 0 이 잘린 7~8자리는 9자리로 되살림', function () {
  eq(normalizeInsuranceCode_('73001620'), '073001620');
  eq(normalizeInsuranceCode_('073001620'), '073001620');
  eq(normalizeInsuranceCode_(73001620), '073001620');
  eq(normalizeInsuranceCode_(' 073001480 '), '073001480');
  eq(normalizeInsuranceCode_(''), '');
  eq(normalizeInsuranceCode_('M2094163'), 'M2094163');
  eq(normalizeInsuranceCode_('01291'), '01291', '5자리 제품코드는 건드리지 않음');
});
t('보험코드: 073001620 과 73001620 은 같은 약(비교 키 동일)', function () {
  eq(insuranceCodeKey_('073001620'), insuranceCodeKey_('73001620'));
  eq(insuranceCodeKey_(73001620), '73001620');
  ok(insuranceCodeKey_('073001620') !== insuranceCodeKey_('073001480'), '다른 약이 합쳐짐');
  eq(insuranceCodeKey_(''), '');
});
t('기준월: 날짜로 바뀐 2026-11-01 도 2026-11 로 읽음', function () {
  eq(normalizeMonth_('2026-11'), '2026-11');
  eq(normalizeMonth_('2026-11-01'), '2026-11');
  eq(normalizeMonth_(new Date(Date.UTC(2026, 10, 1))), '2026-11');
  eq(normalizeMonth_('2026-11-28 1:46:54'), '2026-11');
  eq(normalizeMonth_('2026년 11월'), '2026-11');
  eq(normalizeMonth_(46327), '2026-11', '날짜 서식이 벗겨진 직렬값');
  eq(normalizeMonth_('202611'), '2026-11');
});

t('처방 저장: 보험코드 073001620 이 시트에 텍스트로 남아 앞자리 0 유지', function () {
  var before = __SHEETS['처방내역'].length;
  try {
    var code = getClients(true, TOKEN)[0].거래처코드;
    // 예전 캐시에서처럼 앞자리 0 이 없는 코드가 올라와도 9자리로 되살려 저장해야 합니다.
    var res = savePrescriptions({
      기준월: '2026-11', 처방일: '2026-11-28', 거래처코드: code,
      items: [{ 보험코드: '73001620', 품목명: '건피드정', 규격: '', 제약사: '건일바이오팜㈜', 약가: 119, 수량: 10, 수수료율: 52 }]
    }, TOKEN);
    ok(res.success, '저장 실패');
    eq(res.created, 1, '새 행이 생겨야 함');
    var hit = rxSheetRow_(res.rows[0].처방ID);
    ok(hit, '저장된 행을 찾지 못함');
    var iCode = __SHEETS['처방내역'][0].indexOf('보험코드');
    eq(hit.row[iCode], '073001620', '시트에 앞자리 0 이 사라짐');
    eq(typeof hit.row[iCode], 'string', '시트 보험코드가 숫자로 바뀜');
    var fmt = getSheet_('처방내역').formats[hit.rowNo + ':' + (iCode + 1)];
    eq(fmt, '@', '보험코드 열이 텍스트 서식이 아님');
    ok(res.rows[0].보험코드 === '073001620', '응답 코드가 9자리가 아님: ' + res.rows[0].보험코드);
  } finally {
    __SHEETS['처방내역'].length = before;
  }
});

t('처방 저장: 기준월 2026-11 이 날짜로 바뀌지 않고 그 달 조회에 잡힘', function () {
  var before = __SHEETS['처방내역'].length;
  try {
    var code = getClients(true, TOKEN)[0].거래처코드;
    var res = savePrescriptions({
      기준월: '2026-11', 처방일: '2026-11-28', 거래처코드: code,
      items: [{ 보험코드: '073001480', 품목명: '라베건정10mg', 규격: '', 제약사: '건일바이오팜㈜', 약가: 454, 수량: 7, 수수료율: 58 }]
    }, TOKEN);
    ok(res.success, '저장 실패');
    var hit = rxSheetRow_(res.rows[0].처방ID);
    var iMonth = __SHEETS['처방내역'][0].indexOf('기준월');
    eq(hit.row[iMonth], '2026-11', '기준월이 날짜(직렬값)로 바뀜');
    var got = getPrescriptions('2026-11', code, TOKEN);
    ok(got.rows.some(function (r) { return insuranceCodeKey_(r.보험코드) === '73001480'; }), '그 달 조회에 안 잡힘');
    eq(got.rows.filter(function (r) { return insuranceCodeKey_(r.보험코드) === '73001480'; })[0].기준월, '2026-11');
  } finally {
    __SHEETS['처방내역'].length = before;
  }
});

t('처방 저장: 앞자리 0 없는 예전 줄(73001620)은 새로 만들지 않고 갱신', function () {
  var before = __SHEETS['처방내역'].length;
  try {
    var code = getClients(true, TOKEN)[0].거래처코드;
    // 시트가 예전에 숫자·날짜로 바꿔 저장해 둔 상태를 그대로 재현
    addRxRow_({
      처방ID: 'RXOLD0001', 기준월: new Date(Date.UTC(2026, 10, 1)), 처방일: new Date(Date.UTC(2026, 10, 1)),
      거래처코드: code, 거래처명: '수아의원', 담당자: '최담당', 제약사: '건일바이오팜㈜',
      보험코드: 73001620, 품목명: '건피드정', 규격: '', 약가: 119, 수량: 5,
      처방금액: 595, 수수료율: 52, 예상수수료: 309, 비고: '', 등록일시: '2026-11-01 09:00:00'
    });
    var res = savePrescriptions({
      기준월: '2026-11', 처방일: '2026-11-28', 거래처코드: code,
      items: [{ 보험코드: '073001620', 품목명: '건피드정', 규격: '', 제약사: '건일바이오팜㈜', 약가: 119, 수량: 9, 수수료율: 52 }]
    }, TOKEN);
    eq(res.created, 0, '같은 약인데 새 행이 생김');
    eq(res.updated, 1, '갱신이 안 됨');
    eq(rxRowsOfCode_('73001620').length, 1, '같은 약이 두 줄로 남음');
    var row = rxRowsOfCode_('73001620')[0];
    eq(row['처방ID'], 'RXOLD0001', '처방ID 가 바뀜');
    eq(row['수량'], 9, '수량이 갱신되지 않음');
    eq(row['보험코드'], '073001620', '보험코드가 9자리 텍스트로 고쳐지지 않음');
    eq(row['기준월'], '2026-11', '기준월이 텍스트로 고쳐지지 않음');
  } finally {
    __SHEETS['처방내역'].length = before;
  }
});

t('빠른 입력: 073001620 과 73001620 이 두 줄로 보이지 않음', function () {
  var before = __SHEETS['처방내역'].length;
  try {
    var code = getClients(true, TOKEN)[0].거래처코드;
    addRxRow_({
      처방ID: 'RXOLD0002', 기준월: '2026-11', 처방일: '2026-11-01', 거래처코드: code, 거래처명: '수아의원',
      담당자: '최담당', 제약사: '건일바이오팜㈜', 보험코드: 73001620, 품목명: '건피드정', 규격: '',
      약가: 119, 수량: 10000, 처방금액: 1190000, 수수료율: 52, 예상수수료: 618800, 비고: '', 등록일시: '2026-11-01 10:00:00'
    });
    var quick = getPrescriptionQuickItems(code, TOKEN);
    var hits = quick.items.filter(function (it) { return insuranceCodeKey_(it.보험코드) === '73001620'; });
    eq(hits.length, 1, '같은 약이 ' + hits.length + '줄로 내려감');
    eq(hits[0].보험코드, '073001620');
    eq(hits[0].사용횟수, 1);
    eq(hits[0].최근월, '2026-11');
    eq(hits[0].최근수량, 10000);
    var freq = getFrequentElpharmaProducts(100, TOKEN).items.filter(function (it) { return insuranceCodeKey_(it.보험코드) === '73001620'; });
    eq(freq.length, 1, '자주 쓴 품목에 두 줄로 나옴');
  } finally {
    __SHEETS['처방내역'].length = before;
  }
});

t('처방 조회: 같은 달 같은 약의 앞자리0 중복 줄은 한 줄로', function () {
  var before = __SHEETS['처방내역'].length;
  try {
    var code = getClients(true, TOKEN)[0].거래처코드;
    addRxRow_({
      처방ID: 'RXOLD0003', 기준월: '2026-11', 처방일: '2026-11-01', 거래처코드: code, 거래처명: '수아의원',
      담당자: '최담당', 제약사: '건일바이오팜㈜', 보험코드: 73001480, 품목명: '라베건정10mg', 규격: '',
      약가: 454, 수량: 5, 처방금액: 2270, 수수료율: 58, 예상수수료: 1317, 비고: '', 등록일시: '2026-11-01 10:00:00'
    });
    addRxRow_({
      처방ID: 'RXNEW0004', 기준월: '2026-11', 처방일: '2026-11-28', 거래처코드: code, 거래처명: '수아의원',
      담당자: '최담당', 제약사: '건일바이오팜㈜', 보험코드: '073001480', 품목명: '라베건정10mg', 규격: '',
      약가: 454, 수량: 8, 처방금액: 3632, 수수료율: 58, 예상수수료: 2107, 비고: '', 등록일시: '2026-11-28 10:00:00'
    });
    var got = getPrescriptions('2026-11', code, TOKEN);
    var rows = got.rows.filter(function (r) { return insuranceCodeKey_(r.보험코드) === '73001480'; });
    eq(rows.length, 1, '같은 약이 ' + rows.length + '줄로 내려감');
    eq(rows[0].수량, 8, '가장 최근 저장 줄이 남지 않음');
    eq(rows[0].중복행, 2, '중복 줄 수 표시가 없음');
    eq((rows[0].처방IDs || []).length, 2, '함께 지울 처방ID 가 없음');
    eq(got.summary.건수, got.rows.length, '합계 건수에 중복이 더해짐');
  } finally {
    __SHEETS['처방내역'].length = before;
  }
});

t('처방 삭제: 앞자리 0 으로 갈라진 같은 약 줄을 함께 지움', function () {
  var before = __SHEETS['처방내역'].length;
  try {
    var code = getClients(true, TOKEN)[0].거래처코드;
    addRxRow_({
      처방ID: 'RXDEL0001', 기준월: '2026-12', 처방일: '2026-12-01', 거래처코드: code, 거래처명: '수아의원',
      담당자: '최담당', 제약사: '건일바이오팜㈜', 보험코드: 73001620, 품목명: '건피드정', 규격: '',
      약가: 119, 수량: 10, 처방금액: 1190, 수수료율: 52, 예상수수료: 619, 비고: '', 등록일시: '2026-12-01 10:00:00'
    });
    addRxRow_({
      처방ID: 'RXDEL0002', 기준월: '2026-12', 처방일: '2026-12-02', 거래처코드: code, 거래처명: '수아의원',
      담당자: '최담당', 제약사: '건일바이오팜㈜', 보험코드: '073001620', 품목명: '건피드정', 규격: '',
      약가: 119, 수량: 10, 처방금액: 1190, 수수료율: 52, 예상수수료: 619, 비고: '', 등록일시: '2026-12-02 10:00:00'
    });
    var del = deletePrescription('RXDEL0002', TOKEN);
    ok(del.success, '삭제 실패');
    eq(del.deleted, 2, '갈라진 중복 줄이 남음');
    eq(rxRowsOfCode_('73001620').length, 0, '삭제하고도 줄이 남음');
  } finally {
    __SHEETS['처방내역'].length = before;
  }
});

// ------------------------------------------------------------------ 14. v1.8 — 월별 실적: 직납(거래내역) + 예상 처방(처방내역) 합산
function addTxRow_(obj) {
  var head = __SHEETS['거래내역'][0];
  var row = head.map(function (h) { return obj[h] === undefined ? '' : obj[h]; });
  __SHEETS['거래내역'].push(row);
  return row;
}
function perfMgr_(res, name) {
  return (res.managers || []).filter(function (m) { return m.담당자 === name; })[0];
}
function perfClient_(res, code) {
  return (res.clients || []).filter(function (c) { return c.거래처코드 === code; })[0];
}
/** 직납·처방 시험용 데이터로 바꿔 실행하고, 끝나면 원래 시트로 되돌립니다. */
function withPerfFixtures_(fn) {
  var rxBackup = __SHEETS['처방내역'].slice(1);
  var txBackup = __SHEETS['거래내역'].slice(1);
  var cl = __SHEETS['거래처'];
  var iMgr = cl[0].indexOf('담당자');
  var iCode = cl[0].indexOf('거래처코드');
  var mgrBefore = cl.map(function (r) { return r[iMgr]; });
  var codeA = cl[1][iCode], codeB = cl[2][iCode];
  __SHEETS['처방내역'].length = 1;
  __SHEETS['거래내역'].length = 1;
  try {
    cl[2][iMgr] = '정담당';   // 두 번째 거래처는 다른 담당자 (STAFF 노출 확인용)
    var today = formatDate_(new Date());
    var ym = currentMonth_();
    addTxRow_({ 거래ID: 'TXPERF1', 날짜: today, 구분: '매출', 거래처코드: codeA, 거래처명: 'A의원', 품목명: '테스트주', 수량: 10, 단가: 100000, 공급가액: 909091, 부가세: 90909, 합계금액: 1000000 });
    addTxRow_({ 거래ID: 'TXPERF2', 날짜: today, 구분: '수금', 거래처코드: codeA, 거래처명: 'A의원', 합계금액: 400000, 수금유형: '현금' });
    addRxRow_({ 처방ID: 'RXPERF1', 기준월: ym, 처방일: today, 거래처코드: codeA, 거래처명: 'A의원', 담당자: '최충의', 제약사: '테스트제약', 보험코드: '073001620', 품목명: '건피드정', 규격: '', 약가: 1000, 수량: 10, 처방금액: 10000, 수수료율: 50, 예상수수료: 5000, 비고: '', 등록일시: today + ' 09:00:00' });
    addRxRow_({ 처방ID: 'RXPERF2', 기준월: ym, 처방일: today, 거래처코드: codeA, 거래처명: 'A의원', 담당자: '최충의', 제약사: '테스트제약', 보험코드: '073001480', 품목명: '라베건정10mg', 규격: '', 약가: 2000, 수량: 5, 처방금액: 10000, 수수료율: 60, 예상수수료: 6000, 비고: '', 등록일시: today + ' 09:00:01' });
    addRxRow_({ 처방ID: 'RXPERF3', 기준월: ym, 처방일: today, 거래처코드: codeB, 거래처명: 'B의원', 담당자: '정담당', 제약사: '테스트제약', 보험코드: '649104260', 품목명: '아카에정', 규격: '', 약가: 500, 수량: 4, 처방금액: 2000, 수수료율: 40, 예상수수료: 800, 비고: '', 등록일시: today + ' 10:00:00' });
    fn({ codeA: codeA, codeB: codeB, ym: ym, today: today });
  } finally {
    __SHEETS['처방내역'].length = 1;
    __SHEETS['거래내역'].length = 1;
    rxBackup.forEach(function (r) { __SHEETS['처방내역'].push(r); });
    txBackup.forEach(function (r) { __SHEETS['거래내역'].push(r); });
    cl.forEach(function (r, i) { r[iMgr] = mgrBefore[i]; });
  }
}

t('월별 실적: 직납 매출·예상 처방금액·예상 총매출이 각각 집계됨', function () {
  withPerfFixtures_(function (fx) {
    var res = getMonthlyPerformance(fx.ym, 3, '', TOKEN);
    var m = perfMgr_(res, '최충의');
    ok(m, '최충의 담당자 행이 없습니다');
    eq(m.당월.직납매출, 1000000, '직납매출');
    eq(m.당월.매출합계, 1000000, '매출합계(직납 별칭)');
    eq(m.당월.예상처방금액, 20000, '예상 처방금액');
    eq(m.당월.처방금액, 20000, '처방금액 별칭');
    eq(m.당월.예상총매출, 1020000, '예상 총매출 = 직납 + 예상 처방');
    eq(m.당월.총매출, 1020000, '총매출 별칭');
    eq(m.당월.처방건수, 2, '처방 품목 줄 수');
    eq(m.당월.직납건수, 1, '매출 건수');
    eq(m.당월.예상수수료, 11000, 'MASTER 는 원본 예상수수료 그대로');
    eq(m.당월.수금합계, 400000, '수금');
    eq(m.미수금, 600000, '미수금은 직납(거래내역) 기준');
    ok(m.당월.예상총매출 === m.당월.직납매출 + m.당월.예상처방금액, '총매출 합산식 불일치');
  });
});

t('월별 실적: 처방만 있는 담당자도 행으로 나오고 직납은 0', function () {
  withPerfFixtures_(function (fx) {
    var res = getMonthlyPerformance(fx.ym, 3, '', TOKEN);
    var m = perfMgr_(res, '정담당');
    ok(m, '처방만 있는 담당자 행이 없습니다');
    eq(m.당월.직납매출, 0, '직납매출');
    eq(m.당월.예상처방금액, 2000, '예상 처방금액');
    eq(m.당월.예상총매출, 2000, '예상 총매출');
    eq(m.미수금, 0, '미수금');
  });
});

t('월별 실적: 합계(totals)가 직납·예상 처방·예상 총매출을 함께 담음', function () {
  withPerfFixtures_(function (fx) {
    var res = getMonthlyPerformance(fx.ym, 3, '', TOKEN);
    eq(res.totals.당월.직납매출, 1000000, '합계 직납');
    eq(res.totals.당월.예상처방금액, 22000, '합계 예상 처방');
    eq(res.totals.당월.예상총매출, 1022000, '합계 예상 총매출');
    eq(res.totals.당월.수금합계, 400000, '합계 수금');
    eq(res.totals.미수금, 600000, '합계 미수금');
    eq(res.months.length, 3, '추이 개월 수');
    var last = res.totals.series[res.totals.series.length - 1];
    eq(last.month, res.targetMonth, '추이 마지막 달이 기준월이 아님');
    eq(last.예상총매출, 1022000, '추이 마지막 달 예상 총매출');
    eq(last.직납매출, 1000000, '추이 직납');
    eq(last.예상처방금액, 22000, '추이 예상 처방');
  });
});

t('월별 실적: 병원별 표에 예상 총매출·직납·예상 처방·예상 수수료가 함께', function () {
  withPerfFixtures_(function (fx) {
    var res = getMonthlyPerformance(fx.ym, 3, '', TOKEN);
    var a = perfClient_(res, fx.codeA);
    ok(a, '병원별 행 없음');
    eq(a.직납매출, 1000000, '병원 직납');
    eq(a.예상처방금액, 20000, '병원 예상 처방');
    eq(a.예상총매출, 1020000, '병원 예상 총매출');
    eq(a.예상수수료, 11000, '병원 예상 수수료');
    eq(a.미수금, 600000, '병원 미수금');
    var b = perfClient_(res, fx.codeB);
    eq(b.예상총매출, 2000, '처방만 있는 병원');
    eq(b.예상수수료, 800, '처방만 있는 병원 수수료');
    // 정렬: 예상 총매출 큰 병원이 위
    eq(res.clients[0].거래처코드, fx.codeA, '병원별 정렬이 예상 총매출 순이 아님');
  });
});

t('월별 실적: 담당자 필터를 걸면 그 담당자만 집계', function () {
  withPerfFixtures_(function (fx) {
    var res = getMonthlyPerformance(fx.ym, 3, '정담당', TOKEN);
    eq(res.managers.length, 1, '필터가 안 걸림');
    eq(res.managers[0].담당자, '정담당');
    eq(res.totals.당월.예상총매출, 2000, '필터 합계가 그 담당자 것만이 아님');
    eq(res.clients.length, 1, '병원별도 필터 안 됨');
  });
});

t('월별 실적: STAFF 는 본인 담당 거래처만 + 예상수수료가 등급 차감값', function () {
  withPerfFixtures_(function (fx) {
    var cl = __SHEETS['거래처'];
    var iMgr = cl[0].indexOf('담당자');
    cl[1][iMgr] = '최담당';           // S001 을 choi(최담당) 담당으로
    setTier_('choi', '2단계');
    var res = getMonthlyPerformance(fx.ym, 3, '', STAFF_TOKEN);
    eq(res.managers.length, 1, 'STAFF 에 타 담당자 실적이 보임');
    var m = res.managers[0];
    eq(m.당월.직납매출, 1000000, 'STAFF 직납');
    eq(m.당월.예상처방금액, 20000, 'STAFF 예상 처방');
    // 원본 50% → 48%, 60% → 58% : 10000*0.48 + 10000*0.58
    eq(m.당월.예상수수료, 10600, 'STAFF 예상수수료가 등급 차감값이 아님');
    var txt = JSON.stringify(res);
    ['요율등급', '원본요율', '요율차감'].forEach(function (k) {
      ok(txt.indexOf(k) === -1, 'STAFF 응답에 ' + k + ' 가 들어 있음');
    });
    ok(txt.indexOf('정담당') === -1, 'STAFF 응답에 타 담당자 이름이 들어 있음');
  });
});

t('월별 실적: 같은 달 같은 약의 중복 줄(앞자리 0)은 한 번만 집계', function () {
  withPerfFixtures_(function (fx) {
    addRxRow_({ 처방ID: 'RXPERF1DUP', 기준월: fx.ym, 처방일: fx.today, 거래처코드: fx.codeA, 거래처명: 'A의원', 담당자: '최충의', 제약사: '테스트제약', 보험코드: '73001620', 품목명: '건피드정', 규격: '', 약가: 1000, 수량: 10, 처방금액: 10000, 수수료율: 50, 예상수수료: 5000, 비고: '', 등록일시: fx.today + ' 09:30:00' });
    var res = getMonthlyPerformance(fx.ym, 3, '', TOKEN);
    var m = perfMgr_(res, '최충의');
    eq(m.당월.예상처방금액, 20000, '중복 줄이 두 번 더해짐');
    eq(m.당월.처방건수, 2, '중복 줄이 품목 수에 더해짐');
    var a = perfClient_(res, fx.codeA);
    eq(a.예상처방금액, 20000, '병원별 중복 합산');
  });
});

t('월별 실적: 기준월이 날짜로 굳은 처방 줄도 같은 달로 집계', function () {
  withPerfFixtures_(function (fx) {
    var list = __SHEETS['처방내역'];
    var iM = list[0].indexOf('기준월');
    list[1][iM] = fx.ym + '-01';   // 시트가 날짜로 바꿔 저장한 상태
    var res = getMonthlyPerformance(fx.ym, 3, '', TOKEN);
    var m = perfMgr_(res, '최충의');
    ok(m, '담당자 행 없음');
    eq(m.당월.예상처방금액, 20000, '날짜로 굳은 기준월이 집계되지 않음');
  });
});

t('월별 실적: 거래기간 밖 달의 처방은 그 달 칸에만 들어감', function () {
  withPerfFixtures_(function (fx) {
    addRxRow_({ 처방ID: 'RXPERFOLD', 기준월: '2026-09', 처방일: '2026-09-10', 거래처코드: fx.codeA, 거래처명: 'A의원', 담당자: '최충의', 제약사: '테스트제약', 보험코드: '649100710', 품목명: '암펙솔정', 규격: '', 약가: 100, 수량: 1, 처방금액: 100, 수수료율: 40, 예상수수료: 40, 비고: '', 등록일시: '2026-09-10 10:00:00' });
    var res = getMonthlyPerformance('2026-11', 6, '', TOKEN);
    eq(res.months[0], '2026-06', '6개월 추이 시작');
    var sep = res.totals.series.filter(function (s) { return s.month === '2026-09'; })[0];
    ok(sep, '2026-09 칸 없음');
    eq(sep.예상처방금액, 100, '지난 달 예상 처방');
    var nov = res.totals.series.filter(function (s) { return s.month === '2026-11'; })[0];
    eq(nov.예상처방금액, 22000, '당월 예상 처방');
    eq(nov.직납매출, 1000000, '당월 직납');
  });
});


// ------------------------------------------------------------------ 18. 공지사항 · 게시판 (v1.14)
function boardSheet_() { return getSheet_(SHEET_NAMES.BOARD); }
function boardClear_() {
  var sh = boardSheet_();
  while (sh.getLastRow() > 1) sh.deleteRow(sh.getLastRow());
  return sh;
}
function boardLast_() {
  var sh = boardSheet_();
  var row = sh.values[sh.getLastRow() - 1] || [];
  var head = sh.values[0] || [];
  var o = {};
  for (var i = 0; i < head.length; i++) o[head[i]] = row[i];
  return o;
}

t('게시판: 시트 탭·헤더 10칸이 정의되어 있음', function () {
  eq(SHEET_NAMES.BOARD, '게시판');
  var head = SHEET_HEADERS['게시판'];
  eq(head.join('|'), '번호|구분|카테고리|제목|내용|작성자아이디|작성자명|고정여부|작성일시|수정일시');
});

t('게시판: 시트가 없으면 initializeSheets 가 만들어 줌', function () {
  var sh = boardSheet_();
  ok(sh, '게시판 시트 없음');
  eq(sh.values[0].join('|'), '번호|구분|카테고리|제목|내용|작성자아이디|작성자명|고정여부|작성일시|수정일시');
});

t('게시판: STAFF 가 자유 게시판에 글을 쓴다', function () {
  boardClear_();
  var res = boardCreate({ 구분: '자유', 카테고리: '질문', 제목: '수아의원 단가 문의', 내용: '이번 달 단가 확인 부탁드립니다.' }, STAFF_TOKEN);
  ok(res && res.success, '자유 글 작성 실패');
  eq(res.번호, 1, '첫 글 번호');
  var row = boardLast_();
  eq(row.구분, '자유');
  eq(row.카테고리, '질문');
  eq(row.작성자아이디, 'choi', '작성자 아이디');
  eq(row.작성자명, STAFF.bootstrap.user.담당자명, '작성자 이름');
  eq(row.고정여부, 'N');
  ok(/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/.test(String(row.작성일시)), '작성일시 형식: ' + row.작성일시);
});

t('게시판: STAFF 는 공지사항을 쓸 수 없다', function () {
  throwsMatch(function () {
    boardCreate({ 구분: '공지', 카테고리: '일반 공지', 제목: '공지', 내용: '내용' }, STAFF_TOKEN);
  }, 'MASTER 권한만', 'STAFF 공지 작성');
});

t('게시판: MASTER 는 공지를 쓰고 상단 고정할 수 있다', function () {
  var res = boardCreate({ 구분: '공지', 카테고리: '미지급 사유', 제목: '제약사별 소액처 기준', 내용: '국제약품 소액처 정산 가능', 고정여부: 'Y' }, TOKEN);
  ok(res && res.success, '공지 작성 실패');
  eq(res.번호, 2, '두 번째 글 번호');
  var row = boardLast_();
  eq(row.구분, '공지');
  eq(row.고정여부, 'Y', '고정 여부');
});

t('게시판: 공지 카테고리 목록에 없는 값은 일반 공지로', function () {
  var res = boardCreate({ 구분: '공지', 카테고리: '아무말', 제목: '분류 시험', 내용: '내용' }, TOKEN);
  eq(boardLast_().카테고리, '일반 공지', '카테고리 정규화');
  boardDelete({ 번호: res.번호 }, TOKEN);
});

t('게시판: 제목·내용이 없으면 저장하지 않는다', function () {
  throwsMatch(function () { boardCreate({ 구분: '자유', 제목: '  ', 내용: '내용' }, STAFF_TOKEN); }, '제목', '빈 제목');
  throwsMatch(function () { boardCreate({ 구분: '자유', 제목: '제목', 내용: '   ' }, STAFF_TOKEN); }, '내용', '빈 내용');
});

t('게시판: 로그인 없이는 읽지도 쓰지도 못한다', function () {
  throwsMatch(function () { boardList({}, ''); }, '로그인이 필요', '목록');
  throwsMatch(function () { boardCreate({ 구분: '자유', 제목: '제목', 내용: '내용' }, ''); }, '로그인이 필요', '작성');
});

t('게시판: 목록은 고정 글이 먼저, 그 다음 최신 순', function () {
  var all = boardList({}, TOKEN);
  eq(all.total, 2, '글 수');
  eq(all.items[0].번호, 2, '고정 글이 맨 위');
  eq(all.items[0].고정여부, 'Y');
  eq(all.items[1].번호, 1);
});

t('게시판: 구분·카테고리·검색으로 거를 수 있다', function () {
  eq(boardList({ 구분: '공지' }, TOKEN).total, 1, '공지 수');
  eq(boardList({ 구분: '자유' }, TOKEN).total, 1, '자유 수');
  eq(boardList({ 구분: '공지', 카테고리: '미지급 사유' }, TOKEN).total, 1, '카테고리');
  eq(boardList({ 구분: '공지', 카테고리: '특별 수수료율' }, TOKEN).total, 0, '없는 카테고리');
  eq(boardList({ 검색: '단가' }, TOKEN).total, 1, '검색');
  eq(boardList({ 검색: '없는말' }, TOKEN).total, 0, '검색 없음');
  var one = boardList({ 검색: '국제약품' }, TOKEN);
  eq(one.total, 1, '내용 검색');
  eq(one.items[0].구분, '공지');
});

t('게시판: 목록 응답에 구분별 개수·카테고리별 개수가 함께 온다', function () {
  var res = boardList({}, TOKEN);
  eq(res.counts['공지'], 1, '공지 개수');
  eq(res.counts['자유'], 1, '자유 개수');
  eq(res.categories['공지'][0].카테고리, '미지급 사유');
  eq(res.categories['공지'][0].개수, 1);
  eq(res.isMaster, true);
  eq(boardList({}, STAFF_TOKEN).isMaster, false);
});

t('게시판: 자유 글은 본인만 수정·삭제할 수 있다', function () {
  var master = login('master', 'test');
  // 다른 사람(마스터)이 쓴 자유 글
  var other = boardCreate({ 구분: '자유', 제목: '마스터가 쓴 자유 글', 내용: '내용' }, TOKEN);
  throwsMatch(function () { boardUpdate({ 번호: other.번호, 제목: '가로채기' }, STAFF_TOKEN); }, '본인이 쓴 글만', '남의 글 수정');
  throwsMatch(function () { boardDelete({ 번호: other.번호 }, STAFF_TOKEN); }, '본인이 쓴 글만', '남의 글 삭제');
  // 내가 쓴 글은 수정·삭제 가능
  var mine = boardList({ 구분: '자유' }, STAFF_TOKEN).items.filter(function (r) { return r.번호 === 1; })[0];
  ok(mine, '내 글 없음');
  eq(mine.수정가능, true, '내 글 수정가능');
  eq(mine.삭제가능, true, '내 글 삭제가능');
  var up = boardUpdate({ 번호: 1, 제목: '수아의원 단가 문의(수정)', 내용: '확인했습니다.' }, STAFF_TOKEN);
  ok(up && up.success, '수정 실패');
  var after = boardList({ 구분: '자유' }, STAFF_TOKEN).items.filter(function (r) { return r.번호 === 1; })[0];
  eq(after.제목, '수아의원 단가 문의(수정)');
  eq(after.내용, '확인했습니다.');
  ok(/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/.test(String(after.수정일시)), '수정일시가 비었거나 형식이 다름: ' + after.수정일시);
  boardDelete({ 번호: other.번호 }, TOKEN);   // 마스터가 정리
});

t('게시판: STAFF 는 공지를 수정·삭제·고정할 수 없다', function () {
  throwsMatch(function () { boardUpdate({ 번호: 2, 제목: '바꿔치기' }, STAFF_TOKEN); }, 'MASTER 권한만', '공지 수정');
  throwsMatch(function () { boardDelete({ 번호: 2 }, STAFF_TOKEN); }, 'MASTER 권한만', '공지 삭제');
  throwsMatch(function () { boardUpdate({ 번호: 2, 고정여부: 'N' }, STAFF_TOKEN); }, 'MASTER 권한만', '공지 고정');
  var forStaff = boardList({ 구분: '공지' }, STAFF_TOKEN).items[0];
  eq(forStaff.수정가능, false, 'STAFF 공지 수정가능');
  eq(forStaff.삭제가능, false, 'STAFF 공지 삭제가능');
  eq(forStaff.고정가능, false, 'STAFF 공지 고정가능');
  var forMaster = boardList({ 구분: '공지' }, TOKEN).items[0];
  eq(forMaster.수정가능, true, 'MASTER 공지 수정가능');
});

t('게시판: MASTER 는 남의 자유 글도 고치고 지울 수 있다', function () {
  var res = boardCreate({ 구분: '자유', 제목: '지울 글', 내용: '내용' }, STAFF_TOKEN);
  var up = boardUpdate({ 번호: res.번호, 제목: '마스터가 고침' }, TOKEN);
  ok(up && up.success, 'MASTER 수정 실패');
  var del = boardDelete({ 번호: res.번호 }, TOKEN);
  ok(del && del.success, 'MASTER 삭제 실패');
  eq(boardList({ 구분: '자유' }, TOKEN).items.filter(function (r) { return r.번호 === res.번호; }).length, 0, '삭제 후 남음');
});

t('게시판: 자유 글에는 상단 고정을 쓸 수 없다', function () {
  var res = boardCreate({ 구분: '자유', 제목: '고정 시도', 내용: '내용' }, TOKEN);
  throwsMatch(function () { boardUpdate({ 번호: res.번호, 고정여부: 'Y' }, TOKEN); }, '공지사항에만', '자유 글 고정');
  boardDelete({ 번호: res.번호 }, TOKEN);
});

t('게시판: 공지 고정을 풀면 최신 순으로 내려간다', function () {
  var res = boardCreate({ 구분: '공지', 카테고리: '특별 수수료율', 제목: '12월 캠페인', 내용: '추가 수수료', 고정여부: 'Y' }, TOKEN);
  eq(boardList({ 구분: '공지' }, TOKEN).items[0].번호, res.번호, '새 공지가 맨 위');
  boardUpdate({ 번호: res.번호, 고정여부: 'N' }, TOKEN);
  var top = boardList({ 구분: '공지' }, TOKEN).items[0];
  eq(top.번호, 2, '고정 글(2번)이 다시 맨 위');
  boardDelete({ 번호: res.번호 }, TOKEN);
});

t('게시판: 없는 글·비정상 번호는 조용히 넘어가지 않고 알린다', function () {
  throwsMatch(function () { boardUpdate({ 번호: 9999, 제목: 'x' }, TOKEN); }, '찾을 수 없', '수정');
  throwsMatch(function () { boardDelete({ 번호: 9999 }, TOKEN); }, '찾을 수 없', '삭제');
});

t('게시판: 글을 지워도 번호는 다시 쓰지 않는다', function () {
  var a = boardCreate({ 구분: '자유', 제목: 'A', 내용: '내용' }, STAFF_TOKEN);
  var b = boardCreate({ 구분: '자유', 제목: 'B', 내용: '내용' }, STAFF_TOKEN);
  ok(b.번호 > a.번호, '번호가 커져야 함');
  boardDelete({ 번호: b.번호 }, TOKEN);
  var c = boardCreate({ 구분: '자유', 제목: 'C', 내용: '내용' }, STAFF_TOKEN);
  ok(c.번호 > b.번호, '지운 번호 재사용: ' + c.번호);
  boardDelete({ 번호: c.번호 }, TOKEN);
  boardDelete({ 번호: a.번호 }, TOKEN);
});

t('게시판: 긴 내용도 저장되고 목록에서 잘리지 않는다', function () {
  var long = [];
  for (var i = 1; i <= 400; i++) long.push(i + '번째 줄 — 이엘파마 캠페인 확인');
  var res = boardCreate({ 구분: '공지', 카테고리: '특별 수수료율', 제목: '긴 공지', 내용: long.join('\n') }, TOKEN);
  ok(res && res.success, '긴 글 저장 실패');
  var item = boardList({ 구분: '공지' }, TOKEN).items.filter(function (r) { return r.번호 === res.번호; })[0];
  eq(item.내용.split('\n').length, 400, '줄 수 보존');
  boardDelete({ 번호: res.번호 }, TOKEN);
});

t('게시판: 45,000자를 넘는 내용은 거절한다', function () {
  throwsMatch(function () {
    boardCreate({ 구분: '공지', 제목: '너무 김', 내용: new Array(45002).join('가') }, TOKEN);
  }, '너무 깁니다', '길이 제한');
});

t('게시판: 한글 검색과 대소문자 섞인 검색', function () {
  var res = boardCreate({ 구분: '공지', 카테고리: '일반 공지', 제목: 'EDI 마감 안내', 내용: '2026.12 EDI까지 정산' }, TOKEN);
  eq(boardList({ 검색: 'edi' }, TOKEN).total >= 1, true, '영문 소문자 검색');
  eq(boardList({ 검색: '마감' }, TOKEN).total >= 1, true, '한글 검색');
  eq(boardList({ 검색: '작성자이름없음' }, TOKEN).total, 0, '없는 검색어');
  boardDelete({ 번호: res.번호 }, TOKEN);
});


// ------------------------------------------------------------------ 19. 처방 셋팅 성분 검색 (v1.14)
t('성분검색: 같은 성분을 여러 제약사 품목으로 묶어 준다', function () {
  var res = searchGuideIngredients({ q: 'atorvastatin' }, TOKEN);
  ok(res && res.total성분 >= 1, '검색 결과 없음');
  var g = res.groups[0];
  ok(g.성분명, '성분명 없음');
  ok(g.items.length >= 2, '품목이 2개 미만: ' + g.items.length);
  ok(g.제약사수 >= 2, '제약사가 한 곳뿐: ' + g.제약사수);
  var makers = {};
  g.items.forEach(function (it) { makers[it.제약사] = true; ok(it.보험코드, '보험코드 없음'); });
  eq(Object.keys(makers).length, g.제약사수, '제약사 수가 다름');
  ok(g.최고수수료율 > 0, '최고 수수료율 없음');
  ok(g.최저약가 > 0, '최저 약가 없음');
});

t('성분검색: 품목은 수수료율 높은 순으로 온다', function () {
  var g = searchGuideIngredients({ q: 'atorvastatin' }, TOKEN).groups[0];
  for (var i = 1; i < g.items.length; i++) {
    ok(Number(g.items[i - 1].수수료율) >= Number(g.items[i].수수료율),
      '수수료율 정렬이 아님: ' + g.items[i - 1].수수료율 + ' < ' + g.items[i].수수료율);
  }
});

t('성분검색: 경구제만 나온다 (주사·수액 제외)', function () {
  var res = searchGuideIngredients({ q: '세프트리악손' }, TOKEN);
  if (res.groups.length) {
    res.groups.forEach(function (g) {
      g.items.forEach(function (it) { ok(dosageFormOf_(it) === '경구', '주사제가 섞여 나옴: ' + it.품목명); });
    });
  }
  var all = searchGuideIngredients({ q: '정' , limit: 40}, TOKEN);
  all.groups.forEach(function (g) {
    g.items.forEach(function (it) { eq(dosageFormOf_(it), '경구', '경구가 아님: ' + it.품목명); });
  });
});

t('성분검색: 제약사 이름으로도 찾고, 그 제약사 품목만 나온다', function () {
  var res = searchGuideIngredients({ q: '한화제약' }, TOKEN);
  ok(res.total성분 >= 1, '제약사 검색 실패');
  res.groups.forEach(function (g) {
    g.items.forEach(function (it) { ok(String(it.제약사).indexOf('한화제약') !== -1, '다른 제약사: ' + it.제약사); });
  });
});

t('성분검색: 성분명·품목명·보험코드 어느 것으로도 찾힌다', function () {
  var byName = searchGuideIngredients({ q: '아토타틴' }, TOKEN);
  ok(byName.total품목 >= 1, '품목명 검색 실패');
  var code = byName.groups[0].items[0].보험코드;
  var byCode = searchGuideIngredients({ q: code }, TOKEN);
  ok(byCode.total품목 >= 1, '보험코드 검색 실패: ' + code);
  eq(byCode.groups[0].items[0].보험코드, code, '보험코드 검색 결과가 다름');
});

t('성분검색: 성분키를 넘기면 그 성분 품목 전체', function () {
  var first = searchGuideIngredients({ q: 'atorvastatin' }, TOKEN).groups[0];
  var byKey = searchGuideIngredients({ 성분키: first.성분키 }, TOKEN);
  ok(byKey.total성분 >= 1, '성분키 조회 실패');
  eq(byKey.성분키, first.성분키, '성분키 에코');
  ok(byKey.groups[0].품목수 >= first.items.length, '품목이 줄어듦');
});

t('성분검색: 빈 검색어는 아무것도 돌려주지 않는다', function () {
  var res = searchGuideIngredients({ q: '   ' }, TOKEN);
  eq(res.total성분, 0);
  eq(res.groups.length, 0);
});

t('성분검색: 로그인 없이는 쓸 수 없다', function () {
  throwsMatch(function () { searchGuideIngredients({ q: 'atorvastatin' }, ''); }, '로그인이 필요', '권한');
});

t('성분검색: STAFF 는 요율등급이 차감된 요율만 본다', function () {
  var master = searchGuideIngredients({ q: 'atorvastatin' }, TOKEN).groups[0];
  var staff = searchGuideIngredients({ q: 'atorvastatin' }, STAFF_TOKEN).groups[0];
  eq(staff.items.length, master.items.length, '품목 수가 다름');
  var lower = 0;
  staff.items.forEach(function (it, i) {
    var m = master.items.filter(function (x) { return x.보험코드 === it.보험코드; })[0];
    if (!m) return;
    ok(Number(it.수수료율) <= Number(m.수수료율), 'STAFF 요율이 더 높음');
    if (Number(it.수수료율) < Number(m.수수료율)) lower++;
  });
  ok(lower > 0, 'STAFF 차감이 하나도 반영되지 않음');
});

t('성분검색: 품목이 많은 성분은 상한까지만 보내고 잘림을 알린다', function () {
  var res = searchGuideIngredients({ q: '정', limit: 5 }, TOKEN);
  ok(res.shown성분 <= 5, '상한을 넘음: ' + res.shown성분);
  ok(res.total성분 >= res.shown성분, '총 성분수보다 많이 보냄');
  res.groups.forEach(function (g) {
    ok(g.items.length <= 45, '성분 품목이 45개를 넘음: ' + g.items.length);
    if (g.잘림) eq(g.items.length, 45, '잘림 표시가 있는데 45개가 아님');
  });
});

// ------------------------------------------------------------------ 결과
var PASSED = RESULTS.filter(function (r) { return r.ok; }).length;
var FAILED = RESULTS.length - PASSED;
__TEST_RESULT__ = JSON.stringify({ passed: PASSED, failed: FAILED, cases: RESULTS });
