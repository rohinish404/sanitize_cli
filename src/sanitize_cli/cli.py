
import os
import argparse
import sys
import shutil
from pathlib import Path
import time

try:
    import pygments
    import pygments.lexers
    import pygments.token
    import pygments.util
except ImportError:
    print("Error: The 'Pygments' library is required. Please install it:", file=sys.stderr)
    print("pip install Pygments", file=sys.stderr)
    sys.exit(1)

DEFAULT_BACKUP_DIR_NAME = ".sanitize_backups"

DEFAULT_EXCLUDE_DIRS = [
    ".git", ".svn", "node_modules", "__pycache__", "venv", ".venv",
    "build", "dist", "target", "out",
    DEFAULT_BACKUP_DIR_NAME 
]

def remove_comments_with_pygments(content: str, filename: str) -> tuple[str, bool, int]:
    """
    Removes comments from the given text content using Pygments tokenization.
    (This function remains the same as the previous robust version)

    Returns:
        tuple(modified_content: str, was_modified: bool, chars_removed: int)
    """
    original_length = len(content)
    try:
        lexer = pygments.lexers.get_lexer_for_filename(filename, stripnl=False, stripall=False)
    except pygments.util.ClassNotFound:
        return content, False, 0
    except Exception as e:
        print(f"Warning: Could not get Pygments lexer for {filename}: {e}", file=sys.stderr)
        return content, False, 0

    new_content_parts = []
    first_token = True
    modified = False

    try:
        for ttype, tvalue in lexer.get_tokens(content):
            is_shebang = (
                first_token and
                ttype in pygments.token.Comment.Preproc and
                tvalue.startswith("#!")
            )

            if ttype in pygments.token.Comment and not is_shebang:
                modified = True
                continue 

            new_content_parts.append(tvalue)
            first_token = False

        if not modified:
            return content, False, 0 

        modified_content = "".join(new_content_parts)

        lines = modified_content.splitlines()
        non_empty_lines = []
        consecutive_blank_lines = 0
        for line in lines:
            if line.strip():
                non_empty_lines.append(line)
                consecutive_blank_lines = 0
            else:
                consecutive_blank_lines += 1
                if consecutive_blank_lines <= 1:
                    non_empty_lines.append(line)

        modified_content = '\n'.join(non_empty_lines)

        if modified_content and not modified_content.endswith('\n'):
            modified_content += '\n'
        elif not modified_content.strip():
             modified_content = ""

        removed_count = original_length - len(modified_content)
        final_modified_flag = (removed_count != 0)

        return modified_content, final_modified_flag, removed_count

    except Exception as e:
        print(f"Error processing tokens for {filename}: {e}", file=sys.stderr)
        return content, False, 0

def process_file(
    file_path: Path,
    target_dir: Path, 
    args: argparse.Namespace
) -> bool:
    """
    Processes a single file: reads, removes comments, writes back.
    Backups are now placed in a structured way within '.sanitize_backups'.
    """
    try:
        
        try:
            content_bytes = file_path.read_bytes()
            try:
                original_content = content_bytes.decode('utf-8')
                detected_encoding = 'utf-8'
            except UnicodeDecodeError:
                original_content = content_bytes.decode('latin-1')
                detected_encoding = 'latin-1'
                if args.verbose:
                    print(f"  Info: Used fallback encoding 'latin-1' for {file_path.relative_to(target_dir)}", file=sys.stderr)
        except Exception as e:
            print(f"Error reading file {file_path.relative_to(target_dir)}: {e}", file=sys.stderr)
            return False

        modified_content, was_modified, chars_removed = remove_comments_with_pygments(
            original_content, str(file_path)
        )

        if was_modified:
            relative_path = file_path.relative_to(target_dir) 

            if args.dry_run:
                print(f"[DRY RUN] Would modify: {relative_path} ({chars_removed} chars removed)")
                return True

            backup_path = None 
            if args.backup:
                
                backup_root = target_dir / DEFAULT_BACKUP_DIR_NAME
                
                backup_path = backup_root / relative_path.with_suffix(file_path.suffix + ".bak")
                
                backup_dir_for_file = backup_path.parent
                try:
                    backup_dir_for_file.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(file_path, backup_path) 
                    if args.verbose:
                        
                        backup_display_path = backup_path.relative_to(target_dir)
                        print(f"  Backed up: {relative_path} -> {backup_display_path}")
                except Exception as e:
                    print(f"Error creating backup for {relative_path} at {backup_path}: {e}", file=sys.stderr)
                    if not args.force_unsafe:
                         print("  Aborting modification due to backup failure. Use --force-unsafe to proceed.", file=sys.stderr)
                         return False

            try:
                file_path.write_text(modified_content, encoding=detected_encoding)
                if not args.quiet:
                    print(f"Sanitized: {relative_path} ({chars_removed} chars removed)")
                return True
            except Exception as e:
                print(f"Error writing modified file {relative_path}: {e}", file=sys.stderr)
                
                if args.backup and backup_path and backup_path.exists(): 
                    try:
                        
                        shutil.move(str(backup_path), str(file_path))
                        backup_display_path = backup_path.relative_to(target_dir)
                        print(f"  Restored original file from backup due to write error: {relative_path} (from {backup_display_path})", file=sys.stderr)
                    except Exception as restore_e:
                         print(f"  CRITICAL: Failed to write AND failed to restore backup for {relative_path}: {restore_e}", file=sys.stderr)
                return False
        else:
            
            if args.verbose:
                 try:
                    pygments.lexers.get_lexer_for_filename(str(file_path))
                    print(f"Skipped (no comments found): {file_path.relative_to(target_dir)}")
                 except pygments.util.ClassNotFound:
                    print(f"Skipped (no Pygments lexer found): {file_path.relative_to(target_dir)}")
                 except Exception:
                     print(f"Skipped (lexer issue): {file_path.relative_to(target_dir)}")
            return False

    except Exception as e:
        print(f"Error processing file {file_path.name}: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return False

def main():
    parser = argparse.ArgumentParser(
        description="Recursively remove comments from source files using Pygments tokenization.",
        epilog="""WARNING: While more robust than regex, tokenization might still have edge cases.
        ALWAYS use this on code under version control (Git) and review changes carefully.
        Files without a corresponding Pygments lexer will be skipped."""
    )
    parser.add_argument(
        "directory",
        nargs="?",
        default=".",
        help="The target directory to sanitize (default: current directory)."
    )
    parser.add_argument(
        "-e", "--extensions",
        nargs="+",
        help=(f"List of file extensions (including dot, e.g., .py .js) to process. "
              f"If omitted, attempts to process files Pygments recognizes based on filename.")
    )
    parser.add_argument(
        "--exclude-dirs",
        nargs="+",
        
        default=DEFAULT_EXCLUDE_DIRS,
        help="List of directory names to exclude (case-sensitive)."
    )
    parser.add_argument(
        "--exclude-files",
        nargs="+",
        default=[],
        help="List of specific file names to exclude (case-sensitive)."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show which files would be modified without actually changing them."
    )
    parser.add_argument(
        "--backup",
        action="store_true",
        
        help=f"Create a backup of each modified file in a '{DEFAULT_BACKUP_DIR_NAME}' subdirectory, preserving the original structure."
    )
    parser.add_argument(
        "--force-unsafe",
        action="store_true",
        help="Continue modifying files even if backup creation fails (USE WITH CAUTION!)."
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Print verbose output, including skipped files and backups."
    )
    parser.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="Suppress output except for errors."
    )

    args = parser.parse_args()

    target_dir = Path(args.directory).resolve()
    if not target_dir.is_dir():
        print(f"Error: Directory not found: {target_dir}", file=sys.stderr)
        sys.exit(1)

    if args.quiet and args.verbose:
        args.verbose = False
    if args.quiet and args.dry_run:
         print("Warning: --quiet and --dry-run are mutually exclusive...", file=sys.stderr)

    extensions_to_process = None
    if args.extensions:
        extensions_to_process = set(
            f".{ext.lstrip('.').lower()}" for ext in args.extensions
        )

    excluded_dirs = set(args.exclude_dirs)
    excluded_files = set(args.exclude_files)

    if not args.quiet:
        print(f"Starting comment removal in: {target_dir}")
        print(f"Using Pygments version: {pygments.__version__}")
        if not extensions_to_process:
            print("Processing files recognized by Pygments (no specific extensions provided).")
        else:
             print(f"Processing specific extensions: {' '.join(sorted(list(extensions_to_process)))}")
        if args.dry_run:
            print("--- DRY RUN MODE ---")
        if args.backup:
            print(f"--- Backup enabled (files in {target_dir / DEFAULT_BACKUP_DIR_NAME}) ---")

    modified_count = 0
    processed_count = 0
    skipped_no_lexer_count = 0
    skipped_other_count = 0
    error_count = 0
    start_time = time.time()

    for file_path in target_dir.rglob('*'):
        relative_path_str = str(file_path.relative_to(target_dir)) 

        is_excluded = False
        for excluded_dir in excluded_dirs:
            
            if excluded_dir in file_path.relative_to(target_dir).parts:
                 is_excluded = True
                 break
            
        if is_excluded:
            if args.verbose:
                print(f"Skipped (in excluded dir): {relative_path_str}")
            skipped_other_count += 1
            continue

        if file_path.is_file():
            if file_path.name in excluded_files:
                if args.verbose:
                     print(f"Skipped (excluded file): {relative_path_str}")
                skipped_other_count += 1
                continue

            should_process = False
            if extensions_to_process:
                if file_path.name in extensions_to_process or file_path.suffix.lower() in extensions_to_process:
                     should_process = True
            else:
                 should_process = True 

            if should_process:
                 processed_count += 1
                 try:
                     
                     was_modified_or_would_be = process_file(file_path, target_dir, args)
                     
                     if was_modified_or_would_be:
                          modified_count += 1
                     elif not was_modified_or_would_be:
                          try:
                              pygments.lexers.get_lexer_for_filename(str(file_path))
                          except pygments.util.ClassNotFound:
                              skipped_no_lexer_count +=1
                          except Exception: pass 
                 except Exception as e:
                      print(f"FATAL ERROR during processing dispatch for {relative_path_str}: {e}", file=sys.stderr)
                      error_count += 1
            else:
                if args.verbose:
                     print(f"Skipped (extension not specified): {relative_path_str}")
                skipped_other_count += 1

    end_time = time.time()
    duration = end_time - start_time
    if not args.quiet:
        print("\n--- Summary ---")
        print(f"Processing Time: {duration:.2f} seconds") 
        print(f"Files Scanned (matching criteria): {processed_count}")
        if args.dry_run:
             print(f"Files that WOULD be modified: {modified_count}")
        else:
             print(f"Files Modified: {modified_count}")
        print(f"Files Skipped (no lexer found): {skipped_no_lexer_count}")
        print(f"Files Skipped (excluded/extension mismatch): {skipped_other_count}")
        if error_count > 0:
             print(f"Errors Encountered: {error_count}")
        print("------ Done ------")
        
        if modified_count > 0 and not args.dry_run:
             print(f"\nRECOMMENDATION: Review changes ('git status', 'git diff') and check backups in '{DEFAULT_BACKUP_DIR_NAME}'.") 
        elif not args.dry_run and modified_count == 0 and processed_count > 0:
             print("\nNo comments matching Pygments definitions were found and removed in processed files.")
        elif processed_count == 0:
             print("\nNo files were processed. Check criteria or specify extensions with -e.")

if __name__ == "__main__":
    main()
