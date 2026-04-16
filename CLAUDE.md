# CLAUDE.md — boilerplate-be

이 레포는 **풀스택 개발자를 위한 boilerplate**의 백엔드 서브모듈이다.
상위 레포(`boilerplate-app`)에 FE, 인프라 스크립트, AI 협업 가이드가 함께 있다.

## 스택

- **Runtime**: Python 3.12, AWS Lambda (per-endpoint)
- **API**: API Gateway HTTP v2
- **DB**: DynamoDB (boto3 wrapper — `common/dynamo/`)
- **IaC**: Terraform
- **CI/CD**: GitHub Actions (OIDC)

## 스킬

```
/create-api      → 새 API 엔드포인트 스캐폴딩
/apply-new-tech  → 새 기술 도입 방법 조사·추천
```

## 자주 쓰는 명령어

```bash
make setup      # venv 생성 + 런타임 패키지 설치
make setup-dev  # + 개발 의존성 (pytest, moto) 설치
make local      # 로컬 서버 실행 (Flask, port 5001)
make test       # pytest 실행
make api name=api_post_order domain=order
```

---

## 컨벤션

### ID 생성

**`uuid.uuid4()` 직접 쓰지 않는다.** `common.ids.generate_id` 사용.

```python
from common.ids import generate_id

user_id = generate_id("usr")    # usr_018f3a1c7b4e7abc8xxxxxxxxxxxxxxx
ws_id   = generate_id("ws")     # ws_018f3a1c...
ch_id   = generate_id("ch")     # ch_018f3a1c...
```

이유:
- **시간 정렬**: UUIDv7 기반 (앞 48bit = Unix ms). 문자열 사전순 = 생성 시각 순.
- **가독성**: prefix로 엔티티 즉시 구분 (Stripe 스타일).
- 짧은 prefix (3-letter 권장): `usr`, `ws`, `mem`, `ch`, `log`, `evt`.

> **시계 역전 주의**: NTP 등으로 system time이 뒤로 가면 새 ID가 옛 ID보다 사전순으로 작아질 수 있음. 정렬이 critical하면 별도 timestamp 필드 권장.

### DB 테이블 보호

prod 테이블은 `terraform/shared/databases/main.tf`에서 명시적으로 보호 활성:

```hcl
my_tables = {
  my_domain = {
    hash_key  = "PK"
    range_key = "SK"
    point_in_time_recovery      = true
    deletion_protection_enabled = var.stage == "prod"   # AWS-level 차단
    # ...
  }
}
```

- `deletion_protection_enabled` (AWS-level): terraform destroy도 API에서 거부. **prevent_destroy 우회 케이스(module 통째 제거)도 막는 진짜 마지막 안전핀**.
- `prevent_destroy` (terraform lifecycle): 모듈에서 hardcoded `true`.
- `point_in_time_recovery`: 35일 시점 복원.

dev 테이블은 default false로 자유롭게 리셋 가능.

---

## 진행 현황

boilerplate-be 설계 과정에서 결정하고 구현한 내용의 체크리스트.

### 인프라 / 배포

- [x] **Lambda per-endpoint 아키텍처** — endpoint별 독립 zip, 독립 배포
- [x] **API Gateway HTTP v2** — `shared/api_gateway/`, CORS 설정 포함
- [x] **DynamoDB 모듈** — `modules/dynamodb/`, GSI/LSI/TTL/PITR 지원
- [x] **SQS 모듈** — `modules/sqs/`, FIFO + DLQ 자동 생성 지원 (모듈만 있음, 실사용 없음)
- [x] **GitHub Actions OIDC 인증** — `global/` 최초 1회 → 이후 `apply.yml`이 OIDC로 assume
- [x] **닭-달걀 문제 해결** — IAM Role을 `global/main.tf`로 이동, `for_each stages`로 dev/prod 동시 생성
- [x] **인크리멘털 빌드 캐시** — SHA256 비교 → 변경된 endpoint만 재빌드, `actions/cache@v4`
- [x] **Lambda Layer 분리** — requirements Layer + common 코드 Layer
- [x] **per-stage 배포** — dev(dev 브랜치) / prod(main 브랜치) 자동 배포
- [x] **AWS AppRegistry** — dev/prod 앱 단위 리소스 그룹핑, `awsApplication` 태그 전파, 콘솔 등록 확인 완료
- [x] **커스텀 도메인 Terraform 자동화** — ACM wildcard + Route53 A alias + API Gateway 커스텀 도메인. setup.sh에서 1회 생성 후 Terraform data source로 참조 (destroy 안전)
- [x] **OIDC Provider → data source 전환** — setup.sh에서 AWS CLI로 1회 생성, Terraform destroy로 삭제되지 않음
- [x] **Terraform destroy 워크플로우** — 브랜치 기반 stage 감지, `confirm: yes` 입력 필수, prod environment 승인 필요
- [x] **DynamoDB prevent_destroy 제거** — destroy 워크플로우와 충돌 해결. confirm + environment 승인으로 보호
- [x] **main 브랜치 보호** — PR 없이 push 불가 (admin bypass 가능)
- [x] **prod environment 승인** — destroy.yml의 prod 실행 시 required reviewer 승인 필요
- [ ] **CloudFront** — FE S3 호스팅 전환 또는 WAF/글로벌 레이턴시 필요 시점에 도입
- [ ] **ECR 기반 컨테이너 Lambda** — ML/대용량 라이브러리 필요 시 `boilerplate-be-ecr` 별도 레포로 분리 예정

### 애플리케이션 구조

- [x] **ResponseHandler 데코레이터** — `@ResponseHandler.api`, `(status, data)` 반환 컨벤션
- [x] **error_id 포함 에러 응답** — UUID 기반, CloudWatch 연동 디버깅
- [x] **HttpError 계층** — `NotFoundError`, `BadRequestError`, `UnauthorizedError` 등
- [x] **Flask 로컬 개발 서버** — `app/api/` 자동 탐색 라우트 등록, `make local`
- [x] **request_util** — `parse_event`, `get_path_params`, `get_query_params`
- [ ] **JWT 인증 미들웨어** — app-level JWT 검증 데코레이터 (`@require_auth`), 토큰 발급/갱신
- [x] **페이지네이션 유틸** — opaque cursor (base64) 기반, 모든 query/scan 에 내장
- [x] **DynamoDB 모델 프레임워크** — pydantic 기반 `DynamoModel` + 중첩 `GSI`
      키 템플릿(`KEY@value#...`), Active Record API, 자동 GSI 컬럼 생성.
      규격: `DynamoConcept.md`. 모델: `common/models/{user,group,member}.py`

### 개발 경험 (DX)

- [x] **`make api`** — handler.py 스캐폴딩 (`make api name=api_post_order domain=order`)
- [x] **`make diff-all`** — 변경된 endpoint 확인 (빌드 없이)
- [x] **`/create-api` Claude skill** — handler.py + terraform domains Lambda 항목 동시 생성
- [x] **`/apply-new-tech` Claude skill** — 새 기술 도입 방법 조사·추천
- [x] **`make test`** — pytest + moto(DynamoDB) 기반 단위/통합 테스트 (`make setup-dev`)
- [ ] **로컬 DynamoDB** — DynamoDB Local 컨테이너 연동 (`make local-db`)

### 운영 / 관찰가능성

- [x] **CloudWatch 로그 그룹** — Lambda별 사전 생성, retention 14일
- [x] **X-Ray PassThrough** — 기본 설정 (비용 절감)
- [ ] **X-Ray Active 트레이싱** — 필요 시 `tracing_mode = "Active"`로 전환
- [ ] **CloudWatch 알람** — Lambda 에러율, DynamoDB 용량 경보
- [ ] **WAF** — API Gateway 앞단 보호 (필요 시점에 도입)

### Pending 작업

1. **boilerplate-fe 작업** — CloudFront + S3 + GitHub Actions CI/CD
2. **JWT 인증 미들웨어** — app-level, `@require_auth` 데코레이터 + 토큰 발급/갱신
3. **CloudWatch 알람** — Lambda 에러율 + DynamoDB 용량 경보
