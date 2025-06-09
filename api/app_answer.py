from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import requests
import os
import time
from dotenv import load_dotenv
from typing import List

# Load environment variables
load_dotenv()

app = FastAPI(title="RAG Answer API", version="1.0.0")

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY not found in environment variables")

class Chunk(BaseModel):
    chunk_id: int
    chunk_text: str
    source_name: str = None

class AnswerRequest(BaseModel):
    question: str
    chunks: List[Chunk]

class AnswerResponse(BaseModel):
    answer: str
    sources: List[str]
    runtime_ms: int

@app.get("/")
async def root():
    return {"message": "RAG Answer API is running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "groq_api_configured": bool(GROQ_API_KEY)}

@app.post("/answer", response_model=AnswerResponse)
async def answer(req: AnswerRequest):
    question = req.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Empty question.")
    
    if not req.chunks:
        raise HTTPException(status_code=400, detail="No chunks provided.")
    
    # More precise table chunk detection
    table_chunks = []
    text_chunks = []
    
    for chunk in req.chunks:
        chunk_text = chunk.chunk_text
        # Check for actual table content, not just any | character
        if ("TABLE DATA:" in chunk_text or 
            ("|" in chunk_text and 
             ("---|" in chunk_text or chunk_text.count("|") > 8))):  # Multiple | chars suggest table
            table_chunks.append(chunk)
        else:
            text_chunks.append(chunk)
    
    # Build context-aware prompt
    if table_chunks and len(table_chunks) >= len(text_chunks):
        # Table-focused response
        prompt = (
            "You are an expert data analyst. Analyze the provided tabular data carefully. "
            "When answering:\n"
            "1. Reference specific rows and columns\n"
            "2. Pay attention to column headers\n"
            "3. Be precise with numbers and values\n"
            "4. If data spans multiple table parts, consider all parts\n\n"
        )
        
        # Add table data first
        for i, chunk in enumerate(table_chunks):
            chunk_text = chunk.chunk_text[:2000] + "..." if len(chunk.chunk_text) > 2000 else chunk.chunk_text
            prompt += f"Table Data {i+1} (from {chunk.source_name}):\n{chunk_text}\n\n"
        
        # Add supporting text context
        if text_chunks:
            prompt += "Additional Context:\n"
            for chunk in text_chunks[:3]:  # Limit text chunks when tables are primary
                chunk_text = chunk.chunk_text[:500] + "..." if len(chunk.chunk_text) > 500 else chunk.chunk_text
                prompt += f"{chunk_text}\n\n"
    else:
        # Text-focused response
        prompt = (
            "You are a helpful assistant. Use the provided context to answer the question accurately. "
            "If there are tables, reference them appropriately, but focus on the textual information.\n\n"
        )
        
        # Add text context first
        for chunk in text_chunks:
            chunk_text = chunk.chunk_text[:1000] + "..." if len(chunk.chunk_text) > 1000 else chunk.chunk_text
            prompt += f"Context from {chunk.source_name}:\n{chunk_text}\n\n"
        
        # Add table context if available
        if table_chunks:
            prompt += "Tabular Data:\n"
            for i, chunk in enumerate(table_chunks):
                chunk_text = chunk.chunk_text[:1000] + "..." if len(chunk.chunk_text) > 1000 else chunk.chunk_text
                prompt += f"Table {i+1}:\n{chunk_text}\n\n"
    
    prompt += f"Question: {question}\n\nAnswer:"
    
    # Adjust parameters based on content type
    max_tokens = 800 if table_chunks else 500
    temperature = 0.2 if table_chunks else 0.4
    
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    
    data = {
        "model": "llama-3.1-8b-instant",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": temperature,
        "top_p": 0.9
    }
    
    try:
        t0 = time.time()
        resp = requests.post(GROQ_API_URL, json=data, headers=headers, timeout=60)
        t1 = time.time()
        
        if resp.status_code != 200:
            error_detail = resp.json() if resp.headers.get('content-type') == 'application/json' else resp.text
            raise HTTPException(status_code=502, detail=f"Groq API error: {error_detail}")
        
        response_data = resp.json()
        generated = response_data["choices"][0]["message"]["content"].strip()
        
        # Collect unique source names
        sources = sorted({chunk.source_name for chunk in req.chunks if chunk.source_name})
        
        return AnswerResponse(
            answer=generated,
            sources=sources,
            runtime_ms=int((t1 - t0) * 1000)
        )
        
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Request to Groq failed: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Answer generation failed: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)