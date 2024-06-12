import argparse
import os
from cover_agent.CoverAgent import CoverAgent
from cover_agent.LoadgenAgent import LoadgenAgent
from cover_agent.version import __version__


def parse_args():
    """
    Parse command line arguments.
    """
    parser = argparse.ArgumentParser(description=f"Cover Agent v{__version__}")
    subparsers = parser.add_subparsers(dest='command')

    # unit-test command arguments
    unit_test_parser = subparsers.add_parser('unit-test', help='unit-test command')
    unit_test_parser.add_argument(
        "--test-command",
        required=True,
        help="The command to run tests and generate coverage report.",
    )
    unit_test_parser.add_argument(
        "--test-command-dir",
        default=os.getcwd(),
        help="The directory to run the test command in. Default: %(default)s.",
    )
    unit_test_parser.add_argument(
        "--included-files",
        default=None,
        nargs="*",
        help='List of files to include in the coverage. For example, "--included-files library1.c library2.c." Default: %(default)s.',
    )
    unit_test_parser.add_argument(
        "--coverage-type",
        default="cobertura",
        help="Type of coverage report. Default: %(default)s.",
    )
    unit_test_parser.add_argument(
        "--report-filepath",
        default="test_results.html",
        help="Path to the output report file. Default: %(default)s.",
    )
    unit_test_parser.add_argument(
        "--desired-coverage",
        required=True,
        help="Desired coverage percentage.",
    )

    # loadgen command arguments
    loadgen_parser = subparsers.add_parser('loadgen', help='loadgen command')
    loadgen_parser.add_argument(
        "--protobuf-definition-path", required=True, help="Path to the protobuf definition file."
    )
    loadgen_parser.add_argument(
        "--loadgen-module-file-path", required=True, help="Path to the loadgen module."
    )
    loadgen_parser.add_argument(
        "--included-files",
        default=None,
        nargs="*",
        help='List of files to include in the loadgen. For example, "--included-files library1.c library2.c." Default: %(default)s.',
    )
    loadgen_parser.add_argument(
        "--model", default="ollama/codellama:13b", help="Model to use for loadgen."
    )
    loadgen_parser.add_argument(
        "--api-base", default="http://localhost:11434", help="API base for loadgen."
    )
    loadgen_parser.add_argument(
        "--loadgen-test-command",
        default="./gradlew loadgen",
        help="Command to run the loadgen job."
    )
    loadgen_parser.add_argument(
        "--loadgen-test-command-dir",
        default=os.getcwd(),
        help="Directory to run the loadgen command in. Default: %(default)s."
    )
    loadgen_parser.add_argument(
        "--additional-instructions",
        default=None,
        help="Additional instructions for the loadgen."
    )

    return parser.parse_args()


def main():
    args = parse_args()

    if args.command == 'unit-test':
        agent = CoverAgent(args)
    elif args.command == 'loadgen':
        agent = LoadgenAgent(args)
    else:
        print(f"Unknown command: {args.command}")
        return

    agent.run()


if __name__ == "__main__":
    main()
