from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import uvicorn

app = FastAPI(title="RAG Admin Panel", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Get the directory where this script is located
admin_dir = Path(__file__).parent

# Mount static files with correct path
app.mount("/static", StaticFiles(directory=str(admin_dir / "static")), name="static")

# Templates with correct path
templates = Jinja2Templates(directory=str(admin_dir / "templates"))

@app.get("/")
async def admin_root(request: Request):
    return templates.TemplateResponse("admin.html", {"request": request})

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "RAG Admin Panel"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8005)