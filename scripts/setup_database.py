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
        
        # Enable pgvector extension (required for vector operations)
        try:
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            print("pgvector extension enabled!")
        except Exception as e:
            print(f"Warning: Could not enable pgvector extension: {e}")
            print("Make sure pgvector is installed on your PostgreSQL server")
       
        # Create documents table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id           SERIAL PRIMARY KEY,
                source_name  TEXT NOT NULL UNIQUE,
                raw_text     TEXT NOT NULL,
                uploaded_at  TIMESTAMP DEFAULT NOW()
            );
        """)
        print("Documents table created/verified!")
       
        # Create doc_chunks table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS doc_chunks (
                chunk_id     SERIAL PRIMARY KEY,
                doc_id       INT REFERENCES documents(id) ON DELETE CASCADE,
                chunk_index  INT NOT NULL,
                chunk_text   TEXT NOT NULL,
                embedding    VECTOR(768),
                created_at   TIMESTAMP DEFAULT NOW()
            );
        """)
        print("Doc_chunks table created/verified!")
       
        # Create index for fast nearest-neighbor search
        # Note: This index will be built after embeddings are computed
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_chunks_embedding
            ON doc_chunks USING ivfflat (embedding vector_l2_ops) WITH (lists = 100);
        """)
        print("Embedding index created/verified!")
        
        # Create additional helpful indexes
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_chunks_doc_id ON doc_chunks(doc_id);
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_documents_source ON documents(source_name);
        """)
        print("Additional indexes created/verified!")
       
        conn.commit()
        print("Database schema created successfully!")
       
    except Exception as e:
        print(f"Error setting up database: {e}")
        if 'conn' in locals():
            conn.rollback()
        raise
    finally:
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    setup_database()