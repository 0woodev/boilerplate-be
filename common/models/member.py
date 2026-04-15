from typing import ClassVar

from common.dynamo import DynamoModel, GSI


class Member(DynamoModel):
    """
    Group-User 관계 (role 포함).

    기본 테이블은 "그룹의 멤버 리스트" 쿼리가 주 용도이므로 group_id 를 PK로.
    "유저가 속한 그룹" 은 ByUser GSI, "그룹 내 역할별" 은 ByRole GSI.
    """

    table_name:  ClassVar[str] = "{project_name}-{stage}-members"
    pk_attr:     ClassVar[str] = "PK"
    sk_attr:     ClassVar[str] = "SK"
    pk_template: ClassVar[str] = "GROUP_ID@{group_id}"
    sk_template: ClassVar[str] = "USER_ID@{user_id}"

    group_id:  str = ""
    user_id:   str = ""
    role:      str = "member"       # owner | admin | member
    joined_at: str = ""

    class ByUser(GSI):
        pk_attr:     ClassVar[str] = "ByUserPK"
        sk_attr:     ClassVar[str] = "ByUserSK"
        pk_template: ClassVar[str] = "USER_ID@{user_id}"
        sk_template: ClassVar[str] = "GROUP_ID@{group_id}"

    class ByRole(GSI):
        pk_attr:     ClassVar[str] = "ByRolePK"
        sk_attr:     ClassVar[str] = "ByRoleSK"
        pk_template: ClassVar[str] = "GROUP_ID@{group_id}#ROLE@{role}"
        sk_template: ClassVar[str] = "USER_ID@{user_id}"
