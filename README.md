# PostgreSQL Query Optimization Pipeline

A replayable, LLM-powered static analysis tool that diagnoses PostgreSQL performance issues and generates production-ready optimization recommendations.

## Overview

This pipeline ingests a PostgreSQL database schema (`schema.sql`) and slow-running queries (`slow_queries.sql`), then uses staged LLM reasoning with Google's Gemini-3.1-Flash-Lite to:

1. **Schema Analysis**: Identify missing indexes, foreign key issues, datatype risks
2. **Query Diagnosis**: Diagnose performance bottlenecks for each query separately
3. **Query Rewriting**: Generate optimized SQL with recommended indexes
4. **Index Deduplication**: Consolidate redundant index recommendations deterministically
5. **Regression Review**: Verify query rewrites preserve semantics
6. **Partitioning Analysis**: Recommend table partitioning strategies
7. **Final Plan**: Produce comprehensive schema improvement roadmap

## Quick Start

### 1. Prerequisites

- Python 3.8+
- Google API key for Generative AI (free tier available at https://aistudio.google.com/)

### 2. Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Configure API key
# Edit .env and add your OpenRouter API key:
# OPENROUTER_API_KEY=your_api_key_here
```

### 3. Run Pipeline

```bash
# Execute the full optimization pipeline
python main.py

# Validate all artifacts
python validate.py
```

## Configuration

### .env File

Create a `.env` file in the project root:

```
GOOGLE_API_KEY=your_google_api_key_here
```

Get your free API key at: https://aistudio.google.com/app/apikey

## Input Files

Place your PostgreSQL schema and queries in the project root:

- **schema.sql**: CREATE TABLE statements with existing indexes
- **slow_queries.sql**: SELECT queries with performance characteristics in comments

Example:
```sql
-- Q1: Daily active users report. Runs every hour, takes 45s.
SELECT DATE(last_login) as login_date, country_code, COUNT(*) as dau
FROM users
WHERE last_login >= NOW() - INTERVAL '30 days'
GROUP BY DATE(last_login), country_code
ORDER BY login_date DESC, dau DESC;
```

## Output Artifacts

The pipeline generates these files:

### JSON Outputs

- **schema_analysis.json**: Finding from Stage 1 (missing indexes, datatype risks, etc.)
- **query_diagnoses.json**: Performance diagnosis for each query
- **index_deduplication.json**: Deduplication decisions and consolidation logic
- **regression_risk.json**: Semantic equivalence review of query rewrites

### SQL Outputs

- **optimised_queries.sql**: Rewritten queries with annotations
- **index_plan.sql**: Consolidated CREATE INDEX statements (deduplicated)

### Markdown Outputs

- **schema_improvement_plan.md**: Comprehensive improvement roadmap with:
  - Critical and high-priority fixes
  - Index recommendations
  - Query optimizations
  - Migration strategy
  - Rollback plan
- **partitioning_recommendations.md**: Partitioning strategies for large tables

### Audit Log

- **llm_calls.jsonl**: Complete audit log of all LLM calls with:
  - Stage, query ID, timestamp
  - Model and provider
  - Prompt hash
  - Input/output artifacts

## Pipeline Stages

### Stage 1: Schema Analysis
- **Input**: schema.sql
- **Output**: schema_analysis.json
- **LLM Calls**: 1
- **Purpose**: Identify indexes, foreign keys, datatype issues

### Stage 2: Query Parsing
- **Input**: slow_queries.sql
- **Output**: Internal query metadata
- **Purpose**: Extract individual queries with context

### Stage 3: Query Diagnosis
- **Input**: Full schema + each query (separate call per query)
- **Output**: query_diagnoses.json
- **LLM Calls**: 1 per query (5 in sample)
- **Purpose**: Diagnose bottleneck for each query

### Stage 4: Query Rewriting
- **Input**: Schema + query + its diagnosis (separate call per query)
- **Output**: optimised_queries.sql
- **LLM Calls**: 1 per query (5 in sample)
- **Purpose**: Generate optimized SQL and indexes

### Stage 5: Index Deduplication
- **Input**: All CREATE INDEX statements from Stage 4
- **Output**: index_plan.sql, index_deduplication.json
- **LLM Calls**: 0 (deterministic), 1+ only for ambiguous cases
- **Purpose**: Consolidate redundant index recommendations

### Stage 6: Regression Review
- **Input**: Original queries + rewritten queries (separate call per query)
- **Output**: regression_risk.json
- **LLM Calls**: 1 per query (5 in sample)
- **Purpose**: Verify rewrites are semantically equivalent

### Stage 7: Partitioning Recommendations
- **Input**: Schema + query patterns
- **Output**: partitioning_recommendations.md
- **LLM Calls**: 1
- **Purpose**: Recommend partitioning strategies

### Stage 8: Schema Improvement Plan
- **Input**: All previous outputs
- **Output**: schema_improvement_plan.md
- **Purpose**: Consolidated, actionable improvement plan

## Validation

Run the validator to check all artifacts:

```bash
python validate.py
```

The validator checks:
- ✓ All required artifacts exist
- ✓ JSON files are valid
- ✓ Input files (schema.sql, slow_queries.sql) exist and are readable
- ✓ SQL files contain statements
- ✓ LLM audit log has required stages
- ✓ Each query has diagnosis and rewrite

## Performance Notes

- **No database connection**: Static analysis only
- **Reproducible**: Same input produces same output (deterministic)
- **Stages enforce order**: Cannot skip or reorder stages
- **LLM cost**: ~10-15 API calls for 5 queries + analysis
- **Runtime**: ~2-5 minutes depending on query complexity

## Example Workflow

```bash
# 1. Place your schema and queries
cp my_schema.sql schema.sql
cp my_queries.sql slow_queries.sql

# 2. Set up API key in .env
export GOOGLE_API_KEY="your_key_here"

# 3. Run pipeline
python main.py

# 4. Review outputs
cat schema_improvement_plan.md
cat index_plan.sql

# 5. Validate
python validate.py

# 6. Deploy (carefully!)
# - Review regression_risk.json for non-equivalent rewrites
# - Create indexes with CONCURRENTLY flag
# - Test in staging first
```

## Technical Details

### LLM Integration

- **Provider**: Google Generative AI
- **Model**: Gemini-3.1-Flash-Lite-Preview
- **API**: Google Generative AI Python SDK

### Key Algorithms

**Index Deduplication**:
1. Parse all CREATE INDEX statements
2. Normalize table names and column orders
3. Group by (table, columns)
4. Keep one index per group (deterministic)
5. Use LLM only for ambiguous edge cases

**SQL Parsing**:
- Regex-based extraction of SELECT and CREATE INDEX
- Comment parsing for query context
- PostgreSQL syntax validation

## Limitations

- No support for live database profiling
- Rewrites assume PostgreSQL 12+
- JSONB operators analyzed but not optimized by default
- Partitioning recommendations don't include data migration scripts
- No write overhead analysis (stage 8 in requirements is optional)

## Support

For issues or questions:
1. Check validate.py output for artifact validation
2. Review llm_calls.jsonl for LLM request details
3. Ensure schema.sql and slow_queries.sql are valid PostgreSQL

## License

Open source - modify and distribute freely.
