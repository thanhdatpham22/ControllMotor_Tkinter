import cv2
from PIL import Image, ImageTk


def to_photo_image(frame, max_width: int, max_height: int):
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    height, width = rgb.shape[:2]

    scale = min(max_width / width, max_height / height)
    resized = cv2.resize(
        rgb,
        (max(1, int(width * scale)), max(1, int(height * scale))),
        interpolation=cv2.INTER_AREA,
    )

    image = Image.fromarray(resized)
    return ImageTk.PhotoImage(image=image)
