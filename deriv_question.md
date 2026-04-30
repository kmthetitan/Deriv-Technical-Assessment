## BUILD

Build a replayable pipeline that ingests a PostgreSQL database schema and a set of slow-running SQL queries, uses staged LLM reasoning to diagnose likely performance issues, generates targeted query rewrites and index recommendations, deduplicates index plans deterministically, and produces a production-aware schema improvement plan.

This is a static-analysis challenge. The pipeline must not connect to a live database.

The evaluator will run your pipeline from a clean checkout, may replace the schema and query files with equivalent fixtures, and will verify that the pipeline reads from disk, separates LLM stages, preserves intermediate artifacts, and produces reproducible outputs.

---

## INPUT FILES

Your pipeline must read the following files from disk:

- `schema.sql`
- `slow_queries.sql`

The sample files below are provided for local testing. The evaluator may replace them with different PostgreSQL schema and query files. Your implementation must not depend on the exact query text, table names, ordering, or comments from the public fixture.

---

## SAMPLE `schema.sql`

```sql
CREATE TABLE users (
    id BIGSERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    country_code CHAR(2),
    kyc_status VARCHAR(20) DEFAULT 'pending',
    referral_source VARCHAR(50),
    last_login TIMESTAMPTZ
);

CREATE TABLE accounts (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id),
    account_type VARCHAR(20) NOT NULL,
    currency CHAR(3) NOT NULL,
    balance NUMERIC(18,8) DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE
);

CREATE TABLE positions (
    id BIGSERIAL PRIMARY KEY,
    account_id BIGINT REFERENCES accounts(id),
    symbol VARCHAR(20) NOT NULL,
    direction VARCHAR(5) NOT NULL,
    stake NUMERIC(18,8),
    entry_price NUMERIC(18,8),
    current_price NUMERIC(18,8),
    pnl NUMERIC(18,8),
    opened_at TIMESTAMPTZ DEFAULT NOW(),
    closed_at TIMESTAMPTZ,
    status VARCHAR(20) DEFAULT 'open'
);

CREATE TABLE transactions (
    id BIGSERIAL PRIMARY KEY,
    account_id BIGINT REFERENCES accounts(id),
    transaction_type VARCHAR(30) NOT NULL,
    amount NUMERIC(18,8),
    currency CHAR(3),
    status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    processed_at TIMESTAMPTZ,
    reference VARCHAR(100)
);

CREATE TABLE audit_log (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id),
    action VARCHAR(100),
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    ip_address INET
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_accounts_user_id ON accounts(user_id);
CREATE INDEX idx_positions_account_id ON positions(account_id);
```

---

## SAMPLE `slow_queries.sql`

```sql
-- Q1: Daily active users report. Runs every hour, takes 45s.
SELECT DATE(last_login) as login_date, country_code, COUNT(*) as dau
FROM users
WHERE last_login >= NOW() - INTERVAL '30 days'
GROUP BY DATE(last_login), country_code
ORDER BY login_date DESC, dau DESC;

-- Q2: Open positions PnL dashboard. Runs every 30s, takes 12s.
SELECT u.email, a.currency, SUM(p.pnl) as total_pnl, COUNT(p.id) as position_count
FROM positions p
JOIN accounts a ON p.account_id = a.id
JOIN users u ON a.user_id = u.id
WHERE p.status = 'open'
GROUP BY u.email, a.currency
ORDER BY total_pnl DESC;

-- Q3: Withdrawal reconciliation. Runs nightly, takes 8 minutes.
SELECT t.reference, t.amount, t.currency, t.created_at, t.processed_at,
       u.email, u.country_code,
       EXTRACT(EPOCH FROM (t.processed_at - t.created_at))/3600 as processing_hours
FROM transactions t
JOIN accounts a ON t.account_id = a.id
JOIN users u ON a.user_id = u.id
WHERE t.transaction_type = 'withdrawal'
AND t.status = 'completed'
AND t.created_at >= NOW() - INTERVAL '90 days'
ORDER BY t.created_at DESC;

-- Q4: KYC compliance report. Runs weekly, takes 3 minutes.
SELECT u.country_code,
       COUNT(*) FILTER (WHERE u.kyc_status = 'verified') as verified,
       COUNT(*) FILTER (WHERE u.kyc_status = 'pending') as pending,
       COUNT(*) FILTER (WHERE u.kyc_status = 'rejected') as rejected,
       AVG(EXTRACT(EPOCH FROM (u.last_login - u.created_at))/86400) as avg_days_to_first_login
FROM users u
WHERE u.created_at >= '2024-01-01'
GROUP BY u.country_code
ORDER BY verified DESC;

-- Q5: Audit trail search. Ad hoc, users report it times out.
SELECT al.created_at, al.action, al.ip_address, al.metadata,
       u.email, u.country_code
FROM audit_log al
JOIN users u ON al.user_id = u.id
WHERE al.metadata @> '{"account_id": 12345}'
AND al.created_at >= NOW() - INTERVAL '7 days'
ORDER BY al.created_at DESC;
```

---

## PIPELINE STAGES

Your implementation must enforce these stages in code:

```text
INIT
 -> INPUTS_LOADED
 -> SCHEMA_ANALYSED
 -> QUERIES_PARSED
 -> QUERIES_DIAGNOSED
 -> QUERIES_REWRITTEN
 -> INDEXES_DEDUPED
 -> REGRESSION_REVIEWED, if attempted
 -> SCHEMA_PLAN_GENERATED
 -> RESULTS_FINALISED
```

Final outputs must not be produced before schema analysis, per-query diagnosis, query rewrites, and deterministic index deduplication have completed.

---

## MUST COMPLETE

### 1. Schema Analysis

Make a Stage 1 LLM call using the full schema from `schema.sql`.

Identify:

- missing indexes likely to cause full table scans
- foreign keys without supporting indexes
- columns frequently likely to appear in filters or joins without indexes
- data type choices that may cause performance issues
- existing indexes that may be redundant or insufficient

Save the output to `schema_analysis.json`.

Each finding must use this structure:

```json
{
  "table": "string",
  "column": "string",
  "issue_type": "missing_index | unsupported_foreign_key | datatype_risk | redundant_index | other",
  "severity": "critical | high | medium | low",
  "recommendation": "string"
}
```

---

### 2. Query-by-Query Diagnosis

Parse `slow_queries.sql` into individual queries.

For each query, make a separate Stage 2 LLM call.

Each call must include:

- the full schema
- the single query being diagnosed
- the query comment or runtime characteristic, if available

Do not batch multiple queries into one diagnosis call.

For each query, produce:

- execution plan narrative
- likely bottleneck
- affected tables and columns
- issue classification

Allowed classifications:

```text
missing_index
inefficient_join
full_table_scan
suboptimal_aggregation
json_operator_overhead
sort_overhead
datatype_or_expression_overhead
other
```

Save all diagnoses to `query_diagnoses.json`.

---

### 3. Optimised Query Rewrites

For each query, make a separate Stage 3 LLM call.

Each call must include:

- the full schema
- the original query
- that query's Stage 2 diagnosis
- the specific bottleneck classification

Generate:

- rewritten SQL
- exact PostgreSQL `CREATE INDEX` statements needed
- explanation of how the rewrite addresses the Stage 2 bottleneck
- expected risk or limitation of the rewrite

Save all rewritten queries to `optimised_queries.sql` with inline comments.

All SQL must be syntactically valid PostgreSQL.

---

### 4. Index Conflict Resolution

Collect all index recommendations from Stage 3.

Use deterministic code before any LLM assistance to:

- normalise index definitions
- deduplicate identical recommendations
- identify overlapping indexes on the same table and column prefix
- identify potentially conflicting or redundant indexes

Produce a consolidated `index_plan.sql` containing the minimal practical set of indexes serving all diagnosed queries.

Use an LLM only for genuinely ambiguous cases after deterministic deduplication.

Record deduplication decisions in `index_deduplication.json`.

---

### 5. Schema Improvement Plan

Combine Stage 1 findings, Stage 2 diagnoses, Stage 3 rewrites, and the consolidated index plan into `schema_improvement_plan.md`.

The plan must include:

- Critical fixes, apply immediately
- High priority fixes, apply within the next sprint
- Optimisations, consider during architecture review
- Migration risk notes
- Locking or downtime considerations
- Whether indexes should be created with `CONCURRENTLY`
- Rollback notes for risky changes

---

## SHOULD ATTEMPT

### 6. Query Regression Risk Review

For each rewritten query, make an additional LLM reviewer call.

The reviewer must decide whether the rewrite preserves the semantics of the original query.

Output:

```json
{
  "query_id": "string",
  "semantically_equivalent": true,
  "difference_if_any": "string",
  "severity": "none | low | medium | high"
}
```

Any rewrite marked non-equivalent must be flagged before inclusion in the schema improvement plan.

---

### 7. Partitioning Recommendation

Identify tables that may benefit from partitioning based on query patterns.

For each recommendation, provide:

- table name
- partitioning key
- partitioning strategy
- example PostgreSQL syntax
- migration path from the current unpartitioned table
- operational risk

---

## STRETCH

### 8. Write Overhead Trade-Off

For write-heavy tables, ask an LLM to evaluate the write overhead of proposed indexes.

The output must identify:

- index
- table
- read benefit
- write cost
- whether the index is justified
- risk level

---

### 9. Production Runbook

Produce a production runbook for critical and high-priority changes.

The runbook must include:

- ordered rollout steps
- which changes can run online
- which changes require a maintenance window
- `CREATE INDEX CONCURRENTLY` usage where appropriate
- rollback instructions
- verification checks after deployment

---

## REQUIRED ARTIFACTS

Your repository must produce:

- `schema.sql`
- `slow_queries.sql`
- `schema_analysis.json`
- `query_diagnoses.json`
- `optimised_queries.sql`
- `index_plan.sql`
- `index_deduplication.json`
- `schema_improvement_plan.md`
- `regression_risk.json`, if attempted
- `partitioning_recommendations.md`, if attempted
- `production_runbook.md`, if attempted
- `llm_calls.jsonl`

---

## `llm_calls.jsonl` REQUIREMENTS

Log one JSON object per LLM call.

Each record must include:

```json
{
  "stage": "string",
  "query_id": "string | null",
  "timestamp": "ISO-8601 timestamp",
  "provider": "string",
  "model": "string",
  "prompt_hash": "string",
  "input_artifacts": ["path"],
  "output_artifact": "path"
}
```

There must be separate records for:

- schema analysis
- each query diagnosis
- each query rewrite
- each regression review, if attempted
- ambiguity resolution, if LLM assistance is used for index consolidation

---

## VALIDATION REQUIREMENTS

The repository must include a validation command, for example:

```bash
make validate
```

or:

```bash
python validate.py
```

The validation command must check that:

- required artifacts exist
- JSON files are valid
- `schema.sql` and `slow_queries.sql` were read from disk
- each query has a separate Stage 2 diagnosis record
- each query has a separate Stage 3 rewrite record
- Stage 3 rewrites reference the corresponding Stage 2 bottleneck
- index deduplication was performed before final `index_plan.sql`
- final outputs were not produced before required stages completed
- `llm_calls.jsonl` contains separate records for required stages
- generated SQL files are non-empty and contain PostgreSQL statements

---

## EXECUTION REQUIREMENTS

The evaluator will run the pipeline from a clean checkout.

Generated artifacts may be deleted before evaluation.

The evaluator may replace `schema.sql` and `slow_queries.sql` with equivalent PostgreSQL inputs.

Static precomputed outputs are not sufficient.

The solution must actually run the staged pipeline and regenerate the required artifacts.

---

## TOOLS

Any programming language may be used.

Any LLM provider or AI tooling may be used.

No live database connection is allowed.

---

## TECHNICAL CONSTRAINTS

- Do not connect to a live database.
- Read `schema.sql` and `slow_queries.sql` from disk.
- Do not hardcode the sample schema or sample queries into prompts.
- Stage 2 diagnosis must use one LLM call per query.
- Stage 3 rewrite must use one LLM call per query.
- Stage 2 and Stage 3 must not be collapsed into one call.
- Index deduplication must use deterministic code before LLM ambiguity resolution.
- SQL output must target PostgreSQL.
- Rewrites that may change query semantics must be flagged.