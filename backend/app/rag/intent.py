"""
Phase 22 – Intent Detection Engine

Classifies conversational user queries into specialized intent categories
to guide query rewriting and context retrieval strategies.
"""

from __future__ import annotations

import re
from typing import List, Optional

from app.rag.schemas import IntentType


class IntentDetector:
    """
    Deterministic regex- and heuristic-based intent detector
    for low-latency conversational routing.
    """

    GREETING_PATTERNS = [
        r"^(hi|hello|hey|good\s+(morning|afternoon|evening)|howdy|greetings)\b",
        r"^(thanks|thank\s+you|appreciate\s+it)\b",
        r"^(who\s+are\s+you|what\s+can\s+you\s+do)\b",
    ]

    SUMMARY_PATTERNS = [
        r"\b(summarize|summary|recap|overview|key\s+takeaways|brief|run\s+through)\b",
        r"\bwhat\s+(was|were)\s+discussed\b",
    ]

    DECISION_PATTERNS = [
        r"\b(decision|decide|decided|agreement|resolution|consensus|agreed\s+upon)\b",
        r"\bwhat\s+did\s+we\s+decide\b",
    ]

    ACTION_PATTERNS = [
        r"\b(action\s+item|task|todo|to-do|next\s+steps|deliverable|assigned|deadline|due\s+date)\b",
        r"\bwho\s+is\s+(responsible|assigned|doing)\b",
    ]

    def detect(self, query: str, history: Optional[List[dict]] = None) -> IntentType:
        clean = query.strip().lower()

        # 1. Check Greeting / Chitchat
        for pat in self.GREETING_PATTERNS:
            if re.search(pat, clean):
                return IntentType.CHITCHAT

        # 2. Check Decision Lookup
        for pat in self.DECISION_PATTERNS:
            if re.search(pat, clean):
                return IntentType.DECISION_LOOKUP

        # 3. Check Action Item Lookup
        for pat in self.ACTION_PATTERNS:
            if re.search(pat, clean):
                return IntentType.ACTION_LOOKUP

        # 4. Check Summary
        for pat in self.SUMMARY_PATTERNS:
            if re.search(pat, clean):
                return IntentType.SUMMARY

        # Default to Factual Q&A
        return IntentType.FACTUAL_QA
