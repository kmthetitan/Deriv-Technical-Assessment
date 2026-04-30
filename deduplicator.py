import json
from typing import List, Dict, Set, Tuple
from parser import SQLParser

class IndexDeduplicator:
    def __init__(self):
        self.deduplication_log = []

    def deduplicate_indexes(self, index_recommendations: List[str]) -> Dict:
        """
        Deduplicate index recommendations deterministically.
        Returns: {
            'indexes': [...],  # Final consolidated indexes
            'decisions': [...]  # Deduplication decisions
        }
        """
        normalized_indexes = []
        parsed_indexes = {}  # For tracking originals
        
        # Parse and normalize all indexes
        for idx_sql in index_recommendations:
            normalized = SQLParser.normalize_index_definition(idx_sql)
            if normalized:
                normalized_indexes.append(normalized)
                parsed_indexes[normalized['name']] = normalized
        
        # Group by table and column combination
        table_column_groups = {}
        for idx in normalized_indexes:
            key = SQLParser.get_table_and_columns_from_index(idx)
            if key not in table_column_groups:
                table_column_groups[key] = []
            table_column_groups[key].append(idx)
        
        # Deduplicate within each group
        final_indexes = []
        decisions = []
        
        for (table, columns), indexes in table_column_groups.items():
            if len(indexes) == 1:
                final_indexes.append(indexes[0])
                decisions.append({
                    "table": table,
                    "columns": list(columns),
                    "decision": "kept",
                    "reason": "unique recommendation",
                    "kept_index": indexes[0]['name'],
                    "candidates": [idx['name'] for idx in indexes]
                })
            else:
                # Multiple indexes on same columns: keep first, mark others as duplicates
                kept_idx = indexes[0]
                final_indexes.append(kept_idx)
                
                duplicates = [idx['name'] for idx in indexes[1:]]
                decisions.append({
                    "table": table,
                    "columns": list(columns),
                    "decision": "deduplicated",
                    "reason": "identical index recommendations",
                    "kept_index": kept_idx['name'],
                    "removed_indexes": duplicates,
                    "candidates": [idx['name'] for idx in indexes]
                })
        
        self.deduplication_log = decisions
        
        return {
            "indexes": final_indexes,
            "decisions": decisions,
            "total_original": len(index_recommendations),
            "total_deduplicated": len(final_indexes)
        }

    def check_for_overlapping_indexes(self, normalized_indexes: List[Dict]) -> List[Dict]:
        """
        Identify indexes that overlap on column prefixes.
        Example: (a, b, c) and (a, b) can potentially overlap.
        """
        overlaps = []
        
        for i, idx1 in enumerate(normalized_indexes):
            for idx2 in normalized_indexes[i+1:]:
                # Same table
                if idx1['table'] != idx2['table']:
                    continue
                
                # Check if one is prefix of other
                cols1 = tuple(idx1['columns'])
                cols2 = tuple(idx2['columns'])
                
                if cols1[:len(cols2)] == cols2 or cols2[:len(cols1)] == cols1:
                    overlaps.append({
                        "index1": idx1['name'],
                        "index2": idx2['name'],
                        "table": idx1['table'],
                        "columns1": list(cols1),
                        "columns2": list(cols2),
                        "relationship": "prefix_overlap",
                        "note": "Longer index can satisfy shorter index queries"
                    })
        
        return overlaps

    def save_deduplication_log(self, filepath: str, deduplication_result: Dict):
        """Save deduplication decisions to JSON."""
        with open(filepath, 'w') as f:
            json.dump(deduplication_result, f, indent=2)
