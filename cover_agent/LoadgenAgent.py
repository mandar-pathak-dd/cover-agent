import datetime
import os
import shutil
import sys
import wandb

from cover_agent.CustomLogger import CustomLogger
from cover_agent.LoadgenTestGenerator import LoadgenTestGenerator
from cover_agent.ReportGenerator import ReportGenerator
from cover_agent.UnitTestGenerator import UnitTestGenerator


class LoadgenAgent:
    def __init__(self, args):
        self.args = args
        self.logger = CustomLogger.get_logger(__name__)

        self.loadgen_test_gen = LoadgenTestGenerator(
            protobuf_definition_file = args.protobuf_definition_path,
            loadgen_module_file_path = args.loadgen_module_file_path,
            llm_model = args.model,
            api_base = args.api_base,
            loadgen_command = args.loadgen_test_command,
            loadgen_command_dir = args.loadgen_test_command_dir,
            included_files = args.included_files,
            additional_instructions = args.additional_instructions,
        )

    def run(self):
        self.__generate_loadgen_tests()

    def __generate_loadgen_tests(self):
        self.loadgen_test_gen.generate_tests()
        sys.exit(0)
