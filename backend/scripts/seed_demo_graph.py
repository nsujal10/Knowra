"""
Knowra – Enterprise Knowledge Graph Demo Seeder

Populates high-fidelity, interconnected entities and directed relationships
for realistic client demonstrations and end-to-end testing.
"""

import os
import sys

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from uuid import UUID, uuid4
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.graph.models import KnowledgeEntity, KnowledgeRelationship
from app.models.organization import Organization


def seed_knowledge_graph():
    db: Session = SessionLocal()

    try:
        # 1. Resolve Target Organization
        org = db.query(Organization).filter(Organization.name.ilike("%Softude%")).first()
        if not org:
            org = db.query(Organization).first()

        tenant_id = org.id
        print(f"[*] Seeding Knowledge Graph for Organization: '{org.name}' ({tenant_id})")

        # 2. Define Entities
        meetings_data = [
            {
                "id": uuid4(),
                "name": "Q3 Architecture & Cloud Infrastructure Review",
                "canonical": "meeting_q3_arch_review",
                "type": "MEETING",
                "metadata": {
                    "status": "COMPLETED",
                    "date": "2026-09-28",
                    "duration": "55m",
                    "lead": "Sujal Nage",
                    "summary": "Deep dive into AWS RDS migration, database sharding, and failover topologies.",
                },
            },
            {
                "id": uuid4(),
                "name": "Sprint 44 Engineering Sync & Release Planning",
                "canonical": "meeting_sprint_44_sync",
                "type": "MEETING",
                "metadata": {
                    "status": "COMPLETED",
                    "date": "2026-09-29",
                    "duration": "45m",
                    "lead": "Sarah Chen",
                    "summary": "Release blockers, UI component library refactor, and canary deployment strategy.",
                },
            },
            {
                "id": uuid4(),
                "name": "Security, Auth & Compliance Review",
                "canonical": "meeting_security_auth_review",
                "type": "MEETING",
                "metadata": {
                    "status": "COMPLETED",
                    "date": "2026-09-25",
                    "duration": "60m",
                    "lead": "David Kim",
                    "summary": "Zero-trust credential storage, OAuth 2.0 PKCE enforcement, and SOC2 readiness.",
                },
            },
            {
                "id": uuid4(),
                "name": "Executive Leadership Strategy & AI Roadmap",
                "canonical": "meeting_executive_ai_roadmap",
                "type": "MEETING",
                "metadata": {
                    "status": "COMPLETED",
                    "date": "2026-09-26",
                    "duration": "50m",
                    "lead": "Sujal Nage",
                    "summary": "Strategic allocation for LLM inference latency reduction and cross-meeting RAG synthesis.",
                },
            },
            {
                "id": uuid4(),
                "name": "Frontend Modernization & Design System Sync",
                "canonical": "meeting_frontend_design_sync",
                "type": "MEETING",
                "metadata": {
                    "status": "COMPLETED",
                    "date": "2026-09-27",
                    "duration": "40m",
                    "lead": "Harshita Patel",
                    "summary": "Component tokenization, Next.js 15 migration, and responsive canvas UX guidelines.",
                },
            },
            {
                "id": uuid4(),
                "name": "Data Platform & Vector Database Workshop",
                "canonical": "meeting_vector_db_workshop",
                "type": "MEETING",
                "metadata": {
                    "status": "COMPLETED",
                    "date": "2026-09-24",
                    "duration": "70m",
                    "lead": "Elena Rostova",
                    "summary": "Benchmarking pgvector HNSW indexing, embedding cache invalidation, and chunking strategies.",
                },
            },
        ]

        persons_data = [
            {
                "id": uuid4(),
                "name": "Sujal Nage",
                "canonical": "person_sujal_nage",
                "type": "PERSON",
                "metadata": {
                    "role": "CTO & Chief Architect",
                    "department": "Executive Leadership",
                    "focus": "System Architecture, Cloud Infrastructure, Strategy",
                },
            },
            {
                "id": uuid4(),
                "name": "Sarah Chen",
                "canonical": "person_sarah_chen",
                "type": "PERSON",
                "metadata": {
                    "role": "VP of Engineering",
                    "department": "Engineering Management",
                    "focus": "Delivery, Roadmaps, Release Cadence",
                },
            },
            {
                "id": uuid4(),
                "name": "Marcus Vance",
                "canonical": "person_marcus_vance",
                "type": "PERSON",
                "metadata": {
                    "role": "Staff Infrastructure Engineer",
                    "department": "Site Reliability & Cloud",
                    "focus": "AWS RDS, High Availability, Database Topologies",
                },
            },
            {
                "id": uuid4(),
                "name": "Elena Rostova",
                "canonical": "person_elena_rostova",
                "type": "PERSON",
                "metadata": {
                    "role": "Lead AI & Retrieval Scientist",
                    "department": "Machine Learning",
                    "focus": "Vector Embeddings, HNSW, Graph RAG",
                },
            },
            {
                "id": uuid4(),
                "name": "David Kim",
                "canonical": "person_david_kim",
                "type": "PERSON",
                "metadata": {
                    "role": "Principal Security Architect",
                    "department": "Information Security",
                    "focus": "OAuth PKCE, Credential Vaults, Data Sanitization",
                },
            },
            {
                "id": uuid4(),
                "name": "Harshita Patel",
                "canonical": "person_harshita_patel",
                "type": "PERSON",
                "metadata": {
                    "role": "Senior Frontend Lead",
                    "department": "Product Engineering",
                    "focus": "React 19, Design System, Canvas UX",
                },
            },
        ]

        decisions_data = [
            {
                "id": uuid4(),
                "name": "Standardize on AWS RDS PostgreSQL with Read Replicas",
                "canonical": "decision_aws_rds_standard",
                "type": "DECISION",
                "metadata": {
                    "status": "CONFIRMED",
                    "impact": "CRITICAL",
                    "decided_by": "Sujal Nage",
                    "rationale": "Automated backups, multi-AZ failover, and zero-maintenance connection pooling.",
                },
            },
            {
                "id": uuid4(),
                "name": "Enforce OAuth 2.0 PKCE & Encrypted Credential Vaults",
                "canonical": "decision_oauth_pkce_vaults",
                "type": "DECISION",
                "metadata": {
                    "status": "CONFIRMED",
                    "impact": "HIGH",
                    "decided_by": "David Kim",
                    "rationale": "Mitigates credential interception on public/client-side integrations with Google & Outlook.",
                },
            },
            {
                "id": uuid4(),
                "name": "Migrate from Single-Host EC2 to Multi-AZ RDS",
                "canonical": "decision_ec2_to_rds_migration",
                "type": "DECISION",
                "metadata": {
                    "status": "CONFIRMED",
                    "impact": "HIGH",
                    "decided_by": "Marcus Vance",
                    "rationale": "Eliminates single point of failure and provides 99.99% uptime guarantee.",
                },
            },
            {
                "id": uuid4(),
                "name": "Adopt HNSW Vector Indexing for Cross-Meeting RAG",
                "canonical": "decision_hnsw_indexing_adoption",
                "type": "DECISION",
                "metadata": {
                    "status": "CONFIRMED",
                    "impact": "HIGH",
                    "decided_by": "Elena Rostova",
                    "rationale": "Delivers sub-15ms vector retrieval latency with 98.4% top-k recall accuracy.",
                },
            },
            {
                "id": uuid4(),
                "name": "Adopt Next.js 15 App Router & Server Components",
                "canonical": "decision_nextjs_app_router",
                "type": "DECISION",
                "metadata": {
                    "status": "CONFIRMED",
                    "impact": "MEDIUM",
                    "decided_by": "Harshita Patel",
                    "rationale": "Fast initial page loads, streaming SSR, and modular dashboard routing.",
                },
            },
            {
                "id": uuid4(),
                "name": "Integrate Resend REST API for Automated Meeting Briefings",
                "canonical": "decision_resend_api_integration",
                "type": "DECISION",
                "metadata": {
                    "status": "CONFIRMED",
                    "impact": "MEDIUM",
                    "decided_by": "Sujal Nage",
                    "rationale": "Superior deliverability, native React email templates, and real-time webhook tracking.",
                },
            },
            {
                "id": uuid4(),
                "name": "Enforce Zero-Trust Transcript Data Sanitization",
                "canonical": "decision_zero_trust_sanitization",
                "type": "DECISION",
                "metadata": {
                    "status": "CONFIRMED",
                    "impact": "HIGH",
                    "decided_by": "David Kim",
                    "rationale": "Redacts PII, access tokens, and sensitive financial figures before vector indexing.",
                },
            },
            {
                "id": uuid4(),
                "name": "Establish Weekly Cross-Functional Architecture Board",
                "canonical": "decision_architecture_board_cadence",
                "type": "DECISION",
                "metadata": {
                    "status": "CONFIRMED",
                    "impact": "MEDIUM",
                    "decided_by": "Sarah Chen",
                    "rationale": "Synchronizes schema modifications and API contract evolutions across squads.",
                },
            },
        ]

        actions_data = [
            {
                "id": uuid4(),
                "name": "Provision PostgreSQL 16 on AWS RDS with automated failover",
                "canonical": "action_provision_rds_postgres",
                "type": "ACTION",
                "metadata": {
                    "assignee": "Marcus Vance",
                    "priority": "CRITICAL",
                    "status": "IN_PROGRESS",
                    "due_date": "2026-10-05",
                },
            },
            {
                "id": uuid4(),
                "name": "Implement PKCE auth flow and rotation secrets",
                "canonical": "action_implement_pkce_flow",
                "type": "ACTION",
                "metadata": {
                    "assignee": "David Kim",
                    "priority": "CRITICAL",
                    "status": "IN_PROGRESS",
                    "due_date": "2026-10-04",
                },
            },
            {
                "id": uuid4(),
                "name": "Benchmark HNSW recall vs IVFFlat on 1M embeddings",
                "canonical": "action_benchmark_hnsw_recall",
                "type": "ACTION",
                "metadata": {
                    "assignee": "Elena Rostova",
                    "priority": "HIGH",
                    "status": "COMPLETED",
                    "due_date": "2026-09-30",
                },
            },
            {
                "id": uuid4(),
                "name": "Complete Knowra Design System component library migration",
                "canonical": "action_migrate_design_system",
                "type": "ACTION",
                "metadata": {
                    "assignee": "Harshita Patel",
                    "priority": "MEDIUM",
                    "status": "OPEN",
                    "due_date": "2026-10-08",
                },
            },
            {
                "id": uuid4(),
                "name": "Configure Resend webhook signature validation",
                "canonical": "action_resend_webhook_signatures",
                "type": "ACTION",
                "metadata": {
                    "assignee": "Sujal Nage",
                    "priority": "HIGH",
                    "status": "COMPLETED",
                    "due_date": "2026-09-29",
                },
            },
            {
                "id": uuid4(),
                "name": "Conduct enterprise security audit on transcript endpoints",
                "canonical": "action_security_audit_transcripts",
                "type": "ACTION",
                "metadata": {
                    "assignee": "David Kim",
                    "priority": "HIGH",
                    "status": "OPEN",
                    "due_date": "2026-10-12",
                },
            },
            {
                "id": uuid4(),
                "name": "Deploy Canary Release Pipeline for AI Summarization",
                "canonical": "action_canary_pipeline_deploy",
                "type": "ACTION",
                "metadata": {
                    "assignee": "Sarah Chen",
                    "priority": "HIGH",
                    "status": "OPEN",
                    "due_date": "2026-10-06",
                },
            },
            {
                "id": uuid4(),
                "name": "Refactor Meeting Intelligence Cache to Redis Cluster",
                "canonical": "action_redis_cluster_cache",
                "type": "ACTION",
                "metadata": {
                    "assignee": "Marcus Vance",
                    "priority": "MEDIUM",
                    "status": "OPEN",
                    "due_date": "2026-10-10",
                },
            },
        ]

        topics_data = [
            {
                "id": uuid4(),
                "name": "AWS RDS PostgreSQL",
                "canonical": "topic_aws_rds_postgres",
                "type": "TOPIC",
                "metadata": {"domain": "Cloud Persistence", "tier": "Core Infrastructure"},
            },
            {
                "id": uuid4(),
                "name": "OAuth 2.0 & PKCE",
                "canonical": "topic_oauth_pkce",
                "type": "TOPIC",
                "metadata": {"domain": "Identity & Security", "tier": "Access Control"},
            },
            {
                "id": uuid4(),
                "name": "HNSW Vector Indexing",
                "canonical": "topic_hnsw_vector_indexing",
                "type": "TOPIC",
                "metadata": {"domain": "AI Retrieval", "tier": "Cognitive Search"},
            },
            {
                "id": uuid4(),
                "name": "Resend REST API",
                "canonical": "topic_resend_rest_api",
                "type": "TOPIC",
                "metadata": {"domain": "Communications", "tier": "Notifications"},
            },
            {
                "id": uuid4(),
                "name": "Next.js App Router",
                "canonical": "topic_nextjs_app_router",
                "type": "TOPIC",
                "metadata": {"domain": "Frontend Architecture", "tier": "User Interface"},
            },
            {
                "id": uuid4(),
                "name": "Zero-Trust Security",
                "canonical": "topic_zero_trust_security",
                "type": "TOPIC",
                "metadata": {"domain": "Compliance & InfoSec", "tier": "Governance"},
            },
            {
                "id": uuid4(),
                "name": "Speech Diarization Pipeline",
                "canonical": "topic_speech_diarization",
                "type": "TOPIC",
                "metadata": {"domain": "Audio Intelligence", "tier": "Processing"},
            },
            {
                "id": uuid4(),
                "name": "Multi-Hop Graph RAG",
                "canonical": "topic_multihop_graph_rag",
                "type": "TOPIC",
                "metadata": {"domain": "Knowledge Intelligence", "tier": "Synthesis"},
            },
        ]

        all_specs = meetings_data + persons_data + decisions_data + actions_data + topics_data
        entity_lookup = {}

        # 3. Insert or Update Entities
        for spec in all_specs:
            existing = (
                db.query(KnowledgeEntity)
                .filter(
                    KnowledgeEntity.tenant_id == tenant_id,
                    KnowledgeEntity.canonical_name == spec["canonical"],
                )
                .first()
            )
            if existing:
                existing.name = spec["name"]
                existing.entity_type = spec["type"]
                existing.metadata_json = spec["metadata"]
                entity_lookup[spec["canonical"]] = existing
            else:
                new_ent = KnowledgeEntity(
                    id=spec["id"],
                    tenant_id=tenant_id,
                    name=spec["name"],
                    canonical_name=spec["canonical"],
                    entity_type=spec["type"],
                    aliases=[spec["name"].split()[0]],
                    metadata_json=spec["metadata"],
                )
                db.add(new_ent)
                entity_lookup[spec["canonical"]] = new_ent

        db.flush()
        print(f"[+] Loaded {len(entity_lookup)} canonical demo entities.")

        # 4. Define Directed Graph Relationships
        relations_spec = [
            # Meeting -> Decisions
            ("meeting_q3_arch_review", "decision_aws_rds_standard", "RECORDED_DECISION", 1.0),
            ("meeting_q3_arch_review", "decision_ec2_to_rds_migration", "RECORDED_DECISION", 1.0),
            ("meeting_security_auth_review", "decision_oauth_pkce_vaults", "RECORDED_DECISION", 1.0),
            ("meeting_security_auth_review", "decision_zero_trust_sanitization", "RECORDED_DECISION", 1.0),
            ("meeting_vector_db_workshop", "decision_hnsw_indexing_adoption", "RECORDED_DECISION", 1.0),
            ("meeting_frontend_design_sync", "decision_nextjs_app_router", "RECORDED_DECISION", 1.0),
            ("meeting_executive_ai_roadmap", "decision_resend_api_integration", "RECORDED_DECISION", 1.0),
            ("meeting_sprint_44_sync", "decision_architecture_board_cadence", "RECORDED_DECISION", 1.0),

            # Decisions -> People (Decided By)
            ("decision_aws_rds_standard", "person_sujal_nage", "DECIDED_BY", 0.99),
            ("decision_oauth_pkce_vaults", "person_david_kim", "DECIDED_BY", 0.99),
            ("decision_ec2_to_rds_migration", "person_marcus_vance", "DECIDED_BY", 0.98),
            ("decision_hnsw_indexing_adoption", "person_elena_rostova", "DECIDED_BY", 0.99),
            ("decision_nextjs_app_router", "person_harshita_patel", "DECIDED_BY", 0.97),
            ("decision_resend_api_integration", "person_sujal_nage", "DECIDED_BY", 0.98),
            ("decision_zero_trust_sanitization", "person_david_kim", "DECIDED_BY", 0.99),
            ("decision_architecture_board_cadence", "person_sarah_chen", "DECIDED_BY", 0.97),

            # Meetings -> Actions (Generated Action)
            ("meeting_q3_arch_review", "action_provision_rds_postgres", "GENERATED_ACTION", 1.0),
            ("meeting_q3_arch_review", "action_redis_cluster_cache", "GENERATED_ACTION", 1.0),
            ("meeting_security_auth_review", "action_implement_pkce_flow", "GENERATED_ACTION", 1.0),
            ("meeting_security_auth_review", "action_security_audit_transcripts", "GENERATED_ACTION", 1.0),
            ("meeting_vector_db_workshop", "action_benchmark_hnsw_recall", "GENERATED_ACTION", 1.0),
            ("meeting_frontend_design_sync", "action_migrate_design_system", "GENERATED_ACTION", 1.0),
            ("meeting_executive_ai_roadmap", "action_resend_webhook_signatures", "GENERATED_ACTION", 1.0),
            ("meeting_sprint_44_sync", "action_canary_pipeline_deploy", "GENERATED_ACTION", 1.0),

            # Actions -> People (Assigned To)
            ("action_provision_rds_postgres", "person_marcus_vance", "ASSIGNED_TO", 0.99),
            ("action_implement_pkce_flow", "person_david_kim", "ASSIGNED_TO", 0.99),
            ("action_benchmark_hnsw_recall", "person_elena_rostova", "ASSIGNED_TO", 0.99),
            ("action_migrate_design_system", "person_harshita_patel", "ASSIGNED_TO", 0.98),
            ("action_resend_webhook_signatures", "person_sujal_nage", "ASSIGNED_TO", 0.99),
            ("action_security_audit_transcripts", "person_david_kim", "ASSIGNED_TO", 0.98),
            ("action_canary_pipeline_deploy", "person_sarah_chen", "ASSIGNED_TO", 0.98),
            ("action_redis_cluster_cache", "person_marcus_vance", "ASSIGNED_TO", 0.97),

            # People -> Meetings (Attended / Led)
            ("person_sujal_nage", "meeting_q3_arch_review", "ORGANIZED", 1.0),
            ("person_marcus_vance", "meeting_q3_arch_review", "ATTENDED", 1.0),
            ("person_sarah_chen", "meeting_sprint_44_sync", "ORGANIZED", 1.0),
            ("person_harshita_patel", "meeting_sprint_44_sync", "ATTENDED", 1.0),
            ("person_david_kim", "meeting_security_auth_review", "ORGANIZED", 1.0),
            ("person_sujal_nage", "meeting_security_auth_review", "ATTENDED", 1.0),
            ("person_elena_rostova", "meeting_vector_db_workshop", "ORGANIZED", 1.0),
            ("person_sujal_nage", "meeting_vector_db_workshop", "ATTENDED", 1.0),
            ("person_harshita_patel", "meeting_frontend_design_sync", "ORGANIZED", 1.0),
            ("person_sarah_chen", "meeting_frontend_design_sync", "ATTENDED", 1.0),
            ("person_sujal_nage", "meeting_executive_ai_roadmap", "ORGANIZED", 1.0),
            ("person_sarah_chen", "meeting_executive_ai_roadmap", "ATTENDED", 1.0),

            # Meetings -> Topics (Discussed Topic)
            ("meeting_q3_arch_review", "topic_aws_rds_postgres", "DISCUSSED_TOPIC", 0.95),
            ("meeting_security_auth_review", "topic_oauth_pkce", "DISCUSSED_TOPIC", 0.98),
            ("meeting_security_auth_review", "topic_zero_trust_security", "DISCUSSED_TOPIC", 0.97),
            ("meeting_vector_db_workshop", "topic_hnsw_vector_indexing", "DISCUSSED_TOPIC", 0.99),
            ("meeting_vector_db_workshop", "topic_multihop_graph_rag", "DISCUSSED_TOPIC", 0.94),
            ("meeting_frontend_design_sync", "topic_nextjs_app_router", "DISCUSSED_TOPIC", 0.96),
            ("meeting_executive_ai_roadmap", "topic_resend_rest_api", "DISCUSSED_TOPIC", 0.92),

            # Decisions -> Topics (Affects Domain)
            ("decision_aws_rds_standard", "topic_aws_rds_postgres", "AFFECTS", 0.98),
            ("decision_ec2_to_rds_migration", "topic_aws_rds_postgres", "AFFECTS", 0.96),
            ("decision_oauth_pkce_vaults", "topic_oauth_pkce", "AFFECTS", 0.99),
            ("decision_zero_trust_sanitization", "topic_zero_trust_security", "AFFECTS", 0.98),
            ("decision_hnsw_indexing_adoption", "topic_hnsw_vector_indexing", "AFFECTS", 0.99),
            ("decision_nextjs_app_router", "topic_nextjs_app_router", "AFFECTS", 0.95),
            ("decision_resend_api_integration", "topic_resend_rest_api", "AFFECTS", 0.94),

            # Actions -> Topics (Relates To)
            ("action_provision_rds_postgres", "topic_aws_rds_postgres", "RELATES_TO", 0.98),
            ("action_implement_pkce_flow", "topic_oauth_pkce", "RELATES_TO", 0.99),
            ("action_benchmark_hnsw_recall", "topic_hnsw_vector_indexing", "RELATES_TO", 0.99),
            ("action_migrate_design_system", "topic_nextjs_app_router", "RELATES_TO", 0.95),
            ("action_resend_webhook_signatures", "topic_resend_rest_api", "RELATES_TO", 0.97),
            ("action_security_audit_transcripts", "topic_zero_trust_security", "RELATES_TO", 0.98),

            # Decision -> Decision (Lineage / Supersedes)
            ("decision_aws_rds_standard", "decision_ec2_to_rds_migration", "SUPERSEDES", 0.95),
        ]

        inserted_rels = 0
        for src_can, tgt_can, rel_type, conf in relations_spec:
            src_ent = entity_lookup.get(src_can)
            tgt_ent = entity_lookup.get(tgt_can)
            if not src_ent or not tgt_ent:
                continue

            existing_rel = (
                db.query(KnowledgeRelationship)
                .filter(
                    KnowledgeRelationship.tenant_id == tenant_id,
                    KnowledgeRelationship.source_entity_id == src_ent.id,
                    KnowledgeRelationship.target_entity_id == tgt_ent.id,
                    KnowledgeRelationship.relationship_type == rel_type,
                )
                .first()
            )
            if not existing_rel:
                rel = KnowledgeRelationship(
                    id=uuid4(),
                    tenant_id=tenant_id,
                    source_entity_id=src_ent.id,
                    target_entity_id=tgt_ent.id,
                    relationship_type=rel_type,
                    confidence=conf,
                    metadata_json={},
                )
                db.add(rel)
                inserted_rels += 1

        db.commit()
        print(f"[+] Successfully seeded {inserted_rels} new directed relationships.")
        
        total_ents = db.query(KnowledgeEntity).count()
        total_rels = db.query(KnowledgeRelationship).count()
        print(f"[*] Total Database Knowledge State: {total_ents} entities, {total_rels} relationships.")

    except Exception as e:
        db.rollback()
        print(f"[-] Error seeding knowledge graph: {e}", file=sys.stderr)
        raise e
    finally:
        db.close()


if __name__ == "__main__":
    seed_knowledge_graph()
