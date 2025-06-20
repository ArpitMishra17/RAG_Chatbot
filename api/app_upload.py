from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import tempfile
import os
import shutil
from pathlib import Path
import subprocess
import sys
from typing import Optional
import asyncio
import threading
import time

app = FastAPI(title="RAG Upload API", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Store processing status
processing_status = {}

class UploadResponse(BaseModel):
    success: bool
    message: str
    task_id: Optional[str] = None

class StatusResponse(BaseModel):
    task_id: str
    status: str  # "processing", "completed", "failed"
    message: str
    progress: Optional[str] = None

def run_script(script_path: str, task_id: str):
    """Run a Python script and update status"""
    try:
        processing_status[task_id] = {
            "status": "processing",
            "message": f"Running {script_path}...",
            "progress": "Starting..."
        }
        
        # Get the absolute path to the script
        project_root = Path(__file__).parent.parent
        full_script_path = project_root / "scripts" / script_path
        
        if not full_script_path.exists():
            raise FileNotFoundError(f"Script not found: {full_script_path}")
        
        # Run the script
        result = subprocess.run(
            [sys.executable, str(full_script_path)],
            capture_output=True,
            text=True,
            cwd=str(project_root)
        )
        
        if result.returncode == 0:
            processing_status[task_id] = {
                "status": "completed",
                "message": f"Successfully completed {script_path}",
                "progress": "100%"
            }
        else:
            processing_status[task_id] = {
                "status": "failed",
                "message": f"Script failed: {result.stderr}",
                "progress": "Failed"
            }
            
    except Exception as e:
        processing_status[task_id] = {
            "status": "failed",
            "message": f"Error running {script_path}: {str(e)}",
            "progress": "Failed"
        }

def process_pdf_pipeline(temp_pdf_path: str, task_id: str):
    """Process PDF through ingestion and embedding pipeline"""
    try:
        processing_status[task_id] = {
            "status": "processing",
            "message": "Starting PDF processing pipeline...",
            "progress": "0%"
        }
        
        # Create data/pdfs directory if it doesn't exist
        project_root = Path(__file__).parent.parent
        pdf_dir = project_root / "data" / "pdfs"
        pdf_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy temp file to data/pdfs directory
        filename = Path(temp_pdf_path).name
        destination = pdf_dir / filename
        shutil.copy2(temp_pdf_path, destination)
        
        processing_status[task_id]["progress"] = "10% - PDF copied to processing directory"
        
        # Step 1: Run ingest_pdfs.py
        processing_status[task_id]["message"] = "Extracting and chunking PDF content..."
        processing_status[task_id]["progress"] = "20% - Starting text extraction"
        
        project_root = Path(__file__).parent.parent
        ingest_script = project_root / "scripts" / "ingest_pdfs.py"
        
        result = subprocess.run(
            [sys.executable, str(ingest_script)],
            capture_output=True,
            text=True,
            cwd=str(project_root)
        )
        
        if result.returncode != 0:
            raise Exception(f"PDF ingestion failed: {result.stderr}")
        
        processing_status[task_id]["progress"] = "60% - Text extraction completed"
        
        # Step 2: Run embed_chunks.py
        processing_status[task_id]["message"] = "Computing embeddings for chunks..."
        processing_status[task_id]["progress"] = "70% - Starting embedding computation"
        
        embed_script = project_root / "scripts" / "embed_chunks.py"
        
        result = subprocess.run(
            [sys.executable, str(embed_script)],
            capture_output=True,
            text=True,
            cwd=str(project_root)
        )
        
        if result.returncode != 0:
            raise Exception(f"Embedding computation failed: {result.stderr}")
        
        # Clean up - remove the PDF file from data/pdfs
        try:
            os.remove(destination)
            os.remove(temp_pdf_path)
        except:
            pass  # Ignore cleanup errors
        
        processing_status[task_id] = {
            "status": "completed",
            "message": "PDF processing completed successfully! You can now query the document.",
            "progress": "100%"
        }
        
    except Exception as e:
        processing_status[task_id] = {
            "status": "failed",
            "message": f"Pipeline failed: {str(e)}",
            "progress": "Failed"
        }
        
        # Clean up on failure
        try:
            if 'destination' in locals():
                os.remove(destination)
            os.remove(temp_pdf_path)
        except:
            pass

@app.get("/")
async def root():
    return {"message": "RAG Upload API is running"}

@app.post("/upload", response_model=UploadResponse)
async def upload_pdf(file: UploadFile = File(...)):
    # Validate file type
    if not file.filename or not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    
    # Validate file size (limit to 50MB)
    max_size = 50 * 1024 * 1024  # 50MB
    file_size = 0
    
    try:
        # Create a temporary file with original filename
        temp_dir = tempfile.gettempdir()
        # Clean filename to avoid path issues
        safe_filename = "".join(c for c in file.filename if c.isalnum() or c in (' ', '-', '_', '.')).rstrip()
        temp_file_path = os.path.join(temp_dir, f"upload_{int(time.time())}_{safe_filename}")
        
        with open(temp_file_path, 'wb') as temp_file:
            # Read and write file in chunks to check size
            while True:
                chunk = await file.read(8192)  # 8KB chunks
                if not chunk:
                    break
                file_size += len(chunk)
                if file_size > max_size:
                    os.unlink(temp_file_path)
                    raise HTTPException(status_code=413, detail="File too large. Maximum size is 50MB")
                temp_file.write(chunk)
        
        # Generate task ID
        task_id = f"task_{int(time.time())}_{file.filename}"
        
        # Start processing in background thread
        thread = threading.Thread(
            target=process_pdf_pipeline,
            args=(temp_file_path, task_id)
        )
        thread.daemon = True
        thread.start()
        
        return UploadResponse(
            success=True,
            message=f"PDF upload successful. Processing started for {file.filename}",
            task_id=task_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@app.get("/status/{task_id}", response_model=StatusResponse)
async def get_status(task_id: str):
    if task_id not in processing_status:
        raise HTTPException(status_code=404, detail="Task not found")
    
    status_info = processing_status[task_id]
    return StatusResponse(
        task_id=task_id,
        status=status_info["status"],
        message=status_info["message"],
        progress=status_info.get("progress")
    )

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "RAG Upload API"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8004)