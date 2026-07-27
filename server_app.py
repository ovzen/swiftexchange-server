# -*- coding: utf-8 -*-
import os
import argparse
from pathlib import Path
from datetime import datetime
from typing import List
import logging
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

parser = argparse.ArgumentParser()
parser.add_argument("--host", default="0.0.0.0")
parser.add_argument("--port", type=int, default=8000)
parser.add_argument("--upload-dir", default="uploads")
parser.add_argument("--max-size-mb", type=int, default=1024)
args = parser.parse_args()

UPLOAD_DIR = Path(args.upload_dir)
UPLOAD_DIR.mkdir(exist_ok=True, parents=True)
MAX_FILE_SIZE = args.max_size_mb * 1024 * 1024

app = FastAPI(title="SwiftExchange Server", version="2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

clipboard_text = ""

class FileInfo(BaseModel):
    name: str
    size: int
    modified: str

class ClipboardData(BaseModel):
    text: str

def get_file_info(filepath: Path) -> FileInfo:
    stat = filepath.stat()
    return FileInfo(
        name=filepath.name,
        size=stat.st_size,
        modified=datetime.fromtimestamp(stat.st_mtime).isoformat()
    )

@app.get("/files", response_model=List[FileInfo])
async def list_files():
    logger.info("Запрос списка файлов")
    files = []
    for f in UPLOAD_DIR.iterdir():
        if f.is_file():
            files.append(get_file_info(f))
    return files

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    logger.info(f"Загрузка: {file.filename}")
    safe_name = "".join(c for c in file.filename if c.isalnum() or c in "._- ")
    if not safe_name:
        safe_name = "unnamed"
    file_path = UPLOAD_DIR / safe_name
    size = 0
    try:
        with open(file_path, "wb") as f:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                size += len(chunk)
                if size > MAX_FILE_SIZE:
                    f.close()
                    os.remove(file_path)
                    raise HTTPException(413, "Файл слишком большой")
                f.write(chunk)
        logger.info(f"Сохранён: {safe_name}, {size} байт")
        return {"message": f"Файл '{safe_name}' загружен"}
    except Exception as e:
        if file_path.exists():
            os.remove(file_path)
        raise HTTPException(500, f"Ошибка: {str(e)}")

@app.get("/download/{filename}")
async def download_file(filename: str):
    safe_name = "".join(c for c in filename if c.isalnum() or c in "._- ")
    file_path = UPLOAD_DIR / safe_name
    if not file_path.exists():
        raise HTTPException(404, "Файл не найден")
    return FileResponse(path=file_path, filename=safe_name)

@app.delete("/delete/{filename}")
async def delete_file(filename: str):
    safe_name = "".join(c for c in filename if c.isalnum() or c in "._- ")
    file_path = UPLOAD_DIR / safe_name
    if not file_path.exists():
        raise HTTPException(404, "Файл не найден")
    os.remove(file_path)
    return {"message": f"Файл '{safe_name}' удалён"}

@app.get("/clipboard")
async def get_clipboard():
    return {"text": clipboard_text}

@app.post("/clipboard")
async def set_clipboard(data: ClipboardData):
    global clipboard_text
    clipboard_text = data.text[:10000]
    logger.info(f"Буфер обмена обновлён: {clipboard_text[:50]}...")
    return {"message": "Буфер обмена обновлён"}

@app.exception_handler(Exception)
async def generic_handler(request, exc):
    logger.error(f"Ошибка: {exc}", exc_info=True)
    return JSONResponse(500, {"detail": str(exc)})

if __name__ == "__main__":
    uvicorn.run(app, host=args.host, port=args.port, timeout_keep_alive=300)