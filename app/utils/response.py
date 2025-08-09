from typing import Any, Optional


def api_response(
    *,
    success: bool = True,
    status_code: int = 200,
    message: str = "",
    data: Optional[Any] = None,
) -> dict:
    return {
        "success": success,
        "statusCode": status_code,
        "message": message,
        "data": data or {},
    }
