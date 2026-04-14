from datetime import datetime

import cv2
import numpy as np


def build_placeholder_frame(
    message: str,
    width: int = 1280,
    height: int = 720,
) -> np.ndarray:
    frame = np.zeros((height, width, 3), dtype=np.uint8)
    frame[:] = (26, 26, 26)

    cv2.rectangle(frame, (40, 40), (width - 40, height - 40), (70, 70, 70), 2)
    cv2.putText(
        frame,
        "VM SENSOR",
        (70, 140),
        cv2.FONT_HERSHEY_SIMPLEX,
        1.5,
        (110, 200, 255),
        3,
        cv2.LINE_AA,
    )
    cv2.putText(
        frame,
        message,
        (70, 230),
        cv2.FONT_HERSHEY_SIMPLEX,
        1.0,
        (240, 240, 240),
        2,
        cv2.LINE_AA,
    )
    cv2.putText(
        frame,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        (70, 290),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (180, 180, 180),
        2,
        cv2.LINE_AA,
    )
    return frame
