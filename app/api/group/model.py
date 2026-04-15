from typing import ClassVar

from common.dynamo import DynamoModel, GSI


class Group(DynamoModel):
    table_name:  ClassVar[str] = "{project_name}-{stage}-groups"
    pk_attr:     ClassVar[str] = "PK"
    sk_attr:     ClassVar[str] = "SK"
    pk_template: ClassVar[str] = "GROUP_ID@{group_id}"
    sk_template: ClassVar[str] = "TYPE@profile"

    group_id:       str = ""
    name:           str = ""
    description:    str = ""
    owner_user_id:  str = ""
    created_at:     str = ""

    class ByOwner(GSI):
        pk_attr:     ClassVar[str] = "ByOwnerPK"
        sk_attr:     ClassVar[str] = "ByOwnerSK"
        pk_template: ClassVar[str] = "OWNER_USER_ID@{owner_user_id}"
        sk_template: ClassVar[str] = "CREATED_AT@{created_at}"
