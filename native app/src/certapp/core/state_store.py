"""State persistence and manifest tracking module."""

import csv
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import threading

from src.certapp.core.models import Participant

MANIFEST_FIELDS = [
    "row_index",
    "name",
    "email",
    "certificate_path",
    "validation_status",
    "generation_status",
    "send_status",
    "sent_at",
    "error_message",
]


class ManifestStore:
    """Manages persistent tracking of certificate generation and send status in CSV manifest."""

    def __init__(self, output_dir: str | Path):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.manifest_path = self.output_dir / "manifest.csv"
        self._lock = threading.Lock()
        self._records: Dict[int, Dict[str, str]] = {}
        self.load()

    def load(self) -> None:
        """Loads records from manifest.csv if it exists."""
        with self._lock:
            self._records.clear()
            if not self.manifest_path.exists():
                return

            try:
                with open(self.manifest_path, "r", encoding="utf-8", newline="") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        try:
                            idx = int(row.get("row_index", 0))
                            if idx > 0:
                                self._records[idx] = dict(row)
                        except ValueError:
                            continue
            except Exception:
                pass

    def save(self) -> None:
        """Atomically saves current records to manifest.csv."""
        with self._lock:
            temp_file = self.output_dir / "manifest.tmp"
            with open(temp_file, "w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=MANIFEST_FIELDS)
                writer.writeheader()
                for idx in sorted(self._records.keys()):
                    row = self._records[idx]
                    writer.writerow({k: row.get(k, "") for k in MANIFEST_FIELDS})

            temp_file.replace(self.manifest_path)

    def update_participant(self, participant: Participant, sent_at: Optional[str] = None) -> None:
        """Updates record for a participant in the manifest store."""
        row_dict = {
            "row_index": str(participant.row_index),
            "name": participant.name,
            "email": participant.email,
            "certificate_path": participant.certificate_path or "",
            "validation_status": participant.validation_status,
            "generation_status": participant.generation_status,
            "send_status": participant.send_status,
            "sent_at": sent_at or (datetime.now().isoformat() if participant.send_status == "sent" else ""),
            "error_message": participant.error_message or "",
        }
        with self._lock:
            self._records[participant.row_index] = row_dict
        self.save()

    def sync_participants(self, participants: List[Participant]) -> None:
        """
        Syncs a list of loaded Participants with previously saved manifest state.
        Restores certificate_path, generation_status, send_status if found.
        """
        with self._lock:
            for p in participants:
                if p.row_index in self._records:
                    rec = self._records[p.row_index]
                    if rec.get("certificate_path") and Path(rec["certificate_path"]).exists():
                        p.certificate_path = rec["certificate_path"]
                        p.generation_status = rec.get("generation_status", "generated")
                    if rec.get("send_status"):
                        p.send_status = rec["send_status"]
                    if rec.get("error_message"):
                        p.error_message = rec["error_message"]
