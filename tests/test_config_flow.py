"""Prove a tavolino del config flow e del flusso delle opzioni.

    python tests/test_config_flow.py
"""

from __future__ import annotations

import asyncio

import finto_ha  # noqa: F401
from finto_ha import Banco, Entry, Hass, section

from nexus_pompa_calore.config_flow import NexusPompaCaloreConfigFlow, NexusPompaCaloreOptionsFlow

b = Banco("CONFIG FLOW")

PDC = "sensor.pompa_di_calore_pdc_"
VERE = {
    "mandata": f"{PDC}temp_mandata",
    "ritorno": f"{PDC}temp_ritorno",
    "esterna": f"{PDC}temp_esterna",
    "accumulo": f"{PDC}temp_accumulo_acs",
    "portata": f"{PDC}portata_acqua",
    "frequenza": f"{PDC}frequenza_compressore",
    "compressore": "binary_sensor.pompa_di_calore_pdc_compressore_attivo",
    "sbrinamento": "binary_sensor.pompa_di_calore_pdc_sbrinamento_attivo",
    "cop_riscaldamento": f"{PDC}cop_riscaldamento",
    "cop_sanitario": f"{PDC}cop_sanitario",
    "boost": "switch.pompa_di_calore_boost_acs",
    "vacanza": "switch.pompa_di_calore_pdc_modalita_vacanza_2",
    "guasto": "binary_sensor.centrale_tecnoalarm_guasto_pdc",
}


def hass_vero():
    hass = Hass()
    for entity_id in VERE.values():
        hass.stati.imposta(entity_id, "0")
    hass.stati.imposta("light.salotto", "off")
    # Un'entita' della stessa integrazione, gia' configurata: non va proposta.
    hass.stati.imposta("sensor.vecchia_temp_mandata", "30")
    hass.registro.aggiungi("sensor.vecchia_temp_mandata", "nexus_pompa_calore")
    return hass


def campi(schema):
    """Le chiavi di primo livello per nome, e le sezioni col loro contenuto."""
    return {str(k): (k, v) for k, v in schema.items()}


def suggerito(risultato, sezione, voce):
    _, sez = campi(risultato["schema"])[sezione]
    for chiave in sez.schema:
        if str(chiave) == voce:
            return (chiave.description or {}).get("suggested_value")
    raise KeyError(voce)


def marcatore(risultato, sezione, voce):
    _, sez = campi(risultato["schema"])[sezione]
    return next(k for k in sez.schema if str(k) == voce)


async def main():
    b.sezione("1. Apertura del modulo")
    flusso = NexusPompaCaloreConfigFlow()
    flusso.hass = hass_vero()
    r = await flusso.async_step_user()
    c = campi(r["schema"])
    b.v("modulo utente", r["type"] == "form" and r["step_id"] == "user")
    b.v("nome proposto «Centrale Termica»", c["nome"][0].default == "Centrale Termica")
    b.v("tre sezioni", all(isinstance(c[s][1], section) for s in ("temperature", "funzionamento", "altro")))
    b.v("la sezione «altro» parte chiusa, le altre aperte",
        c["altro"][1].options["collapsed"] and not c["temperature"][1].options["collapsed"])
    b.v("mandata proposta dal nome", suggerito(r, "temperature", "mandata") == VERE["mandata"])
    b.v("un'entita' creata da questa integrazione non viene proposta",
        suggerito(r, "temperature", "mandata") != "sensor.vecchia_temp_mandata")
    b.v("guasto proposto dalla centrale d'allarme", suggerito(r, "altro", "guasto") == VERE["guasto"])
    b.v("mandata obbligatoria, esterna facoltativa",
        type(marcatore(r, "temperature", "mandata")).__name__ == "Required"
        and type(marcatore(r, "temperature", "esterna")).__name__ == "Optional")
    selettore = c["temperature"][1].schema[marcatore(r, "temperature", "mandata")]
    b.v("il selettore della mandata cerca solo sensori", selettore.config["domain"] == ["sensor"])
    selettore = c["altro"][1].schema[marcatore(r, "altro", "boost")]
    b.v("il boost accetta switch e input_boolean", {"switch", "input_boolean"} <= set(selettore.config["domain"]))

    b.sezione("2. Invio")
    modulo = {
        "nome": "  PdC Hisense ",
        "temperature": {"mandata": VERE["mandata"], "ritorno": VERE["ritorno"], "esterna": ""},
        "funzionamento": {"portata": VERE["portata"], "compressore": VERE["compressore"]},
        "altro": {},
    }
    r = await flusso.async_step_user(modulo)
    b.v("voce creata", r["type"] == "create_entry")
    b.v("titolo ripulito dagli spazi", r["title"] == "PdC Hisense")
    b.v("nei dati le entita' in piano, senza vuoti", r["data"] == {"entita": {
        "mandata": VERE["mandata"], "ritorno": VERE["ritorno"], "portata": VERE["portata"], "compressore": VERE["compressore"]}})
    flusso = NexusPompaCaloreConfigFlow()
    flusso.hass = hass_vero()
    r = await flusso.async_step_user({"nome": "", "temperature": {"mandata": VERE["mandata"], "ritorno": VERE["ritorno"]}})
    b.v("nome vuoto: quello predefinito", r["title"] == "Centrale Termica")

    b.sezione("3. Errori")
    flusso = NexusPompaCaloreConfigFlow()
    flusso.hass = hass_vero()
    r = await flusso.async_step_user({"nome": "Doppia", "temperature": {"mandata": VERE["mandata"], "ritorno": VERE["mandata"]}})
    b.v("stessa entita' su due voci: il modulo torna con l'errore", r["type"] == "form" and r["errors"] == {"base": "entita_ripetuta"})
    b.v("il nome scritto resta", campi(r["schema"])["nome"][0].default == "Doppia")
    b.v("le scelte fatte restano, non le proposte", suggerito(r, "funzionamento", "portata") is None)
    r = await flusso.async_step_user({"nome": "X", "temperature": {"mandata": VERE["mandata"]}})
    b.v("manca il ritorno: errore", r["errors"] == {"base": "mancano_obbligatorie"})

    b.sezione("4. Opzioni")
    voce = Entry({"entita": {"mandata": VERE["mandata"], "ritorno": VERE["ritorno"], "portata": VERE["portata"]}})
    opzioni = NexusPompaCaloreOptionsFlow()
    opzioni.config_entry = voce
    r = await opzioni.async_step_init()
    c = campi(r["schema"])
    b.v("le entita' attuali sono precompilate", suggerito(r, "funzionamento", "portata") == VERE["portata"])
    b.v("una voce non collegata resta vuota (niente proposte a sorpresa)", suggerito(r, "altro", "guasto") is None)
    b.v("nelle opzioni tutte le sezioni sono aperte", not c["altro"][1].options["collapsed"])
    b.v("c'e' la sezione dell'animazione, chiusa", c["animazione"][1].options["collapsed"])
    riferimento = next(iter(c["animazione"][1].schema))
    b.v("fondo scala predefinito 20 L/min", riferimento.default == 20.0)
    r = await opzioni.async_step_init({
        "temperature": {"mandata": VERE["mandata"], "ritorno": VERE["ritorno"]},
        "funzionamento": {},
        "altro": {"guasto": VERE["guasto"]},
        "animazione": {"riferimento": 30},
    })
    b.v("opzioni salvate: entita' cambiate e fondo scala", r["type"] == "create_entry" and r["data"] == {
        "entita": {"mandata": VERE["mandata"], "ritorno": VERE["ritorno"], "guasto": VERE["guasto"]},
        "riferimento": 30.0})
    voce.options = r["data"]
    opzioni = NexusPompaCaloreOptionsFlow()
    opzioni.config_entry = voce
    r = await opzioni.async_step_init()
    b.v("riaprendo, valgono le opzioni e non i dati iniziali",
        suggerito(r, "funzionamento", "portata") is None and suggerito(r, "altro", "guasto") == VERE["guasto"])
    b.v("e il fondo scala salvato", next(iter(campi(r["schema"])["animazione"][1].schema)).default == 30.0)
    r = await opzioni.async_step_init({"temperature": {"mandata": VERE["mandata"]}, "animazione": {"riferimento": 25}})
    b.v("anche nelle opzioni mandata e ritorno sono obbligatorie", r["type"] == "form" and r["errors"] == {"base": "mancano_obbligatorie"})


asyncio.run(main())
b.fine()
