from unittest.mock import Mock, MagicMock

import pytest

from guardrails.validators import EventDetail
from autopr.validators import create_unidiff_validator

dockerfile = """FROM duffn/python-poetry:3.9-slim

# Install git
RUN apt-get update && apt-get install -y git

# Set up entrypoint
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Run the app
ENTRYPOINT ["/entrypoint.sh"]"""
correct_dockerfile_unidiff = """--- Dockerfile
+++ Dockerfile
@@ -5,6 +5,8 @@
 
 # Set up entrypoint
 COPY entrypoint.sh /entrypoint.sh
+
+# Make entrypoint executable
 RUN chmod +x /entrypoint.sh
 
 # Run the app
"""
wrong_line_counts_dockerfile_unidiff = """--- Dockerfile
+++ Dockerfile
@@ -5,505 +5,10 @@
 
 # Set up entrypoint
 COPY entrypoint.sh /entrypoint.sh
+
+# Make entrypoint executable
 RUN chmod +x /entrypoint.sh
 
 # Run the app
"""
wrong_line_numbers_dockerfile_unidiff = """--- Dockerfile
+++ Dockerfile
@@ -6,6 +4,8 @@
 
 # Set up entrypoint
 COPY entrypoint.sh /entrypoint.sh
+
+# Make entrypoint executable
 RUN chmod +x /entrypoint.sh
 
 # Run the app
"""
hallucinated_lines_dockerfile_unidiff = """--- Dockerfile
+++ Dockerfile
@@ -5,6 +5,8 @@
 
 # Set up entrypoint
 COPY entrypoint.sh /entrypoint.sh
 HUHU
+
+# Make entrypoint executable
 RUN chmod +x /entrypoint.sh
 
 # Run the app
 HIHI
 HAHA
"""
a_b_filename_dockerfile_unidiff = """--- a/Dockerfile
+++ b/Dockerfile
@@ -5,6 +5,8 @@
 
 # Set up entrypoint
 COPY entrypoint.sh /entrypoint.sh
+
+# Make entrypoint executable
 RUN chmod +x /entrypoint.sh
 
 # Run the app
"""
plusplusplus_name_is_wrong_dockerfile_unidiff = """--- Dockerfile
+++ Dockerfile_new
@@ -5,6 +5,8 @@
 
 # Set up entrypoint
 COPY entrypoint.sh /entrypoint.sh
+
+# Make entrypoint executable
 RUN chmod +x /entrypoint.sh
 
 # Run the app
"""
correct_multisection_dockerfile_unidiff = """--- Dockerfile
+++ Dockerfile
@@ -3,1 +3,2 @@
 # Install git
+
 RUN apt-get update && apt-get install -y git
--- Dockerfile
+++ Dockerfile
@@ -8,3 +8,5 @@
 RUN chmod +x /entrypoint.sh
 
+ Ha
+ Haha
 # Run the app
"""
incorrect_multisection_dockerfile_unidiff = """--- Dockerfile
+++ Dockerfile
@@ -3,0 +3,1 @@
 # Install git
+
 RUN apt-get update && apt-get install -y git
@@ -9,3 +9,5 @@
 RUN chmod +x /entrypoint.sh

+ Ha
+ Haha
 # Run the app
"""

readme = """# Pull Request Drafter Github Action

## Environment Variables

- `GITHUB_TOKEN` - The GitHub token to use for the action. This is automatically provided by GitHub, you do not need to create your own token.
"""

correct_readme_unidiff = """--- README.md
+++ README.md
@@ -1,4 +1,20 @@
-# Pull Request Drafter Github Action
+# Automatic Pull Request Github Action 🎉🚀
 
-## Environment Variables
+## Input Variables
+
+The input variables for this Github Action are documented in `action.yml`. They include:
+
+- `github_token`
+- `openai_api_key`
+- `issue_number`
+- `issue_title`
+- `issue_body`
+- `base_branch`
 
+## Guardrails Library
+
+This Github Action utilizes the guardrails library, which can be found in `generation_service.py` and `validators.py`. The library helps in generating and validating pull requests based on the input variables and the codebase.
+
+## Including the Github Action in Your Repository
+
+To include the Automatic Pull Request Github Action in your own repository, add its configuration to your `.github/workflows` directory. Follow the documentation in `action.yml` for further guidance.
"""

wrong_readme_unidiff = """diff --git a/README.md b/README.md
--- a/README.md
+++ b/README.md
@@ -1,6 +1,18 @@
-# Pull Request Drafter Github Action
+# Automatic Pull Request Github Action 🎉🚀
 
-## Environment Variables
+## Input Variables
+
+The input variables for this Github Action are documented in `action.yml`. They include:
+
+- `github_token`
+- `openai_api_key`
+- `issue_number`
+- `issue_title`
+- `issue_body`
+- `base_branch`
 
+## Guardrails Library
+
+This Github Action utilizes the guardrails library, which can be found in `generation_service.py` and `validators.py`. The library helps in generating and validating pull requests based on the input variables and the codebase.
+
+## Including the Github Action in Your Repository
+
+To include the Automatic Pull Request Github Action in your own repository, add its configuration to your `.github/workflows` directory. Follow the documentation in `action.yml` for further guidance.
"""

new_file_unidiff = """--- /dev/null
+++ README.md
@@ -0,0 +1,4 @@
+# Pull Request Drafter Github Action
+
+## Environment Variables
+ 
"""
missing_minusminusminus_unidiff = """+++ README.md
@@ -0,0 +1,4 @@
+# Pull Request Drafter Github Action
+
+## Environment Variables
+ 
"""

new_lockfile_unidiff = """--- /dev/null
+++ .gptignore
@@ -0,0 +1,1 @@
+*.lock
"""
new_lockfile_incorrect_unidiff = """--- .gptignore
+++ .gptignore_new
@@ -0,0 +1 @@
+*.lock
"""

validators_file = '\n' * 102 + """
    elif first_line:
        # Search for the line in the file content
        for offset in range(-search_range, search_range + 1):
            check_line_number = current_line_number + offset
            check_file_line = current_file_content[check_line_number]
            if 0 <= check_line_number < len(current_file_content) and line[1:] == check_file_line:
                current_line_number = check_line_number + 1
                # Fix @@ line
                cleaned_lines[-1] = f"@@ -{check_line_number + 1},1 +{check_line_number + 1},1 @@"
                cleaned_lines.append(line)
                break
 """
validators_correct_unidiff = """--- autopr/autopr/validators.py
+++ autopr/autopr/validators.py
@@ -106,7 +106,8 @@
         for offset in range(-search_range, search_range + 1):
             check_line_number = current_line_number + offset
-            check_file_line = current_file_content[check_line_number]
-            if 0 <= check_line_number < len(current_file_content) and line[1:] == check_file_line:
+            if 0 <= check_line_number < len(current_file_content):
+                check_file_line = current_file_content[check_line_number]
+                if line[1:] == check_file_line:
                     current_line_number = check_line_number + 1
                     # Fix @@ line
                     cleaned_lines[-1] = f"@@ -{check_line_number + 1},1 +{check_line_number + 1},1 @@"
"""
validators_positive_indendation_offset_unidiff = """--- autopr/validators.py
+++ autopr/validators.py
@@ -105,8 +105,9 @@
     for offset in range(-search_range, search_range + 1):
         check_line_number = current_line_number + offset
-        check_file_line = current_file_content[check_line_number]
-        if 0 <= check_line_number < len(current_file_content) and line[1:] == check_file_line:
+        if 0 <= check_line_number < len(current_file_content):
+            check_file_line = current_file_content[check_line_number]
+            if line[1:] == check_file_line:
                 current_line_number = check_line_number + 1
                 # Fix @@ line
                 cleaned_lines[-1] = f"@@ -{check_line_number + 1},1 +{check_line_number + 1},1 @@"
"""
validators_negative_indendation_offset_unidiff = """--- autopr/validators.py
+++ autopr/validators.py
@@ -105,8 +105,9 @@
             for offset in range(-search_range, search_range + 1):
                 check_line_number = current_line_number + offset
-                check_file_line = current_file_content[check_line_number]
-                if 0 <= check_line_number < len(current_file_content) and line[1:] == check_file_line:
+                if 0 <= check_line_number < len(current_file_content):
+                    check_file_line = current_file_content[check_line_number]
+                    if line[1:] == check_file_line:
                         current_line_number = check_line_number + 1
                         # Fix @@ line
                         cleaned_lines[-1] = f"@@ -{check_line_number + 1},1 +{check_line_number + 1},1 @@"
"""
validators_mixed_indentation_offset_unidiff = """--- autopr/validators.py
+++ autopr/validators.py
@@ -105,8 +105,9 @@
                    for offset in range(-search_range, search_range + 1):
  check_line_number = current_line_number + offset
-        check_file_line = current_file_content[check_line_number]
-        if 0 <= check_line_number < len(current_file_content) and line[1:] == check_file_line:
+        if 0 <= check_line_number < len(current_file_content):
+            check_file_line = current_file_content[check_line_number]
+            if line[1:] == check_file_line:
                 current_line_number = check_line_number + 1
                 # Fix @@ line
                 cleaned_lines[-1] = f"@@ -{check_line_number + 1},1 +{check_line_number + 1},1 @@"
"""



@pytest.mark.parametrize(
    "cases, file_contents, correct_unidiff",
    [
        (
            [
                (
                    "Unidiff line counts are wrong",
                    wrong_line_counts_dockerfile_unidiff,
                ),
                (
                    "Unidiff line numbers are wrong",
                    wrong_line_numbers_dockerfile_unidiff,
                ),
                (
                    "Unidiff contains hallucinated lines",
                    hallucinated_lines_dockerfile_unidiff,
                ),
                (
                    "Unidiff contains a/b filenames",
                    a_b_filename_dockerfile_unidiff,
                ),
                (
                    "+++ name is wrong",
                    plusplusplus_name_is_wrong_dockerfile_unidiff,
                ),
            ],
            dockerfile,
            correct_dockerfile_unidiff,
        ),
        (
            [
                (
                    "multisection does not have headers for each hunk",
                    incorrect_multisection_dockerfile_unidiff,
                ),
            ],
            dockerfile,
            correct_multisection_dockerfile_unidiff,
        ),
        (
            [
                (
                    "Unidiff contains git --diff line",
                    wrong_readme_unidiff,
                ),
            ],
            readme,
            correct_readme_unidiff,
        ),
        (
            [
                (
                    "Unidiff is missing ---",
                    missing_minusminusminus_unidiff,
                ),
            ],
            "",
            new_file_unidiff,
        ),
        (
            [
                (
                    "Unidiff contains incorrect filepaths",
                    new_lockfile_incorrect_unidiff,
                ),
            ],
            "",
            new_lockfile_unidiff,
        ),
        (
            [
                (
                    "Unidiff contains not enough leading spaces",
                    validators_positive_indendation_offset_unidiff,
                ),
                (
                    "Unidiff contains too many leading spaces",
                    validators_negative_indendation_offset_unidiff,
                ),
                (
                    "Unidiff contains mixed leading spaces",
                    validators_mixed_indentation_offset_unidiff,
                ),
            ],
            validators_file,
            validators_correct_unidiff,
        ),
    ],
)
def test_unidiff_fix(subtests, file_contents: str, correct_unidiff: str, cases: list[tuple[str, str]]) -> None:
    """Test that the unidiff_fix function fixes unidiffs."""
    mock_repo = MagicMock()
    mock_tree = MagicMock()
    mock_blob = MagicMock()
    mock_blob.data_stream.read.return_value = file_contents.encode()

    # Make sure gptignore does not exist
    def truediv_side_effect(path):
        if path == '.gptignore':
            raise KeyError('.gptignore not found')
        return mock_blob
    mock_tree.__truediv__.side_effect = truediv_side_effect

    # Make this return autopr (repo.remotes.origin.url.split('.git')[0].split('/')[-1])
    mock_repo.remotes.origin.url = '/autopr.git'
    validator_class = create_unidiff_validator(mock_repo, mock_tree)
    validator = validator_class(on_fail="fix")
    for reason, corrupted_unidiff in cases:
        with subtests.test(msg=reason):
            correct_schema = {"diff": correct_unidiff}
            corrupted_schema = {"diff": corrupted_unidiff}
            error = EventDetail(
                "diff",
                corrupted_unidiff,
                corrupted_schema,
                "",
                None,
            )
            fixed_schema = validator.fix(error)
            print(fixed_schema['diff'])
            assert fixed_schema['diff'] == correct_schema['diff']