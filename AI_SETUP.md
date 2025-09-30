# AI Configuration Summary

## System Design

```
┌──────────────────────────────────────────────┐
│         Claude Desktop (MCP Client)          │
│              Orchestration Layer             │
└────────────────────┬─────────────────────────┘
                     │ MCP Protocol
┌────────────────────▼─────────────────────────┐
│         Your Application Backend             │
│                                              │
│  ┌──────────────────────────────────────┐   │
│  │       AI Provider Manager            │   │
│  │                                      │   │
│  │  Primary: Gemini 2.5                │   │
│  │  ├─ OCR (Amharic optimized)         │   │
│  │  ├─ Proofreading                    │   │
│  │  ├─ Entity extraction               │   │
│  │  └─ Summarization                   │   │
│  │                                      │   │
│  │  Fallback: OpenRouter                │   │
│  │  └─ Claude 3.5 Sonnet               │   │
│  └──────────────────────────────────────┘   │
└──────────────────────────────────────────────┘
```

## What Each Part Does

### 1. Gemini 2.5 (Primary)
**Cost:** FREE (15 req/min, 1M tokens/min)

**Why Gemini for Amharic:**
- Best understanding of Amharic language
- Native multilingual support (no English translation needed)
- Vision capabilities for document OCR
- Fast inference
- Free tier is generous

**Tasks:**
- OCR from images/PDFs
- Spell checking and grammar correction
- Named entity recognition (Ethiopian names, places)
- Text summarization in Amharic
- Entity extraction

### 2. OpenRouter (Fallback)
**Cost:** $10 free credit, then pay-as-you-go

**Why OpenRouter:**
- Access to Claude 3.5 Sonnet (good for Amharic)
- Automatic failover when Gemini rate-limited
- Single API for multiple models

**When Used:**
- Gemini quota exceeded
- Gemini API error
- Specific Claude features needed

### 3. Claude Desktop (MCP Client)
**Cost:** Free (or use API credits)

**Why Claude:**
- Orchestrates complex workflows
- Decides when to use which tool
- Handles multi-step processing
- User-friendly interface

**Example Flow:**
```
User: "Process these 10 Amharic documents"

Claude Desktop:
1. Loops through documents
2. Calls your MCP tool: process_document_image()
3. Your backend → Gemini does OCR
4. Claude collects results
5. Claude calls: summarize_amharic_text()
6. Returns final report to user
```

## API Keys You Need

### Required
```bash
# Gemini (FREE)
GOOGLE_API_KEY=AIza...  # Get from https://makersuite.google.com/app/apikey
```

### Recommended (Fallback)
```bash
# OpenRouter ($10 free)
OPENROUTER_API_KEY=sk-or-...  # Get from https://openrouter.ai/keys
```

### Optional
```bash
# If using Claude API directly instead of Desktop app
ANTHROPIC_API_KEY=sk-ant-...  # Get from https://console.anthropic.com/
```

## Cost Estimation

### For Local Testing (Your Use Case)

**Gemini Free Tier:**
- 15 requests/minute = 900 requests/hour
- 1 million tokens/minute
- Should cover 100% of local testing

**If You Hit Limits:**
- OpenRouter fallback kicks in automatically
- ~$0.001 per request (very cheap)

**Typical Usage:**
```
100 documents/day × 2 API calls each = 200 calls/day

With Gemini free tier: $0.00
If all went to OpenRouter: ~$0.20/day
```

## MCP Tools Available

Your backend exposes 6 tools to Claude:

### 1. process_document_image
```python
# What it does
- Takes image path
- Calls Gemini OCR
- Automatically proofreads if Amharic
- Returns corrected text + confidence

# When Claude uses it
"Process this scanned document"
"What does this image say?"
"Extract text from these photos"
```

### 2. proofread_amharic_text
```python
# What it does
- Takes Amharic text
- Fixes spelling/grammar
- Preserves meaning
- Returns corrected version

# When Claude uses it
"Fix errors in this text"
"Proofread this Amharic document"
"Is this spelled correctly?"
```

### 3. extract_amharic_entities
```python
# What it does
- Finds people, places, organizations, dates
- Returns structured list
- Ethiopian context aware

# When Claude uses it
"Who is mentioned in this document?"
"List all locations found"
"Extract names from this text"
```

### 4. summarize_amharic_text
```python
# What it does
- Creates Amharic summary
- Configurable length
- Preserves key info

# When Claude uses it
"Summarize this long document"
"Give me a brief overview"
"What's the main point?"
```

### 5. search_documents
```python
# What it does
- Searches previously processed docs
- Supports Amharic queries
- Returns highlighted results

# When Claude uses it
"Find documents about X"
"Search for mentions of Y"
"Do we have docs on Z?"
```

### 6. get_processing_status
```python
# What it does
- Checks job progress
- Returns completion percentage
- Shows results when done

# When Claude uses it
"Is processing complete?"
"Check status of job ABC"
"How many documents done?"
```

## Configuration Files

### Backend: `backend/src/config/ai_providers.py`
- `GeminiProvider` class - Handles Gemini API
- `OpenRouterProvider` class - Handles fallback
- `AIProviderManager` - Auto-switches between providers

### MCP Server: `backend/src/mcp/simple_server.py`
- Exposes tools to Claude
- Simple, focused on Amharic tasks
- No complex orchestration (Claude does that)

### Environment: `.env`
```bash
# Add these after running generate_encryption_keys.py
GOOGLE_API_KEY=your_gemini_key
OPENROUTER_API_KEY=your_openrouter_key  # optional
ANTHROPIC_API_KEY=your_claude_key  # optional
```

## Testing the Setup

### 1. Test Gemini OCR Directly
```bash
curl -X POST http://localhost:8000/api/v1/ocr/image \
  -F "file=@test_amharic.jpg" \
  -F "language=amh"

# Response shows which provider was used
{
  "text": "የአማርኛ ጽሁፍ...",
  "confidence": 0.95,
  "provider": "gemini",  # ← Should say "gemini"
  "proofread": {...}
}
```

### 2. Test Fallback
```bash
# Remove Gemini key temporarily
unset GOOGLE_API_KEY

# Same request
curl -X POST http://localhost:8000/api/v1/ocr/image ...

# Response shows fallback
{
  ...
  "provider": "openrouter"  # ← Now says "openrouter"
}
```

### 3. Test with Claude Desktop

In Claude Desktop chat:
```
You: "Process this Amharic document: /path/to/doc.jpg"

Claude will:
1. See available MCP tool: process_document_image
2. Call it with your image path
3. Get OCR result from Gemini
4. Present result to you in chat
```

## Why This Architecture?

### Separation of Concerns
- **Gemini**: Does heavy lifting (OCR, NLP)
- **Claude**: Orchestrates workflow
- **Your Backend**: Connects them with business logic

### Cost Optimization
- Free Gemini for 99% of requests
- Pay OpenRouter only on failure/overflow
- No expensive Claude API calls for simple tasks

### Flexibility
- Swap providers anytime
- Add new tools easily
- Claude learns to use tools automatically

### Local-First
- All data stays on your machine
- No cloud dependencies except AI APIs
- Full control

## Troubleshooting

### "Provider not available"
```bash
# Check API keys loaded
docker-compose exec backend env | grep API_KEY

# Should see:
GOOGLE_API_KEY=AIza...
OPENROUTER_API_KEY=sk-or-...
```

### "Gemini quota exceeded"
```bash
# Normal! Fallback will handle it
# Check logs to confirm:
docker-compose logs backend | grep -i "gemini\|openrouter"

# Should see:
"Gemini OCR failed, trying fallback"
"OpenRouter provider initialized"
```

### Claude not seeing MCP tools
```bash
# Check MCP server running
curl http://localhost:8001/tools

# Restart Claude Desktop
# Check config file:
cat ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

## Next Steps

1. ✅ Get Gemini API key (5 minutes)
2. ✅ Add to `.env` file
3. ✅ Start services: `docker-compose up -d`
4. ✅ Test OCR endpoint
5. ✅ Configure Claude Desktop MCP
6. ✅ Process your Amharic documents!

---

**You're all set!** Gemini handles Amharic processing, OpenRouter provides backup, Claude orchestrates everything. 🎯