import logging
import math
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import torch
from PIL import Image


EVENT_KEYWORDS = {
    "event",
    "tonight",
    "tickets",
    "rsvp",
    "lineup",
    "doors",
    "show",
    "concert",
    "party",
    "festival",
    "live",
    "dj",
    "set",
    "stage",
    "venue",
    "dance",
    "opening",
    "release",
    "launch",
    "saturday",
    "friday",
    "sunday",
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "jan",
    "january",
    "feb",
    "february",
    "mar",
    "march",
    "apr",
    "april",
    "may",
    "jun",
    "june",
    "jul",
    "july",
    "aug",
    "august",
    "sep",
    "sept",
    "september",
    "oct",
    "october",
    "nov",
    "november",
    "dec",
    "december",
}


@dataclass
class ClassificationResult:
    is_event: bool
    score: float
    details: Dict[str, float]


class EventListingClassifier:
    """Classify posts as event listings using caption and images."""
    def __init__(
        self,
        model_name: str = "ViT-B-32",
        pretrained: str = "laion2b_s34b_b79k",
        device: Optional[str] = None,
    ) -> None:
        """Load the CLIP model and prepare prompts for scoring."""
        import open_clip

        self.model_name = model_name
        self.pretrained = pretrained
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.logger = logging.getLogger(__name__)

        model, _, preprocess = open_clip.create_model_and_transforms(
            model_name, pretrained=pretrained
        )
        model.to(self.device)
        model.eval()

        self.model = model
        self.preprocess = preprocess
        self.tokenizer = open_clip.get_tokenizer(model_name)

        self.event_prompts = [
            "a flyer for an upcoming event",
            "a poster announcing a party",
            "a concert announcement poster",
            "a dance event flyer",
            "a ticketed event poster",
            "an event lineup graphic",
        ]
        self.non_event_prompts = [
            "a selfie",
            "a casual photo of friends",
            "a landscape photo",
            "a food photo",
            "a pet photo",
            "a random instagram post",
        ]

        self.event_text = self._encode_text(self.event_prompts)
        self.non_event_text = self._encode_text(self.non_event_prompts)
        self.threshold = float(os.environ.get("EVENT_LISTING_THRESHOLD", "0.30"))

    def _encode_text(self, prompts: List[str]) -> torch.Tensor:
        """Embed prompt text with the CLIP text encoder."""
        tokens = self.tokenizer(prompts)
        tokens = tokens.to(self.device)
        with torch.no_grad():
            text_features = self.model.encode_text(tokens)
            text_features = text_features / text_features.norm(dim=-1, keepdim=True)
        return text_features

    def _encode_image(self, image: Image.Image) -> torch.Tensor:
        """Embed an image with the CLIP image encoder."""
        image_tensor = self.preprocess(image).unsqueeze(0).to(self.device)
        with torch.no_grad():
            image_features = self.model.encode_image(image_tensor)
            image_features = image_features / image_features.norm(dim=-1, keepdim=True)
        return image_features

    def _keyword_score(self, caption: Optional[str]) -> float:
        """Score caption text for event-related keywords."""
        if not caption:
            return 0.0
        tokens = set(re.findall(r"[a-zA-Z]{2,}", caption.lower()))
        matches = EVENT_KEYWORDS.intersection(tokens)
        if not matches:
            return 0.0
        return min(1.0, len(matches) / 6)

    def _clip_score(self, image_paths: List[Path]) -> Optional[float]:
        """Score images against event and non-event prompts."""
        if not image_paths:
            return None

        scores = []
        for path in image_paths:
            try:
                image = Image.open(path).convert("RGB")
            except Exception:
                continue
            image_features = self._encode_image(image)
            event_sim = (image_features @ self.event_text.T).mean().item()
            non_event_sim = (image_features @ self.non_event_text.T).mean().item()
            scores.append(event_sim - non_event_sim)

        if not scores:
            return None
        return float(sum(scores) / len(scores))

    def classify_listing(
        self, caption: Optional[str], image_paths: List[Path]
    ) -> ClassificationResult:
        """Return a YES/NO decision with scores for event listings."""
        start_time = time.monotonic()
        self.logger.debug("CLIP inference start (%s images)", len(image_paths))
        keyword_score = self._keyword_score(caption)
        clip_score = self._clip_score(image_paths)
        elapsed = time.monotonic() - start_time
        self.logger.debug("CLIP inference finished in %.2fs", elapsed)

        if clip_score is None:
            combined = keyword_score
        else:
            combined = (0.55 * keyword_score) + (0.45 * (1 / (1 + math.exp(-clip_score))))

        is_event = combined >= self.threshold
        details = {
            "keyword_score": keyword_score,
            "clip_score": clip_score if clip_score is not None else -1.0,
            "combined_score": combined,
            "threshold": self.threshold,
        }
        return ClassificationResult(is_event=is_event, score=combined, details=details)
