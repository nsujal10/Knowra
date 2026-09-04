import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from app.core.database import SessionLocal, init_vector_extension
from sqlalchemy import text

def test_db():
    init_vector_extension()
    db = SessionLocal()
    try:
        # Clear
        db.execute(text("DELETE FROM smoke_test_vectors"))
        db.commit()
        
        # Insert
        embedding = [0.1] * 384
        db.execute(
            text("INSERT INTO smoke_test_vectors (text, embedding) VALUES (:txt, :emb)"),
            {"txt": "Test sentence", "emb": str(embedding)}
        )
        db.commit()
        
        # Query
        res = db.execute(
            text("SELECT text, embedding <=> :query_emb AS distance FROM smoke_test_vectors ORDER BY distance LIMIT 1"),
            {"query_emb": str(embedding)}
        ).fetchone()
        
        print(f"DB Vector Test Passed! Closest text: {res.text}, Distance: {res.distance}")
    finally:
        db.close()

if __name__ == "__main__":
    test_db()
