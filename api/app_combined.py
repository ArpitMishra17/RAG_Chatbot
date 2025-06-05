from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import requests
import asyncio
from typing import List, Optional

app = FastAPI(title="RAG Combined API", version="1.0.0")

# API endpoints
RETRIEVE_URL = "http://localhost:8000/retrieve"
ANSWER_URL = "http://localhost:8001/answer"

class QueryRequest(BaseModel):
    question: str
    num_chunks: int = 10

class Chunk(BaseModel):
    chunk_id: int
    chunk_text: str
    source_name: Optional[str] = None

class QueryResponse(BaseModel):
    question: str
    answer: str
    sources: List[int]
    chunks_used: int
    runtime_ms: int
    low_confidence: bool

@app.get("/")
async def root():
    return {"message": "RAG Combined API is running"}

@app.post("/query", response_model=QueryResponse)
async def query(req: QueryRequest):
    question = req.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty.")
    
    try:
        # Step 1: Retrieve relevant chunks
        retrieve_payload = {
            "question": question,
            "num_chunks": req.num_chunks
        }
        
        retrieve_resp = requests.post(RETRIEVE_URL, json=retrieve_payload, timeout=30)
        if retrieve_resp.status_code != 200:
            raise HTTPException(status_code=502, detail="Retrieval service failed")
        
        retrieve_data = retrieve_resp.json()
        chunks = retrieve_data["chunks"]
        
        if not chunks:
            return QueryResponse(
                question=question,
                answer="I couldn't find any relevant information to answer your question.",
                sources=[],
                chunks_used=0,
                runtime_ms=0,
                low_confidence=True
            )
        
        # Step 2: Generate answer
        answer_payload = {
            "question": question,
            "chunks": chunks
        }
        
        answer_resp = requests.post(ANSWER_URL, json=answer_payload, timeout=60)
        if answer_resp.status_code != 200:
            raise HTTPException(status_code=502, detail="Answer service failed")
        
        answer_data = answer_resp.json()
        
        return QueryResponse(
            question=question,
            answer=answer_data["answer"],
            sources=answer_data["sources"],
            chunks_used=len(chunks),
            runtime_ms=answer_data["runtime_ms"],
            low_confidence=answer_data["low_confidence"]
        )
        
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Service communication failed: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query processing failed: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)