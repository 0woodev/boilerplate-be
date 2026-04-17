"""UUIDv7 + prefix 생성기 테스트."""
import re
import time

import pytest

from common.ids import _uuid7_hex, generate_id


HEX32_RE = re.compile(r"^[0-9a-f]{32}$")


class TestUuid7Hex:
    def test_returns_32_char_hex(self):
        v = _uuid7_hex()
        assert HEX32_RE.match(v), v

    def test_version_bits_are_7(self):
        # 13th char (index 12) = version nibble
        v = _uuid7_hex()
        assert v[12] == "7", v

    def test_variant_bits_are_10(self):
        # 17th char (index 16) — variant nibble high bits 10xx → 8,9,a,b
        v = _uuid7_hex()
        assert v[16] in ("8", "9", "a", "b"), v

    def test_timestamp_first(self):
        # 생성 전후 시각으로 앞 12자 hex 타임스탬프 감싸지는지
        before = int(time.time() * 1000)
        v = _uuid7_hex()
        after = int(time.time() * 1000)
        ts = int(v[:12], 16)
        assert before <= ts <= after

    def test_monotonic_sort(self):
        # 시간 순서대로 생성한 여러 ID는 문자열 정렬 시 생성 순서와 일치
        ids = []
        for _ in range(10):
            ids.append(_uuid7_hex())
            time.sleep(0.002)  # 2ms 간격 — ms 해상도 타임스탬프 변화 보장
        assert ids == sorted(ids)

    def test_uniqueness(self):
        # 동일 ms 내 대량 생성해도 충돌 없음 (rand_b 62bit 덕)
        ids = {_uuid7_hex() for _ in range(10000)}
        assert len(ids) == 10000

    def test_uniqueness_in_same_ms(self, monkeypatch):
        """time을 freeze해서 정확히 같은 ms 내에서도 충돌 없음 검증."""
        fixed = 1745000000.123  # 임의 고정 시각
        monkeypatch.setattr("common.ids.time.time", lambda: fixed)
        ids = {_uuid7_hex() for _ in range(10000)}
        assert len(ids) == 10000
        # 모두 같은 timestamp prefix 가져야 함
        ts_prefixes = {i[:12] for i in ids}
        assert len(ts_prefixes) == 1


class TestGenerateId:
    def test_format(self):
        v = generate_id("usr")
        assert v.startswith("usr_")
        assert len(v) == len("usr_") + 32

    def test_prefix_required(self):
        with pytest.raises(ValueError):
            generate_id("")

    def test_prefix_no_underscore(self):
        with pytest.raises(ValueError):
            generate_id("us_r")

    def test_sort_order_across_ms(self):
        # 시간 순 = 사전 순 (단, 같은 ms 내 생성은 random이 결정 → ms 간격 둠)
        a = generate_id("usr")
        time.sleep(0.002)
        b = generate_id("usr")
        assert a < b
