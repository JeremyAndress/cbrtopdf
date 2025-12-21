from enum import Enum

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".tiff", ".bmp"}


class ReadingDirecctionEnum(Enum):
    LEFT_TO_RIGHT = "ltr"  # Comic
    RIGHT_TO_LEFT = "rtl"  # Manga
