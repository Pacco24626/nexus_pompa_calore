"""Config flow: come si chiama l'impianto e quali entita' lo descrivono.

Le entita' si scelgono in tre sezioni (temperature, funzionamento, altro) e il
modulo arriva gia' compilato con quelle riconosciute dal nome. Le stesse sezioni
tornano in «Configura», con in piu' il fondo scala delle animazioni.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import section
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import selector

from .const import (
    CONF_ENTITA,
    CONF_NOME,
    CONF_RIFERIMENTO,
    DOMAIN,
    NOME_PREDEFINITO,
    RIFERIMENTO_PREDEFINITO,
)
from .logica import SEZIONI, SLOT, entita_da_modulo, errori_entita, proposte

SEZIONE_ANIMAZIONE = "animazione"


def _proposte_da_hass(hass: HomeAssistant) -> dict[str, str]:
    """Le entita' proposte, escluse quelle create da questa stessa integrazione."""
    nostre = {
        voce.entity_id for voce in er.async_get(hass).entities.values() if voce.platform == DOMAIN
    }
    return proposte(hass.states.async_entity_ids(), escludi=nostre)


def _campi_entita(valori: Mapping[str, str], chiuse: tuple[str, ...]) -> dict[Any, Any]:
    """Le tre sezioni di entita', con i valori proposti (o gia' scelti) precompilati.

    Si usa il valore suggerito e non quello predefinito: cosi' una voce facoltativa
    si puo' anche svuotare.
    """
    campi: dict[Any, Any] = {}
    for nome_sezione in SEZIONI:
        interno: dict[Any, Any] = {}
        for slot in (s for s in SLOT if s.sezione == nome_sezione):
            descrizione = {"suggested_value": valori[slot.chiave]} if valori.get(slot.chiave) else None
            marcatore = vol.Required if slot.obbligatorio else vol.Optional
            interno[marcatore(slot.chiave, description=descrizione)] = selector.EntitySelector(
                selector.EntitySelectorConfig(domain=list(slot.domini))
            )
        campi[vol.Required(nome_sezione)] = section(
            vol.Schema(interno), {"collapsed": nome_sezione in chiuse}
        )
    return campi


class NexusPompaCaloreConfigFlow(ConfigFlow, domain=DOMAIN):
    """Una voce per pompa di calore: se ne possono configurare piu' d'una."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errori: dict[str, str] = {}
        nome = NOME_PREDEFINITO
        if user_input is not None:
            entita = entita_da_modulo(user_input)
            nome = (user_input.get(CONF_NOME) or "").strip() or NOME_PREDEFINITO
            errori = errori_entita(entita)
            if not errori:
                return self.async_create_entry(title=nome, data={CONF_ENTITA: entita})
            valori = entita
        else:
            valori = _proposte_da_hass(self.hass)

        schema = vol.Schema(
            {
                vol.Required(CONF_NOME, default=nome): str,
                **_campi_entita(valori, chiuse=("altro",)),
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errori)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return NexusPompaCaloreOptionsFlow()


class NexusPompaCaloreOptionsFlow(OptionsFlow):
    """Entita' e fondo scala si cambiano senza reinstallare; il nome rinominando la voce."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        attuali = {**self.config_entry.data, **self.config_entry.options}
        errori: dict[str, str] = {}
        riferimento = attuali.get(CONF_RIFERIMENTO, RIFERIMENTO_PREDEFINITO)

        if user_input is not None:
            entita = entita_da_modulo(user_input)
            riferimento = (user_input.get(SEZIONE_ANIMAZIONE) or {}).get(CONF_RIFERIMENTO, riferimento)
            errori = errori_entita(entita)
            if not errori:
                return self.async_create_entry(
                    data={CONF_ENTITA: entita, CONF_RIFERIMENTO: float(riferimento)}
                )
            valori = entita
        else:
            valori = dict(attuali.get(CONF_ENTITA) or {})

        schema = vol.Schema(
            {
                **_campi_entita(valori, chiuse=()),
                vol.Required(SEZIONE_ANIMAZIONE): section(
                    vol.Schema(
                        {
                            vol.Required(CONF_RIFERIMENTO, default=float(riferimento)): selector.NumberSelector(
                                selector.NumberSelectorConfig(
                                    min=1,
                                    max=200,
                                    step=0.5,
                                    mode=selector.NumberSelectorMode.BOX,
                                    unit_of_measurement="L/min",
                                )
                            )
                        }
                    ),
                    {"collapsed": True},
                ),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema, errors=errori)
