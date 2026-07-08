# Payment-Rx ROI 대시보드

Novartis CA 지역 Part D 처방 데이터와 2022년 Open Payments 지급 데이터를 결합한 영업팀용 대시보드입니다. 상세 요구사항은 `PRD_Payment-Rx_ROI_Dashboard.md`를 참고하세요. (P0 기능만 포함된 MVP 버전)

## 폴더 구조

```
dashboard/
├── index.html          # 대시보드 메인 페이지
├── assets/
│   ├── style.css
│   └── app.js
├── data/
│   └── data.json        # 사전 집계된 데이터 (아래 스크립트로 생성)
├── scripts/
│   └── build_data.py    # part_d_prescriber.csv + open_payments.csv → data.json 변환 스크립트
└── README.md
```

`data.json`은 원본 CSV(개인정보 포함, 용량 문제)를 그대로 올리는 대신 미리 집계한 결과만 담고 있습니다. 원본 CSV를 갱신할 때는 `scripts/build_data.py` 상단의 경로를 로컬 CSV 위치로 바꾼 뒤 다시 실행해 `data/data.json`을 재생성하면 됩니다.

## 로컬에서 미리보기

```bash
cd dashboard
python3 -m http.server 8000
# 브라우저에서 http://localhost:8000 접속
```

## GitHub Pages 배포 단계

### 1. GitHub 저장소 생성
1. GitHub 로그인 후 우측 상단 `+` → `New repository` 클릭
2. Repository name 입력 (예: `hcp-roi-dashboard`)
3. Public으로 설정 (GitHub Pages 무료 사용을 위해 권장. Private도 유료 플랜에서는 가능)
4. `Create repository` 클릭 (README 등은 생성하지 않아도 무방)

### 2. 로컬 저장소 초기화 및 푸시
`dashboard` 폴더가 있는 위치에서 터미널을 열고 아래 명령을 순서대로 실행합니다. `<GitHub계정>`과 `<저장소이름>`은 실제 값으로 바꿔주세요.

```bash
cd dashboard
git init
git add .
git commit -m "Initial commit: Payment-Rx ROI dashboard MVP"
git branch -M main
git remote add origin https://github.com/<GitHub계정>/<저장소이름>.git
git push -u origin main
```

### 3. GitHub Pages 활성화
1. GitHub 저장소 페이지에서 `Settings` 탭 클릭
2. 좌측 메뉴에서 `Pages` 클릭
3. `Build and deployment` → `Source`를 `Deploy from a branch`로 설정
4. `Branch`를 `main` / `/ (root)`로 선택 후 `Save`
5. 1~2분 후 상단에 `https://<GitHub계정>.github.io/<저장소이름>/` 형태의 URL이 표시되면 배포 완료

### 4. 이후 업데이트 반영 (월별 데이터 갱신 시)
```bash
# data/data.json 재생성 후
git add .
git commit -m "Update data: YYYY-MM"
git push
```
GitHub Pages는 `main` 브랜치에 푸시할 때마다 자동으로 재배포됩니다.

## 데이터/방법론 유의사항 (PRD 참고)

- ROI = 제품별 총 약제비(Tot_Drug_Cst) ÷ 지급총액이며, 순수 매출·이익 지표가 아닙니다.
- 하나의 지급 레코드가 여러 제품에 매핑된 경우 각 제품에 지급액이 전액 중복 반영됩니다.
- 의사 실명·NPI 등 식별정보가 포함되어 있으므로, Public 저장소로 배포 시 사내 데이터 정책 및 Compliance 팀 확인을 권장합니다. 외부 노출이 우려되면 Private 저장소 + GitHub Enterprise/Pro의 Pages 접근 제한 기능을 검토하세요.
