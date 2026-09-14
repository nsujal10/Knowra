# Enterprise Search Architecture & Evaluation Guide

## Executive Summary
Knowra employs a defense-in-depth, hybrid retrieval architecture combining **Dense Semantic Vector Search** (`pgvector`), **PostgreSQL Full-Text Search** (FTS `tsvector`/`tsquery`), **Reciprocal Rank Fusion** (RRF), and an optional **Cross-Encoder Reranker**. This guide details the formal benchmarking methodology, relevance metrics, multi-tenant isolation, and zero-downtime re-indexing lifecycle for enterprise-grade vector deployments.

---

## 1. Architectural Principles

### 1.1 Multi-Tenant SQL Isolation Gate
Enterprise security mandates that multi-tenant isolation occurs at the SQL predicate level prior to vector similarity distance ranking.
```sql
SELECT c.id, c.content, (e.embedding <=> :query_vector) AS cosine_distance
FROM knowledge_chunks c
JOIN knowledge_embeddings e ON e.chunk_id = c.id
WHERE c.tenant_id = :tenant_id   -- Mandatory Pre-Filter: NEVER evaluate similarity globally
  AND e.model_name = :model_name
ORDER BY cosine_distance ASC
LIMIT :limit;
```
By enforcing `WHERE c.tenant_id = :tenant_id` before ordering by cosine distance (`<=>`), the database engine prunes vector space partitions belonging to other organizations, completely preventing vector side-channel leaks.

### 1.2 Deterministic Idempotency
All chunks possess a canonical SHA-256 fingerprint:
$$\text{hash} = \text{SHA-256}(\text{normalize}(\text{chunk\_text}))$$
Embedding generation tasks in Celery query `knowledge_embeddings` by `(chunk_id, provider_name, model_name, model_version, content_hash)`. If a match is found, generation is skipped (`SKIP`), saving compute and preserving consistent vector IDs.

---

## 2. Hybrid Retrieval & RRF Formulation

### 2.1 Reciprocal Rank Fusion (RRF)
Given a set of candidate retrieval channels $C$ (e.g., $C = \{\text{vector}, \text{keyword}\}$) with assigned channel weights $w_c$ and a smoothing constant $k \in [50, 60]$, the fusion score for document $d$ is:

$$\text{RRF}(d) = \sum_{c \in C} w_c \cdot \frac{1}{k + r_c(d)}$$

where $r_c(d)$ is the 1-based ordinal rank of document $d$ within channel $c$. If $d \notin \text{top\_k}(c)$, its contribution from channel $c$ is 0.

### 2.2 Why RRF Over Score Normalization
1. **Scale Invariance**: Cosine distance $[0, 2]$ and BM25/`ts_rank` $[0, \infty)$ have incompatible dynamic ranges. Min-max normalization is sensitive to outlier scores and query variations.
2. **Robustness**: RRF focuses purely on relative ordering, mitigating score distortion when one retrieval channel returns high confidence on spurious token matches.

---

## 3. Search Evaluation & Benchmarking Strategy

### 3.1 Evaluation Metrics

#### A. Recall@K
Measures whether the ground-truth relevant chunks are present in the top-$K$ returned results.
$$\text{Recall}@K = \frac{|\text{Retrieved}_K \cap \text{Relevant}|}{|\text{Relevant}|}$$
*Target*: $\text{Recall}@5 \ge 0.85$, $\text{Recall}@10 \ge 0.95$.

#### B. Mean Reciprocal Rank (MRR)
Evaluates where the *first* relevant result appears across a set of $Q$ queries:
$$\text{MRR} = \frac{1}{|Q|} \sum_{q=1}^{|Q|} \frac{1}{\text{rank}_q}$$
where $\text{rank}_q$ is the rank position of the first relevant chunk for query $q$.
*Target*: $\text{MRR} \ge 0.75$.

#### C. Normalized Discounted Cumulative Gain (nDCG@K)
Evaluates graded relevance (e.g., 0 = irrelevant, 1 = related, 2 = exact decision/action item):
$$\text{DCG}@K = \sum_{i=1}^K \frac{2^{\text{rel}_i} - 1}{\log_2(i + 1)}, \quad \text{IDCG}@K = \sum_{i=1}^{|\text{REL}_K|} \frac{2^{\text{rel}_i^*} - 1}{\log_2(i + 1)}$$
$$\text{nDCG}@K = \frac{\text{DCG}@K}{\text{IDCG}@K}$$
*Target*: $\text{nDCG}@10 \ge 0.82$.

### 3.2 Golden Evaluation Dataset Generation
1. Extract 100 enterprise transcripts with annotated decisions and action items.
2. Formulate 3 classes of queries:
   - **Exact keyword lookup**: Acronyms, project codenames, timestamps ("Project Apollo status by Sarah").
   - **Semantic exploratory**: Conceptual queries ("What was decided regarding cloud database migration?").
   - **Cross-topic synthesis**: Hybrid queries ("Security audit risks discussed in Q3").
3. Run automated nightly regression benchmarks against staging databases.

---

## 4. Zero-Downtime Re-Indexing Workflow

When upgrading embedding models (e.g., from `all-MiniLM-L6-v2` to a 768-dim or 1536-dim model, or updating chunking parameters):

### 4.1 Dual-Model Storage Strategy
The `knowledge_embeddings` schema decouples embedding storage by `(chunk_id, provider_name, model_name, model_version)`:
1. **Active Model Serving**: Production queries continue targeting `model_name = 'current-model'` and `model_version = 'v1'`.
2. **Shadow Backfill**: Background Celery workers ingest chunks and compute vectors under `model_name = 'next-gen-model'`, `model_version = 'v2'`.
3. **Index Construction**:
   ```sql
   -- Create index concurrently without table locks
   CREATE INDEX CONCURRENTLY ix_knowledge_embeddings_v2_hnsw
   ON knowledge_embeddings USING hnsw (embedding vector_cosine_ops)
   WHERE model_name = 'next-gen-model' AND model_version = 'v2';
   ```
4. **Instant Cutover**: Update configuration parameter `DEFAULT_EMBEDDING_MODEL = 'next-gen-model'` and `DEFAULT_EMBEDDING_VERSION = 'v2'`. All new queries immediately hit the new index.
5. **Pruning**: Once verified, drop obsolete vectors:
   ```sql
   DELETE FROM knowledge_embeddings WHERE model_name = 'current-model' AND model_version = 'v1';
   ```

---

## 5. Production Tuning & Performance Guidelines

| Component | Setting / Parameter | Recommended Value | Rationale |
| :--- | :--- | :--- | :--- |
| **`pgvector` Index** | HNSW (`m=16, ef_construction=64`) | In-memory index | Lower latency (<5ms) compared to IVFFlat, zero training phase needed. |
| **Vector Search** | `ef_search` | `ef_search = 40` | High recall trade-off with negligible latency penalty. |
| **FTS Index** | GIN on `to_tsvector('english', content)` | Standard GIN | Sub-millisecond keyword retrieval on transcript chunks. |
| **RRF Constant** | $k$ | $60$ | Industry standard (TREC benchmarked) to balance vector vs keyword ranks. |
| **RRF Candidates**| `candidate_pool_size` | 50 per channel | Provides rich candidate diversity prior to cross-encoder reranking. |
| **Batch Size** | `batch_size` | 32 (or 16 on GPU memory limits)| Maximizes throughput while avoiding timeout on rate-limited providers. |
