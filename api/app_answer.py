from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import requests
import os
import re
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
    sources: List[int]
    runtime_ms: int
    low_confidence: bool

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
    
    # Build the chain-of-thought prompt
    prompt = (
        "You are an intelligent assistant. Follow these steps to answer the user's question:\n"
        "1. Analyze each passage below\n"
        "2. Identify which passage(s) contain relevant information\n"
        "3. Provide a clear, concise answer based only on the given passages\n"
        "4. Reference passage numbers in your answer using [1], [2], etc.\n\n"
        "Passages:\n"
    )
    
    for idx, chunk in enumerate(req.chunks, start=1):
        # Truncate very long chunks to manage token limits
        chunk_text = chunk.chunk_text[:1000] + "..." if len(chunk.chunk_text) > 1000 else chunk.chunk_text
        prompt += f"[{idx}] {chunk_text}\n\n"
    
    prompt += f"Question: {question}\n\nAnswer:"
    
    # Prepare Groq API request
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    
    data = {
        "model": "llama3-8b-8192",  # Using Llama 3 8B model
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ],
        "max_tokens": 512,
        "temperature": 0.1,
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
        
        # Check for low confidence on numeric/date questions
        low_conf = False
        numeric_triggers = ["how many", "total", "%", "number", "sum", "count", "date", "year", "when"]
        if any(trigger in question.lower() for trigger in numeric_triggers):
            nums = re.findall(r"\b\d+(?:,\d{3})*(?:\.\d+)?\b", generated)
            if not nums:
                low_conf = True
        
        # Extract cited passage numbers
        sources = sorted({int(n) for n in re.findall(r"\[(\d+)\]", generated)}) if generated else []
        
        return AnswerResponse(
            answer=generated,
            sources=sources,
            runtime_ms=int((t1 - t0) * 1000),
            low_confidence=low_conf
        )
        
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Request to Groq failed: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Answer generation failed: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)