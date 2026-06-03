"""FastAPI 서버 — 캡컷 에이전트"""
from __future__ import annotations

import os
import uuid
from pathlib import Path

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from .pipeline import process

UPLOAD_DIR = Path("/tmp/capcut_uploads")
DRAFT_DIR = Path("/tmp/capcut_drafts")
UPLOAD_DIR.mkdir(exist_ok=True)
DRAFT_DIR.mkdir(exist_ok=True)

app = FastAPI(title="CapCut Agent")

# ── 정적 파일 ─────────────────────────────────────────────────
_static = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(_static)), name="static")


@app.get("/")
async def index():
    return FileResponse(str(_static / "index.html"))


# ── 영상 업로드 ──────────────────────────────────────────────
@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    ext = Path(file.filename).suffix.lower()
    if ext not in {".mp4", ".mov", ".avi", ".mkv", ".webm"}:
        return {"error": "지원하지 않는 형식입니다."}

    job_id = uuid.uuid4().hex
    dest = UPLOAD_DIR / f"{job_id}{ext}"
    content = await file.read()
    dest.write_bytes(content)

    return {"job_id": job_id, "filename": file.filename, "size": len(content)}


# ── SSE 처리 스트림 ───────────────────────────────────────────
@app.get("/process/{job_id}")
async def process_video(
    job_id: str,
    silence_db: float = -40.0,
    min_silence: float = 0.4,
    whisper_model: str = "base",
    language: str = "ko",
):
    # 업로드된 파일 찾기
    matches = list(UPLOAD_DIR.glob(f"{job_id}.*"))
    if not matches:
        async def err():
            yield 'data: {"step":"error","pct":0,"msg":"파일을 찾을 수 없습니다."}\n\n'
        return StreamingResponse(err(), media_type="text/event-stream")

    video_path = str(matches[0])

    return StreamingResponse(
        process(
            video_path=video_path,
            draft_base=str(DRAFT_DIR),
            silence_db=silence_db,
            min_silence=min_silence,
            whisper_model=whisper_model,
            language=language,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# ── 드래프트 다운로드 (ZIP) ───────────────────────────────────
@app.get("/download/{job_id}")
async def download_draft(job_id: str):
    import zipfile, io, tempfile

    matches = list(UPLOAD_DIR.glob(f"{job_id}.*"))
    if not matches:
        return {"error": "Not found"}

    video_name = Path(matches[0]).stem
    draft_dir = DRAFT_DIR / video_name

    if not draft_dir.exists():
        return {"error": "드래프트가 아직 생성되지 않았습니다."}

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in draft_dir.rglob("*"):
            if f.is_file():
                zf.write(f, f.relative_to(draft_dir.parent))
    buf.seek(0)

    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{video_name}_draft.zip"'},
    )
