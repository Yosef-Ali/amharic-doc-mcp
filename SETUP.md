# Quick Setup Guide - Amharic Document System

Simple setup for local testing with Gemini + Claude MCP.

## 1. Get API Keys (Free)

### Gemini API Key (Primary - Free)

1. Go to https://makersuite.google.com/app/apikey
2. Click "Create API Key"
3. Copy your key

**Free tier:** 15 requests/minute, 1M tokens/minute

### OpenRouter API Key (Fallback)

1. Go to https://openrouter.ai/keys
2. Sign up and get $10 free credit
3. Copy your key

### Claude API Key (for MCP client)

1. Go to https://console.anthropic.com/
2. Get API key (optional - only if using Claude directly)

## 2. Setup Environment

```bash
# Clone repo
cd amharic-doc-mcp

# Create .env file
cat > .env << 'EOF'
# AI Providers (Required)
GOOGLE_API_KEY=your_gemini_api_key_here
OPENROUTER_API_KEY=your_openrouter_key_here

# MCP (Optional)
ANTHROPIC_API_KEY=your_anthropic_key_here

# Encryption (Auto-generated)
MASTER_ENCRYPTION_KEY=will_be_generated
ENCRYPTION_KEY_VERSION=1
EOF

# Generate encryption keys
cd backend
python scripts/generate_encryption_keys.py --output ../.env

# Edit .env and add your API keys
nano ../.env
```

## 3. Start Services

```bash
cd infrastructure
docker-compose up -d
```

Wait ~30 seconds for all services to start.

## 4. Test OCR with Gemini

```bash
# Test Gemini OCR
curl -X POST http://localhost:8000/api/v1/ocr/image \
  -F "file=@your_amharic_document.jpg" \
  -F "language=amh"

# Response:
{
  "text": "የአማርኛ ጽሁፍ...",
  "confidence": 0.95,
  "provider": "gemini",
  "proofread": {
    "corrected": "...",
    "has_changes": false
  }
}
```

## 5. Use Claude MCP Client

### Option A: Claude Desktop App

1. Install Claude Desktop
2. Add MCP server config:

```json
// ~/Library/Application Support/Claude/claude_desktop_config.json
{
  "mcpServers": {
    "amharic-doc": {
      "command": "python",
      "args": ["-m", "src.mcp.simple_server"],
      "cwd": "/path/to/amharic-doc-mcp/backend"
    }
  }
}
```

3. Restart Claude Desktop

4. Use tools in chat:
```
Please process this Amharic document image: /path/to/image.jpg
```

### Option B: API Integration

```python
# In your code
from anthropic import Anthropic

client = Anthropic(api_key="your_key")

# Use MCP tools
response = client.messages.create(
    model="claude-3-5-sonnet-20241022",
    messages=[{
        "role": "user",
        "content": "Process this Amharic document and proofread it"
    }],
    tools=[
        {
            "name": "process_document_image",
            "description": "OCR using Gemini, best for Amharic",
            "input_schema": {
                "type": "object",
                "properties": {
                    "image_path": {"type": "string"},
                    "language": {"type": "string", "default": "amh"}
                }
            }
        }
    ]
)
```

## 6. Access Web Interface

Open in browser:
- **Web UI**: http://localhost:3000
- **API Docs**: http://localhost:8000/docs
- **Monitoring**: http://localhost:3001 (admin/admin)

## Available MCP Tools

Claude can use these tools:

1. **process_document_image** - OCR with Gemini + proofreading
2. **proofread_amharic_text** - Fix spelling/grammar
3. **extract_amharic_entities** - Find names, places, etc.
4. **summarize_amharic_text** - Generate Amharic summary
5. **search_documents** - Search processed docs
6. **get_processing_status** - Check job progress

## Example Workflows

### Workflow 1: Process Amharic Document

```
User to Claude: "Please process this Amharic document image and fix any errors"

Claude uses:
1. process_document_image(image.jpg, language="amh")
   → Returns text with proofreading
2. extract_amharic_entities(text)
   → Finds people, places
3. summarize_amharic_text(text, max_length=200)
   → Creates summary

Result: Corrected text, entities, and summary in Amharic
```

### Workflow 2: Batch Processing

```
User to Claude: "Process all images in this folder"

Claude orchestrates:
- For each image:
  - Call process_document_image
  - Store results
  - Track progress

- When complete:
  - Summarize all documents
  - Create index
```

## Troubleshooting

### Gemini Rate Limit

```
Error: "Quota exceeded"

Solution: OpenRouter will automatically be used as fallback
Check logs: docker-compose logs backend
```

### MCP Connection Failed

```bash
# Check MCP server is running
curl http://localhost:8001/health

# Check Claude config path
ls -la ~/Library/Application\ Support/Claude/claude_desktop_config.json

# Restart Claude Desktop
```

### No API Keys

```
Error: "GOOGLE_API_KEY not found"

Solution:
1. Edit .env file
2. Add: GOOGLE_API_KEY=your_key_here
3. Restart: docker-compose restart backend
```

## Performance

### Gemini OCR Speed
- Small image (< 1MB): ~2-3 seconds
- Large image (5MB): ~5-8 seconds
- Free tier: 15 requests/minute

### Resource Usage
- RAM: ~4GB total (all services)
- Storage: ~2GB for Docker images
- CPU: Minimal (no local GPU needed)

## Backup Your Work

```bash
# Backup everything
cd infrastructure/scripts
./backup_local.sh

# Restore if needed
./restore_local.sh amharic-doc-backup-YYYYMMDD_HHMMSS
```

## Next Steps

1. **Test with your documents**
   - Upload Amharic PDFs/images
   - Check OCR accuracy
   - Test proofreading

2. **Integrate with your workflow**
   - Use Claude Desktop for interactive processing
   - Or integrate MCP tools in your code

3. **Monitor performance**
   - Grafana: http://localhost:3001
   - Check Gemini usage vs fallback rate

## Support

- Gemini docs: https://ai.google.dev/docs
- OpenRouter docs: https://openrouter.ai/docs
- Claude MCP: https://modelcontextprotocol.io/

---

**That's it!** You now have Gemini doing OCR/proofreading with OpenRouter fallback, and Claude handling orchestration via MCP. 🎉