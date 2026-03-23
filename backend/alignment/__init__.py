"""
Hifdh Review App - Alignment Module

This module contains the core alignment components:
- ArabicTextNormalizer: Normalizes Arabic text for comparison
- ContinuationAlignmentEngine: Tracks position in expected text
- MistakeClassifier: Categorizes alignment events into mistake types
- FeedbackPolicyEngine: Decides when and how to surface feedback
"""

from .normalizer import ArabicTextNormalizer
from .engine import ContinuationAlignmentEngine
from .classifier import MistakeClassifier
from .feedback import FeedbackPolicyEngine

__all__ = [
    "ArabicTextNormalizer",
    "ContinuationAlignmentEngine",
    "MistakeClassifier",
    "FeedbackPolicyEngine",
]
