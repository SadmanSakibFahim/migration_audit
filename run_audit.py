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
            src_df = load_table_safe(meta.source, table_name)
            tgt_df = load_table_safe(meta.target, table_name)
        except DataLoadError:
            logger.error(f"Skipping table '{table_name}' due to load error.")
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
    return all_results
