import os
import psycopg2
from pdfminer.high_level import extract_text
from dotenv import load_dotenv
import sys

# Load environment variables
load_dotenv()

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

def chunk_text(text, chunk_size=500, overlap=100):
    """Split text into overlapping chunks"""
    words = text.split()
    chunks = []
    start = 0
    
    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunk = " ".join(words[start:end])
        chunks.append(chunk)
        
        if end >= len(words):
            break
            
        start += (chunk_size - overlap)
    
    return chunks

def ingest_pdfs():
    """Extract and ingest PDFs into database"""
    # Determine the absolute path to the project's root directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir) # Assumes script is in a 'scripts' subdirectory
    pdf_dir = os.path.join(project_root, "data", "pdfs")
    
    if not os.path.exists(pdf_dir):
        print(f"PDF directory {pdf_dir} does not exist!")
        return
    
    pdf_files = [f for f in os.listdir(pdf_dir) if f.lower().endswith('.pdf')]
    
    if not pdf_files:
        print(f"No PDF files found in {pdf_dir}")
        return
    
    print(f"Found {len(pdf_files)} PDF files to process")
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    for filename in pdf_files:
        try:
            print(f"Processing {filename}...")
            
            # Check if file already processed
            cur.execute("SELECT id FROM documents WHERE source_name = %s", (filename,))
            if cur.fetchone():
                print(f"  - {filename} already processed, skipping...")
                continue
            
            file_path = os.path.join(pdf_dir, filename)
            
            # Extract text from PDF
            raw_text = extract_text(file_path)
            
            if not raw_text.strip():
                print(f"  - No text extracted from {filename}, skipping...")
                continue
            
            # Insert document
            cur.execute(
                "INSERT INTO documents (source_name, raw_text) VALUES (%s, %s) RETURNING id;",
                (filename, raw_text)
            )
            doc_id = cur.fetchone()[0]
            conn.commit()
            
            # Chunk the text
            chunks = chunk_text(raw_text)
            print(f"  - Created {len(chunks)} chunks")
            
            # Insert chunks
            for idx, chunk in enumerate(chunks):
                cur.execute(
                    """
                    INSERT INTO doc_chunks (doc_id, chunk_index, chunk_text, embedding)
                    VALUES (%s, %s, %s, NULL);
                    """,
                    (doc_id, idx, chunk)
                )
            
            conn.commit()
            print(f"  - Successfully processed {filename}")
            
        except Exception as e:
            print(f"  - Error processing {filename}: {e}")
            conn.rollback()
    
    cur.close()
    conn.close()
    print("PDF ingestion completed!")

if __name__ == "__main__":
    ingest_pdfs()