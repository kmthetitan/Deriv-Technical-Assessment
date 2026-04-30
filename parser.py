import re
from typing import List, Dict, Tuple

class SQLParser:
    @staticmethod
    def parse_slow_queries(file_path: str) -> List[Dict]:
        """Parse slow_queries.sql into individual queries with metadata."""
        with open(file_path, 'r') as f:
            content = f.read()
        
        queries = []
        # Split by comment lines that start with --
        pattern = r'--\s*(.+?)\n(SELECT.*?)(?=(?:--|$))'
        matches = re.finditer(pattern, content, re.DOTALL | re.IGNORECASE)
        
        query_id = 1
        for match in matches:
            comment = match.group(1).strip()
            query_text = match.group(2).strip()
            
            if query_text:
                queries.append({
                    "query_id": f"Q{query_id}",
                    "comment": comment,
                    "sql": query_text
                })
                query_id += 1
        
        return queries

    @staticmethod
    def parse_schema(file_path: str) -> str:
        """Read schema.sql and return as string."""
        with open(file_path, 'r') as f:
            return f.read()

    @staticmethod
    def extract_create_index_statements(sql_text: str) -> List[str]:
        """Extract CREATE INDEX statements from SQL."""
        pattern = r'CREATE\s+(?:UNIQUE\s+)?INDEX\s+[^;]+;'
        matches = re.finditer(pattern, sql_text, re.IGNORECASE)
        return [match.group(0) for match in matches]

    @staticmethod
    def normalize_index_definition(create_index_sql: str) -> Dict:
        """Normalize index definition for deduplication."""
        # Extract components: name, table, columns, uniqueness
        match = re.match(
            r'CREATE\s+(?P<unique>UNIQUE\s+)?INDEX\s+(?P<name>\w+)\s+ON\s+(?P<table>\w+)\s*\((?P<columns>[^)]+)\)',
            create_index_sql,
            re.IGNORECASE
        )
        
        if not match:
            return None
        
        columns = [col.strip().split()[0] for col in match.group('columns').split(',')]
        
        return {
            "name": match.group('name'),
            "table": match.group('table').lower(),
            "columns": columns,
            "unique": bool(match.group('unique')),
            "original_sql": create_index_sql.strip()
        }

    @staticmethod
    def get_table_and_columns_from_index(normalized: Dict) -> Tuple[str, Tuple]:
        """Get table and column tuple for comparison."""
        return (
            normalized['table'],
            tuple(normalized['columns'])
        )
