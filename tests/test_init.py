"""Source checks for the gif.create_gif service handler."""

from __future__ import annotations

import ast
from pathlib import Path

INIT = (
    Path(__file__).resolve().parents[1]
    / "custom_components"
    / "gif"
    / "__init__.py"
)


def test_camera_path_uses_async_get_image_and_asyncio_sleep() -> None:
    """Stills come from camera.async_get_image; waits must not block the loop."""
    source = INIT.read_text(encoding="utf-8")
    assert "from homeassistant.components.camera import async_get_image" in source
    assert "asyncio.sleep" in source
    assert "time.sleep" not in source
    assert "SERVICE_SNAPSHOT" not in source
    assert "async_handle_snapshot_service" not in source
    assert "async_add_executor_job" in source
    assert "create_gif_from_image_bytes" in source


def test_helpers_do_not_import_homeassistant() -> None:
    """GIF assembly and snapshot helpers must stay testable without HA core."""
    root = Path(__file__).resolve().parents[1] / "custom_components" / "gif"
    for name in ("gif.py", "snapshot.py", "const.py", "output.py"):
        source = (root / name).read_text(encoding="utf-8")
        assert "homeassistant" not in source


def test_schema_keeps_images_and_output_optional() -> None:
    """Existing images usage stays valid; output_path is optional with a default."""
    tree = ast.parse(INIT.read_text(encoding="utf-8"))
    schema_assign = None
    for node in tree.body:
        if isinstance(node, ast.Assign):
            names = [
                target.id
                for target in node.targets
                if isinstance(target, ast.Name)
            ]
            if "CREATE_GIF_SCHEMA" in names:
                schema_assign = node
                break
    assert schema_assign is not None
    dumped = ast.unparse(schema_assign)
    assert "ATTR_IMAGES" in dumped
    assert "ATTR_CAMERA" in dumped
    assert "ATTR_COUNT" in dumped
    assert "ATTR_INTERVAL" in dumped
    assert "vol.Optional(ATTR_OUTPUT_PATH)" in dumped
    assert "vol.Required(ATTR_OUTPUT_PATH)" not in dumped
    assert "vol.Required(ATTR_IMAGES)" not in dumped
    assert "entity_domain" in dumped
    assert "camera" in dumped


def test_service_returns_optional_response_with_default_path() -> None:
    """Action returns output_path (and url when under www); path defaults via hass.config.path."""
    source = INIT.read_text(encoding="utf-8")
    assert "SupportsResponse.OPTIONAL" in source
    assert "build_service_response" in source
    assert "resolve_output_path" in source
    assert "hass.config.path" in source
    assert "dt_util.now" in source
    assert "return build_service_response" in source

