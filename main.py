"""
main.py
-------
Auto-Director: Agentic Workflow for AI Micro-Drama Generation

CLI entry point and pipeline orchestrator.

Usage:
    python3 main.py sample_input/story.txt
    python3 main.py sample_input/story.txt --output my_drama.mp4
    python3 main.py sample_input/story.txt --verbose
    python3 main.py --help
"""

from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.table import Table
from rich import print as rprint

from config import settings
from core.exceptions import AutoDirectorError
from core.logger import configure_logging, get_logger

app = typer.Typer(
    name="autodirector",
    help="🎬  Auto-Director: turn a text story into a 9:16 vertical micro-drama video.",
    add_completion=False,
)
console = Console(stderr=True)
log = get_logger(__name__)


# ── Pipeline ──────────────────────────────────────────────────────────────────

def _run_pipeline(story_text: str, output_filename: str) -> tuple[str, dict[str, float]]:
    """
    Run the full 5-agent pipeline and return (output_path, stage_timings).
    Timings dict maps stage name → elapsed seconds.
    """
    # Import agents here so configure_logging() has already been called
    from agents.scriptwriter_agent import ScriptwriterAgent
    from agents.voice_agent import VoiceAgent
    from agents.visual_agent import VisualAgent
    from agents.subtitle_agent import SubtitleAgent
    from agents.director_agent import DirectorAgent

    timings: dict[str, float] = {}

    stages = [
        ("Scriptwriter  — breaking story into scenes",  ScriptwriterAgent, {}),
        ("Voice         — synthesising narration audio", VoiceAgent,        {}),
        ("Visual        — generating scene images",      VisualAgent,        {}),
        ("Subtitles     — aligning captions to audio",  SubtitleAgent,      {}),
        ("Director      — assembling final video",       DirectorAgent,      {"output_filename": output_filename}),
    ]

    with Progress(
        SpinnerColumn(),
        TextColumn("[bold cyan]{task.description}"),
        TimeElapsedColumn(),
        console=console,
        transient=False,
    ) as progress:

        # ── Stage 1: Scriptwriter ──────────────────────────────────────────
        task = progress.add_task(stages[0][0], total=None)
        t0 = time.perf_counter()
        scenes = ScriptwriterAgent().run(story_text)
        timings["Scriptwriter"] = time.perf_counter() - t0
        progress.update(task, description=f"[green]✓ {stages[0][0]}  ({len(scenes)} scenes)")
        progress.stop_task(task)
        log.info("Scriptwriter done — %d scenes planned.", len(scenes))

        # ── Stage 2: Voice ────────────────────────────────────────────────
        task = progress.add_task(stages[1][0], total=None)
        t0 = time.perf_counter()
        scenes = VoiceAgent().run(scenes)
        timings["Voice"] = time.perf_counter() - t0
        total_audio = sum(s.duration for s in scenes)
        progress.update(task, description=f"[green]✓ {stages[1][0]}  ({total_audio:.1f}s total audio)")
        progress.stop_task(task)

        # ── Stage 3: Visual ───────────────────────────────────────────────
        task = progress.add_task(stages[2][0], total=None)
        t0 = time.perf_counter()
        scenes = VisualAgent().run(scenes)
        timings["Visual"] = time.perf_counter() - t0
        progress.update(task, description=f"[green]✓ {stages[2][0]}")
        progress.stop_task(task)

        # ── Stage 4: Subtitles ────────────────────────────────────────────
        task = progress.add_task(stages[3][0], total=None)
        t0 = time.perf_counter()
        scenes = SubtitleAgent().run(scenes)
        timings["Subtitles"] = time.perf_counter() - t0
        progress.update(task, description=f"[green]✓ {stages[3][0]}")
        progress.stop_task(task)

        # ── Stage 5: Director ─────────────────────────────────────────────
        task = progress.add_task(stages[4][0], total=None)
        t0 = time.perf_counter()
        out_path = DirectorAgent().run(scenes, output_filename)
        timings["Director"] = time.perf_counter() - t0
        progress.update(task, description=f"[green]✓ {stages[4][0]}")
        progress.stop_task(task)

    return out_path, timings


def _print_summary(out_path: str, timings: dict[str, float], wall_time: float) -> None:
    """Print a rich summary table after the pipeline completes."""
    table = Table(title="Pipeline Summary", show_header=True, header_style="bold magenta")
    table.add_column("Stage", style="cyan", no_wrap=True)
    table.add_column("Time", justify="right", style="green")

    for stage, elapsed in timings.items():
        table.add_row(stage, f"{elapsed:.1f}s")

    table.add_section()
    table.add_row("[bold]Total wall time[/bold]", f"[bold]{wall_time:.1f}s[/bold]")

    console.print()
    console.print(table)
    console.print(Panel(
        f"[bold green]✓ Done![/bold green]\n"
        f"Output: [bold]{out_path}[/bold]",
        border_style="green",
    ))


# ── CLI Command ───────────────────────────────────────────────────────────────

@app.command()
def main(
    story_file: Path = typer.Argument(
        ...,
        help="Path to a .txt file containing the story to adapt.",
        exists=True,
        file_okay=True,
        readable=True,
    ),
    output: str = typer.Option(
        "final_video.mp4",
        "--output", "-o",
        help="Output filename (saved inside the output/ directory).",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose", "-v",
        help="Enable DEBUG-level logging.",
    ),
) -> None:
    """
    Convert a text story into a fully synchronised 9:16 vertical micro-drama video.

    Runs in DEMO mode (offline, no API keys needed) by default.
    Set GEMINI_API_KEY and/or ELEVENLABS_API_KEY environment variables
    (or add them to a .env file) to switch to LIVE mode.
    """
    # Wire logging level before anything else imports a logger
    log_level = "DEBUG" if verbose else settings.LOG_LEVEL
    configure_logging(log_level)

    story_text = story_file.read_text(encoding="utf-8").strip()
    if not story_text:
        console.print("[bold red]Error:[/bold red] Story file is empty.")
        raise typer.Exit(code=1)

    console.print(Panel(
        f"[bold]🎬 Auto-Director[/bold]\n"
        f"Mode : [bold cyan]{settings.active_mode}[/bold cyan]\n"
        f"Story: [dim]{story_file}[/dim]\n"
        f"FPS  : {settings.FPS}  |  "
        f"Resolution: {settings.VIDEO_WIDTH}×{settings.VIDEO_HEIGHT}",
        border_style="cyan",
    ))

    wall_start = time.perf_counter()
    try:
        out_path, timings = _run_pipeline(story_text, output)
    except AutoDirectorError as exc:
        console.print(f"\n[bold red]Pipeline error:[/bold red] {exc}")
        log.error("Pipeline aborted: %s", exc, exc_info=True)
        raise typer.Exit(code=1)
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user.[/yellow]")
        raise typer.Exit(code=130)

    wall_time = time.perf_counter() - wall_start
    _print_summary(out_path, timings, wall_time)


if __name__ == "__main__":
    app()
