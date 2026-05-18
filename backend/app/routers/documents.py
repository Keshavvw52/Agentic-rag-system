"""Document management endpoints: upload, list, delete."""

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, status
from app.auth.jwt_handler import get_current_user
from app.services.ingestion import ingest_document, delete_document, list_documents
from app.schemas.schemas import DocumentResponse

router = APIRouter()

ALLOWED_TYPES = {
    "application/pdf", "text/plain",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/msword",
}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB


@router.post("/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    """Upload and ingest a document (PDF, TXT, DOCX)."""
    if file.content_type not in ALLOWED_TYPES:
        # Also allow by extension
        ext = (file.filename or "").rsplit(".", 1)[-1].lower()
        if ext not in ("pdf", "txt", "docx", "doc", "md"):
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type: {file.content_type}. Allowed: PDF, TXT, DOCX",
            )

    file_bytes = await file.read()
    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large (max 50MB)")

    try:
        doc = await ingest_document(
            file_bytes=file_bytes,
            filename=file.filename or "document",
            content_type=file.content_type or "text/plain",
            user_id=current_user["id"],
        )
        return DocumentResponse(
            id=str(doc["_id"]),
            filename=doc["filename"],
            file_type=doc["file_type"],
            chunk_count=doc["chunk_count"],
            status=doc["status"],
            created_at=doc["created_at"],
            user_id=doc["user_id"],
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")


@router.get("")
async def list_docs(current_user: dict = Depends(get_current_user)):
    """List all documents for the current user."""
    docs = await list_documents(current_user["id"])
    return {"documents": [
        DocumentResponse(
            id=str(d["_id"]),
            filename=d["filename"],
            file_type=d["file_type"],
            chunk_count=d["chunk_count"],
            status=d["status"],
            created_at=d["created_at"],
            user_id=d["user_id"],
        )
        for d in docs
    ]}


@router.delete("/{document_id}")
async def delete_doc(
    document_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Delete a document and all its vector embeddings."""
    deleted = await delete_document(document_id, current_user["id"])
    if not deleted:
        raise HTTPException(status_code=404, detail="Document not found")
    return {"message": "Document deleted successfully"}