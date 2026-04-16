"""ID 생성 유틸 — time-sortable UUIDv7 + human-readable prefix.

UUIDv7 (RFC 9562):
  - 앞 48bit = Unix ms timestamp
  - 문자열 사전순 정렬 = 시간 순 정렬 (DynamoDB SK에 바로 의미)
  - Python 3.14 에서 uuid.uuid7() stdlib 지원 예정. 그 전까지는 직접 구현.

Format:
  {prefix}_{32-char hex}
  e.g. "usr_018f3a1c7b4e7abc8xxxxxxxxxxxxxxx" (36 chars)

Prefix convention (3-letter):
  usr_ / ws_ / mem_ / ch_ / log_ / evt_ / err_
"""
import os
import time


def _uuid7_hex() -> str:
    """Generate UUIDv7 as 32-char hex (no dashes).

    Bit layout:
      [0:48]   = Unix ms timestamp
      [48:52]  = version (0111 = 7)
      [52:64]  = random (rand_a, 12 bits)
      [64:66]  = variant (10)
      [66:128] = random (rand_b, 62 bits)
    """
    ts_ms = int(time.time() * 1000) & 0xFFFF_FFFF_FFFF       # 48 bit
    rand_a = int.from_bytes(os.urandom(2), "big") & 0x0FFF   # 12 bit
    rand_b = int.from_bytes(os.urandom(8), "big") & 0x3FFF_FFFF_FFFF_FFFF  # 62 bit
    value = (
        (ts_ms << 80)
        | (0x7 << 76)
        | (rand_a << 64)
        | (0x2 << 62)
        | rand_b
    )
    return f"{value:032x}"


def generate_id(prefix: str) -> str:
    """Generate a time-sortable, prefixed identifier.

    Args:
        prefix: 엔티티 식별자 (e.g. "usr", "ws", "ch"). "_" 없이.

    Returns:
        "{prefix}_{32-char hex}" — 전체 문자열 정렬 시 생성 시각 순서 보장.
    """
    if not prefix or "_" in prefix:
        raise ValueError(f"prefix must be non-empty without underscore: {prefix!r}")
    return f"{prefix}_{_uuid7_hex()}"
