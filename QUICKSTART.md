# Quickstart - 2 Minutes Setup

For personal local use. No complex configuration needed.

## Step 1: Get Free API Key (1 minute)

Visit: https://makersuite.google.com/app/apikey

Click "Create API Key" → Copy it

## Step 2: Run Setup (1 minute)

```bash
cd amharic-doc-mcp/backend/scripts
./setup_simple.sh
```

**Paste your Gemini API key when asked.**

Everything else is auto-configured!

## Step 3: Start Services

```bash
cd ../../infrastructure
docker-compose up -d
```

Wait 30 seconds.

## Step 4: Test

```bash
cd ..
./test_ai.py
```

## Step 5: Use It

Open: http://localhost:3000

That's it! 🎉

---

## What You Get

- ✅ Gemini AI for Amharic OCR (free)
- ✅ Automatic proofreading
- ✅ Document search
- ✅ Web interface
- ✅ Monitoring dashboards

## Access URLs

- Web UI: http://localhost:3000
- API: http://localhost:8000/docs
- Monitoring: http://localhost:3001 (admin/admin)

## Troubleshooting

**Services won't start?**
```bash
docker-compose logs
```

**Gemini not working?**
```bash
# Check API key loaded
docker-compose exec backend env | grep GOOGLE_API_KEY
```

**Want to backup?**
```bash
cd infrastructure/scripts
./backup_local.sh
```

---

## Configuration File

Your `.env` file contains only 4 things:

```bash
GOOGLE_API_KEY=your_key          # Required
OPENROUTER_API_KEY=optional      # Fallback
MASTER_ENCRYPTION_KEY=auto       # Auto-generated
POSTGRES_PASSWORD=local_default  # For local use
```

**That's all you need!**

No complex configs. No unnecessary settings. Just works.

---

## Need More?

- Full setup: [SETUP.md](./SETUP.md)
- AI details: [AI_SETUP.md](./AI_SETUP.md)
- Main docs: [README.md](./README.md)