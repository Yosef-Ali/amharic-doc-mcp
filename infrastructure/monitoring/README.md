# Observability Stack

Complete observability solution for the Amharic Document Processing System including metrics, logging, tracing, and alerting.

## Architecture

```
┌─────────────┐
│ Application │
│  Services   │──┐
└─────────────┘  │
                 │ Metrics
┌─────────────┐  │  Traces
│ Databases & │──┼─────────► Prometheus ──► Grafana
│Infrastructure│  │              │              (Visualization)
└─────────────┘  │              │
                 │              └──► Alertmanager
┌─────────────┐  │                      (Notifications)
│  Exporters  │──┘
└─────────────┘
```

## Components

### Metrics Collection
- **Prometheus**: Time-series metrics database
  - Port: 9090
  - Retention: 30 days
  - Scrape interval: 15s

### Visualization
- **Grafana**: Metrics dashboards and visualization
  - Port: 3001
  - Default credentials: admin/admin
  - Pre-configured dashboards:
    - Application Overview
    - Infrastructure Monitoring
    - Document Processing Metrics
    - SLA Dashboard

### Alerting
- **Alertmanager**: Alert routing and notifications
  - Port: 9093
  - Supports: Email, Slack, PagerDuty
  - Alert grouping and deduplication

### Distributed Tracing
- **OpenTelemetry**: Standardized tracing
  - Automatic FastAPI instrumentation
  - Database query tracing
  - Custom span creation
  - Export to Jaeger/OTLP

### Exporters
Infrastructure metrics exporters:
- **Node Exporter** (9100): System metrics (CPU, memory, disk, network)
- **Postgres Exporter** (9187): PostgreSQL metrics
- **MongoDB Exporter** (9216): MongoDB metrics
- **Redis Exporter** (9121): Redis metrics
- **Elasticsearch Exporter** (9114): Elasticsearch metrics

## Getting Started

### Start the Observability Stack

```bash
cd infrastructure
docker-compose up -d prometheus grafana alertmanager node-exporter
docker-compose up -d postgres-exporter mongodb-exporter redis-exporter elasticsearch-exporter
```

### Access Dashboards

1. **Prometheus**: http://localhost:9090
   - Query metrics directly
   - View targets and alerts

2. **Grafana**: http://localhost:3001
   - Username: `admin`
   - Password: `admin`
   - Pre-loaded dashboards in "Amharic Document System" folder

3. **Alertmanager**: http://localhost:9093
   - View active alerts
   - Manage silences

## Key Metrics

### Application Metrics

**API Performance**
- `http_requests_total`: Total HTTP requests
- `http_request_duration_seconds`: Request latency histogram
- `http_requests_in_progress`: Active requests

**Document Processing**
- `document_processing_completed_total`: Successful processing count
- `document_processing_failures_total`: Failed processing count
- `document_processing_duration_seconds`: Processing time
- `celery_queue_length`: Queue depth by priority

**OCR Quality**
- `ocr_confidence_score`: OCR confidence (0-1)
- `ocr_processing_timeout_total`: OCR timeouts

**Search Performance**
- `search_query_duration_seconds`: Search latency
- `search_indexing_queue_length`: Indexing backlog

### Infrastructure Metrics

**Databases**
- `pg_stat_database_numbackends`: PostgreSQL connections
- `mongodb_op_counters_total`: MongoDB operations
- `redis_memory_used_bytes`: Redis memory usage
- `redis_keyspace_hits_total`: Redis cache hits

**Storage**
- `minio_cluster_usage_total_bytes`: MinIO storage used
- `elasticsearch_cluster_health_status`: Elasticsearch health

**System Resources**
- `node_cpu_seconds_total`: CPU usage
- `node_memory_MemAvailable_bytes`: Available memory
- `node_disk_io_time_seconds_total`: Disk I/O

## Alerting Rules

### Critical Alerts (Immediate Notification)
- `APIDown`: Backend API unavailable
- `CeleryWorkerDown`: Worker service down
- `PostgreSQLDown`: Database unavailable
- `DocumentProcessingStalled`: No processing progress
- `ProcessingSLAViolation`: SLA breach (>30min processing)

### Warning Alerts
- `HighErrorRate`: >5% error rate
- `SlowResponseTime`: p95 latency >2s
- `DocumentProcessingFailureRate`: >10% failures
- `LowOCRConfidence`: Average confidence <85%
- `HighMemoryUsage`: >85% memory used

### Alert Routing
- **Critical**: Email + Slack + PagerDuty (immediate)
- **Database**: Database team (2h repeat)
- **Application**: Backend team (2h repeat)
- **Infrastructure**: Ops team (4h repeat)
- **SLA Violations**: Management escalation (30min repeat)

## Dashboard Guide

### Application Overview Dashboard
- Real-time API metrics
- Document processing statistics
- Queue health
- OCR quality metrics
- System availability

**Key Panels:**
- Request rate and error rate graphs
- Response time percentiles (p50, p95, p99)
- Processing throughput
- Queue depth by priority
- OCR confidence gauge
- 24h availability stat

### Infrastructure Dashboard
- Database performance
- Storage utilization
- System resources
- Network metrics

**Key Panels:**
- PostgreSQL connections and query time
- MongoDB operations rate
- Redis memory and hit rate
- MinIO storage usage
- Elasticsearch cluster health
- CPU, memory, disk, network graphs

## Custom Metrics in Code

### Add Prometheus Metrics

```python
from prometheus_client import Counter, Histogram, Gauge

# Counter example
documents_processed = Counter(
    'document_processing_completed_total',
    'Total documents processed successfully',
    ['format', 'language']
)
documents_processed.labels(format='pdf', language='amh').inc()

# Histogram example
processing_duration = Histogram(
    'document_processing_duration_seconds',
    'Document processing time',
    ['priority']
)
with processing_duration.labels(priority='urgent').time():
    # ... processing logic ...

# Gauge example
queue_size = Gauge(
    'celery_queue_length',
    'Number of tasks in queue',
    ['queue']
)
queue_size.labels(queue='standard').set(150)
```

### Add OpenTelemetry Tracing

```python
from src.config.opentelemetry import get_tracer, SpanAttributes

tracer = get_tracer(__name__)

async def process_document(document_id: str):
    with tracer.start_as_current_span("process_document") as span:
        span.set_attribute(SpanAttributes.DOCUMENT_ID, document_id)

        try:
            result = await perform_ocr(document_id)
            span.set_attribute(SpanAttributes.OCR_CONFIDENCE, result.confidence)
            span.add_event("Processing completed")
            return result
        except Exception as e:
            span.record_exception(e)
            raise
```

## Alert Configuration

### Email Alerts
Edit `alertmanager/alertmanager.yml`:
```yaml
global:
  smtp_smarthost: 'smtp.gmail.com:587'
  smtp_from: 'alerts@amharic-docs.ai'
  smtp_auth_username: 'alerts@amharic-docs.ai'
  smtp_auth_password: '{{ SMTP_PASSWORD }}'
```

### Slack Alerts
Set environment variable:
```bash
export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
```

### PagerDuty Integration
Set environment variable:
```bash
export PAGERDUTY_SERVICE_KEY="your-service-key"
```

## Troubleshooting

### Prometheus Not Scraping Targets
1. Check target health: http://localhost:9090/targets
2. Verify service is exposing metrics endpoint
3. Check network connectivity between containers

### No Data in Grafana
1. Verify Prometheus datasource: Configuration → Data Sources
2. Check Prometheus has data: http://localhost:9090/graph
3. Verify time range in Grafana dashboard

### Alerts Not Firing
1. Check alert rules: http://localhost:9090/alerts
2. Verify Alertmanager config: http://localhost:9093
3. Check alert inhibition rules

### High Memory Usage
Prometheus retention can be adjusted:
```yaml
command:
  - '--storage.tsdb.retention.time=15d'  # Reduce from 30d
```

## Production Recommendations

1. **Enable TLS** for all endpoints
2. **Secure credentials** using secrets management
3. **Configure authentication** on Grafana/Prometheus
4. **Set up persistent storage** for metrics data
5. **Configure backup** for Prometheus data
6. **Enable remote write** for long-term storage
7. **Set resource limits** on containers
8. **Monitor the monitoring** (meta-monitoring)

## SLA Targets

Based on system requirements:

- **API Availability**: 99.9% (measured over 30 days)
- **Document Processing**: <30 minutes (95th percentile)
- **Search Latency**: <100ms simple, <500ms complex (95th percentile)
- **OCR Confidence**: >90% average
- **Queue Processing**: 10,000 documents/day capacity

All SLA violations trigger management-level alerts.

## References

- Prometheus documentation: https://prometheus.io/docs/
- Grafana documentation: https://grafana.com/docs/
- OpenTelemetry Python: https://opentelemetry.io/docs/instrumentation/python/
- Alertmanager documentation: https://prometheus.io/docs/alerting/latest/alertmanager/