#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
영문 성분명 → 한글 발음 사전 생성기 (v1.22)
--------------------------------------------------------------------
index.html 안의  /* ING_KO_START */ … /* ING_KO_END */  구역에
`const ING_KO_DICT_ = { 'amlodipine': '암로디핀', … }` 를 다시 씁니다.

사전의 출처
  1) 구글 시트 `CSO_미니CRM` 의 `성분사전`(성분명·영문키) · `진료과성분`(성분명·영문키)
     → tools/fixtures/ingredient_pairs.json (2026-11-28 gog 로 읽어 저장)
  2) `이엘파마품목`(9,106행) · `제품마스터`(212행)의 성분명에 실제로 나오는 염기·복합 성분 중
     시트에 한글명이 없는 것 → 아래 CURATED 에 손으로 적은 통용 한글 발음
  3) 그래도 없는 희귀 성분은 앱 안의 음차 변환 폴백(ingKoTranslit_)이 처리합니다.

사용:
    python3 tools/build_ing_dict.py            # index.html 의 사전 구역 다시 쓰기
    python3 tools/build_ing_dict.py --check    # 파일과 index.html 이 같은지만 확인
"""
import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(HERE)
INDEX = os.path.join(PROJECT, 'index.html')
PAIRS = os.path.join(HERE, 'fixtures', 'ingredient_pairs.json')

START = '/* ING_KO_START */'
END = '/* ING_KO_END */'

# ---------------------------------------------------------------------------
# 손으로 적은 통용 한글 발음 (시트 `성분사전` 에 한글명이 없는 성분)
#   · 이엘파마품목 9,106행·제품마스터 212행의 성분명에서 뽑은 염기 성분 기준
#   · 값은 괄호 안 설명을 뺀 짧은 통용 발음 (예: 아스코르브산(비타민C) → 아스코르브산)
# ---------------------------------------------------------------------------
CURATED = {
    # --- 고혈압·이상지질혈증 ------------------------------------------------
    'valsartan': '발사르탄',
    'hydrochlorothiazide': '히드로클로로티아지드',
    'hct': '히드로클로로티아지드',
    'olmesartan': '올메사르탄',
    'olmesartan medoxomil': '올메사르탄',
    'candesartan': '칸데사르탄',
    'candesartan cilexetil': '칸데사르탄',
    'irbesartan': '이르베사르탄',
    'ibesartan': '이르베사르탄',
    'fimasartan': '피마사르탄',
    'pitavastatin': '피타바스타틴',
    'simvastatin': '심바스타틴',
    'pravastatin': '프라바스타틴',
    'felodipine': '펠로디핀',
    'lercanidipine': '레르카니디핀',
    'benidipine': '베니디핀',
    'azelnidipine': '아젤니디핀',
    'cilnidipine': '실니디핀',
    'nifedipine': '니페디핀',
    's-amlodipine': '에스암로디핀',
    'carvedilol': '카르베딜롤',
    'bisoprolol': '비소프롤롤',
    'nebivolol': '네비볼롤',
    'atenolol': '아테놀롤',
    'carteolol': '카르테올롤',
    'enalapril': '에날라프릴',
    'captopril': '캡토프릴',
    'cilazapril': '실라자프릴',
    'chlorthalidone': '클로르탈리돈',
    'indapamide': '인다파미드',
    'torasemide': '토라세미드',
    'spironolactone': '스피로놀락톤',
    'doxazosin': '독사조신',
    'terazosin': '테라조신',
    'naftopidil': '나프토피딜',
    'alfuzosin': '알푸조신',
    'tamsulosin': '탐스로신',
    'silodosin': '실로도신',
    'diltiazem': '딜티아젬',
    'etoricoxib': '에토리콕시브',
    'clopidogrel bisulfate': '클로피도그렐',
    'clopidogrel camsylate': '클로피도그렐',
    'cilostazol': '실로스타졸',
    'sarpogrelate': '사르포그렐레이트',
    'rivaroxaban': '리바록사반',
    'micronized rivaroxaban': '리바록사반',
    'edoxaban': '에독사반',
    'apixaban': '아픽사반',
    'diosmin': '디오스민',
    'triflusal': '트리플루살',
    'ticlopidine': '티클로피딘',
    'limaprost': '리마프로스트',
    'beraprost': '베라프로스트',
    'fenofibrate': '페노피브레이트',
    'fenofibrate granule': '페노피브레이트',
    'micronized fenofibrate': '페노피브레이트',
    'choline fenofibrate': '페노피브레이트',
    'fenofibric acid': '페노피브린산',
    'ezetimibe': '에제티미브',
    'omega-3-acid ethyl esters': '오메가3산에틸에스테르',
    'omega- -acid ethyl esters': '오메가3산에틸에스테르',
    'icosapent ethyl': '이코사펜트에틸',
    'deflazacort': '데플라자코르트',

    # --- 당뇨·대사 ----------------------------------------------------------
    'glimepiride': '글리메피리드',
    'dapagliflozin': '다파글리플로진',
    'dapagliflozin propanediol': '다파글리플로진',
    'dapagliflozin lactose mixture': '다파글리플로진',
    'dapagliflozin bis l-proline': '다파글리플로진',
    'dapagliflozin citric acid': '다파글리플로진',
    'enavogliflozin': '에나보글리플로진',
    'linagliptin': '리나글립틴',
    'vildagliptin': '빌다글립틴',
    'teneligliptin': '테네리글립틴',
    'teneligliptin ditosylate': '테네리글립틴',
    'teneligliptin hydrobromide': '테네리글립틴',
    'alogliptin': '알로글립틴',
    'alogliptin benzoate': '알로글립틴',
    'pioglitazone': '피오글리타존',
    'miglitol': '미글리톨',
    'metformin colloidal silicon dioxide': '메트포르민',
    'metformin hcl': '메트포르민',

    # --- 소화기·위염 --------------------------------------------------------
    'lansoprazole': '란소프라졸',
    's-pantoprazole': '에스판토프라졸',
    'fexuprazan': '펙수프라잔',
    'roxatidine': '록사티딘',
    'cimetidine': '시메티딘',
    'levosulpiride': '레보설피리드',
    'tiropramide': '티로프라미드',
    'irsogladine': '이르소글라딘',
    'diacerein': '디아세레인',
    'trimebutine s.r.': '트리메부틴',
    'octylonium': '옥틸로늄',
    'almagate': '알마게이트',
    'polaprezinc': '폴라프레진크',
    'misoprostol': '미소프로스톨',
    'racecadotril': '라세카도트릴',
    'dioctahedral smectite': '디옥타헤드랄스멕타이트',
    'polycarbophil': '폴리카르보필',
    'alginate': '알긴산',
    'alginic acid': '알긴산',
    'macrogol': '마크로골',
    'polyethylene glycol': '폴리에틸렌글리콜',
    'lactulose concentrate': '락툴로오스',
    'bisacodyl': '비사코딜',
    'picosulfate': '피코술페이트',
    'docusate': '도큐세이트',
    'sennoside': '센노사이드',
    'ursodesoxycholic acid': '우르소데옥시콜산',
    'chenodesoxycholic acid': '케노데옥시콜산',
    'pancreatin': '판크레아틴',
    'pancrease powder': '판크레아틴',
    'pancreatin enteric coated granule': '판크레아틴',
    'diastase protease cellulase': '소화효소제',
    'biodiastase': '비오디아스타제',
    'cellulase': '셀룰라아제',
    'hemicellulase': '헤미셀룰라아제',
    'lipase': '리파제',
    'scopolia extract': '스코폴리아엑스',
    'ox bile extract': '우담즙엑스',
    'simethicone': '시메티콘',
    'dimethicone': '디메티콘',
    'phloroglucinol': '플로로글루시놀',
    'oxethazaine': '옥세타자인',
    'alverine': '알베린',
    'spherical adsorptive carbon': '구형흡착탄',
    'bismuth subsalicylate': '비스무트살리실레이트',
    'glycyrrhiza powder': '감초분말',
    'green tea powder': '녹차분말',
    'orthosiphon powder': '오르토시폰분말',

    # --- 호흡기·알레르기 ----------------------------------------------------
    'acebrophylline': '아세브로필린',
    'doxofylline': '독소필린',
    'erdosteine': '에르도스테인',
    'sobrerol': '소브레롤',
    'levodropropizine': '레보드로프로피진',
    'tulobuterol': '툴로부테롤',
    'bambuterol': '밤부테롤',
    'clenbuterol': '클렌부테롤',
    'formoterol': '포모테롤',
    'micronized formoterol': '포모테롤',
    'salmeterol': '살메테롤',
    'montelukast': '몬테루카스트',
    'epinastine': '에피나스틴',
    'bepotastine': '베포타스틴',
    'bepotastine salicylate': '베포타스틴',
    'bepotastine nicotinate': '베포타스틴',
    'ebastine': '에바스틴',
    'fexofenadine': '펙소페나딘',
    'loratadine': '로라타딘',
    'ketotifen': '케토티펜',
    'rupatadine': '루파타딘',
    'triprolidine': '트리프롤리딘',
    'doxylamine': '독실아민',
    'dimenhydrinate': '디멘히드리네이트',
    'diphenhydramine': '디펜히드라민',
    'hydroxyzine': '하이드록시진',
    'guaifenesin': '구아이페네신',
    'benzonatate': '벤조나테이트',
    'dihydrocodeine': '디히드로코데인',
    'dl-methylephedrine': '메틸에페드린',
    'ephedrine': '에페드린',
    'phenylephrine': '페닐레프린',
    'caffeine': '카페인',
    'theobromine': '테오브로민',
    'tranilast': '트라닐라스트',
    'cromoglicate': '크로모글리케이트',
    'beclomethasone': '베클로메타손',
    'budesonide': '부데소니드',
    'fluticasone': '플루티카손',
    'mometasone': '모메타손',
    'mometasone furoate': '모메타손푸로에이트',
    'prednisolone': '프레드니솔론',
    'prednicarbate': '프레드니카르베이트',
    'levo-cloperastine fendizoate': '레보클로페라스틴',
    'hederae helix fluid': '아이비엽엑스',
    'ivy leaf': '아이비엽엑스',
    'ivy leaf ethanol dry ext': '아이비엽엑스',
    'ivy leaf ethanol dried ext.': '아이비엽엑스',
    'ivy leaf ethanol ext.': '아이비엽엑스',
    'pelargonium sidoides': '펠라르고늄엑스',
    'pelargonium sidoides ethanol extract': '펠라르고늄엑스',

    # --- 감염·항생제 --------------------------------------------------------
    'clavulanate': '클라불란산',
    'clavulanate diluted': '클라불란산',
    'cefprozil': '세프프로질',
    'cefadroxil': '세파드록실',
    'cephradine': '세프라딘',
    'cefmetazole': '세프메타졸',
    'ceftazidime': '세프타지딤',
    'cefotaxime': '세포탁심',
    'ceftriaxone': '세프트리악손',
    'cefaclor': '세파클러',
    'amoxicillin': '아목시실린',
    'sulbactam': '술박탐',
    'pivoxyl sulbactam': '술박탐피복실',
    'tazobactam': '타조박탐',
    'linezolid': '리네졸리드',
    'neomycin': '네오마이신',
    'netilmicin': '네틸마이신',
    'nystatin': '니스타틴',
    'polymyxin b': '폴리믹신B',
    'fosfomycin': '포스포마이신',
    'fosfomycin trometamol': '포스포마이신',
    'rifaximin': '리팍시민',
    'minocycline': '미노사이클린',
    'doxycycline hyclate': '독시사이클린',
    'nadifloxacin': '나디플록사신',
    'levofloxacin': '레보플록사신',
    'oseltamivir': '오셀타미비르',
    'entecavir': '엔테카비르',
    'tenofovir disoproxil': '테노포비르디소프록실',
    'tenofovir disoproxil hemiedisylate': '테노포비르디소프록실',
    'tenofovir alafenamide hemimalate': '테노포비르알라페나미드',
    'tenofovir alafenamide hemifumarate': '테노포비르알라페나미드',
    'adefovir dipivoxil': '아데포비르디피복실',
    'acyclovir': '아시클로버',
    'famciclovir': '팜시클로비르',
    'fluconazole': '플루코나졸',
    'itraconazole': '이트라코나졸',
    'ketoconazole': '케토코나졸',
    'clotrimazole': '클로트리마졸',
    'flutrimazol': '플루트리마졸',
    'efinaconazole': '에피나코나졸',
    'amorolfine': '아모롤핀',
    'butenafine': '부테나핀',
    'ciclopirox olamine': '시클로피록스',
    'permethrin': '퍼메트린',
    'hydroquinone': '하이드로퀴논',
    'hydrous benzoyl peroxide': '벤조일퍼옥사이드',

    # --- 신경·정신·통증 -----------------------------------------------------
    'pregabalin': '프레가발린',
    'gabapentin': '가바펜틴',
    'fluoxetine': '플루옥세틴',
    'tianeptine': '티아넵틴',
    'bupropion': '부프로피온',
    'desvenlafaxine': '데스벤라팍신',
    'desvenlafaxine benzoate': '데스벤라팍신',
    'clomipramine': '클로미프라민',
    'buspirone': '부스피론',
    'eszopiclone': '에스조피클론',
    'melatonin': '멜라토닌',
    'rasagiline': '라사길린',
    'ropinirole': '로피니롤',
    'carbidopa': '카르비도파',
    'entacapone': '엔타카폰',
    'amantadine': '아만타딘',
    'donepezil': '도네페질',
    'galantamine': '갈란타민',
    'galantamine hydrobromide': '갈란타민',
    'memantine': '메만틴',
    'risperidone': '리스페리돈',
    'olanzapine': '올란자핀',
    'amisulpride': '아미설프라이드',
    'quetiapine': '쿠에티아핀',
    'naltrexone': '날트렉손',
    'sumatriptan': '수마트립탄',
    'naratriptan': '나라트립탄',
    'dapoxetine': '다포세틴',
    'tizanidine': '티자니딘',
    'baclofen': '바클로펜',
    'orphenadrine': '오르페나드린',
    'chlorphenesin carbamate': '클로르페네신카바메이트',
    'trimetazidine': '트리메타지딘',
    'nicergoline': '니세르골린',
    'kallidinogenase': '칼리디노게나제',
    'citrulline malate': '시트룰린',
    'thiamine': '티아민',
    'benfotiamine': '벤포티아민',
    'bisbenthiamine': '비스벤티아민',
    'bisbentiamine': '비스벤티아민',
    'fursultiamine': '푸르설티아민',
    'mecobalamin': '메코발라민',
    'cyanocobalamin': '시아노코발라민',
    'nicotinamide': '니코틴아미드',
    'pantothenate': '판토텐산',
    'tocopherol': '토코페롤',
    'biotin': '비오틴',
    'd-biotin': '비오틴',
    'folic acid': '엽산',
    'vitc': '비타민C',
    'vitb': '비타민B',
    'vitb2': '비타민B2',
    'vitb6': '비타민B6',
    'cholecalciferol': '콜레칼시페롤',
    'cholecalciferol concentrated': '콜레칼시페롤',
    'cholecalciferol concentrated powder': '콜레칼시페롤',
    'cholecalciferol concentrated granule': '콜레칼시페롤',
    'cholecalciferol granule': '콜레칼시페롤',
    'alfacalcidol': '알파칼시돌',
    'calcitriol': '칼시트리올',
    'calcipotriol': '칼시포트리올',
    'keratin': '케라틴',
    'hyaluronate': '히알루론산',
    'sodium hyaluronate': '히알루론산나트륨',
    'l-cystine': '시스틴',
    'l-cystein': '시스테인',
    'medicinal yeast': '건조효모',
    'p-amino benzoic acid': '파라아미노벤조산',
    'l-isoleucine': '이소류신',
    'l-leucine': '류신',
    'l-valine': '발린',
    'manganese': '망간',
    'selenium': '셀렌',
    'selenite pentahydrate': '아셀렌산나트륨',
    'selenium in dried yeast': '셀렌',
    'chromium': '크롬',
    'chromium in dried yeast': '크롬',
    'ammonium': '암모늄',
    'zinc': '아연',

    # --- 비뇨·생식·호르몬 ---------------------------------------------------
    'propiverine': '프로피베린',
    'tolterodine': '톨터로딘',
    'tolterodine l-tartrate': '톨터로딘',
    'solifenacin': '솔리페나신',
    'mirabegron': '미라베그론',
    'prucalopride': '프루칼로프라이드',
    'diquafosol': '디쿠아포솔',
    'desmopressin': '데스모프레신',
    'dienogest': '디에노게스트',
    'drospirenone': '드로스피레논',
    'ethinyl estradiol': '에티닐에스트라디올',
    'micronized progesterone': '프로게스테론',
    'megestrol': '메게스트롤',
    'tibolone': '티볼론',
    'raloxifene': '랄록시펜',
    'bazedoxifene': '바제독시펜',
    'ulipristal': '울리프리스탈',
    'finasteride': '피나스테리드',
    'dutasteride': '두타스테리드',
    'minoxidil': '미녹시딜',
    'tadalafil': '타다라필',
    'sildenafil': '실데나필',
    'apremilast': '아프레밀라스트',
    'leflunomide': '레플루노마이드',
    'tofacitinib': '토파시티닙',
    'mycophenolate mofetil': '미코페놀레이트모페틸',
    'sevelamer': '세벨라머',
    'cinacalcet': '시나칼셋',
    'deferasirox': '데페라시록스',
    'polystyrene sulfonate': '폴리스티렌술폰산',
    'bicalutamide': '비칼루타미드',
    'enzalutamide': '엔잘루타미드',
    'pirfenidone': '피르페니돈',

    # --- 안과·피부·외용 -----------------------------------------------------
    'fluorometholone': '플루오로메톨론',
    'latanoprost': '라타노프로스트',
    'pilocarpine': '필로카르핀',
    'tetrahydrozoline': '테트라히드로졸린',
    'olopatadine': '올로파타딘',
    'ketorolac tromethamine': '케토롤락',
    'nepafenac': '네파페낙',
    'clobetasol propionate': '클로베타솔',
    'betamethasone dipropionate': '베타메타손',
    'desoxymethasone': '데속시메타손',
    'desonide': '데소니드',
    'diflucortolone valerate': '디플루코르톨론',
    'methylprednisolone aceponate': '메틸프레드니솔론',
    'beclomethasone dipropionate': '베클로메타손',
    'difluprednate': '디플루프레드네이트',
    'pramoxine': '프라목신',
    'benzydamine': '벤지다민',
    'ibuprofen piconol': '이부프로펜',
    'propylene glycol': '프로필렌글리콜',
    'l-menthol': '멘톨',
    'aluminum silicate': '알루미늄규산염',
    'aluminum gel': '알루미늄겔',
    'talc': '탈크',
    'zinc oxide': '산화아연',

    # --- 소염·진통·근이완 ---------------------------------------------------
    'aceclofenac': '아세클로페낙',
    'loxoprofen': '록소프로펜',
    'zaltoprofen': '잘토프로펜',
    'naproxen': '나프록센',
    'nabumetone': '나부메톤',
    'morniflumate': '모르니플루메이트',
    'talniflumate': '탈니플루메이트',
    'polmacoxib': '폼마콕시브',
    'eicosapent': '이코사펜트',
    'microencapsulated acetaminophen': '아세트아미노펜',
    'acetaminophen': '아세트아미노펜',
    'tramadol': '트라마돌',
    'epinastine hcl': '에피나스틴',

    # --- 수액·주사·기타 -----------------------------------------------------
    'carboxymethylcellulose': '카르복시메틸셀룰로오스',
    'ketorolac': '케토롤락',
    'r-thioctic acid tromethamine': '티옥트산',
    'thioctic acid': '티옥트산',
    'dobesilate': '도베실레이트',
    'dihydroergotamine': '디히드로에르고타민',
    'lipase ap6': '리파제',
    'safflower oil': '홍화유',
    'whey': '유청',
    'inosiplex': '이노시플렉스',
    'phase': '페이즈',
    'standardized lyophilized mixed bacterial lysates': '세균용해물',
    'bacillus licheniformis': '바실루스리케니포르미스',
    'bacillus subtilis': '바실루스서브틸리스',
    'clostridium butyricum': '클로스트리디움부티리쿰',
    'clostridium butyricum toa': '클로스트리디움부티리쿰',
    'enterococcus faecium': '엔테로코쿠스페시움',
    'lactobacillus acidophilus': '락토바실루스아시도필루스',
    'lactobacillus casei': '락토바실루스카세이',
    'lactobacillus casei variety rhamnosus': '락토바실루스카세이',
    'saccharomyces boulardii': '사카로마이세스불라르디',
    'dizet': '디젯',
    'methylol cephalexin lysinate': '세팔렉신',
    'helicobacter pylori': '헬리코박터파일로리',
    'spherical carbon': '구형흡착탄',

    # --- 생약·추출물 --------------------------------------------------------
    'ginkgo leaf dried extract': '은행엽엑스',
    'ginkgo leaf extract': '은행엽엑스',
    'milk thistle fruit dried extract': '밀크시슬엑스',
    'milk thistle extract': '밀크시슬엑스',
    'artemisia asiatica ethanol extract': '애엽엑스',
    'artemisia asiatica': '애엽엑스',
    'artemisia herb isopropanol soft extract': '애엽엑스',
    'aloe extract': '알로에엑스',
    'ginseng ethanol dried extract': '인삼엑스',
    'cnidium rhizome dried extract': '천궁엑스',
    'cimicifuga fluid extract': '승마엑스',
    'hyperici methanol extract': '서양고추나물엑스',
    'hyperici dried extract': '서양고추나물엑스',
    'saposhnikoviae radix': '방풍엑스',
    'titrated extract of centella asiatica': '병풀엑스',
    'purified and micronized flavonoid fraction': '플라보노이드분획',
    'powdered red clover extract': '레드클로버엑스',
    'bilberry fruit dried ext.': '빌베리엑스',
    'basic fuchsin': '염기성푸크신',

    # --- 희귀·복합 성분 (이엘파마품목·제품마스터 성분명에 실제로 나오는 것) ----
    'biphenyl dimethyl dicarboxylate': '비페닐디메틸디카르복실레이트',
    'adefovir': '아데포비르',
    'tenofovir': '테노포비르',
    'camostat': '카모스타트',
    'cefditoren': '세프디토렌',
    'cefpodoxime': '세프포독심',
    'ciclopirox': '시클로피록스',
    'clobetasol': '클로베타솔',
    'diflucortolone': '디플루코르톨론',
    'midodrine': '미도드린',
    'mycophenolate': '미코페놀레이트',
    'pentosan polysulfate': '펜토산폴리설페이트',
    'r-thioctic acid': '티옥트산',
    'triamcinolone': '트리암시놀론',
    'varenicline': '바레니클린',
    'alitretinoin': '알리트레티노인',
    'diethylpropion': '디에틸프로피온',
    'phendimetrazine': '펜디메트라진',
    'methylol cephalexin': '세팔렉신',
    'ivy': '아이비엽',
    'cyclosporine': '사이클로스포린',
    'ammonium chloride': '염화암모늄',
    'calcium citrate hydrate': '구연산칼슘',
    'calcium citrate': '구연산칼슘',
    'calcium pantothenate': '판토텐산칼슘',
    'zinc sulfate hydrate': '황산아연',
    'magnesium trihydrate': '마그네슘',
    'calcium carbonate': '탄산칼슘',
    'precipitated calcium carbonate': '탄산칼슘',
    'magnesium oxide': '산화마그네슘',
    'magnesium hydroxide': '수산화마그네슘',
    'aluminum magnesium silicate': '알루미늄규산마그네슘',
    'dimethyl fumarate': '디메틸푸마레이트',
    'l ornithine l aspartate': 'L-오르니틴-L-아스파르트산',
    'dl methylephedrine': '메틸에페드린',
    's amlodipine': '에스암로디핀',
    'r thioctic acid': '티옥트산',
    'l cystine': '시스틴',
    'l cystein': '시스테인',
    'l arginine': 'L-아르기닌',
    'l carnitine': 'L-카르니틴',
    'l isoleucine': '이소류신',
    'l leucine': '류신',
    'l valine': '발린',
    'l menthol': '멘톨',
    'levo cloperastine fendizoate': '레보클로페라스틴',
    'lipase ap': '리파제',
    'sodium carbonate hydroxide': '탄산수소나트륨',
    'coptidis rhizoma': '황련엑스',
    'lactobacillus casei rhamnosus': '락토바실루스카세이',
    'omega acid ethyl esters': '오메가3산에틸에스테르',
    'omega 3 acid ethyl esters': '오메가3산에틸에스테르',
    'ivy leaf': '아이비엽엑스',
    'hyaluronic acid': '히알루론산',
    'hyaluronate': '히알루론산',
}

# 시트·이엘파마 데이터에 있으나 위 CURATED 로는 짧게 줄이기 어려운 복합 생약·특수 품목은
# 음차 폴백에 맡깁니다(빈 괄호가 생기지 않게 아예 표기하지 않는 편이 낫습니다).


def norm_key(s):
    """사전 키 정규화 — 소문자·공백 하나로."""
    s = str(s or '').strip().lower()
    s = s.replace('.', '')
    s = re.sub(r'\s+', ' ', s)
    return s


def clean_value(v):
    """표시용으로 괄호 설명을 뺍니다 (예: 아스코르브산(비타민C) → 아스코르브산)."""
    v = str(v or '').strip()
    v = re.sub(r'\([^)]*\)', '', v).strip()
    v = re.sub(r'\s+', ' ', v)
    return v


def build_dict():
    pairs = {}
    if os.path.exists(PAIRS):
        data = json.load(open(PAIRS, encoding='utf-8'))
        pairs = data.get('pairs', {})
    merged = {}
    for k, v in pairs.items():
        key = norm_key(k)
        val = clean_value(v)
        if key and val:
            merged[key] = val
    for k, v in CURATED.items():
        key = norm_key(k)
        val = clean_value(v)
        if key and val:
            merged[key] = val
    return merged


def js_block(mapping):
    items = ['%s: %s' % (json.dumps(k, ensure_ascii=False), json.dumps(v, ensure_ascii=False))
             for k, v in sorted(mapping.items())]
    lines = []
    for i in range(0, len(items), 4):
        lines.append('     ' + ', '.join(items[i:i + 4]))
    return (START + '\n' +
            '   // 영문 성분명 → 한글 발음 (tools/build_ing_dict.py 가 만듭니다. 손으로 고치지 마세요)\n' +
            '   const ING_KO_DICT_ = {\n' + ',\n'.join(lines) + '\n   };\n' +
            '   ' + END)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--index', default=INDEX, help='index.html 경로')
    ap.add_argument('--check', action='store_true', help='고치지 않고 같은지만 확인')
    args = ap.parse_args()

    mapping = build_dict()
    html = open(args.index, encoding='utf-8').read()
    new_block = js_block(mapping)
    pattern = re.compile(re.escape(START) + r'.*?' + re.escape(END), re.S)
    if not pattern.search(html):
        sys.exit('index.html 에 %s … %s 구역이 없습니다.' % (START, END))

    if args.check:
        old = pattern.search(html).group(0)
        if old.strip() == new_block.strip():
            print('사전 구역이 같습니다 (%d개 성분).' % len(mapping))
            return
        sys.exit('사전 구역이 다릅니다 — python3 tools/build_ing_dict.py 로 다시 만드세요.')

    open(args.index, 'w', encoding='utf-8').write(pattern.sub(lambda m: new_block, html, count=1))
    print('사전 %d개 성분을 index.html 에 넣었습니다.' % len(mapping))


if __name__ == '__main__':
    main()
