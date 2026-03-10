"""
pipeline/ai/__init__.py
=======================

Public interface for the EVUA AI-assist package.

Typical usage
-------------
    from pipeline.ai import AIAssistStage, AIClient

    client = AIClient()                          # auto-selects Gemini or Groq
    stage  = AIAssistStage(app_dir, analysis, client)
    result = stage.run()                         # direct use
    # — or —
    ai_result = stage.assist(analysis, patterns, transformation, risk)  # ABC contract
"""

from pipeline.ai.client import AIClient
from pipeline.ai.stage import AIAssistStage, AIAssistResult
from pipeline.ai.result import AIResult, AISuggestion
from pipeline.ai.base import AIStage

__all__ = [
    "AIClient",
    "AIAssistStage",
    "AIAssistResult",
    "AIResult",
    "AISuggestion",
    "AIStage",
]