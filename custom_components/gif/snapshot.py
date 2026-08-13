"""Camera snapshot helpers for gif.create_gif.

Home Assistant-free so unit tests can mock snapshots without a live core.
Pillow / disk work belongs in an executor; this module stays sync except for
the async capture loop (which only awaits the injected snapshot and sleep).
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
import os
import tempfile

from .const import (
    CAMERA_DOMAIN,
    DEFAULT_COUNT,
    DEFAULT_FPS,
    DEFAULT_INTERVAL,
    DEFAULT_LOOP,
    MAX_COUNT,
    MAX_INTERVAL,
    MIN_COUNT,
    MIN_IMAGES,
    MIN_INTERVAL,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from .gif import GifCreationError, GifValidationError, create_gif_sync

GetImage = Callable[[], Awaitable[bytes]]
Sleep = Callable[[float], Awaitable[object]]

SOURCE_IMAGES = "images"
SOURCE_CAMERA = "camera"


def resolve_image_source(
    images: list[str] | None,
    camera: str | None,
) -> tuple[str, list[str] | None, str | None]:
    """Return (mode, image paths, camera entity_id).

    ``images`` and ``camera`` are mutually exclusive. Exactly one must be set.
    """
    image_list = [str(path) for path in images] if images else []
    camera_id = camera.strip() if isinstance(camera, str) and camera.strip() else None
    has_images = bool(image_list)
    has_camera = bool(camera_id)

    if has_images and has_camera:
        raise GifValidationError(
            "images and camera are mutually exclusive; provide one or the other",
            translation_key="source_exclusive",
        )
    if not has_images and not has_camera:
        raise GifValidationError(
            "Provide either images (at least 2 file paths) or a camera entity",
            translation_key="source_required",
        )
    if has_images:
        if len(image_list) < MIN_IMAGES:
            raise GifValidationError(
                f"At least {MIN_IMAGES} images are required",
                translation_key="min_images",
            )
        return SOURCE_IMAGES, image_list, None
    return SOURCE_CAMERA, None, camera_id


def validate_count_interval(
    count: object = DEFAULT_COUNT, interval: object = DEFAULT_INTERVAL
) -> tuple[int, float]:
    """Normalize snapshot count and interval for camera mode."""
    try:
        count_int = int(count)  # type: ignore[arg-type]
    except (TypeError, ValueError) as err:
        raise GifValidationError(
            "Count must be an integer",
            translation_key="count_invalid",
        ) from err
    if count_int < MIN_COUNT or count_int > MAX_COUNT:
        raise GifValidationError(
            f"Count must be between {MIN_COUNT} and {MAX_COUNT}",
            translation_key="count_range",
        )

    try:
        interval_float = float(interval)  # type: ignore[arg-type]
    except (TypeError, ValueError) as err:
        raise GifValidationError(
            "Interval must be a number of seconds",
            translation_key="interval_invalid",
        ) from err
    if interval_float < MIN_INTERVAL or interval_float > MAX_INTERVAL:
        raise GifValidationError(
            f"Interval must be between {MIN_INTERVAL} and {MAX_INTERVAL} seconds",
            translation_key="interval_range",
        )
    return count_int, interval_float


def validate_camera_entity(entity_id: str, state: object | None) -> None:
    """Ensure *entity_id* exists, is a camera, and is available.

    *state* is whatever ``hass.states.get`` returns (or ``None``).
    """
    domain = entity_id.split(".", 1)[0] if "." in entity_id else ""
    if domain != CAMERA_DOMAIN:
        raise GifValidationError(
            f"{entity_id} is not a camera entity",
            translation_key="camera_not_camera",
            translation_placeholders={"entity_id": entity_id},
        )
    if state is None:
        raise GifValidationError(
            f"Unknown camera entity {entity_id}",
            translation_key="camera_not_found",
            translation_placeholders={"entity_id": entity_id},
        )
    state_value = getattr(state, "state", None)
    if state_value in (STATE_UNAVAILABLE, STATE_UNKNOWN):
        raise GifValidationError(
            f"Camera {entity_id} is not available",
            translation_key="camera_unavailable",
            translation_placeholders={"entity_id": entity_id},
        )


async def async_collect_snapshots(
    get_image: GetImage,
    count: int,
    interval: float,
    sleep: Sleep,
) -> list[bytes]:
    """Capture *count* snapshots, sleeping *interval* seconds between them.

    Does not sleep after the last frame. *get_image* and *sleep* are injected
    so tests can mock a camera without Home Assistant.
    """
    frames: list[bytes] = []
    last_index = count - 1
    for index in range(count):
        content = await get_image()
        if not content:
            raise GifCreationError("Camera returned an empty snapshot")
        frames.append(content)
        if index < last_index and interval > 0:
            await sleep(interval)
    return frames


def write_snapshot_files(frames: list[bytes], directory: str) -> list[str]:
    """Write snapshot bytes as numbered JPEGs in *directory*."""
    os.makedirs(directory, exist_ok=True)
    paths: list[str] = []
    for index, content in enumerate(frames):
        path = os.path.join(directory, f"frame_{index:03d}.jpg")
        with open(path, "wb") as handle:
            handle.write(content)
        paths.append(path)
    return paths


def cleanup_snapshot_dir(directory: str, paths: list[str]) -> None:
    """Delete snapshot files and the temp directory if it is empty."""
    for path in paths:
        try:
            os.unlink(path)
        except OSError:
            pass
    try:
        os.rmdir(directory)
    except OSError:
        pass


def create_gif_from_image_bytes(
    frames: list[bytes],
    fps: int = DEFAULT_FPS,
    output_path: str | None = None,
    loop: bool = DEFAULT_LOOP,
) -> None:
    """Write temp JPEGs, assemble a GIF, then delete the temps."""
    tmp_dir = tempfile.mkdtemp(prefix="ha_gif_")
    paths: list[str] = []
    try:
        paths = write_snapshot_files(frames, tmp_dir)
        create_gif_sync(paths, fps=fps, output_path=output_path, loop=loop)
    finally:
        cleanup_snapshot_dir(tmp_dir, paths)
