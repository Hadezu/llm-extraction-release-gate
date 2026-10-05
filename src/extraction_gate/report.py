from importlib.resources import files
from pathlib import Path

from jinja2 import Environment, select_autoescape

from .storage import atomic_json


def write_report(path: Path, comparison: dict):
    # A report must not overwrite an earlier inspected decision.
    path.mkdir(parents=True, exist_ok=False)
    template = (
        files("extraction_gate").joinpath("report.html").read_text(encoding="utf-8")
    )
    env = Environment(autoescape=select_autoescape(default_for_string=True))
    html = env.from_string(template).render(r=comparison)
    atomic_json(path / "comparison.json", comparison)
    (path / "index.html").write_text(html, encoding="utf-8")
