# run_audit.py
import yaml
import pandas as pd
from typing import List

from tqdm import tqdm

from core.logger import get_logger
from core.loader import load_table
from core.exceptions import DataLoadError
from core.check_runner import CheckRunner
from core.result import TestResult
from core.config_models import AuditConfig
from core.row_validator import validate_rows, export_invalid_rows, create_invalid_rows_summary_log

logger = get_logger(__name__)


def load_config(config_path: str) -> AuditConfig:
    """Load YAML config safely and validate with pydantic."""
    try:
        with open(config_path, "r") as f:
            cfg_dict = yaml.safe_load(f) or {}
        return AuditConfig(**cfg_dict)
    except Exception as e:
        logger.error(f"Failed to load or validate config: {e}")
        raise


def load_table_safe(path: str, table_name: str) -> "pd.DataFrame":
    """Load table and wrap exceptions in DataLoadError."""
    try:
        return load_table(path)
    except Exception as e:
        logger.error(f"Failed to load table '{table_name}' from '{path}': {e}")
        raise DataLoadError(
            table_name=table_name,
            source=path,
            original_exception=e
        )


def _normalize_results(results) -> List[TestResult]:
    """
    Normalize any runner output into List[TestResult].
    This makes run_audit resilient to future changes.
    """
    if results is None:
        return []
    if isinstance(results, list):
        return results
    return [results]


def run_audit(
    config_path: str = "config/audit.yaml",
    tables_to_run: List[str] = None,
    dry_run: bool = False,
    ignore_invalid_rows: bool = False,
) -> List[TestResult]:

    logger.info("Starting audit run")
    cfg = load_config(config_path)

    tables_cfg = cfg.tables
    volume_tolerance = cfg.tolerances.volume_loss_pct
    aggregate_tolerance = cfg.tolerances.aggregate_pct_diff

    if not tables_cfg:
        logger.warning("No tables defined in config. Exiting.")
        return []

    tables_list = tables_to_run or list(tables_cfg.keys())
    logger.info(f"Tables to audit: {tables_list}")

    all_results: List[TestResult] = []

    for table_name in tqdm(tables_list, desc="Auditing tables"):
        if table_name not in tables_cfg:
            logger.warning(f"Table '{table_name}' not found in config. Skipping.")
            continue

        meta = tables_cfg[table_name]
        logger.info(f"Auditing table: {table_name}")

        try:
            # Handle complex mappings (N:1, 1:N, N:M)
            if meta.is_complex_mapping():
                from core.loader import load_table
                logger.info(f"Processing complex mapping for '{table_name}': {meta.complex_mapping.mapping_type}")
                
                # #region agent log
                import json
                import os
                try:
                    os.makedirs('.cursor', exist_ok=True)
                    with open('.cursor\\debug.log', 'a', encoding='utf-8') as f:
                        f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"run_audit.py:88","message":"Starting complex mapping","data":{"table_name":table_name,"mapping_type":meta.complex_mapping.mapping_type,"num_sources":len(meta.complex_mapping.sources),"num_targets":len(meta.complex_mapping.targets)},"timestamp":int(__import__('time').time()*1000)}) + '\n')
                except Exception as e:
                    logger.debug(f"Could not write debug log: {e}")
                # #endregion
                
                # Load and validate each source file individually
                valid_sources = []
                for src in meta.complex_mapping.sources:
                    temp_df = load_table_safe(src.path, table_name)
                    # #region agent log
                    try:
                        with open('.cursor\\debug.log', 'a', encoding='utf-8') as f:
                            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"run_audit.py:101","message":"Loaded source file","data":{"path":src.path,"rows":len(temp_df),"columns":list(temp_df.columns)},"timestamp":int(__import__('time').time()*1000)}) + '\n')
                    except: pass
                    # #endregion
                    logger.debug(f"Loaded source file {src.path}: {len(temp_df)} rows")
                    if ignore_invalid_rows:
                        valid_df, invalid_rows = validate_rows(temp_df, meta, table_name, is_source=True)
                        if invalid_rows:
                            export_invalid_rows(invalid_rows, src.path, table_name, is_source=True)
                        temp_df = valid_df
                        # #region agent log
                        try:
                            with open('.cursor\\debug.log', 'a', encoding='utf-8') as f:
                                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"run_audit.py:110","message":"After validation","data":{"rows":len(temp_df),"invalid_rows":len(invalid_rows)},"timestamp":int(__import__('time').time()*1000)}) + '\n')
                        except: pass
                        # #endregion
                    
                    # Apply column mapping if specified
                    if src.column_mapping:
                        temp_df = temp_df.rename(columns=src.column_mapping)
                    
                    valid_sources.append(temp_df)
                
                # #region agent log
                try:
                    with open('.cursor\\debug.log', 'a', encoding='utf-8') as f:
                        f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"B","location":"run_audit.py:122","message":"Before merge","data":{"num_valid_sources":len(valid_sources),"strategy":meta.complex_mapping.aggregation_strategy,"source_rows":[len(df) for df in valid_sources]},"timestamp":int(__import__('time').time()*1000)}) + '\n')
                except: pass
                # #endregion
                logger.info(f"Before merge: {len(valid_sources)} source files with rows: {[len(df) for df in valid_sources]}")
                
                # Merge sources based on strategy
                if len(valid_sources) == 0:
                    logger.error(f"No valid source data loaded for table '{table_name}'")
                    src_df = pd.DataFrame()  # Empty DataFrame
                elif len(valid_sources) == 1:
                    src_df = valid_sources[0]
                else:
                    # Multiple sources - merge them
                    if meta.complex_mapping.aggregation_strategy == 'merge':
                        # Simple concatenation of all sources
                        src_df = pd.concat(valid_sources, ignore_index=True)
                    elif meta.complex_mapping.aggregation_strategy == 'sum':
                        # Sum numeric columns, keep first non-numeric
                        src_df = valid_sources[0].copy()
                        for df in valid_sources[1:]:
                            common_cols = set(src_df.columns) & set(df.columns)
                            for col in common_cols:
                                if pd.api.types.is_numeric_dtype(src_df[col]):
                                    src_df[col] = src_df[col].fillna(0) + df[col].fillna(0)
                    else:
                        # Default: concatenate
                        src_df = pd.concat(valid_sources, ignore_index=True)
                
                # Log merge result
                logger.info(f"After merge: src_df has {len(src_df)} rows, columns: {list(src_df.columns) if len(src_df) > 0 else '[]'}")
                # #region agent log
                try:
                    import os
                    os.makedirs('.cursor', exist_ok=True)
                    with open('.cursor\\debug.log', 'a', encoding='utf-8') as f:
                        f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"B","location":"run_audit.py:148","message":"After merge","data":{"src_df_rows":len(src_df),"src_df_columns":list(src_df.columns) if len(src_df) > 0 else []},"timestamp":int(__import__('time').time()*1000)}) + '\n')
                except Exception as e:
                    logger.debug(f"Could not write debug log: {e}")
                # #endregion
                
                # Load and validate each target file individually
                valid_targets = []
                for tgt in meta.complex_mapping.targets:
                    temp_df = load_table_safe(tgt.path, table_name)
                    if ignore_invalid_rows:
                        valid_df, invalid_rows = validate_rows(temp_df, meta, table_name, is_source=False)
                        if invalid_rows:
                            export_invalid_rows(invalid_rows, tgt.path, table_name, is_source=False)
                        temp_df = valid_df
                    
                    # Apply column mapping if specified
                    if tgt.column_mapping:
                        temp_df = temp_df.rename(columns=tgt.column_mapping)
                    
                    valid_targets.append(temp_df)
                
                # Merge targets based on strategy
                if len(valid_targets) == 0:
                    logger.error(f"No valid target data loaded for table '{table_name}'")
                    tgt_df = pd.DataFrame()  # Empty DataFrame
                elif len(valid_targets) == 1:
                    tgt_df = valid_targets[0]
                else:
                    # Multiple targets - merge them (for 1:N or N:M mappings)
                    # All split strategies result in concatenation of target files
                    tgt_df = pd.concat(valid_targets, ignore_index=True)
            else:
                # Handle simple mappings (backward compatible)
                source_path = meta.source if isinstance(meta.source, str) else meta.source[0].path if isinstance(meta.source, list) else None
                target_path = meta.target if isinstance(meta.target, str) else meta.target[0].path if isinstance(meta.target, list) else None
                
                if not source_path or not target_path:
                    logger.error(f"Invalid source/target configuration for table '{table_name}'")
                    continue
                
                src_df = load_table_safe(source_path, table_name)
                tgt_df = load_table_safe(target_path, table_name)
                
                # Validate and filter invalid rows if requested
                if ignore_invalid_rows:
                    src_df, src_invalid = validate_rows(src_df, meta, table_name, is_source=True)
                    if src_invalid:
                        export_invalid_rows(src_invalid, source_path, table_name, is_source=True)
                        logger.info(f"Filtered {len(src_invalid)} invalid rows from source '{table_name}'")
                    
                    tgt_df, tgt_invalid = validate_rows(tgt_df, meta, table_name, is_source=False)
                    if tgt_invalid:
                        export_invalid_rows(tgt_invalid, target_path, table_name, is_source=False)
                        logger.info(f"Filtered {len(tgt_invalid)} invalid rows from target '{table_name}'")
        except DataLoadError:
            logger.error(f"Skipping table '{table_name}' due to load error.")
            continue
        except Exception as e:
            logger.error(f"Unexpected error loading table '{table_name}': {e}")
            continue

        logger.info(
            f"{table_name}: source_rows={len(src_df)}, target_rows={len(tgt_df)}"
        )

        if dry_run:
            logger.info(
                f"Dry-run enabled. Skipping checks for table '{table_name}'."
            )
            continue

        runner = CheckRunner(
            table_name=table_name,
            meta=meta,
            src_df=src_df,
            tgt_df=tgt_df,
            volume_tolerance=volume_tolerance,
            aggregate_tolerance=aggregate_tolerance,
        )

        table_results_raw = runner.execute_all()
        table_results = _normalize_results(table_results_raw)

        logger.info(
            f"{table_name}: collected {len(table_results)} check results"
        )

        all_results.extend(table_results)
        logger.info(f"Completed audit for table: {table_name}")

    logger.info(
        f"Audit run finished. Total checks executed: {len(all_results)}"
    )
    
    # Create summary log of invalid rows if filtering was enabled
    if ignore_invalid_rows:
        from pathlib import Path
        import os
        # Determine output directory (use current working directory or config directory)
        # Prefer creating in a logs directory if it exists, otherwise use config directory
        config_path_obj = Path(config_path)
        output_dir = Path(os.getcwd()) / "logs"
        if not output_dir.exists():
            output_dir = config_path_obj.parent
        output_dir.mkdir(parents=True, exist_ok=True)
        summary_log = create_invalid_rows_summary_log(str(output_dir))
        if summary_log:
            logger.info(f"Invalid rows summary log created: {summary_log}")
            print(f"\n✓ Invalid rows summary log: {summary_log}\n")
    
    return all_results
