import psycopg2
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv
import os
import gc
import torch

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
    
    # Use device detection for better performance
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    print(f"Using device: {device}")
    
    model = SentenceTransformer("Alibaba-NLP/gte-multilingual-base", trust_remote_code=True)
    model = model.to(device)
    print("Model loaded successfully!")
   
    conn = None
    cur = None
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
       
        # Get chunks without embeddings
        cur.execute("SELECT chunk_id, chunk_text FROM doc_chunks WHERE embedding IS NULL ORDER BY chunk_id;")
        rows = cur.fetchall()
       
        if not rows:
            print("No chunks need embedding!")
            return
       
        print(f"Computing embeddings for {len(rows)} chunks...")
       
        batch_size = 8 if device == 'cuda' else 16  # Smaller batch for GPU to avoid memory issues
        processed = 0
        
        for i in range(0, len(rows), batch_size):
            batch = rows[i:i + batch_size]
            batch_num = i//batch_size + 1
            total_batches = (len(rows) + batch_size - 1)//batch_size
            
            print(f"Processing batch {batch_num}/{total_batches} ({len(batch)} chunks)")
           
            # Extract texts for batch processing
            chunk_ids = [row[0] for row in batch]
            texts = [row[1] for row in batch]
            
            try:
                # Compute embeddings for the entire batch
                embeddings = model.encode(texts, normalize_embeddings=True, batch_size=len(texts))
                
                # Verify embedding dimensions and update database
                for chunk_id, embedding in zip(chunk_ids, embeddings):
                    embedding_list = embedding.tolist()
                    
                    # Verify embedding dimension
                    if len(embedding_list) != 768:
                        raise ValueError(f"Embedding dimension {len(embedding_list)} != 768 for chunk {chunk_id}")
                    
                    # Update database
                    cur.execute(
                        "UPDATE doc_chunks SET embedding = %s WHERE chunk_id = %s;",
                        (embedding_list, chunk_id)
                    )
                
                conn.commit()
                processed += len(batch)
                print(f"  - Processed {processed}/{len(rows)} chunks")
                
                # Clear memory periodically
                if batch_num % 10 == 0:
                    gc.collect()
                    if device == 'cuda':
                        torch.cuda.empty_cache()
               
            except Exception as e:
                print(f"Error processing batch {batch_num}: {e}")
                conn.rollback()
                # Continue with next batch instead of failing completely
                continue
       
        print(f"\nSuccessfully processed {processed}/{len(rows)} chunks")
        
        # Check if we have enough data points for index training
        cur.execute("SELECT COUNT(*) FROM doc_chunks WHERE embedding IS NOT NULL;")
        embedding_count = cur.fetchone()[0]
        
        if embedding_count >= 100:  # Minimum recommended for IVFFlat
            print("Training ANN index...")
            try:
                # First, check if the index exists and has data
                cur.execute("""
                    SELECT COUNT(*) FROM pg_stat_user_indexes 
                    WHERE indexrelname = 'idx_chunks_embedding';
                """)
                
                if cur.fetchone()[0] > 0:
                    # Try to train the index
                    cur.execute("SELECT ivfflat_train('idx_chunks_embedding');")
                    conn.commit()
                    print("Index training completed!")
                else:
                    print("Index not found, it will be auto-trained on first use.")
                    
            except Exception as e:
                print(f"Index training warning (this is normal for small datasets): {e}")
                # Index training failure is not critical
                pass
        else:
            print(f"Only {embedding_count} embeddings computed. Index training requires at least 100 vectors.")
   
    except Exception as e:
        print(f"Critical error in compute_embeddings: {e}")
        if conn:
            conn.rollback()
        raise
        
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()
        
        # Clean up GPU memory
        if device == 'cuda':
            torch.cuda.empty_cache()
            
    print("Embedding computation completed!")

if __name__ == "__main__":
    compute_embeddings()