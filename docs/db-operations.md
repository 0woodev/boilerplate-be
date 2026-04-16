# DB 변경 운영 가이드

> DynamoDB 테이블/스키마 변경은 **데이터 손실 위험**이 있는 작업이다.
> PR 한 번에 끝나는 일이 거의 없다.
> 이 문서는 변경 유형별 절차와 체크리스트를 정의한다.

---

## 5대 원칙

1. **데이터 손실 가능한 작업은 PR 하나에 안 담는다** — 보호 해제와 destroy는 분리
2. **`deletion_protection_enabled`는 마지막 안전핀** — 의식적으로 해제할 때만 풀린다
3. **PITR 35일 백업** — 사고 시 시점 복원 가능하게 모든 prod 테이블에서 활성
4. **신규 코드 도입 시 dual-write/dual-read 단계** — 즉시 전환 X
5. **검증 단계 며칠 두기** — 자동 비교 + 수동 샘플링

---

## 변경 유형 분류 — 위험도 기준

| 유형 | 위험도 | 한 PR 가능? | 절차 |
|---|---|---|---|
| GSI 추가 | 🟢 안전 | O | [GSI 추가](#gsi-추가) |
| 새 필드 추가 | 🟢 안전 | O | [필드 추가](#필드-추가) |
| 새 테이블 추가 | 🟢 안전 | O | [테이블 추가](#테이블-추가) |
| GSI 제거 | 🟡 주의 | △ | [GSI 제거](#gsi-제거) |
| 필드 의미 변경 (int → object) | 🟡 주의 | X | [필드 변경](#필드-변경) |
| 테이블 폐기 | 🔴 위험 | X | [테이블 폐기](#테이블-폐기) |
| 테이블 병합 | 🔴 위험 | X | [테이블 병합](#테이블-병합) |
| PK/SK 구조 변경 | 🔴 위험 | X | [키 구조 변경](#키-구조-변경) |

---

## PR 체크리스트 (DB 변경 포함 PR)

PR description에 다음 4개 항목 채울 것:

```markdown
## DB 변경 영향 분석

### 1. 변경 유형
- [ ] 안전 (필드/테이블/GSI 추가)
- [ ] 주의 (필드 의미 변경, GSI 제거)
- [ ] 위험 (테이블 폐기/병합/키 변경)

### 2. 영향받는 데이터
- 테이블: ___
- 추정 아이템 수: ___
- 환경: dev / prod

### 3. 마이그레이션 전략
- [ ] 마이그레이션 불필요 (스키마만 변경)
- [ ] Backfill 스크립트 필요 → 위치: ___
- [ ] Dual-write/dual-read 단계 거침
- [ ] PITR 백업 시점 기록: ___

### 4. 롤백 계획
- 코드 롤백 방법: ___
- 데이터 복원 방법 (PITR 시점): ___
- 검증 쿼리: ___
```

---

## 절차 상세

### 안전 변경

#### 필드 추가

DynamoDB는 schemaless. 모델 코드만 추가하면 끝.

```python
# Before
class Channel(DynamoModel):
    nickname: str = ""

# After
class Channel(DynamoModel):
    nickname: str = ""
    description: str = ""   # 신규 필드, default 있으니 기존 데이터 영향 없음
```

**주의**: default 없으면 기존 아이템 read 시 Pydantic validation 실패. 항상 default 설정.

#### 테이블 추가

Terraform에 모듈 추가, apply. 기존 데이터 무관.

```hcl
locals {
  new_tables = {
    new-domain = {
      hash_key  = "PK"
      range_key = "SK"
      gsi = [...]
    }
  }
}
module "new_domain_tables" {
  source = "../../modules/dynamodb"
  tables = local.new_tables
  ...
}
```

#### GSI 추가

DynamoDB가 자동 backfill. 추가 즉시 사용 가능 (큰 테이블은 backfill 시간 걸림).

```hcl
gsi = [
  ...
  { name = "NewIndex", hash_key = "NewIdxPK", range_key = "NewIdxSK" }   # 추가
]
```

기존 아이템에 GSI 키 attribute 없으면 인덱스에서 누락 (sparse index — 이건 의도적이면 OK).

---

### 주의 변경

#### GSI 제거

```
Step 1: 코드에서 해당 GSI를 사용하는 query 모두 제거
Step 2: 1주일 모니터링 (CloudWatch에서 해당 인덱스 호출 0인지)
Step 3: Terraform에서 GSI 제거 → apply
```

GSI 제거는 in-place 가능. 데이터 손실 없음. 단, 사용 코드 확실히 정리 후.

#### 필드 변경

같은 key를 다른 타입/구조로 사용하는 경우. 예: `visitors: int` → `visitors: dict`.

```
PR #1 — 신규 필드 추가
  - 기존 visitors 유지 + visitors_v2: dict 신규
  - 쓰기 핸들러: 둘 다 채움
  - 읽기 핸들러: visitors_v2 우선, 없으면 visitors fallback

PR #2 — Backfill
  - 일회성 스크립트로 모든 아이템 visitors → visitors_v2 변환
  - 진행률 로그

PR #3 — 코드 정리
  - 읽기에서 visitors fallback 제거
  - 쓰기에서 visitors 채우기 제거

PR #4 (옵션) — 데이터 정리
  - cleanup 스크립트로 모든 아이템에서 visitors 필드 제거
```

---

### 위험 변경

#### 테이블 폐기

전체 절차 ~2주.

```
[D-7] 코드/앱에서 read/write 모두 제거
  - 모든 핸들러에서 모델 import 삭제
  - 모델 파일 자체 삭제 (테스트 동반)
  - PR 머지 → dev/prod 배포
  - CloudWatch에서 해당 테이블 호출 metric 0 확인

[D-1] 백업 스냅샷
  - PITR 시점 기록
  - 추가로 export-to-s3 권장 (장기 보관)

[D-Day] 보호 해제 PR
  - 해당 테이블만 deletion_protection_enabled = false
  - prevent_destroy = false
  - apply (인프라 변경 없음, 보호 플래그만 OFF)

[D-Day +1h] 삭제 PR
  - terraform 모듈에서 해당 테이블 항목 삭제
  - destroy workflow 수동 실행 (confirm: yes + prod approval)
```

**왜 PR 두 개?**
- 보호 해제와 삭제를 한 PR에 담으면 리뷰어가 의도를 놓칠 수 있음
- 두 단계라 사이에 "정말 지울 거?" 한 번 더 자문 가능

#### 테이블 병합

데이터 마이그레이션 작업. ~2-4주 소요.

##### Phase A — 새 테이블 생성

```
PR — "merged_table 추가"
- Terraform에 새 테이블 + GSI 추가
- 기존 테이블은 그대로
- apply
```

##### Phase B — Dual-write

```
PR — "신규 쓰기는 양쪽에"
- POST/PATCH 핸들러: 기존 테이블 + 새 테이블 둘 다 write
- TransactWriteItems로 원자성 보장
- 신규 쓰기부터 자동 동기화
```

##### Phase C — Backfill

```
일회성 마이그레이션 작업 (Lambda 또는 ECS):
1. 기존 테이블 A scan
2. 각 키에 대해 기존 테이블 B에서 관련 데이터 조회
3. 합쳐서 새 테이블에 PutItem (conditional: 이미 있으면 skip)
4. 진행률 CloudWatch 기록

마이그레이션 중 신규 쓰기는 Phase B 덕에 양쪽 들어가는 중
```

##### Phase D — 검증 (3-7일)

- 두 데이터셋 sample 비교 스크립트
- 카운트 일치 확인
- 핸드폴 케이스 (특이 데이터) 직접 비교
- Grafana/CloudWatch 차이 모니터링

##### Phase E — Read 전환

```
PR — "GET 핸들러 새 테이블에서 읽기"
- 점진 전환 권장 (feature flag): 5% → 25% → 100% rollout
- 전환 후 며칠 dual-write 유지 (롤백 가능성)
```

##### Phase F — 옛 테이블 폐기

위 [테이블 폐기](#테이블-폐기) 절차.

#### 키 구조 변경

예: `PK=POST_ID@xxx` → `PK=WS@yyy#POST_ID@xxx` (멀티테넌트 도입).

같은 테이블에서 PK 못 바꿈 → **테이블 병합과 동일 절차**.

새 테이블을 만들고, dual-write/backfill/검증/read 전환/옛 테이블 폐기.

---

## 사고 대응

### Case 1: 실수로 destroy 됐다

PITR 활성화돼있으면 시점 복원 가능 (35일 이내).

```bash
aws dynamodb restore-table-to-point-in-time \
  --source-table-name <원본> \
  --target-table-name <원본>-restored \
  --restore-date-time 2026-04-16T05:00:00Z
```

복원된 테이블 ↔ 코드가 보는 테이블 이름 다르므로:
1. 복원 테이블에서 데이터 export-to-s3
2. 새 원본 테이블 생성 (terraform apply)
3. import-from-s3로 데이터 복구

### Case 2: dual-write 중 데이터 불일치 발견

```
1. dual-write 즉시 중단 (코드 롤백)
2. 비교 스크립트로 차이 분석
3. 어느 쪽이 truth인지 판단 (보통 기존 테이블)
4. 신규 테이블의 잘못된 데이터 삭제 또는 패치
5. 원인 수정 후 dual-write 재개
```

### Case 3: 마이그레이션 도중 throttling

```
1. 마이그레이션 작업 일시 중단
2. 대상 테이블 BillingMode = PROVISIONED + WCU/RCU 임시 증설
   또는 ON_DEMAND 유지하되 마이그레이션 작업의 동시성 낮춤
3. 재개 (이미 처리된 키는 conditional skip 덕에 idempotent)
```

---

## 보호장치 점검 체크리스트

**모든 prod 테이블에 적용되어야 함:**

- [ ] `deletion_protection_enabled = true` (AWS-level 삭제 차단)
- [ ] `point_in_time_recovery.enabled = true` (35일 시점 복원)
- [ ] `lifecycle.prevent_destroy = true` (terraform plan 단계 차단)
- [ ] CloudWatch 알람 (사용량/에러 급증 감지)
- [ ] AWS Backup 정책 (선택, 장기 보관용)

**알려진 빈틈:**
- `prevent_destroy`는 "module 인스턴스 자체가 config에서 사라지면" 우회되는 경우 있음
- → `deletion_protection_enabled`가 진짜 마지막 방어선

---

## 참고

- DynamoDB Operations: https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/operating.html
- PITR: https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/PointInTimeRecovery.html
- DynamoModel 프레임워크: `DynamoConcept.md`
- 모델 정의: `common/models/`
- Terraform 테이블 선언: `terraform/shared/databases/`
