"""Prove a tavolino dell'impianto e dei sensori, su un Home Assistant finto.

    python tests/test_impianto.py
"""

from __future__ import annotations

import asyncio

import finto_ha
from finto_ha import Banco, Entry, Hass

from nexus_pompa_calore.const import STATI
from nexus_pompa_calore.impianto import Impianto
from nexus_pompa_calore.sensor import MappaSensor, SaltoTermicoSensor, StatoSensor

b = Banco("IMPIANTO")

PDC = "sensor.pompa_di_calore_pdc_"
ENTITA = {
    "mandata": f"{PDC}temp_mandata",
    "ritorno": f"{PDC}temp_ritorno",
    "portata": f"{PDC}portata_acqua",
    "compressore": "binary_sensor.pompa_di_calore_pdc_compressore_attivo",
    "sbrinamento": "binary_sensor.pompa_di_calore_pdc_sbrinamento_attivo",
}


def prepara():
    hass = Hass()
    hass.stati.imposta(ENTITA["mandata"], "29.5")
    hass.stati.imposta(ENTITA["ritorno"], "28.5")
    hass.stati.imposta(ENTITA["portata"], "0")
    hass.stati.imposta(ENTITA["compressore"], "off")
    hass.stati.imposta(ENTITA["sbrinamento"], "off")
    hass.stati.imposta("light.salotto", "off")
    entry = Entry({"entita": dict(ENTITA)}, title="Centrale Termica", entry_id="pdc1")
    return hass, entry


async def main():
    b.sezione("1. Avvio")
    hass, entry = prepara()
    impianto = Impianto(hass, entry)
    await impianto.async_start()
    b.v("stato iniziale: fermo", impianto.derivate["stato"] == "fermo")
    b.v("salto termico iniziale: 1,0", impianto.derivate["salto_termico"] == 1.0)
    b.v("ascolta solo le entita' collegate (uno ascoltatore, cinque id)",
        len(hass.stati.ascoltatori) == 1 and hass.stati.ascoltatori[0][0] == set(ENTITA.values()))
    b.v("ascolta le rinomine del registro", any(t == finto_ha.EVENT_ENTITY_REGISTRY_UPDATED for t, _ in hass.bus.ascoltatori))

    b.sezione("2. Sensori")
    mappa, stato, salto = MappaSensor(impianto), StatoSensor(impianto), SaltoTermicoSensor(impianto)
    for sensore in (mappa, stato, salto):
        await sensore.async_added_to_hass()
    attributi = mappa.extra_state_attributes
    b.v("la mappa dice il suo ruolo", attributi["ruolo"] == "mappa_pompa_calore")
    b.v("la mappa porta il nome della voce", attributi["nome"] == "Centrale Termica")
    b.v("la mappa porta le entita' collegate", attributi["entita"] == ENTITA)
    b.v("fondo scala predefinito: 20 L/min", attributi["opzioni"] == {"riferimento": 20.0})
    b.v("la mappa porta i valori calcolati", attributi["derivate"] == {"stato": "fermo", "salto_termico": 1.0})
    b.v("stato della mappa: quante entita' collegate", mappa.native_value == 5)
    b.v("gli attributi sono oggetti nuovi a ogni lettura",
        mappa.extra_state_attributes["entita"] is not attributi["entita"]
        and mappa.extra_state_attributes["derivate"] is not attributi["derivate"])
    b.v("unique_id legati alla voce", {mappa.unique_id, stato.unique_id, salto.unique_id} == {"pdc1_mappa", "pdc1_stato", "pdc1_salto_termico"})
    b.v("lo stato e' un elenco chiuso", stato.device_class == "enum" and stato._attr_options == STATI)
    b.v("il salto termico ha la classe delle differenze di temperatura", salto.device_class == "temperature_delta")
    b.v("il salto termico si legge dal sensore", salto.native_value == 1.0)
    b.v("icona dello stato fermo", stato.icon == "mdi:heat-pump-outline")

    b.sezione("3. La macchina parte")
    scritture = stato.scritture if hasattr(stato, "scritture") else 0
    hass.stati.imposta(ENTITA["compressore"], "on")
    b.v("compressore acceso: in marcia", stato.native_value == "in_marcia")
    b.v("i sensori vengono riscritti", getattr(stato, "scritture", 0) == scritture + 1)
    hass.stati.imposta(ENTITA["mandata"], "52.4")
    hass.stati.imposta(ENTITA["ritorno"], "45.1")
    b.v("il salto termico segue le temperature", salto.native_value == 7.3)
    riscritte = getattr(mappa, "scritture", 0)
    hass.stati.imposta(ENTITA["portata"], "13.6")
    b.v("un cambio che non muove i calcolati non riscrive nulla", getattr(mappa, "scritture", 0) == riscritte)
    hass.stati.imposta("light.salotto", "on")
    b.v("un'entita' estranea non riscrive nulla", getattr(mappa, "scritture", 0) == riscritte)

    b.sezione("4. Sbrinamento e letture perse")
    hass.stati.imposta(ENTITA["sbrinamento"], "on")
    b.v("sbrinamento", stato.native_value == "sbrinamento")
    b.v("icona dello sbrinamento", stato.icon == "mdi:snowflake-melt")
    hass.stati.imposta(ENTITA["sbrinamento"], "off")
    hass.stati.imposta(ENTITA["compressore"], "unavailable")
    b.v("compressore non disponibile: decide la portata", stato.native_value == "in_marcia")
    hass.stati.imposta(ENTITA["ritorno"], "unavailable")
    b.v("ritorno non disponibile: salto termico sconosciuto", salto.native_value is None)

    b.sezione("5. Rinomina di un'entita' collegata")
    hass.bus.spara(finto_ha.EVENT_ENTITY_REGISTRY_UPDATED, {"action": "update", "entity_id": "sensor.ritorno_nuovo", "old_entity_id": ENTITA["ritorno"], "changes": {}})
    b.v("la voce viene aggiornata una volta", len(hass.config_entries.aggiornamenti) == 1)
    b.v("il nuovo id finisce nelle opzioni", entry.options["entita"]["ritorno"] == "sensor.ritorno_nuovo")
    b.v("le altre entita' restano", entry.options["entita"]["mandata"] == ENTITA["mandata"])
    hass.bus.spara(finto_ha.EVENT_ENTITY_REGISTRY_UPDATED, {"action": "update", "entity_id": "light.cucina", "old_entity_id": "light.salotto", "changes": {}})
    b.v("la rinomina di un'entita' estranea non tocca la voce", len(hass.config_entries.aggiornamenti) == 1)
    hass.bus.spara(finto_ha.EVENT_ENTITY_REGISTRY_UPDATED, {"action": "update", "entity_id": ENTITA["mandata"], "changes": {"name": "x"}})
    b.v("un cambio di nome senza nuovo id non tocca la voce", len(hass.config_entries.aggiornamenti) == 1)

    b.sezione("6. Opzioni e arresto")
    entry.options = {**entry.options, "riferimento": 35}
    b.v("il fondo scala delle opzioni arriva alla card", mappa.extra_state_attributes["opzioni"] == {"riferimento": 35.0})
    entry.options = {**entry.options, "riferimento": "rotto"}
    b.v("un fondo scala illeggibile torna al predefinito", mappa.extra_state_attributes["opzioni"] == {"riferimento": 20.0})
    await impianto.async_stop()
    b.v("all'arresto nessun ascoltatore resta attaccato", not hass.stati.ascoltatori and not hass.bus.ascoltatori)
    for sensore in (mappa, stato, salto):
        sensore.rimuovi()
    b.v("e i sensori si staccano dall'impianto", not impianto._ascoltatori)

    b.sezione("7. Impianto con le sole obbligatorie")
    hass2 = Hass()
    hass2.stati.imposta("sensor.m", "40")
    hass2.stati.imposta("sensor.r", "35")
    minimo = Impianto(hass2, Entry({"entita": {"mandata": "sensor.m", "ritorno": "sensor.r"}}))
    await minimo.async_start()
    b.v("salto termico calcolato", minimo.derivate["salto_termico"] == 5.0)
    b.v("stato sconosciuto: niente di cui fidarsi", minimo.derivate["stato"] is None)


asyncio.run(main())
b.fine()
