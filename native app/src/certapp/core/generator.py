"""Batch Certificate Generator engine."""

import logging
from pathlib import Path
from typing import List, Optional, Callable
import threading

from src.certapp.core.models import Participant, LayoutConfig, GenerationResult
from src.certapp.core.renderer import get_renderer, RendererError
from src.certapp.core.state_store import ManifestStore
from src.certapp.core.utils import sanitize_filename

logger = logging.getLogger("certapp.generator")


class CertificateGenerator:
    """Orchestrates single and batch certificate generation."""

    def __init__(
        self,
        config: LayoutConfig,
        output_dir: str | Path,
        naming_pattern: str = "{name}_certificate",
        overwrite: bool = True
    ):
        self.config = config
        self.output_dir = Path(output_dir)
        self.naming_pattern = naming_pattern
        self.overwrite = overwrite
        self.manifest_store = ManifestStore(self.output_dir)

    def _build_output_filename(self, participant: Participant) -> str:
        raw_name = self.naming_pattern.format(
            name=participant.name,
            email=participant.email,
            row_index=participant.row_index,
            **participant.extra_fields
        )
        safe_name = sanitize_filename(raw_name)
        ext = ".pdf" if self.config.output_format.lower() == "pdf" else ".png"
        return f"{safe_name}{ext}"

    def generate_single(self, participant: Participant) -> GenerationResult:
        """Generates a certificate for a single participant."""
        if participant.validation_status != "valid":
            participant.generation_status = "failed"
            participant.error_message = f"Skipped invalid participant: {participant.validation_message}"
            self.manifest_store.update_participant(participant)
            return GenerationResult(participant=participant, success=False, error=participant.error_message)

        filename = self._build_output_filename(participant)
        out_path = self.output_dir / filename

        # Skip if already exists and not overwrite
        if out_path.exists() and not self.overwrite and participant.generation_status == "generated":
            participant.certificate_path = str(out_path)
            return GenerationResult(participant=participant, success=True, output_path=str(out_path))

        try:
            renderer = get_renderer(self.config.background_path, self.config.output_format)
            rendered_path = renderer.render_participant(participant, self.config, out_path)

            participant.certificate_path = rendered_path
            participant.generation_status = "generated"
            participant.error_message = None
            self.manifest_store.update_participant(participant)

            return GenerationResult(participant=participant, success=True, output_path=rendered_path)
        except Exception as e:
            err_msg = str(e)
            logger.error(f"Failed to generate certificate for {participant.name}: {err_msg}")
            participant.generation_status = "failed"
            participant.error_message = err_msg
            self.manifest_store.update_participant(participant)

            return GenerationResult(participant=participant, success=False, error=err_msg)

    def generate_batch(
        self,
        participants: List[Participant],
        progress_callback: Optional[Callable[[int, int, Participant, GenerationResult], None]] = None,
        stop_event: Optional[threading.Event] = None
    ) -> List[GenerationResult]:
        """Generates certificates for a batch of participants with per-row resilience and cancellation support."""
        results: List[GenerationResult] = []
        total = len(participants)

        for idx, participant in enumerate(participants, 1):
            if stop_event and stop_event.is_set():
                logger.info("Batch generation cancelled by user.")
                break

            result = self.generate_single(participant)
            results.append(result)

            if progress_callback:
                progress_callback(idx, total, participant, result)

        return results
