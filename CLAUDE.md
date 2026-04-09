# CLAUDE.md — boilerplate-be

이 레포는 **풀스택 개발자를 위한 boilerplate**의 백엔드 서브모듈이다.
상위 레포(`boilerplate-app`)에 FE, 인프라 스크립트, AI 협업 가이드가 함께 있다.

## 세션 시작 시 반드시 읽기

```
PROGRESS.md
```

현재까지 결정된 아키텍처, 구현 완료 항목, 다음 작업 목록이 담겨 있다.
이 파일을 읽지 않으면 이전 맥락 없이 작업하게 된다.

## 스택

- **Runtime**: Python 3.12, AWS Lambda (per-endpoint)
- **API**: API Gateway HTTP v2
- **DB**: DynamoDB (PynamoDB)
- **IaC**: Terraform
- **CI/CD**: GitHub Actions (OIDC)

## 스킬

```
/create-api      → 새 API 엔드포인트 스캐폴딩
/apply-new-tech  → 새 기술 도입 방법 조사·추천
```

## 자주 쓰는 명령어

```bash
make setup    # venv 생성 + 패키지 설치
make local    # 로컬 서버 실행 (Flask, port 5001)
make api name=api_post_order domain=order
```
