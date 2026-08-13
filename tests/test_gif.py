"""Tests for GIF creation helpers."""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from .helpers import load_gif_module

const = load_gif_module("const")
gif = load_gif_module("gif")

DEFAULT_FPS = const.DEFAULT_FPS
DEFAULT_LOOP = const.DEFAULT_LOOP
DOMAIN = const.DOMAIN
MAX_FPS = const.MAX_FPS
MIN_FPS = const.MIN_FPS
MIN_IMAGES = const.MIN_IMAGES
SERVICE_CREATE_GIF = const.SERVICE_CREATE_GIF
GifCreationError = gif.GifCreationError
GifValidationError = gif.GifValidationError
create_gif_sync = gif.create_gif_sync


def _write_image(
    path: Path,
    size: tuple[int, int],
    color: tuple[int, int, int] | tuple[int, int, int, int],
    mode: str = "RGB",
) -> Path:
    Image.new(mode, size, color).save(path)
    return path


def test_domain_and_service_contract() -> None:
    """Public HACS contract must stay stable."""
    assert DOMAIN == "gif"
    assert SERVICE_CREATE_GIF == "create_gif"
    assert DEFAULT_FPS == 10
    assert DEFAULT_LOOP is True
    assert MIN_IMAGES == 2
    assert MIN_FPS == 1
    assert MAX_FPS == 60
    assert const.ATTR_IMAGES == "images"
    assert const.ATTR_OUTPUT_PATH == "output_path"
    assert const.ATTR_URL == "url"


def test_create_gif_writes_animated_file(tmp_path: Path) -> None:
    """Two RGB frames produce a looping GIF at the requested size."""
    frame_a = _write_image(tmp_path / "a.png", (32, 24), (255, 0, 0))
    frame_b = _write_image(tmp_path / "b.png", (32, 24), (0, 0, 255))
    output = tmp_path / "out.gif"

    create_gif_sync(
        [str(frame_a), str(frame_b)],
        fps=10,
        output_path=str(output),
        loop=True,
    )

    assert output.is_file()
    with Image.open(output) as gif:
        assert gif.format == "GIF"
        assert gif.size == (32, 24)
        assert gif.info.get("loop") == 0
        assert gif.info.get("duration") == 100
        n_frames = getattr(gif, "n_frames", 1)
        assert n_frames == 2


def test_create_gif_resizes_mixed_sizes(tmp_path: Path) -> None:
    """Later frames are resized to the first image."""
    frame_a = _write_image(tmp_path / "a.png", (40, 20), (255, 0, 0))
    frame_b = _write_image(tmp_path / "b.png", (10, 10), (0, 255, 0))
    output = tmp_path / "out.gif"

    create_gif_sync(
        [str(frame_a), str(frame_b)],
        fps=5,
        output_path=str(output),
        loop=True,
    )

    with Image.open(output) as gif:
        assert gif.size == (40, 20)
        assert gif.info.get("duration") == 200


def test_create_gif_converts_rgba_and_palette(tmp_path: Path) -> None:
    """RGBA and palette sources are converted to a GIF-safe mode."""
    frame_a = _write_image(
        tmp_path / "a.png", (16, 16), (255, 0, 0, 128), mode="RGBA"
    )
    palette = Image.new("P", (16, 16))
    palette.putpalette([0, 255, 0] * 256)
    palette_path = tmp_path / "b.png"
    palette.save(palette_path)
    output = tmp_path / "out.gif"

    create_gif_sync(
        [str(frame_a), str(palette_path)],
        fps=10,
        output_path=str(output),
        loop=False,
    )

    with Image.open(output) as gif:
        assert gif.format == "GIF"
        assert gif.size == (16, 16)
        assert gif.info.get("loop") == 1


def test_create_gif_creates_parent_directory(tmp_path: Path) -> None:
    """Missing output directories are created."""
    frame_a = _write_image(tmp_path / "a.png", (8, 8), (0, 0, 0))
    frame_b = _write_image(tmp_path / "b.png", (8, 8), (255, 255, 255))
    output = tmp_path / "nested" / "dir" / "out.gif"

    create_gif_sync(
        [str(frame_a), str(frame_b)],
        fps=10,
        output_path=str(output),
        loop=True,
    )

    assert output.is_file()


def test_create_gif_duration_at_least_one_ms(tmp_path: Path) -> None:
    """High FPS still yields a duration of at least 1 ms."""
    frame_a = _write_image(tmp_path / "a.png", (4, 4), (1, 2, 3))
    frame_b = _write_image(tmp_path / "b.png", (4, 4), (4, 5, 6))
    output = tmp_path / "out.gif"

    create_gif_sync(
        [str(frame_a), str(frame_b)],
        fps=MAX_FPS,
        output_path=str(output),
        loop=True,
    )

    with Image.open(output) as gif:
        assert gif.info.get("duration") >= 1


@pytest.mark.parametrize(
    ("images", "fps", "output_path", "match"),
    [
        ([], 10, "out.gif", "At least 2 images"),
        (["only-one.png"], 10, "out.gif", "At least 2 images"),
        (["a.png", "b.png"], 10, "", "Output path is required"),
        (["a.png", "b.png"], 10, None, "Output path is required"),
        (["a.png", "b.png"], 0, "out.gif", "FPS must be between"),
        (["a.png", "b.png"], MAX_FPS + 1, "out.gif", "FPS must be between"),
        (["a.png", "b.png"], "fast", "out.gif", "FPS must be an integer"),
    ],
)
def test_create_gif_rejects_invalid_inputs(
    images: list[str],
    fps: object,
    output_path: str | None,
    match: str,
) -> None:
    """Validation failures raise GifValidationError."""
    with pytest.raises(GifValidationError, match=match):
        create_gif_sync(images, fps=fps, output_path=output_path, loop=True)  # type: ignore[arg-type]


def test_create_gif_missing_source_raises(tmp_path: Path) -> None:
    """Unreadable source files raise GifCreationError."""
    missing_a = tmp_path / "missing_a.png"
    missing_b = tmp_path / "missing_b.png"
    output = tmp_path / "out.gif"

    with pytest.raises(GifCreationError, match="Failed to open image"):
        create_gif_sync(
            [str(missing_a), str(missing_b)],
            fps=10,
            output_path=str(output),
            loop=True,
        )


def test_create_gif_unwritable_output_raises(tmp_path: Path) -> None:
    """Unwritable output paths raise GifCreationError."""
    frame_a = _write_image(tmp_path / "a.png", (8, 8), (0, 0, 0))
    frame_b = _write_image(tmp_path / "b.png", (8, 8), (255, 255, 255))
    blocked = tmp_path / "blocked"
    blocked.mkdir()

    with pytest.raises(GifCreationError, match="Failed to save GIF"):
        create_gif_sync(
            [str(frame_a), str(frame_b)],
            fps=10,
            output_path=str(blocked),
            loop=True,
        )
