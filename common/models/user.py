from typing import ClassVar

from common.dynamo import DynamoModel, GSI


class User(DynamoModel):
    table_name:  ClassVar[str] = "{project_name}-{stage}-users"
    pk_attr:     ClassVar[str] = "PK"
    sk_attr:     ClassVar[str] = "SK"
    pk_template: ClassVar[str] = "USER_ID@{user_id}"
    sk_template: ClassVar[str] = "TYPE@profile"

    user_id:    str = ""
    email:      str = ""
    name:       str = ""
    status:     str = "active"          # active | suspended | deleted
    created_at: str = ""

    class ByEmail(GSI):
        pk_attr:     ClassVar[str] = "ByEmailPK"
        sk_attr:     ClassVar[str] = "ByEmailSK"
        pk_template: ClassVar[str] = "EMAIL@{email}"
        sk_template: ClassVar[str] = "TYPE@profile"

    class ByStatus(GSI):
        pk_attr:     ClassVar[str] = "ByStatusPK"
        sk_attr:     ClassVar[str] = "ByStatusSK"
        pk_template: ClassVar[str] = "STATUS@{status}"
        sk_template: ClassVar[str] = "CREATED_AT@{created_at}"
