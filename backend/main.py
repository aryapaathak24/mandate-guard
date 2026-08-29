"""Agentic Guard backend entrypoint."""

from fastapi import FastAPI

app = FastAPI(title="Agentic Guard")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}