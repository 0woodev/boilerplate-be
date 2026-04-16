# DynamoConcept — DynamoDB 모듈 기능 명세

이 문서는 `common/dynamo/` 가 **무엇을** 해줘야 하는지(기능)를 정리한다.
구현 방식(어떻게)은 별개의 설계 문서에서 다룬다.

---

## 1. 기본 원칙

- **서비스별 테이블** — 도메인마다 전용 테이블 하나. 단일 테이블에 이종 엔티티 섞지 않음.
- **모든 테이블은 PK + SK 구조** — 현재 1엔티티=1레코드라도 미래 확장 대비.
- **키 규칙은 모델에만 존재** — handler/비즈니스 코드는 키 문자열을 절대 보지 않는다.
- **규칙 변경이 안전** — 키 포맷이 바뀌면 모델 한 줄 수정으로 끝. 사용처는 영향 없음.

---

## 2. 키 컨벤션

- `KEY@value` — 하나의 key=value 쌍
- `#` — 쌍 사이 구분자
- 예시
  - PK: `USER_ID@abc123`
  - SK: `TYPE@profile`
  - SK (composite): `DATE@2024-01-15#TYPE@workout`

DB 값만 보고도 어떤 필드 조합인지 추측 가능하게 자기 문서화.

### 일관성 원칙 (Option A)

**모든 PK/SK/GSI 키 컬럼은 위 템플릿을 따른다. 단일 필드 GSI 도 예외 없음.**

- 예: ByEmail GSI 라도 `ByEmailPK = "EMAIL@{email}"` (raw `email` 필드 재사용 X)
- 컬럼이 중복되는 비용 > 일관성/확장성 가치 라고 확신될 때만 raw 필드 사용 고려
- Sparse index 는 템플릿 렌더 실패 시 컬럼 생략으로 자동 처리

---

## 3. 모델 정의

모델 클래스 하나에 다음이 모여있다:

- 테이블 이름 (환경별 치환: `{project_name}`, `{stage}`)
- 기본 테이블 PK/SK
  - **컬럼명** (`pk_attr` / `sk_attr`) — terraform 선언과 1:1
  - **값 규칙** (`pk_template` / `sk_template`)
- 필드 선언 (타입 힌트 포함)
- GSI 목록 (각 GSI는 하위 클래스로 — §6)

**요구사항:**
- 필드만 보고 IDE 자동완성 돼야 함
- 모델에 **선언되지 않은 필드도 저장/조회 시 보존** (PynamoDB 처럼 누락되지 않음)
- 중첩 구조 지원 — `user.home.address.city` 같은 접근 가능 (DynamoDB Map)
- 리스트 필드 지원 — `user.tags = ["a", "b"]` (DynamoDB List)

---

## 4. CRUD — Active Record

인스턴스 메서드:
- `instance.save()` — PK/SK/GSI 컬럼 자동 조립해서 저장
- `instance.delete()` — 자기 키로 삭제

클래스 메서드:
- `Model.get(**fields)` — PK+SK에 필요한 필드만 넘기면 단건 조회 (None 반환 가능)
- `Model.update_by_key(updates, **fields)` — 부분 수정
- `Model.delete_by_key(**fields)` — 키 필드만으로 삭제

인스턴스로도 전달 가능:
- `Model.get(instance)` — 인스턴스의 키 필드로 조회
- `Model.delete_by_key(instance)` — 같은 패턴

---

## 5. 쿼리

### 기본 (eq / begins_with 자동)

`Model.query(**fields)` — 넘긴 필드의 정도에 따라 자동 결정:

| 필드 조합 | 동작 |
|---|---|
| PK 필드만 | 그 PK 의 전체 아이템 |
| PK + SK 전체 필드 | 정확히 일치 (eq) |
| PK + SK 일부 필드 | SK begins_with (첫 빠진 필드 앞까지) |

### 범위 — 명시적 메서드

- `Model.query_gt(**fields)` — SK > 렌더링값
- `Model.query_gte(**fields)`
- `Model.query_lt(**fields)`
- `Model.query_lte(**fields)`

### BETWEEN — start/end dict

```
Model.query_between(
    **pk_fields,                  # PK 필드
    start={"date": "2024-01-01"}, # SK 하한 (partial OK)
    end={"date": "2024-12-31"},   # SK 상한
)
```

### 전체 스캔

- `Model.scan()` — 테이블 전체 (마이그레이션 / 소규모 리스팅)

### 페이지네이션

모든 `query*` / `scan` 은:
- `limit` 파라미터 받음
- `cursor` 파라미터 받음 (불투명 문자열)
- 반환값: `(results, next_cursor)` — 다음 페이지 없으면 `next_cursor=None`

---

## 6. GSI

### 선언 — 모델의 중첩 클래스

각 GSI 는 자기 자신의 **컬럼명(attr)** 과 **값 규칙(template)** 을 가진 하위 클래스:

- `index` — DynamoDB 인덱스 이름 (terraform 선언과 1:1 매칭)
- `pk_attr` / `sk_attr` — GSI 가 사용할 컬럼명
- `pk_template` / `sk_template` — 그 컬럼에 들어갈 값 규칙

```
class User(DynamoModel):
    ...

    class ByEmail(GSI):
        index:        ClassVar[str] = "GSI1"
        pk_attr:      ClassVar[str] = "GSI1PK"
        sk_attr:      ClassVar[str] = "GSI1SK"
        pk_template:  ClassVar[str] = "EMAIL@{email}"
        sk_template:  ClassVar[str] = "TYPE@profile"

    class ByCreatedAt(GSI):
        index:        ClassVar[str] = "GSI2"
        pk_attr:      ClassVar[str] = "GSI2PK"
        sk_attr:      ClassVar[str] = "GSI2SK"
        pk_template:  ClassVar[str] = "TYPE@profile"
        sk_template:  ClassVar[str] = "CREATED_AT@{created_at}"
```

### 규칙

- **attr 이름 = terraform의 hash_key/range_key 이름** 과 반드시 일치해야 한다.
- 모델 간 GSI attr 이름을 재사용해도 되지만, 한 테이블 안에서 index 별로는 달라야 한다 (DynamoDB 요구사항).
- `sk_attr` / `sk_template` 은 생략 가능 (hash-only GSI).

### 쿼리 — 기본 테이블과 동일 API

- `User.ByEmail.query(email="...")`
- `User.ByCreatedAt.query_gt(created_at="2024-01-01")`
- `User.ByCreatedAt.query_between(start={...}, end={...})`

모두 `query*` 시리즈와 시그니처 일치.

### 자동 컬럼 생성

`user.save()` 한 번이면 **정의된 모든 GSI 컬럼이 자동 채워져** 저장된다.
handler 는 GSI 의 존재를 의식할 필요 없음.

### Sparse GSI

GSI 템플릿이 요구하는 필드가 인스턴스에 비어있으면 해당 GSI 컬럼은 **빠진 채로 저장** → 자연스럽게 sparse index 가 됨. (e.g. email 없는 유저는 `ByEmail` 인덱스에서 제외)

---

## 7. 마이그레이션

### 새 필드 추가 / GSI 추가 시

1. 모델에 필드 또는 GSI 중첩 클래스 추가
2. Terraform에 (GSI 추가 시만) GSI 선언 추가 → apply
3. 마이그레이션 스크립트 한 번 실행:
   ```
   cursor = None
   while True:
       users, cursor = User.scan(cursor=cursor)
       for u in users:
           u.save()   # 새 스키마 기준으로 재저장 — 신규 필드/GSI 컬럼 자동 생성
       if not cursor: break
   ```

### 중요 특성

- **미선언 필드도 보존** 되므로, 예상 못 한 오래된 필드가 재저장 중 사라지지 않음
- PK/SK/GSI 값은 항상 모델의 **현재** 템플릿 기준으로 재생성됨 (과거 값 믿지 않음)

---

## 8. 저수준 API (escape hatch)

모델로 표현하기 어려운 ad-hoc 쿼리는 `DynamoClient` 에 직접 내려갈 수 있다.
- `DynamoClient.get/put/delete/update/query/scan` — `dict in / dict out`
- `QueryMethod` enum: `EQ / BEGINS_WITH / BETWEEN / GT / GTE / LT / LTE`

권장은 아님 — 가능하면 모델 메서드로 표현 후 한 곳에 모아두기.

---

## 9. 테이블 이름 / 환경

- 모델의 `table_name` 은 템플릿 문자열
  - 예: `"{project_name}-{stage}-users"`
- 런타임에 Lambda 환경변수 `PROJECT_NAME`, `STAGE` 로 치환
- 핸들러는 실제 테이블명을 모른다

---

## 10. 보존되는 특성 요약

| 특성 | 보장 |
|---|---|
| 키 문자열 handler 노출 | 안 함 |
| 모델 미선언 필드 | 보존됨 |
| 중첩/리스트 필드 | pydantic 방식으로 자연스럽게 |
| 타입 힌트/자동완성 | 제공됨 |
| sparse GSI | 자동 (필드 없으면 컬럼 생략) |
| 키 규칙 변경 | 모델 한 곳만 수정 |
| 스키마 확장 | scan + save 루프로 마이그레이션 |
