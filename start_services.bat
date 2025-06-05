@echo off
echo Starting RAG services...

:: Activate virtual environment
call C:\Users\mishr\Desktop\projects\rag_proto\venv\Scripts\activate

:: Change to project directory
cd /d C:\Users\mishr\Desktop\projects\rag_proto

:: Start retrieval service
echo Starting retrieval service on port 8000...
start /b python api\app_retrieve.py
timeout /t 3

:: Start answer service
echo Starting answer service on port 8001...
start /b python api\app_answer.py
timeout /t 3

:: Start combined service
echo Starting combined service on port 8002...
start /b python api\app_combined.py

echo Services started!
echo Retrieval API: http://localhost:8000
echo Answer API: http://localhost:8001
echo Combined API: http://localhost:8002
echo.
echo To stop services, use Task Manager or close the Command Prompt windows.