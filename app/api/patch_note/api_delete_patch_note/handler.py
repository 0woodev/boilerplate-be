from common.awslambda.response_handler import ResponseHandler
from common.awslambda.request_util import get_path_params
from common.access import require_authenticated_user

from common.models import PatchNote

ROUTE = ("DELETE", "/patch-notes/{patch_note_id}")


@ResponseHandler.api
def handler(event, context):
    require_authenticated_user(event)
    patch_note_id = get_path_params(event).get("patch_note_id")

    PatchNote.delete_by_key(patch_note_id=patch_note_id)
    return None
