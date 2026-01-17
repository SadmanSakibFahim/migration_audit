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
        required=True,
        help="Output path for audit report (DOCX)"
    )

    run_parser.add_argument(
        "--client",
        required=True,
        help="Client name for report"
    )

    run_parser.add_argument(
        "--migration",
        required=True,
        help="Migration description (source → target)"
    )

    run_parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging verbosity (default: INFO)"
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
        from core.verdict import final_verdict
        from core.exceptions import AuditError
        from core.logger import get_logger

        logger = get_logger(__name__)

        logger.info(f"Running audit with log level: {args.log_level}")

        try:
            results = run_audit(config_path=args.config)
        except AuditError as e:
            logger.error(f"Audit failed: {e}")
            exit(1)

        build_report(
            results=results,
            output_path=args.out,
            client=args.client,
            migration=args.migration
        )

        verdict = final_verdict(results)
        print(f"\nAudit complete. Final verdict: {verdict}\n")


if __name__ == "__main__":
    main()