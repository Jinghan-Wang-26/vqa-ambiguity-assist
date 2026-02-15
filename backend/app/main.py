import os

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from .pipeline import iter_choose, iter_start, one_pass, scene_only
from .schemas import (
    IterChooseRequest,
    IterChooseResponse,
    IterStartResponse,
    OnePassResponse,
    SceneResponse,
)
from .utils import sha256_bytes, to_data_url
from .video import video_iter_choose, video_iter_start, video_onepass

load_dotenv()
FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://localhost:3000")

app = FastAPI(title="Ambiguity-Aware VQA Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_ORIGIN],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/v1/video/onepass")
async def v1_video_onepass(
    video: UploadFile = File(...), question: str = Form(...)
):
    b = await video.read()
    return video_onepass(
        b, question, cache_key=video.filename, filename=video.filename
    )


@app.post("/v1/scene", response_model=SceneResponse)
async def v1_scene(image: UploadFile = File(...), question: str = Form(...)):
    data = await image.read()
    mime = image.content_type or "image/png"
    data_url = to_data_url(data, mime)
    cache_key = sha256_bytes(data)
    inv, amb = scene_only(data_url, question, cache_key=cache_key)
    return SceneResponse(inventory=inv, ambiguity=amb)


@app.post("/v1/onepass", response_model=OnePassResponse)
async def v1_onepass(image: UploadFile = File(...), question: str = Form(...)):
    data = await image.read()
    mime = image.content_type or "image/png"
    data_url = to_data_url(data, mime)
    cache_key = sha256_bytes(data)
    return one_pass(data_url, question, cache_key=cache_key)


@app.post("/v1/iter/start", response_model=IterStartResponse)
async def v1_iter_start(
    image: UploadFile = File(...), question: str = Form(...)
):
    data = await image.read()
    mime = image.content_type or "image/png"
    data_url = to_data_url(data, mime)
    cache_key = sha256_bytes(data)
    return iter_start(data_url, question, cache_key=cache_key)


@app.post("/v1/iter/choose", response_model=IterChooseResponse)
async def v1_iter_choose(req: IterChooseRequest):
    return iter_choose(req.session_id, req.chosen)


@app.post("/v1/video/iter/start")
async def v1_video_iter_start(
    video: UploadFile = File(...), question: str = Form(...)
):
    b = await video.read()
    return video_iter_start(
        b, question, cache_key=video.filename, filename=video.filename
    )


@app.post("/v1/video/iter/choose")
async def v1_video_iter_choose(
    session_id: str = Form(...), chosen: str = Form(...)
):
    # 这里用 Form 是为了前端也可用 FormData，统一
    return video_iter_choose(session_id, chosen)
