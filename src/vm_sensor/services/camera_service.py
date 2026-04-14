import platform

import cv2
import numpy as np

from vm_sensor.utils.frame_utils import build_placeholder_frame


class CameraService:
    def __init__(self, camera_index: int = 0) -> None:
        self.camera_index = camera_index
        self.capture: cv2.VideoCapture | None = None
        self.last_frame = build_placeholder_frame("Camera offline")

    def start(self) -> bool:
        if self.capture and self.capture.isOpened():
            return True

        backend = cv2.CAP_DSHOW if platform.system() == "Windows" else cv2.CAP_ANY
        capture = cv2.VideoCapture(self.camera_index, backend)

        if not capture.isOpened():
            self.capture = None
            self.last_frame = build_placeholder_frame(
                f"Cannot open camera #{self.camera_index}"
            )
            return False

        self.capture = capture
        return True

    def read_frame(self) -> np.ndarray:
        if self.capture and self.capture.isOpened():
            ok, frame = self.capture.read()
            if ok:
                self.last_frame = frame
                return frame.copy()

        self.last_frame = build_placeholder_frame(
            f"Camera #{self.camera_index} unavailable"
        )
        return self.last_frame.copy()

    def set_camera_index(self, camera_index: int) -> bool:
        self.release()
        self.camera_index = camera_index
        return self.start()

    def release(self) -> None:
        if self.capture and self.capture.isOpened():
            self.capture.release()
        self.capture = None
