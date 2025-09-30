
# Implementation Plan: Amharic Document Preparation System

**Branch**: `001-build-a-comprehensive` | **Date**: 2025-09-30 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/Users/mekdesyared/amharic-doc-mcp/specs/001-build-a-comprehensive/spec.md`

## Execution Flow (/plan command scope)
```
1. Load feature spec from Input path
   → If not found: ERROR "No feature spec at {path}"
2. Fill Technical Context (scan for NEEDS CLARIFICATION)
   → Detect Project Type from file system structure or context (web=frontend+backend, mobile=app+api)
   → Set Structure Decision based on project type
3. Fill the Constitution Check section based on the content of the constitution document.
4. Evaluate Constitution Check section below
   → If violations exist: Document in Complexity Tracking
   → If no justification possible: ERROR "Simplify approach first"
   → Update Progress Tracking: Initial Constitution Check
5. Execute Phase 0 → research.md
   → If NEEDS CLARIFICATION remain: ERROR "Resolve unknowns"
6. Execute Phase 1 → contracts, data-model.md, quickstart.md, agent-specific template file (e.g., `CLAUDE.md` for Claude Code, `.github/copilot-instructions.md` for GitHub Copilot, `GEMINI.md` for Gemini CLI, `QWEN.md` for Qwen Code or `AGENTS.md` for opencode).
7. Re-evaluate Constitution Check section
   → If new violations: Refactor design, return to Phase 1
   → Update Progress Tracking: Post-Design Constitution Check
8. Plan Phase 2 → Describe task generation approach (DO NOT create tasks.md)
9. STOP - Ready for /tasks command
```

**IMPORTANT**: The /plan command STOPS at step 7. Phases 2-4 are executed by other commands:
- Phase 2: /tasks command creates tasks.md
- Phase 3-4: Implementation execution (manual or via tools)

## Summary
Build a comprehensive Amharic Document Preparation System that processes multiple document sources (PDF, images, Word, CSV, web content) and generates unified, searchable documents. The system must achieve >95% OCR accuracy for Amharic text, support 50 concurrent users, process 10,000 documents/day, and provide sub-100ms search response times. Key capabilities include multi-format ingestion with validation, intelligent OCR with mixed-language support, batch processing with priority queues, multi-format export (PDF, DOCX, HTML, Markdown, JSON), and full-text search with Amharic-specific normalization. System is deployed on-premises with local authentication, AES-128 encryption, and compliance with GDPR and Ethiopian data protection regulations.

## Technical Context
**Language/Version**: Python 3.11+ (for OCR/ML libraries, async support, CrewAI compatibility)
**Primary Dependencies**: Tesseract 5.x (OCR), FastAPI 0.104+ (web framework), MeiliSearch 1.5+ (search), Celery 5.3+ with Redis 7.x (task queue), CrewAI 0.76+ (agent orchestration)
**Storage**: PostgreSQL 15+ (metadata, audit logs, user data with JSONB for flexible schemas), MinIO (S3-compatible object storage for documents), MeiliSearch (search index with custom Amharic tokenization)
**Testing**: pytest with pytest-asyncio (TDD contract/integration/unit tests), hypothesis (property-based OCR accuracy validation), Vitest + Testing Library (frontend)
**Target Platform**: Linux server (on-premises deployment, Docker containerization for service isolation)
**Project Type**: web (FastAPI backend + React/TypeScript frontend dashboard)
**Performance Goals**: OCR 100 pages in 30s (8-core/16GB), search <100ms simple/<500ms complex, 50 concurrent processing jobs, 10k documents/day throughput
**Constraints**: On-premises only (no cloud services), <100MB per file, 99.9% uptime, AES-128 encryption at rest, WCAG 2.1 AA accessibility
**Scale/Scope**: 50 concurrent users, 10k documents/day, support 7 file formats (PDF/JPG/PNG/TIFF/BMP/DOCX/CSV), 5 export formats, 3-tier priority queue system

## Constitution Check
*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### I. Library-First ✅
- **Status**: PASS
- **Compliance**: Each document processing agent (OCR, format converters, search indexer, export generators) will be implemented as standalone, testable libraries with clear interfaces
- **Example**: `amharic_ocr` library, `document_converter` library, `search_indexer` library - each self-contained and independently testable

### II. CLI Interface ✅
- **Status**: PASS
- **Compliance**: All libraries expose CLI with text I/O protocol (stdin/args → stdout, errors → stderr)
- **Format Support**: JSON for machine consumption, human-readable for debugging
- **Example**: `amharic-ocr process --input doc.pdf --output result.json` or `cat doc.pdf | amharic-ocr --format json`

### III. Test-First (NON-NEGOTIABLE) ✅
- **Status**: PASS - ENFORCED
- **Compliance**: TDD mandatory for all CrewAI agents and services
- **Workflow**: Contract tests written → User approved → Tests fail → Implementation → Red-Green-Refactor
- **Coverage**: All OCR agents, processing pipeline agents, search agents, export agents

### IV. Integration Testing ✅
- **Status**: PASS
- **Required Areas**:
  - CrewAI agent communication (OCR agent → Processing agent → Export agent)
  - Multi-database transactions (metadata DB + search index consistency)
  - OCR pipeline validation (end-to-end document processing)
  - Search index consistency (document update → index update verification)
  - MCP tool execution flows (if applicable for agent orchestration)

### V. Observability ✅
- **Status**: PASS
- **Implementation**:
  - Text I/O ensures debuggability across all CLI tools
  - Structured logging for all CrewAI agents (processing status, errors, retries)
  - OpenTelemetry tracing for processing pipelines (ingestion → OCR → export → indexing)
  - Performance metrics: OCR accuracy (character-level >95%), processing times (100 pages/30s), search latency (<100ms/<500ms)
  - Quality metrics dashboards for confidence scores and manual review flags

**Initial Gate Assessment**: ✅ PASS - No constitutional violations. Proceeding to Phase 0.

**Post-Design Re-evaluation**: ✅ PASS - Design artifacts maintain constitutional compliance:
- Library-First: Each processing component (OCR, converters, search, export) designed as standalone library with CLI
- CLI Interface: All libraries expose text I/O protocol per contracts
- Test-First: Contract tests defined in API spec, integration tests in quickstart.md, TDD workflow enforced
- Integration Testing: Multi-database, agent communication, and pipeline tests specified in quickstart.md
- Observability: OpenTelemetry tracing, structured logging, Prometheus metrics specified in research.md

## Project Structure

### Documentation (this feature)
```
specs/[###-feature]/
├── plan.md              # This file (/plan command output)
├── research.md          # Phase 0 output (/plan command)
├── data-model.md        # Phase 1 output (/plan command)
├── quickstart.md        # Phase 1 output (/plan command)
├── contracts/           # Phase 1 output (/plan command)
└── tasks.md             # Phase 2 output (/tasks command - NOT created by /plan)
```

### Source Code (repository root)
```
backend/
├── src/
│   ├── lib/                        # Library-First: standalone, testable components
│   │   ├── ocr/                   # Amharic OCR engine (Tesseract/EasyOCR wrapper)
│   │   ├── converters/            # Format converters (PDF, Word, CSV, images)
│   │   ├── search/                # Search indexer and query engine
│   │   ├── export/                # Multi-format export generators
│   │   ├── validation/            # File validation and quality checks
│   │   └── storage/               # Storage abstraction layer
│   ├── models/                     # Data models (Document, ProcessingJob, User, etc.)
│   ├── services/                   # Business logic services
│   │   ├── ingestion.py           # Document ingestion orchestration
│   │   ├── processing.py          # Processing queue management
│   │   ├── quality.py             # Quality assurance and confidence scoring
│   │   └── auth.py                # Local authentication service
│   ├── agents/                     # CrewAI agent definitions
│   │   ├── ocr_agent.py           # OCR processing agent
│   │   ├── processing_agent.py    # Document processing orchestrator
│   │   ├── search_agent.py        # Search indexing agent
│   │   └── export_agent.py        # Export generation agent
│   ├── api/                        # FastAPI REST endpoints
│   │   ├── routes/
│   │   ├── middleware/
│   │   └── schemas/               # Pydantic request/response models
│   └── cli/                        # CLI interfaces for all libraries
│       ├── ocr_cli.py
│       ├── converter_cli.py
│       ├── search_cli.py
│       └── export_cli.py
└── tests/
    ├── contract/                   # Contract tests (API schemas, agent interfaces)
    ├── integration/                # End-to-end pipeline tests
    └── unit/                       # Unit tests for libraries and services

frontend/
├── src/
│   ├── components/                # Reusable UI components
│   │   ├── upload/                # Drag-and-drop file upload
│   │   ├── processing/            # Processing status and progress
│   │   ├── search/                # Search interface with Amharic support
│   │   └── export/                # Export format selection
│   ├── pages/                     # Page-level components
│   │   ├── Dashboard.tsx          # Batch operations dashboard
│   │   ├── Upload.tsx             # Document upload interface
│   │   ├── Search.tsx             # Search and retrieval
│   │   └── Admin.tsx              # User management (RBAC)
│   ├── services/                  # API client services
│   └── i18n/                      # Amharic/English localization
└── tests/
    ├── unit/                      # Component unit tests
    └── e2e/                       # End-to-end user flow tests (WCAG 2.1 AA)

infrastructure/
├── docker/                        # Container definitions
│   ├── backend.Dockerfile
│   ├── frontend.Dockerfile
│   └── docker-compose.yml
└── scripts/                       # Deployment and backup scripts
```

**Structure Decision**: Web application architecture selected based on requirements for backend API + frontend dashboard. Backend follows Library-First principle with standalone `lib/` components, each exposing CLI interfaces. CrewAI agents orchestrate processing pipelines. Frontend provides user-facing dashboard with Amharic/English bilingual support and WCAG 2.1 AA accessibility compliance.

## Phase 0: Outline & Research
1. **Extract unknowns from Technical Context** above:
   - For each NEEDS CLARIFICATION → research task
   - For each dependency → best practices task
   - For each integration → patterns task

2. **Generate and dispatch research agents**:
   ```
   For each unknown in Technical Context:
     Task: "Research {unknown} for {feature context}"
   For each technology choice:
     Task: "Find best practices for {tech} in {domain}"
   ```

3. **Consolidate findings** in `research.md` using format:
   - Decision: [what was chosen]
   - Rationale: [why chosen]
   - Alternatives considered: [what else evaluated]

**Output**: research.md with all NEEDS CLARIFICATION resolved

## Phase 1: Design & Contracts
*Prerequisites: research.md complete*

1. **Extract entities from feature spec** → `data-model.md`:
   - Entity name, fields, relationships
   - Validation rules from requirements
   - State transitions if applicable

2. **Generate API contracts** from functional requirements:
   - For each user action → endpoint
   - Use standard REST/GraphQL patterns
   - Output OpenAPI/GraphQL schema to `/contracts/`

3. **Generate contract tests** from contracts:
   - One test file per endpoint
   - Assert request/response schemas
   - Tests must fail (no implementation yet)

4. **Extract test scenarios** from user stories:
   - Each story → integration test scenario
   - Quickstart test = story validation steps

5. **Update agent file incrementally** (O(1) operation):
   - Run `.specify/scripts/bash/update-agent-context.sh claude`
     **IMPORTANT**: Execute it exactly as specified above. Do not add or remove any arguments.
   - If exists: Add only NEW tech from current plan
   - Preserve manual additions between markers
   - Update recent changes (keep last 3)
   - Keep under 150 lines for token efficiency
   - Output to repository root

**Output**: data-model.md, /contracts/*, failing tests, quickstart.md, agent-specific file

## Phase 2: Task Planning Approach
*This section describes what the /tasks command will do - DO NOT execute during /plan*

**Task Generation Strategy**:
The /tasks command will generate a comprehensive, dependency-ordered task list based on Phase 1 design artifacts:

1. **From API Contracts** (`contracts/api-spec.yaml`):
   - Contract test task for each endpoint group (Auth, Documents, Processing, Search, Export, Quality, MCP)
   - Pydantic schema validation tasks for request/response models
   - WebSocket connection test tasks
   - Total: ~15 contract test tasks

2. **From Data Model** (`data-model.md`):
   - Entity model creation tasks (User, Document, ProcessingJob, ProcessingTask, ExtractedContent, QualityMetric, SearchIndex, ExportTemplate)
   - Database migration tasks for PostgreSQL schema
   - MinIO bucket configuration tasks
   - MeiliSearch index setup tasks
   - Total: ~12 data model tasks

3. **From Quickstart Scenarios** (`quickstart.md`):
   - Integration test for Scenario 1: Multi-format processing
   - Integration test for Scenario 2: Real-time dashboard
   - Integration test for Scenario 3: Amharic quality validation
   - Integration test for Scenario 4: Search and discovery
   - Integration test for Scenario 5: Export system
   - Performance test tasks
   - Total: ~8 integration test tasks

4. **From Research Decisions** (`research.md`):
   - Library implementation tasks (OCR, converters, search, export, validation, storage)
   - CrewAI agent implementation tasks (OCR Specialist, Processing Coordinator, Quality Assurance, Export Generator)
   - CLI interface tasks for each library
   - Service layer tasks (ingestion, processing, quality, auth)
   - API route implementation tasks
   - Frontend component tasks (upload, processing status, search, export, admin)
   - Infrastructure tasks (Docker, deployment scripts)
   - Total: ~45 implementation tasks

**Ordering Strategy**:
1. **Phase Setup** (tasks 1-5):
   - Initialize project structure
   - Set up development environment
   - Configure databases and dependencies
   - Create base test framework

2. **TDD Cycle - Data Layer** (tasks 6-20):
   - [TEST] Write contract tests for data models
   - [IMPL] Implement PostgreSQL models
   - [IMPL] Implement MinIO storage interface
   - [IMPL] Implement MeiliSearch index configuration
   - [TEST] Run and verify model tests pass

3. **TDD Cycle - Library Layer** (tasks 21-40) - **Many [P]arallel**:
   - [TEST] Write contract tests for OCR library [P]
   - [IMPL] Implement OCR library with CLI [P]
   - [TEST] Write contract tests for converter libraries [P]
   - [IMPL] Implement PDF/Word/CSV/Image converters [P]
   - [TEST] Write contract tests for search library [P]
   - [IMPL] Implement search indexer library [P]
   - [TEST] Write contract tests for export library [P]
   - [IMPL] Implement multi-format export library [P]
   - [TEST] Write contract tests for validation library [P]
   - [IMPL] Implement file validation library [P]

4. **TDD Cycle - Agent Layer** (tasks 41-55):
   - [TEST] Write contract tests for CrewAI agents
   - [IMPL] Implement OCR Specialist agent
   - [IMPL] Implement Processing Coordinator agent
   - [IMPL] Implement Quality Assurance agent
   - [IMPL] Implement Export Generator agent
   - [TEST] Integration tests for agent communication

5. **TDD Cycle - Service Layer** (tasks 56-70):
   - [TEST] Write contract tests for services
   - [IMPL] Implement ingestion service
   - [IMPL] Implement processing queue service (Celery)
   - [IMPL] Implement authentication service
   - [IMPL] Implement quality assurance service
   - [TEST] Service integration tests

6. **TDD Cycle - API Layer** (tasks 71-90):
   - [TEST] API contract tests from OpenAPI spec
   - [IMPL] Implement FastAPI routes (Auth, Documents, Processing, Search, Export, Quality, MCP)
   - [IMPL] Implement WebSocket endpoints
   - [IMPL] Implement middleware (auth, CORS, rate limiting)
   - [TEST] End-to-end API integration tests

7. **TDD Cycle - Frontend** (tasks 91-110):
   - [TEST] Component unit tests
   - [IMPL] Implement upload components
   - [IMPL] Implement processing dashboard
   - [IMPL] Implement search interface
   - [IMPL] Implement export interface
   - [IMPL] Implement admin interface
   - [IMPL] Implement i18n (Amharic/English)
   - [TEST] E2E accessibility tests (WCAG 2.1 AA)

8. **Integration & Validation** (tasks 111-120):
   - [TEST] Execute quickstart.md Scenario 1-5
   - [TEST] Performance testing (50 concurrent users)
   - [TEST] Load testing (10k docs/day)
   - [IMPL] Observability setup (Prometheus, Grafana, OpenTelemetry)
   - [IMPL] Security hardening (encryption, RBAC, audit logs)
   - [DOCS] Complete deployment documentation

**Parallelization Strategy**:
- Library implementations are independent - mark all as [P]
- Converter libraries can be developed in parallel
- Frontend components are largely independent - mark as [P]
- API routes can be parallelized by domain (Documents [P], Processing [P], Search [P])

**Task Dependencies**:
- Data models → Services → Agents → API routes
- Libraries → Agents (agents depend on library interfaces)
- API → Frontend (frontend consumes API contracts)
- All implementation → Final integration tests

**Estimated Output**:
- **Total tasks**: ~120 tasks
- **Parallel-capable tasks**: ~40 tasks (33%)
- **Critical path**: Database setup → Libraries → Agents → API → Integration tests
- **Estimated effort**: 8-10 weeks with 2-3 developers following TDD

**Constitutional Compliance in Tasks**:
- Every implementation task preceded by corresponding test task
- All library tasks include CLI interface requirement
- Integration test tasks verify multi-component interactions
- Observability tasks include structured logging and tracing setup

**IMPORTANT**: This phase is executed by the /tasks command, NOT by /plan

## Phase 3+: Future Implementation
*These phases are beyond the scope of the /plan command*

**Phase 3**: Task execution (/tasks command creates tasks.md)  
**Phase 4**: Implementation (execute tasks.md following constitutional principles)  
**Phase 5**: Validation (run tests, execute quickstart.md, performance validation)

## Complexity Tracking
*Fill ONLY if Constitution Check has violations that must be justified*

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |


## Progress Tracking
*This checklist is updated during execution flow*

**Phase Status**:
- [x] Phase 0: Research complete (/plan command) - `research.md` generated with all technology decisions
- [x] Phase 1: Design complete (/plan command) - `data-model.md`, `contracts/api-spec.yaml`, `quickstart.md`, `CLAUDE.md` generated
- [x] Phase 2: Task planning complete (/plan command - describe approach only) - Comprehensive task generation strategy documented
- [ ] Phase 3: Tasks generated (/tasks command) - Next step: run `/tasks` to create `tasks.md`
- [ ] Phase 4: Implementation complete
- [ ] Phase 5: Validation passed

**Gate Status**:
- [x] Initial Constitution Check: PASS - All principles satisfied before Phase 0
- [x] Post-Design Constitution Check: PASS - Design artifacts maintain constitutional compliance
- [x] All NEEDS CLARIFICATION resolved - Technical Context fully specified after Phase 0
- [x] Complexity deviations documented - No violations, no deviations required

**Artifacts Generated**:
- [x] `/specs/001-build-a-comprehensive/plan.md` - This file (Implementation Plan)
- [x] `/specs/001-build-a-comprehensive/research.md` - Technology decisions and best practices
- [x] `/specs/001-build-a-comprehensive/data-model.md` - Entity relationship model and database schema
- [x] `/specs/001-build-a-comprehensive/contracts/api-spec.yaml` - OpenAPI 3.0 specification (1137 lines)
- [x] `/specs/001-build-a-comprehensive/quickstart.md` - Integration test scenarios and validation guide
- [x] `/CLAUDE.md` - Updated agent-specific context with new tech stack

---
*Based on Constitution v2.1.1 - See `/memory/constitution.md`*
