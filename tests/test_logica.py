"""Prove a tavolino della logica: proposte, stato della macchina, salto termico.

    python tests/test_logica.py
"""

from __future__ import annotations

import finto_ha  # noqa: F401  (prepara i moduli e il percorso)
from finto_ha import Banco

from nexus_pompa_calore.logica import (
    OBBLIGATORI,
    SLOT,
    acceso,
    entita_da_modulo,
    errori_entita,
    numero,
    proposte,
    rinomina,
    salto_termico,
    stato_impianto,
)

b = Banco("LOGICA")

# Le entita' vere dell'impianto del 16/09, piu' qualche intruso plausibile.
IMPIANTO = [
    "binary_sensor.centrale_tecnoalarm_guasto_pdc",
    "binary_sensor.pompa_di_calore_pdc_compressore_attivo",
    "binary_sensor.pompa_di_calore_pdc_sbrinamento_attivo",
    "sensor.pompa_di_calore_pdc_cop_riscaldamento",
    "sensor.pompa_di_calore_pdc_cop_sanitario",
    "sensor.pompa_di_calore_pdc_frequenza_compressore",
    "sensor.pompa_di_calore_pdc_portata_acqua",
    "sensor.pompa_di_calore_pdc_temp_accumulo_acs",
    "sensor.pompa_di_calore_pdc_temp_esterna",
    "sensor.pompa_di_calore_pdc_temp_mandata",
    "sensor.pompa_di_calore_pdc_temp_ritorno",
    "switch.pompa_di_calore_boost_acs",
    "switch.pompa_di_calore_pdc_modalita_vacanza_2",
    "light.salotto",
    "sensor.giardino_portata_irrigazione",
    "sensor.caldaia_vecchia_temp_mandata",
    "sensor.caldaia_vecchia_temp_ritorno",
    "sensor.centrale_termica_stato",
]

b.sezione("1. Proposte dal nome")
p = proposte(IMPIANTO)
b.v("con due macchine la mandata e' la prima in ordine alfabetico: e' solo una proposta",
    p["mandata"] == "sensor.caldaia_vecchia_temp_mandata")
p_vera = proposte([e for e in IMPIANTO if "caldaia" not in e])
b.v("senza caldaia: tutte le tredici voci trovate", len(p_vera) == 13)
b.v("il compressore e' il binario giusto", p_vera["compressore"] == "binary_sensor.pompa_di_calore_pdc_compressore_attivo")
b.v("il guasto viene dalla centrale d'allarme", p_vera["guasto"] == "binary_sensor.centrale_tecnoalarm_guasto_pdc")
b.v("la portata e' quella della pompa di calore anche se l'irrigazione viene prima in ordine alfabetico",
    p_vera["portata"] == "sensor.pompa_di_calore_pdc_portata_acqua")
con_caldaia = proposte(IMPIANTO)
b.v("con due macchine le voci seguono il prefisso della mandata scelta",
    con_caldaia["ritorno"].startswith(con_caldaia["mandata"].rsplit("temp_mandata", 1)[0]))
b.v("un'entita' esclusa non viene proposta",
    "mandata" not in proposte(["sensor.x_temp_mandata"], escludi=["sensor.x_temp_mandata"]))
b.v("il dominio conta: uno switch non e' una temperatura", "mandata" not in proposte(["switch.pompa_temp_mandata"]))
b.v("nessuna entita', nessuna proposta", proposte([]) == {})
b.v("la proposta non cambia con l'ordine di arrivo", proposte(IMPIANTO) == proposte(list(reversed(IMPIANTO))))

b.sezione("2. Modulo")
modulo = {
    "nome": "Centrale Termica",
    "temperature": {"mandata": "sensor.m", "ritorno": "sensor.r", "esterna": ""},
    "funzionamento": {"portata": " sensor.p "},
    "altro": {},
}
e = entita_da_modulo(modulo)
b.v("le sezioni diventano una mappa piatta", e == {"mandata": "sensor.m", "ritorno": "sensor.r", "portata": "sensor.p"})
b.v("i campi vuoti non entrano", "esterna" not in e)
b.v("una chiave sconosciuta non entra", "intrusa" not in entita_da_modulo({"temperature": {"intrusa": "sensor.x"}}))
b.v("mandata e ritorno sono le obbligatorie", set(OBBLIGATORI) == {"mandata", "ritorno"})
b.v("senza ritorno: errore", errori_entita({"mandata": "sensor.m"}) == {"base": "mancano_obbligatorie"})
b.v("la stessa entita' su due voci: errore",
    errori_entita({"mandata": "sensor.m", "ritorno": "sensor.m"}) == {"base": "entita_ripetuta"})
b.v("modulo giusto: nessun errore", errori_entita(e) == {})
b.v("ogni voce ha una sezione valida", all(s.sezione in ("temperature", "funzionamento", "altro") for s in SLOT))

b.sezione("3. Rinomina")
mappa = {"mandata": "sensor.m", "ritorno": "sensor.r"}
b.v("l'entita' rinominata cambia nella mappa", rinomina(mappa, "sensor.r", "sensor.ritorno") == {"mandata": "sensor.m", "ritorno": "sensor.ritorno"})
b.v("un'entita' non nostra non tocca niente", rinomina(mappa, "sensor.altro", "sensor.nuovo") is None)
b.v("rinomina su se stessa: niente da fare", rinomina(mappa, "sensor.m", "sensor.m") is None)
b.v("la mappa originale resta com'era", mappa == {"mandata": "sensor.m", "ritorno": "sensor.r"})

b.sezione("4. Letture")
b.v("numero con la virgola", numero("12,5") == 12.5)
b.v("«unavailable» non e' zero", numero("unavailable") is None)
b.v("testo non numerico", numero("acceso") is None)
b.v("«nan» non passa", numero("nan") is None)
b.v("acceso su «on»", acceso("on") is True)
b.v("spento su «off»", acceso("off") is False)
b.v("non si sa su «unavailable»", acceso("unavailable") is None)

b.sezione("5. Salto termico")
b.v("mandata meno ritorno", salto_termico("52.4", "45.1") == 7.3)
b.v("negativo quando il ritorno e' piu' caldo (sbrinamento)", salto_termico("24.1", "26.8") == -2.7)
b.v("un capo non disponibile: niente salto", salto_termico("52.4", "unavailable") is None)
b.v("caso vero di notte", salto_termico("29.5", "28.5") == 1.0)

b.sezione("6. Stato della macchina")
b.v("compressore acceso: in marcia", stato_impianto({"compressore": "on"}) == "in_marcia")
b.v("compressore spento: fermo", stato_impianto({"compressore": "off", "portata": "0"}) == "fermo")
b.v("il guasto vince su tutto", stato_impianto({"compressore": "on", "guasto": "on", "sbrinamento": "on"}) == "guasto")
b.v("lo sbrinamento vince sulla marcia", stato_impianto({"compressore": "on", "sbrinamento": "on"}) == "sbrinamento")
b.v("guasto spento non conta", stato_impianto({"compressore": "on", "guasto": "off"}) == "in_marcia")
b.v("compressore non disponibile: decide la frequenza",
    stato_impianto({"compressore": "unavailable", "frequenza": "46"}) == "in_marcia")
b.v("senza compressore: frequenza a zero e' fermo", stato_impianto({"frequenza": "0"}) == "fermo")
b.v("solo portata, sopra la soglia: in marcia", stato_impianto({"portata": "9.2"}) == "in_marcia")
b.v("solo portata, rumore del flussimetro: fermo", stato_impianto({"portata": "0.3"}) == "fermo")
b.v("nessuna fonte leggibile: non si sa", stato_impianto({"compressore": "unknown", "portata": "unavailable"}) is None)
b.v("nessuna fonte configurata: non si sa", stato_impianto({"mandata": "30"}) is None)
b.v("guasto non disponibile non inventa un guasto", stato_impianto({"guasto": "unavailable", "compressore": "off"}) == "fermo")

b.fine()
