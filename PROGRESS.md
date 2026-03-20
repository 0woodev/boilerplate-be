# BE 레포 설계 진행 현황

boilerplate-be 설계 과정에서 결정하고 구현한 내용의 체크리스트.
다음 대화 시 이 파일을 참고해서 이어서 작업한다.

---

## 인프라 / 배포

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
- [x] **커스텀 도메인 Terraform 자동화** — ACM wildcard(`*.wooapps.net`) + Route53 A alias + API Gateway 커스텀 도메인. setup.sh에서 1회 생성 후 Terraform data source로 참조 (destroy 안전)
- [x] **OIDC Provider → data source 전환** — setup.sh에서 AWS CLI로 1회 생성, Terraform destroy로 삭제되지 않음
- [x] **Terraform destroy 워크플로우** — 브랜치 기반 stage 감지 (dev→dev, main→prod), `confirm: yes` 입력 필수, prod environment 승인 필요
- [x] **DynamoDB prevent_destroy 제거** — destroy 워크플로우와 충돌 해결. confirm + environment 승인으로 보호
- [x] **main 브랜치 보호** — PR 없이 push 불가 (admin bypass 가능)
- [x] **prod environment 승인** — destroy.yml의 prod 실행 시 required reviewer 승인 필요
- [ ] **CloudFront** — FE S3 호스팅 전환 또는 WAF/글로벌 레이턴시 필요 시점에 도입
- [ ] **ECR 기반 컨테이너 Lambda** — ML/대용량 라이브러리 필요 시 `boilerplate-be-ecr` 별도 레포로 분리 예정

---

## 애플리케이션 구조

- [x] **ResponseHandler 데코레이터** — `@ResponseHandler.api`, `(status, data)` 반환 컨벤션
- [x] **error_id 포함 에러 응답** — UUID 기반, CloudWatch 연동 디버깅
- [x] **HttpError 계층** — `NotFoundError`, `BadRequestError`, `UnauthorizedError` 등
- [x] **Flask 로컬 개발 서버** — `app/api/` 자동 탐색 라우트 등록, `make local`
- [x] **request_util** — `parse_event`, `get_path_params`, `get_query_params`
- [ ] **인증 미들웨어** — JWT / Cognito 기반 인증 (현재 없음)
- [ ] **페이지네이션 유틸** — DynamoDB LastEvaluatedKey 기반 커서 페이지네이션
- [ ] **공통 DynamoDB 헬퍼** — PynamoDB 모델 베이스 클래스 정리

---

## 개발 경험 (DX)

- [x] **`make api`** — handler.py 스캐폴딩 (`make api name=api_post_order domain=order`)
- [x] **`make diff-all`** — 변경된 endpoint 확인 (빌드 없이)
- [x] **`/create-api` Claude skill** — handler.py + terraform domains Lambda 항목 동시 생성
- [ ] **`make test`** — 단위 테스트 실행 환경 (현재 없음)
- [ ] **로컬 DynamoDB** — DynamoDB Local 컨테이너 연동 (`make local-db`)

---

## 운영 / 관찰가능성

- [x] **CloudWatch 로그 그룹** — Lambda별 사전 생성, retention 14일
- [x] **X-Ray PassThrough** — 기본 설정 (비용 절감)
- [ ] **X-Ray Active 트레이싱** — 필요 시 `tracing_mode = "Active"`로 전환
- [ ] **CloudWatch 알람** — Lambda 에러율, DynamoDB 용량 경보
- [ ] **WAF** — API Gateway 앞단 보호 (필요 시점에 도입)

---

## boilerplate-app (루트 레포)

- [x] **setup.sh** — GitHub 레포 생성 + boilerplate 클론/push + submodule 등록 + S3/DynamoDB/OIDC/ACM 생성
- [x] **teardown.sh** — GitHub 레포 삭제 + S3 버킷(전체 버전) 삭제 + DynamoDB 테이블 삭제
- [x] **README.md** — 전체 셋업/배포/삭제 가이드, DNS 전파 주의사항 포함
- [x] **new-app 테스트 및 teardown** — boilerplate 기반 새 프로젝트 생성/배포/삭제 검증 완료

---

## Pending 작업 (다음 대화에서 이어서)

1. **boilerplate-fe 작업** — CloudFront + S3 + GitHub Actions CI/CD (bp-be와 동일한 패턴)
2. **인증 미들웨어** — Lambda Authorizer 또는 Cognito 기반
3. **CloudWatch 알람** — Lambda 에러율 + DynamoDB 용량 경보
