# 수메디팜 미니 CRM (PWA)

거래처·주문(매출)·수금·회전일을 **구글 시트**에 그대로 쌓으면서, 폰에서는 **앱처럼** 쓰는 수메디팜 전용 미니 CRM입니다.

- 라이브(현재): **https://cnddmlek-hash.github.io/soomedipharm/crm/**
  (전용 저장소 `soomedipharm-crm`이 만들어지면 https://cnddmlek-hash.github.io/soomedipharm-crm/ 로 옮깁니다. 파일은 그대로 쓰면 됩니다.)
- 화면/기능: 기존 Apps Script 웹앱 v1.1과 동일 (타이핑 검색 자동완성, MASTER/STAFF 로그인, 심평원 확인 + 다처방 TOP5, 거래처 상세 모달, 지난 주문 다시 담기 등)
- 서버: 구글 시트에 붙인 Apps Script 웹앱 (`downloads/Code.gs` → 시트의 Apps Script에 배포)

## 1. 폰에 설치(홈 화면에 추가)

1. 폰 브라우저(크롬/삼성 인터넷)에서 위 라이브 주소를 엽니다.
2. 첫 화면 **🔗 시트 서버 연결하기** 에서 Apps Script 웹앱 주소(끝이 `/exec`)를 붙여넣고 **[연결 테스트] → [저장하고 시작]**.
   - 주소는 그 폰에만 저장되므로, 폰마다 한 번씩만 입력하면 됩니다.
3. 크롬이면 하단 **📲 홈 화면에 추가** 안내 → [추가]. (안 뜨면 메뉴 ⋮ → "앱 설치" / "홈 화면에 추가")
4. 홈 화면 아이콘으로 열면 주소창 없이 전체화면 앱으로 뜹니다.

## 2. 시트 서버(Apps Script) 준비 — 최초 1회

1. 구글 시트 `CSO_미니CRM` → **확장 프로그램 → Apps Script**
2. `Code.gs` 전체를 `downloads/Code.gs`(외부 연동 API 포함본) 내용으로 교체 → 저장
3. **배포 → 배포 관리 → 기존 배포본 수정(✏️)**
   - 설명: 아무거나(예: `PWA 연동`)
   - **버전: 새 버전**
   - **액세스 권한: 모든 사용자** ← PWA가 로그인 없이 호출할 수 있어야 합니다.
     (앱 자체 로그인 `master` / `choi`가 실제 접근을 통제합니다. 시트 데이터는 이 웹앱을 거쳐서만 나갑니다.)
4. **배포** → 나오는 **웹앱 URL**(`https://script.google.com/macros/s/…/exec`)을 복사해 위 1-2 단계에 붙여넣기

> 액세스 권한이 "모든 사용자"가 아니면(예: "Google 계정이 있는 모든 사용자") PWA에서 연결이 되지 않습니다.
> 시트를 직접 공유할 필요는 없습니다. 시트는 본인 계정만 열 수 있게 두세요.

## 3. 앞으로 화면/기능을 고칠 때

이 저장소(`main` 브랜치 루트)에 push하면 GitHub Pages가 1~2분 안에 자동 반영합니다.
서비스워커가 **네트워크 우선**이라, 앱을 다시 열면 새 화면이 바로 뜹니다(오프라인일 때만 캐시 사용).

```
index.html   화면 (한 파일에 CSS/JS 포함)
manifest.json  PWA 설정(이름·아이콘·색)
sw.js        서비스워커(업데이트 반영)
icon-*.png   앱 아이콘
tools/make_icons.py  아이콘 재생성 스크립트
```

## 4. 구조

```
[폰 PWA (GitHub Pages)]  --fetch(POST, JSON)-->  [Apps Script 웹앱 /exec]  -->  [구글 시트 CSO_미니CRM]
```

- 요청: `{"fn":"함수명","args":[...],"token":"로그인토큰"}`
- 응답: `{"ok":true,"result":...}` 또는 `{"ok":false,"error":{"code":"...","message":"..."}}`
- 상태 확인: `…/exec?action=ping`
- JSONP 폴백: `…/exec?action=api&fn=…&args=…&token=…&callback=…`
- 기존 Apps Script 화면(HTML 서비스)으로 열면 지금처럼 `google.script.run`으로 동작합니다(같은 코드).

## 5. 주의

- 저장소는 공개이지만 **시트 ID·웹앱 주소·비밀번호는 들어 있지 않습니다.** 웹앱 주소는 각 기기 브라우저(localStorage)에만 저장됩니다.
- 비밀번호는 시트 `사용자` 탭에 평문으로 있으니, 시트 공유 범위는 본인 계정으로만 두세요.
