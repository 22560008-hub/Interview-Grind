from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from fastapi.staticfiles import StaticFiles
from app.api import questions, answers, wrong, stats, favorites
from app.core.config import settings
from app.core.database import Base, engine
from app.models import question, answer, favorite  # noqa: F401

Base.metadata.create_all(bind=engine)

app = FastAPI(title=settings.app_name, version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["系统"])
def health():
    return {"status": "ok", "app": settings.app_name}


app.include_router(questions.router)
app.include_router(answers.router)
app.include_router(wrong.router)
app.include_router(stats.router)
app.include_router(favorites.router)
app.mount("/", StaticFiles(directory="static", html=True), name="static")
