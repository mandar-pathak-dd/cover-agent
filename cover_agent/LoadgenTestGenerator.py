import datetime
import logging
import os
import re
from wandb.sdk.data_types.trace_tree import Trace

from cover_agent.LoadgenPromptBuilder import LoadgenPromptBuilder
from cover_agent.Runner import Runner
from cover_agent.CoverageProcessor import CoverageProcessor
from cover_agent.CustomLogger import CustomLogger
from cover_agent.PromptBuilder import PromptBuilder
from cover_agent.AICaller import AICaller
from cover_agent.FilePreprocessor import FilePreprocessor
from cover_agent.utils import load_yaml
from cover_agent.settings.config_loader import get_settings


# We need

class LoadgenTestGenerator:
    def __init__(
        self,
        loadgen_module_file_path: str,
        protobuf_definition_file: str,
        llm_model: str,
        api_base: str = "",
        loadgen_command: str = './gradlew loadgen',
        loadgen_command_dir: str = os.getcwd(),
        included_files: list = None,
        additional_instructions: str = "",
    ):
        # Class variables
        self.protobuf_definition_path = protobuf_definition_file
        self.loadgen_module_file_path = loadgen_module_file_path
        # self.code_coverage_report_path = code_coverage_report_path
        self.loadgen_command = loadgen_command
        self.loadgen_command_dir = loadgen_command_dir
        self.included_files = self.get_included_files(included_files)
        self.additional_instructions = additional_instructions

        # Objects to instantiate
        self.ai_caller = AICaller(model=llm_model, api_base=api_base)

        # Get the logger instance from CustomLogger
        self.logger = CustomLogger.get_logger(__name__)

        # States to maintain within this class
        self.preprocessor = FilePreprocessor(self.loadgen_module_file_path)
        self.failed_test_runs = []

        # Run coverage and build the prompt
        # self.run_coverage()
        self.prompt = self.build_prompt()

    @staticmethod
    def get_included_files(included_files):
        """
        A method to read and concatenate the contents of included files into a single string.

        Parameters:
            included_files (list): A list of paths to included files.

        Returns:
            str: A string containing the concatenated contents of the included files, or an empty string if the input list is empty.
        """
        if included_files:
            included_files_content = []
            file_names = []
            for file_path in included_files:
                try:
                    with open(file_path, "r") as file:
                        included_files_content.append(file.read())
                        file_names.append(file_path)
                except IOError as e:
                    print(f"Error reading file {file_path}: {str(e)}")
            out_str = ""
            if included_files_content:
                for i, content in enumerate(included_files_content):
                    out_str += f"file_path: `{file_names[i]}`\ncontent:\n```\n{content}\n```\n"

            return out_str.strip()
        return ""

    def build_prompt(self):
        self.prompt_builder = LoadgenPromptBuilder(
            protobuf_definition_path=self.protobuf_definition_path,
            loadgen_module_path=self.loadgen_module_file_path,
            included_files=self.included_files,
            additional_instructions=self.additional_instructions,
        )

        return self.prompt_builder.build_prompt()

    def generate_tests(self, max_tokens=8192, dry_run=False):
        self.prompt = self.build_prompt()

        response, prompt_token_count, response_token_count = (
            self.ai_caller.call_model(prompt=self.prompt, max_tokens=max_tokens)
        )

        # Write the response to the `loadgen_module_file_path` file
        with open(self.loadgen_module_file_path, "w") as test_file:
            test_file.write(response)
        return []

    def validate_test(self, generated_test: dict, generated_tests_dict: dict):
        try:
            # Step 0: no pre-process.
            # We asked the model that each generated test should be a self-contained independent test
            test_code = generated_test.get("test_code", "").rstrip()
            additional_imports = generated_test.get("new_imports_code", "").strip()
            if additional_imports and additional_imports[0] == '"' and additional_imports[-1] == '"':
                additional_imports = additional_imports.strip('"')

            # check if additional_imports only contains '"':
            if additional_imports and additional_imports == '""':
                additional_imports = ""
            relevant_line_number_to_insert_tests_after = self.relevant_line_number_to_insert_tests_after
            relevant_line_number_to_insert_imports_after = self.relevant_line_number_to_insert_imports_after

            needed_indent = self.test_headers_indentation
            # remove initial indent of the test code, and insert the needed indent
            test_code_indented = test_code
            if needed_indent:
                initial_indent = len(test_code) - len(test_code.lstrip())
                delta_indent = int(needed_indent) - initial_indent
                if delta_indent > 0:
                    test_code_indented = "\n".join(
                        [delta_indent * " " + line for line in test_code.split("\n")]
                    )
            test_code_indented = "\n" + test_code_indented.strip("\n") + "\n"

            if test_code_indented and relevant_line_number_to_insert_tests_after:

                # Step 1: Append the generated test to the relevant line in the test file
                with open(self.loadgen_module_file_path, "r") as test_file:
                    original_content = test_file.read()  # Store original content
                original_content_lines = original_content.split("\n")
                test_code_lines = test_code_indented.split("\n")
                # insert the test code at the relevant line
                processed_test_lines = (
                    original_content_lines[:relevant_line_number_to_insert_tests_after]
                    + test_code_lines
                    + original_content_lines[relevant_line_number_to_insert_tests_after:]
                )
                # insert the additional imports at line 'relevant_line_number_to_insert_imports_after'
                processed_test = "\n".join(processed_test_lines)
                if relevant_line_number_to_insert_imports_after and additional_imports and additional_imports not in processed_test:
                    additional_imports_lines = additional_imports.split("\n")
                    processed_test_lines = (
                        processed_test_lines[:relevant_line_number_to_insert_imports_after]
                        + additional_imports_lines
                        + processed_test_lines[relevant_line_number_to_insert_imports_after:]
                    )
                    self.relevant_line_number_to_insert_tests_after += len(additional_imports_lines) # this is important, otherwise the next test will be inserted at the wrong line
                processed_test = "\n".join(processed_test_lines)

                with open(self.loadgen_module_file_path, "w") as test_file:
                    test_file.write(processed_test)

                # Step 2: Run the test using the Runner class
                self.logger.info(
                    f'Running test with the following command: "{self.loadgen_command}"'
                )
                stdout, stderr, exit_code, time_of_test_command = Runner.run_command(
                    command=self.loadgen_command, cwd=self.loadgen_command_dir
                )

                # Step 3: Check for pass/fail from the Runner object
                if exit_code != 0:
                    # Test failed, roll back the test file to its original content
                    with open(self.loadgen_module_file_path, "w") as test_file:
                        test_file.write(original_content)
                    self.logger.info(f"Skipping a generated test that failed")
                    fail_details = {
                        "status": "FAIL",
                        "reason": "Test failed",
                        "exit_code": exit_code,
                        "stderr": stderr,
                        "stdout": stdout,
                        "test": generated_test,
                    }

                    error_message = extract_error_message_python(fail_details["stdout"])
                    if error_message:
                        logging.error(f"Error message:\n{error_message}")

                    self.failed_test_runs.append(
                        {"code": generated_test, "error_message": error_message}
                    )  # Append failure details to the list

                    if 'WANDB_API_KEY' in os.environ:
                        fail_details["error_message"] = error_message
                        root_span = Trace(
                            name="fail_details_" + datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S"),
                            kind="llm",  # kind can be "llm", "chain", "agent" or "tool
                            inputs={"test_code": fail_details["test"]},
                            outputs=fail_details)
                        root_span.log(name='inference')

                    return fail_details

                # If test passed, check for coverage increase
                try:
                    # Step 4: Check that the coverage has increased using the CoverageProcessor class
                    new_coverage_processor = CoverageProcessor(
                        file_path=self.code_coverage_report_path,
                        src_file_path=self.protobuf_definition_path,
                        coverage_type=self.coverage_type,
                    )
                    _, _, new_percentage_covered = (
                        new_coverage_processor.process_coverage_report(
                            time_of_test_command=time_of_test_command
                        )
                    )

                    if new_percentage_covered <= self.current_coverage:
                        # Coverage has not increased, rollback the test by removing it from the test file
                        with open(self.loadgen_module_file_path, "w") as test_file:
                            test_file.write(original_content)
                        self.logger.info(
                            "Test did not increase coverage. Rolling back."
                        )
                        fail_details = {
                            "status": "FAIL",
                            "reason": "Coverage did not increase",
                            "exit_code": exit_code,
                            "stderr": stderr,
                            "stdout": stdout,
                            "test": generated_test,
                        }
                        self.failed_test_runs.append(
                            {
                                "code": fail_details["test"],
                                "error_message": "did not increase code coverage",
                            }
                        )  # Append failure details to the list

                        if 'WANDB_API_KEY' in os.environ:
                            root_span = Trace(
                                name="fail_details_"+datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S"),
                                kind="llm",  # kind can be "llm", "chain", "agent" or "tool
                                inputs={"test_code": fail_details["test"]},
                                outputs=fail_details)
                            root_span.log(name='inference')

                        return fail_details
                except Exception as e:
                    # Handle errors gracefully
                    self.logger.error(f"Error during coverage verification: {e}")
                    # Optionally, roll back even in case of error
                    with open(self.loadgen_module_file_path, "w") as test_file:
                        test_file.write(original_content)
                    fail_details = {
                        "status": "FAIL",
                        "reason": "Runtime error",
                        "exit_code": exit_code,
                        "stderr": stderr,
                        "stdout": stdout,
                        "test": generated_test,
                    }
                    self.failed_test_runs.append(
                        {
                            "code": fail_details["test"],
                            "error_message": "coverage verification error",
                        }
                    )  # Append failure details to the list
                    return fail_details

                # If everything passed and coverage increased, update current coverage and log success
                self.current_coverage = new_percentage_covered
                self.logger.info(
                    f"Test passed and coverage increased. Current coverage: {round(new_percentage_covered * 100, 2)}%"
                )
                return {
                    "status": "PASS",
                    "reason": "",
                    "exit_code": exit_code,
                    "stderr": stderr,
                    "stdout": stdout,
                    "test": generated_test,
                }
        except Exception as e:
            self.logger.error(f"Error validating test: {e}")
            return {
                "status": "FAIL",
                "reason": f"Error validating test: {e}",
                "exit_code": None,
                "stderr": str(e),
                "stdout": "",
                "test": generated_test,
            }


def extract_error_message_python(fail_message):
    try:
        # Define a regular expression pattern to match the error message
        MAX_LINES = 20
        pattern = r"={3,} FAILURES ={3,}(.*?)(={3,}|$)"
        match = re.search(pattern, fail_message, re.DOTALL)
        if match:
            err_str = match.group(1).strip("\n")
            err_str_lines = err_str.split("\n")
            if len(err_str_lines) > MAX_LINES:
                # show last MAX_lines lines
                err_str = "...\n" + "\n".join(err_str_lines[-MAX_LINES:])
            return err_str
        return ""
    except Exception as e:
        logging.error(f"Error extracting error message: {e}")
        return ""
