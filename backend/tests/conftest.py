"""Test configuration and fixtures for the Amharic document system."""

import asyncio
import pytest
import pytest_asyncio
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock

from testcontainers.postgres import PostgresContainer
from testcontainers.mongodb import MongoDbContainer
from testcontainers.redis import RedisContainer
from testcontainers.minio import MinioContainer
from testcontainers.elasticsearch import ElasticSearchContainer

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from motor.motor_asyncio import AsyncIOMotorClient
import redis.asyncio as redis
from minio import Minio
from elasticsearch import AsyncElasticsearch


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an instance of the default event loop for the test session."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def postgres_container() -> AsyncGenerator[PostgresContainer, None]:
    """Start PostgreSQL test container."""
    with PostgresContainer("postgres:15") as postgres:
        yield postgres


@pytest.fixture(scope="session")
async def mongodb_container() -> AsyncGenerator[MongoDbContainer, None]:
    """Start MongoDB test container."""
    with MongoDbContainer("mongo:7") as mongodb:
        yield mongodb


@pytest.fixture(scope="session")
async def redis_container() -> AsyncGenerator[RedisContainer, None]:
    """Start Redis test container."""
    with RedisContainer("redis:7") as redis_container:
        yield redis_container


@pytest.fixture(scope="session")
async def minio_container() -> AsyncGenerator[MinioContainer, None]:
    """Start MinIO test container."""
    with MinioContainer() as minio:
        yield minio


@pytest.fixture(scope="session")
async def elasticsearch_container() -> AsyncGenerator[ElasticSearchContainer, None]:
    """Start Elasticsearch test container."""
    with ElasticSearchContainer("elasticsearch:8.10.0") as elasticsearch:
        # Disable security for testing
        elasticsearch.with_env("xpack.security.enabled", "false")
        elasticsearch.with_env("discovery.type", "single-node")
        yield elasticsearch


@pytest.fixture
async def db_session(postgres_container: PostgresContainer) -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session."""
    # Get connection details
    db_url = postgres_container.get_connection_url().replace("postgresql://", "postgresql+asyncpg://")
    
    # Create async engine
    engine = create_async_engine(db_url, echo=True)
    
    # Create tables (would normally use Alembic migrations)
    # async with engine.begin() as conn:
    #     await conn.run_sync(Base.metadata.create_all)
    
    # Create session
    async with AsyncSession(engine) as session:
        yield session
    
    await engine.dispose()


@pytest.fixture
async def mongo_client(mongodb_container: MongoDbContainer) -> AsyncGenerator[AsyncIOMotorClient, None]:
    """Create a test MongoDB client."""
    connection_url = mongodb_container.get_connection_url()
    client = AsyncIOMotorClient(connection_url)
    
    yield client
    
    client.close()


@pytest.fixture
async def redis_client(redis_container: RedisContainer) -> AsyncGenerator[redis.Redis, None]:
    """Create a test Redis client."""
    client = redis.Redis(
        host=redis_container.get_container_host_ip(),
        port=redis_container.get_exposed_port(6379),
        decode_responses=True
    )
    
    yield client
    
    await client.aclose()


@pytest.fixture
async def minio_client(minio_container: MinioContainer) -> AsyncGenerator[Minio, None]:
    """Create a test MinIO client."""
    client = Minio(
        f"{minio_container.get_container_host_ip()}:{minio_container.get_exposed_port(9000)}",
        access_key=minio_container.access_key,
        secret_key=minio_container.secret_key,
        secure=False
    )
    
    yield client


@pytest.fixture
async def elasticsearch_client(elasticsearch_container: ElasticSearchContainer) -> AsyncGenerator[AsyncElasticsearch, None]:
    """Create a test Elasticsearch client."""
    client = AsyncElasticsearch(
        [f"http://{elasticsearch_container.get_container_host_ip()}:{elasticsearch_container.get_exposed_port(9200)}"]
    )
    
    yield client
    
    await client.close()


# Factory fixtures for creating test data
@pytest.fixture
def user_factory():
    """Factory for creating test users."""
    def _create_user(
        email: str = "test@example.com",
        username: str = "testuser",
        role: str = "processor",
        **kwargs
    ):
        from src.models.schemas.auth import User
        return User(
            email=email,
            username=username,
            role=role,
            **kwargs
        )
    return _create_user


@pytest.fixture
def document_factory():
    """Factory for creating test documents."""
    def _create_document(
        filename: str = "test.pdf",
        document_type: str = "pdf",
        file_size: int = 1024,
        content_hash: str = "test_hash",
        **kwargs
    ):
        from src.models.schemas.documents import Document
        return Document(
            filename=filename,
            document_type=document_type,
            file_size=file_size,
            content_hash=content_hash,
            **kwargs
        )
    return _create_document


@pytest.fixture
def processing_job_factory():
    """Factory for creating test processing jobs."""
    def _create_job(
        job_name: str = "Test Job",
        total_documents: int = 1,
        **kwargs
    ):
        from src.models.schemas.processing import ProcessingJob
        return ProcessingJob(
            job_name=job_name,
            total_documents=total_documents,
            **kwargs
        )
    return _create_job


# Mock fixtures for external services
@pytest.fixture
def mock_crewai_orchestrator():
    """Mock CrewAI orchestrator for testing."""
    return AsyncMock()


@pytest.fixture
def mock_tesseract_ocr():
    """Mock Tesseract OCR engine for testing."""
    mock = AsyncMock()
    mock.image_to_string.return_value = "Sample Amharic text: ሰላም"
    mock.get_confidence.return_value = 0.95
    return mock


@pytest.fixture
def mock_spacy_nlp():
    """Mock spaCy NLP pipeline for testing."""
    mock = AsyncMock()
    mock.process.return_value = {
        "entities": [
            {"text": "ኢትዮጵያ", "label": "GPE", "start": 0, "end": 7}
        ],
        "language": "amh",
        "confidence": 0.98
    }
    return mock


# Test data fixtures
@pytest.fixture
def sample_pdf_content():
    """Sample PDF content for testing."""
    return b"%PDF-1.4 sample content"


@pytest.fixture
def sample_image_content():
    """Sample image content for testing."""
    # This would be actual image bytes in a real implementation
    return b"fake_image_bytes"


@pytest.fixture
def sample_amharic_text():
    """Sample Amharic text for testing."""
    return "ሰላም ለዓለም! ይህ የአማርኛ ጽሁፍ ናሙና ነው።"


@pytest.fixture
def sample_document_metadata():
    """Sample document metadata for testing."""
    return {
        "original_name": "sample_document.pdf",
        "mime_type": "application/pdf",
        "page_count": 5,
        "language_detected": "amh",
        "author": "Test Author"
    }


# Utility fixtures
@pytest.fixture
def temp_file_cleanup():
    """Fixture to clean up temporary files after tests."""
    created_files = []
    
    def track_file(filepath: str):
        created_files.append(filepath)
        return filepath
    
    yield track_file
    
    # Cleanup
    import os
    for filepath in created_files:
        if os.path.exists(filepath):
            os.remove(filepath)