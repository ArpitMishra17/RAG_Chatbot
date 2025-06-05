from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer
import psycopg2
import os
from dotenv import load_dotenv
from typing import List

# Load environment variables
load_dotenv()

app = FastAPI(title="RAG Retrieval API", version="1.0.0")

# Load embedding model once at startup
print("Loading embedding model...")
embed_model = SentenceTransformer("Alibaba-NLP/gte-multilingual-base", trust_remote_code=True)
print("Embedding model loaded!")

class RetrieveRequest(BaseModel):
    question: str
    num_chunks: int = 10

class Chunk(BaseModel):
    chunk_id: int
    chunk_text: str
    source_name: str

class RetrieveResponse(BaseModel):
    chunks: List[Chunk]
    total_found: int

def get_db_connection():
    """Create and return database connection"""
    conn_params = {
        'dbname': os.getenv('DB_NAME'),
        'user': os.getenv('DB_USER'),
        'password': os.getenv('DB_PASSWORD'),
        'host': os.getenv('DB_HOST'),
        'port': os.getenv('DB_PORT')
    }
    return psycopg2.connect(**conn_params)

@app.get("/")
async def root():
    return {"message": "RAG Retrieval API is running"}

@app.get("/health")
async def health_check():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM doc_chunks WHERE embedding IS NOT NULL;")
        embedded_chunks = cur.fetchone()[0]
        cur.close()
        conn.close()
        
        return {
            "status": "healthy",
            "embedded_chunks": embedded_chunks
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database connection failed: {e}")

@app.post("/retrieve", response_model=RetrieveResponse)
async def retrieve(req: RetrieveRequest):
    question = req.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty.")
    
    if req.num_chunks <= 0 or req.num_chunks > 50:
        raise HTTPException(status_code=400, detail="num_chunks must be between 1 and 50.")
    
    try:
        # Embed the question
        q_vec = embed_model.encode(question).tolist()
        
        # Query database
        conn = get_db_connection()
        cur = conn.cursor()
        
        sql = """
        SELECT dc.chunk_id, dc.chunk_text, d.source_name
        FROM doc_chunks dc
        JOIN documents d ON dc.doc_id = d.id
        WHERE dc.embedding IS NOT NULL
        ORDER BY dc.embedding <-> %s::vector
        LIMIT %s;
        """
        
        cur.execute(sql, (q_vec, req.num_chunks))
        rows = cur.fetchall()
        
        chunks = [
            Chunk(
                chunk_id=row[0],
                chunk_text=row[1],
                source_name=row[2]
            ) for row in rows
        ]
        
        cur.close()
        conn.close()
        
        return RetrieveResponse(
            chunks=chunks,
            total_found=len(chunks)
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Retrieval failed: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)