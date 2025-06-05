import requests
import json
import sys

def test_query(question, num_chunks=10):
    """Test the RAG system with a question"""
    url = "http://localhost:8002/query"
    payload = {
        "question": question,
        "num_chunks": num_chunks
    }
    
    try:
        response = requests.post(url, json=payload, timeout=60)
        if response.status_code == 200:
            result = response.json()
            print(f"\nQuestion: {result['question']}")
            print(f"Answer: {result['answer']}")
            print(f"Sources: {result['sources']}")
            print(f"Chunks used: {result['chunks_used']}")
            print(f"Runtime: {result['runtime_ms']}ms")
            print(f"Low confidence: {result['low_confidence']}")
        else:
            print(f"Error: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_client.py 'Your question here'")
        sys.exit(1)
    
    question = sys.argv[1]
    test_query(question)