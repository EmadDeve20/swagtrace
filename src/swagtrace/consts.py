DEFAULT_YAML_FILE = "swagtrace.yaml"

DEFAULT_TEST_MODULE_FOLDER = "swagtrace_tests"

PREPARE_AND_FINAL_FORMAT_FILE  = """# 1. Configuration & Variables
# Define key-value pairs to be injected into the YAML template.
# You can set static values here or dynamically update this dictionary inside prepare().
# NOTE: Variable names (keys) are CASE-SENSITIVE (e.g., 'DB_PORT' != 'db_port').
VARIABLES = {}


# 2. Preparation Phase
# This function runs FIRST. Use it to perform any setup, fetch dynamic data,
# or modify the 'VARIABLES' dictionary before the YAML file is generated.
# Tip: Modify the dictionary directly (e.g., VARIABLES['MY_KEY'] = 'value').
def prepare():
    pass


# 3. Main Execution Phase
# This function runs as the FINAL step, right after the 'execute' command in the YAML file has finished.
# Place your core logic or post-processing tasks here.
def main():
    pass

"""


TEST_CASE_FORMAT_FILE = """from httpx import Response

# -----------------------------------------------------------------------------
# 1. CONFIGURATION & DYNAMIC VARIABLES
# -----------------------------------------------------------------------------
# Key-value pairs injected into the HTTP Request template (e.g., YAML/JSON).
# You can define static defaults here or dynamically populate/override them 
# inside the prepare() function.
# NOTE: Variable names (keys) are CASE-SENSITIVE (e.g., 'TOKEN' != 'token').
VARIABLES = %(variables)s


# -----------------------------------------------------------------------------
# 2. PREPARATION PHASE (PHASE 1 - Runs FIRST)
# -----------------------------------------------------------------------------
# Executed BEFORE generating the request template and making the HTTP call.
# Use this to:
# - Set up prerequisites (e.g., seed database, generate mock payload).
# - Fetch authorization tokens or dynamic parameters.
# - Inject values directly into the 'VARIABLES' dictionary.
def prepare():
    pass


# -----------------------------------------------------------------------------
# 3. ASSERTION & INSPECTION PHASE (PHASE 2 - Runs AFTER HTTP Request)
# -----------------------------------------------------------------------------
# Executed IMMEDIATELY after the API call finishes.
# Receives the live 'requests.Response' object from the target server.
# Use this to:
# - Write custom asserts (e.g., assert response.status_code == 200).
# - Parse response JSON/Headers and validate domain logic.
# - Store state/IDs created by this request for downstream use.
def main(response: Response):
    pass


# -----------------------------------------------------------------------------
# 4. CLEANUP & TEARDOWN PHASE (PHASE 3 - Runs LAST)
# -----------------------------------------------------------------------------
# Executed as the final step after main() completes.
# Use this optional step to clean up any side-effects or temporary data:
# - Delete objects created in database/API during the test execution.
# - Invalidate session tokens or flush temporary test state.
def finalize():
    pass

"""

