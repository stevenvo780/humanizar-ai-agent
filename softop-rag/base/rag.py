"""Recuperación sobre faq.json: vectores en memoria (numpy) y similitud coseno.

Por defecto usa TF-IDF local (10 FAQs: determinista, sin coste ni latencia de red). Si hay
OPENAI_API_KEY, usa embeddings semánticos de OpenAI con el mismo índice y la misma búsqueda.
"""

from __future__ import annotations

import json
import os
import re
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import numpy as np

STOPWORDS = frozenset(
    "a al como con cual cuando de del el en es esta este la las le lo los mas me mi mis o para "
    "por que se si sin su sus te tu un una uno unos y ya yo hago hacer puedo debo".split()
)
SUFFIXES = ("aciones", "acion", "iones", "ion", "ando", "iendo", "ar", "er", "ir", "es", "s")
Embed = Callable[[list[str]], np.ndarray]


@dataclass(frozen=True)
class Faq:
    id: int
    pregunta: str
    respuesta: str

    @property
    def texto(self) -> str:
        return f"{self.pregunta}\n{self.respuesta}"


def load_faqs(path: Path) -> list[Faq]:
    items = json.loads(path.read_text(encoding="utf-8"))
    return [Faq(int(item["id"]), str(item["pregunta"]), str(item["respuesta"])) for item in items]


def tokens(text: str) -> list[str]:
    """Minúsculas, sin tildes ni stopwords y con un stemming ligero del español."""
    plain = unicodedata.normalize("NFKD", text.lower()).encode("ascii", "ignore").decode()
    result = []
    for word in re.findall(r"[a-z0-9]+", plain):
        if word in STOPWORDS or len(word) < 3:
            continue
        for suffix in SUFFIXES:
            if word.endswith(suffix) and len(word) - len(suffix) >= 4:
                word = word[: -len(suffix)]
                break
        result.append(word)
    return result


class TfidfEmbedder:
    """Vectores TF-IDF normalizados; el vocabulario sale del propio documento de FAQ."""

    def __init__(self, corpus: list[str]) -> None:
        docs = [tokens(text) for text in corpus]
        self.vocab = {term: i for i, term in enumerate(sorted({t for d in docs for t in d}))}
        df = np.zeros(len(self.vocab))
        for doc in docs:
            for term in set(doc):
                df[self.vocab[term]] += 1
        self.idf = np.log((1 + len(docs)) / (1 + df)) + 1

    def __call__(self, texts: list[str]) -> np.ndarray:
        matrix = np.zeros((len(texts), len(self.vocab)))
        for row, text in enumerate(texts):
            for term in tokens(text):
                if term in self.vocab:
                    matrix[row, self.vocab[term]] += 1
        return matrix * self.idf


def openai_embedder(model: str = "text-embedding-3-small") -> Embed:
    from openai import OpenAI

    client = OpenAI()

    def embed(texts: list[str]) -> np.ndarray:
        response = client.embeddings.create(model=model, input=texts)
        return np.array([item.embedding for item in response.data])

    return embed


def normalize(matrix: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    return np.divide(matrix, norms, out=np.zeros_like(matrix), where=norms > 0)


class FaqIndex:
    """Índice vectorial en memoria: una fila por FAQ (pregunta + respuesta)."""

    def __init__(self, faqs: list[Faq], embed: Embed, min_score: float) -> None:
        self.faqs, self.embed, self.min_score = faqs, embed, min_score
        self.matrix = normalize(embed([faq.texto for faq in faqs]))

    def search(self, question: str, k: int = 3) -> list[tuple[Faq, float]]:
        query = normalize(self.embed([question]))[0]
        if not query.any():
            return []
        scores = self.matrix @ query
        ranked = np.argsort(-scores)[:k]
        return [(self.faqs[i], float(scores[i])) for i in ranked if scores[i] >= self.min_score]


def build_index(path: Path) -> FaqIndex:
    faqs = load_faqs(path)
    if os.getenv("OPENAI_API_KEY") and os.getenv("EMBEDDINGS", "openai") == "openai":
        return FaqIndex(faqs, openai_embedder(), min_score=float(os.getenv("MIN_SCORE", "0.3")))
    return FaqIndex(faqs, TfidfEmbedder([f.texto for f in faqs]), float(os.getenv("MIN_SCORE", "0.1")))
