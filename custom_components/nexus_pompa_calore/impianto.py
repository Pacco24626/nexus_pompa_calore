"""L'impianto: segue le entita' collegate e tiene i valori calcolati.

Non legge niente dalla pompa di calore: lavora solo sulle entita' che Home
Assistant ha gia'. Quando una di queste cambia ricalcola stato e salto termico,
e avvisa i sensori solo se il risultato e' davvero cambiato.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.entity_registry import EVENT_ENTITY_REGISTRY_UPDATED
from homeassistant.helpers.event import async_track_state_change_event

from .const import CONF_ENTITA, CONF_RIFERIMENTO, RIFERIMENTO_PREDEFINITO, RUOLO_MAPPA
from .logica import rinomina, salto_termico, stato_impianto


class Impianto:
    """Una pompa di calore configurata."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        self.derivate: dict[str, Any] = {"stato": None, "salto_termico": None}
        self._ascoltatori: list[Callable[[], None]] = []
        self._annulla: list[Callable[[], None]] = []

    # -------------------------------------------------------------------------
    @property
    def configurazione(self) -> dict[str, Any]:
        return {**self.entry.data, **self.entry.options}

    @property
    def entita(self) -> dict[str, str]:
        return dict(self.configurazione.get(CONF_ENTITA) or {})

    @property
    def opzioni(self) -> dict[str, Any]:
        riferimento = self.configurazione.get(CONF_RIFERIMENTO, RIFERIMENTO_PREDEFINITO)
        try:
            riferimento = float(riferimento)
        except (TypeError, ValueError):
            riferimento = float(RIFERIMENTO_PREDEFINITO)
        return {CONF_RIFERIMENTO: riferimento if riferimento > 0 else float(RIFERIMENTO_PREDEFINITO)}

    @property
    def attributi(self) -> dict[str, Any]:
        """Quello che serve alla card. Oggetti nuovi a ogni lettura: HA confronta
        gli attributi con una copia superficiale e non vedrebbe le modifiche sul posto."""
        return {
            "ruolo": RUOLO_MAPPA,
            "nome": self.entry.title,
            "entita": self.entita,
            "opzioni": self.opzioni,
            "derivate": dict(self.derivate),
        }

    # -------------------------------------------------------------------------
    async def async_start(self) -> None:
        ids = sorted(set(self.entita.values()))
        if ids:
            self._annulla.append(async_track_state_change_event(self.hass, ids, self._al_cambio))
        self._annulla.append(self.hass.bus.async_listen(EVENT_ENTITY_REGISTRY_UPDATED, self._al_registro))
        self._ricalcola()

    async def async_stop(self) -> None:
        while self._annulla:
            self._annulla.pop()()

    @callback
    def async_add_listener(self, azione: Callable[[], None]) -> Callable[[], None]:
        self._ascoltatori.append(azione)

        def rimuovi() -> None:
            if azione in self._ascoltatori:
                self._ascoltatori.remove(azione)

        return rimuovi

    # -------------------------------------------------------------------------
    def _grezzo(self, entity_id: str) -> str | None:
        stato = self.hass.states.get(entity_id)
        return None if stato is None else stato.state

    def _ricalcola(self) -> bool:
        letture = {slot: self._grezzo(entity_id) for slot, entity_id in self.entita.items()}
        nuove = {
            "stato": stato_impianto(letture),
            "salto_termico": salto_termico(letture.get("mandata"), letture.get("ritorno")),
        }
        if nuove == self.derivate:
            return False
        self.derivate = nuove
        return True

    @callback
    def _al_cambio(self, _evento: Event) -> None:
        if self._ricalcola():
            for azione in list(self._ascoltatori):
                azione()

    @callback
    def _al_registro(self, evento: Event) -> None:
        """Un'entita' collegata rinominata: si aggiorna il collegamento, non si perde."""
        dati = evento.data
        if dati.get("action") != "update" or "old_entity_id" not in dati:
            return
        nuove = rinomina(self.entita, dati["old_entity_id"], dati["entity_id"])
        if nuove is None:
            return
        # Le opzioni vincono sui dati: basta scriverle, il ricaricamento lo fa
        # l'ascoltatore degli aggiornamenti registrato in __init__.
        self.hass.config_entries.async_update_entry(
            self.entry, options={**self.entry.options, CONF_ENTITA: nuove}
        )
