"""Application settings and configuration management."""

from functools import lru_cache
from typing import Any, Dict, List, Optional
import os

from pydantic import BaseSettings, Field, AnyUrl, SecretStr, PostgresDsn, validator


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # Application
    app_name: str = "Amharic Document Preparation System"
    app_version: str = "1.0.0"
    debug: bool = False
    
    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = False
    
    # Security
    secret_key: SecretStr = Field(..., env="SECRET_KEY")
    algorithm: str = Field("HS256", env="JWT_ALGORITHM")
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    
    # Database URLs
    database_url: PostgresDsn | None = Field(default=None, env="DATABASE_URL")
    mongodb_url: AnyUrl | None = Field(default=None, env="MONGODB_URL")
    redis_url: AnyUrl | None = Field(default=None, env="REDIS_URL")
    
    # Storage
    minio_endpoint: str = Field(..., env="MINIO_ENDPOINT")
    minio_access_key: str = Field(..., env="MINIO_ACCESS_KEY")
    minio_secret_key: str = Field(..., env="MINIO_SECRET_KEY")
    minio_secure: bool = True
    
    # Document storage buckets
    raw_documents_bucket: str = "raw-documents"
    processed_documents_bucket: str = "processed-documents"
    temporary_files_bucket: str = "temporary-files"
    backups_bucket: str = "backups"
    templates_bucket: str = "templates"
    
    # Search
    elasticsearch_url: str = Field(..., env="ELASTICSEARCH_URL")
    elasticsearch_index_prefix: str = "amharic_docs"
    
    # Processing
    max_file_size_mb: int = 100
    max_concurrent_jobs: int = 50
    processing_timeout_seconds: int = 300
    ocr_confidence_threshold: float = 0.85
    
    # CrewAI Configuration
    crewai_agents_count: int = 9
    agent_memory_enabled: bool = True
    agent_verbose: bool = False
    
    # OCR Configuration
    tesseract_cmd: str = "/usr/bin/tesseract"
    tesseract_languages: List[str] = ["amh", "eng"]
    ocr_dpi: int = 300
    
    # Language Processing
    spacy_model_path: str = "models/amharic_nlp"
    enable_spell_check: bool = True
    enable_ner: bool = True
    
    # Performance
    worker_processes: int = 4
    max_requests: int = Field(1000, env="MAX_REQUESTS")
    max_requests_jitter: int = Field(100, env="MAX_REQUESTS_JITTER")
    
    # Monitoring
    enable_prometheus: bool = True
    prometheus_port: int = 9090
    enable_tracing: bool = True
    jaeger_endpoint: Optional[str] = None
    
    # Logging
    log_level: str = "INFO"
    log_format: str = "json"
    log_file: Optional[str] = None
    
    # Backup and Retention
    backup_enabled: bool = True
    backup_schedule: str = "0 2 * * *"  # Daily at 2 AM
    backup_retention_days: int = 30
    
    # Compliance
    enable_audit_logging: bool = True
    data_retention_days: int = 2555  # 7 years for compliance
    enable_gdpr_features: bool = True
    
    # Development
    docs_url: Optional[str] = "/docs" if debug else None
    openapi_url: Optional[str] = "/openapi.json" if debug else None
    
    @validator("database_url", pre=True)
    def assemble_db_connection(cls, v: Optional[str]) -> Any:
        """Validate and assemble database URL."""
        if isinstance(v, str):
            return v
        return PostgresDsn.build(
            scheme="postgresql+asyncpg",
            user=os.getenv("POSTGRES_USER"),
            password=os.getenv("POSTGRES_PASSWORD"),
            host=os.getenv("POSTGRES_HOST", "localhost"),
            port=os.getenv("POSTGRES_PORT", "5432"),
            path=f"/{os.getenv('POSTGRES_DB', 'amharic_docs')}",
        )
    
    @validator("mongodb_url", pre=True)
    def assemble_mongo_connection(cls, v: Optional[str]) -> str:
        """Validate and assemble MongoDB URL."""
        if v:
            return v
        
        user = os.getenv("MONGO_USER")
        password = os.getenv("MONGO_PASSWORD")
        host = os.getenv("MONGO_HOST", "localhost")
        port = os.getenv("MONGO_PORT", "27017")
        database = os.getenv("MONGO_DB", "amharic_docs")
        
        if user and password:
            return f"mongodb://{user}:{password}@{host}:{port}/{database}"
        return f"mongodb://{host}:{port}/{database}"
    
    @validator("redis_url", pre=True)
    def assemble_redis_connection(cls, v: Optional[str]) -> str:
        """Validate and assemble Redis URL."""
        if v:
            return v
        
        host = os.getenv("REDIS_HOST", "localhost")
        port = os.getenv("REDIS_PORT", "6379")
        password = os.getenv("REDIS_PASSWORD")
        
        if password:
            return f"redis://:{password}@{host}:{port}/0"
        return f"redis://{host}:{port}/0"
    
    @validator("elasticsearch_url", pre=True)
    def assemble_elasticsearch_connection(cls, v: Optional[str]) -> str:
        """Validate and assemble Elasticsearch URL."""
        if v:
            return v
        
        host = os.getenv("ELASTICSEARCH_HOST", "localhost")
        port = os.getenv("ELASTICSEARCH_PORT", "9200")
        scheme = os.getenv("ELASTICSEARCH_SCHEME", "http")
        
        return f"{scheme}://{host}:{port}"
    
    @validator("minio_endpoint", pre=True)
    def assemble_minio_endpoint(cls, v: Optional[str]) -> str:
        """Validate and assemble MinIO endpoint."""
        if v:
            return v
        
        host = os.getenv("MINIO_HOST", "localhost")
        port = os.getenv("MINIO_PORT", "9000")
        
        return f"{host}:{port}"
    
    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings()


# Database configuration
DATABASE_CONFIG = {
    "echo": get_settings().debug,
    "pool_pre_ping": True,
    "pool_recycle": 300,
}

# MongoDB configuration
MONGODB_CONFIG = {
    "maxPoolSize": 10,
    "minPoolSize": 1,
    "maxIdleTimeMS": 30000,
    "waitQueueTimeoutMS": 5000,
}

# Redis configuration
REDIS_CONFIG = {
    "encoding": "utf-8",
    "decode_responses": True,
    "socket_keepalive": True,
    "socket_keepalive_options": {},
    "health_check_interval": 30,
}

# Elasticsearch configuration
ELASTICSEARCH_CONFIG = {
    "max_retries": 3,
    "retry_on_timeout": True,
    "timeout": 30,
}

# MinIO configuration
MINIO_CONFIG = {
    "region": "us-east-1",
}

# Agent configuration
AGENT_CONFIG = {
    "orchestrator": {
        "role": "Processing Orchestrator",
        "goal": "Coordinate document processing workflow",
        "backstory": "Expert in managing complex document processing pipelines",
        "verbose": get_settings().agent_verbose,
        "allow_delegation": True,
    },
    "document_analyzer": {
        "role": "Document Type Analyzer",
        "goal": "Identify and classify document types",
        "backstory": "Specialist in document format detection and routing",
        "verbose": get_settings().agent_verbose,
        "allow_delegation": False,
    },
    "pdf_extractor": {
        "role": "PDF Content Extractor",
        "goal": "Extract text and structure from PDF documents",
        "backstory": "Expert in PDF parsing and content extraction",
        "verbose": get_settings().agent_verbose,
        "allow_delegation": False,
    },
    "image_ocr": {
        "role": "OCR Specialist",
        "goal": "Extract text from images using OCR",
        "backstory": "Advanced OCR engineer specializing in Amharic text recognition",
        "verbose": get_settings().agent_verbose,
        "allow_delegation": False,
    },
    "word_extractor": {
        "role": "Word Document Processor",
        "goal": "Extract content from Microsoft Word documents",
        "backstory": "Expert in Word document parsing and formatting preservation",
        "verbose": get_settings().agent_verbose,
        "allow_delegation": False,
    },
    "csv_processor": {
        "role": "CSV Data Processor",
        "goal": "Process and analyze CSV data files",
        "backstory": "Data processing specialist for structured document formats",
        "verbose": get_settings().agent_verbose,
        "allow_delegation": False,
    },
    "web_scraper": {
        "role": "Web Content Extractor",
        "goal": "Extract content from web pages",
        "backstory": "Web scraping expert with respect for robots.txt and rate limits",
        "verbose": get_settings().agent_verbose,
        "allow_delegation": False,
    },
    "amharic_nlp": {
        "role": "Amharic Language Processor",
        "goal": "Process and analyze Amharic text",
        "backstory": "Ethiopian language specialist with deep NLP expertise",
        "verbose": get_settings().agent_verbose,
        "allow_delegation": False,
    },
    "quality_assurance": {
        "role": "Quality Assurance Specialist",
        "goal": "Validate processing quality and accuracy",
        "backstory": "Quality control expert ensuring high processing standards",
        "verbose": get_settings().agent_verbose,
        "allow_delegation": False,
    },
}
