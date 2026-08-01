DEFAULT_YAML_FILE = "swagtrace.yaml"

DEFAULT_TEST_MODULE_FOLDER = "swagtrace_tests"

prepare_AND_FINAL_FORMAT_FILE = """# 1. Configuration & Variables
# Define key-value pairs to be injected into the YAML template.
# You can set static values here or dynamically update this dictionary inside prepper().
# NOTE: Variable names (keys) are CASE-SENSITIVE (e.g., 'DB_PORT' != 'db_port').
VARIABLES = {}


# 2. Preparation Phase
# This function runs FIRST. Use it to perform any setup, fetch dynamic data,
# or modify the 'VARIABLES' dictionary before the YAML file is generated.
# Tip: Modify the dictionary directly (e.g., VARIABLES['MY_KEY'] = 'value').
def prepper():
    pass


# 3. Main Execution Phase
# This function runs as the FINAL step, right after the 'execute' command in the YAML file has finished.
# Place your core logic or post-processing tasks here.
def main():
    pass

"""

