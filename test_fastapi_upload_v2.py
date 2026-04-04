from fastapi import FastAPI, File, UploadFile, Request
from typing import List, Optional
import uvicorn
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from functools import wraps

app = FastAPI()

def requires_permission(action: str):
    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            print(f"Checking permission for {action}")
            return await func(request, *args, **kwargs)
        return wrapper
    return decorator

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    print(f"Validation Error: {exc.errors()}")
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors(), "body": str(exc.body)},
    )

@app.post("/test")
@requires_permission("run_audit")
async def test_upload(
    request: Request,
    config: Optional[UploadFile] = File(None),
    source_files: Optional[List[UploadFile]] = File(None),
    target_files: Optional[List[UploadFile]] = File(None),
):
    return {
        "config": config.filename if config else None,
        "source_files": [f.filename for f in source_files] if source_files else [],
        "target_files": [f.filename for f in target_files] if target_files else []
    }

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8003)
