d4-a716-446655440000",
  "ocr_metrics": {
    "average_confidence": 0.95,
    "min_confidence": 0.82,
    "max_confidence": 0.99,
    "pages_processed": 5,
    "words_recognized": 1247,
    "low_confidence_words": 23
  },
  "nlp_metrics": {
    "entities_recognized": 45,
    "sentiment_score": 0.75,
    "language_detected": "amharic",
    "language_confidence": 0.98
  },
  "quality_score": 0.93,
  "anomalies_detected": 2,
  "processing_duration_seconds": 298
}
```

### Get System Quality Report

Get overall quality report for the system.

```http
GET /quality/system?days=7
Authorization: Bearer {token}
```

**Response:**
```json
{
  "period_days": 7,
  "total_documents": 850,
  "ocr_statistics": {
    "average_confidence": 0.93,
    "documents_above_threshold": 820,
    "documents_below_threshold": 30,
    "threshold": 0.85
  },
  "sla_statistics": {
    "on_time_completion": 810,
    "delayed_completion": 40,
    "sla_compliance_rate": 0.95,
    "average_processing_time_seconds": 180
  },
  "anomalies_detected": 15,
  "failed_documents": 5,
  "success_rate": 0.99
}
```

---

## ❌ Error Handling

### Error Response Format

All errors follow a consistent format:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid request parameters",
    "details": [
      {
        "field": "filename",
        "message": "Filename is required"
      }
    ],
    "request_id": "req_abc123xyz",
    "timestamp": "2025-01-26T10:30:00Z"
  }
}
```

### HTTP Status Codes

| Code | Description | Example |
|------|-------------|---------|
| 200 | Success | Request completed successfully |
| 201 | Created | Resource created |
| 204 | No Content | Deletion successful |
| 400 | Bad Request | Invalid parameters |
| 401 | Unauthorized | Missing or invalid token |
| 403 | Forbidden | Insufficient permissions |
| 404 | Not Found | Resource doesn't exist |
| 409 | Conflict | Resource already exists |
| 422 | Unprocessable Entity | Validation failed |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Server error |
| 503 | Service Unavailable | Service temporarily down |

### Error Codes

| Code | Description |
|------|-------------|
| `AUTHENTICATION_ERROR` | Authentication failed |
| `AUTHORIZATION_ERROR` | Insufficient permissions |
| `VALIDATION_ERROR` | Request validation failed |
| `NOT_FOUND` | Resource not found |
| `CONFLICT` | Resource conflict |
| `RATE_LIMIT_EXCEEDED` | Too many requests |
| `PROCESSING_ERROR` | Document processing failed |
| `OCR_ERROR` | OCR processing failed |
| `EXPORT_ERROR` | Export generation failed |
| `STORAGE_ERROR` | Storage operation failed |
| `DATABASE_ERROR` | Database operation failed |
| `WEBHOOK_ERROR` | Webhook delivery failed |
| `INTERNAL_ERROR` | Internal server error |

### Example Error Responses

#### Validation Error (400)
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "File size exceeds maximum allowed size",
    "details": [
      {
        "field": "file",
        "message": "File size must be less than 100MB",
        "max_size": 104857600,
        "provided_size": 150000000
      }
    ]
  }
}
```

#### Authentication Error (401)
```json
{
  "error": {
    "code": "AUTHENTICATION_ERROR",
    "message": "Invalid or expired token"
  }
}
```

#### Rate Limit Error (429)
```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Rate limit exceeded",
    "retry_after": 60,
    "limit": 100,
    "window": "1 minute"
  }
}
```

#### Processing Error (422)
```json
{
  "error": {
    "code": "PROCESSING_ERROR",
    "message": "Document processing failed",
    "details": [
      {
        "step": "ocr_extraction",
        "message": "Unable to extract text from corrupted PDF"
      }
    ],
    "job_id": "660e8400-e29b-41d4-a716-446655440001"
  }
}
```

---

## 🚦 Rate Limiting

### Rate Limit Headers

All responses include rate limit information:

```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1643212800
```

### Default Rate Limits

| Endpoint Category | Limit | Window |
|------------------|-------|--------|
| Authentication | 10 requests | 1 minute |
| Document Upload | 10 uploads | 1 minute |
| Search | 30 requests | 1 minute |
| Export | 20 requests | 1 minute |
| General API | 100 requests | 1 minute |
| WebSocket | 1000 messages | 1 minute |

### Rate Limit Response

When rate limit is exceeded:

```http
HTTP/1.1 429 Too Many Requests
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1643212800
Retry-After: 60

{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Rate limit exceeded. Try again in 60 seconds",
    "retry_after": 60
  }
}
```

---

## 🔄 Pagination

### Query Parameters

All list endpoints support pagination:

- `page` (integer): Page number (starting from 1)
- `page_size` (integer): Items per page (default: 20, max: 100)

### Pagination Response

```json
{
  "items": [...],
  "total": 150,
  "page": 1,
  "page_size": 20,
  "total_pages": 8,
  "has_next": true,
  "has_previous": false,
  "next_page": 2,
  "previous_page": null
}
```

---

## 🔗 Link Relations

Response headers include link relations for pagination:

```http
Link: <http://api.example.com/documents?page=2>; rel="next",
      <http://api.example.com/documents?page=8>; rel="last",
      <http://api.example.com/documents?page=1>; rel="first"
```

---

## 📝 Request IDs

Every request receives a unique ID for tracking:

```http
X-Request-ID: req_abc123xyz789
```

Include this ID when reporting issues to support.

---

## 🌍 Internationalization

### Supported Languages

- `en` - English
- `am` - Amharic

### Language Selection

Specify preferred language in request header:

```http
Accept-Language: am
```

Or via query parameter:

```http
GET /documents?lang=am
```

---

## 📊 Monitoring & Health

### Health Check

Basic health check endpoint:

```http
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-01-26T10:30:00Z",
  "version": "1.0.0"
}
```

### Detailed Health Check

Detailed health check with component status:

```http
GET /health/detailed
Authorization: Bearer {token}
```

**Response:**
```json
{
  "status": "healthy",
  "components": {
    "database": {
      "status": "healthy",
      "response_time_ms": 5
    },
    "mongodb": {
      "status": "healthy",
      "response_time_ms": 3
    },
    "redis": {
      "status": "healthy",
      "response_time_ms": 1
    },
    "elasticsearch": {
      "status": "healthy",
      "response_time_ms": 8
    },
    "minio": {
      "status": "healthy",
      "response_time_ms": 4
    }
  },
  "timestamp": "2025-01-26T10:30:00Z"
}
```

### Metrics Endpoint

Prometheus metrics:

```http
GET /metrics
```

**Response:** Prometheus format metrics

---

## 🧪 Testing

### Test Authentication

For testing purposes (development only):

```http
POST /auth/test-login
Content-Type: application/json

{
  "test_user": "demo"
}
```

**Response:**
```json
{
  "access_token": "test_token_...",
  "note": "This is a test token. Do not use in production."
}
```

### Mock Processing

Simulate document processing (development only):

```http
POST /processing/mock
Authorization: Bearer {token}
Content-Type: application/json

{
  "duration_seconds": 5,
  "success": true
}
```

---

## 📖 Code Examples

### Python

```python
import requests
import base64

# Authentication
response = requests.post(
    'http://localhost:8000/api/v1/auth/login',
    json={'username': 'user@example.com', 'password': 'password123'}
)
token = response.json()['access_token']

# Upload document
with open('document.pdf', 'rb') as f:
    file_data = base64.b64encode(f.read()).decode()

response = requests.post(
    'http://localhost:8000/api/v1/mcp/tools/upload_document/execute',
    headers={'Authorization': f'Bearer {token}'},
    json={
        'arguments': {
            'file_data': file_data,
            'filename': 'document.pdf',
            'content_type': 'application/pdf'
        }
    }
)
result = response.json()
job_id = result['result']['job_id']

# Check status
response = requests.post(
    'http://localhost:8000/api/v1/mcp/tools/get_processing_progress/execute',
    headers={'Authorization': f'Bearer {token}'},
    json={'arguments': {'job_id': job_id}}
)
status = response.json()
print(f"Status: {status['result']['status']}")
```

### JavaScript/TypeScript

```typescript
import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000/api/v1';

// Authentication
const { data: authData } = await axios.post(`${API_BASE_URL}/auth/login`, {
  username: 'user@example.com',
  password: 'password123'
});
const token = authData.access_token;

// Upload document
const fileInput = document.querySelector('input[type="file"]');
const file = fileInput.files[0];
const reader = new FileReader();

reader.onload = async () => {
  const base64Data = reader.result.split(',')[1];
  
  const { data: uploadData } = await axios.post(
    `${API_BASE_URL}/mcp/tools/upload_document/execute`,
    {
      arguments: {
        file_data: base64Data,
        filename: file.name,
        content_type: file.type
      }
    },
    {
      headers: { Authorization: `Bearer ${token}` }
    }
  );
  
  console.log('Upload result:', uploadData);
};

reader.readAsDataURL(file);
```

### cURL

```bash
# Login
TOKEN=$(curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"user@example.com","password":"password123"}' \
  | jq -r '.access_token')

# Upload document
FILE_DATA=$(base64 -i document.pdf)
curl -X POST http://localhost:8000/api/v1/mcp/tools/upload_document/execute \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"arguments\": {
      \"file_data\": \"$FILE_DATA\",
      \"filename\": \"document.pdf\",
      \"content_type\": \"application/pdf\"
    }
  }"
```

---

## 🔒 Security Best Practices

1. **Always use HTTPS in production**
2. **Store tokens securely** (never in localStorage for sensitive apps)
3. **Implement token refresh** before expiration
4. **Validate all inputs** on client side
5. **Handle errors gracefully** without exposing sensitive information
6. **Implement request timeouts**
7. **Use rate limiting on client side**
8. **Verify webhook signatures**
9. **Sanitize file uploads** before processing
10. **Log security events** for audit trails

---

## 📚 Additional Resources

- [OpenAPI Specification](http://localhost:8000/openapi.json)
- [Swagger UI](http://localhost:8000/docs)
- [ReDoc Documentation](http://localhost:8000/redoc)
- [WebSocket Protocol Guide](./WEBSOCKET.md)
- [MCP Integration Guide](./MCP.md)
- [Error Handling Guide](./ERROR_HANDLING.md)

---

## 🆘 Support

For API-related questions or issues:

- **Email**: api-support@amharic-docs.ai
- **Documentation**: https://docs.amharic-docs.ai
- **Status Page**: https://status.amharic-docs.ai
- **GitHub Issues**: https://github.com/your-org/amharic-doc-mcp/issues

---

**Last Updated**: January 26, 2025  
**API Version**: v1.0.0
