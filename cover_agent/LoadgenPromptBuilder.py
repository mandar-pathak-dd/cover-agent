import logging
import sys

from jinja2 import Environment, StrictUndefined
from cover_agent.settings.config_loader import get_settings
import os

MAX_TESTS_PER_RUN = 4

# Markdown text used as conditional appends
ADDITIONAL_INCLUDES_TEXT = """
## Additional Includes
The following is a set of included files used as context for the source code above. This is usually included libraries needed as context to write better tests:
======
{included_files}
======
"""

ADDITIONAL_INSTRUCTIONS_TEXT = """
## Additional Instructions
======
{additional_instructions}
======
"""

FAILED_TESTS_TEXT = """
## Previous Iterations Failed Tests
Below is a list of failed tests that you generated in previous iterations. Do not generate the same tests again, and take the failed tests into account when generating new tests.
======
{failed_test_runs}
======
"""


class LoadgenPromptBuilder:

    def __init__(
        self,
        protobuf_definition_path: str,
        loadgen_module_path: str,
        included_files: str = "",
        additional_instructions: str = "",
    ):
        self.protobuf_definition_path = protobuf_definition_path.split("/")[-1]
        self.loadgen_module_path = loadgen_module_path.split("/")[-1]
        self.protobuf_definition = self._read_file(protobuf_definition_path)
        self.loadgen_module = self._read_loadgen_module(loadgen_module_path)
        # add line numbers to each line in 'source_file'. start from 1
        self.protobuf_definition_numbered = "\n".join(
            [f"{i + 1} {line}" for i, line in enumerate(self.protobuf_definition.split("\n"))]
        )
        self.loadgen_module_numbered = "\n".join(
            [f"{i + 1} {line}" for i, line in enumerate(self.loadgen_module.split("\n"))]
        )

        # Conditionally fill in optional sections
        self.included_files = (
            ADDITIONAL_INCLUDES_TEXT.format(included_files=included_files)
            if included_files
            else ""
        )
        self.additional_instructions = (
            ADDITIONAL_INSTRUCTIONS_TEXT.format(
                additional_instructions=additional_instructions
            )
            if additional_instructions
            else ""
        )

    def _read_loadgen_module(self, file_path):
        """
        Helper method to create a loadgen module file if it does not exist.

        Parameters:
            file_path (str): Path to the file to be created.

        Returns:
            str: The content of the file.
        """
        if not os.path.exists(file_path):
            try:
                with open(file_path, "w") as f:
                    f.write("")
            except Exception as e:
                print(f"Error creating file: {e}")
                sys.exit(1)
        return self._read_file(file_path)


    def _read_file(self, file_path):
        """
        Helper method to read file contents.

        Parameters:
            file_path (str): Path to the file to be read.

        Returns:
            str: The content of the file.
        """
        try:
            with open(file_path, "r") as f:
                return f.read()
        except Exception as e:
            return f"Error reading {file_path}: {e}"

    def build_prompt(self) -> dict:
        """
        Replaces placeholders with the actual content of files read during initialization, and returns the formatted prompt.

        Parameters:
            None

        Returns:
            str: The formatted prompt string.
        """
        variables = {
            "protobuf_definition_path": self.protobuf_definition_path,
            "loadgen_module_path": self.loadgen_module_path,
            "protobuf_definition_numbered": self.protobuf_definition_numbered,
            "loadgen_module_numbered": self.loadgen_module_numbered,
            "protobuf_definition": self.protobuf_definition,
            "loadgen_module": self.loadgen_module,
            "additional_includes_section": self.included_files,
            "additional_instructions_text": self.additional_instructions,
        }
        environment = Environment(undefined=StrictUndefined)
        try:
            system_prompt = environment.from_string(
                get_settings().test_generation_prompt.system
            ).render(variables)
            user_prompt = environment.from_string(
                get_settings().test_generation_prompt.user
            ).render(variables)
        except Exception as e:
            logging.error(f"Error rendering prompt: {e}")
            return {"system": "", "user": ""}

        # print(f"#### user_prompt:\n\n{user_prompt}")
        return {"system": system_prompt, "user": user_prompt}

    def build_prompt_custom(self, file) -> dict:
        variables = {
            "protobuf_definition_path": self.protobuf_definition_path,
            "loadgen_module_path": self.loadgen_module_path,
            "protobuf_definition_numbered": self.protobuf_definition_numbered,
            "loadgen_module_numbered": self.loadgen_module_numbered,
            "protobuf_definition": self.protobuf_definition,
            "loadgen_module": self.loadgen_module,
            "additional_includes_section": self.included_files,
            "additional_instructions_text": self.additional_instructions,
        }
        environment = Environment(undefined=StrictUndefined)
        try:
            system_prompt = environment.from_string(
                get_settings().get(file).system
            ).render(variables)
            user_prompt = environment.from_string(get_settings().get(file).user).render(
                variables
            )
        except Exception as e:
            logging.error(f"Error rendering prompt: {e}")
            return {"system": "", "user": ""}

        return {"system": system_prompt, "user": user_prompt}
