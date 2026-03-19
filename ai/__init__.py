"""
AI add-on layer for Vendor Atlas.

This package is entirely optional. The core app functions without it.
Enable AI features via environment variables (see features/flags.py).

Structure:
    ai/
        router.py               — FastAPI router mounted at /api/ai/*
        services/
            content_generator.py    — vendor bio, product description generation
            smart_matcher.py        — AI-powered vendor ↔ event matching
            marketing_automation.py — social posts, email copy, campaign ideas
"""
