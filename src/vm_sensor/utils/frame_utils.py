from datetime import datetime

import cv2
import numpy as np


def build_placeholder_frame(
    message: str,
    width: int = 659,
    height: int = 494,
) -> np.ndarray:
    frame = np.zeros((height, width, 3), dtype=np.uint8)
    frame[:] = (26, 26, 26)

    cv2.rectangle(frame, (30, 30), (width - 30, height - 30), (70, 70, 70), 2)
    cv2.putText(
        frame,
        "VM SENSOR",
        (50, 100),
        cv2.FONT_HERSHEY_SIMPLEX,
        1.1,
        (110, 200, 255),
        2,
        cv2.LINE_AA,
    )
    cv2.putText(
        frame,
        message,
        (50, 180),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.75,
        (240, 240, 240),
        2,
        cv2.LINE_AA,
    )
    cv2.putText(
        frame,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        (50, 240),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        (180, 180, 180),
        1,
        cv2.LINE_AA,
    )
    return frame
