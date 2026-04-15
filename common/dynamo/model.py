"""DynamoDB Active Record model + GSI definitions.

See DynamoConcept.md for the complete spec.
"""
import os
from typing import Any, ClassVar, Self

from pydantic import BaseModel, ConfigDict

from .client import DynamoClient, QueryMethod
from .keys import render_full, render_partial


class GSI:
    """
    Base class for nested GSI definitions within a DynamoModel.

    Subclasses declare:
      - pk_attr / sk_attr (DB column names — must match terraform)
      - pk_template / sk_template (value rules, same convention as main keys)

    Access: `User.ByEmail.query(email="...")` etc.
    """

    _parent: ClassVar[type["DynamoModel"] | None] = None

    pk_attr:     ClassVar[str] = ""
    sk_attr:     ClassVar[str | None] = None
    pk_template: ClassVar[str] = ""
    sk_template: ClassVar[str | None] = None

    @classmethod
    def index_name(cls) -> str:
        """GSI name for IndexName param; defaults to class name (e.g. 'ByEmail')."""
        return cls.__name__

    @classmethod
    def query(cls, instance=None, *, limit=None, cursor=None, **fields):
        return cls._parent._query_auto(
            _KeySpec.from_gsi(cls), instance, limit, cursor, fields
        )

    @classmethod
    def query_starts_with(cls, instance=None, *, limit=None, cursor=None, **fields):
        return cls._parent._query_starts_with(
            _KeySpec.from_gsi(cls), instance, limit, cursor, fields
        )

    @classmethod
    def query_gt(cls, instance=None, *, limit=None, cursor=None, **fields):
        return cls._parent._query_range(
            _KeySpec.from_gsi(cls), QueryMethod.GT,
            instance, limit, cursor, fields,
        )

    @classmethod
    def query_gte(cls, instance=None, *, limit=None, cursor=None, **fields):
        return cls._parent._query_range(
            _KeySpec.from_gsi(cls), QueryMethod.GTE,
            instance, limit, cursor, fields,
        )

    @classmethod
    def query_lt(cls, instance=None, *, limit=None, cursor=None, **fields):
        return cls._parent._query_range(
            _KeySpec.from_gsi(cls), QueryMethod.LT,
            instance, limit, cursor, fields,
        )

    @classmethod
    def query_lte(cls, instance=None, *, limit=None, cursor=None, **fields):
        return cls._parent._query_range(
            _KeySpec.from_gsi(cls), QueryMethod.LTE,
            instance, limit, cursor, fields,
        )

    @classmethod
    def query_between(cls, instance=None, *, start: dict, end: dict,
                      limit=None, cursor=None, **fields):
        return cls._parent._query_between(
            _KeySpec.from_gsi(cls),
            start, end, instance, limit, cursor, fields,
        )


class _KeySpec:
    """Internal — bundles pk/sk attr+template for main table or a GSI."""

    def __init__(self, index_name, pk_attr, sk_attr, pk_template, sk_template):
        self.index_name = index_name
        self.pk_attr = pk_attr
        self.sk_attr = sk_attr
        self.pk_template = pk_template
        self.sk_template = sk_template

    @classmethod
    def from_main(cls, model_cls: type["DynamoModel"]) -> "_KeySpec":
        return cls(
            index_name=None,
            pk_attr=model_cls.pk_attr,
            sk_attr=model_cls.sk_attr,
            pk_template=model_cls.pk_template,
            sk_template=model_cls.sk_template,
        )

    @classmethod
    def from_gsi(cls, gsi_cls: type[GSI]) -> "_KeySpec":
        return cls(
            index_name=gsi_cls.index_name(),
            pk_attr=gsi_cls.pk_attr,
            sk_attr=gsi_cls.sk_attr,
            pk_template=gsi_cls.pk_template,
            sk_template=gsi_cls.sk_template,
        )


class DynamoModel(BaseModel):
    """
    Active Record base for DynamoDB entities.

    Subclass declares:
      - table_name (template with {project_name} / {stage})
      - pk_attr / sk_attr (main table column names)
      - pk_template / sk_template (value rules)
      - fields (pydantic fields)
      - optional nested GSI classes

    See DynamoConcept.md for the full spec.
    """

    model_config = ConfigDict(extra="allow")

    table_name:  ClassVar[str] = ""
    pk_attr:     ClassVar[str] = "PK"
    sk_attr:     ClassVar[str | None] = "SK"
    pk_template: ClassVar[str] = ""
    sk_template: ClassVar[str | None] = None

    # set by __init_subclass__ — list of nested GSI classes on this subclass
    _gsis: ClassVar[list[type[GSI]]] = []

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        gsis = []
        for _, attr in cls.__dict__.items():
            if isinstance(attr, type) and issubclass(attr, GSI) and attr is not GSI:
                attr._parent = cls
                gsis.append(attr)
        cls._gsis = gsis

    # ── table name ────────────────────────────────────────────
    @classmethod
    def _resolved_table(cls) -> str:
        return cls.table_name.format(
            project_name=os.environ["PROJECT_NAME"],
            stage=os.environ["STAGE"],
        )

    # ── serialization ─────────────────────────────────────────
    def to_item(self) -> dict[str, Any]:
        data = self.model_dump()
        # Main table keys (required)
        data[self.pk_attr] = render_full(self.pk_template, data)
        if self.sk_template is not None and self.sk_attr:
            data[self.sk_attr] = render_full(self.sk_template, data)
        # GSI keys (sparse — skip if fields missing)
        for gsi in self._gsis:
            try:
                pk_val = render_full(gsi.pk_template, data)
            except ValueError:
                continue
            if gsi.sk_template is not None and gsi.sk_attr:
                try:
                    sk_val = render_full(gsi.sk_template, data)
                except ValueError:
                    continue
                data[gsi.pk_attr] = pk_val
                data[gsi.sk_attr] = sk_val
            else:
                data[gsi.pk_attr] = pk_val
        return data

    @classmethod
    def from_item(cls, item: dict) -> Self:
        internals: set[str] = {cls.pk_attr}
        if cls.sk_attr:
            internals.add(cls.sk_attr)
        for gsi in cls._gsis:
            internals.add(gsi.pk_attr)
            if gsi.sk_attr:
                internals.add(gsi.sk_attr)
        return cls(**{k: v for k, v in item.items() if k not in internals})

    # ── CRUD (instance) ───────────────────────────────────────
    def save(self) -> None:
        DynamoClient.put(self._resolved_table(), self.to_item())

    def delete(self) -> None:
        data = self.model_dump()
        DynamoClient.delete(self._resolved_table(), self._build_key(data))

    # ── CRUD (class) ──────────────────────────────────────────
    @classmethod
    def get(cls, instance=None, **fields) -> Self | None:
        fields = cls._merge_instance(instance, fields)
        item = DynamoClient.get(cls._resolved_table(), cls._build_key(fields))
        return cls.from_item(item) if item else None

    @classmethod
    def update_by_key(cls, updates: dict, instance=None, **fields) -> Self:
        fields = cls._merge_instance(instance, fields)
        item = DynamoClient.update(
            cls._resolved_table(), cls._build_key(fields), updates,
        )
        return cls.from_item(item)

    @classmethod
    def delete_by_key(cls, instance=None, **fields) -> None:
        fields = cls._merge_instance(instance, fields)
        DynamoClient.delete(cls._resolved_table(), cls._build_key(fields))

    # ── Query (main table) ────────────────────────────────────
    @classmethod
    def query(cls, instance=None, *, limit=None, cursor=None, **fields):
        return cls._query_auto(
            _KeySpec.from_main(cls), instance, limit, cursor, fields,
        )

    @classmethod
    def query_starts_with(cls, instance=None, *, limit=None, cursor=None, **fields):
        return cls._query_starts_with(
            _KeySpec.from_main(cls), instance, limit, cursor, fields,
        )

    @classmethod
    def query_gt(cls, instance=None, *, limit=None, cursor=None, **fields):
        return cls._query_range(
            _KeySpec.from_main(cls), QueryMethod.GT,
            instance, limit, cursor, fields,
        )

    @classmethod
    def query_gte(cls, instance=None, *, limit=None, cursor=None, **fields):
        return cls._query_range(
            _KeySpec.from_main(cls), QueryMethod.GTE,
            instance, limit, cursor, fields,
        )

    @classmethod
    def query_lt(cls, instance=None, *, limit=None, cursor=None, **fields):
        return cls._query_range(
            _KeySpec.from_main(cls), QueryMethod.LT,
            instance, limit, cursor, fields,
        )

    @classmethod
    def query_lte(cls, instance=None, *, limit=None, cursor=None, **fields):
        return cls._query_range(
            _KeySpec.from_main(cls), QueryMethod.LTE,
            instance, limit, cursor, fields,
        )

    @classmethod
    def query_between(cls, instance=None, *, start: dict, end: dict,
                      limit=None, cursor=None, **fields):
        return cls._query_between(
            _KeySpec.from_main(cls),
            start, end, instance, limit, cursor, fields,
        )

    @classmethod
    def scan(cls, *, limit=None, cursor=None) -> tuple[list[Self], str | None]:
        items, next_cursor = DynamoClient.scan(
            cls._resolved_table(), limit=limit, cursor=cursor,
        )
        return [cls.from_item(it) for it in items], next_cursor

    # ── helpers ───────────────────────────────────────────────
    @classmethod
    def _merge_instance(cls, instance, fields: dict) -> dict:
        if instance is None:
            return fields
        return {**instance.model_dump(exclude_unset=True), **fields}

    @classmethod
    def _build_key(cls, fields: dict) -> dict:
        key = {cls.pk_attr: render_full(cls.pk_template, fields)}
        if cls.sk_template is not None and cls.sk_attr:
            key[cls.sk_attr] = render_full(cls.sk_template, fields)
        return key

    # ── query core (used by both main and GSI) ───────────────
    @classmethod
    def _query_auto(cls, spec: _KeySpec, instance, limit, cursor, fields):
        fields = cls._merge_instance(instance, fields)
        pk_value = render_full(spec.pk_template, fields)

        method = QueryMethod.EQ
        range_value = None
        range_key = None
        if spec.sk_template and spec.sk_attr:
            sk_value, is_complete = render_partial(spec.sk_template, fields)
            if sk_value:
                range_value = sk_value
                range_key = spec.sk_attr
                method = QueryMethod.EQ if is_complete else QueryMethod.BEGINS_WITH

        items, next_cursor = DynamoClient.query(
            cls._resolved_table(),
            index_name=spec.index_name,
            hash_key=spec.pk_attr,
            hash_value=pk_value,
            range_key=range_key,
            method=method,
            range_value=range_value,
            limit=limit,
            cursor=cursor,
        )
        return [cls.from_item(it) for it in items], next_cursor

    @classmethod
    def _query_starts_with(cls, spec: _KeySpec, instance, limit, cursor, fields):
        """Explicit begins_with — partial fields는 물론, 모든 필드가 채워져도
        EQ 로 수축시키지 않는다. 단일 placeholder SK에서 접두사 매칭 시 사용."""
        fields = cls._merge_instance(instance, fields)
        pk_value = render_full(spec.pk_template, fields)
        if not (spec.sk_template and spec.sk_attr):
            raise ValueError(
                f"{cls.__name__}: query_starts_with requires sk_template"
            )
        sk_value, _ = render_partial(spec.sk_template, fields)
        if not sk_value:
            raise ValueError(
                f"{cls.__name__}: query_starts_with requires at least one SK field"
            )
        items, next_cursor = DynamoClient.query(
            cls._resolved_table(),
            index_name=spec.index_name,
            hash_key=spec.pk_attr,
            hash_value=pk_value,
            range_key=spec.sk_attr,
            method=QueryMethod.BEGINS_WITH,
            range_value=sk_value,
            limit=limit,
            cursor=cursor,
        )
        return [cls.from_item(it) for it in items], next_cursor

    @classmethod
    def _query_range(cls, spec: _KeySpec, method: QueryMethod,
                     instance, limit, cursor, fields):
        fields = cls._merge_instance(instance, fields)
        pk_value = render_full(spec.pk_template, fields)
        if not (spec.sk_template and spec.sk_attr):
            raise ValueError(
                f"{cls.__name__}: {method.value} requires sk_template on this key"
            )
        sk_value, _ = render_partial(spec.sk_template, fields)
        if not sk_value:
            raise ValueError(
                f"{cls.__name__}: {method.value} requires at least one SK field"
            )
        items, next_cursor = DynamoClient.query(
            cls._resolved_table(),
            index_name=spec.index_name,
            hash_key=spec.pk_attr,
            hash_value=pk_value,
            range_key=spec.sk_attr,
            method=method,
            range_value=sk_value,
            limit=limit,
            cursor=cursor,
        )
        return [cls.from_item(it) for it in items], next_cursor

    @classmethod
    def _query_between(cls, spec: _KeySpec, start: dict, end: dict,
                       instance, limit, cursor, fields):
        fields = cls._merge_instance(instance, fields)
        pk_value = render_full(spec.pk_template, fields)
        if not (spec.sk_template and spec.sk_attr):
            raise ValueError(
                f"{cls.__name__}: query_between requires sk_template"
            )
        sv_start, _ = render_partial(spec.sk_template, start)
        sv_end, _ = render_partial(spec.sk_template, end)
        if not sv_start or not sv_end:
            raise ValueError(
                f"{cls.__name__}: query_between requires at least one SK field in start and end"
            )
        items, next_cursor = DynamoClient.query(
            cls._resolved_table(),
            index_name=spec.index_name,
            hash_key=spec.pk_attr,
            hash_value=pk_value,
            range_key=spec.sk_attr,
            method=QueryMethod.BETWEEN,
            range_value=sv_start,
            range_value2=sv_end,
            limit=limit,
            cursor=cursor,
        )
        return [cls.from_item(it) for it in items], next_cursor
