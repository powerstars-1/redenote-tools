from fastapi import Request
from pydantic import BaseModel


def get_request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "req_unknown")


def build_success_response(*, request_id: str, data: BaseModel | dict) -> dict:
    payload = data.model_dump(mode="json") if isinstance(data, BaseModel) else data
    return {
        "success": True,
        "request_id": request_id,
        "data": payload,
        "error": None,
    }


def build_error_response(*, request_id: str, code: str, message: str) -> dict:
    return {
        "success": False,
        "request_id": request_id,
        "data": None,
        "error": {
            "code": code,
            "message": message,
        },
    }
