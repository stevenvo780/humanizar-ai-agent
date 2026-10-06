"""Trusted PDF reader child: stdin bytes, stdout text, no application settings or API keys."""

import io
import logging
import resource
import sys


def extract(data: bytes, limit: int) -> str:
    from pypdf import PdfReader
    from pypdf.generic import ArrayObject, DictionaryObject, IndirectObject, PdfObject, StreamObject

    reader = PdfReader(io.BytesIO(data), strict=True)
    if reader.is_encrypted or len(reader.pages) > 250:
        raise ValueError("PDF encrypted or too many pages")
    identifiers = {
        (identifier, generation)
        for generation, objects in reader.xref.items()
        for identifier in objects
        if identifier
    }
    identifiers.update((identifier, 0) for identifier in reader.xref_objStm)
    # Streams can be embedded directly inside dictionaries/arrays, not only xref objects.
    pending: list[PdfObject] = [reader.trailer]
    pending.extend(
        IndirectObject(identifier, generation, reader) for identifier, generation in identifiers
    )
    visited_references: set[tuple[int, int]] = set()
    visited_objects: set[int] = set()
    decompressed, traversed = 0, 0
    while pending:
        obj = pending.pop()
        traversed += 1
        if traversed > 100000:
            raise ValueError("PDF object traversal budget exceeded")
        if isinstance(obj, IndirectObject):
            reference = (obj.idnum, obj.generation)
            if reference not in visited_references:
                visited_references.add(reference)
                resolved = reader.get_object(obj)
                if resolved is not None:
                    pending.append(resolved)
        elif isinstance(obj, (DictionaryObject, ArrayObject)):
            identifier = id(obj)
            if identifier in visited_objects:
                continue
            visited_objects.add(identifier)
            if isinstance(obj, StreamObject):
                decompressed += len(obj.get_data())
                if decompressed > limit:
                    raise ValueError("PDF decompression budget exceeded")
            pending.extend(obj.values() if isinstance(obj, DictionaryObject) else obj)
    parts: list[str] = []
    characters = 0
    for page in reader.pages:
        text = page.extract_text() or ""
        characters += len(text)
        if characters > limit:
            raise ValueError("PDF text budget exceeded")
        parts.append(text)
    return "\n\n".join(parts)


def main() -> int:
    sys.dont_write_bytecode = True
    logging.disable(logging.CRITICAL)
    resource.setrlimit(resource.RLIMIT_CPU, (4, 4))
    resource.setrlimit(resource.RLIMIT_AS, (384 * 1024 * 1024, 384 * 1024 * 1024))
    resource.setrlimit(resource.RLIMIT_FSIZE, (0, 0))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    try:
        limit, upload_limit = int(sys.argv[1]), int(sys.argv[2])
        if not (1 <= limit <= 200 * 1024 * 1024 and 1 <= upload_limit <= 100 * 1024 * 1024):
            return 2
        data = sys.stdin.buffer.read(upload_limit + 1)
        if len(data) > upload_limit or not data.startswith(b"%PDF-"):
            return 2
        text = extract(data, limit)
        sys.stdout.buffer.write(text.encode("utf-8"))
        return 0
    except Exception:
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
