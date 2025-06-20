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
timeout /t 3

:: Start frontend service
echo Starting frontend service on port 8003...
start /b python frontend\app.py
timeout /t 3

:: Start upload service
echo Starting upload service on port 8004...
start /b python api\app_upload.py
timeout /t 3

:: Start admin panel
echo Starting admin panel on port 8005...
start /b python admin\app.py

echo All services started!
echo.
echo Retrieval API: http://localhost:8000
echo Answer API: http://localhost:8001
echo Combined API: http://localhost:8002
echo Frontend (Chat): http://localhost:8003
echo Upload API: http://localhost:8004
echo Admin Panel: http://localhost:8005
echo.
echo Access the RAG Chat at: http://localhost:8003
echo Access the Admin Panel at: http://localhost:8005
echo.
echo To stop services, use Task Manager or close the Command Prompt windows.