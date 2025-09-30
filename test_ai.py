#!/usr/bin/env python3
"""
Quick test script for AI providers

Tests Gemini and OpenRouter integration
"""

import os
import sys

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from src.config.ai_providers import get_ai_provider


def test_providers():
    """Test AI provider initialization"""
    print("=" * 60)
    print("Testing AI Providers")
    print("=" * 60)

    try:
        ai = get_ai_provider()
        print("✅ AI Provider Manager initialized")

        if ai.primary_provider:
            print(f"✅ Primary provider: {ai.primary_provider}")
        else:
            print("⚠️  No primary provider")

        print(f"✅ Available providers: {list(ai.providers.keys())}")

    except Exception as e:
        print(f"❌ Provider initialization failed: {e}")
        print("\nMake sure you have API keys set:")
        print("  export GOOGLE_API_KEY=your_key")
        print("  export OPENROUTER_API_KEY=your_key")
        return False

    return True


def test_text_proofreading():
    """Test Amharic text proofreading"""
    print("\n" + "=" * 60)
    print("Testing Amharic Proofreading")
    print("=" * 60)

    test_text = "ሰላም! ይህ የአማርኛ ጽሁፍ ነው።"  # "Hello! This is Amharic text."

    try:
        ai = get_ai_provider()

        print(f"\nOriginal text: {test_text}")
        print("Sending to AI for proofreading...")

        result = ai.proofread_amharic(test_text)

        print(f"\n✅ Proofread successful!")
        print(f"   Provider: {result['provider']}")
        print(f"   Has changes: {result['has_changes']}")

        if result['has_changes']:
            print(f"   Corrected: {result['corrected']}")
        else:
            print("   ✅ No errors found!")

        return True

    except Exception as e:
        print(f"❌ Proofreading failed: {e}")
        return False


def test_summarization():
    """Test Amharic summarization"""
    print("\n" + "=" * 60)
    print("Testing Amharic Summarization")
    print("=" * 60)

    long_text = """
ኢትዮጵያ በምስራቅ አፍሪካ የምትገኝ ሀገር ናት። ከመቶ በላይ ሚሊዮን ህዝብ አለት።
አዲስ አበባ የኢትዮጵያ ዋና ከተማ ናት። ኢትዮጵያ ብዙ ቋንቋዎች እና ባህሎች አሏት።
የኢትዮጵያ ታሪክ በጣም ጥንታዊ እና የተለያየ ነው።
    """.strip()

    try:
        ai = get_ai_provider()
        gemini = ai.get_gemini_provider()

        if not gemini:
            print("⚠️  Gemini not available, skipping summarization test")
            return True

        print(f"\nOriginal text ({len(long_text)} chars):")
        print(long_text)

        print("\nGenerating summary...")

        summary = gemini.summarize_amharic(long_text, max_length=100)

        print(f"\n✅ Summary generated!")
        print(f"   Length: {len(summary)} chars")
        print(f"   Summary: {summary}")

        return True

    except Exception as e:
        print(f"❌ Summarization failed: {e}")
        return False


def main():
    """Run all tests"""
    print("\n🚀 Amharic Document System - AI Provider Test\n")

    # Check environment
    has_gemini = bool(os.getenv("GOOGLE_API_KEY"))
    has_openrouter = bool(os.getenv("OPENROUTER_API_KEY"))

    print("Environment Check:")
    print(f"  GOOGLE_API_KEY: {'✅ Set' if has_gemini else '❌ Not set'}")
    print(f"  OPENROUTER_API_KEY: {'✅ Set' if has_openrouter else '❌ Not set'}")

    if not has_gemini and not has_openrouter:
        print("\n❌ No API keys found!")
        print("\nSet at least one:")
        print("  export GOOGLE_API_KEY=your_gemini_key")
        print("  export OPENROUTER_API_KEY=your_openrouter_key")
        sys.exit(1)

    print()

    # Run tests
    results = []

    results.append(("Provider Init", test_providers()))
    results.append(("Proofreading", test_text_proofreading()))
    results.append(("Summarization", test_summarization()))

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)

    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {name}: {status}")

    total = len(results)
    passed = sum(1 for _, p in results if p)

    print(f"\n{passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All tests passed! System ready to use.")
        return 0
    else:
        print("\n⚠️  Some tests failed. Check error messages above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())