from abc import ABC, abstractmethod
from dataclasses import dataclass
import io
from typing import Any

from PIL import Image


@dataclass
class OCRLine:
    text: str
    confidence: float | None = None
    box: list | None = None


@dataclass
class OCRResult:
    text: str
    lines: list[OCRLine]
    provider: str


class OCRProvider(ABC):
    provider_id = "abstract"

    @abstractmethod
    def extract_image(self, image_bytes: bytes) -> OCRResult:
        raise NotImplementedError


class DisabledOCRProvider(OCRProvider):
    provider_id = "disabled"

    def extract_image(self, image_bytes: bytes) -> OCRResult:
        return OCRResult(text="", lines=[], provider=self.provider_id)


class PaddleOCRProvider(OCRProvider):
    """Optional local OCR provider.

    PaddleOCR is imported lazily so the core image stays lightweight. Install
    backend/requirements-ocr.txt and a compatible PaddlePaddle runtime, then set
    OCR_PROVIDER=paddle.
    """

    provider_id = "paddleocr"

    def __init__(self, language: str = "ar") -> None:
        try:
            from paddleocr import PaddleOCR
        except ImportError as exc:
            raise RuntimeError(
                "OCR_PROVIDER=paddle requires optional PaddleOCR dependencies"
            ) from exc
        self._engine = PaddleOCR(lang=language, use_doc_orientation_classify=False)

    def extract_image(self, image_bytes: bytes) -> OCRResult:
        import numpy as np

        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        raw: Any = self._engine.ocr(np.asarray(image))
        lines: list[OCRLine] = []
        for page in raw or []:
            for item in page or []:
                if not isinstance(item, (list, tuple)) or len(item) < 2:
                    continue
                box, recognized = item[0], item[1]
                if isinstance(recognized, (list, tuple)) and recognized:
                    text = str(recognized[0]).strip()
                    confidence = float(recognized[1]) if len(recognized) > 1 else None
                    if text:
                        lines.append(OCRLine(text=text, confidence=confidence, box=box))
        return OCRResult(
            text="\n".join(line.text for line in lines),
            lines=lines,
            provider=self.provider_id,
        )


def get_ocr_provider(name: str | None) -> OCRProvider:
    normalized = (name or "none").strip().lower()
    if normalized in {"none", "disabled", "off"}:
        return DisabledOCRProvider()
    if normalized in {"paddle", "paddleocr"}:
        return PaddleOCRProvider()
    raise ValueError(f"Unsupported OCR provider: {name}")
