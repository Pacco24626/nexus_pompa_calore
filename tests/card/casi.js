/**
 * I casi di prova della card: un finto Home Assistant con i valori veri
 * dell'impianto e il sensore «Mappa impianto» come lo scrive l'integrazione.
 * I valori calcolati (stato, salto termico) sono quelli che danno le prove
 * Python sugli stessi numeri.
 */

export const MAPPA = "sensor.centrale_termica_mappa_impianto";

const PDC = "sensor.pompa_di_calore_pdc_";
export const ENTITA = {
  mandata: `${PDC}temp_mandata`,
  ritorno: `${PDC}temp_ritorno`,
  esterna: `${PDC}temp_esterna`,
  accumulo: `${PDC}temp_accumulo_acs`,
  portata: `${PDC}portata_acqua`,
  frequenza: `${PDC}frequenza_compressore`,
  cop_riscaldamento: `${PDC}cop_riscaldamento`,
  cop_sanitario: `${PDC}cop_sanitario`,
  compressore: "binary_sensor.pompa_di_calore_pdc_compressore_attivo",
  sbrinamento: "binary_sensor.pompa_di_calore_pdc_sbrinamento_attivo",
  boost: "switch.pompa_di_calore_boost_acs",
  vacanza: "switch.pompa_di_calore_pdc_modalita_vacanza_2",
  guasto: "binary_sensor.centrale_tecnoalarm_guasto_pdc",
};

const UNITA = {
  mandata: "°C", ritorno: "°C", esterna: "°C", accumulo: "°C", portata: "L/min", frequenza: "Hz",
};

function stato(entity_id, state, attributes = {}) {
  return { entity_id, state: String(state), attributes };
}

function stati(valori, derivate, { entita = ENTITA, nome = "Centrale Termica", riferimento = 20 } = {}) {
  const tutti = {};
  Object.entries(entita).forEach(([slot, id]) => {
    if (valori[slot] === undefined) return;
    tutti[id] = stato(id, valori[slot], UNITA[slot] ? { unit_of_measurement: UNITA[slot] } : {});
  });
  tutti[MAPPA] = stato(MAPPA, Object.keys(entita).length, {
    ruolo: "mappa_pompa_calore",
    nome,
    entita: { ...entita },
    opzioni: { riferimento },
    derivate,
  });
  return tutti;
}

export const CASI = {
  fermo: {
    titolo: "Di notte, tutto fermo (valori veri del 16/09)",
    stati: stati(
      { mandata: 29.5, ritorno: 28.5, esterna: 19, accumulo: 48.5, portata: 0, frequenza: 0, cop_riscaldamento: 0, cop_sanitario: 2.92,
        compressore: "off", sbrinamento: "off", boost: "off", vacanza: "off", guasto: "off" },
      { stato: "fermo", salto_termico: 1.0 }
    ),
  },
  marcia: {
    titolo: "In marcia sull'ACS",
    stati: stati(
      { mandata: 52.4, ritorno: 45.1, esterna: 7.5, accumulo: 51.2, portata: 13.6, frequenza: 46, cop_riscaldamento: 3.4, cop_sanitario: 2.91,
        compressore: "on", sbrinamento: "off", boost: "on", vacanza: "off", guasto: "off" },
      { stato: "in_marcia", salto_termico: 7.3 }
    ),
  },
  sbrinamento: {
    titolo: "Sbrinamento con guasto, accumulo non disponibile",
    stati: stati(
      { mandata: 24.1, ritorno: 26.8, esterna: -1.5, accumulo: "unavailable", portata: 9.2, frequenza: 30, cop_riscaldamento: 1.8, cop_sanitario: 2.4,
        compressore: "on", sbrinamento: "on", boost: "off", vacanza: "on", guasto: "on" },
      { stato: "guasto", salto_termico: -2.7 }
    ),
  },
  senza_portata: {
    titolo: "Solo mandata, ritorno e compressore (niente portata)",
    stati: stati(
      { mandata: 40, ritorno: 35, compressore: "on" },
      { stato: "in_marcia", salto_termico: 5.0 },
      { entita: { mandata: ENTITA.mandata, ritorno: ENTITA.ritorno, compressore: ENTITA.compressore }, nome: "PdC piccola" }
    ),
  },
};

/** Un finto hass: gli stati del caso, piu' cio' che la card usa davvero. */
export function fintoHass(stati, scuro = false) {
  return {
    states: stati,
    locale: { language: "it" },
    themes: { darkMode: scuro },
    formatEntityState: (st) => {
      const unita = st.attributes.unit_of_measurement;
      if (st.state === "on") return "Attivo";
      if (st.state === "off") return "Inattivo";
      if (st.state === "unavailable") return "Non disponibile";
      const numero = Number(st.state);
      const testo = Number.isFinite(numero) ? numero.toLocaleString("it-IT") : st.state;
      return unita ? `${testo} ${unita}` : testo;
    },
  };
}
