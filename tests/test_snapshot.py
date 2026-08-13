"""Tests for camera snapshot helpers (no live Home Assistant core)."""

from __future__ import annotations

import asyncio
import io
import tempfile
from pathlib import Path
from types import SimpleNamespace

import pytest
from PIL import Image

from .helpers import load_gif_module

const = load_gif_module("const")
gif = load_gif_module("gif")
snapshot = load_gif_module("snapshot")

DEFAULT_COUNT = const.DEFAULT_COUNT
DEFAULT_INTERVAL = const.DEFAULT_INTERVAL
MAX_COUNT = const.MAX_COUNT
MAX_INTERVAL = const.MAX_INTERVAL
MIN_COUNT = const.MIN_COUNT
MIN_INTERVAL = const.MIN_INTERVAL
GifCreationError = gif.GifCreationError
GifValidationError = gif.GifValidationError
async_collect_snapshots = snapshot.async_collect_snapshots
cleanup_snapshot_dir = snapshot.cleanup_snapshot_dir
create_gif_from_image_bytes = snapshot.create_gif_from_image_bytes
resolve_image_source = snapshot.resolve_image_source
validate_camera_entity = snapshot.validate_camera_entity
validate_count_interval = snapshot.validate_count_interval
write_snapshot_files = snapshot.write_snapshot_files
SOURCE_CAMERA = snapshot.SOURCE_CAMERA
SOURCE_IMAGES = snapshot.SOURCE_IMAGES


def _jpeg_bytes(color: tuple[int, int, int], size: tuple[int, int] = (16, 16)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, format="JPEG")
    return buf.getvalue()


def test_camera_mode_constants() -> None:
    """Camera capture defaults and caps are part of the public contract."""
    assert DEFAULT_COUNT == 10
    assert DEFAULT_INTERVAL == 0.5
    assert MIN_COUNT == 2
    assert MAX_COUNT == 60
    assert MIN_INTERVAL == 0.1
    assert MAX_INTERVAL == 10.0
    assert const.ATTR_CAMERA == "camera"
    assert const.ATTR_COUNT == "count"
    assert const.ATTR_INTERVAL == "interval"


def test_resolve_images_only() -> None:
    """File-path mode still works when camera is omitted."""
    mode, images, camera = resolve_image_source(
        ["/a.jpg", "/b.jpg"], None
    )
    assert mode == SOURCE_IMAGES
    assert images == ["/a.jpg", "/b.jpg"]
    assert camera is None


def test_resolve_camera_only() -> None:
    """Camera mode is selected when images are omitted."""
    mode, images, camera = resolve_image_source(None, "camera.front_door")
    assert mode == SOURCE_CAMERA
    assert images is None
    assert camera == "camera.front_door"


def test_resolve_rejects_both_sources() -> None:
    """Do not silently mix images and camera."""
    with pytest.raises(GifValidationError, match="mutually exclusive"):
        resolve_image_source(["/a.jpg", "/b.jpg"], "camera.front_door")


def test_resolve_rejects_neither_source() -> None:
    """One of images or camera is required."""
    with pytest.raises(GifValidationError, match="Provide either images"):
        resolve_image_source(None, None)
    with pytest.raises(GifValidationError, match="Provide either images"):
        resolve_image_source([], "  ")


@pytest.mark.parametrize(
    ("entity_id", "state", "match"),
    [
        ("light.kitchen", SimpleNamespace(state="on"), "not a camera"),
        ("front_door", SimpleNamespace(state="idle"), "not a camera"),
        ("camera.missing", None, "Unknown camera"),
        (
            "camera.front_door",
            SimpleNamespace(state="unavailable"),
            "not available",
        ),
        (
            "camera.front_door",
            SimpleNamespace(state="unknown"),
            "not available",
        ),
    ],
)
def test_validate_camera_entity_rejects(
    entity_id: str, state: object | None, match: str
) -> None:
    """Missing, wrong-domain, and unavailable cameras fail closed."""
    with pytest.raises(GifValidationError, match=match):
        validate_camera_entity(entity_id, state)


def test_validate_camera_entity_accepts_idle() -> None:
    """A present, available camera is allowed."""
    validate_camera_entity(
        "camera.front_door", SimpleNamespace(state="idle")
    )


def test_validate_count_interval_defaults() -> None:
    """Camera mode defaults are 10 frames at 0.5 s."""
    assert validate_count_interval() == (10, 0.5)


@pytest.mark.parametrize(
    ("count", "interval", "match"),
    [
        (1, 0.5, "Count must be between"),
        (61, 0.5, "Count must be between"),
        ("many", 0.5, "Count must be an integer"),
        (10, 0.05, "Interval must be between"),
        (10, 10.1, "Interval must be between"),
        (10, "slow", "Interval must be a number"),
    ],
)
def test_validate_count_interval_rejects(
    count: object, interval: object, match: str
) -> None:
    """Count and interval are capped so automations cannot run forever."""
    with pytest.raises(GifValidationError, match=match):
        validate_count_interval(count, interval)


def test_async_collect_snapshots_sleeps_between_frames_only() -> None:
    """Interval waits happen between snapshots, not after the last one."""
    colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255)]
    frames = [_jpeg_bytes(color) for color in colors]
    slept: list[float] = []
    index = {"n": 0}

    async def get_image() -> bytes:
        content = frames[index["n"]]
        index["n"] += 1
        return content

    async def fake_sleep(seconds: float) -> None:
        slept.append(seconds)

    collected = asyncio.run(
        async_collect_snapshots(get_image, 3, 0.5, fake_sleep)
    )
    assert collected == frames
    assert slept == [0.5, 0.5]


def test_async_collect_snapshots_rejects_empty_frame() -> None:
    """Empty camera bytes fail before temp files are written."""

    async def get_image() -> bytes:
        return b""

    async def fake_sleep(_seconds: float) -> None:
        raise AssertionError("should not sleep after an empty snapshot")

    with pytest.raises(GifCreationError, match="empty snapshot"):
        asyncio.run(async_collect_snapshots(get_image, 2, 0.5, fake_sleep))


def test_write_and_cleanup_snapshot_files(tmp_path: Path) -> None:
    """Temp JPEGs are numbered and removed by cleanup."""
    frames = [_jpeg_bytes((1, 2, 3)), _jpeg_bytes((4, 5, 6))]
    directory = tmp_path / "shots"
    paths = write_snapshot_files(frames, str(directory))
    assert [Path(path).name for path in paths] == [
        "frame_000.jpg",
        "frame_001.jpg",
    ]
    for path, content in zip(paths, frames, strict=True):
        assert Path(path).read_bytes() == content

    cleanup_snapshot_dir(str(directory), paths)
    assert not directory.exists()


def test_create_gif_from_image_bytes_assembles_and_cleans(
    tmp_path: Path,
) -> None:
    """Mocked JPEG snapshots become a GIF and temp files are deleted."""
    output = tmp_path / "out.gif"
    before = set(Path(tempfile.gettempdir()).glob("ha_gif_*"))

    create_gif_from_image_bytes(
        [_jpeg_bytes((255, 0, 0)), _jpeg_bytes((0, 0, 255))],
        fps=10,
        output_path=str(output),
        loop=True,
    )

    assert output.is_file()
    with Image.open(output) as result:
        assert result.format == "GIF"
        assert result.size == (16, 16)
        assert getattr(result, "n_frames", 1) == 2

    after = set(Path(tempfile.gettempdir()).glob("ha_gif_*"))
    assert after <= before


def test_create_gif_from_image_bytes_cleans_up_on_failure(tmp_path: Path) -> None:
    """Invalid snapshot bytes still delete the temp directory."""
    before = set(Path(tempfile.gettempdir()).glob("ha_gif_*"))

    with pytest.raises(GifCreationError, match="Failed to open image"):
        create_gif_from_image_bytes(
            [b"not-an-image", b"also-not"],
            fps=10,
            output_path=str(tmp_path / "out.gif"),
            loop=True,
        )

    after = set(Path(tempfile.gettempdir()).glob("ha_gif_*"))
    assert after <= before
    assert not (tmp_path / "out.gif").exists()
