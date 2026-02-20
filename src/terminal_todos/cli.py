"""Command-line interface for Terminal Todos."""

import os
import sys

# CRITICAL: Disable tqdm progress bars BEFORE any other imports
# This prevents multiprocessing lock errors in Textual TUI environment
os.environ["TQDM_DISABLE"] = "1"

import click
from datetime import datetime
from pathlib import Path

from terminal_todos import __version__
from terminal_todos.config import get_settings


@click.group()
@click.version_option(version=__version__, prog_name="terminal-todos")
def main():
    """Terminal Todos - AI-powered notes and todo management in your terminal."""
    pass


@main.command()
@click.option(
    "--debug",
    is_flag=True,
    help="Enable debug mode",
)
def run(debug: bool) -> None:
    """Launch the Terminal Todos TUI application."""
    # Verify configuration is loadable
    try:
        settings = get_settings()
        click.echo(f"Data directory: {settings.data_dir}")

        # Check if .env file exists
        if not Path(".env").exists():
            click.echo(
                click.style(
                    "⚠️  Warning: .env file not found. Copy .env.example to .env and add your OPENAI_API_KEY.",
                    fg="yellow",
                ),
                err=True,
            )
            click.echo(f"Create .env file with: OPENAI_API_KEY=your-key-here")
            return

        # Check if API key is set
        if not settings.openai_api_key or settings.openai_api_key == "your-openai-api-key-here":
            click.echo(
                click.style(
                    "⚠️  Error: OPENAI_API_KEY not set in .env file.",
                    fg="red",
                ),
                err=True,
            )
            return

    except Exception as e:
        click.echo(
            click.style(f"❌ Configuration error: {e}", fg="red"),
            err=True,
        )
        sys.exit(1)

    # Launch TUI application
    from terminal_todos.tui.app import run_app

    try:
        run_app()
    except KeyboardInterrupt:
        click.echo("\n👋 Goodbye!")
    except Exception as e:
        click.echo(
            click.style(f"❌ Application error: {e}", fg="red"),
            err=True,
        )
        if debug:
            raise
        sys.exit(1)


@main.command()
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    default=None,
    help="Output ZIP file path (default: terminal-todos-export-TIMESTAMP.zip)",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Show detailed export progress",
)
def export(output: str, verbose: bool) -> None:
    """Export all data to a ZIP file for migration."""
    from terminal_todos.core.export_service import ExportService

    # Generate default filename with timestamp if not provided
    if not output:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output = f"terminal-todos-export-{timestamp}.zip"

    click.echo(f"Exporting data to {output}...")

    try:
        service = ExportService()
        result = service.export_to_zip(output)

        click.echo(click.style("✓ Export successful!", fg="green"))
        click.echo(f"  Todos:  {result['counts']['todos']}")
        click.echo(f"  Notes:  {result['counts']['notes']}")
        click.echo(f"  Emails: {result['counts']['emails']}")
        click.echo(f"  Events: {result['counts']['events']}")
        click.echo(f"\nFile: {result['output_path']}")

    except Exception as e:
        click.echo(click.style(f"✗ Export failed: {e}", fg="red"), err=True)
        if verbose:
            raise
        sys.exit(1)


@main.command("import")
@click.argument("zip_file", type=click.Path(exists=True))
@click.option(
    "--confirm-overwrite",
    is_flag=True,
    help="Confirm overwriting existing data",
)
@click.option(
    "--method",
    type=click.Choice(["json", "sqlite"]),
    default="json",
    help="Import method (json=incremental, sqlite=full replace)",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Show detailed import progress",
)
def import_data(zip_file: str, confirm_overwrite: bool, method: str, verbose: bool) -> None:
    """Import data from an export ZIP file."""
    from terminal_todos.core.import_service import ImportService

    click.echo(f"Importing data from {zip_file}...")

    try:
        service = ImportService()

        # Check for existing data
        existing = service._check_existing_data()
        if existing["has_data"] and not confirm_overwrite:
            click.echo(
                click.style(
                    "⚠️  Warning: Database contains existing data:",
                    fg="yellow",
                ),
                err=True,
            )
            click.echo(f"  Todos: {existing['todos']}")
            click.echo(f"  Notes: {existing['notes']}")
            click.echo("\nUse --confirm-overwrite to proceed with import.")
            sys.exit(1)

        result = service.import_from_zip(
            zip_file,
            confirm_overwrite=confirm_overwrite,
            method=method,
        )

        click.echo(click.style("✓ Import successful!", fg="green"))
        click.echo(f"  Imported {result['todos']} todos")
        click.echo(f"  Imported {result['notes']} notes")
        click.echo(f"  Imported {result['emails']} emails")
        click.echo(f"  Imported {result['events']} events")
        click.echo(f"  Rebuilt {result['embeddings']} embeddings")

    except Exception as e:
        click.echo(click.style(f"✗ Import failed: {e}", fg="red"), err=True)
        if verbose:
            raise
        sys.exit(1)


# Make 'terminal-todos' launch TUI by default (for backwards compatibility)
@main.result_callback()
@click.pass_context
def default_command(ctx, result, **kwargs):
    """If no subcommand is provided, default to 'run'."""
    if ctx.invoked_subcommand is None:
        ctx.invoke(run)


if __name__ == "__main__":
    main()
