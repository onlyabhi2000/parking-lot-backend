from fastapi.responses import JSONResponse
from typing import Any

def standard_response(status_code: int, message: str, data: Any = None):
    return JSONResponse(
        status_code=status_code,
        content={
            "status_code": status_code,
            "message": message,
            "data": data
        }
    )

