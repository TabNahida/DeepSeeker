from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .types import StepEvent


@dataclass
class LLMCallRecord:
    """Record of a single LLM API call with full input/output."""
    timestamp: str
    call_type: str  # e.g., "llm0_plan", "llm0_select", "llm1_summarize"
    messages: List[Dict[str, Any]]
    response: Dict[str, Any]
    model: str
    duration_ms: int


class StepLogger:
    """
    Collects step events and optionally prints them to console.
    
    Features:
    - Console: Shows concise, human-readable step progress
    - File: Saves complete LLM I/O records and detailed logs
    - RAW STEP: Keeps console output minimal and clean
    - FULL LOG: Complete records saved to timestamped log files
    """

    def __init__(
        self, 
        verbose: bool = True, 
        logger: Optional[logging.Logger] = None,
        log_dir: Optional[str] = None,
        debug: bool = False
    ):
        self.verbose = verbose
        self.debug = debug
        self.events: List[StepEvent] = []
        self.llm_records: List[LLMCallRecord] = []
        
        # Setup console logger for concise output
        self.logger = logger or logging.getLogger("deepseeker")
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter("[%(levelname)s] %(message)s")
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
        
        # Setup file logger for detailed records
        self.log_dir = Path(log_dir) if log_dir else Path("logs")
        self.log_dir.mkdir(exist_ok=True)
        
        # Create timestamped log file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = self.log_dir / f"deepseeker_{timestamp}.log"
        
        # File logger for detailed records
        self.file_logger = logging.getLogger(f"deepseeker.file.{timestamp}")
        # Set level based on debug flag
        self.file_logger.setLevel(logging.DEBUG if debug else logging.INFO)
        
        # Remove existing handlers to avoid duplicates
        self.file_logger.handlers.clear()
        
        file_handler = logging.FileHandler(self.log_file, encoding='utf-8')
        file_formatter = logging.Formatter(
            "%(asctime)s.%(msecs)03d | %(levelname)-8s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        file_handler.setFormatter(file_formatter)
        self.file_logger.addHandler(file_handler)

    def log(
        self,
        step_type: str,
        message: str,
        data: Optional[Dict[str, Any]] = None,
        error: bool = False,
    ) -> None:
        """Log a step event - concise for console, detailed for file."""
        event = StepEvent(
            step_type=step_type,
            message=message,
            data=data or {},
            error=error,
        )
        self.events.append(event)

        # Console output: Keep it concise (RAW STEP)
        if self.verbose:
            prefix = "❌" if error else "●"
            # Simplified message for console
            console_msg = self._format_console_message(step_type, message, error)
            self.logger.info(f"{prefix} {console_msg}")

        # File output: Detailed record
        log_level = logging.ERROR if error else logging.INFO
        detailed_msg = f"[{step_type}] {message}"
        if data:
            detailed_msg += f" | data={json.dumps(data, ensure_ascii=False, default=str)}"
        self.file_logger.log(log_level, detailed_msg)

    def log_llm_call(
        self,
        call_type: str,
        messages: List[Dict[str, Any]],
        response: Dict[str, Any],
        model: str,
        duration_ms: int,
    ) -> None:
        """Record a complete LLM API call with input/output."""
        record = LLMCallRecord(
            timestamp=datetime.now().isoformat(),
            call_type=call_type,
            messages=messages,
            response=response,
            model=model,
            duration_ms=duration_ms,
        )
        self.llm_records.append(record)
        
        # Always log basic call info
        self.file_logger.info(f"LLM_CALL | {call_type} | {model} | {duration_ms}ms")
        
        # Only log detailed messages/responses if debug mode is enabled
        if self.debug:
            self.file_logger.debug(f"  Messages: {json.dumps(messages, ensure_ascii=False, indent=2)}")
            self.file_logger.debug(f"  Response: {json.dumps(response, ensure_ascii=False, indent=2)}")

    def _format_console_message(self, step_type: str, message: str, error: bool) -> str:
        """Format concise message for console output."""
        if error:
            return f"ERROR [{step_type}] {message}"
        
        # Simplify common step types
        if step_type == "plan":
            return "Planning search strategy..."
        elif step_type == "search":
            # Extract just the essential info
            if "Running search" in message:
                return message.split(" with query=")[0] + "..."
            elif "returned" in message and "results" in message:
                return message
            return message
        elif step_type == "select":
            if "selected" in message:
                return message
            return "Selecting relevant results..."
        elif step_type == "summarize":
            if "Fetching" in message:
                return "Reading article..."
            elif "summarized" in message:
                return message.split(" (relevance=")[0] + ")"
            return "Summarizing..."
        elif step_type == "final":
            if "synthesizing" in message:
                return "Synthesizing final answer..."
            return message
        else:
            return f"[{step_type}] {message}"

    def to_json(self) -> str:
        """Return all step events as JSON string."""
        return json.dumps([asdict(e) for e in self.events], ensure_ascii=False, indent=2)

    def save_full_log(self) -> str:
        """Save complete log including LLM calls and return the file path."""
        full_log = {
            "metadata": {
                "created_at": datetime.now().isoformat(),
                "total_steps": len(self.events),
                "total_llm_calls": len(self.llm_records),
            },
            "steps": [asdict(e) for e in self.events],
            "llm_calls": [asdict(r) for r in self.llm_records],
        }
        
        full_log_file = self.log_dir / f"deepseeker_full_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(full_log_file, 'w', encoding='utf-8') as f:
            json.dump(full_log, f, ensure_ascii=False, indent=2)
        
        return str(full_log_file)

    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of the session."""
        return {
            "total_steps": len(self.events),
            "total_llm_calls": len(self.llm_records),
            "errors": sum(1 for e in self.events if e.error),
            "log_file": str(self.log_file),
            "steps_by_type": {
                step_type: sum(1 for e in self.events if e.step_type == step_type)
                for step_type in set(e.step_type for e in self.events)
            }
        }
