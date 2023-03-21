import logging
import re
import tempfile
from typing import Union, Any, Dict, List, Optional

from git import GitCommandError

from guardrails import register_validator, Validator
from guardrails.validators import EventDetail
import git

logger = logging.getLogger(__name__)


def fix_unidiff_line_counts(lines: list[str]) -> list[str]:
    # TODO also fix unidiff line numbers
    corrected_lines = []

    for i, line in enumerate(lines):
        if line.startswith("@@"):
            # Extract the original x and y values
            match = re.match(r"@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@", line)
            start_x, start_y = int(match.group(1)), int(match.group(2))

            # Calculate the correct y values based on the hunk content
            x_count, y_count = 0, 0
            j = i + 1
            while j < len(lines):
                # Check if the next hunk is detected
                if (
                    j + 2 < len(lines) and
                    lines[j].startswith("---") and
                    lines[j + 1].startswith("+++") and
                    lines[j + 2].startswith("@@")
                ) or lines[j].startswith("@@"):
                    break

                if lines[j].startswith("-"):
                    x_count += 1
                elif lines[j].startswith("+"):
                    y_count += 1
                elif not lines[j].startswith("\\"):
                    x_count += 1
                    y_count += 1

                j += 1

            # Update the @@ line with the correct y values
            corrected_line = f"@@ -{start_x},{x_count - 1} +{start_y},{y_count - 1} @@"
            corrected_lines.append(corrected_line)
        else:
            corrected_lines.append(line)

    return corrected_lines


def adjust_line_indentation(line: str, indentation_offset: int) -> str:
    if indentation_offset >= 0:
        return indentation_offset * ' ' + line
    else:
        return line[-indentation_offset:]


def remove_hallucinations(lines: List[str], tree: git.Tree) -> List[str]:
    cleaned_lines: list[str] = []
    current_file_content: Optional[list[str]] = None
    current_line_number: int = 0
    search_range: int = 3
    first_line_semaphore: int = 0
    indentation_offset: int = 0
    is_new_file: bool = False

    for i, line in enumerate(lines):
        first_line_semaphore = max(0, first_line_semaphore - 1)
        if line.startswith("---") and lines[i + 1].startswith("+++") and lines[i + 2].startswith("@@"):  # hunk header
            is_new_file = False

            # Extract the filename after ---
            filepath_match = re.match(r"--- (.+)", line)
            filepath = filepath_match.group(1)

            # Get the file content
            try:
                blob = tree / filepath
                current_file_content = blob.data_stream.read().decode().splitlines()
            except KeyError:
                is_new_file = True
                current_file_content = None
                current_line_number = 0

            cleaned_lines.append(line)
        elif line.startswith("@@"):  # line count (hunk header 3/3)
            current_line_number = int(re.match(r"@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@", line).group(1)) - 1
            cleaned_lines.append(line)
            indentation_offset = 0
            first_line_semaphore = 2
        elif line.startswith("+++"):  # filename (hunk header 2/2)
            cleaned_lines.append(line)
        elif line.startswith("-"):  # remove line
            if is_new_file:
                continue
            line_content = line[1:]
            if current_line_number >= len(current_file_content):
                continue
            file_line = current_file_content[current_line_number]
            # Put the right line into the diff
            cleaned_lines.append(f"-{file_line}")
            current_line_number += 1
            if line_content.lstrip() != file_line.lstrip():
                continue
            if (
                line_content != file_line and
                line_content.lstrip() == file_line.lstrip()
            ):
                # Fix indentation also in + lines
                real_indentation = len(file_line) - len(file_line.lstrip())
                hallucinated_indentation = len(line_content) - len(line_content.lstrip())
                indentation_offset = real_indentation - hallucinated_indentation
        elif line.startswith("+"):  # new line
            cleaned_lines.append(f"+{adjust_line_indentation(line[1:], indentation_offset)}")
        elif line.lstrip() != line:  # context line
            # Line has a leading whitespace, check if it's in the actual file content
            if is_new_file or current_line_number >= len(current_file_content):
                continue
            file_line = current_file_content[current_line_number]
            if line.lstrip() == file_line.lstrip():
                # If indentation is wrong, use that
                if indentation_offset:
                    cleaned_lines.append(f" {adjust_line_indentation(line[1:], indentation_offset)}")
                else:  # Else, use the real line
                    cleaned_lines.append(f" {file_line}")
                current_line_number += 1
            elif first_line_semaphore:
                # Search for the line in the file content
                for offset in range(-search_range, search_range + 1):
                    check_line_number = current_line_number + offset
                    check_file_line = current_file_content[check_line_number]
                    if not 0 <= check_line_number < len(current_file_content):
                        continue
                    elif line.lstrip() == check_file_line.lstrip():
                        current_line_number = check_line_number + 1
                        # Fix @@ line
                        cleaned_lines[-1] = f"@@ -{check_line_number + 1},1 +{check_line_number + 1},1 @@"
                        cleaned_lines.append(f' {check_file_line}')
                        break
        else:
            if line:
                print("Unknown line: ", line)
            cleaned_lines.append(line)
            current_line_number += 1

    if cleaned_lines[-1] != "":
        cleaned_lines[-1] = ""
    return cleaned_lines


def create_unidiff_validator(repo: git.Repo, tree: git.Tree):
    class Unidiff(Validator):
        """Validate value is a valid unidiff.
        - Name for `format` attribute: `unidiff`
        - Supported data types: `string`
        """

        def validate(self, key: str, value: Any, schema: Union[Dict, List]) -> Dict:
            logger.debug(f"Validating {value} is unidiff...")

            # try to apply the patch with git apply --check
            with tempfile.NamedTemporaryFile() as f:
                f.write(value.encode())
                f.flush()
                try:
                    repo.git.execute(["git",
                                      "apply",
                                      "--check",
                                      "--unidiff-zero",
                                      "--inaccurate-eof",
                                      "--allow-empty",
                                      f.name])
                except GitCommandError as e:
                    raise EventDetail(
                        key,
                        value,
                        schema,
                        e.stderr,
                        None,
                    )

            return schema

        def fix(self, error: EventDetail) -> Any:
            value = error.value
            lines = value.splitlines()

            # Drop any `diff --git` lines
            lines = [line for line in lines if not line.startswith("diff --git")]

            # Remove whitespace in front of --- lines if it's there
            for i, line in enumerate(lines):
                stripped_line = line.lstrip()
                if stripped_line.startswith("---") and \
                        lines[i + 1].startswith("+++") and \
                        lines[i + 2].startswith("@@"):
                    lines[i] = stripped_line

            # Rename any hunks that start with --- a/ or +++ b/
            for i, line in enumerate(lines):
                if len(lines) < i + 2:
                    break
                if line.startswith("--- a/") and lines[i + 1].startswith("+++ b/"):
                    lines[i] = line.replace("--- a/", "--- ")
                    lines[i + 1] = lines[i + 1].replace("+++ b/", "+++ ")

            # Add space at the start of any line that's empty, except if it precedes a --- line, or is the last line
            for i, line in enumerate(lines):
                if len(lines) < i + 2:
                    break
                if line == "" and not lines[i + 1].startswith("---") and i != len(lines) - 1:
                    lines[i] = " "

            # Ensure the whole thing ends with a newline
            if not lines[-1] == "":
                lines.append("")

            # If there are any +++ @@ lines, without a preceding --- line,
            # add a `--- /dev/null` line before it
            insert_indices: list[int] = []
            for i, line in enumerate(lines):
                if line.startswith("+++ ") and lines[i + 1].startswith('@@ ') and not lines[i - 1].startswith("---"):
                    insert_indices.append(i)
            for i, index in enumerate(insert_indices):
                lines.insert(index + i, "--- /dev/null")

            # Fix filenames, such that in every block of three consecutive --- +++ @@ lines,
            # the filename after +++ matches the filename after ---
            # Except the filename after --- is /dev/null
            for i, line in enumerate(lines):
                if line.startswith("---") and not line.startswith("--- /dev/null"):
                    # Extract the filename after ---
                    filename_match = re.match(r"--- (.+)", line)
                    filename = filename_match.group(1)

                    # Check if the next line starts with +++ and the line after that starts with @@
                    if i + 1 < len(lines) and lines[i + 1].startswith("+++") and \
                            i + 2 < len(lines) and lines[i + 2].startswith("@@"):
                        # Update the next line's filename to match the filename after ---
                        lines[i + 1] = f"+++ {filename}"

            # If the file referenced on --- and +++ lines is not in the repo, replace it with /dev/null
            for i, line in enumerate(lines):
                if line.startswith("---") and lines[i + 1].startswith("+++") and lines[i + 2].startswith("@@"):
                    # Extract the filename after +++
                    filename_match = re.match(r"\+\+\+ (.+)", lines[i + 1])
                    filename = filename_match.group(1)

                    # Check if the file is in the tree
                    try:
                        tree / filename
                    except KeyError:
                        # See if any of the filepaths in the tree end with the filename
                        # If so, use that as the filename
                        for tree_file in tree.traverse():
                            path = tree_file.path
                            if path.endswith(filename):
                                lines[i] = f"--- {path}"
                                lines[i + 1] = f"+++ {path}"
                                break
                        else:
                            lines[i] = f"--- /dev/null"

            # If there is a lone @@ line, prefix it with the --- and +++ lines from the previous block
            current_block: list[str] = []
            insertions: list[tuple[int, list[str]]] = []
            for i, line in enumerate(lines):
                if line.startswith("---") and lines[i + 1].startswith("+++ ") and lines[i + 2].startswith("@@"):
                    current_block = [lines[i], lines[i + 1]]
                if line.startswith("@@") and not lines[i - 1].startswith("+++ "):
                    insertions.append((i, current_block))
            for i, (index, newlines) in enumerate(insertions):
                actual_index = index + i * 2
                lines.insert(actual_index, newlines[0])
                lines.insert(actual_index + 1, newlines[1])

            # Fix filepaths, such that if it starts with a directory with the same name as the repo,
            # the path is prepended with that name again
            repo_name = repo.remotes.origin.url.split('.git')[0].split('/')[-1]
            try:
                tree / repo_name
            except KeyError:
                pass
            else:
                for i, line in enumerate(lines):
                    if line.startswith("---") and lines[i + 1].startswith("+++") and lines[i + 2].startswith("@@"):
                        if lines[i + 1].startswith(f"+++ {repo_name}/"):
                            lines[i] = line.replace(f"--- {repo_name}/", f"--- {repo_name}/{repo_name}/")
                            lines[i + 1] = lines[i + 1].replace(f"+++ {repo_name}/", f"+++ {repo_name}/{repo_name}/")

            # Recalculate the @@ line
            lines = remove_hallucinations(lines, tree)

            # Recalculate the line counts in the unidiff
            lines = fix_unidiff_line_counts(lines)

            value = "\n".join(lines)

            try:
                self.validate(error.key, value, error.schema)
            except EventDetail:
                return super().fix(error)

            error.schema[error.key] = value
            return error.schema

    return register_validator(name="unidiff", data_type="string")(Unidiff)


def create_filepath_validator(tree: git.Tree):
    class FilePath(Validator):
        """Validate value is a valid file path.
        - Name for `format` attribute: `filepath`
        - Supported data types: `string`
        """
        def validate(self, key: str, value: Any, schema: Union[Dict, List]) -> Dict:
            # Check if the filepath exists in the repo
            try:
                blob = tree / value
            except KeyError:
                raise EventDetail(
                    key,
                    value,
                    schema,
                    f"File path '{value}' does not exist in the repo.",
                    None,
                )

            if blob.type != "blob":
                raise EventDetail(
                    key,
                    value,
                    schema,
                    f"File path '{value}' is not a file.",
                    None,
                )

            return schema

    return register_validator(name="filepath", data_type="string")(FilePath)