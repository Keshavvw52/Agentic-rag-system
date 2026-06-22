"""
Document ingestion service: upload, chunk, embed, and store documents.
Supports PDF, TXT, and DOCX formats with per-user isolation.
"""

import io
import uuid
from datetime import datetime, timezone
from typing import BinaryIO

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader, TextLoader, Docx2txtLoader, UnstructuredPDFLoader

from app.config.settings import settings
from app.db.chromadb import get_user_collection, embed_texts
from app.db.mongodb import get_database


SUPPORTED_TYPES = {
    "application/pdf": "pdf",
    "text/plain": "txt",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "application/msword": "doc",
}

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=settings.CHUNK_SIZE,
    chunk_overlap=settings.CHUNK_OVERLAP,
    separators=["\n\n", "\n", ". ", " ", ""],
)


async def ingest_document(
    file_bytes: bytes,
    filename: str,
    content_type: str,
    user_id: str,
) -> dict:
    """
    Full document ingestion pipeline:
    1. Extract text from file
    2. Split into chunks
    3. Generate embeddings
    4. Store in ChromaDB
    5. Store metadata in MongoDB
    """
    db = get_database()
    document_id = str(uuid.uuid4())

    # Determine file type
    file_ext = SUPPORTED_TYPES.get(content_type, filename.rsplit(".", 1)[-1].lower())

    # Extract text
    text_chunks = await _extract_text(file_bytes, filename, file_ext)

    if not text_chunks:
        raise ValueError("Could not extract text from document")

    # Create chunk documents with metadata
    chunks = []
    for i, chunk_text in enumerate(text_chunks):
        chunks.append({
            "text": chunk_text.page_content if hasattr(chunk_text, "page_content") else chunk_text,
            "chunk_index": i,
            "document_id": document_id,
            "filename": filename,
            "user_id": user_id,
        })

    # Generate embeddings
    texts = [c["text"] for c in chunks]
    embeddings = embed_texts(texts)

    # Store in ChromaDB (user-isolated collection)
    collection = get_user_collection(user_id)
    chunk_ids = [f"{document_id}_chunk_{i}" for i in range(len(chunks))]

    collection.add(
        ids=chunk_ids,
        embeddings=embeddings,
        documents=texts,
        metadatas=[{
            "document_id": c["document_id"],
            "filename": c["filename"],
            "user_id": c["user_id"],
            "chunk_index": c["chunk_index"],
        } for c in chunks],
    )

    # Store document metadata in MongoDB
    doc_record = {
        "_id": document_id,
        "user_id": user_id,
        "filename": filename,
        "file_type": file_ext,
        "chunk_count": len(chunks),
        "status": "ready",
        "created_at": datetime.now(timezone.utc),
    }
    await db.documents.insert_one(doc_record)

    return doc_record


async def _extract_text(file_bytes: bytes, filename: str, file_ext: str) -> list:
    """Extract and split text from various file formats."""
    import tempfile
    import os

    # Write to temp file (LangChain loaders need file paths)
    with tempfile.NamedTemporaryFile(
        suffix=f".{file_ext}", delete=False
    ) as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name

    try:
        if file_ext == "pdf":
            loader = PyPDFLoader(tmp_path)
        elif file_ext in ("txt", "md"):
            loader = TextLoader(tmp_path, encoding="utf-8")
        elif file_ext in ("docx", "doc"):
            loader = Docx2txtLoader(tmp_path)
        else:
            raise ValueError(f"Unsupported file type: {file_ext}")

        docs = loader.load()
        if file_ext == "pdf" and not _has_meaningful_text(docs):
            loader = UnstructuredPDFLoader(tmp_path, mode="single")
            docs = loader.load()

        chunks = text_splitter.split_documents(docs)
        meaningful_chunks = [
            chunk for chunk in chunks
            if _has_meaningful_text([chunk])
        ]
        return meaningful_chunks
    finally:
        os.unlink(tmp_path)


def _has_meaningful_text(docs: list) -> bool:
    text = "\n".join(
        (doc.page_content if hasattr(doc, "page_content") else str(doc)).strip()
        for doc in docs
    )
    alpha_numeric_count = sum(char.isalnum() for char in text)
    return alpha_numeric_count >= 20


async def delete_document(document_id: str, user_id: str) -> bool:
    """Delete document and all its chunks from ChromaDB and MongoDB."""
    db = get_database()

    # Verify ownership
    doc = await db.documents.find_one({"_id": document_id, "user_id": user_id})
    if not doc:
        return False

    # Delete from ChromaDB
    collection = get_user_collection(user_id)
    try:
        results = collection.get(where={"document_id": document_id})
        if results["ids"]:
            collection.delete(ids=results["ids"])
    except Exception:
        pass

    # Delete from MongoDB
    await db.documents.delete_one({"_id": document_id})
    return True


async def list_documents(user_id: str) -> list[dict]:
    """List all documents for a user."""
    db = get_database()
    cursor = db.documents.find({"user_id": user_id}).sort("created_at", -1)
    docs = []
    async for doc in cursor:
        doc["id"] = str(doc["_id"])
        docs.append(doc)
    return docs
