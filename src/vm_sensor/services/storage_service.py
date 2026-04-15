import json
from datetime import datetime
from pathlib import Path

import cv2
from vm_sensor.models import PolygonAnnotation, SegmentResult

class StorageService:
    def __init__(self, output_dir: Path) -> None:
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def save_capture(
        self,
        segment_result: SegmentResult,
        save_yolo: bool = False,
        save_json: bool = False,
    ) -> dict[str, Path]:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        base_name = f"capture_{stamp}"

        raw_path = self.output_dir / f"{base_name}_raw.jpg"
        segment_path = self.output_dir / f"{base_name}_segment.jpg"

        cv2.imwrite(str(raw_path), segment_result.source_frame)
        cv2.imwrite(str(segment_path), segment_result.overlay_frame)

        saved_paths: dict[str, Path] = {
            "raw_image": raw_path,
            "segment_image": segment_path,
        }

        if save_yolo:
            yolo_path = self.output_dir / f"{base_name}.txt"
            self._write_yolo_annotation(
                yolo_path,
                segment_result.polygons,
                segment_result.source_frame.shape[1],
                segment_result.source_frame.shape[0],
            )
            saved_paths["yolo"] = yolo_path

        if save_json:
            json_path = self.output_dir / f"{base_name}.json"
            self._write_json_annotation(json_path, segment_result, raw_path, segment_path)
            saved_paths["json"] = json_path

        return saved_paths

    @staticmethod
    def _write_yolo_annotation(
        path: Path,
        polygons: list[PolygonAnnotation],
        image_width: int,
        image_height: int,
    ) -> None:
        lines: list[str] = []

        for polygon in polygons:
            if len(polygon.points) < 3:
                continue

            normalized = []
            for x_coord, y_coord in polygon.points:
                normalized.append(f"{x_coord / image_width:.6f}")
                normalized.append(f"{y_coord / image_height:.6f}")

            lines.append(f"{polygon.class_id} {' '.join(normalized)}")

        path.write_text("\n".join(lines), encoding="utf-8")

    @staticmethod
    def _write_json_annotation(
        path: Path,
        segment_result: SegmentResult,
        raw_path: Path,
        segment_path: Path,
    ) -> None:
        payload = {
            "mode": segment_result.mode,
            "raw_image": raw_path.name,
            "segment_image": segment_path.name,
            "image_size": {
                "width": int(segment_result.source_frame.shape[1]),
                "height": int(segment_result.source_frame.shape[0]),
            },
            "objects": [
                {
                    "class_id": polygon.class_id,
                    "label": polygon.label,
                    "score": polygon.score,
                    "points": [
                        {"x": float(x_coord), "y": float(y_coord)}
                        for x_coord, y_coord in polygon.points
                    ],
                }
                for polygon in segment_result.polygons
            ],
        }
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
