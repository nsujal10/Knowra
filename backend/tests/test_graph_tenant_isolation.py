"""
Test: Knowledge Graph Tenant Isolation (Phase 24)
Asserts that graph traversals strictly respect tenant_id boundaries and
prevent cross-tenant relationship discovery or edge hopping.
"""

import uuid
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.models.organization import Organization
from app.models.user import User
from app.graph.extraction.service import GraphExtractionService
from app.graph.models import KnowledgeEntity, KnowledgeRelationship
from app.graph.retrieval.traversal import GraphTraversalEngine


@pytest.fixture
def db_session():
    engine = create_engine(settings.DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.rollback()
    session.close()


def test_graph_strict_tenant_isolation(db_session):
    run_id = str(uuid.uuid4())[:8]

    # 1. Provision Tenant Alpha and Tenant Beta
    org_a = Organization(name=f"Graph Tenant Alpha {run_id}", slug=f"graph-a-{run_id}")
    org_b = Organization(name=f"Graph Tenant Beta {run_id}", slug=f"graph-b-{run_id}")
    db_session.add_all([org_a, org_b])
    db_session.commit()

    # 2. Add Entity and Edge to Tenant Alpha
    entity_a1 = KnowledgeEntity(
        tenant_id=org_a.id,
        name="Project Apollo",
        canonical_name="Project Apollo",
        entity_type="PROJECT",
    )
    entity_a2 = KnowledgeEntity(
        tenant_id=org_a.id,
        name="Apollo Satellite Deployment",
        canonical_name="Apollo Satellite Deployment",
        entity_type="ACTION",
    )
    db_session.add_all([entity_a1, entity_a2])
    db_session.flush()

    edge_a = KnowledgeRelationship(
        tenant_id=org_a.id,
        source_entity_id=entity_a1.id,
        target_entity_id=entity_a2.id,
        relationship_type="OWNS",
    )
    db_session.add(edge_a)

    # 3. Add Entity with IDENTICAL name but in Tenant Beta
    entity_b1 = KnowledgeEntity(
        tenant_id=org_b.id,
        name="Project Apollo",
        canonical_name="Project Apollo",
        entity_type="PROJECT",
    )
    entity_b2 = KnowledgeEntity(
        tenant_id=org_b.id,
        name="Competitor Apollo Infiltration",
        canonical_name="Competitor Apollo Infiltration",
        entity_type="ACTION",
    )
    db_session.add_all([entity_b1, entity_b2])
    db_session.flush()

    edge_b = KnowledgeRelationship(
        tenant_id=org_b.id,
        source_entity_id=entity_b1.id,
        target_entity_id=entity_b2.id,
        relationship_type="ATTACKS",
    )
    db_session.add(edge_b)
    db_session.commit()

    # 4. Traversal under Tenant Alpha
    engine_a = GraphTraversalEngine(db=db_session, tenant_id=org_a.id)
    subgraph_a = engine_a.traverse_subgraph(root_entity_id=entity_a1.id, depth=2)

    assert subgraph_a is not None
    assert len(subgraph_a.nodes) == 2
    assert len(subgraph_a.edges) == 1

    node_names_a = {n.name for n in subgraph_a.nodes}
    assert "Apollo Satellite Deployment" in node_names_a
    assert "Competitor Apollo Infiltration" not in node_names_a, "Tenant Alpha must NOT see Tenant Beta's nodes"

    # 5. Attempt Cross-Tenant Traversal: Tenant Alpha querying Tenant Beta's entity ID
    cross_attempt = engine_a.traverse_subgraph(root_entity_id=entity_b1.id, depth=1)
    assert cross_attempt is None, "Cross-tenant entity traversal must return None"

    # 6. Traversal under Tenant Beta
    engine_b = GraphTraversalEngine(db=db_session, tenant_id=org_b.id)
    subgraph_b = engine_b.traverse_subgraph(root_entity_id=entity_b1.id, depth=2)

    assert subgraph_b is not None
    assert len(subgraph_b.nodes) == 2
    node_names_b = {n.name for n in subgraph_b.nodes}
    assert "Competitor Apollo Infiltration" in node_names_b
    assert "Apollo Satellite Deployment" not in node_names_b, "Tenant Beta must NOT see Tenant Alpha's nodes"
