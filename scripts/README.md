# Scripts Directory

This directory contains utility scripts for the Albatross Migration Audit engine.

## Test Data Generator
`generate_comprehensive_test_data.py` is a robust data generator designed to produce realistic source and target datasets that exercise **every** check within the audit engine framework.

It programmatically injects data quality issues into a corresponding target dataset to simulate real-world schema and data migration corruption, generating a compatible `audit.yaml` configuration automatically.

### Basic Usage

Generate a small default dataset with a diverse mix of all possible errors:
```bash
python3 scripts/generate_comprehensive_test_data.py
```
*This will create a `random_data/` directory in the project root containing source CSVs, target CSVs, reference tables, and an `audit.yaml` config.*

### Advanced Configuration

You can strictly control the size, failure rates, and the *exact* types of errors injected into the generated dataset using command line arguments.

```bash
python3 scripts/generate_comprehensive_test_data.py \
    --rows 50000 \
    --fail-rate 0.5 \
    --errors "volume, enums, strings"
```

#### Available Arguments:

- `--rows` (int): Sets the number of *source* rows to generate. Target rows will automatically calculate a random volume variance if volume errors are allowed. (Default: `150`)
- `--fail-rate` (float): The fractional percentage of rows (0.0 to 1.0) that should contain at least one injected error. (Default: `0.35`)
- `--out-dir` (string): The requested output directory path for the generated CSVs and config. (Default: `random_data`)
- `--seed` (int): An optional integer RNG seed for perfectly reproducible deterministic data generation. 
- `--errors` (string): A comma-separated list of the specific error categories to inject. By default, it injects `"all"`.

#### Available Error Categories (`--errors`):

*   `volume`: Introduces row-count/volume mismatches (randomly adds or drops rows in the target).
*   `enums`: Injects completely invalid categorical mappings into enum fields.
*   `strings`: Simulates hard string truncation, UTF-8 encoding/mojibake corruption, and extra invisible whitespace padding.
*   `booleans`: Mutates boolean true/false columns into invalid string/integer representations.
*   `nulls`: Drops required `NOT NULL` fields or primary keys.
*   `precision`: Rounds high-precision decimals down, simulating float/decimal truncation in databases.
*   `relationships`: Injects broken Foreign Keys (inserts IDs that don't exist in the reference tables).
*   `aggregates`: Will trigger alongside `volume` mismatches to purposely fail SUM/AVG aggregate checks.
*   `all`: (Default) Randomly includes every error type above.

### Running an Audit against the Generated Data

Once the data is generated, you can immediately verify the engine's behavior against it from the project root:

```bash
python3 cli.py run --config random_data/audit.yaml --client "Test" --migration "Test Run"
```
