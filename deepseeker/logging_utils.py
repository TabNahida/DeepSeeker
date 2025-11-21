from __future__ import annotations

import json
import logging
from dataclasses import asdict
from typing import Any, Dict, List, Optional

from .types import StepEvent


class StepLogger:
    """
    Collects step events and optionally prints them to console.

    This is what you'll use to:
    - show "now searching ..."
    - show which URLs are selected
    - show failure messages
    """

    def __init__(self, verbose: bool = True, logger: Optional[logging.Logger] = None):
        self.verbose = verbose
        self.events: List[StepEvent] = []
        self.logger = logger or logging.getLogger("deepseeker")
        if not self.logger.handlers:
            # Simple default handler
            handler = logging.StreamHandler()
            formatter = logging.Formatter("[%(levelname)s] %(message)s")
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)

    def log(
        self,
        step_type: str,
        message: str,
        data: Optional[Dict[str, Any]] = None,
        error: bool = False,
    ) -> None:
        event = StepEvent(
            step_type=step_type,
            message=message,
            data=data or {},
            error=error,
        )
        self.events.append(event)

        if self.verbose:
            prefix = "ERROR" if error else "STEP"
            self.logger.info(f"{prefix} [{step_type}] {message}")

    def to_json(self) -> str:
        """Return all events as JSON string."""
        return json.dumps([asdict(e) for e in self.events], ensure_ascii=False, indent=2)
