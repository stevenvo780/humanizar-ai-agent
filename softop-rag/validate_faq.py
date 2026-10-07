"""Valida un despliegue de POST /preguntar contra faq.json: respuesta literal y casos negativos.

Uso: python validate_faq.py http://localhost:8000          (sólo librería estándar)
"""

import json
import sys
import time
import urllib.request
from pathlib import Path

NO_INFO = "No encuentro esa información en las preguntas frecuentes."
NEGATIVE = ["¿Cuánto cuesta un examen de la vista?", "¿Cuál es la capital de Francia?"]


def ask(base: str, question: str) -> tuple[str, float]:
    body = json.dumps({"pregunta": question}).encode()
    request = urllib.request.Request(
        f"{base.rstrip('/')}/preguntar", body, {"content-type": "application/json"}
    )
    start = time.perf_counter()
    with urllib.request.urlopen(request, timeout=60) as response:
        payload = json.loads(response.read())
    return payload["respuesta"], time.perf_counter() - start


def main() -> int:
    base = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
    faqs = json.loads(Path(__file__).with_name("base").joinpath("faq.json").read_text("utf-8"))
    cases = [(f["pregunta"], f["respuesta"]) for f in faqs] + [(q, NO_INFO) for q in NEGATIVE]
    failures = 0
    for question, expected in cases:
        answer, seconds = ask(base, question)
        ok = answer.strip() == expected
        failures += not ok
        print(f"{'OK ' if ok else 'DIF'} {seconds:4.1f}s  {question}")
        if not ok:
            print(f"     esperado: {expected}\n     recibido: {answer}")
    print(f"\n{len(cases) - failures}/{len(cases)} respuestas idénticas al texto de faq.json")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
