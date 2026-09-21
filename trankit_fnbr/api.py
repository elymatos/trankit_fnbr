from typing import Any, Dict, Protocol

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, field_validator


class FNBrPipeline(Protocol):
    def analyze(self, text: str, top_k: int = 3) -> Dict[str, Any]:
        ...


class AnalysisRequest(BaseModel):
    text: str
    top_k: int = Field(default=3, ge=1, le=15)

    @field_validator("text")
    @classmethod
    def text_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("text must not be blank")
        return value


def create_app(pipeline: FNBrPipeline) -> FastAPI:
    app = FastAPI(title="Trankit FNBr", version="0.1.0")
    initializer = getattr(pipeline, "initialize", None)
    if initializer is not None:
        app.add_event_handler("startup", initializer)

    @app.post("/fnbr/", summary="Analyze raw text with the self-contained FNBr pipeline")
    def analyze(request: AnalysisRequest) -> Dict[str, Any]:
        try:
            return pipeline.analyze(request.text, top_k=request.top_k)
        except (ConnectionError, TimeoutError) as error:
            raise HTTPException(status_code=503, detail="FNBr lexicon is unavailable") from error

    return app
