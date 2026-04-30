#!/usr/bin/env python3
import json
import os
from pathlib import Path
from llm_client import LLMClient
from parser import SQLParser
from stages import PipelineStages
from deduplicator import IndexDeduplicator

class PipelineOrchestrator:
    def __init__(self, base_dir: str = "."):
        self.base_dir = base_dir
        self.llm = LLMClient()
        self.stages = PipelineStages(self.llm)
        self.status = "INIT"

    def run_pipeline(self):
        """Execute the complete optimization pipeline."""
        print("[INIT] Starting pipeline...")
        self.status = "INIT"
        
        # Load inputs
        print("[INPUTS_LOADED] Loading schema and queries...")
        self.status = "INPUTS_LOADED"
        schema_path = os.path.join(self.base_dir, "schema.sql")
        queries_path = os.path.join(self.base_dir, "slow_queries.sql")
        
        schema_sql = SQLParser.parse_schema(schema_path)
        
        # Stage 1: Schema Analysis
        print("[SCHEMA_ANALYSED] Analyzing schema for performance issues...")
        self.status = "SCHEMA_ANALYSED"
        schema_analysis = self.stages.stage_1_schema_analysis(schema_sql)
        self._save_json("schema_analysis.json", schema_analysis)
        print(f"  Found {len(schema_analysis)} findings")
        
        # Stage 2: Parse Queries
        print("[QUERIES_PARSED] Parsing slow queries...")
        self.status = "QUERIES_PARSED"
        parsed_queries = self.stages.stage_2_parse_queries(queries_path)
        print(f"  Extracted {len(parsed_queries)} queries")
        
        # Stage 3: Diagnose Queries
        print("[QUERIES_DIAGNOSED] Diagnosing each query...")
        self.status = "QUERIES_DIAGNOSED"
        diagnoses = self.stages.stage_3_diagnose_queries()
        self._save_json("query_diagnoses.json", diagnoses)
        print(f"  Diagnosed {len(diagnoses)} queries")
        
        # Stage 4: Rewrite Queries
        print("[QUERIES_REWRITTEN] Rewriting queries with optimizations...")
        self.status = "QUERIES_REWRITTEN"
        rewrites = self.stages.stage_4_rewrite_queries()
        self._save_optimized_queries(rewrites)
        print(f"  Rewrote {len(rewrites)} queries")
        
        # Stage 5: Deduplicate Indexes
        print("[INDEXES_DEDUPED] Deduplicating index recommendations...")
        self.status = "INDEXES_DEDUPED"
        dedup_result = self.stages.stage_5_deduplicate_indexes()
        self._save_index_plan(dedup_result)
        self._save_json("index_deduplication.json", dedup_result['decisions'])
        print(f"  Deduplicated: {dedup_result['total_original']} -> {dedup_result['total_deduplicated']} indexes")
        
        # Stage 6: Regression Review
        print("[REGRESSION_REVIEWED] Reviewing query rewrites for semantic safety...")
        self.status = "REGRESSION_REVIEWED"
        regression_reviews = self.stages.stage_6_regression_review()
        self._save_json("regression_risk.json", regression_reviews)
        print(f"  Reviewed {len(regression_reviews)} rewrites")
        
        # Stage 7: Partitioning Recommendations
        print("[SCHEMA_PLAN_GENERATED] Generating partitioning recommendations...")
        self.status = "SCHEMA_PLAN_GENERATED"
        partitioning = self.stages.stage_7_partitioning_recommendations()
        self._save_text("partitioning_recommendations.md", partitioning)
        print("  Partitioning recommendations generated")
        
        # Final: Generate Schema Improvement Plan
        print("[RESULTS_FINALISED] Generating final schema improvement plan...")
        self.status = "RESULTS_FINALISED"
        improvement_plan = self._generate_schema_improvement_plan()
        self._save_text("schema_improvement_plan.md", improvement_plan)
        
        # Save LLM call log
        self.llm.save_llm_log("llm_calls.jsonl")
        
        print("\n" + "="*70)
        print("PIPELINE COMPLETED SUCCESSFULLY")
        print("="*70)
        print(f"Total LLM calls made: {self.llm.get_call_count()}")
        print(f"Final status: {self.status}")
        print(f"Artifacts generated:")
        print(f"  - schema_analysis.json")
        print(f"  - query_diagnoses.json")
        print(f"  - optimised_queries.sql")
        print(f"  - index_plan.sql")
        print(f"  - index_deduplication.json")
        print(f"  - regression_risk.json")
        print(f"  - partitioning_recommendations.md")
        print(f"  - schema_improvement_plan.md")
        print(f"  - llm_calls.jsonl")

    def _save_json(self, filename: str, data):
        """Save data to JSON file."""
        filepath = os.path.join(self.base_dir, filename)
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)

    def _save_text(self, filename: str, text: str):
        """Save text to file."""
        filepath = os.path.join(self.base_dir, filename)
        with open(filepath, 'w') as f:
            f.write(text)

    def _save_optimized_queries(self, rewrites: list):
        """Save optimized queries to SQL file with annotations."""
        filepath = os.path.join(self.base_dir, "optimised_queries.sql")
        with open(filepath, 'w') as f:
            for rewrite in rewrites:
                f.write(f"-- {rewrite['query_id']}: {rewrite['explanation']}\n")
                f.write(f"-- Expected benefit: {rewrite['expected_benefit']}\n")
                f.write(f"-- Risks: {rewrite['risks']}\n")
                f.write(f"{rewrite['optimized_sql']};\n\n")
                
                for idx_stmt in rewrite.get('create_index_statements', []):
                    if idx_stmt.strip():
                        f.write(f"{idx_stmt};\n")
                f.write("\n")

    def _save_index_plan(self, dedup_result: dict):
        """Save consolidated index plan to SQL file."""
        filepath = os.path.join(self.base_dir, "index_plan.sql")
        with open(filepath, 'w') as f:
            f.write("-- Consolidated Index Plan\n")
            f.write("-- Generated after deterministic deduplication\n")
            f.write(f"-- Total indexes: {dedup_result['total_deduplicated']}\n\n")
            
            for idx in dedup_result['indexes']:
                f.write(f"{idx['original_sql']};\n")

    def _generate_schema_improvement_plan(self) -> str:
        """Generate comprehensive schema improvement plan."""
        plan = "# Schema Improvement Plan\n\n"
        
        plan += "## Executive Summary\n\n"
        plan += "This plan consolidates findings from schema analysis, query diagnosis, optimization, "
        plan += "and regression testing to provide a comprehensive roadmap for database performance improvement.\n\n"
        
        # Critical Fixes
        plan += "## Critical Fixes (Apply Immediately)\n\n"
        critical = [f for f in self.stages.schema_analysis if f.get('severity') == 'critical']
        if critical:
            for finding in critical:
                plan += f"- **{finding['table']}.{finding['column']}** ({finding['issue_type']})\n"
                plan += f"  {finding['recommendation']}\n\n"
        else:
            plan += "No critical issues identified.\n\n"
        
        # High Priority
        plan += "## High Priority (Next Sprint)\n\n"
        high = [f for f in self.stages.schema_analysis if f.get('severity') == 'high']
        if high:
            for finding in high:
                plan += f"- **{finding['table']}.{finding['column']}** ({finding['issue_type']})\n"
                plan += f"  {finding['recommendation']}\n\n"
        else:
            plan += "No high priority issues identified.\n\n"
        
        # Index Recommendations
        plan += "## Index Recommendations\n\n"
        plan += "### Consolidated Index Plan\n\n"
        plan += "The following indexes address multiple query bottlenecks and have been deduplicated:\n\n"
        plan += "```sql\n"
        with open(os.path.join(self.base_dir, "index_plan.sql"), 'r') as f:
            plan += f.read()
        plan += "```\n\n"
        
        # Query Optimizations
        plan += "## Query Optimizations\n\n"
        for rewrite in self.stages.query_rewrites:
            plan += f"### {rewrite['query_id']}\n\n"
            plan += f"**Optimization**: {rewrite['explanation']}\n\n"
            plan += f"**Expected Benefit**: {rewrite['expected_benefit']}\n\n"
            plan += f"**Risks**: {rewrite['risks']}\n\n"
        
        # Regression Review
        plan += "## Regression Review Results\n\n"
        risk_rewrites = [r for r in self.stages.regression_reviews if not r.get('semantically_equivalent', True)]
        if risk_rewrites:
            plan += "⚠️ **WARNING**: The following rewrites may not be semantically equivalent:\n\n"
            for review in risk_rewrites:
                plan += f"- **{review['query_id']}** (Severity: {review['severity']})\n"
                plan += f"  {review['difference_if_any']}\n\n"
        else:
            plan += "✓ All query rewrites are semantically equivalent to originals.\n\n"
        
        # Migration Strategy
        plan += "## Migration Strategy\n\n"
        plan += "### Index Creation\n"
        plan += "- All indexes should be created with `CREATE INDEX CONCURRENTLY` to avoid locking\n"
        plan += "- Create indexes during off-peak hours (e.g., late night UTC)\n"
        plan += "- Monitor disk space during index creation\n\n"
        
        plan += "### Query Deployment\n"
        plan += "- Deploy optimized queries in a blue-green deployment pattern\n"
        plan += "- Run A/B tests before full rollout\n"
        plan += "- Monitor performance metrics during rollout\n\n"
        
        plan += "### Rollback Plan\n"
        plan += "- Keep original queries and indexes in version control\n"
        plan += "- Prepare rollback scripts for quick revert\n"
        plan += "- Maintain backups before schema changes\n\n"
        
        plan += "## Partitioning Recommendations\n\n"
        plan += "See `partitioning_recommendations.md` for detailed partitioning strategies.\n\n"
        
        plan += "## Monitoring and Verification\n\n"
        plan += "After deployment:\n"
        plan += "1. Monitor query execution times\n"
        plan += "2. Check index usage with `pg_stat_user_indexes`\n"
        plan += "3. Verify no unintended query plan changes\n"
        plan += "4. Monitor write overhead on affected tables\n\n"
        
        return plan

def main():
    """Main entry point."""
    orchestrator = PipelineOrchestrator(base_dir=os.getcwd())
    try:
        orchestrator.run_pipeline()
    except Exception as e:
        print(f"ERROR: Pipeline failed at {orchestrator.status}")
        print(f"Details: {str(e)}")
        raise

if __name__ == "__main__":
    main()
