from dataclasses import dataclass, field

import numpy as np


@dataclass(slots=True)
class SegmentSettings:
    confidence: float = 0.40
    threshold: int = 120
    blur_kernel: int = 5
    min_area: int = 800
    overlay_alpha: float = 0.45
    source_type: str = "camera"
    camera_backend: str = "opencv"
    camera_index: int = 0
    basler_serial: str | None = None
    image_folder: str | None = None
    model_path: str | None = None


@dataclass(slots=True)
class PolygonAnnotation:
    class_id: int
    points: list[tuple[float, float]]
    label: str = "region"
    score: float | None = None


@dataclass(slots=True)
class SegmentResult:
    source_frame: np.ndarray
    overlay_frame: np.ndarray
    mask_frame: np.ndarray
    polygons: list[PolygonAnnotation] = field(default_factory=list)
    mode: str = "fallback"
