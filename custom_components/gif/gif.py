"""Synchronous GIF creation helpers.

Pillow work belongs in an executor. This module does not import Home Assistant
so unit tests can run against it directly.
"""

from __future__ import annotations

import os

from PIL import Image

from .const import DEFAULT_FPS, DEFAULT_LOOP, MAX_FPS, MIN_FPS, MIN_IMAGES


class GifError(Exception):
    """Base error for GIF creation."""


class GifValidationError(GifError):
    """Raised when service input is invalid."""

    translation_key: str | None
    translation_placeholders: dict[str, str] | None

    def __init__(
        self,
        message: str,
        *,
        translation_key: str | None = None,
        translation_placeholders: dict[str, str] | None = None,
    ) -> None:
        super().__init__(message)
        self.translation_key = translation_key
        self.translation_placeholders = translation_placeholders


class GifCreationError(GifError):
    """Raised when reading or writing image files fails."""


def _validate_inputs(
    images: list[str], fps: int, output_path: str | None
) -> tuple[list[str], int, str]:
    """Normalize and validate create_gif arguments."""
    if not images or len(images) < MIN_IMAGES:
        raise GifValidationError(
            f"At least {MIN_IMAGES} images are required"
        )
    if not output_path:
        raise GifValidationError("Output path is required")

    try:
        fps_int = int(fps)
    except (TypeError, ValueError) as err:
        raise GifValidationError("FPS must be an integer") from err
    if fps_int < MIN_FPS or fps_int > MAX_FPS:
        raise GifValidationError(
            f"FPS must be between {MIN_FPS} and {MAX_FPS}"
        )

    return list(images), fps_int, str(output_path)


def _prepare_frame(
    src: Image.Image, size: tuple[int, int] | None
) -> Image.Image:
    """Return a GIF-safe RGB copy, resized to *size* when given."""
    # convert() copies pixels so the source file can be closed.
    frame = src.convert("RGBA")
    if size is not None and frame.size != size:
        frame = frame.resize(size, Image.Resampling.LANCZOS)

    background = Image.new("RGB", frame.size, (255, 255, 255))
    background.paste(frame, mask=frame.split()[3])
    frame.close()
    return background


def create_gif_sync(
    images: list[str],
    fps: int = DEFAULT_FPS,
    output_path: str | None = None,
    loop: bool = DEFAULT_LOOP,
) -> None:
    """Create an animated GIF from image file paths.

    Frames are converted to RGB (alpha flattened onto white) and resized to
    match the first image. Frame duration is at least 1 ms.
    """
    images, fps, output_path = _validate_inputs(images, fps, output_path)

    frames: list[Image.Image] = []
    try:
        first_size: tuple[int, int] | None = None
        for img_path in images:
            try:
                with Image.open(img_path) as src:
                    frame = _prepare_frame(src, first_size)
            except OSError as err:
                raise GifCreationError(
                    f"Failed to open image {img_path}: {err}"
                ) from err
            if first_size is None:
                first_size = frame.size
            frames.append(frame)

        duration = max(1, round(1000 / fps))
        loop_value = 0 if loop else 1

        try:
            parent = os.path.dirname(output_path)
            if parent:
                os.makedirs(parent, exist_ok=True)
            frames[0].save(
                output_path,
                format="GIF",
                save_all=True,
                append_images=frames[1:],
                duration=duration,
                loop=loop_value,
            )
        except OSError as err:
            raise GifCreationError(
                f"Failed to save GIF to {output_path}: {err}"
            ) from err
    finally:
        for frame in frames:
            frame.close()
