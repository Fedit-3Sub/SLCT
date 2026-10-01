"""편집 토큰으로 쓰기 작업을 막는다.

`SLCT_EDIT_TOKEN` 이 설정돼 있으면 조회(GET 등)는 누구나 할 수 있고, 다이어그램
저장·로직 실행·LLM 생성·연합트윈 등록 같은 쓰기 작업은 토큰이 있어야 한다.
토큰은 `X-SLCT-Token` 헤더(편집기가 보냄) 또는 `?token=` 질의 문자열로 받는다.
비어 있으면 검사하지 않는다(로컬 개발).

연합트윈이 부르는 로직 호출(invoke)과 카탈로그 모의 경로는 토큰 없이 열어 둔다.
invoke 는 저장된 로직만 실행하고, 로직을 저장하려면 토큰이 필요하므로
외부에서 임의 주소를 서버가 호출하게 만들 수는 없다.
"""

import hmac
import os

from rest_framework.permissions import SAFE_METHODS, BasePermission

HEADER = "HTTP_X_SLCT_TOKEN"
PUBLIC_VIEWS = {"LogicInvokeView", "PipelineRunView", "EditTokenCheckView"}


def configured_token() -> str:
    return os.environ.get("SLCT_EDIT_TOKEN", "").strip()


def request_token(request) -> str:
    return (request.META.get(HEADER) or request.GET.get("token") or "").strip()


def is_editor(request) -> bool:
    expected = configured_token()
    if not expected:
        return True
    return hmac.compare_digest(request_token(request).encode(), expected.encode())


class EditTokenPermission(BasePermission):
    message = "수정하려면 편집 토큰이 필요합니다. 토큰이 포함된 주소(?token=...)로 접속하세요."

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        if type(view).__name__ in PUBLIC_VIEWS:
            return True
        return is_editor(request)
