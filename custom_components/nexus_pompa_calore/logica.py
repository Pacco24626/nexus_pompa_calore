"""Logica della pompa di calore senza Home Assistant: si prova a tavolino.

Qui stanno le regole che si possono sbagliare in silenzio: quali entita' proporre
per ogni voce, quando la macchina e' «in marcia», come si calcola il salto
termico e cosa fare quando un'entita' collegata viene rinominata.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Slot:
    """Una voce del sinottico: che entita' ci va e dove sta nel modulo."""

    chiave: str
    domini: tuple[str, ...]
    cerca: str  # espressione sull'object_id, per la proposta automatica
    obbligatorio: bool
    sezione: str


SEZIONI = ("temperature", "funzionamento", "altro")

SLOT: tuple[Slot, ...] = (
    Slot("mandata", ("sensor",), r"temp(eratura)?_mandata$", True, "temperature"),
    Slot("ritorno", ("sensor",), r"temp(eratura)?_ritorno$", True, "temperature"),
    Slot("esterna", ("sensor",), r"temp(eratura)?_esterna$", False, "temperature"),
    Slot("accumulo", ("sensor",), r"temp(eratura)?_accumulo", False, "temperature"),
    Slot("compressore", ("binary_sensor",), r"compressore_attivo$", False, "funzionamento"),
    Slot("frequenza", ("sensor",), r"frequenza_compressore$", False, "funzionamento"),
    Slot("portata", ("sensor",), r"portata", False, "funzionamento"),
    Slot("sbrinamento", ("binary_sensor",), r"sbrinamento", False, "funzionamento"),
    Slot("cop_riscaldamento", ("sensor",), r"cop_riscaldamento$", False, "altro"),
    Slot("cop_sanitario", ("sensor",), r"cop_sanitario$", False, "altro"),
    Slot("boost", ("switch", "input_boolean", "binary_sensor"), r"boost_acs$", False, "altro"),
    Slot("vacanza", ("switch", "input_boolean", "binary_sensor"), r"vacanza", False, "altro"),
    Slot("guasto", ("binary_sensor",), r"guasto_pdc$", False, "altro"),
)
CHIAVI = tuple(slot.chiave for slot in SLOT)
OBBLIGATORI = tuple(slot.chiave for slot in SLOT if slot.obbligatorio)

# Sotto mezzo litro al minuto l'acqua e' ferma: e' il rumore del flussimetro.
SOGLIA_PORTATA = 0.5

_NON_VALIDI = {"unknown", "unavailable", "none", ""}


# -----------------------------------------------------------------------------
# Configurazione
# -----------------------------------------------------------------------------
def _dividi(entity_id: str) -> tuple[str, str]:
    dominio, _, oggetto = entity_id.partition(".")
    return dominio, oggetto


def proposte(entity_ids: Iterable[str], escludi: Iterable[str] = ()) -> dict[str, str]:
    """Le entita' che sembrano quelle giuste per ogni voce, riconosciute dal nome.

    E' solo una proposta per il modulo. Fra piu' candidati vince quello con lo
    stesso prefisso della mandata (quasi certamente la stessa macchina), poi
    l'ordine alfabetico: la proposta non cambia da un'apertura all'altra.
    """
    esclusi = set(escludi)
    tutte = sorted(e for e in entity_ids if "." in e and e not in esclusi)
    scelte: dict[str, str] = {}
    prefisso = ""
    for slot in SLOT:
        candidati = [
            e
            for e in tutte
            if _dividi(e)[0] in slot.domini and re.search(slot.cerca, _dividi(e)[1])
        ]
        if not candidati:
            continue
        if prefisso:
            candidati.sort(key=lambda e: (not _dividi(e)[1].startswith(prefisso), e))
        scelta = candidati[0]
        scelte[slot.chiave] = scelta
        if slot.chiave == "mandata":
            oggetto = _dividi(scelta)[1]
            trovato = re.search(slot.cerca, oggetto)
            prefisso = oggetto[: trovato.start()] if trovato else ""
    return scelte


def entita_da_modulo(dati: Mapping[str, Any]) -> dict[str, str]:
    """Le entita' scelte nel modulo, tolte dalle sezioni e senza i campi vuoti."""
    entita: dict[str, str] = {}
    for sezione in SEZIONI:
        for chiave, valore in (dati.get(sezione) or {}).items():
            if chiave in CHIAVI and isinstance(valore, str) and valore.strip():
                entita[chiave] = valore.strip()
    return entita


def errori_entita(entita: Mapping[str, str]) -> dict[str, str]:
    """Gli errori del modulo, nel formato di Home Assistant (vuoto se va bene)."""
    if any(chiave not in entita for chiave in OBBLIGATORI):
        return {"base": "mancano_obbligatorie"}
    valori = list(entita.values())
    if len(valori) != len(set(valori)):
        return {"base": "entita_ripetuta"}
    return {}


def rinomina(entita: Mapping[str, str], vecchio: str, nuovo: str) -> dict[str, str] | None:
    """Le entita' con un id rinominato, o None se il rinominato non e' fra le nostre."""
    if not vecchio or not nuovo or vecchio == nuovo or vecchio not in entita.values():
        return None
    return {chiave: (nuovo if valore == vecchio else valore) for chiave, valore in entita.items()}


# -----------------------------------------------------------------------------
# Valori
# -----------------------------------------------------------------------------
def numero(stato: str | None) -> float | None:
    """Il numero di uno stato grezzo, o None se non c'e' o non e' un numero."""
    if stato is None:
        return None
    testo = str(stato).strip()
    if testo.lower() in _NON_VALIDI:
        return None
    try:
        valore = float(testo.replace(",", "."))
    except ValueError:
        return None
    return valore if valore == valore and abs(valore) != float("inf") else None


def acceso(stato: str | None) -> bool | None:
    """True se «on», False se «off», None se non si puo' dire."""
    if stato is None:
        return None
    testo = str(stato).strip().lower()
    if testo == "on":
        return True
    if testo == "off":
        return False
    return None


def salto_termico(mandata: str | None, ritorno: str | None) -> float | None:
    """Mandata meno ritorno, al decimo. Negativo se il ritorno e' piu' caldo."""
    m = numero(mandata)
    r = numero(ritorno)
    if m is None or r is None:
        return None
    return round(m - r, 1)


def stato_impianto(letture: Mapping[str, str | None]) -> str | None:
    """Lo stato della macchina dalle letture grezze delle voci configurate.

    Guasto e sbrinamento vincono su tutto. Poi decide la prima fonte leggibile
    fra compressore, frequenza e portata: una fonte non disponibile non dice
    «fermo», passa la parola alla successiva. Se nessuna si legge: None.
    """
    if acceso(letture.get("guasto")) is True:
        return "guasto"
    if acceso(letture.get("sbrinamento")) is True:
        return "sbrinamento"

    if "compressore" in letture:
        valore = acceso(letture["compressore"])
        if valore is not None:
            return "in_marcia" if valore else "fermo"
    if "frequenza" in letture:
        valore = numero(letture["frequenza"])
        if valore is not None:
            return "in_marcia" if valore > 0 else "fermo"
    if "portata" in letture:
        valore = numero(letture["portata"])
        if valore is not None:
            return "in_marcia" if valore > SOGLIA_PORTATA else "fermo"
    return None
