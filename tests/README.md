# tests/ — 테스트 가이드

## 스택

| 도구 | 역할 |
|---|---|
| **pytest** | 테스트 러너 |
| **moto** | AWS 서비스 **인메모리 가짜 구현** — boto3 호출을 가로채 실제 AWS 안 감 |

> 💡 **moto 이름의 유래**: **mo**ck + bo**to**. 이름 그대로 boto3(AWS SDK) 를 mock 해준다.
> `@mock_aws` 데코레이터 (또는 `with mock_aws():` 컨텍스트) 안에서는 boto3 가 실제 AWS 가
> 아닌 moto 의 가짜 백엔드와 대화한다.

## 핵심 이해: moto 는 "진짜" 처럼 보이는 "가짜" 다

```
실제 운영 코드:              boto3.resource("dynamodb").Table("x").put_item(...)
                                        │
                                        ▼
                            ┌──────────────────────┐
                            │ AWS DynamoDB (실제)  │
                            └──────────────────────┘

moto 가 활성화된 테스트:      boto3.resource("dynamodb").Table("x").put_item(...)
                                        │
                                        ▼  (moto 가 boto3 SDK 를 monkey-patch)
                            ┌──────────────────────────┐
                            │ moto 인메모리 DynamoDB   │
                            │ (테스트 프로세스 안에만 존재) │
                            └──────────────────────────┘
```

- **네트워크 호출 없음** — 인터넷 끊어도 동작
- **AWS 비용 0원** — 실제 API 콜 아니니까
- **빠름** — 메모리에서만 동작 (55 tests ≈ 2초)
- **격리됨** — 각 `@pytest.fixture` 블록 끝나면 전부 사라짐
- **100% 호환 아님** — moto 는 DynamoDB 의 "주요 동작" 을 따라 만든 거라 드물게 edge case 가 실제 AWS 와 다를 수 있음

→ CI/로컬에서는 moto 로 빠르게 돌리고, 최종 검증은 dev 환경에 배포해 실제 DynamoDB로 확인.

---

## 파일 구조

```
tests/
├── conftest.py              # 모든 테스트가 공유하는 fixture/helper
├── test_keys.py             # 키 템플릿 렌더링 (moto 불필요 — 순수 함수)
├── test_dynamo_model.py     # DynamoModel + GSI framework
├── test_user_model.py       # User 모델
├── test_group_model.py      # Group 모델
└── test_member_model.py     # Member 모델
```

## conftest.py 의 fixture 세 가지

### 1. `_env` (autouse)
환경변수 세팅. `PROJECT_NAME`/`STAGE` 는 `DynamoModel.table_name` 템플릿 치환용.
`AWS_DEFAULT_REGION` + fake credentials 는 moto 가 기본값을 요구하기 때문.
**autouse=True** 라 모든 테스트에 자동 적용됨.

### 2. `_reset_dynamo_client_cache` (autouse)
`DynamoClient` 는 boto3 `resource` 를 클래스 변수로 캐시함 (Lambda 콜드스타트 최적화).
moto 의 mock 은 테스트별로 새 백엔드 → 이전 테스트의 캐시를 물고 있으면 mock 과 연결 안 됨.
테스트 시작/종료 시 캐시를 `None` 으로 리셋.

### 3. `aws` (명시적 요청)
`mock_aws()` 컨텍스트를 활성화. 이 fixture 를 쓰는 테스트 안에서 **모든 boto3 DynamoDB 호출이 moto 로 리다이렉트**.
테스트 끝나면 컨텍스트 종료 → 생성한 모든 가짜 테이블/데이터 사라짐.

```python
def test_something(aws):   # ← aws fixture 요청 = moto 활성화
    boto3.client("dynamodb").create_table(...)  # moto 로 감
```

---

## `create_table` 헬퍼

### 가짜를 만드는가?

**네 — moto 인메모리 테이블**. 실제 AWS 와 무관.

```python
# tests/conftest.py::create_table
boto3.client("dynamodb").create_table(
    TableName="test-local-users",
    KeySchema=[...],
    ...
)
```

이 호출은 moto 가 인터셉트해서 **프로세스 메모리 안에만** 테이블을 만듦.

### 왜 필요한가?

moto 는 "테이블이 존재하는지" 도 진짜처럼 흉내냄. `put_item` 호출 전에 `create_table` 안 해두면
`ResourceNotFoundException` 이 실제 AWS 처럼 뜬다. 그래서 fixture 에서 미리 만들어둠.

### 지우는가?

**자동으로** — `mock_aws()` 컨텍스트가 끝나면 moto 가 자기 인메모리 상태를 통째로 버림.
`delete_table` 을 호출할 필요 없음.

### 사용 예

```python
@pytest.fixture
def users_table(aws):
    create_table(
        "test-local-users",
        gsi=[
            {"name": "ByEmail", "hash_key": "ByEmailPK", "range_key": "ByEmailSK"},
        ],
    )
    # 여기서 return/yield 없음 — 테스트 함수가 실행될 때 테이블은 이미 만들어져 있음

def test_find_by_email(users_table):
    User(...).save()       # moto 테이블에 저장됨
    users, _ = User.ByEmail.query(email="...")
    assert ...
```

테스트 끝나면 `aws` fixture 의 `mock_aws()` 컨텍스트 종료 → 가짜 테이블/데이터 사라짐.

---

## 새 모델 테스트 작성 순서

```python
# 1. 모델 import
from app.api.foo.model import Foo
from tests.conftest import create_table

FOOS_TABLE = "test-local-foos"   # 모델의 table_name 템플릿이 렌더링한 값과 동일하게

# 2. 테이블 fixture — aws 를 의존성으로 요청
@pytest.fixture
def foos_table(aws):
    create_table(
        FOOS_TABLE,
        gsi=[
            {"name": "ByBar", "hash_key": "ByBarPK", "range_key": "ByBarSK"},
        ],
    )

# 3. 테스트 — 방금 만든 테이블 fixture 를 요청하면 그 안에서 CRUD 돌릴 수 있음
def test_save_and_get(foos_table):
    Foo(foo_id="f1", bar="x").save()
    got = Foo.get(foo_id="f1")
    assert got.bar == "x"
```

table_name 은 `_env` fixture 가 주입하는 `PROJECT_NAME=test`, `STAGE=local` 로 치환되므로,
모델의 `table_name = "{project_name}-{stage}-foos"` 면 실제 이름은 `test-local-foos`.

---

## 실행

```bash
make test                       # 전체 실행
.venv/bin/pytest tests/test_user_model.py -v     # 특정 파일만
.venv/bin/pytest tests/ -k "email"               # 이름에 "email" 들어간 테스트만
.venv/bin/pytest tests/ -x                       # 첫 실패에서 중단
.venv/bin/pytest tests/ --pdb                    # 실패 지점에서 디버거 진입
```

---

## moto 가 커버 못 하는 것

- **Conditional writes** — 대부분 OK, 드물게 예외 메시지 차이
- **Scan with FilterExpression** — 대부분 OK
- **Transactions** — 기본적으로 OK
- **Streams** — 활성화는 되지만 실시간 트리거는 제한적
- **정확한 에러 코드** — 대부분 맞지만 드물게 차이

확신 안 서면 dev 환경 배포해서 실제 DynamoDB 로 한번 확인하는 게 베스트.

---

## 주요 참조

- moto 공식 문서: https://docs.getmoto.org/
- pytest 공식 문서: https://docs.pytest.org/
- DynamoConcept.md — 우리 프레임워크 스펙
