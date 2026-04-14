from pathlib import Path
import numpy as np
import cv2

from vm_sensor.utils.frame_utils import build_placeholder_frame

SUPPORTED_IMAGE_PATTERNS = (
    "*.jpg",
    "*.jpeg",
    "*.png",
    "*.bmp",
    "*.tif",
    "*.tiff",
    "*.webp",
)


class ImageFolderService:
    def __init__(self) -> None:
        self.folder_path: Path | None = None
        self.image_paths: list[Path] = []
        self.current_index = 0
        self.last_frame = build_placeholder_frame("Image folder not selected")

    def load_folder(self, folder_path: str) -> tuple[bool, str]:
        target = Path(folder_path)

        if not target.is_dir():
            self.folder_path = None
            self.image_paths = []
            self.current_index = 0
            self.last_frame = build_placeholder_frame("Image folder not found")
            return False, f"Folder not found: {target}"

        image_paths: list[Path] = []
        for pattern in SUPPORTED_IMAGE_PATTERNS:
            image_paths.extend(target.glob(pattern))

        self.folder_path = target
        self.image_paths = sorted({path.resolve() for path in image_paths})
        self.current_index = 0

        if not self.image_paths:
            self.last_frame = build_placeholder_frame("No images found in folder")
            return False, f"No supported images found in: {target}"

        self.last_frame = self.read_frame()
        return True, f"Loaded {len(self.image_paths)} images from {target.name}"

    def read_frame(self) -> np.ndarray:
        if not self.image_paths:
            self.last_frame = build_placeholder_frame("Image folder not selected")
            return self.last_frame.copy()

        image_path = self.image_paths[self.current_index]
        frame = cv2.imread(str(image_path))
        if frame is None:
            self.last_frame = build_placeholder_frame(f"Cannot read {image_path.name}")
            return self.last_frame.copy()

        self.last_frame = frame
        return frame.copy()

    def next_image(self) -> np.ndarray:
        if self.image_paths:
            self.current_index = (self.current_index + 1) % len(self.image_paths)
        return self.read_frame()

    def previous_image(self) -> np.ndarray:
        if self.image_paths:
            self.current_index = (self.current_index - 1) % len(self.image_paths)
        return self.read_frame()

    def summary(self) -> str:
        if not self.image_paths:
            return "Folder source is empty."

        return (
            f"Folder image {self.current_index + 1}/{len(self.image_paths)}: "
            f"{self.image_paths[self.current_index].name}"
        )
