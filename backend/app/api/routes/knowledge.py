"""Knowledge base: semantic search and administrator document management."""

import asyncio
from typing import Annotated, Any

from fastapi import APIRouter, File, HTTPException, Query, Response, UploadFile
from starlette.requests import Request

from app.api.dependencies import ScopedAdmin, ScopedUser, SettingsDep, StoreDep
from app.api.schemas import DocumentDetail, DocumentList, UploadResponse
from app.core.concurrency import run_sync
from app.knowledge.ingestion import IngestionError, parse_upload

router = APIRouter(prefix="/api", tags=["knowledge"])


@router.get("/search")
async def search(
    query: Annotated[str, Query(min_length=1, max_length=1000)],
    _user: ScopedUser,
    store: StoreDep,
) -> dict[str, Any]:
    sources = await run_sync(store.search, query)
    return {"sources": [source.model_dump() for source in sources]}


@router.get("/documents", response_model=DocumentList)
def documents(_user: ScopedAdmin, store: StoreDep) -> DocumentList:
    return store.list_documents()


@router.post("/documents", response_model=UploadResponse)
async def upload(
    request: Request,
    file: Annotated[UploadFile, File()],
    _user: ScopedAdmin,
    config: SettingsDep,
    store: StoreDep,
) -> UploadResponse:
    # One ingestion at a time: parsing and embedding are CPU and memory bound.
    slots: asyncio.Semaphore = request.app.state.ingestion_slots
    await slots.acquire()
    data = bytearray()
    limit = config.max_upload_mb * 1024 * 1024
    try:
        while block := await file.read(65536):
            data.extend(block)
            if len(data) > limit:
                raise HTTPException(413, "El archivo excede el tamaño permitido.")
        parsed, skipped = await run_sync(parse_upload, file.filename or "", bytes(data), config)
        created = await run_sync(store.add_documents, parsed)
        current = await run_sync(store.list_documents)
        return UploadResponse(documents=created, total_chunks=current.total_chunks, skipped=skipped)
    except IngestionError as exc:
        raise HTTPException(422, str(exc)) from exc
    finally:
        slots.release()
        await file.close()


@router.get("/documents/{document_id}", response_model=DocumentDetail)
async def document_detail(
    document_id: str, response: Response, _user: ScopedAdmin, store: StoreDep
) -> DocumentDetail:
    detail = await run_sync(store.get_document, document_id)
    if detail is None:
        raise HTTPException(404, "Documento no encontrado.")
    response.headers["Cache-Control"] = "no-store"
    return detail


@router.delete("/documents/{document_id}", status_code=204)
def delete(document_id: str, _user: ScopedAdmin, store: StoreDep) -> Response:
    if not store.delete(document_id):
        raise HTTPException(404, "Documento no encontrado.")
    return Response(status_code=204)
