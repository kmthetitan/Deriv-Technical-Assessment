 The question is asking you to build a replayable static-analysis pipeline for PostgreSQL performance tuning.

  In plain terms: you need to write a program that reads a database schema and a file of slow SQL queries, uses multiple staged LLM calls to analyze them, proposes query rewrites and
  indexes, deduplicates the index recommendations with deterministic code, and writes a set of output artifacts that prove the pipeline actually ran.

  The key point: this is not asking you to manually write the final answers once. It is asking you to build a pipeline that can be rerun from scratch on different input files.

  What You Are Building

  You are building a command-line tool or script that does roughly this:

  1. Read schema.sql from disk.
  2. Read slow_queries.sql from disk.
  3. Analyze the schema using one LLM call.
  4. Split slow_queries.sql into individual queries.
  5. Diagnose each query using a separate LLM call per query.
  6. Rewrite each query using another separate LLM call per query.
  7. Extract index recommendations from the rewrites.
  8. Deduplicate and consolidate indexes using deterministic code.
  9. Generate a final schema improvement plan.
  10. Log every LLM call to llm_calls.jsonl.
  11. Provide a validation command that proves the artifacts are valid and the stages happened in order.

  The evaluator may delete your generated files and replace schema.sql / slow_queries.sql, so your code must regenerate everything dynamically.

  The Most Important Requirement

  The assessment is testing whether you can build a staged, auditable LLM workflow, not just whether you can suggest good indexes.

  The pipeline must enforce this sequence:

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

  That means your code should track pipeline state and prevent final outputs from being created before the required earlier stages are done.

  Inputs

  Your program must read these files:

  schema.sql
  slow_queries.sql

  You cannot hardcode the sample schema or the sample queries. The evaluator may replace them.

  So your parser needs to work generally enough for PostgreSQL DDL and multiple SQL queries with comments.

  Required Outputs

  Your pipeline must generate these files:

  schema_analysis.json
  query_diagnoses.json
  optimised_queries.sql
  index_plan.sql
  index_deduplication.json
  schema_improvement_plan.md
  llm_calls.jsonl

  Optional, if you attempt the extra tasks:

  regression_risk.json
  partitioning_recommendations.md
  production_runbook.md

  The original input files must also exist:

  schema.sql
  slow_queries.sql

  Stage 1: Schema Analysis

  You make one LLM call using the full schema.

  The LLM should identify things like:

  - missing indexes
  - foreign keys without indexes
  - columns likely to be filtered or joined without indexes
  - risky data types
  - redundant or insufficient indexes

  The output goes to:

  schema_analysis.json

  Each finding must look like:

  {
    "table": "users",
    "column": "last_login",
    "issue_type": "missing_index",
    "severity": "high",
    "recommendation": "Create an index on users(last_login) to support date-range filtering."
  }

  Stage 2: Query Diagnosis

  You must parse slow_queries.sql into individual queries.

  Then for each query, make a separate LLM call.

  For example, if there are 5 queries, you need 5 Stage 2 calls.

  Each Stage 2 call includes:

  - full schema
  - one query only
  - the comment/runtime info if available

  The result should describe:

  - likely execution plan behavior
  - bottleneck
  - affected tables and columns
  - issue classification

  Allowed classifications include:

  missing_index
  inefficient_join
  full_table_scan
  suboptimal_aggregation
  json_operator_overhead
  sort_overhead
  datatype_or_expression_overhead
  other

  Output:

  query_diagnoses.json

  Stage 3: Query Rewrites

  For each query, make another separate LLM call.

  So if there are 5 queries, you need 5 Stage 3 rewrite calls.

  Each rewrite call must include:

  - full schema
  - original query
  - that query’s Stage 2 diagnosis
  - the specific bottleneck classification

  The output should include:

  - rewritten SQL
  - exact PostgreSQL CREATE INDEX statements
  - explanation
  - risk or limitation

  All rewritten queries are saved into:

  optimised_queries.sql

  with inline comments.

  Important: Stage 2 and Stage 3 cannot be combined. The evaluator will check that diagnosis and rewrite are separate calls.

  Stage 4: Index Conflict Resolution

  This is a major part of the task.

  Your Stage 3 calls will probably produce overlapping index recommendations. Your code must collect them and deduplicate them before creating the final index plan.

  This deduplication must be done by deterministic code first.

  That means you should normalize index definitions, compare them, and identify things like:

  CREATE INDEX idx_users_last_login ON users(last_login);

  versus:

  CREATE INDEX idx_users_last_login_country ON users(last_login, country_code);

  The second may cover the first for some query patterns, depending on ordering and usage.

  Your code should produce:

  index_plan.sql
  index_deduplication.json

  index_plan.sql should contain the minimal practical set of indexes.

  index_deduplication.json should explain what was kept, removed, merged, or flagged.

  You may use an LLM for ambiguous cases, but only after deterministic deduplication.

  Stage 5: Schema Improvement Plan

  This is the final human-readable report.

  It combines:

  - schema analysis
  - query diagnoses
  - query rewrites
  - index plan
  - deduplication decisions
  - production considerations

  Output:

  schema_improvement_plan.md

  It must include sections like:

  Critical fixes, apply immediately
  High priority fixes, apply within the next sprint
  Optimisations, consider during architecture review
  Migration risk notes
  Locking or downtime considerations
  Whether indexes should be created with CONCURRENTLY
  Rollback notes for risky changes

  This should read like a production DBA/engineering recommendation document, not just a list of indexes.

  Optional: Regression Risk Review

  This is a “should attempt” item, so it is not as mandatory as the core pipeline, but doing it strengthens the submission.

  For each rewritten query, make another LLM call asking whether the rewrite preserves the original semantics.

  Output:

  regression_risk.json

  Each item should look like:

  {
    "query_id": "Q1",
    "semantically_equivalent": true,
    "difference_if_any": "",
    "severity": "none"
  }

  If a rewrite changes behavior, your final plan must flag it.

  Optional: Partitioning Recommendations

  You can also generate:

  partitioning_recommendations.md

  This should identify tables that may benefit from partitioning, especially large time-series-like tables such as transactions, audit logs, or positions.

  For each recommendation, include:

  - table
  - partitioning key
  - strategy
  - example PostgreSQL syntax
  - migration path
  - operational risk

  Optional Stretch: Write Overhead Trade-Off

  This asks you to evaluate whether proposed indexes are worth the write cost.

  Indexes speed up reads but slow down inserts/updates/deletes. The output should explain that trade-off per index.

  Optional Stretch: Production Runbook

  This asks for a deployment plan:

  production_runbook.md

  It should include:

  - rollout order
  - online changes
  - maintenance-window changes
  - CREATE INDEX CONCURRENTLY
  - rollback steps
  - verification checks

  The LLM Call Log Is Critical

  Every LLM call must be logged to:

  llm_calls.jsonl

  One JSON object per line.

  Each record must include:

  {
    "stage": "QUERY_REWRITTEN",
    "query_id": "Q1",
    "timestamp": "2026-04-30T10:00:00Z",
    "provider": "openai",
    "model": "gpt-4.1",
    "prompt_hash": "abc123",
    "input_artifacts": ["schema.sql", "query_diagnoses.json"],
    "output_artifact": "optimised_queries.sql"
  }

  The evaluator will likely inspect this file to verify that:

  - schema analysis was one call
  - each query diagnosis was separate
  - each query rewrite was separate
  - regression review calls are separate if attempted
  - any index ambiguity resolution calls are logged

  Validation Command

  You must include something like:

  python validate.py

  or:

  make validate

  The validator should check:

  - required files exist
  - JSON is valid
  - SQL files are non-empty
  - each query has a Stage 2 diagnosis
  - each query has a Stage 3 rewrite
  - Stage 3 references the Stage 2 bottleneck
  - index deduplication happened before index_plan.sql
  - final outputs were not produced too early
  - llm_calls.jsonl has the required records

  This is how the evaluator confirms your pipeline is not just static precomputed output.

  What They Are Really Evaluating

  They are probably looking for these qualities:

  1. Replayability
     Can the evaluator delete generated files and rerun your pipeline?
  2. Input generality
     Does your code work if schema.sql and slow_queries.sql are replaced?
  3. Stage separation
     Are schema analysis, diagnosis, rewrite, deduplication, and final reporting distinct steps?
  4. Per-query LLM calls
     Did you avoid batching all queries into one LLM call?
  5. Deterministic index processing
     Did your code deduplicate indexes itself instead of asking the LLM to do everything?
  6. Artifact quality
     Are the JSON, SQL, Markdown, and JSONL files structured and useful?
  7. Production awareness
     Does the final plan discuss locking, downtime, CONCURRENTLY, rollback, migration risk, and write overhead?
  8. No live database
     This must be static analysis only. Do not connect to PostgreSQL.

  A Good Implementation Shape

  A strong solution would likely have files like:

  pipeline.py
  validate.py
  schema.sql
  slow_queries.sql
  outputs...

  Internally, pipeline.py might have functions such as:

  load_inputs()
  analyse_schema()
  parse_queries()
  diagnose_queries()
  rewrite_queries()
  dedupe_indexes()
  review_regressions()
  generate_schema_plan()
  write_llm_call_log()

  You would also want a simple stage tracker, maybe something like:

  pipeline_state.json

  or an in-memory ordered stage list that gets written into the artifacts.

  In Short

  You are being asked to build an automated static PostgreSQL tuning assistant.

  It must:

  - read schema and slow queries from disk
  - use staged LLM calls
  - keep intermediate artifacts
  - rewrite queries
  - recommend indexes
  - deduplicate indexes deterministically
  - produce a production-ready improvement plan
  - log every LLM call
  - validate that the whole pipeline ran correctly

  The key is not only the quality of the SQL recommendations. The bigger challenge is proving that your tool is replayable, staged, auditable, deterministic where required, and not
  hardcoded to the sample fixture.