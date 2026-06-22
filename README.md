# Agentic RAG System

A full-stack Agentic RAG application that lets users upload documents, ask questions, and inspect how the system reasoned before producing an answer.

The project combines:

- `backend/`: FastAPI + LangGraph + ChromaDB + MongoDB
- `frontend/`: React + TypeScript + Vite + Tailwind CSS

## Features

- User authentication with JWT
- Document upload and ingestion for `PDF`, `TXT`, `DOC`, `DOCX`, and `MD`
- Agentic query pipeline with classification, routing, retrieval, evaluation, generation, verification, and scoring
- Corrective RAG flow with retries and refinement
- Hallucination detection with claim extraction and verification
- Confidence scoring for answer quality
- Query traces, iteration history, and claims inspection
- Configurable routing and threshold settings per user
- Dashboard stats and evaluation results

## Architecture

### Backend

The FastAPI backend exposes APIs for:

- Auth: signup, login, current user
- Documents: upload, list, delete
- Querying: agentic query, simple baseline query, trace, claims, iterations, history
- Evaluation: hallucination scoring and recent result summaries
- Configuration: routing rules and threshold updates
- Stats: user-level usage and quality metrics

Core backend pieces:

- `app/graph/agentic_pipeline.py`: main agentic orchestration
- `app/services/retrieval.py`: retrieval and strategy logic
- `app/services/corrective_rag.py`: corrective retrieval flow
- `app/services/hallucination_detector.py`: claim verification and hallucination checks
- `app/services/confidence_scorer.py`: confidence scoring
- `app/db/mongodb.py`: MongoDB integration
- `app/db/chromadb.py`: Chroma vector storage

### Frontend

The React frontend includes:

- Landing page
- Signup and login
- Query experience
- Trace and claims inspection
- Evaluation and comparison views
- Configuration screen for routing and thresholds
- Stats/dashboard views

Vite proxies `/api` requests to `http://localhost:8000` during development.

## Tech Stack

### Backend

- FastAPI
- LangChain / LangGraph
- ChromaDB
- MongoDB
- Groq API
- Sentence Transformers

### Frontend

- React 18
- TypeScript
- Vite
- Tailwind CSS
- Axios
- Zustand
- Framer Motion

## Project Structure

```text
agentic-rag-system/
|-- backend/
|   |-- app/
|   |-- data/
|   |-- requirements.txt
|-- frontend/
|   |-- src/
|   |-- public/
|   |-- package.json
|-- README.md
|-- .gitignore
```

## Prerequisites

Install these before running locally:

- Python 3.11+ recommended
- Node.js 18+ recommended
- MongoDB running locally or reachable remotely
- A Groq API key

## Backend Setup

From the `backend` folder:

```powershell
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

Create `backend/.env` with values like:

```env
APP_NAME=Agentic RAG System
DEBUG=True

MONGODB_URL=mongodb://localhost:27017
MONGODB_DB_NAME=agentic_rag

JWT_SECRET=replace-with-a-long-random-secret
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=1440

GROQ_API_KEY=your_groq_api_key
GROQ_MODEL=llama-3.3-70b-versatile
GROQ_FAST_MODEL=llama-3.1-8b-instant

CHROMA_PERSIST_DIR=./data/chroma
CHROMA_COLLECTION_PREFIX=user_

EMBEDDING_MODEL=all-MiniLM-L6-v2
RERANKER_MODEL=cross-encoder/ms-marco-MiniLM-L-6-v2

TAVILY_API_KEY=
USE_TAVILY=False

FRONTEND_URL=http://localhost:5173
```

Run the backend:

```powershell
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Backend health check:

- `GET http://localhost:8000/`
- `GET http://localhost:8000/api/health`

## Frontend Setup

From the `frontend` folder:

```powershell
npm install
npm run dev
```

Frontend dev server:

- `http://localhost:5173`

## Docker Setup

This repository now includes Docker support for the full stack:

- `backend/Dockerfile`: multi-stage Python image for the FastAPI API
- `frontend/Dockerfile`: multi-stage Node to Nginx build for the React UI
- `frontend/nginx.conf`: serves the SPA and proxies `/api` to the backend container
- `docker-compose.yml`: starts MongoDB, the backend, and the frontend together

### 1. Prepare backend environment

Copy the example file and fill in your real secrets:

```powershell
Copy-Item backend/.env.example backend/.env
```

Important values:

- `GROQ_API_KEY`: required for LLM calls
- `JWT_SECRET`: change this before using the app seriously

### 2. Build and start containers

From the project root:

```powershell
docker compose up --build
```

### 3. Open the app

- Frontend: `http://localhost:8080`
- Backend API: `http://localhost:8000`
- Backend health check: `http://localhost:8000/api/health`

### 4. Stop containers

```powershell
docker compose down
```

To also remove named volumes:

```powershell
docker compose down -v
```

## Typical Development Flow

1. Start MongoDB.
2. Start the backend on port `8000`.
3. Start the frontend on port `5173`.
4. Create an account or sign in.
5. Upload documents.
6. Run queries and inspect traces, claims, and confidence scores.

## Important Notes Before Pushing

- This folder is currently not initialized as a Git repository yet.
- There is no root `README.md` or root `.gitignore` by default, which is why they were added.
- The workspace currently contains generated/local artifacts such as `backend/venv`, `frontend/node_modules`, `frontend/dist`, `__pycache__`, and local ChromaDB data. The new `.gitignore` will help prevent adding them to Git.
- If any of those files were already staged in another copy of the repo, `.gitignore` will not remove them automatically. You would need to untrack them before pushing.

## Suggested Next Git Commands

```powershell
git init
git add .
git status
git commit -m "Initial commit"
git branch -M main
git remote add origin <your-github-repo-url>
git push -u origin main
```

## License

Add your preferred license here before publishing publicly.
