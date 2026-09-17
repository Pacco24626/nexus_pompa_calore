"""Costanti dell'integrazione Nexus Pompa di Calore."""

from __future__ import annotations

from homeassistant.const import Platform

DOMAIN = "nexus_pompa_calore"
PLATFORMS: list[Platform] = [Platform.SENSOR]

CONF_NOME = "nome"
CONF_ENTITA = "entita"
CONF_RIFERIMENTO = "riferimento"

NOME_PREDEFINITO = "Centrale Termica"
# Portata (L/min) oltre la quale il flusso disegnato non corre piu' veloce.
RIFERIMENTO_PREDEFINITO = 20

RUOLO_MAPPA = "mappa_pompa_calore"

# Stati del sensore «Stato»: in ordine di precedenza, il guasto vince su tutto.
STATI = ["guasto", "sbrinamento", "in_marcia", "fermo"]

CARD_URL_BASE = "/nexus_pompa_calore"
CARD_FILE = "nexus-pompa-calore-card.js"
