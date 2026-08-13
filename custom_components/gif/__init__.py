"""The GIF integration."""

from __future__ import annotations

import asyncio
import logging
from typing import NoReturn

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType

from .const import (
    ATTR_CAMERA,
    ATTR_COUNT,
    ATTR_FPS,
    ATTR_IMAGES,
    ATTR_INTERVAL,
    ATTR_LOOP,
    ATTR_OUTPUT_PATH,
    DEFAULT_COUNT,
    DEFAULT_FPS,
    DEFAULT_INTERVAL,
    DEFAULT_LOOP,
    DOMAIN,
    MAX_COUNT,
    MAX_FPS,
    MAX_INTERVAL,
    MIN_COUNT,
    MIN_FPS,
    MIN_IMAGES,
    MIN_INTERVAL,
    SERVICE_CREATE_GIF,
)
from .gif import GifCreationError, GifValidationError, create_gif_sync
from .snapshot import (
    SOURCE_CAMERA,
    async_collect_snapshots,
    create_gif_from_image_bytes,
    resolve_image_source,
    validate_camera_entity,
    validate_count_interval,
)

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

CREATE_GIF_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_IMAGES): vol.All(
            cv.ensure_list, [cv.string], vol.Length(min=MIN_IMAGES)
        ),
        vol.Optional(ATTR_CAMERA): cv.entity_domain("camera"),
        vol.Optional(ATTR_COUNT, default=DEFAULT_COUNT): vol.All(
            vol.Coerce(int), vol.Range(min=MIN_COUNT, max=MAX_COUNT)
        ),
        vol.Optional(ATTR_INTERVAL, default=DEFAULT_INTERVAL): vol.All(
            vol.Coerce(float), vol.Range(min=MIN_INTERVAL, max=MAX_INTERVAL)
        ),
        vol.Optional(ATTR_FPS, default=DEFAULT_FPS): vol.All(
            vol.Coerce(int), vol.Range(min=MIN_FPS, max=MAX_FPS)
        ),
        vol.Required(ATTR_OUTPUT_PATH): cv.string,
        vol.Optional(ATTR_LOOP, default=DEFAULT_LOOP): cv.boolean,
    }
)


def _raise_validation_error(err: GifValidationError) -> NoReturn:
    """Re-raise a helper validation error as ServiceValidationError."""
    raise ServiceValidationError(
        str(err),
        translation_domain=DOMAIN,
        translation_key=err.translation_key,
        translation_placeholders=err.translation_placeholders,
    ) from err


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Register gif.create_gif so automations can validate it at startup."""

    async def async_create_gif(call: ServiceCall) -> None:
        """Create a GIF from image files or camera snapshots."""
        if not _async_entry_is_loaded(hass):
            raise ServiceValidationError(
                "The GIF integration is not set up",
                translation_domain=DOMAIN,
                translation_key="not_setup",
            )

        images: list[str] | None = call.data.get(ATTR_IMAGES)
        camera_id: str | None = call.data.get(ATTR_CAMERA)
        fps: int = call.data.get(ATTR_FPS, DEFAULT_FPS)
        output_path: str = call.data[ATTR_OUTPUT_PATH]
        loop: bool = call.data.get(ATTR_LOOP, DEFAULT_LOOP)
        count: int = call.data.get(ATTR_COUNT, DEFAULT_COUNT)
        interval: float = call.data.get(ATTR_INTERVAL, DEFAULT_INTERVAL)

        try:
            mode, image_paths, camera_id = resolve_image_source(images, camera_id)
            if mode == SOURCE_CAMERA:
                assert camera_id is not None
                count, interval = validate_count_interval(count, interval)
                validate_camera_entity(camera_id, hass.states.get(camera_id))
        except GifValidationError as err:
            _raise_validation_error(err)

        try:
            if mode == SOURCE_CAMERA:
                frames = await _async_snapshot_camera(
                    hass, camera_id, count, interval
                )
                await hass.async_add_executor_job(
                    create_gif_from_image_bytes, frames, fps, output_path, loop
                )
            else:
                await hass.async_add_executor_job(
                    create_gif_sync, image_paths, fps, output_path, loop
                )
        except GifValidationError as err:
            _raise_validation_error(err)
        except GifCreationError as err:
            raise HomeAssistantError(str(err)) from err

        _LOGGER.info("GIF created at %s", output_path)

    hass.services.async_register(
        DOMAIN,
        SERVICE_CREATE_GIF,
        async_create_gif,
        schema=CREATE_GIF_SCHEMA,
    )
    return True


async def _async_snapshot_camera(
    hass: HomeAssistant, entity_id: str, count: int, interval: float
) -> list[bytes]:
    """Capture *count* stills from a camera via async_get_image."""
    # Official still API: homeassistant.components.camera.async_get_image
    # (the same stills path the snapshot service uses internally). We want
    # image bytes for temp JPEGs, not a user-specified snapshot filename.
    from homeassistant.components.camera import async_get_image

    async def _get_image() -> bytes:
        try:
            image = await async_get_image(hass, entity_id)
        except Exception as err:
            raise HomeAssistantError(
                f"Failed to snapshot {entity_id}: {err}",
                translation_domain=DOMAIN,
                translation_key="snapshot_failed",
                translation_placeholders={
                    "entity_id": entity_id,
                    "error": str(err),
                },
            ) from err
        if not image.content:
            raise HomeAssistantError(
                f"Camera {entity_id} returned an empty snapshot",
                translation_domain=DOMAIN,
                translation_key="empty_snapshot",
                translation_placeholders={"entity_id": entity_id},
            )
        return image.content

    try:
        return await async_collect_snapshots(
            _get_image, count, interval, asyncio.sleep
        )
    except GifCreationError as err:
        raise HomeAssistantError(
            str(err),
            translation_domain=DOMAIN,
            translation_key="empty_snapshot",
            translation_placeholders={"entity_id": entity_id},
        ) from err


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up GIF from a config entry."""
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry.

    The service stays registered (HA action-setup) so automations can still
    be validated. Calls raise if no loaded entry remains.
    """
    return True


def _async_entry_is_loaded(hass: HomeAssistant) -> bool:
    """Return True if a GIF config entry is currently loaded."""
    return any(
        entry.state is ConfigEntryState.LOADED
        for entry in hass.config_entries.async_entries(DOMAIN)
    )
