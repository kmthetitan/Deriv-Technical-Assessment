import json
import os
from typing import List, Dict
from parser import SQLParser
from llm_client import LLMClient
from deduplicator import IndexDeduplicator

class PipelineStages:
    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client
        self.schema = ""
        self.queries = []
        self.schema_analysis = []
        self.query_diagnoses = []
        self.query_rewrites = []
        self.regression_reviews = []

    def stage_1_schema_analysis(self, schema_sql: str) -> List[Dict]:
        """Stage 1: Analyze schema for performance issues."""
        self.schema = schema_sql
        
        prompt = f"""You are a PostgreSQL performance expert. Analyze this database schema and identify performance issues.

SCHEMA:
{schema_sql}

For each finding, provide:
1. Table name
2. Column name (if applicable)
3. Issue type: missing_index | unsupported_foreign_key | datatype_risk | redundant_index | other
4. Severity: critical | high | medium | low
5. Detailed recommendation

Format your response as a JSON array with objects matching this structure:
{{
  "table": "string",
  "column": "string",
  "issue_type": "string",
  "severity": "string",
  "recommendation": "string"
}}

Provide ONLY the JSON array, no other text."""

        result = self.llm.call_llm(
            prompt,
            stage="SCHEMA_ANALYSED",
            input_artifacts=["schema.sql"],
            output_artifact="schema_analysis.json"
        )
        
        try:
            # Extract JSON from response
            json_match = result.find('[')
            if json_match != -1:
                json_str = result[json_match:]
                json_match_end = json_str.rfind(']')
                if json_match_end != -1:
                    json_str = json_str[:json_match_end+1]
                    self.schema_analysis = json.loads(json_str)
        except json.JSONDecodeError:
            # Fallback: try to extract findings from text
            self.schema_analysis = self._extract_findings_from_text(result)
        
        return self.schema_analysis

    def stage_2_parse_queries(self, queries_sql: str) -> List[Dict]:
        """Stage 2: Parse individual queries from slow_queries.sql."""
        self.queries = SQLParser.parse_slow_queries(queries_sql)
        return self.queries

    def stage_3_diagnose_queries(self) -> List[Dict]:
        """Stage 3: Diagnose each query separately."""
        diagnoses = []
        
        for query in self.queries:
            prompt = f"""You are a PostgreSQL query optimization expert. Analyze this slow query and diagnose performance issues.

SCHEMA:
{self.schema}

SLOW QUERY ({query['query_id']}):
{query['sql']}

CONTEXT: {query['comment']}

Analyze and provide:
1. Execution plan narrative
2. Likely bottleneck
3. Affected tables and columns
4. Issue classification (one of: missing_index, inefficient_join, full_table_scan, suboptimal_aggregation, json_operator_overhead, sort_overhead, datatype_or_expression_overhead, other)

Format your response as JSON:
{{
  "query_id": "string",
  "execution_plan_narrative": "string",
  "bottleneck": "string",
  "affected_tables": ["string"],
  "affected_columns": ["string"],
  "issue_classification": "string"
}}

Provide ONLY the JSON object, no other text."""

            result = self.llm.call_llm(
                prompt,
                stage="QUERIES_DIAGNOSED",
                query_id=query['query_id'],
                input_artifacts=["schema.sql", "slow_queries.sql"],
                output_artifact="query_diagnoses.json"
            )
            
            try:
                json_match = result.find('{')
                if json_match != -1:
                    json_str = result[json_match:]
                    json_match_end = json_str.rfind('}')
                    if json_match_end != -1:
                        json_str = json_str[:json_match_end+1]
                        diagnosis = json.loads(json_str)
                        diagnoses.append(diagnosis)
            except json.JSONDecodeError:
                diagnoses.append({
                    "query_id": query['query_id'],
                    "execution_plan_narrative": "Analysis failed",
                    "bottleneck": "unknown",
                    "affected_tables": [],
                    "affected_columns": [],
                    "issue_classification": "other"
                })
        
        self.query_diagnoses = diagnoses
        return diagnoses

    def stage_4_rewrite_queries(self) -> List[Dict]:
        """Stage 4: Rewrite each query with optimizations."""
        rewrites = []
        
        for query in self.queries:
            diagnosis = next((d for d in self.query_diagnoses if d['query_id'] == query['query_id']), None)
            if not diagnosis:
                continue
            
            prompt = f"""You are a PostgreSQL optimization expert. Rewrite this query for optimal performance.

SCHEMA:
{self.schema}

ORIGINAL QUERY ({query['query_id']}):
{query['sql']}

DIAGNOSIS:
- Bottleneck: {diagnosis['bottleneck']}
- Issue: {diagnosis['issue_classification']}

Provide:
1. Optimized SQL (valid PostgreSQL)
2. Required CREATE INDEX statements (if any)
3. Explanation of optimization
4. Expected performance benefit and any risks

Format your response as JSON:
{{
  "query_id": "string",
  "optimized_sql": "string",
  "create_index_statements": ["string"],
  "explanation": "string",
  "expected_benefit": "string",
  "risks": "string"
}}

Provide ONLY the JSON object, no other text."""

            result = self.llm.call_llm(
                prompt,
                stage="QUERIES_REWRITTEN",
                query_id=query['query_id'],
                input_artifacts=["schema.sql", "slow_queries.sql", "query_diagnoses.json"],
                output_artifact="optimised_queries.sql"
            )
            
            try:
                json_match = result.find('{')
                if json_match != -1:
                    json_str = result[json_match:]
                    json_match_end = json_str.rfind('}')
                    if json_match_end != -1:
                        json_str = json_str[:json_match_end+1]
                        rewrite = json.loads(json_str)
                        rewrites.append(rewrite)
            except json.JSONDecodeError:
                rewrites.append({
                    "query_id": query['query_id'],
                    "optimized_sql": query['sql'],
                    "create_index_statements": [],
                    "explanation": "Rewrite failed",
                    "expected_benefit": "unknown",
                    "risks": "unknown"
                })
        
        self.query_rewrites = rewrites
        return rewrites

    def stage_5_deduplicate_indexes(self) -> Dict:
        """Stage 5: Deduplicate index recommendations."""
        all_indexes = []
        
        for rewrite in self.query_rewrites:
            for idx_stmt in rewrite.get('create_index_statements', []):
                if idx_stmt.strip():
                    all_indexes.append(idx_stmt)
        
        deduplicator = IndexDeduplicator()
        result = deduplicator.deduplicate_indexes(all_indexes)
        
        return result

    def stage_6_regression_review(self) -> List[Dict]:
        """Stage 6: Review query rewrites for semantic equivalence."""
        reviews = []
        
        for query in self.queries:
            rewrite = next((r for r in self.query_rewrites if r['query_id'] == query['query_id']), None)
            if not rewrite:
                continue
            
            prompt = f"""You are a PostgreSQL semantic expert. Review if this rewritten query is semantically equivalent to the original.

ORIGINAL QUERY:
{query['sql']}

REWRITTEN QUERY:
{rewrite['optimized_sql']}

Determine:
1. Is the rewritten query semantically equivalent to the original?
2. If not, what is the difference?
3. Severity of difference (none | low | medium | high)

Format your response as JSON:
{{
  "query_id": "string",
  "semantically_equivalent": true/false,
  "difference_if_any": "string",
  "severity": "string"
}}

Provide ONLY the JSON object, no other text."""

            result = self.llm.call_llm(
                prompt,
                stage="REGRESSION_REVIEWED",
                query_id=query['query_id'],
                input_artifacts=["slow_queries.sql", "optimised_queries.sql"],
                output_artifact="regression_risk.json"
            )
            
            try:
                json_match = result.find('{')
                if json_match != -1:
                    json_str = result[json_match:]
                    json_match_end = json_str.rfind('}')
                    if json_match_end != -1:
                        json_str = json_str[:json_match_end+1]
                        review = json.loads(json_str)
                        reviews.append(review)
            except json.JSONDecodeError:
                reviews.append({
                    "query_id": query['query_id'],
                    "semantically_equivalent": True,
                    "difference_if_any": "",
                    "severity": "none"
                })
        
        self.regression_reviews = reviews
        return reviews

    def stage_7_partitioning_recommendations(self) -> str:
        """Stage 7: Provide partitioning recommendations."""
        query_list = "\n\n".join([f"{q['query_id']}: {q['sql']}" for q in self.queries])
        
        prompt = f"""You are a PostgreSQL partitioning expert. Analyze these queries and recommend partitioning strategies.

SCHEMA:
{self.schema}

QUERIES:
{query_list}

For each table that could benefit from partitioning, provide:
1. Table name
2. Partitioning key (column)
3. Partitioning strategy (RANGE, LIST, HASH)
4. Example PostgreSQL syntax
5. Migration path from current unpartitioned table
6. Operational risks and benefits

Format as a detailed markdown document with sections for each recommendation."""

        result = self.llm.call_llm(
            prompt,
            stage="SCHEMA_PLAN_GENERATED",
            input_artifacts=["schema.sql", "slow_queries.sql", "query_diagnoses.json"],
            output_artifact="partitioning_recommendations.md"
        )
        
        return result

    @staticmethod
    def _extract_findings_from_text(text: str) -> List[Dict]:
        """Fallback: extract findings from unstructured text."""
        return []
