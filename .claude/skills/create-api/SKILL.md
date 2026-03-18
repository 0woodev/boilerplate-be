---
name: create-api
description: 새 API 엔드포인트를 생성합니다. handler.py 파일 생성 및 terraform domains에 Lambda 항목을 추가합니다.
---

다음 설명을 보고 새 API 엔드포인트를 생성해줘.

**입력:** $ARGUMENTS

---

## 작업 순서

### 1. 이름 결정

입력 설명을 분석해서 아래 정보를 도출해:
- **HTTP method**: GET / POST / PUT / DELETE / PATCH
- **domain**: 어떤 도메인인지 (예: user, product, order...)
- **api_gateway_route**: REST 경로 (예: `GET /users/{user_id}`)
- **handler name**: `api_{method}_{resource}[_{qualifier}]` 형식

네이밍 규칙:
- 소문자 snake_case
- `api_{method}_{resource}[_{qualifier}]`
  - method: http method 소문자 (get, post, put, delete, patch)
  - resource: 대상 리소스 (단건은 단수, 목록은 복수)
  - qualifier: 구분이 필요할 때만 추가 (`by_email`, `by_status` 등)
- domain은 폴더로 구분되므로 이름에 포함하지 않음
- 경로 파라미터는 `{param_name}` 형식

좋은 예시:
- `api_post_user` (POST /users)
- `api_get_user` (GET /users/{user_id})
- `api_get_users` (GET /users — 목록은 복수형)
- `api_put_user` (PUT /users/{user_id})
- `api_delete_user` (DELETE /users/{user_id})
- `api_get_user_by_email` (GET /users/email/{email})

### 2. make api 실행

```bash
make api name={handler_name} domain={domain}
```

### 3. terraform/domains/{domain}/main.tf 업데이트

`locals.lambdas` 블록에 새 항목 추가:

```hcl
{handler_name} = {
  zip_path          = "${path.module}/../../../.build/app/api/{domain}/{handler_name}/build.zip"
  handler           = "handler.handler"
  api_gateway_route = "{METHOD} {path}"
  # TODO: environment_variables 필요 시 추가
  # environment_variables = {
  #   TABLE_NAME = local.table_name.xxx
  # }
}
```

`terraform/domains/{domain}/` 폴더가 없으면:
- `terraform/domains/{domain}/main.tf`, `variables.tf`, `outputs.tf` 생성
- `terraform/main.tf`에 새 domain 모듈 등록

### 4. 완료 후 안내

생성된 파일 경로와 다음 작업을 안내해줘:
- `app/api/{domain}/{handler_name}/handler.py` — 비즈니스 로직 작성
- terraform 경로 파라미터, environment_variables 필요 여부 확인
