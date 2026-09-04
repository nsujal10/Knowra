from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
import os
import structlog

logger = structlog.get_logger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres_password@localhost:5432/enterprise_ai")

try:
    engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_size=5, max_overflow=10)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base = declarative_base()
except Exception as e:
    logger.error("Database initialization failed", error=str(e))
    raise

def init_vector_extension():
    try:
        with engine.begin() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS smoke_test_vectors (
                    id SERIAL PRIMARY KEY,
                    text TEXT,
                    embedding vector(384)
                );
            """))
            logger.info("Vector extension and test table initialized successfully")
    except Exception as e:
        logger.error("Failed to initialize pgvector", error=str(e))
        raise
