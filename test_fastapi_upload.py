from fastapi import FastAPI, File, UploadFile, Request
from typing import List, Optional
import uvicorn
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

app = FastAPI()

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    print(f"Validation Error: {exc.errors()}")
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors(), "body": str(exc.body)},
    )

@app.post("/test")
async def test_upload(
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
    uvicorn.run(app, host="127.0.0.1", port=8002)
