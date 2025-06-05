import psycopg2
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def setup_database():
    # Database connection parameters
    conn_params = {
        'dbname': os.getenv('DB_NAME'),
        'user': os.getenv('DB_USER'),
        'password': os.getenv('DB_PASSWORD'),
        'host': os.getenv('DB_HOST'),
        'port': os.getenv('DB_PORT')
    }
    
    try:
        # Connect to PostgreSQL
        conn = psycopg2.connect(**conn_params)
        cur = conn.cursor()
        
        print("Connected to PostgreSQL successfully!")
        
        # Create documents table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id           SERIAL PRIMARY KEY,
                source_name  TEXT NOT NULL,
                raw_text     TEXT NOT NULL,
                uploaded_at  TIMESTAMP DEFAULT NOW()
            );
        """)
        
        # Create doc_chunks table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS doc_chunks (
                chunk_id     SERIAL PRIMARY KEY,
                doc_id       INT REFERENCES documents(id),
                chunk_index  INT NOT NULL,
                chunk_text   TEXT NOT NULL,
                embedding    VECTOR(768)
            );
        """)
        
        # Create index for fast nearest-neighbor search
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_chunks_embedding
            ON doc_chunks USING ivfflat (embedding vector_l2_ops) WITH (lists = 100);
        """)
        
        conn.commit()
        print("Database schema created successfully!")
        
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"Error setting up database: {e}")

if __name__ == "__main__":
    setup_database()