"""Headless reproducibility companion; no API, browser or database needed."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app.demo import generate_demo
from app.engine import run_backtest
from app.reports import report_markdown

parser = argparse.ArgumentParser()
parser.add_argument("--dataset", type=Path)
parser.add_argument("--config", type=Path)
parser.add_argument("--output", type=Path, default=Path("artifacts"))
args = parser.parse_args()
dataset = json.loads(args.dataset.read_text()) if args.dataset else generate_demo()
configuration = json.loads(args.config.read_text()) if args.config else {}
result = run_backtest(dataset, configuration)
args.output.mkdir(parents=True, exist_ok=True)
(args.output / "result.json").write_text(json.dumps(result, indent=2, allow_nan=False))
(args.output / "report.md").write_text(report_markdown(result))
(args.output / "config.json").write_text(json.dumps(result["config"], indent=2))
print(json.dumps({"dataset": result["dataset_kind"], "fingerprint": result["fingerprint"], "out_of_sample": result["out_of_sample"]["metrics"]}, indent=2))
