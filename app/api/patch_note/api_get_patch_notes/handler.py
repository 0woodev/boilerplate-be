from common.awslambda.response_handler import ResponseHandler

from common.models import PatchNote

ROUTE = ("GET", "/patch-notes")


@ResponseHandler.api
def handler(event, context):
    # GET 은 공개. ByDate GSI 는 date#updated_at SK 오름차순으로 반환되므로
    # reverse 하여 date 내림차순(동일 date면 updated_at 내림차순)으로 제공한다.
    notes, _ = PatchNote.ByDate.query()
    notes.reverse()
    return {
        "patch_notes": [n.model_dump() for n in notes],
    }
