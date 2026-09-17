"""Sensori: la mappa per la card, lo stato della macchina e il salto termico."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import MATCH_ALL, EntityCategory, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, STATI
from .impianto import Impianto

ICONE_STATO = {
    "guasto": "mdi:alert-circle",
    "sbrinamento": "mdi:snowflake-melt",
    "in_marcia": "mdi:heat-pump",
    "fermo": "mdi:heat-pump-outline",
}


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    impianto: Impianto = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([MappaSensor(impianto), StatoSensor(impianto), SaltoTermicoSensor(impianto)])


class _SensoreImpianto(SensorEntity):
    _attr_should_poll = False
    _attr_has_entity_name = True

    def __init__(self, impianto: Impianto, chiave: str) -> None:
        self._impianto = impianto
        self._attr_translation_key = chiave
        self._attr_unique_id = f"{impianto.entry.entry_id}_{chiave}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, impianto.entry.entry_id)},
            name=impianto.entry.title,
            manufacturer="Automatic Systems",
            model="Sinottico pompa di calore",
        )

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(self._impianto.async_add_listener(self.async_write_ha_state))


class MappaSensor(_SensoreImpianto):
    """Stato: quante entita' sono collegate. Attributi: tutto quello che serve alla card.

    Diagnostico, cosi' non finisce nelle plance automatiche; gli attributi non
    vanno nel database, perche' sono configurazione e valori gia' registrati altrove.
    """

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:transit-connection-variant"
    _unrecorded_attributes = frozenset({MATCH_ALL})

    def __init__(self, impianto: Impianto) -> None:
        super().__init__(impianto, "mappa")

    @property
    def native_value(self) -> int:
        return len(self._impianto.entita)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return self._impianto.attributi


class StatoSensor(_SensoreImpianto):
    """Guasto, sbrinamento, in marcia o fermo; sconosciuto se nessuna fonte si legge."""

    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = STATI

    def __init__(self, impianto: Impianto) -> None:
        super().__init__(impianto, "stato")

    @property
    def native_value(self) -> str | None:
        return self._impianto.derivate.get("stato")

    @property
    def icon(self) -> str:
        return ICONE_STATO.get(self.native_value or "", "mdi:heat-pump-outline")


class SaltoTermicoSensor(_SensoreImpianto):
    """Mandata meno ritorno.

    E' una differenza, non una temperatura: con la classe «temperatura» Home
    Assistant la convertirebbe in Fahrenheit sbagliando lo zero. Dal 2025.12 c'e'
    la classe giusta («differenza di temperatura»); prima si resta senza classe.
    """

    _attr_device_class = getattr(SensorDeviceClass, "TEMPERATURE_DELTA", None)
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 1
    _attr_icon = "mdi:thermometer-lines"

    def __init__(self, impianto: Impianto) -> None:
        super().__init__(impianto, "salto_termico")

    @property
    def native_value(self) -> float | None:
        return self._impianto.derivate.get("salto_termico")
