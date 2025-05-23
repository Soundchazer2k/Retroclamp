"""Fix indentation in compression_tab.py."""

import re

# Read the file
with open("gui/compression_tab.py", encoding="utf-8") as f:
    lines = f.readlines()

# Check for class definition to determine the base indentation level
class_line_idx = None
for i, line in enumerate(lines):
    if line.strip().startswith("class CompressionTab"):
        class_line_idx = i
        break

if class_line_idx is None:
    print("Error: Could not find CompressionTab class")
    exit(1)

# Process the file - normalize indentation
result_lines = []
indent_level = 0
class_indent = 0  # Indentation of the class definition

for i, line in enumerate(lines):
    stripped = line.lstrip()

    # Skip empty lines
    if not stripped:
        result_lines.append("\n")
        continue

    # Determine indentation based on pattern
    if stripped.startswith("class "):
        indent_level = 0
    elif re.match(r"\s*def\s+\w+\s*\(", line):
        # Method definition - should be indented 4 spaces from class
        indent_level = 1
    elif i > 0 and lines[i - 1].strip().endswith(":"):
        # Line after a colon should be more indented
        prev_indent = len(lines[i - 1]) - len(lines[i - 1].lstrip())
        indent_level = prev_indent // 4 + 1

    # Apply indentation
    indent = " " * (4 * indent_level)
    result_lines.append(f"{indent}{stripped}")

# Write the corrected file
with open("gui/compression_tab.py.fixed", "w", encoding="utf-8") as f:
    f.writelines(result_lines)

print("Indentation fixed. Results written to gui/compression_tab.py.fixed")
