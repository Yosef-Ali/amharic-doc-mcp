# Amharic Document System - Backend

> FastAPI-based backend with CrewAI multi-agent orchestration and MCP integration

## 📋 Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running the Application](#running-the-application)
- [Project Structure](#project-structure)
- [Development](#development)
- [Testing](#testing)
- [API Documentation](#api-documentation)

## 🌟 Overview

The backend is a production-ready FastAPI application that provides:

- **MCP Server**: Model Context Protocol tools for CopilotKit integration
- **CrewAI Orchestration**: Multi-agent document processing workflows
- **Async Processing**: Non-blocking document processing with Celery
- **RESTful API**: Comprehensive REST endpoints for all operations
- **WebSocket Support**: Real-time progress updates and notifications
- **Multi-Database**: PostgreSQL, MongoDB, Redis, Elasticsearch, MinIO

## 📦 Prerequisites

- Python 3.11 or higher
- pip or uv package manager
- PostgreSQL 16+
- MongoDB 7+
- Redis 7+
- MinIO (or S3-compatible storage)
- Elasticsearch 8+
- Tesseract OCR (for OCR functionality)

### System Dependencies

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install -y \
    python3.11 python3.11-dev python3-pip \
    tesseract-ocr tesseract-ocr-amh \
    libpq-dev \
    build-essential
```

**macOS:**
```bash
brew install python@3.11 tesseract tesseract-lang postgresql
```

**Windows:**
- Install Python 3.11 from [python.org](https://www.python.org)
- Install Tesseract from [GitHub releases](https://github.com/UB-Mannheim/tesseract/wiki)
- Install PostgreSQL from [postgresql.org](https://www.postgresql.org)

## 🚀 Installation

### Option 1: Using UV (Recommended)

```bash
# Install uv if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment and install dependencies
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -e ".[dev]"
```

### Option 2: Using pip

```bash
# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"
```

### Download Language Models

```bash
# Download spaCy models
python -m spacy download en_core_web_sm

# Note: Amharic models may need to be downloaded separately
# Check documentation for Amharic NLP model setup
```

## ⚙️ Configuration

### 1. Create Environment File

```bash
cp .env.example .env
```

### 2. Edit `.env` with Your Settings

```env
# Application
APP_NAME=Amharic Document System
APP_VERSION=1.0.0
DEBUG=true
ENVIRONMENT=development

# Server
HOST=0.0.0.0
PORT=8000
RELOAD=true

# Database - PostgreSQL
DATABASE_URL=postgresql+asyncpg://postgres:postgres_pass@localhost:5432/amharic_doc_system
DB_ECHO=false  # Set to true for SQL query logging

# Database - MongoDB
MONGODB_URL=mongodb://admin:mongo_pass@localhost:27017/amharic_documents?authSource=admin
MONGODB_DATABASE=amharic_documents

# Cache - Redis
REDIS_URL=redis://localhost:6379/0
REDIS_PASSWORD=
REDIS_MAX_CONNECTIONS=10

# Object Storage - MinIO
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minio_pass
MINIO_SECURE=false
MINIO_BUCKET_NAME=amharic-documents

# Search - Elasticsearch
ELASTICSEARCH_URL=http://localhost:9200
ELASTICSEARCH_INDEX=amharic_documents
ELASTICSEARCH_USER=
ELASTICSEARCH_PASSWORD=

# Security
JWT_SECRET_KEY=your-super-secret-jwt-key-change-this-in-production
JWT_ALGORITHM=HS256
JWT_EXPIRATION_MINUTES=60
REFRESH_TOKEN_EXPIRATION_DAYS=7

# CORS
CORS_ORIGINS=["http://localhost:3000","http://localhost:5173"]
CORS_ALLOW_CREDENTIALS=true

# File Upload
MAX_UPLOAD_SIZE=104857600  # 100MB in bytes
ALLOWED_EXTENSIONS=pdf,png,jpg,jpeg,docx,doc,csv,txt,html

# OCR Configuration
TESSERACT_PATH=/usr/bin/tesseract  # Adjust for your system
TESSERACT_LANG=amh+eng
OCR_DPI=300
OCR_CONFIDENCE_THRESHOLD=0.6

# CrewAI Configuration
OPENAI_API_KEY=  # Optional: for enhanced AI capabilities
CREWAI_VERBOSE=true
CREWAI_MAX_ITER=5

# Celery (Async Tasks)
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/1
CELERY_TASK_TRACK_STARTED=true

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json  # or "text"
LOG_FILE=logs/app.log

# Monitoring
PROMETHEUS_ENABLED=true
PROMETHEUS_PORT=9090
OPENTELEMETRY_ENABLED=false
JAEGER_ENDPOINT=http://localhost:14268/api/traces
```

### 3. Initialize Databases

```bash
# Run database migrations
alembic upgrade head

# Create initial MinIO buckets (optional script)
python scripts/init_storage.py

# Create Elasticsearch indices
python scripts/init_search.py
```

## 🏃 Running the Application

### Development Mode

```bash
# Start the server with auto-reload
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# Or use the development script
python -m src.main
```

### Production Mode

```bash
# Using Gunicorn with Uvicorn workers
gunicorn src.main:app \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8000 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile -
```

### Start Celery Worker (for async tasks)

```bash
# In a separate terminal
celery -A src.tasks.celery_app worker --loglevel=info
```

### Start Celery Beat (for scheduled tasks)

```bash
# In another terminal
celery -A src.tasks.celery_app beat --loglevel=info
```

## 📁 Project Structure

```
backend/
├── src/
│   ├── agents/                 # CrewAI agent implementations
│   │   ├── orchestrator/       # Main workflow coordinator
│   │   ├── document_analyzer/  # Document structure analysis
│   │   ├── image_ocr/         # OCR processing agent
│   │   ├── amharic_nlp/       # Amharic NLP agent
│   │   ├── pdf_extractor/     # PDF text extraction
│   │   ├── word_extractor/    # Word document processing
│   │   ├── csv_processor/     # CSV data handling
│   │   ├── web_scraper/       # Web content extraction
│   │   └── quality_assurance/ # QA validation agent
│   ├── api/                   # API endpoints
│   │   ├── routes/           # Route handlers
│   │   │   ├── mcp.py        # MCP endpoints
│   │   │   ├── documents.py  # Document management
│   │   │   ├── processing.py # Processing jobs
│   │   │   ├── search.py     # Search functionality
│   │   │   ├── export.py     # Export operations
│   │   │   ├── auth.py       # Authentication
│   │   │   └── quality.py    # Quality metrics
│   │   └── websocket.py      # WebSocket handlers
│   ├── mcp/                   # MCP integration
│   │   └── tools/            # MCP tool adapters
│   ├── services/              # Business logic layer
│   │   ├── documents.py      # Document operations
│   │   ├── processing.py     # Processing orchestration
│   │   ├── search.py         # Search operations
│   │   ├── export.py         # Export functionality
│   │   ├── summarization.py  # Text summarization
│   │   ├── webhooks.py       # Webhook management
│   │   ├── quality.py        # Quality assurance
│   │   └── audit.py          # Audit logging
│   ├── db/                    # Database layer
│   │   ├── models/           # SQLAlchemy models
│   │   ├── database.py       # Database connections
│   │   └── repositories/     # Data access layer
│   ├── models/                # Pydantic schemas
│   │   └── schemas/          # API request/response models
│   ├── config/                # Configuration
│   │   ├── settings.py       # Settings management
│   │   └── logging.py        # Logging configuration
│   ├── tasks/                 # Celery tasks
│   │   └── celery_app.py     # Celery configuration
│   └── main.py                # Application entry point
├── tests/                     # Test suite
│   ├── unit/                 # Unit tests
│   ├── integration/          # Integration tests
│   ├── contract/             # Contract tests
│   └── conftest.py           # Test configuration
├── alembic/                   # Database migrations
├── scripts/                   # Utility scripts
├── docker/                    # Docker configurations
├── pyproject.toml            # Project dependencies
├── alembic.ini               # Alembic configuration
└── README.md                 # This file
```

## 🔧 Development

### Code Style

We enforce code quality with:

```bash
# Format code with Black
black src tests

# Lint with Ruff
ruff check src tests

# Type check with MyPy
mypy src

# Security scan with Bandit
bandit -r src

# Run all checks
pre-commit run --all-files
```

### Adding New Agents

1. Create agent directory in `src/agents/`
2. Implement agent class with CrewAI interface
3. Add agent configuration to orchestrator
4. Write tests in `tests/unit/agents/`

Example:
```python
# src/agents/my_agent/__init__.py
from crewai import Agent

def create_my_agent() -> Agent:
    return Agent(
        role='My Custom Agent',
        goal='Perform specific task',
        backstory='Expert in domain...',
        verbose=True,
        allow_delegation=False
    )
```

### Adding New MCP Tools

1. Add tool function to `src/mcp/tools/__init__.py`
2. Register tool in `MCP_TOOLS` dictionary
3. Add route handler in `src/api/routes/mcp.py`
4. Write tests in `tests/integration/mcp/`

### Database Migrations

```bash
# Create new migration
alembic revision --autogenerate -m "Description of changes"

# Apply migrations
alembic upgrade head

# Rollback one version
alembic downgrade -1

# View migration history
alembic history
```

## 🧪 Testing

### Run All Tests

```bash
pytest
```

### Run Specific Test Categories

```bash
# Unit tests only (fast)
pytest -m unit

# Integration tests
pytest -m integration

# Contract tests
pytest -m contract

# Skip slow tests
pytest -m "not slow"
```

### Coverage Report

```bash
# Generate coverage report
pytest --cov=src --cov-report=html --cov-report=term

# Open HTML report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

### Testing MCP Tools

```bash
# Test MCP integration
pytest tests/integration/mcp/ -v

# Test specific tool
pytest tests/integration/mcp/test_upload_document.py -v
```

### Load Testing

```bash
# Install locust
pip install locust

# Run load tests
locust -f tests/load/locustfile.py --host=http://localhost:8000
```

## 📖 API Documentation

### Interactive API Docs

Once the server is running, access:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

### Key Endpoints

#### MCP Endpoints
- `GET /api/v1/mcp/tools` - List available MCP tools
- `POST /api/v1/mcp/tools/{tool_name}/execute` - Execute MCP tool
- `GET /api/v1/mcp/status` - Server status and metrics
- `WS /api/v1/mcp/ws/{user_id}` - WebSocket connection

#### Document Management
- `POST /api/v1/documents/upload` - Upload document
- `GET /api/v1/documents/{document_id}` - Get document
- `DELETE /api/v1/documents/{document_id}` - Delete document
- `GET /api/v1/documents` - List documents

#### Processing
- `POST /api/v1/processing/jobs` - Create processing job
- `GET /api/v1/processing/jobs/{job_id}` - Get job status
- `GET /api/v1/processing/stats` - Processing statistics

#### Search
- `POST /api/v1/search` - Search documents
- `GET /api/v1/search/suggestions` - Get search suggestions

#### Export
- `POST /api/v1/export/{document_id}` - Export document
- `GET /api/v1/export/templates` - List export templates

## 🐛 Debugging

### Enable Debug Logging

```bash
# Set in .env
LOG_LEVEL=DEBUG
DB_ECHO=true

# Or via environment variable
LOG_LEVEL=DEBUG uvicorn src.main:app --reload
```

### Debug with VS Code

Create `.vscode/launch.json`:
```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "FastAPI",
            "type": "python",
            "request": "launch",
            "module": "uvicorn",
            "args": [
                "src.main:app",
                "--reload",
                "--host", "0.0.0.0",
                "--port", "8000"
            ],
            "jinja": true,
            "justMyCode": false
        }
    ]
}
```

### Common Issues

**Issue**: Database connection errors
```bash
# Solution: Check if PostgreSQL is running
systemctl status postgresql  # Linux
brew services list  # macOS

# Test connection
psql -U postgres -h localhost -d amharic_doc_system
```

**Issue**: Import errors for Amharic models
```bash
# Solution: Download required models
python scripts/download_models.py
```

**Issue**: Celery tasks not executing
```bash
# Solution: Ensure Celery worker is running
celery -A src.tasks.celery_app inspect active
```

## 📊 Monitoring

### Prometheus Metrics

Access metrics at: http://localhost:8000/metrics

Key metrics:
- `http_requests_total` - Total HTTP requests
- `http_request_duration_seconds` - Request duration
- `processing_jobs_total` - Total processing jobs
- `processing_job_duration_seconds` - Job processing time

### Health Checks

```bash
# Application health
curl http://localhost:8000/health

# MCP health
curl http://localhost:8000/api/v1/mcp/health

# Database health
curl http://localhost:8000/health/db
```

## 🤝 Contributing

Please read the main [CONTRIBUTING.md](../CONTRIBUTING.md) for guidelines.

## 📝 License

MIT License - see [LICENSE](../LICENSE) for details.

## 🆘 Support

- **Documentation**: Check [docs/](../docs/)
- **Issues**: [GitHub Issues](https://github.com/your-org/amharic-doc-mcp/issues)
- **Email**: support@amharic-docs.ai
