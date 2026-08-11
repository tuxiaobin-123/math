"""Small, auditable experiment tracker rather than a folder of loose scripts."""

from __future__ import annotations

import json
import platform
import random
import time
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable

import numpy as np


@dataclass
class ExperimentResult:
    case: str
    model: str
    metrics: dict[str, float | int | None]
    parameters: dict[str, Any]
    seed: int
    runtime_seconds: float
    started_at: str
    audits: list[dict[str, Any]] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


class ExperimentTracker:
    def __init__(self, output_dir: str | Path, seed: int = 42):
        self.output_dir = Path(output_dir)
        self.seed = seed
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def run(
        self,
        *,
        case: str,
        model: str,
        parameters: dict[str, Any],
        function: Callable[[], tuple[dict[str, float | int | None], list[dict[str, Any]]]],
        notes: list[str] | None = None,
    ) -> ExperimentResult:
        random.seed(self.seed)
        np.random.seed(self.seed)
        started_at = datetime.now(UTC).isoformat()
        start = time.perf_counter()
        metrics, audits = function()
        result = ExperimentResult(
            case=case,
            model=model,
            metrics=metrics,
            parameters=parameters,
            seed=self.seed,
            runtime_seconds=time.perf_counter() - start,
            started_at=started_at,
            audits=audits,
            notes=notes or [],
        )
        destination = self.output_dir / f"{case}__{model}.json"
        destination.write_text(
            json.dumps(asdict(result), ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )
        self._write_environment()
        return result

    def _write_environment(self) -> None:
        environment = {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "numpy": np.__version__,
        }
        (self.output_dir / "environment.json").write_text(
            json.dumps(environment, ensure_ascii=False, indent=2), encoding="utf-8"
        )
