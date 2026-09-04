"""Go-On UTOR-RKY20-N7-1 Aircon IR integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .const import CONF_INFRARED_ENTITY_ID, DOMAIN

PLATFORMS = [Platform.CLIMATE]


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Stabilize entity identity and remove duplicates created by old settings."""
    if entry.version < 3:
        registry = er.async_get(hass)
        entities = [
            entity
            for entity in er.async_entries_for_config_entry(registry, entry.entry_id)
            if entity.platform == DOMAIN and entity.entity_id.startswith("climate.")
        ]
        if entities:
            old_unique_id = f"{entry.data.get(CONF_INFRARED_ENTITY_ID)}_climate"
            keep = next(
                (entity for entity in entities if entity.unique_id == old_unique_id),
                entities[-1],
            )
            for entity in entities:
                if entity.entity_id != keep.entity_id:
                    registry.async_remove(entity.entity_id)
            registry.async_update_entity(
                keep.entity_id, new_unique_id=f"{entry.entry_id}_climate"
            )
        hass.config_entries.async_update_entry(entry, version=3)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Go-On UTOR-RKY20-N7-1 Aircon IR from a config entry."""

    async def _update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
        await hass.config_entries.async_reload(entry.entry_id)

    entry.async_on_unload(entry.add_update_listener(_update_listener))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
