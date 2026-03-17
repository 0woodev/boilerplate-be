# boilerplate-be

Backend boilerplate. [boilerplate-app](https://github.com/0woodev/boilerplate-app)의 `setup.sh`에 의해 새 프로젝트의 `be/` submodule로 복제된다.

## 사용 방법

직접 클론하지 않고, `boilerplate-app`의 `setup.sh`를 통해 사용한다.

```
boilerplate-be (클론) → {app_name}-be (새 레포) → main repo의 be/ submodule
```

## 플레이스홀더

`setup.sh` 실행 시 아래 값들이 자동으로 치환된다.

| 플레이스홀더 | 치환값 |
|---|---|
| `{{PROJECT_NAME}}` | 프로젝트 이름 |
| `{{BE_DOMAIN}}` | `{app_name}-api.{domain}` |
| `{{AWS_REGION}}` | AWS 리전 |
| `{{AWS_ACCOUNT_ID}}` | AWS 계정 ID |
| `{{GITHUB_OWNER}}` | GitHub 유저/org명 |
| `{{TF_STATE_BUCKET}}` | Terraform state S3 버킷명 |

## 현재 구조

```
be/
├── app/
│   ├── main.py     ← FastAPI 앱 + Mangum (Lambda handler)
│   └── api/        ← API routes (예정)
├── requirements.txt
└── README.md
```

## 기술 스택

| 항목 | 기술 |
|---|---|
| 언어 | Python |
| 로컬 실행 | FastAPI + Uvicorn |
| Lambda 실행 | FastAPI + Mangum |
| DB | DynamoDB (boto3) |
| 인프라 | Terraform |
| 메시지 큐 | SQS |
| 배포 | GitHub Actions + Terraform (S3 state 백엔드) |

## 로컬 실행

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## 히스토리

- 로컬: FastAPI + Uvicorn, Lambda: Mangum 어댑터 사용
- Terraform state: S3 백엔드 + DynamoDB lock 테이블
- Lambda 배포: GitHub Actions OIDC 인증 (static 자격증명 없음)
- Lambda 버전 관리: `publish = true` + Alias 사용
- 공통 코드: Lambda Layer로 관리

## 앞으로 할 것

- [ ] boto3 DynamoDB wrapper 라이브러리 (`lib/dynamo/`)
- [ ] Lambda 함수 구조 (`app/lambdas/`)
- [ ] Lambda Layer 공통 코드 (`common/`)
- [ ] Terraform 인프라 코드 (lambda.tf, api_gateway.tf, dynamodb.tf, sqs.tf)
- [ ] GitHub Actions workflow (OIDC 인증, PR → plan, merge → apply)
