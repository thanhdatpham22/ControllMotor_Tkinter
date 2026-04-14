from pathlib import Path

import cv2
import numpy as np

from vm_sensor.models import PolygonAnnotation, SegmentResult, SegmentSettings

try:
    from ultralytics import YOLO
except ImportError:
    YOLO = None


class YoloSegmenter:
    def __init__(self, model_path: str | None = None) -> None:
        self.model_path = model_path
        self.model = None
        self.status_message = "Fallback contour segmentation is active."
        if model_path:
            self.load_model(model_path)

    def load_model(self, model_path: str) -> str:
        model_file = Path(model_path)

        if YOLO is None:
            self.model = None
            self.status_message = "Ultralytics is not installed. Using fallback mode."
            return self.status_message

        if not model_file.is_file():
            self.model = None
            self.status_message = f"Model not found: {model_file}"
            return self.status_message

        try:
            self.model = YOLO(str(model_file))
            self.model_path = str(model_file)
            self.status_message = f"YOLO model loaded: {model_file.name}"
        except Exception as exc:  # pragma: no cover - runtime dependency
            self.model = None
            self.status_message = f"Failed to load model: {exc}"

        return self.status_message

    def segment(self, frame: np.ndarray, settings: SegmentSettings) -> SegmentResult:
        if self.model is not None:
            try:
                return self._segment_with_yolo(frame, settings)
            except Exception as exc:  # pragma: no cover - runtime dependency
                self.status_message = f"YOLO prediction failed, fallback used: {exc}"

        return self._segment_with_fallback(frame, settings)

    def _segment_with_yolo(
        self, frame: np.ndarray, settings: SegmentSettings
    ) -> SegmentResult:
        result = self.model.predict(
            source=frame,
            conf=settings.confidence,
            verbose=False,
        )[0]

        overlay_frame = result.plot()
        mask_frame = np.zeros(frame.shape[:2], dtype=np.uint8)
        polygons: list[PolygonAnnotation] = []

        names = result.names if hasattr(result, "names") else {}
        boxes = result.boxes
        masks = result.masks

        if masks is not None:
            for idx, mask_points in enumerate(masks.xy):
                contour = np.round(mask_points).astype(np.int32)
                if contour.shape[0] < 3:
                    continue

                cv2.fillPoly(mask_frame, [contour], 255)

                class_id = 0
                score = None
                label = "region"

                if boxes is not None and idx < len(boxes):
                    class_id = int(boxes.cls[idx].item())
                    score = float(boxes.conf[idx].item())
                    label = names.get(class_id, f"class_{class_id}")

                polygons.append(
                    PolygonAnnotation(
                        class_id=class_id,
                        points=[(float(x), float(y)) for x, y in mask_points.tolist()],
                        label=label,
                        score=score,
                    )
                )

        self.status_message = "YOLO segmentation completed."
        return SegmentResult(
            source_frame=frame.copy(),
            overlay_frame=overlay_frame,
            mask_frame=cv2.cvtColor(mask_frame, cv2.COLOR_GRAY2BGR),
            polygons=polygons,
            mode="yolo",
        )

    def _segment_with_fallback(
        self, frame: np.ndarray, settings: SegmentSettings
    ) -> SegmentResult:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        blur_kernel = max(1, settings.blur_kernel)
        if blur_kernel % 2 == 0:
            blur_kernel += 1

        blurred = cv2.GaussianBlur(gray, (blur_kernel, blur_kernel), 0)
        _, binary = cv2.threshold(
            blurred, settings.threshold, 255, cv2.THRESH_BINARY
        )

        contours, _ = cv2.findContours(
            binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        fill_layer = frame.copy()
        edge_layer = frame.copy()
        mask_frame = np.zeros_like(gray)
        polygons: list[PolygonAnnotation] = []

        for contour in contours:
            if cv2.contourArea(contour) < settings.min_area:
                continue

            epsilon = 0.003 * cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, epsilon, True)
            if approx.shape[0] < 3:
                continue

            cv2.fillPoly(fill_layer, [approx], (0, 160, 255))
            cv2.polylines(edge_layer, [approx], True, (0, 255, 0), 2)
            cv2.fillPoly(mask_frame, [approx], 255)

            polygons.append(
                PolygonAnnotation(
                    class_id=0,
                    points=[
                        (float(point[0][0]), float(point[0][1])) for point in approx
                    ],
                    label="region",
                    score=1.0,
                )
            )

        overlay_frame = cv2.addWeighted(
            fill_layer,
            settings.overlay_alpha,
            frame.copy(),
            1.0 - settings.overlay_alpha,
            0,
        )
        overlay_frame = cv2.addWeighted(overlay_frame, 0.85, edge_layer, 0.15, 0)

        self.status_message = "Fallback contour segmentation completed."
        return SegmentResult(
            source_frame=frame.copy(),
            overlay_frame=overlay_frame,
            mask_frame=cv2.cvtColor(mask_frame, cv2.COLOR_GRAY2BGR),
            polygons=polygons,
            mode="fallback",
        )
