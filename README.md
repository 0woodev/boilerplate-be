# boilerplate-be

Backend boilerplate. [boilerplate-app](https://github.com/0woodev/boilerplate-app)의 `setup.sh`에 의해 새 프로젝트의 `be/` submodule로 복제된다.

## 플레이스홀더

`setup.sh` 실행 시 아래 값들이 자동으로 치환된다.

| 플레이스홀더 | 설명 |
|---|---|
| `{{PROJECT_NAME}}` | 프로젝트 이름 |
| `{{AWS_REGION}}` | AWS 리전 |
| `{{AWS_ACCOUNT_ID}}` | AWS 계정 ID |
| `{{GITHUB_OWNER}}` | GitHub 유저/org명 |
| `{{TF_STATE_BUCKET}}` | Terraform state S3 버킷명 (`{GITHUB_OWNER}-{PROJECT_NAME}-tf-state`) |

## 기술 스택

| 항목 | 기술 |
|---|---|
| 언어 | Python 3.12 |
| 로컬 실행 | Flask (자동 라우트 등록) |
| Lambda 실행 | Pure Python (Mangum 없음) |
| DB | DynamoDB (PynamoDB) |
| 인프라 | Terraform |
| 배포 | GitHub Actions + OIDC 인증 |

## 프로젝트 구조

```
boilerplate-be/
├── app/
│   └── api/
│       └── {domain}/
│           └── {api_method_action}/   ← endpoint별 독립 Lambda
│               └── handler.py         ← ROUTE + @ResponseHandler.api
├── common/
│   └── awslambda/
│       ├── response_handler.py        ← @ResponseHandler.api 데코레이터
│       ├── request_util.py            ← event body/path/query 파싱
│       └── exceptions.py             ← HttpError 계층 (4xx/5xx)
├── terraform/
│   ├── main.tf                        ← Lambda Layer, API GW, OIDC 역할
│   ├── variables.tf
│   ├── domains/
│   │   └── user/main.tf              ← Lambda 목록 (endpoint별 zip_path)
│   ├── shared/
│   │   ├── api_gateway/              ← HTTP API v2
│   │   └── databases/                ← DynamoDB (Lambda와 라이프사이클 분리)
│   ├── modules/
│   │   ├── lambda/                   ← Lambda + IAM + API GW 연동
│   │   ├── dynamodb/
│   │   └── sqs/
│   └── global/                       ← GitHub Actions OIDC provider (계정당 1회)
├── .github/workflows/
│   ├── global.yml                    ← OIDC provider 최초 생성 (수동)
│   ├── plan.yml                      ← PR → terraform plan + PR 코멘트
│   └── apply.yml                     ← dev/main push → terraform apply
├── local_server.py                   ← Flask 로컬 개발 서버
├── Makefile
└── requirements.txt
```

## 시작하기

### 1. venv 생성 및 의존성 설치

```bash
make setup
source .venv/bin/activate
```

### 2. 로컬 서버 실행

```bash
make local
# → http://localhost:5001
```

`app/api/` 하위의 모든 `handler.py`를 자동 탐색해 Flask 라우트로 등록한다. 새 API를 추가해도 `local_server.py`를 수정할 필요 없음.

### 3. 새 API 추가

```bash
make api name=api_post_create_order domain=order
# → app/api/order/api_post_create_order/handler.py 생성
```

생성된 파일에서 `ROUTE`와 핸들러 로직만 구현하면 됨.

## 핸들러 작성 규칙

```python
from common.awslambda.response_handler import ResponseHandler
from common.awslambda.request_util import parse_event, get_path_params
from common.awslambda.exceptions import NotFoundError

ROUTE = ("POST", "/orders")  # local_server.py 자동 라우트 등록용


@ResponseHandler.api
def handler(event, context):
    body = parse_event(event)
    return 201, {"order_id": "..."}  # (status_code, data) 또는 data만 반환 (→ 200)
```

**반환값 규칙**

| 반환 | 응답 |
|---|---|
| `data` | 200 OK |
| `(201, data)` | 201 Created |
| `None` | 204 No Content |
| `raise NotFoundError("...")` | 404 `{"error": "...", "error_id": "..."}` |
| `raise BadRequestError("...")` | 400 |
| unhandled Exception | 500 + CloudWatch 스택트레이스 |

에러 응답에는 `error_id`(UUID)가 포함된다. CloudWatch에서 해당 ID로 검색하면 스택트레이스를 바로 찾을 수 있음.

## 빌드

```bash
make all           # Lambda zip + Layer 전체 빌드
make zip-src-all   # Lambda 핸들러 zip만 (endpoint별 개별 build.zip)
make zip-layer-all # requirements.txt → .build/layer/layer.zip
make zip-common-src-all  # common/ → .build/common/layer.zip

make diff-all      # 변경된 endpoint 확인 (zip 생성 없이)
make clean-all     # .build/ 정리
```

빌드 결과물은 `.build/`에 생성되며 git에서 제외된다. SHA256 기반 증분 빌드로 변경된 endpoint만 재패키징한다.

## 배포

GitHub Actions가 자동으로 처리한다.

| 이벤트 | 동작 |
|---|---|
| PR → `dev` | `terraform plan` 결과를 PR 코멘트로 게시 |
| push → `dev` | `stage=dev`로 `terraform apply` |
| push → `main` | `stage=prod`로 `terraform apply` |

### 최초 AWS 셋업 (프로젝트 생성 시 1회)

```bash
# 1. S3 버킷 + DynamoDB lock 테이블 생성
./scripts/aws_setup.sh

# 2. GitHub Actions OIDC provider 생성 (GitHub Actions에서 수동 실행)
#    → Actions 탭 → "Terraform Global (One-time Setup)" → Run workflow
```

## Terraform 구조

- **`global/`**: GitHub Actions OIDC provider (AWS 계정당 1회, `terraform.tfstate` 별도 관리)
- **`shared/`**: API Gateway, DynamoDB — Lambda 배포와 라이프사이클 분리
- **`domains/{domain}/main.tf`**: Lambda 목록 관리. 새 endpoint 추가 시 이 파일만 수정
- **`modules/lambda/`**: Lambda + IAM + API GW 연동. IAM은 `{project_name}*` 와일드카드로 DynamoDB/SQS 접근

### 새 도메인 추가

1. `app/api/{domain}/` 하위에 핸들러 구현
2. `terraform/domains/{domain}/main.tf` 생성
3. `terraform/main.tf`에 `module "{domain}_domain"` 블록 추가
