"""
Phase 24 – Graph Traversal Engine

Executes secure multi-hop graph traversals with strict tenant boundary enforcement,
meeting-level access control, and graph context synthesis for RAG fusion.
"""

from __future__ import annotations

from typing import List, Optional, Set, Tuple
from uuid import UUID

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.auth.scope import AuthorizedRetrievalScope
from app.graph.models import KnowledgeEntity, KnowledgeRelationship
from app.graph.schemas import EntitySchema, RelationshipSchema, SubGraphResponse
from app.intelligence.cross_meeting.resolver import CrossMeetingResolver
from app.models.transcript_segment import TranscriptSegment


class GraphTraversalEngine:
    """
    Traverses organizational knowledge graph nodes and edges.
    Guarantees that no traversal step crosses tenant boundaries.
    """

    def __init__(self, db: Session, tenant_id: UUID) -> None:
        self.db = db
        self.tenant_id = tenant_id
        self.resolver = CrossMeetingResolver()

    def find_entities_by_name(self, query: str, limit: int = 10) -> List[KnowledgeEntity]:
        """Finds entities within tenant matching text query or known aliases."""
        clean = self.resolver.normalize(query)
        if not clean:
            return []

        tokens = clean.split()
        conditions = [
            KnowledgeEntity.canonical_name.ilike(f"%{clean}%"),
            KnowledgeEntity.name.ilike(f"%{clean}%"),
        ]
        for t in tokens:
            if len(t) > 3:
                conditions.append(KnowledgeEntity.name.ilike(f"%{t}%"))

        entities = (
            self.db.query(KnowledgeEntity)
            .filter(
                KnowledgeEntity.tenant_id == self.tenant_id,
                or_(*conditions),
            )
            .limit(limit)
            .all()
        )
        return entities

    def traverse_subgraph(
        self,
        root_entity_id: UUID,
        depth: int = 1,
        scope: Optional[AuthorizedRetrievalScope] = None,
    ) -> Optional[SubGraphResponse]:
        """
        Traverses a k-hop neighborhood from root_entity_id.
        Enforces tenant isolation and optional meeting-level RBAC filtering.
        """
        root = (
            self.db.query(KnowledgeEntity)
            .filter(
                KnowledgeEntity.id == root_entity_id,
                KnowledgeEntity.tenant_id == self.tenant_id,
            )
            .first()
        )
        if not root:
            return None

        visited_nodes: Set[UUID] = {root_entity_id}
        node_map = {root_entity_id: root}
        collected_edges: List[KnowledgeRelationship] = []

        current_layer: Set[UUID] = {root_entity_id}

        for _ in range(max(1, min(depth, 3))):
            if not current_layer:
                break

            # Find edges where source or target is in current layer
            query = (
                self.db.query(KnowledgeRelationship)
                .filter(
                    KnowledgeRelationship.tenant_id == self.tenant_id,
                    or_(
                        KnowledgeRelationship.source_entity_id.in_(list(current_layer)),
                        KnowledgeRelationship.target_entity_id.in_(list(current_layer)),
                    ),
                )
            )

            # Meeting-level filter if scope restricted
            if scope and scope.allowed_meeting_ids is not None:
                query = query.filter(
                    or_(
                        KnowledgeRelationship.meeting_id.is_(None),
                        KnowledgeRelationship.meeting_id.in_(list(scope.allowed_meeting_ids)),
                    )
                )

            edges = query.all()
            next_layer: Set[UUID] = set()

            for edge in edges:
                if edge not in collected_edges:
                    collected_edges.append(edge)

                for nid in (edge.source_entity_id, edge.target_entity_id):
                    if nid not in visited_nodes:
                        visited_nodes.add(nid)
                        next_layer.add(nid)

            if next_layer:
                new_nodes = (
                    self.db.query(KnowledgeEntity)
                    .filter(
                        KnowledgeEntity.tenant_id == self.tenant_id,
                        KnowledgeEntity.id.in_(list(next_layer)),
                    )
                    .all()
                )
                for n in new_nodes:
                    node_map[n.id] = n

            current_layer = next_layer

        # Build response schemas
        node_schemas = [EntitySchema.model_validate(n) for n in node_map.values()]
        edge_schemas = []

        for e in collected_edges:
            src = node_map.get(e.source_entity_id)
            tgt = node_map.get(e.target_entity_id)
            edge_schemas.append(
                RelationshipSchema(
                    id=e.id,
                    source_entity_id=e.source_entity_id,
                    target_entity_id=e.target_entity_id,
                    source_name=src.name if src else "Unknown",
                    target_name=tgt.name if tgt else "Unknown",
                    relationship_type=e.relationship_type,
                    confidence=e.confidence,
                    meeting_id=e.meeting_id,
                    evidence_segment_id=e.evidence_segment_id,
                )
            )

        return SubGraphResponse(
            root_entity=EntitySchema.model_validate(root),
            depth=depth,
            nodes=node_schemas,
            edges=edge_schemas,
        )

    def get_graph_context_for_query(
        self,
        query: str,
        scope: Optional[AuthorizedRetrievalScope] = None,
    ) -> List[str]:
        """
        Synthesizes relevant graph relationship statements to augment RAG context.
        """
        entities = self.find_entities_by_name(query, limit=3)
        if not entities:
            return []

        facts: List[str] = []
        for ent in entities:
            subgraph = self.traverse_subgraph(ent.id, depth=1, scope=scope)
            if subgraph:
                for edge in subgraph.edges:
                    fact = f"Entity Fact: '{edge.source_name}' --[{edge.relationship_type}]--> '{edge.target_name}'"
                    if fact not in facts:
                        facts.append(fact)

        return facts[:10]
