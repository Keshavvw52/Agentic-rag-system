from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from app.config.settings import settings
from app.db.mongodb import connect_to_mongo, close_mongo_connection
from app.db.chromadb import init_chromadb
from app.routers import auth, documents, query, evaluation, config_routes, stats


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application startup and shutdown lifecycle."""
    # Startup
    print("Startup: beginning application initialization")
    print("Startup: connecting to MongoDB")
    await connect_to_mongo()
    print("Startup: MongoDB ready")
    print("Startup: initializing ChromaDB")
    await init_chromadb()
    print("Startup: ChromaDB ready")
    print("Agentic RAG System started successfully")
    yield
    # Shutdown
    await close_mongo_connection()
    print("Agentic RAG System shut down")


app = FastAPI(
    title="Agentic RAG System",
    description="Self-correcting, adaptive RAG with hallucination detection & intelligent query routing",
    version="1.0.0",
    lifespan=lifespan,
)


# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(documents.router, prefix="/api/documents", tags=["Documents"])
app.include_router(query.router, prefix="/api/query", tags=["Query"])
app.include_router(evaluation.router, prefix="/api/evaluate", tags=["Evaluation"])
app.include_router(config_routes.router, prefix="/api/config", tags=["Configuration"])
app.include_router(stats.router, prefix="/api", tags=["Stats"])

@app.get("/")
async def root():
    return {
        "message": "Agentic RAG Backend Running"
    }
@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "service": "Agentic RAG System", "version": "1.0.0"}
