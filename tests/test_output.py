"""Tests for default GIF output paths and service response (no live HA)."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from PIL import Image

from .helpers import load_gif_module

const = load_gif_module("const")
gif = load_gif_module("gif")
output = load_gif_module("output")

ATTR_OUTPUT_PATH = const.ATTR_OUTPUT_PATH
ATTR_URL = const.ATTR_URL
DEFAULT_IMAGES_PREFIX = const.DEFAULT_IMAGES_PREFIX
build_service_response = output.build_service_response
camera_filename_prefix = output.camera_filename_prefix
create_gif_sync = gif.create_gif_sync
local_url_for_www_file = output.local_url_for_www_file
resolve_output_path = output.resolve_output_path
sanitize_filename_stem = output.sanitize_filename_stem

WHEN = datetime(2026, 8, 13, 15, 30, 45)


def _config_path(config_dir: Path):
    def path(*parts: str) -> str:
        return str(config_dir.joinpath(*parts))

    return path


def _write_image(path: Path) -> Path:
    Image.new("RGB", (8, 8), (255, 0, 0)).save(path)
    return path


def test_output_constants() -> None:
    """Response keys and default prefixes are part of the public contract."""
    assert ATTR_OUTPUT_PATH == "output_path"
    assert ATTR_URL == "url"
    assert DEFAULT_IMAGES_PREFIX == "images"
    assert const.WWW_DIRNAME == "www"
    assert const.WWW_GIF_DIRNAME == "gif"


def test_sanitize_filename_stem() -> None:
    """Object ids are made filesystem-safe."""
    assert sanitize_filename_stem("front_door") == "front_door"
    assert sanitize_filename_stem("Front Door!!") == "Front_Door"
    assert sanitize_filename_stem("front/door") == "front_door"
    assert sanitize_filename_stem("..") == "gif"
    assert sanitize_filename_stem("!!!", fallback="camera") == "camera"


def test_camera_filename_prefix_uses_object_id() -> None:
    """Camera entity_id is reduced to a sanitized object_id."""
    assert camera_filename_prefix("camera.front_door") == "front_door"
    assert camera_filename_prefix("camera.front/door") == "front_door"


def test_default_path_camera_mode(tmp_path: Path) -> None:
    """Camera mode without output_path writes under www/gif with a timestamp."""
    path = resolve_output_path(
        None,
        camera_entity_id="camera.front_door",
        config_path=_config_path(tmp_path),
        when=WHEN,
    )
    assert path == str(
        tmp_path / "www" / "gif" / "front_door_20260813_153045.gif"
    )


def test_default_path_images_mode(tmp_path: Path) -> None:
    """Images mode without output_path uses images_<timestamp>.gif."""
    path = resolve_output_path(
        None,
        camera_entity_id=None,
        config_path=_config_path(tmp_path),
        when=WHEN,
    )
    assert path == str(tmp_path / "www" / "gif" / "images_20260813_153045.gif")


def test_blank_output_path_uses_default(tmp_path: Path) -> None:
    """Empty or whitespace output_path is treated as omitted."""
    config_path = _config_path(tmp_path)
    expected = str(tmp_path / "www" / "gif" / "front_door_20260813_153045.gif")
    for blank in ("", "   "):
        assert (
            resolve_output_path(
                blank,
                camera_entity_id="camera.front_door",
                config_path=config_path,
                when=WHEN,
            )
            == expected
        )


def test_explicit_output_path_is_honored(tmp_path: Path) -> None:
    """A provided output_path wins over the www/gif default."""
    requested = str(tmp_path / "custom" / "out.gif")
    path = resolve_output_path(
        requested,
        camera_entity_id="camera.front_door",
        config_path=_config_path(tmp_path),
        when=WHEN,
    )
    assert path == requested


def test_default_path_creates_www_gif_directory(tmp_path: Path) -> None:
    """Saving to the default path creates www/gif when it is missing."""
    frame_a = _write_image(tmp_path / "a.png")
    frame_b = _write_image(tmp_path / "b.png")
    output_path = resolve_output_path(
        None,
        camera_entity_id="camera.front_door",
        config_path=_config_path(tmp_path),
        when=WHEN,
    )
    assert not (tmp_path / "www" / "gif").exists()

    create_gif_sync(
        [str(frame_a), str(frame_b)],
        fps=10,
        output_path=output_path,
        loop=True,
    )

    assert Path(output_path).is_file()
    assert (tmp_path / "www" / "gif").is_dir()


def test_response_payload_includes_local_url(tmp_path: Path) -> None:
    """Files under www get output_path plus a /local URL."""
    output_path = str(tmp_path / "www" / "gif" / "front_door_20260813_153045.gif")
    payload = build_service_response(output_path, _config_path(tmp_path))
    assert payload == {
        ATTR_OUTPUT_PATH: output_path,
        ATTR_URL: "/local/gif/front_door_20260813_153045.gif",
    }


def test_response_payload_omits_url_outside_www(tmp_path: Path) -> None:
    """Paths outside www still return output_path but no url."""
    output_path = str(tmp_path / "elsewhere" / "out.gif")
    payload = build_service_response(output_path, _config_path(tmp_path))
    assert payload == {ATTR_OUTPUT_PATH: output_path}
    assert ATTR_URL not in payload


def test_local_url_rejects_www_dir_itself(tmp_path: Path) -> None:
    """The www directory is not a GIF file and has no /local URL."""
    www = str(tmp_path / "www")
    assert local_url_for_www_file(www, www) is None
