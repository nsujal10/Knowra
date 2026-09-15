"""
Phase 23 – Query Decomposer

Deconstructs complex longitudinal questions (e.g. tracking a project's decisions,
actions, and discussions over multiple meetings) into parallel sub-query tasks.
"""

from __future__ import annotations

import re
from typing import List, Optional
from uuid import uuid4

from app.intelligence.cross_meeting.schemas import DecomposedQueryPlan, SubQueryTask


class QueryDecomposer:
    """
    Analyzes complex user prompts and decomposes them into focused sub-queries
    targeting topics, decision evolutions, action items, and knowledge graph edges.
    """

    LONGITUDINAL_INDICATORS = [
        r"\b(evolve|evolved|evolution|history|timeline|progression|over\s+time|over\s+months|over\s+the\s+last)\b",
        r"\b(past\s+meetings|previous\s+meetings|across\s+meetings|multiple\s+meetings|last\s+\d+\s+meetings|recent\s+meetings)\b",
        r"\b(what\s+changed|how\s+did\s+we\s+get\s+to|journey\s+of|change|changed|changes)\b",
        r"\b(decisions\s+and\s+actions|all\s+actions\s+for|decisions\s+affecting)\b",
    ]

    def is_cross_meeting_query(self, query: str) -> bool:
        clean = query.lower()
        for pat in self.LONGITUDINAL_INDICATORS:
            if re.search(pat, clean):
                return True
        return False

    def extract_entity_focus(self, query: str) -> Optional[str]:
        """Extracts the central subject/entity being queried (e.g. 'Project Apollo', 'Mobile App')."""
        match = re.search(r"(?:for|regarding|about|of|on)\s+([A-Za-z0-9\s_-]{3,35})(?:\?|$|\.|\,)", query, re.IGNORECASE)
        if match:
            candidate = match.group(1).strip()
            # Clean stop words
            if candidate.lower() not in {"the meeting", "our meetings", "this", "that", "all"}:
                return candidate
        return None

    def decompose(self, query: str) -> DecomposedQueryPlan:
        clean = query.strip()
        is_cross = self.is_cross_meeting_query(clean)
        entity = self.extract_entity_focus(clean)

        tasks: List[SubQueryTask] = []

        # 1. Semantic Topic Retrieval Task
        tasks.append(
            SubQueryTask(
                task_id=f"task_{uuid4().hex[:6]}",
                query_type="SEMANTIC_TOPIC",
                sub_query=clean,
                entity_focus=entity,
            )
        )

        # 2. Decision History Task
        decision_sub = f"decisions regarding {entity}" if entity else f"decisions in {clean}"
        tasks.append(
            SubQueryTask(
                task_id=f"task_{uuid4().hex[:6]}",
                query_type="DECISION_HISTORY",
                sub_query=decision_sub,
                entity_focus=entity,
            )
        )

        # 3. Action Items Task
        action_sub = f"action items and deliverables for {entity}" if entity else f"action items for {clean}"
        tasks.append(
            SubQueryTask(
                task_id=f"task_{uuid4().hex[:6]}",
                query_type="ACTION_ITEMS",
                sub_query=action_sub,
                entity_focus=entity,
            )
        )

        # 4. Graph Traversal Task
        if entity:
            tasks.append(
                SubQueryTask(
                    task_id=f"task_{uuid4().hex[:6]}",
                    query_type="GRAPH_RELATIONSHIP",
                    sub_query=f"relationships connected to {entity}",
                    entity_focus=entity,
                )
            )

        intent = "CROSS_MEETING_EVOLUTION" if is_cross else "GENERAL_CROSS_MEETING"

        return DecomposedQueryPlan(
            original_query=clean,
            intent=intent,
            requires_cross_meeting=is_cross,
            tasks=tasks,
        )
