from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PAGES = (
    ("results/RESULTS.md", "results/RESULTS.html", "Partial Match — Dossiers"),
    ("results/score-notes.md", "results/score-notes.html", "Partial Match — Scoring method"),
    ("notes/data-log.md", "notes/data-log.html", "Partial Match — Data log"),
    ("notes/credibility.md", "notes/credibility.html", "Partial Match — Validation"),
)


def main() -> None:
    pandoc = shutil.which("pandoc")
    if pandoc is None:
        raise SystemExit("Pandoc is required to build the evidence HTML pages.")

    for source, output, title in PAGES:
        subprocess.run(
            [
                pandoc,
                "--from=gfm",
                "--to=html5",
                "--standalone",
                "--template=web/evidence-template.html",
                "--metadata",
                f"title={title}",
                "--output",
                output,
                source,
            ],
            cwd=ROOT,
            check=True,
        )


if __name__ == "__main__":
    main()
