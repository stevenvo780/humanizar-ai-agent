"""Softop FAQ Bot: POST /preguntar responde sólo con faq.json usando RAG."""

from functools import lru_cache
from pathlib import Path
from typing import Annotated

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field

from base.llm import LLM, NO_INFO, SYSTEM_PROMPT, LLMUnavailable, build_prompt, make_llm
from base.rag import FaqIndex, build_index

load_dotenv()
FAQ_PATH = Path(__file__).with_name("faq.json")

app = FastAPI(title="Softop FAQ Bot")


class Pregunta(BaseModel):
    pregunta: str = Field(min_length=1, max_length=1000)


class Respuesta(BaseModel):
    respuesta: str


@lru_cache
def get_index() -> FaqIndex:
    return build_index(FAQ_PATH)


@lru_cache
def get_llm() -> LLM:
    return make_llm()


@app.get("/")
def hello_world() -> dict[str, str]:
    return {"status": "ok", "message": "hello world"}


@app.post("/preguntar", response_model=Respuesta)
def preguntar(
    body: Pregunta,
    index: Annotated[FaqIndex, Depends(get_index)],
) -> Respuesta:
    # 1) Recuperar: sin fragmentos relevantes no se llama al modelo (evita inventar y gastar).
    hits = index.search(body.pregunta, k=3)
    if not hits:
        return Respuesta(respuesta=NO_INFO)
    # 2) Aumentar: el prompt inyecta sólo esos fragmentos y restringe al modelo a ellos.
    prompt = build_prompt(body.pregunta, hits)
    # 3) Generar.
    try:
        answer = get_llm().complete(SYSTEM_PROMPT, prompt).strip()
    except LLMUnavailable as exc:
        raise HTTPException(503, str(exc)) from exc
    except Exception as exc:  # error del proveedor: mensaje genérico, sin detalles internos
        raise HTTPException(503, "El modelo de lenguaje no está disponible.") from exc
    return Respuesta(respuesta=answer or NO_INFO)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("base.app:app", host="127.0.0.1", port=8000)
