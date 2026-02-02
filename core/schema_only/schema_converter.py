import re
import json
import yaml
from typing import Dict, Any, List

class SchemaConverter:
    def __init__(self):
        pass

    def convert_to_config(self, schema_path: str, format: str = 'sql') -> Dict[str, Any]:
        """
        Converts a schema file to an audit.yaml configuration dictionary.
        """
        with open(schema_path, 'r') as f:
            content = f.read()

        if format.lower() == 'sql':
            return self._parse_sql(content)
        elif format.lower() == 'json':
            return self._parse_json_schema(content)
        else:
            raise ValueError(f"Unsupported format: {format}")

    def _parse_sql(self, content: str) -> Dict[str, Any]:
        """
        Basic SQL DDL parser. verify CREATE TABLE statements.
        """
        config = {'tables': {}}
        
        # Regex to find CREATE TABLE statements
        table_pattern = re.compile(r'CREATE\s+TABLE\s+(\w+)\s*\((.*?)\);', re.DOTALL | re.IGNORECASE)
        
        tables = table_pattern.findall(content)
        
        for table_name, body in tables:
            columns_def = self._parse_sql_columns(body)
            
            table_config = {
                'source': f'data/source/{table_name}.csv',
                'target': f'data/target/{table_name}.csv',
                'primary_key': 'id', # Default assumption, user can change
                'aggregates': columns_def['numeric_cols'],
                'data_constraints': columns_def['constraints'],
                'mappings': [], 
                'relationships': []
            }
            
            # Try to guess primary key
            for col, constraints in columns_def['constraints'].items():
                if 'primary_key' in constraints: 
                    table_config['primary_key'] = col
                    columns_def['constraints'][col].remove('primary_key')
            
            config['tables'][table_name] = table_config
            
        return config

    def _parse_sql_columns(self, body: str) -> Dict[str, Any]:
        constraints = {}
        numeric_cols = []
        pk_cols = []
        
        # Split by comma, but be careful about commas in parentheses (e.g. DECIMAL(10,2))
        # For simplicity in this basic version, we'll split by comma and clean up
        lines = [line.strip() for line in body.split(',')]
        
        for line in lines:
            if not line or line.upper().startswith('PRIMARY KEY') or line.upper().startswith('FOREIGN KEY'):
                continue
                
            parts = line.split()
            if len(parts) < 2:
                continue
                
            col_name = parts[0]
            col_type = parts[1].upper()
            
            col_constraints = []
            
            # Check for PK inline
            is_pk = False
            if ('PRIMARY' in line.upper() and 'KEY' in line.upper()) or col_name.lower() == 'id':
                col_constraints.append('primary_key')
                is_pk = True
                pk_cols.append(col_name)

            # Heuristic for FK: ends with _id or explicit constraint
            is_fk = col_name.lower().endswith('_id') or 'REFERENCES' in line.upper()

            # Map SQL types to audit types (if necessary, or just keep as identity for now)
            if 'INT' in col_type or 'DECIMAL' in col_type or 'NUMERIC' in col_type or 'FLOAT' in col_type:
                # Exclude PKs and FKs from mathematical aggregates
                if not is_pk and not is_fk:
                    numeric_cols.append(col_name)
                
            if 'DATE' in col_type or 'TIME' in col_type:
                col_constraints.append('date')
            
            # Check for NOT NULL
            if 'NOT NULL' in line.upper():
                col_constraints.append('not_null')
            
            constraints[col_name] = col_constraints
            
        return {'constraints': constraints, 'numeric_cols': numeric_cols}

    def _parse_json_schema(self, content: str) -> Dict[str, Any]:
        """
        Parses a JSON schema (assuming a top-level object or list of objects defines tables).
        For simplicity, assume the JSON represents a single table definition or a collection.
        If it's a standard JSON Schema draft, we look for 'properties'.
        """
        try:
            schema = json.loads(content)
        except json.JSONDecodeError:
            raise ValueError("Invalid JSON content")
            
        config = {'tables': {}}
        
        # Heuristic: Is this a single object schema or multiple?
        # Let's assume a structure like { "definitions": { "User": { ... } } } or root is the table.
        # If root has "properties", treat as one table named "unknown_table" or derived from filename.
        
        if 'properties' in schema:
            table_name = schema.get('title', 'main_table').lower()
            config['tables'][table_name] = self._convert_json_properties_to_table_config(schema, table_name)
        
        return config

    def _convert_json_properties_to_table_config(self, schema_node: Dict[str, Any], table_name: str) -> Dict[str, Any]:
        constraints = {}
        properties = schema_node.get('properties', {})
        required = schema_node.get('required', [])
        
        for prop_name, prop_def in properties.items():
            col_constraints = []
            prop_type = prop_def.get('type')
            
            if prop_name in required:
                col_constraints.append('not_null')
                
            if prop_type == 'integer' or prop_type == 'number':
                pass
            
            # Check for format (date, email)
            fmt = prop_def.get('format')
            if fmt == 'date' or fmt == 'date-time':
                col_constraints.append('date')
            if fmt == 'email':
                # If audit tool supported email constraint
                pass
            
            constraints[prop_name] = col_constraints
            
        return {
            'source': f'data/source/{table_name}.csv',
            'target': f'data/target/{table_name}.csv',
            'primary_key': 'id', # Default
            'data_constraints': constraints,
            'mappings': [],
            'relationships': []
        }

if __name__ == '__main__':
    # Test execution
    converter = SchemaConverter()
    print("SchemaConverter initialized")
