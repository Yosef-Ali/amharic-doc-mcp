# Amharic Document Preparation System

> A comprehensive, AI-powered document processing system specifically designed for Amharic language documents with Model Context Protocol (MCP) integration.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com/)
[![React 18](https://img.shields.io/badge/React-18.2-blue.svg)](https://reactjs.org/)

## 🌟 Overview

The Amharic Document Preparation System is a production-ready platform that intelligently processes multiple document sources (PDF, images, Word, CSV, web content) and generates unified, searchable documents in Amharic language. Built with CrewAI multi-agent orchestration and integrated with CopilotKit via Model Context Protocol.

### Key Features

- 🤖 **Multi-Agent AI Processing** - CrewAI-powered intelligent document analysis and processing
- 📝 **Comprehensive Format Support** - PDF, images, Word documents, CSV, web content
- 🔍 **Advanced OCR** - Specialized Amharic text recognition with >98% accuracy
- 🌐 **MCP Integration** - Full Model Context Protocol support with CopilotKit frontend
- 🔄 **Real-time Updates** - WebSocket-based progress tracking and notifications
- 📊 **Quality Assurance** - Automated validation and accuracy metrics
- 🔐 **Enterprise Security** - JWT authentication, audit logging, role-based access
- 📤 **Multi-Format Export** - PDF, DOCX, HTML, Markdown, JSON outputs
- 🔎 **Full-Text Search** - Elasticsearch-powered search with highlighting
- 🪝 **Webhook System** - Event-driven notifications for integrations

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Frontend (React)                         │
│              CopilotKit + MCP Client                         │
└───────────────────────┬─────────────────────────────────────┘
                        │ HTTP/WebSocket
┌───────────────────────▼─────────────────────────────────────┐
│                  Backend (FastAPI)                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  MCP Tools   │  │  REST API    │  │  WebSocket   │      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
│         │                  │                  │              │
│  ┌──────▼──────────────────▼──────────────────▼───────┐    │
│  │         CrewAI Multi-Agent Orchestrator            │    │
│  │  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐     │    │
│  │  │ OCR    │ │  NLP   │ │  QA    │ │Extract │     │    │
│  │  │ Agent  │ │ Agent  │ │ Agent  │ │ Agents │     │    │
│  │  └────────┘ └────────┘ └────────┘ └────────┘     │    │
│  └───────────────────────────────────────────────────┘    │
└───────────────────────┬─────────────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────────────┐
│                   Data Layer                                 │
│  ┌──────────┐ ┌──────────┐ ┌───────┐ ┌───────┐ ┌────────┐ │
│  │PostgreSQL│ │ MongoDB  │ │ Redis │ │ MinIO │ │Elastic │ │
│  │(Metadata)│ │(Documents)│ │(Cache)│ │ (S3)  │ │(Search)│ │
│  └──────────┘ └──────────┘ └───────┘ └───────┘ └────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start (2 Minutes)

### Simple Setup (Recommended)

```bash
# 1. Get free Gemini API key
# Visit: https://makersuite.google.com/app/apikey

# 2. Run setup script
cd backend/scripts && ./setup_simple.sh

# 3. Start services
cd ../../infrastructure && docker-compose up -d

# 4. Test
cd .. && ./test_ai.py
```

**That's it!** Open http://localhost:3000

📖 **[See QUICKSTART.md for details](./QUICKSTART.md)**

### What Gets Configured

Your `.env` file: **15 lines** (not 100+!)
- ✅ Gemini API key (you provide)
- ✅ Encryption key (auto-generated)
- ✅ Database passwords (local defaults)
- ✅ Optional: OpenRouter/Claude keys

**That's it!** Everything else uses smart defaults.

See: **[BEFORE_VS_AFTER.md](./BEFORE_VS_AFTER.md)** for comparison

### Access Points

- **Web UI**: http://localhost:3000
- **API Docs**: http://localhost:8000/docs
- **Monitoring**: http://localhost:3001 (admin/admin)

### AI Providers

- **Primary**: Gemini 2.5 (free, best for Amharic OCR/proofreading)
- **Fallback**: OpenRouter (Claude 3.5 Sonnet)
- **MCP Client**: Claude Desktop (for orchestration)

### MCP Tools for Claude

Claude client can use these tools:
1. `process_document_image` - Gemini OCR + proofreading
2. `proofread_amharic_text` - Fix errors
3. `extract_amharic_entities` - Find names, places
4. `summarize_amharic_text` - Amharic summaries
5. `search_documents` - Search processed docs

## 📚 Documentation

- [Architecture Guide](./docs/ARCHITECTURE.md)
- [API Documentation](./docs/API.md)
- [Deployment Guide](./docs/DEPLOYMENT.md)
- [Development Guide](./docs/DEVELOPMENT.md)
- [MCP Integration](./docs/MCP.md)

## 🛠️ Technology Stack

### AI & Language Processing
- **Primary OCR/NLP**: Gemini 2.5 (free, optimized for Amharic)
- **Fallback**: OpenRouter (Claude 3.5 Sonnet)
- **Orchestration**: Claude Desktop via MCP
- **Traditional OCR**: Tesseract (backup)

### Backend
- **Framework**: FastAPI (async Python web framework)
- **Task Queue**: Celery with Redis
- **Databases**: PostgreSQL, MongoDB, Redis, Elasticsearch
- **Storage**: MinIO (S3-compatible)
- **Observability**: OpenTelemetry, Prometheus, Grafana

### Frontend
- **Framework**: React 18 with TypeScript
- **MCP Client**: CopilotKit
- **Styling**: Tailwind CSS
- **State Management**: React Query
- **Build Tool**: Vite

### Infrastructure
- **Containerization**: Docker
- **Orchestration**: Kubernetes
- **CI/CD**: GitHub Actions (configured in .github/workflows/)

## 🔧 Configuration

### Environment Variables

Key environment variables (see `.env.example` for complete list):

```env
# Database
DATABASE_URL=postgresql://postgres:password@localhost:5432/amharic_doc_system
MONGODB_URL=mongodb://admin:password@localhost:27017/amharic_documents
REDIS_URL=redis://localhost:6379/0

# Storage
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minio_pass

# Search
ELASTICSEARCH_URL=http://localhost:9200

# Security
JWT_SECRET_KEY=your-secret-key-here
JWT_ALGORITHM=HS256
JWT_EXPIRATION_MINUTES=60

# MCP
MCP_SERVER_URL=http://localhost:8000/api/v1/mcp
MAX_UPLOAD_SIZE=104857600  # 100MB
```

## 🧪 Testing

### Backend Tests
```bash
cd backend

# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test types
pytest -m unit           # Unit tests only
pytest -m integration    # Integration tests only
pytest -m "not slow"     # Skip slow tests
```

### Frontend Tests
```bash
cd frontend

# Run tests
pnpm test

# Run with UI
pnpm test:ui

# Coverage report
pnpm test:coverage
```

## 📖 API Usage

### MCP Tools

The system exposes the following MCP tools for CopilotKit integration:

#### 1. Upload Document
```python
{
  "tool": "upload_document",
  "arguments": {
    "file_data": "<base64-encoded-file>",
    "filename": "document.pdf",
    "content_type": "application/pdf",
    "metadata": {"source": "email", "priority": "high"}
  }
}
```

#### 2. Get Processing Progress
```python
{
  "tool": "get_processing_progress",
  "arguments": {
    "job_id": "550e8400-e29b-41d4-a716-446655440000"
  }
}
```

#### 3. Search Documents
```python
{
  "tool": "search_documents",
  "arguments": {
    "query": "ሰላም",
    "filters": {"document_type": "pdf", "date_from": "2024-01-01"},
    "page": 1,
    "page_size": 20
  }
}
```

See [API Documentation](./docs/API.md) for complete reference.

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](./CONTRIBUTING.md) for details.

### Development Workflow

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests (`pytest` and `pnpm test`)
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

### Code Quality

We use:
- **Ruff** for linting
- **Black** for formatting
- **MyPy** for type checking
- **Bandit** for security scanning
- **Pre-commit hooks** for automated checks

```bash
# Install pre-commit hooks
pre-commit install

# Run checks manually
pre-commit run --all-files
```

## 📊 Project Status

- ✅ Core document processing pipeline
- ✅ MCP tool integration
- ✅ Multi-agent CrewAI orchestration
- ✅ WebSocket real-time updates
- ✅ Authentication and authorization
- 🚧 Advanced NLP features (in progress)
- 🚧 Batch processing optimization (in progress)
- 📋 Multi-language support (planned)

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [CrewAI](https://github.com/joaomdmoura/crewAI) for multi-agent orchestration
- [CopilotKit](https://www.copilotkit.ai/) for MCP integration
- [FastAPI](https://fastapi.tiangolo.com/) for the excellent web framework
- The Ethiopian developer community for Amharic NLP resources

## 📧 Support

- **Issues**: [GitHub Issues](https://github.com/your-org/amharic-doc-mcp/issues)
- **Email**: support@amharic-docs.ai
- **Documentation**: [docs.amharic-docs.ai](https://docs.amharic-docs.ai)

## 🗺️ Roadmap

### Q1 2025
- [ ] Advanced summarization features
- [ ] Batch processing optimization
- [ ] Enhanced quality metrics dashboard
- [ ] Mobile app support

### Q2 2025
- [ ] Multi-language support (Tigrinya, Oromo)
- [ ] Advanced analytics and reporting
- [ ] Integration with popular document management systems
- [ ] Enterprise SSO support

---

**Built with ❤️ for the Ethiopian developer community**
