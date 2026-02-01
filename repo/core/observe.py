import csv
import os
from pathlib import Path

class ResonanceLogger:
    """
    Observer for Sheratan Resonance Cycles.
    Logs (cycle, segment, resonance) to CSV for analysis and replay.
    """
    def __init__(self, path="logs/resonance_log.csv"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        
        # Check if file exists to decide whether to write header
        exists = self.path.exists()
        self.file = open(self.path, "a", newline="", encoding="utf-8")
        self.writer = csv.writer(self.file)
        
        if not exists:
            self.writer.writerow(["cycle", "segment", "resonance"])
            self.file.flush()

    def log(self, cycle: int, segment: int, value: float):
        """Logs a single resonance result."""
        self.writer.writerow([cycle, int(segment), float(value)])

    def flush(self):
        """Flushes the log to disk."""
        self.file.flush()

    def close(self):
        """Closes the log file."""
        self.file.close()
