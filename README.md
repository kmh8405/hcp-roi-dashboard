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
│   └── data.json        # 사전 집계된 데이터 (Supabase에서 아래 스크립트로 생성)
├── build_data.py         # Supabase(Postgres) → data.json 변환 스크립트
├── scripts/
│   └── build_data.py    # build_data.py와 동일 (중복 파일, 로직 변경 시 둘 다 수정)
├── requirements.txt      # psycopg2-binary (build_data.py 실행에 필요)
├── .github/workflows/
│   └── refresh-data.yml # 매일 자동으로 data.json을 재생성/커밋하는 GitHub Actions
└── README.md
```

`data.json`은 원본 데이터(개인정보 포함)를 그대로 올리는 대신 미리 집계한 결과만 담고 있습니다. 원본 데이터는 CSV가 아니라 **Supabase(Postgres)** 에 저장되어 있고, `build_data.py`가 `DATABASE_URL` 환경변수로 접속해 두 테이블(`part_d_prescriber`, `open_payments`)을 쿼리한 뒤 `data/data.json`을 재생성합니다.

- 최초 1회, `part_d_prescriber.csv`/`open_payments.csv`를 Supabase 두 테이블로 이관(COPY)해 두었습니다. 이관이 끝난 뒤에는 스크립트가 더 이상 로컬 CSV 파일을 참조하지 않으므로, 원본 CSV 파일을 이동/삭제/경로 변경해도 파이프라인에는 영향이 없습니다.
- Supabase 테이블에 새 데이터가 들어오면(수동 업로드, 별도 ETL 등 방식은 무관) 아래 GitHub Actions가 매일 자동으로 `data.json`을 재생성해 커밋합니다.

### 데이터 자동 갱신 (GitHub Actions)

`.github/workflows/refresh-data.yml`이 다음을 수행합니다.

- 매일 06:00 KST(cron `0 21 * * *`, UTC 기준)에 자동 실행 + `Actions` 탭에서 수동 실행(`workflow_dispatch`)도 가능
- `requirements.txt` 설치 → `DATABASE_URL` 시크릿으로 Supabase 접속 → `build_data.py` 실행 → `data/data.json`이 바뀌었으면 자동 커밋·푸시
- GitHub Pages는 `main` 브랜치 루트를 서빙하므로, 푸시되면 대시보드도 자동으로 최신 데이터로 갱신됩니다

Supabase 연결 정보는 저장소 `Settings → Secrets and variables → Actions`에 `DATABASE_URL` 이름으로 등록되어 있습니다(Connection Pooler URI 형식). 비밀번호를 변경하면 이 시크릿 값도 함께 갱신해야 합니다.

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

### 4. 이후 업데이트 반영

데이터 갱신은 위 GitHub Actions(`refresh-data.yml`)가 자동으로 처리합니다. Supabase에 새 데이터를 넣어두면 다음 스케줄에 자동 반영되고, 즉시 반영이 필요하면 저장소 `Actions` 탭 → `Refresh dashboard data` → `Run workflow`로 수동 실행할 수 있습니다.

로컬에서 직접 재생성하고 싶다면 (비밀번호가 쉘 히스토리에 남지 않도록 `.env` 파일 사용을 권장합니다. `.env`는 `.gitignore`에 포함되어 있습니다):
```bash
cd dashboard
pip install -r requirements.txt
echo 'DATABASE_URL=<Supabase Connection Pooler URI>' > .env
set -a && source .env && set +a
python3 build_data.py
git add data/data.json
git commit -m "Update data: YYYY-MM"
git push
```
GitHub Pages는 `main` 브랜치에 푸시할 때마다 자동으로 재배포됩니다.

## 데이터/방법론 유의사항 (PRD 참고)

- ROI = 제품별 총 약제비(Tot_Drug_Cst) ÷ 지급총액이며, 순수 매출·이익 지표가 아닙니다.
- 하나의 지급 레코드가 여러 제품에 매핑된 경우 각 제품에 지급액이 전액 중복 반영됩니다.
- 의사 실명·NPI 등 식별정보가 포함되어 있으므로, Public 저장소로 배포 시 사내 데이터 정책 및 Compliance 팀 확인을 권장합니다. 외부 노출이 우려되면 Private 저장소 + GitHub Enterprise/Pro의 Pages 접근 제한 기능을 검토하세요.
