# Technical Research: Amharic Document Preparation System

**Feature**: 001-build-a-comprehensive
**Date**: 2025-09-30
**Purpose**: Resolve NEEDS CLARIFICATION items from Technical Context

---

## Research Areas

### 1. OCR Engine Selection for Amharic

**Decision**: **Tesseract 5.x** with custom Amharic training data

**Rationale**:
- **Tesseract 5.x**: Industry-standard OCR with LSTM neural networks, mature Amharic (Ethiopic script) support via `amh` and `tir` language packs
- **Native Ethiopic support**: Pre-trained models for Amharic/Tigrinya characters
- **Customizable**: Allows fine-tuning with domain-specific training data (religious texts, administrative documents)
- **Performance**: Can achieve >95% accuracy target with 300+ DPI scans and properly trained models
- **Integration**: Python bindings via `pytesseract`, CLI-friendly for Library-First principle
- **On-premises**: Fully local execution, no cloud dependencies, meets deployment constraint

**Alternatives Considered**:
- **EasyOCR**: Good for multi-language but less mature Amharic support, slower inference
- **PaddleOCR**: Excellent for Chinese/Asian scripts but limited Ethiopic training data
- **Google Cloud Vision API**: Rejected due to on-premises constraint

**Implementation Notes**:
- Use `tesseract --oem 1` (LSTM-only mode) for best accuracy
- Combine `amh` + `eng` language packs for mixed-language documents
- Implement custom post-processing for Amharic text normalization (Ge'ez script variations)
- Pre-processing pipeline: deskewing, noise reduction, binarization for optimal OCR quality

---

### 2. Web Framework Selection

**Decision**: **FastAPI** 0.104+

**Rationale**:
- **Async support**: Native asyncio for concurrent document processing (50 concurrent users requirement)
- **Performance**: ASGI-based, faster than Flask, handles high throughput (10k documents/day)
- **Type safety**: Pydantic models for request/response validation (contract test support)
- **Auto-documentation**: OpenAPI/Swagger generation for contract tests
- **WebSocket support**: Real-time progress updates (FR-014, FR-031 requirements)
- **Testing**: Excellent pytest integration for TDD workflow
- **CrewAI compatible**: Works seamlessly with async agent execution

**Alternatives Considered**:
- **Flask**: Simpler but lacks native async, requires threading workarounds for concurrency
- **Django**: Too heavy for API-only backend, ORM overhead unnecessary

**Implementation Notes**:
- Use `BackgroundTasks` for async processing job triggers
- Implement WebSocket endpoints for real-time progress streaming
- Middleware: CORS, authentication, rate limiting, request logging
- Dependency injection for testability (services, database connections)

---

### 3. Search Engine Selection

**Decision**: **MeiliSearch** 1.5+

**Rationale**:
- **Performance**: Sub-50ms search latency, easily meets <100ms simple query target
- **Amharic support**: Excellent Unicode handling, custom tokenization for Ethiopic script
- **Typo tolerance**: Built-in fuzzy search beneficial for OCR error tolerance
- **On-premises**: Standalone binary, no cloud dependencies, low operational complexity
- **Resource efficient**: Lower memory footprint than Elasticsearch (critical for on-premises constraint)
- **Developer experience**: Simple REST API, easy integration, straightforward deployment

**Alternatives Considered**:
- **Elasticsearch**: More powerful but heavyweight, requires JVM, higher resource consumption, complex ops
- **PostgreSQL full-text**: Insufficient performance for <100ms target with large document corpus
- **Typesense**: Similar to MeiliSearch but less mature Amharic support

**Implementation Notes**:
- Custom Amharic tokenizer configuration for proper word segmentation
- Index schema: separate fields for Amharic content, metadata, language markers
- Implement synonym dictionary for Amharic term variations
- Pagination strategy: limit 100 results for <100ms guarantee

---

### 4. Task Queue System

**Decision**: **Celery** 5.3+ with **Redis** 7.x backend

**Rationale**:
- **Mature ecosystem**: Battle-tested for high-volume processing (10k docs/day requirement)
- **Priority queues**: Native support for 3-tier priority system (Urgent/Standard/Bulk from FR-017)
- **Retry logic**: Built-in retry mechanisms with exponential backoff (FR-015 error recovery)
- **Monitoring**: Flower dashboard for observability (constitutional requirement)
- **Scalability**: Horizontal scaling for on-premises capacity expansion (FR-043)
- **Integration**: Excellent FastAPI + pytest integration for TDD

**Alternatives Considered**:
- **RQ (Redis Queue)**: Simpler but lacks advanced priority queue features
- **Dramatiq**: Good alternative but smaller ecosystem, less documentation

**Implementation Notes**:
- 3 separate queues: `urgent`, `standard`, `bulk` with different worker pools
- Queue overflow policies: Redis list length monitoring, circuit breaker patterns
- Task routing: Document type/size-based intelligent queue selection
- Result backend: Redis for task status tracking, 7-day retention

---

### 5. Database Selection

**Decision**: **PostgreSQL** 15+ for metadata, **MinIO** for document storage

**Rationale**:
- **PostgreSQL**:
  - ACID compliance for critical metadata (processing status, user data, audit logs)
  - JSON/JSONB support for flexible metadata storage (extracted content, quality metrics)
  - Excellent performance for 50 concurrent users, 10k documents/day scale
  - Full RBAC support via row-level security (FR-048 requirement)
  - Native encryption at rest support (AES-128 from FR-047)

- **MinIO**:
  - S3-compatible object storage for document files (original + processed)
  - On-premises deployment, no cloud dependencies
  - Built-in versioning for 30-day backup retention (FR-046)
  - Encryption at rest (AES-256, exceeds AES-128 requirement)
  - Scales to multi-terabyte storage on local infrastructure

**Alternatives Considered**:
- **SQLite**: Too limited for 50 concurrent users, no proper concurrency
- **Filesystem storage**: Lacks versioning, backup management, encryption complexity
- **MongoDB**: Unnecessary for structured metadata, weaker consistency guarantees

**Implementation Notes**:
- PostgreSQL schema: strict typing for metadata, JSONB for extracted content
- MinIO bucket structure: `/originals/{doc_id}`, `/processed/{doc_id}`, `/exports/{doc_id}`
- Referential integrity: PostgreSQL foreign keys reference MinIO object paths
- Backup strategy: PostgreSQL daily dumps + MinIO bucket replication

---

### 6. Frontend Technology Stack

**Decision**: **React** 18+ with **TypeScript** 5.x, **Vite** build tool

**Rationale**:
- **React + TypeScript**: Type-safe component development, reduces runtime errors
- **Vite**: Fast development builds, HMR, optimal production bundles
- **Accessibility**: Mature ecosystem for WCAG 2.1 AA compliance (react-aria, radix-ui)
- **i18n support**: react-i18next for Amharic/English bilingual interface (FR-034)
- **Real-time**: Native WebSocket support for progress updates
- **Testing**: Excellent Vitest + Testing Library support for TDD

**Component Libraries**:
- **Radix UI**: Unstyled, accessible primitives (WCAG 2.1 AA baseline)
- **TanStack Query**: Async state management for API calls
- **React Dropzone**: Drag-and-drop file upload (FR-030)
- **React Virtuoso**: Virtual scrolling for large document lists

**Implementation Notes**:
- Amharic font loading: Google Fonts Noto Sans Ethiopic
- RTL support: CSS logical properties for bidirectional text
- Accessibility testing: automated axe-core checks in CI/CD
- Progressive enhancement: fallback for WebSocket to polling

---

## Best Practices Research

### OCR Pipeline Optimization
- **Pre-processing**: OpenCV for image enhancement (deskew, denoise, contrast adjustment)
- **Batch processing**: Process pages in parallel using multiprocessing pool (8-core CPU utilization)
- **Confidence scoring**: Character-level and word-level confidence from Tesseract TSV output
- **Post-processing**: Amharic-specific spell checking using Hunspell dictionaries
- **Ground truth validation**: Edit distance metrics against known documents for accuracy measurement

### Amharic Text Processing
- **Normalization**: Unicode NFD/NFC normalization for Ethiopic combining characters
- **Tokenization**: Syllable-based tokenization (Amharic syllabary structure)
- **Language detection**: FastText for identifying Amharic vs Tigrinya vs English segments
- **Mixed-language handling**: Preserve reading order, tag language boundaries in metadata
- **Named entity recognition**: spaCy custom model for Ethiopian names, places, organizations

### Security & Compliance
- **Authentication**: bcrypt for password hashing, JWT tokens for API session management
- **RBAC implementation**: PostgreSQL row-level security + application-level permissions
- **Encryption**: AES-128-CBC for database fields, TLS 1.3 for API transport
- **Audit logging**: Structured JSON logs with user ID, action, timestamp, IP address
- **GDPR compliance**: Right to erasure, data export, consent management, retention policies
- **Ethiopian data protection**: Align with Proclamation No. 1205/2020 data sovereignty requirements

### Performance Optimization
- **OCR parallelization**: GNU Parallel or Celery canvas for page-level concurrency
- **Caching strategy**: Redis cache for frequently accessed documents, TTL-based invalidation
- **Search optimization**: MeiliSearch index warming, query result caching
- **Database indexing**: B-tree on status fields, GIN on JSONB metadata, partial indexes for active jobs
- **Frontend optimization**: Code splitting, lazy loading, CDN for static assets

### Observability Implementation
- **Structured logging**: Python `structlog` with JSON output, log levels for filtering
- **Metrics collection**: Prometheus for processing times, queue depths, error rates
- **Tracing**: OpenTelemetry for distributed tracing across OCR pipeline stages
- **Dashboards**: Grafana for visualizing OCR accuracy trends, processing throughput, system health
- **Alerting**: Alert on queue overflow, processing failures, search latency violations

---

## Integration Patterns

### CrewAI Agent Communication
- **Agent roles**: OCR Specialist, Processing Coordinator, Quality Assurance, Export Generator
- **Communication**: Shared task state via Redis, event-driven triggers
- **Error handling**: Agent-level retry with exponential backoff, dead-letter queue for failures
- **Coordination**: Processing Coordinator orchestrates pipeline stages, monitors agent health

### Multi-Database Transactions
- **Two-phase commit**: PostgreSQL transaction + MinIO upload atomicity
- **Consistency checks**: Verify metadata DB references match MinIO object existence
- **Rollback strategy**: Delete MinIO objects on PostgreSQL transaction failure
- **Eventual consistency**: Search index updates asynchronously with reconciliation job

### Pipeline Validation
- **End-to-end test**: Upload sample document → verify all outputs (metadata, processed file, search index entry)
- **Quality gates**: Assert OCR confidence >70%, processing time <30s/100 pages, search indexed within 5s
- **Regression testing**: Maintain test corpus of diverse Amharic documents with ground truth

---

## Dependencies Summary

### Backend Core
```
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
celery[redis]==5.3.4
redis==5.0.1
psycopg2-binary==2.9.9
minio==7.2.0
crewai==0.76.0
```

### OCR & Processing
```
pytesseract==0.3.10
tesseract-ocr==5.3.0 (system package)
opencv-python==4.8.1
Pillow==10.1.0
pdf2image==1.16.3
python-docx==1.1.0
```

### Search & NLP
```
meilisearch==0.28.0
fasttext==0.9.2
spacy==3.7.2
```

### Testing & Observability
```
pytest==7.4.3
pytest-asyncio==0.21.1
hypothesis==6.92.0
opentelemetry-api==1.21.0
structlog==23.2.0
```

### Frontend
```json
{
  "react": "^18.2.0",
  "typescript": "^5.3.0",
  "vite": "^5.0.0",
  "@radix-ui/react-*": "^1.0.0",
  "@tanstack/react-query": "^5.0.0",
  "react-i18next": "^13.5.0",
  "react-dropzone": "^14.2.0",
  "vitest": "^1.0.0"
}
```

---

## Resolved Technical Context

All NEEDS CLARIFICATION items from Technical Context have been resolved:

| Item | Resolution |
|------|------------|
| OCR engine | Tesseract 5.x with Amharic language packs |
| Web framework | FastAPI 0.104+ |
| Search engine | MeiliSearch 1.5+ |
| Task queue | Celery 5.3+ with Redis 7.x |
| Document storage | MinIO (S3-compatible object storage) |
| Metadata database | PostgreSQL 15+ |
| Search index | MeiliSearch (separate from metadata DB) |

**Status**: ✅ Phase 0 complete - All technical unknowns resolved