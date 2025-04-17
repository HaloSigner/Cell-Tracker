✅ 1. 다른 Google 계정에서 GCP(Google Cloud Platform)에 로그인
https://console.cloud.google.com/

오른쪽 상단에서 계정 변경 후 원하는 프로젝트 선택 or 새로 생성

✅ 2. Google Sheets API 활성화
Google Sheets API Console

프로젝트 선택 → "활성화" 클릭

✅ 3. 서비스 계정 만들기
IAM & 관리자 > 서비스 계정으로 이동

서비스 계정 만들기 클릭

이름 입력 (예: streamlit-cell-manager)

역할은 Editor 또는 Project > Editor 권장

생성 완료 후 키 추가 > 새 키 만들기 > JSON 선택 → JSON 파일 다운로드

✅ 4. Streamlit secrets.toml에 등록
다운받은 JSON 파일의 내용을 secrets.toml에 아래처럼 저장하세요:

toml
Copy
Edit
[gspread]
type = "service_account"
project_id = "your_project_id"
private_key_id = "..."
private_key = "-----BEGIN PRIVATE KEY-----\\nMIIEvgIBAD...\\n-----END PRIVATE KEY-----\\n"
client_email = "your-service-account@your-project-id.iam.gserviceaccount.com"
client_id = "..."
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "https://www.googleapis.com/robot/v1/metadata/x509/..."
⚠️ private_key에서 줄바꿈은 반드시 \\n으로 변환해야 합니다.

✅ 5. 해당 Google Sheet 공유하기
연동하고자 하는 Google Sheet 문서를 열고:

공유 > 사람 및 그룹 추가 클릭

client_email (예: ...@...iam.gserviceaccount.com) 입력

권한은 편집자로 설정

✅ 6. 코드에서 적용
코드 수정 없이 그대로 사용 가능:

python
Copy
Edit
gc = gspread.service_account_from_dict(st.secrets["gspread"])
sh = gc.open_by_key("문서 ID")
✅ 7. Streamlit Cloud에 배포하는 경우
.streamlit/secrets.toml에 위 정보를 업로드 or 입력해야 함

또는 Streamlit Cloud에서 Secrets 설정 UI에 입력
