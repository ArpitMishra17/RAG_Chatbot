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
    
    # Build the generative prompt
    prompt = (
        "You are an intelligent assistant. Use the provided context to generate a clear, concise, and natural answer to the user's question. "
        "Do not directly quote the context or reference passage numbers. Synthesize the information to provide a coherent response.\n\n"
        "Context:\n"
    )
    
    for chunk in req.chunks:
        # Truncate very long chunks to manage token limits
        chunk_text = chunk.chunk_text[:1000] + "..." if len(chunk.chunk_text) > 1000 else chunk.chunk_text
        prompt += f"{chunk_text}\n\n"
    
    prompt += f"Question: {question}\n\nAnswer:"
    
    # Prepare Groq API request
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    
    data = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ],
        "max_tokens": 512,
        "temperature": 0.7,  # Increased for more natural, generative responses
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