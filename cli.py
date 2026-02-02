import argparse

def build_parser():
    parser = argparse.ArgumentParser(
        description="Migration Validation & Risk Audit CLI"
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser(
        "run",
        help="Run migration audit and generate report"
    )

    run_parser.add_argument(
        "--config",
        required=True,
        help="Path to audit configuration YAML"
    )

    run_parser.add_argument(
        "--out",
        required=False,
        help="Output path for audit report (DOCX). Defaults to outputs/<timestamp>/Audit_Report.docx"
    )

    run_parser.add_argument(
        "--client",
        required=True,
        help="Client name for report"
    )

    run_parser.add_argument(
        "--migration",
        required=True,
        help="Migration description (source -> target)"
    )

    run_parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging verbosity (default: INFO)"
    )

    run_parser.add_argument(
        "--ignore-invalid-rows",
        action="store_true",
        help="Ignore invalid rows during audit. Invalid rows will be logged and exported to invalid_data subfolder."
    )

    run_parser.add_argument(
        "--test",
        action="store_true",
        help="Run in test mode (CI/CD). Saves results to timestamped subfolders in 'test_outputs' with a '_test' suffix."
    )

    return parser

def main():
    parser = build_parser()
    args = parser.parse_args()

    # 🔑 Set logging level globally BEFORE any logger is created
    import os
    os.environ["LOG_LEVEL"] = args.log_level

    if args.command == "run":
        from run_audit import run_audit
        from reports.report_builder import build_report
        from core.audit.verdict import final_verdict
        from core.audit.exceptions import AuditError
        from core.audit.logger import get_logger

        logger = get_logger(__name__)

        logger.info(f"Running audit with log level: {args.log_level}")
        
        if args.ignore_invalid_rows:
            logger.info("Invalid row filtering enabled. Invalid rows will be excluded from audit.")

        try:
            results = run_audit(
                config_path=args.config,
                ignore_invalid_rows=args.ignore_invalid_rows,
                no_auth=args.test # Bypass auth in CI/Test mode
            )
        except AuditError as e:
            logger.error(f"Audit failed: {e}")
            exit(1)

        # Determine output location rules
        build_args = {
            "results": results,
            "output_path": args.out,
            "client": args.client,
            "migration": args.migration
        }

        if args.test:
            build_args["base_dir"] = "test_outputs"
            build_args["label"] = "_test"

        build_report(**build_args)

        verdict = final_verdict(results)
        from core.audit.verdict import Verdict
        
        # Always exit successfully - let users review the report and decide
        print(f"\nAudit complete. Final verdict: {verdict}\n")
        
        if verdict in [Verdict.NO_GO, Verdict.ERROR]:
            print(f"⚠️  WARNING: Migration audit indicates issues. Please review the report carefully.\n")


if __name__ == "__main__":
    main()