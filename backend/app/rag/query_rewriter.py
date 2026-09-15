"""
Phase 22 – Conversational Query Rewriter

Resolves conversational context, anaphoric references, and coreferences
to produce an optimized hybrid search query (dense semantic + lexical keyword).
"""

from __future__ import annotations

import re
from typing import List, Optional

from app.rag.schemas import IntentType


class QueryRewriter:
    """
    Transforms conversational prompts into standalone retrieval queries
    by injecting context from previous turns and highlighting domain keywords.
    """

    PRONOUN_PATTERN = re.compile(r"\b(it|that|this|they|them|he|she|these|those)\b", re.IGNORECASE)

    def rewrite(
        self,
        query: str,
        intent: IntentType,
        history: Optional[List[dict]] = None,
    ) -> str:
        clean = query.strip()
        if not clean:
            return clean

        # Chitchat requires no retrieval augmentation
        if intent == IntentType.CHITCHAT:
            return clean

        # Context extraction from recent turns
        recent_context = ""
        if history:
            recent_texts = [
                msg.get("content", "").strip()
                for msg in history[-4:]
                if msg.get("content") and len(msg.get("content", "").strip()) > 5
            ]
            recent_context = " ".join(recent_texts)

        rewritten = clean

        # If query contains ambiguous pronouns and we have recent dialogue context
        if self.PRONOUN_PATTERN.search(clean) and recent_context:
            # Extract key nouns / phrase from previous context (strip punctuation)
            cleaned_context = re.sub(r"[^\w\s]", " ", recent_context).split()
            keywords = [w for w in cleaned_context if len(w) > 4 and w.lower() not in {"about", "which", "there", "their", "would", "could", "should"}][:3]
            if keywords:
                rewritten = f"{clean} ({' '.join(keywords)})"

        # Specialized Intent Keyword Augmentation for Hybrid RRF
        if intent == IntentType.ACTION_LOOKUP and "action" not in rewritten.lower():
            rewritten = f"{rewritten} action item task assignment"
        elif intent == IntentType.DECISION_LOOKUP and "decision" not in rewritten.lower():
            rewritten = f"{rewritten} decision agreed conclusion"
        elif intent == IntentType.SUMMARY and "summary" not in rewritten.lower():
            rewritten = f"{rewritten} overview key discussion topics"

        return rewritten
