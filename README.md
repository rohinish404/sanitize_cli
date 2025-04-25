# Sanitize Comments CLI

[![PyPI version](https://badge.fury.io/py/sanitize-comments-cli.svg)](https://badge.fury.io/py/sanitize-comments-cli) <!-- Optional: Add PyPI version badge after first release -->
<!-- [![Build Status](https://travis-ci.org/your-username/sanitize-comments.svg?branch=main)](https://travis-ci.org/your-username/sanitize-comments) --> <!-- Optional: Add CI badge if you set it up -->
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT) <!-- Optional: Add License badge -->

A fast command-line tool to recursively remove comments from source code files within a directory. It uses the `Pygments` library for accurate language detection and comment tokenization, making it significantly more robust than simple regex solutions.

The goal is to help clean up codebases by removing potentially distracting or outdated comments, especially before distribution or analysis, while minimizing the risk of corrupting the actual code.

**⚠️ WARNING: USE WITH EXTREME CAUTION! ⚠️**

> This tool modifies your source files directly!
>
> *   **Potential for Errors:** While `Pygments` is robust, extremely complex or non-standard code syntax might confuse the tokenizer in rare edge cases, potentially leading to incorrect modifications.
> *   **Version Control Essential:** **ALWAYS** use this tool on projects managed with version control (like **Git**). Commit or stash your changes *before* running `sanitize`.
> *   **Review Changes:** Carefully review the changes made by the tool using `git diff` or similar **before** committing the results.
> *   **Use Backups:** The `--backup` flag is **highly recommended**. It creates backups of modified files in a `.sanitize_backups` directory.
> *   **Dry Run First:** Always perform a `--dry-run` first to see which files *would* be modified without actually changing them.
> *   **Skipped Files:** Files for which `Pygments` does not have a suitable lexer (tokenizer) will be skipped automatically to avoid errors.

## Features

*   Removes single-line (`#`, `//`, etc.) and multi-line (`/* ... */`, etc.) comments.
*   Uses `Pygments` for language detection and accurate tokenization.
*   Handles comment markers safely, even when they appear inside strings or other code constructs.
*   Preserves shebang lines (`#!/usr/bin/env python3`).
*   Recursively processes files in a directory.
*   Supports a wide range of languages (any language known to Pygments).
*   Configurable file extensions and exclusions.
*   Optional backups of original files in a dedicated `.sanitize_backups` directory.
*   Dry run mode to preview changes.

## Installation

Requires **Python 3.8+** and `pipx`.

```bash
pipx install sanitize-comments-cli


# Show help message and all options
sanitize --help

# 1. Recommended: Dry run to see potential changes (verbose output)
sanitize --dry-run --verbose .

# 2. Run with backups (creates backups in ./.sanitize_backups/)
sanitize --backup .

# 3. Review changes with Git BEFORE committing
git status
git diff path/to/changed/file.js # Review individual files

# --- Common Options ---

# Specify a different target directory
sanitize --backup ./src

# Process only specific file types (e.g., Python and JavaScript)
sanitize -e .py .js --backup .

# Exclude specific directories (e.g., build artifacts, vendor libs)
# Note: Common ones like .git, node_modules, venv are excluded by default
sanitize --exclude-dirs build dist generated --backup .

# Exclude specific files
sanitize --exclude-files config.js legacy_code.py --backup .

# Run without backups (Use ONLY if you have reliable version control!)
# sanitize .