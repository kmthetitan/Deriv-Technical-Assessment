#!/usr/bin/env python3
import json
import os
import re
from pathlib import Path

class PipelineValidator:
    def __init__(self, base_dir: str = "."):
        self.base_dir = base_dir
        self.errors = []
        self.warnings = []

    def validate_all(self) -> bool:
        """Run all validation checks."""
        print("Running pipeline validation...")
        print("=" * 70)
        
        # Check required artifacts exist
        self._check_artifacts_exist()
        
        # Check JSON files are valid
        self._check_json_files()
        
        # Check input files exist
        self._check_input_files()
        
        # Check LLM audit log
        self._check_llm_audit_log()
        
        # Check SQL files
        self._check_sql_files()
        
        # Check stage completeness
        self._check_stage_completeness()
        
        # Print results
        self._print_results()
        
        return len(self.errors) == 0

    def _check_artifacts_exist(self):
        """Check all required artifacts exist."""
        required_artifacts = [
            "schema.sql",
            "slow_queries.sql",
            "schema_analysis.json",
            "query_diagnoses.json",
            "optimised_queries.sql",
            "index_plan.sql",
            "index_deduplication.json",
            "regression_risk.json",
            "partitioning_recommendations.md",
            "schema_improvement_plan.md",
            "llm_calls.jsonl"
        ]
        
        print("\n✓ Checking required artifacts exist...")
        for artifact in required_artifacts:
            path = os.path.join(self.base_dir, artifact)
            if os.path.exists(path):
                size = os.path.getsize(path)
                print(f"  ✓ {artifact} ({size} bytes)")
            else:
                self.errors.append(f"Missing artifact: {artifact}")
                print(f"  ✗ {artifact} MISSING")

    def _check_json_files(self):
        """Validate JSON files."""
        print("\n✓ Validating JSON files...")
        json_files = [
            "schema_analysis.json",
            "query_diagnoses.json",
            "index_deduplication.json",
            "regression_risk.json"
        ]
        
        for json_file in json_files:
            path = os.path.join(self.base_dir, json_file)
            if os.path.exists(path):
                try:
                    with open(path, 'r') as f:
                        data = json.load(f)
                    print(f"  ✓ {json_file} is valid JSON")
                except json.JSONDecodeError as e:
                    self.errors.append(f"{json_file} is invalid JSON: {str(e)}")
                    print(f"  ✗ {json_file} INVALID: {str(e)}")

    def _check_input_files(self):
        """Verify input files exist and are read."""
        print("\n✓ Checking input files...")
        for input_file in ["schema.sql", "slow_queries.sql"]:
            path = os.path.join(self.base_dir, input_file)
            if os.path.exists(path):
                with open(path, 'r') as f:
                    content = f.read()
                if len(content) > 0:
                    print(f"  ✓ {input_file} exists and is readable")
                else:
                    self.errors.append(f"{input_file} is empty")
            else:
                self.errors.append(f"{input_file} not found")

    def _check_llm_audit_log(self):
        """Validate LLM call audit log."""
        print("\n✓ Validating LLM audit log...")
        path = os.path.join(self.base_dir, "llm_calls.jsonl")
        
        if not os.path.exists(path):
            self.errors.append("llm_calls.jsonl not found")
            return
        
        try:
            with open(path, 'r') as f:
                records = []
                for line in f:
                    if line.strip():
                        record = json.loads(line)
                        records.append(record)
                
            print(f"  ✓ llm_calls.jsonl contains {len(records)} records")
            
            # Check for required stages
            stages = set()
            query_ids = set()
            for record in records:
                stages.add(record.get('stage'))
                if record.get('query_id'):
                    query_ids.add(record['query_id'])
            
            print(f"  ✓ Stages covered: {sorted(stages)}")
            print(f"  ✓ Unique query IDs: {sorted(query_ids)}")
            
            # Validate required records
            required_stages = ["SCHEMA_ANALYSED", "QUERIES_DIAGNOSED", "QUERIES_REWRITTEN"]
            for stage in required_stages:
                if stage not in stages:
                    self.warnings.append(f"Stage {stage} not found in llm_calls.jsonl")
                    
        except json.JSONDecodeError as e:
            self.errors.append(f"llm_calls.jsonl has invalid JSON: {str(e)}")

    def _check_sql_files(self):
        """Validate SQL files."""
        print("\n✓ Validating SQL files...")
        sql_files = ["optimised_queries.sql", "index_plan.sql"]
        
        for sql_file in sql_files:
            path = os.path.join(self.base_dir, sql_file)
            if os.path.exists(path):
                with open(path, 'r') as f:
                    content = f.read()
                
                if len(content.strip()) == 0:
                    self.errors.append(f"{sql_file} is empty")
                    print(f"  ✗ {sql_file} is empty")
                elif "SELECT" in content.upper() or "CREATE INDEX" in content.upper():
                    print(f"  ✓ {sql_file} contains SQL statements")
                else:
                    self.warnings.append(f"{sql_file} may not contain valid SQL")
                    print(f"  ⚠ {sql_file} validation uncertain")

    def _check_stage_completeness(self):
        """Check that all queries have diagnoses and rewrites."""
        print("\n✓ Checking stage completeness...")
        
        # Count queries
        with open(os.path.join(self.base_dir, "slow_queries.sql"), 'r') as f:
            query_count = len(re.findall(r'--\s*Q\d+', f.read()))
        
        # Count diagnoses
        with open(os.path.join(self.base_dir, "query_diagnoses.json"), 'r') as f:
            diagnoses = json.load(f)
        diagnosis_count = len(diagnoses)
        
        # Count rewrites
        with open(os.path.join(self.base_dir, "index_deduplication.json"), 'r') as f:
            dedup = json.load(f)
        
        print(f"  ✓ Found {query_count} queries")
        print(f"  ✓ Generated {diagnosis_count} diagnoses")
        
        if query_count != diagnosis_count:
            self.warnings.append(f"Query count ({query_count}) != diagnosis count ({diagnosis_count})")

    def _print_results(self):
        """Print validation results."""
        print("\n" + "=" * 70)
        
        if not self.errors and not self.warnings:
            print("✓ VALIDATION PASSED - All checks successful!")
            return
        
        if self.errors:
            print(f"✗ VALIDATION FAILED - {len(self.errors)} error(s):")
            for error in self.errors:
                print(f"  - {error}")
        
        if self.warnings:
            print(f"⚠ WARNINGS - {len(self.warnings)} warning(s):")
            for warning in self.warnings:
                print(f"  - {warning}")
        
        print("=" * 70)

def main():
    """Main entry point."""
    validator = PipelineValidator(base_dir=os.getcwd())
    success = validator.validate_all()
    return 0 if success else 1

if __name__ == "__main__":
    exit(main())
