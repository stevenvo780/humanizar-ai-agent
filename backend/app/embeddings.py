import hashlib
import math
import re
import unicodedata
from collections import Counter
from typing import Protocol

from app.settings import Settings

STOPWORDS = frozenset(
    [
        "a",
        "al",
        "algo",
        "and",
        "are",
        "as",
        "at",
        "con",
        "cual",
        "cuales",
        "como",
        "de",
        "del",
        "desde",
        "el",
        "en",
        "es",
        "esta",
        "este",
        "for",
        "hay",
        "how",
        "in",
        "is",
        "la",
        "las",
        "lo",
        "los",
        "me",
        "mi",
        "of",
        "on",
        "or",
        "para",
        "por",
        "que",
        "se",
        "su",
        "the",
        "to",
        "un",
        "una",
        "y",
        "what",
        "which",
        "who",
        "your",
        "puedes",
        "podrias",
        "favor",
        "saber",
        "quiero",
        "son",
        "tiene",
        "tienen",
        "sobre",
    ]
)

SYNONYMS = {
    **dict.fromkeys(
        [
            "precios",
            "pricing",
            "cuesta",
            "cuestan",
            "coste",
            "costo",
            "tarifa",
            "tarifas",
            "price",
            "sale",
            "cost",
        ],
        "precio",
    ),
    **dict.fromkeys(["planes", "plans"], "plan"),
    **dict.fromkeys(["integraciones", "integrations", "integracion", "integrar"], "integracion"),
    **dict.fromkeys(["support", "ayuda"], "soporte"),
    **dict.fromkeys(["horarios", "hours"], "horario"),
    **dict.fromkeys(["mensual", "mensuales", "meses", "monthly"], "mes"),
    **dict.fromkeys(["fundada", "fundado", "fundo", "founded", "fundacion"], "fundacion"),
}
QUESTION_WORDS = frozenset(
    [
        "quien",
        "cuanto",
        "cuantos",
        "cuando",
        "donde",
        "dime",
        "dinos",
        "informacion",
        "empresa",
        "company",
        "acerca",
        "tengo",
        "necesito",
        "saber",
        "favor",
        "what",
        "tell",
    ]
)


def terms(text: str) -> list[str]:
    normalized = unicodedata.normalize("NFKD", text.casefold())
    normalized = "".join(char for char in normalized if not unicodedata.combining(char))
    return [
        SYNONYMS.get(term, term)
        for term in re.findall(r"[a-z0-9]+", normalized)
        if term not in STOPWORDS
    ]


class Embedder(Protocol):
    dimension: int
    signature: str

    def embed(self, texts: list[str]) -> list[list[float]]: ...


class HashEmbedder:
    dimension = 384
    signature = "lexical-hash-v1-384"

    def embed(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for text in texts:
            counts = Counter(terms(text))
            vector = [0.0] * self.dimension
            for term, count in counts.items():
                digest = hashlib.blake2b(term.encode(), digest_size=8).digest()
                index = int.from_bytes(digest, "little") % self.dimension
                vector[index] += 1 + math.log(count)
            norm = math.sqrt(sum(value * value for value in vector)) or 1.0
            vectors.append([value / norm for value in vector])
        return vectors


class SemanticEmbedder:
    def __init__(self, model_name: str, threads: int = 2) -> None:
        try:
            from fastembed import TextEmbedding
        except ImportError as exc:
            raise RuntimeError("Install backend[semantic] to enable FastEmbed") from exc
        self._model = TextEmbedding(model_name=model_name, threads=threads)
        self.signature = "fastembed-" + hashlib.sha256(model_name.encode()).hexdigest()[:12]
        self.dimension = len(self.embed(["dimension probe"])[0])

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [[float(value) for value in vector] for vector in self._model.embed(texts)]


def create_embedder(settings: Settings) -> Embedder:
    if settings.embedding_provider == "hash":
        return HashEmbedder()
    return SemanticEmbedder(settings.fastembed_model, settings.fastembed_threads)
