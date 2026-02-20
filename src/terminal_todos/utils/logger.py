"""Logging utilities for Terminal Todos."""

import sys
import traceback
from datetime import datetime
from pathlib import Path
from typing import Optional

from terminal_todos.config import get_settings


# Error log file path
def get_error_log_path() -> Path:
    """Get the path to the error log file."""
    settings = get_settings()
    log_path = settings.data_dir / "error.log"
    return log_path


def log_to_file(message: str, level: str = "ERROR"):
    """
    Write a log message to the error log file.

    Args:
        message: The message to log
        level: Log level (ERROR, DEBUG, INFO, WARNING)
    """
    try:
        log_path = get_error_log_path()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"\n{'=' * 80}\n")
            f.write(f"[{timestamp}] {level}\n")
            f.write(f"{'=' * 80}\n")
            f.write(message)
            f.write(f"\n{'=' * 80}\n\n")
    except Exception as e:
        # Fallback to stderr if file logging fails
        print(f"Failed to write to error log: {e}", file=sys.stderr)


def log_error(error: Exception, context: str = "", show_traceback: bool = True) -> str:
    """
    Log an error with optional verbose details.

    Args:
        error: The exception that occurred
        context: Additional context about where/why the error occurred
        show_traceback: Whether to include full traceback

    Returns:
        Formatted error message string
    """
    settings = get_settings()

    # Basic error message
    error_msg = str(error)
    error_type = type(error).__name__

    # Build detailed log message
    log_message = f"Context: {context or 'An error occurred'}\n"
    log_message += f"Exception Type: {error_type}\n"
    log_message += f"Exception Message: {error_msg}\n"

    if show_traceback:
        log_message += "\nFull Traceback:\n"
        log_message += traceback.format_exc()

    # ALWAYS log to file regardless of verbose setting
    log_to_file(log_message, level="ERROR")

    if settings.verbose_logging:
        # Verbose mode: also print detailed information to stderr
        print("\n" + "=" * 80, file=sys.stderr)
        print(f"❌ ERROR: {context or 'An error occurred'}", file=sys.stderr)
        print("=" * 80, file=sys.stderr)
        print(f"Exception Type: {error_type}", file=sys.stderr)
        print(f"Exception Message: {error_msg}", file=sys.stderr)

        if show_traceback:
            print("\nFull Traceback:", file=sys.stderr)
            print("-" * 80, file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
            print("-" * 80, file=sys.stderr)

        print("=" * 80 + "\n", file=sys.stderr)

        # Return detailed message for UI
        return f"{context}: {error_type}: {error_msg}"
    else:
        # Non-verbose mode: just return basic error
        return f"{context}: {error_msg}" if context else error_msg


def log_debug(message: str, details: Optional[dict] = None) -> None:
    """
    Log a debug message (only shown in verbose mode).

    Args:
        message: The debug message
        details: Optional dictionary of additional details
    """
    settings = get_settings()

    # Build log message
    log_message = f"DEBUG: {message}\n"
    if details:
        for key, value in details.items():
            log_message += f"  - {key}: {value}\n"

    # Log to file
    log_to_file(log_message, level="DEBUG")

    if settings.verbose_logging:
        print(f"🔍 DEBUG: {message}", file=sys.stderr)

        if details:
            for key, value in details.items():
                print(f"  - {key}: {value}", file=sys.stderr)


def log_info(message: str) -> None:
    """
    Log an informational message (only shown in verbose mode).

    Args:
        message: The info message
    """
    settings = get_settings()

    # Log to file
    log_to_file(f"INFO: {message}", level="INFO")

    if settings.verbose_logging:
        print(f"ℹ️  INFO: {message}", file=sys.stderr)


def get_full_traceback() -> str:
    """
    Get the full traceback as a string.

    Returns:
        Formatted traceback string
    """
    return traceback.format_exc()
