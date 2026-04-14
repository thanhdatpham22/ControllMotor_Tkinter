from pathlib import Path

import numpy as np

from vm_sensor.models import PolygonAnnotation, SegmentResult
from vm_sensor.services.storage_service import StorageService


def test_save_capture_writes_requested_outputs(tmp_path: Path) -> None:
    service = StorageService(tmp_path)
    frame = np.zeros((100, 100, 3), dtype=np.uint8)

    result = SegmentResult(
        source_frame=frame,
        overlay_frame=frame.copy(),
        mask_frame=frame.copy(),
        polygons=[
            PolygonAnnotation(
                class_id=0,
                points=[(10.0, 10.0), (90.0, 10.0), (90.0, 90.0), (10.0, 90.0)],
                label="region",
                score=1.0,
            )
        ],
        mode="fallback",
    )

    saved = service.save_capture(result, save_yolo=True, save_json=True)

    assert saved["raw_image"].exists()
    assert saved["segment_image"].exists()
    assert saved["yolo"].exists()
    assert saved["json"].exists()
