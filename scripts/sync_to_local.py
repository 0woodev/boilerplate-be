"""DynamoDB 데이터 동기화.

원본 → 대상으로 테이블 데이터를 복사. 대상 테이블을 비우고 원본을 그대로 넣음.

지원 방향:
  dev  → local   로컬 개발용 (기본)
  prod → local   prod 데이터로 로컬 개발
  prod → dev     prod를 dev에 복원 (확인 프롬프트 있음)

Usage:
    python scripts/sync_to_local.py                          # dev → local
    python scripts/sync_to_local.py --from prod              # prod → local
    python scripts/sync_to_local.py --from prod --to dev     # prod → dev (확인 필요)
    python scripts/sync_to_local.py --dry-run                # 건수만 확인
"""

import argparse
import os

import boto3
from botocore.config import Config

PROJECT = os.environ.get("PROJECT_NAME", "my-project")
LOCAL_ENDPOINT = "http://localhost:8000"
# scripts/create_local_tables.py 의 TABLES 키와 일치해야 함.
TABLES = ["users", "groups", "members"]


def table_name(key: str, stage: str) -> str:
    return f"{PROJECT}-{stage}-{key}"


def get_client(stage: str):
    """stage에 맞는 DynamoDB resource 반환."""
    if stage == "local":
        return boto3.resource(
            "dynamodb",
            endpoint_url=LOCAL_ENDPOINT,
            region_name="ap-northeast-2",
            aws_access_key_id="local",
            aws_secret_access_key="local",
        )
    # dev, prod — 실제 AWS
    return boto3.resource(
        "dynamodb",
        region_name="ap-northeast-2",
        config=Config(read_timeout=30, retries={"max_attempts": 3}),
    )


def scan_all(table) -> list[dict]:
    """테이블 전체 scan (페이지네이션 처리)."""
    items = []
    response = table.scan()
    items.extend(response["Items"])
    while "LastEvaluatedKey" in response:
        response = table.scan(ExclusiveStartKey=response["LastEvaluatedKey"])
        items.extend(response["Items"])
    return items


def clear_table(table) -> int:
    """테이블의 모든 항목 삭제."""
    key_names = [k["AttributeName"] for k in table.key_schema]
    items = scan_all(table)
    if not items:
        return 0
    with table.batch_writer() as batch:
        for item in items:
            key = {k: item[k] for k in key_names}
            batch.delete_item(Key=key)
    return len(items)


def copy_items(items: list[dict], target_table):
    """항목 목록을 대상 테이블에 batch write."""
    with target_table.batch_writer() as batch:
        for item in items:
            batch.put_item(Item=item)


def main():
    parser = argparse.ArgumentParser(description="DynamoDB 데이터 동기화")
    parser.add_argument("--from", dest="source", default="dev", choices=["dev", "prod"],
                        help="복사 원본 stage (default: dev)")
    parser.add_argument("--to", dest="target", default="local", choices=["local", "dev"],
                        help="복사 대상 stage (default: local)")
    parser.add_argument("--dry-run", action="store_true", help="건수만 확인, 실제 복사 안 함")
    args = parser.parse_args()

    source, target = args.source, args.target

    # 안전장치: 원격 환경에 쓰기 전 확인
    if target != "local":
        print(f"⚠️  주의: {source} → {target} (원격 환경에 덮어씁니다)")
        print(f"   {target} 의 기존 데이터가 전부 삭제되고 {source} 데이터로 교체됩니다.")
        confirm = input(f"   계속하시겠습니까? (yes 입력): ")
        if confirm.strip().lower() != "yes":
            print("❌ 취소됨")
            return

    # 같은 환경끼리 복사 방지
    if source == target:
        print(f"❌ 원본과 대상이 같습니다: {source}")
        return

    print(f"🔄 {source} → {target} 동기화")
    print(f"   프로젝트: {PROJECT}")
    print(f"   테이블: {', '.join(TABLES)}\n")

    src_client = get_client(source)
    tgt_client = get_client(target)

    for key in TABLES:
        src_name = table_name(key, source)
        tgt_name = table_name(key, target)

        print(f"{'='*50}")
        print(f"📋 {src_name} → {tgt_name}")
        print(f"{'='*50}")

        # 1. 원본에서 scan
        try:
            src_table = src_client.Table(src_name)
            src_items = scan_all(src_table)
            print(f"  📥 원본 항목 수: {len(src_items)}")
        except Exception as e:
            print(f"  ❌ 원본 scan 실패: {e}")
            continue

        if args.dry_run:
            print(f"  🏁 dry-run — 스킵\n")
            continue

        # 2. 대상 테이블 비우기
        try:
            tgt_table = tgt_client.Table(tgt_name)
            deleted = clear_table(tgt_table)
            print(f"  🗑️  대상 기존 항목 삭제: {deleted}개")
        except Exception as e:
            print(f"  ❌ 대상 테이블 비우기 실패: {e}")
            if target == "local":
                print(f"     `make local-db-init` 먼저 실행하세요.")
            continue

        # 3. 복사
        try:
            copy_items(src_items, tgt_table)
            print(f"  ✅ 복사 완료: {len(src_items)}개")
        except Exception as e:
            print(f"  ❌ 복사 실패: {e}")
            continue

        print()

    if not args.dry_run:
        print("🎉 동기화 완료!")
        if target == "local":
            print(f"   `make local STAGE=local` 로 시작하면 {source} 데이터로 동작합니다.")


if __name__ == "__main__":
    main()
