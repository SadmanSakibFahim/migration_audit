import csv
import datetime
import os
import random
from typing import Any, Dict, List


class DataGenerator:
    def __init__(self):
        pass

    def generate_data_for_config(
        self, config: Dict[str, Any], output_dir: str, row_count: int = 100
    ):
        """
        Generates CSV files for each table in the config.
        """
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        tables = config.get("tables", {})
        generated_files = []

        for table_name, table_config in tables.items():
            # We'll generate source and target files if they are distinct in config,
            # but usually for schema-only audit we start with one set of "perfect" data
            # and then maybe modify it for the other side.
            # For this simple generator, let's just generate the 'source' file specified in config
            # or a default filename if not specified.

            # Note: The converter puts 'data/source/{table}.csv' in the config.
            # We should respect the output_dir provided here and ignore the exact path in config for filename generation,
            # OR we respect the config path.
            # Let's write to output_dir/{table_name}_source.csv and output_dir/{table_name}_target.csv

            data = self._generate_table_data(table_config, row_count)

            source_path = os.path.join(output_dir, f"{table_name}_source.csv")
            self._write_csv(source_path, data, table_config)
            generated_files.append(source_path)

            target_path = os.path.join(output_dir, f"{table_name}_target.csv")
            self._write_csv(target_path, data, table_config)  # exact copy for now
            generated_files.append(target_path)

        return generated_files

    def _generate_table_data(
        self, table_config: Dict[str, Any], row_count: int
    ) -> List[Dict[str, Any]]:
        data = []
        constraints = table_config.get("data_constraints", {})
        mappings = table_config.get("mappings", [])

        # Determine columns from constraints keys + mapping keys + any other inferred
        # For this basic version, we only know columns that have constraints or mappings.
        # Ideally we'd have a full column list in the config, but our converter only extracted constraints.
        # Let's collect all known columns.
        columns = set(constraints.keys())
        for m in mappings:
            for c in m.get("columns", []):
                columns.add(c)

        # Check if PK is in columns, if not add it
        pk = table_config.get("primary_key", "id")
        columns.add(pk)

        col_list = list(columns)

        for i in range(row_count):
            row = {}
            for col in col_list:
                row[col] = self._generate_value(col, constraints.get(col, []), mappings)

            # Ensure PK uniqueness (overwrite generated value if simple)
            if pk == "id":
                row[pk] = i + 1
            else:
                row[pk] = str(i + 1)  # simple fallback

            data.append(row)

        return data

    def _generate_value(
        self, col_name: str, col_constraints: List[str], mappings: List[Dict[str, Any]]
    ) -> Any:
        # Check mappings for allowed values first
        for m in mappings:
            if col_name in m.get("columns", []):
                allowed = m.get("allowed_values", [])
                if allowed:
                    return random.choice(allowed)

        # Check type constraints
        if "date" in col_constraints:
            # Generate random date
            start_date = datetime.date(2020, 1, 1)
            end_date = datetime.date(2025, 12, 31)
            delta = end_date - start_date
            random_days = random.randrange(delta.days)
            return (start_date + datetime.timedelta(days=random_days)).isoformat()

        # Default generation based on name heuristics or fallback
        if "email" in col_name.lower():
            return f"user{random.randint(1000,9999)}@example.com"
        if "name" in col_name.lower():
            return f"Name_{random.randint(1, 1000)}"
        if "price" in col_name.lower() or "amount" in col_name.lower():
            return round(random.uniform(10.0, 500.0), 2)

        # Fallback string
        return f"val_{random.randint(1, 100)}"

    def _write_csv(
        self, filepath: str, data: List[Dict[str, Any]], table_config: Dict[str, Any]
    ):
        if not data:
            return

        keys = list(data[0].keys())
        # Ideally sort keys so PK is first?
        pk = table_config.get("primary_key", "id")
        if pk in keys:
            keys.remove(pk)
            keys.insert(0, pk)

        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(data)


if __name__ == "__main__":
    gen = DataGenerator()
    print("DataGenerator initialized")
