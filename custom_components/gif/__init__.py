"""The GIF integration."""

from __future__ import annotations

import logging

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType

from .const import (
    ATTR_FPS,
    ATTR_IMAGES,
    ATTR_LOOP,
    ATTR_OUTPUT_PATH,
    DEFAULT_FPS,
    DEFAULT_LOOP,
    DOMAIN,
    MAX_FPS,
    MIN_FPS,
    MIN_IMAGES,
    SERVICE_CREATE_GIF,
)
from .gif import GifCreationError, GifValidationError, create_gif_sync

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

CREATE_GIF_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_IMAGES): vol.All(
            cv.ensure_list, [cv.string], vol.Length(min=MIN_IMAGES)
        ),
        vol.Optional(ATTR_FPS, default=DEFAULT_FPS): vol.All(
            vol.Coerce(int), vol.Range(min=MIN_FPS, max=MAX_FPS)
        ),
        vol.Required(ATTR_OUTPUT_PATH): cv.string,
        vol.Optional(ATTR_LOOP, default=DEFAULT_LOOP): cv.boolean,
    }
)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Register gif.create_gif so automations can validate it at startup."""

    async def async_create_gif(call: ServiceCall) -> None:
        """Create a GIF from a list of image files."""
        if not _async_entry_is_loaded(hass):
            raise ServiceValidationError(
                "The GIF integration is not set up",
                translation_domain=DOMAIN,
                translation_key="not_setup",
            )

        images: list[str] = call.data[ATTR_IMAGES]
        fps: int = call.data.get(ATTR_FPS, DEFAULT_FPS)
        output_path: str = call.data[ATTR_OUTPUT_PATH]
        loop: bool = call.data.get(ATTR_LOOP, DEFAULT_LOOP)

        try:
            await hass.async_add_executor_job(
                create_gif_sync, images, fps, output_path, loop
            )
        except GifValidationError as err:
            raise ServiceValidationError(str(err)) from err
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
