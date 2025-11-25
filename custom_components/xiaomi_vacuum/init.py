 """The Xiaomi 1C Vacuum integration."""
import logging

_LOGGER = logging.getLogger(__name__)

DOMAIN = "xiaomi_vacuum"

async def async_setup(hass, config):
    """Set up the Xiaomi 1C Vacuum integration."""
    return True

async def async_setup_entry(hass, entry):
    """Set up Xiaomi 1C Vacuum from a config entry."""
    hass.async_create_task(
        hass.config_entries.async_forward_entry_setup(entry, "vacuum")
    )
    return True

async def async_unload_entry(hass, entry):
    """Unload a config entry."""
    return await hass.config_entries.async_forward_entry_unload(entry, "vacuum")