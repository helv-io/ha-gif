"""Default GIF output paths and service response helpers.

Home Assistant-free so unit tests can cover path generation without a live core.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
import os
import re

from .const import (
    ATTR_OUTPUT_PATH,
    ATTR_URL,
    DEFAULT_IMAGES_PREFIX,
    WWW_DIRNAME,
    WWW_GIF_DIRNAME,
)

ConfigPath = Callable[..., str]

TIMESTAMP_FORMAT = "%Y%m%d_%H%M%S"
LOCAL_URL_PREFIX = "/local"
_UNSAFE_FILENAME = re.compile(r"[^A-Za-z0-9_-]+")


def sanitize_filename_stem(value: str, fallback: str = "gif") -> str:
    """Return a filesystem-safe stem, or *fallback* if nothing usable remains."""
    cleaned = _UNSAFE_FILENAME.sub("_", value)
    cleaned = re.sub(r"_+", "_", cleaned).strip("_-")
    return cleaned or fallback


def camera_filename_prefix(entity_id: str) -> str:
    """Sanitize a camera entity's object_id for use in a filename."""
    object_id = entity_id.split(".", 1)[-1] if "." in entity_id else entity_id
    return sanitize_filename_stem(object_id, fallback="camera")


def build_default_output_path(
    config_path: ConfigPath,
    prefix: str,
    when: datetime | None = None,
) -> str:
    """Return ``<config>/www/gif/<prefix>_<YYYYMMDD_HHMMSS>.gif``."""
    stamp = (when or datetime.now()).strftime(TIMESTAMP_FORMAT)
    stem = sanitize_filename_stem(prefix)
    filename = f"{stem}_{stamp}.gif"
    return config_path(WWW_DIRNAME, WWW_GIF_DIRNAME, filename)


def resolve_output_path(
    output_path: str | None,
    *,
    camera_entity_id: str | None = None,
    config_path: ConfigPath,
    when: datetime | None = None,
) -> str:
    """Use *output_path* when set; otherwise default under ``www/gif``."""
    if isinstance(output_path, str) and output_path.strip():
        return output_path.strip()
    if camera_entity_id:
        prefix = camera_filename_prefix(camera_entity_id)
    else:
        prefix = DEFAULT_IMAGES_PREFIX
    return build_default_output_path(config_path, prefix, when)


def local_url_for_www_file(output_path: str, www_dir: str) -> str | None:
    """Return a ``/local/...`` URL when *output_path* is under HA's www folder."""
    abs_output = os.path.abspath(output_path)
    abs_www = os.path.abspath(www_dir)
    try:
        common = os.path.commonpath([abs_output, abs_www])
    except ValueError:
        return None
    if common != abs_www:
        return None
    relative = os.path.relpath(abs_output, abs_www)
    if relative.startswith("..") or relative in (os.curdir, os.pardir):
        return None
    return f"{LOCAL_URL_PREFIX}/{relative.replace(os.sep, '/')}"


def build_service_response(
    output_path: str, config_path: ConfigPath
) -> dict[str, str]:
    """Return the action response: path, plus url when the file is under www."""
    payload: dict[str, str] = {ATTR_OUTPUT_PATH: output_path}
    url = local_url_for_www_file(output_path, config_path(WWW_DIRNAME))
    if url is not None:
        payload[ATTR_URL] = url
    return payload
