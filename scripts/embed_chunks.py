import psycopg2
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv
import os

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

def compute_embeddings():
    """Compute embeddings for all chunks without embeddings"""
    print("Loading embedding model...")
    model = SentenceTransformer("Alibaba-NLP/gte-multilingual-base", trust_remote_code=True)
    print("Model loaded successfully!")
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Get chunks without embeddings
    cur.execute("SELECT chunk_id, chunk_text FROM doc_chunks WHERE embedding IS NULL;")
    rows = cur.fetchall()
    
    if not rows:
        print("No chunks need embedding!")
        cur.close()
        conn.close()
        return
    
    print(f"Computing embeddings for {len(rows)} chunks...")
    
    batch_size = 16  # Process in batches to manage memory
    for i in range(0, len(rows), batch_size):
        batch = rows[i:i + batch_size]
        print(f"Processing batch {i//batch_size + 1}/{(len(rows) + batch_size - 1)//batch_size}")
        
        for chunk_id, text in batch:
            try:
                # Compute embedding
                embedding = model.encode(text, normalize_embeddings=True).tolist()
                # Verify embedding dimension
                if len(embedding) != 768:
                    raise ValueError(f"Embedding dimension {len(embedding)} != 768 for chunk {chunk_id}")
                # Update database
                cur.execute(
                    "UPDATE doc_chunks SET embedding = %s WHERE chunk_id = %s;",
                    (embedding, chunk_id)
                )
                
            except Exception as e:
                print(f"Error processing chunk {chunk_id}: {e}")
        
        conn.commit()
    
    print("Training ANN index...")
    try:
        cur.execute("SELECT ivfflat_train('idx_chunks_embedding');")
        conn.commit()
        print("Index training completed!")
    except Exception as e:
        print(f"Index training error (this is normal for small datasets): {e}")
    
    cur.close()
    conn.close()
    print("Embedding computation completed!")

if __name__ == "__main__":
    compute_embeddings()