# Quickstart Guide: Amharic Document Preparation System

**Feature**: 001-build-a-comprehensive  
**Date**: 2025-01-26  
**Purpose**: Rapid system validation and integration testing scenarios

## Overview

This quickstart guide provides step-by-step instructions for setting up, testing, and validating the Amharic Document Preparation System. It serves as both a user onboarding guide and a comprehensive integration test suite.

## Prerequisites

### System Requirements
- **Docker** 20.10+ with Docker Compose
- **Python** 3.11+ (for development)
- **Node.js** 18+ (for CopilotKit frontend)
- **Kubernetes** 1.24+ (for production deployment)
- **Git** for version control
- **jq** 1.7+ (JSON parsing in shell commands)

### Hardware Requirements
- **Minimum**: 8GB RAM, 4 CPU cores, 50GB storage
- **Recommended**: 16GB RAM, 8 CPU cores, 200GB SSD storage
- **Production**: 32GB RAM, 16 CPU cores, 1TB SSD storage

### Test Data Requirements
- Sample Amharic PDF documents (provided in `/test-data/`)
- Sample scanned images with Amharic text
- Word documents with mixed Amharic/English content
- CSV files with Ethiopian data

## Quick Start (5 Minutes)

### 1. Environment Setup
```bash
# Clone the repository
git clone https://github.com/your-org/amharic-document-system.git
cd amharic-document-system

# Copy environment configuration
cp .env.example .env
# Edit .env with your configuration

# Start the complete system with Docker Compose
docker-compose up -d

# Wait for all services to be healthy
docker-compose ps
```

### 2. Verify System Health
```bash
# Check API health
curl http://localhost:8000/health

# Check database connectivity
curl http://localhost:8000/api/v1/status

# Check CrewAI agents status
curl http://localhost:8000/api/v1/processing/status
```

### 3. First Document Upload (Web UI)
1. Open browser to http://localhost:3000
2. Login with demo credentials: `demo@amharic-docs.ai` / `demo123`
3. Click "Upload Documents" 
4. Drag and drop `/test-data/sample-amharic.pdf`
5. Click "Start Processing"
6. Watch real-time progress in the dashboard

### 4. Obtain an API Access Token
```bash
# Log in with the demo credentials to retrieve an access token
JWT_TOKEN=$(curl -s -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email": "demo@amharic-docs.ai", "password": "demo123"}' \
  | jq -r '.access_token')

if [ -z "${JWT_TOKEN}" ] || [ "${JWT_TOKEN}" = "null" ]; then
  echo "Login failed. Confirm the API is running and the credentials are valid." >&2
else
  # Export the token so subsequent commands can use it
  export JWT_TOKEN
  echo "JWT_TOKEN exported for API requests." >&2
fi
```

### 5. Verify Processing Results
```bash
# Check processing job status
JOB_ID=$(curl -s "http://localhost:8000/api/v1/processing/jobs" \
  -H "Authorization: Bearer ${JWT_TOKEN}" | jq -r '.jobs[0].id')

if [ -z "${JOB_ID}" ] || [ "${JOB_ID}" = "null" ]; then
  echo "No processing jobs found. Confirm the upload completed successfully." >&2
else
  curl "http://localhost:8000/api/v1/processing/jobs/${JOB_ID}" \
    -H "Authorization: Bearer ${JWT_TOKEN}"

  # Capture the processed document ID associated with the job
  DOC_ID=$(curl -s "http://localhost:8000/api/v1/documents?job_id=${JOB_ID}" \
    -H "Authorization: Bearer ${JWT_TOKEN}" | jq -r '.documents[0].id')

  if [ -z "${DOC_ID}" ] || [ "${DOC_ID}" = "null" ]; then
    echo "Processed document not found. Verify the job includes completed documents." >&2
  else
    # Download processed document
    curl -X POST "http://localhost:8000/api/v1/export/documents/${DOC_ID}" \
      -H "Authorization: Bearer ${JWT_TOKEN}" \
      -H "Content-Type: application/json" \
      -d '{"format": "pdf"}' \
      --output processed-document.pdf
  fi
fi
```

## Detailed Validation Scenarios

### Scenario 1: Multi-Format Document Processing

**Objective**: Validate that the system can handle all supported document formats

**Test Steps**:
```bash
# 1. Prepare test files
mkdir -p test-uploads
cp test-data/sample.pdf test-uploads/
cp test-data/amharic-scan.jpg test-uploads/
cp test-data/mixed-content.docx test-uploads/
cp test-data/ethiopian-data.csv test-uploads/

# 2. Upload via API
curl -X POST "http://localhost:8000/api/v1/documents/upload" \
  -H "Authorization: Bearer ${JWT_TOKEN}" \
  -F "files=@test-uploads/sample.pdf" \
  -F "files=@test-uploads/amharic-scan.jpg" \
  -F "files=@test-uploads/mixed-content.docx" \
  -F "files=@test-uploads/ethiopian-data.csv" \
  -F "job_name=Multi-Format Test"

# 3. Verify all agents are triggered
curl "http://localhost:8000/api/v1/processing/jobs/${JOB_ID}/tasks" \
  -H "Authorization: Bearer ${JWT_TOKEN}"

# 4. Expected agent sequence:
# - DocumentAnalyzer: Detect file types
# - PDFExtractor: Process PDF
# - ImageOCR: Process JPG with Tesseract
# - WordExtractor: Process DOCX
# - CSVProcessor: Process CSV
# - AmharicNLP: Analyze all extracted text
# - QualityAssurance: Validate results
```

**Success Criteria**:
- All 4 documents processed successfully
- OCR accuracy >95% for clear text
- Amharic text properly normalized to UTF-8
- Document structure preserved
- Processing completed within 2 minutes

### Scenario 2: Real-Time Processing Dashboard

**Objective**: Validate CopilotKit integration and real-time updates

**Test Steps**:
1. Open CopilotKit dashboard at http://localhost:3000
2. Start a large batch upload (10+ documents)
3. Verify real-time progress updates
4. Test WebSocket connection stability
5. Verify agent status indicators

**Validation Commands**:
```bash
# Monitor WebSocket connection
wscat -c "ws://localhost:8000/ws/processing/${JOB_ID}?token=${JWT_TOKEN}"

# Expected WebSocket messages:
# {"type": "job_started", "job_id": "...", "total_documents": 10}
# {"type": "task_progress", "task_id": "...", "agent_type": "pdf_extractor", "progress": 25}
# {"type": "document_completed", "document_id": "...", "status": "completed"}
# {"type": "job_completed", "job_id": "...", "final_status": "completed"}
```

**Success Criteria**:
- Real-time updates appear within 2 seconds
- Progress percentages are accurate
- Agent status updates correctly
- No WebSocket disconnections during processing

### Scenario 3: Amharic Text Quality Validation

**Objective**: Validate Amharic-specific processing capabilities

**Test Files**: Use documents from `/test-data/amharic-samples/`
- `religious-text.pdf` - Ethiopian Orthodox text
- `government-form.jpg` - Scanned government document
- `mixed-language.docx` - Amharic/English content

**Test Steps**:
```bash
# Upload Amharic test documents
curl -X POST "http://localhost:8000/api/v1/documents/upload" \
  -H "Authorization: Bearer ${JWT_TOKEN}" \
  -F "files=@test-data/amharic-samples/religious-text.pdf" \
  -F "configuration={\"ocr_languages\": [\"amh\", \"eng\"], \"enable_spell_check\": true, \"enable_ner\": true}"

# Wait for processing and check quality metrics
DOC_ID=$(curl -s "http://localhost:8000/api/v1/documents" \
  -H "Authorization: Bearer ${JWT_TOKEN}" | jq -r '.documents[0].id')
curl "http://localhost:8000/api/v1/quality/metrics/${DOC_ID}" \
  -H "Authorization: Bearer ${JWT_TOKEN}"
```

**Expected Quality Metrics**:
```json
{
  "metrics": [
    {
      "metric_type": "ocr_accuracy",
      "score": 0.97,
      "details": {
        "confidence_threshold": 0.85,
        "character_accuracy": 0.98,
        "word_accuracy": 0.96
      }
    },
    {
      "metric_type": "language_detection",
      "score": 0.99,
      "details": {
        "detected_language": "amh",
        "confidence": 0.99,
        "script_type": "ge'ez"
      }
    },
    {
      "metric_type": "ner_confidence",
      "score": 0.89,
      "details": {
        "entities_found": 15,
        "high_confidence_entities": 13
      }
    }
  ]
}
```

**Success Criteria**:
- OCR accuracy ≥95% for clear scans
- Language detection confidence ≥90%
- NER identifies Ethiopian names, places, dates
- Text normalization preserves Amharic characters

### Scenario 4: Search and Discovery

**Objective**: Validate full-text search with Amharic language support

**Test Steps**:
```bash
# After processing documents, test search functionality
curl -X POST "http://localhost:8000/api/v1/search/documents" \
  -H "Authorization: Bearer ${JWT_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "ኢትዮጵያ",
    "filters": {
      "document_types": ["pdf", "image"],
      "languages": ["amh"]
    },
    "sort": {"field": "relevance", "order": "desc"}
  }'

# Test search suggestions
curl "http://localhost:8000/api/v1/search/suggestions?query=እም" \
  -H "Authorization: Bearer ${JWT_TOKEN}"
```

**Expected Search Results**:
```json
{
  "results": [
    {
      "document": {
        "id": "...",
        "filename": "religious-text.pdf",
        "document_type": "pdf"
      },
      "relevance_score": 0.95,
      "highlights": ["<mark>ኢትዮጵያ</mark> ኦርቶዶክስ ተዋሕዶ ቤተ ክርስቲያን"],
      "snippet": "በ<mark>ኢትዮጵያ</mark> ያለው የእምነት ስርዓት..."
    }
  ],
  "total_matches": 3,
  "query_time": 0.045
}
```

**Success Criteria**:
- Amharic text search works correctly
- Search results properly highlighted
- Faceted filtering functions
- Query time <100ms for typical searches

### Scenario 5: Export and Template System

**Objective**: Validate export functionality with multiple formats

**Test Steps**:
```bash
# List available export templates
curl "http://localhost:8000/api/v1/export/templates" \
  -H "Authorization: Bearer ${JWT_TOKEN}"

# Export processed document in multiple formats
for format in pdf docx html markdown json; do
  curl -X POST "http://localhost:8000/api/v1/export/documents/${DOC_ID}" \
    -H "Authorization: Bearer ${JWT_TOKEN}" \
    -H "Content-Type: application/json" \
    -d "{\"format\": \"${format}\", \"include_metadata\": true}" \
    --output "export-test.${format}"
  
  # Verify file was created and has content
  ls -la "export-test.${format}"
done
```

**Success Criteria**:
- All export formats generate successfully
- Original formatting preserved in PDF/DOCX exports
- Metadata included when requested
- Amharic text renders correctly in all formats

## Performance Testing

### Load Testing with Multiple Users

**Test Scenario**: 50 concurrent users uploading documents
```bash
# Install load testing tool
pip install locust

# Run load test
locust -f test/load_test.py --host=http://localhost:8000 --users=50 --spawn-rate=5

# Monitor system resources during test
docker stats
```

**Performance Targets**:
- API response time: <500ms p95
- Document processing: 30 seconds for 100-page PDF
- Concurrent users: 50 without degradation
- Memory usage: <8GB per processing agent

### Processing Throughput Test

**Test Scenario**: Process 100 documents measuring throughput
```bash
# Generate test batch
python scripts/generate_test_batch.py --count=100 --output=batch-test/

# Upload entire batch
python scripts/batch_upload.py --directory=batch-test/ --job-name="Throughput Test"

# Monitor processing metrics
curl "http://localhost:8000/api/v1/quality/summary?date_from=$(date -d '1 hour ago' '+%Y-%m-%d')"
```

**Throughput Targets**:
- Processing rate: 10,000 documents per day
- Queue processing: No backlog under normal load
- Agent utilization: 70-80% average
- Error rate: <1% for valid documents

## Troubleshooting

### Common Issues and Solutions

**Issue**: Documents stuck in "processing" status
```bash
# Check agent health
curl "http://localhost:8000/api/v1/processing/status"

# Restart specific agent
docker-compose restart crewai-pdf-extractor

# Check agent logs
docker-compose logs crewai-orchestrator
```

**Issue**: OCR accuracy below threshold
```bash
# Check Tesseract language packs
docker exec amharic-ocr-agent tesseract --list-langs

# Verify image preprocessing
curl "http://localhost:8000/api/v1/processing/tasks/${TASK_ID}" | jq '.input_data.image_quality'

# Adjust OCR configuration
curl -X PATCH "http://localhost:8000/api/v1/processing/jobs/${JOB_ID}" \
  -d '{"configuration": {"quality_threshold": 0.8}}'
```

**Issue**: Search results empty for Amharic queries
```bash
# Check Elasticsearch index health
curl "http://localhost:9200/_cluster/health"

# Verify Amharic analyzer configuration
curl "http://localhost:9200/documents/_settings"

# Reindex documents
curl -X POST "http://localhost:8000/api/v1/search/reindex"
```

### Log Analysis

**Key log locations**:
- API logs: `docker-compose logs api-server`
- Agent logs: `docker-compose logs crewai-*`
- Database logs: `docker-compose logs postgres mongodb`
- Search logs: `docker-compose logs elasticsearch`

**Important log patterns to monitor**:
```bash
# Processing failures
grep "FAILED" docker-compose.log

# OCR quality issues  
grep "confidence.*below.*threshold" docker-compose.log

# Performance bottlenecks
grep "processing.*timeout\|queue.*full" docker-compose.log
```

## System Validation Checklist

Before considering the system production-ready, verify:

### Functional Requirements ✓
- [ ] PDF processing with >95% accuracy
- [ ] Image OCR with Amharic support
- [ ] Word document text extraction
- [ ] CSV data processing
- [ ] Web content scraping
- [ ] Real-time processing dashboard
- [ ] Full-text search with highlighting
- [ ] Multi-format export capabilities
- [ ] Quality metrics tracking
- [ ] User authentication and authorization

### Performance Requirements ✓
- [ ] 50 concurrent users supported
- [ ] 100MB file size limit enforced
- [ ] 30-second processing for 100-page PDFs
- [ ] 10,000 documents per day throughput
- [ ] <500ms API response times
- [ ] Real-time WebSocket updates

### Security Requirements ✓
- [ ] AES-128 encryption for stored data
- [ ] JWT authentication working
- [ ] Role-based access control
- [ ] Audit logging enabled
- [ ] Input validation preventing attacks
- [ ] HTTPS/TLS encryption in production

### Quality Requirements ✓
- [ ] WCAG 2.1 Level AA accessibility
- [ ] Daily backups with 30-day retention
- [ ] Error handling and recovery
- [ ] Monitoring and alerting configured
- [ ] Documentation complete
- [ ] Integration tests passing

## Next Steps

After completing the quickstart validation:

1. **Production Deployment**: Follow `/infrastructure/README.md` for Kubernetes deployment
2. **Custom Training**: Train OCR models with your specific document types
3. **Integration**: Set up external system integrations using API contracts
4. **Monitoring**: Configure production monitoring and alerting
5. **Scaling**: Implement horizontal scaling based on usage patterns

## Support and Resources

- **Documentation**: `/docs/` directory for detailed guides
- **API Reference**: OpenAPI spec at `/contracts/api-spec.yaml`
- **Sample Code**: `/examples/` for integration examples
- **Issue Tracking**: Use GitHub issues for bug reports
- **Community**: Join our Slack workspace for support

---

**Validation Status**: ✅ Ready for integration testing  
**Estimated Setup Time**: 15 minutes for basic setup, 2 hours for complete validation  
**Next Phase**: Execute `/tasks` command to generate implementation tasks
