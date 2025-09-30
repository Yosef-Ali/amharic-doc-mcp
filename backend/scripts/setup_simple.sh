#!/bin/bash
#
# Simple Setup Script
# Creates minimal .env file for personal use
#

set -e

echo "========================================"
echo "Amharic Document System - Simple Setup"
echo "========================================"
echo ""

# Check if .env already exists
if [ -f "../.env" ]; then
    echo "⚠️  .env file already exists!"
    read -p "Overwrite? (yes/no): " confirm
    if [ "$confirm" != "yes" ]; then
        echo "Setup cancelled."
        exit 0
    fi
fi

# Generate master encryption key
echo "Generating encryption key..."
MASTER_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")

# Get Gemini API key
echo ""
echo "📝 Enter your API keys:"
echo ""
read -p "Gemini API key (required): " GEMINI_KEY

if [ -z "$GEMINI_KEY" ]; then
    echo "❌ Gemini API key is required!"
    echo "Get one free at: https://makersuite.google.com/app/apikey"
    exit 1
fi

# Optional OpenRouter key
echo ""
read -p "OpenRouter API key (optional, press Enter to skip): " OPENROUTER_KEY

# Optional Claude key
echo ""
read -p "Claude API key (optional, press Enter to skip): " CLAUDE_KEY

# Create .env file
cat > ../.env << EOF
# ============================================
# Amharic Document System - Personal Config
# Generated: $(date)
# ============================================

# AI APIs
GOOGLE_API_KEY=${GEMINI_KEY}
EOF

if [ -n "$OPENROUTER_KEY" ]; then
    echo "OPENROUTER_API_KEY=${OPENROUTER_KEY}" >> ../.env
fi

if [ -n "$CLAUDE_KEY" ]; then
    echo "ANTHROPIC_API_KEY=${CLAUDE_KEY}" >> ../.env
fi

cat >> ../.env << EOF

# Encryption
MASTER_ENCRYPTION_KEY=${MASTER_KEY}
ENCRYPTION_KEY_VERSION=1

# Database (local defaults)
POSTGRES_PASSWORD=postgres_pass
MONGODB_PASSWORD=mongo_pass
EOF

echo ""
echo "========================================"
echo "✅ Setup Complete!"
echo "========================================"
echo ""
echo ".env file created with:"
echo "  ✅ Gemini API key"
if [ -n "$OPENROUTER_KEY" ]; then
    echo "  ✅ OpenRouter API key (fallback)"
fi
if [ -n "$CLAUDE_KEY" ]; then
    echo "  ✅ Claude API key"
fi
echo "  ✅ Encryption key (auto-generated)"
echo "  ✅ Database passwords (defaults)"
echo ""
echo "Next steps:"
echo "  1. cd ../infrastructure"
echo "  2. docker-compose up -d"
echo "  3. Wait 30 seconds for services to start"
echo "  4. Open http://localhost:3000"
echo ""
echo "Test AI:"
echo "  cd .. && ./test_ai.py"
echo ""