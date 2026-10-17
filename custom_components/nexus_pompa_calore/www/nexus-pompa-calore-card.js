/**
 * Nexus Pompa di Calore — card del sinottico animato.
 *
 * Unita' esterna, riscaldamento e accumulo ACS: il flusso nelle tubazioni va
 * alla velocita' della portata, la ventola alla frequenza del compressore, il
 * bollitore cambia colore con la temperatura.
 *
 * La card non si configura con le entita': legge il sensore «Mappa impianto»
 * dell'integrazione, dove stanno le entita' collegate, le opzioni e i valori
 * calcolati (stato e salto termico). Il disegno sta dentro la card:
 * scala con la plancia, segue il tema chiaro o scuro, e le animazioni vanno
 * alla velocita' che dicono i sensori.
 *
 * Le funzioni di calcolo sono esportate e si provano a tavolino: tests/test_card.mjs
 */

const VERSIONE_CARD = "1.1.0";
const DOMINIO = "nexus_pompa_calore";
const RUOLO_MAPPA = "mappa_pompa_calore";
const NOME_INTEGRAZIONE = "Nexus Pompa di Calore";
const DESCRIZIONE_CARD = "Centrale termica animata: flusso, ventola e accumulo si muovono con i valori veri della pompa di calore.";

// -----------------------------------------------------------------------------
// Logica: tutto cio' che si puo' sbagliare in silenzio, e che si prova da solo
// -----------------------------------------------------------------------------
const NON_VALIDI = new Set(["unknown", "unavailable", "none", ""]);

/** Il numero di uno stato di Home Assistant, o null se non e' un numero. */
export function numero(stato) {
  if (stato === null || stato === undefined) return null;
  const grezzo = typeof stato === "object" ? stato.state : stato;
  if (grezzo === null || grezzo === undefined) return null;
  const testo = String(grezzo).trim();
  if (NON_VALIDI.has(testo.toLowerCase())) return null;
  const valore = Number(testo.replace(",", "."));
  return Number.isFinite(valore) ? valore : null;
}

/** Vero se lo stato c'e' ed e' utilizzabile (non sconosciuto, non non-disponibile). */
export function valido(stato) {
  if (!stato || stato.state === undefined) return false;
  return !NON_VALIDI.has(String(stato.state).trim().toLowerCase());
}

/** Vero se un binario e' acceso. */
export function acceso(stato) {
  return Boolean(stato) && String(stato.state).toLowerCase() === "on";
}

// Un ciclo di tratteggio nel disegno: trattino 18 + spazio 26 unita'.
export const PERIODO_TRATTEGGIO = 44;
const VELOCITA_MINIMA = 20; // unita' del disegno al secondo, a impianto appena acceso
const VELOCITA_MASSIMA = 150; // a fondo scala

/**
 * Quanto conta il valore rispetto al fondo scala: 0 (fermo) .. 1 (pieno).
 * Oltre il fondo scala resta 1: il disegno non puo' andare piu' veloce del vero.
 */
export function frazione(valore, riferimento, soglia = 0) {
  const v = Math.abs(numero(valore) ?? NaN);
  if (!Number.isFinite(v) || v <= soglia) return 0;
  const rif = Math.abs(Number(riferimento)) || 1;
  return Math.min(v / rif, 1);
}

/**
 * La durata di un ciclo di tratteggio, in secondi, o null se il flusso e' fermo.
 * Piu' il valore e' alto, piu' il ciclo e' breve: i trattini corrono.
 */
export function durataFlusso(valore, riferimento, soglia = 0) {
  const f = frazione(valore, riferimento, soglia);
  if (f === 0) return null;
  const velocita = VELOCITA_MINIMA + (VELOCITA_MASSIMA - VELOCITA_MINIMA) * f;
  return Math.round((PERIODO_TRATTEGGIO / velocita) * 1000) / 1000;
}

/** La durata di un giro di ventola, in secondi, o null se il compressore e' fermo. */
export function durataVentola(hz, compressoreAcceso) {
  if (!compressoreAcceso) return null;
  const f = numero(hz);
  if (f === null || f <= 0) return 1.2; // acceso ma senza frequenza: giro di cortesia
  return Math.round(Math.min(Math.max(28 / f, 0.5), 4) * 100) / 100;
}

/** Il colore dell'acqua dell'accumulo: freddo blu, tiepido ambra, caldo rosso. */
export function coloreAcs(temperatura) {
  const t = numero(temperatura);
  if (t === null) return null;
  const scala = [
    [25, "#3C84C6"],
    [38, "#5BA8C9"],
    [45, "#E39B32"],
    [52, "#DE4A51"],
  ];
  if (t <= scala[0][0]) return scala[0][1];
  for (let i = 1; i < scala.length; i += 1) {
    if (t <= scala[i][0]) return scala[i][1];
  }
  return scala[scala.length - 1][1];
}

// -----------------------------------------------------------------------------
// Stile: colori del tema, animazioni, e il rispetto di chi non vuole movimento
// -----------------------------------------------------------------------------
const STILE = `
:host { display: block; }
ha-card { overflow: hidden; }
.testata {
  padding: 14px 18px 2px;
  font-size: var(--ha-card-header-font-size, 22px);
  font-weight: 500;
  line-height: 1.2;
  color: var(--ha-card-header-color, var(--primary-text-color));
}
.corpo { padding: 8px 8px 10px; }
svg { display: block; width: 100%; height: auto; }

.tessere { display: flex; flex-wrap: wrap; gap: 8px; padding: 2px 10px 6px; }
.tessere:empty { display: none; }
.tessera {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 5px 12px; border-radius: 999px;
  font-size: 13px; font-weight: 600; line-height: 1.3;
  background: var(--ns-tessera-fondo, rgba(86,97,111,0.10));
  color: var(--ns-tessera-testo, #56616F);
  border: 1px solid var(--ns-tessera-bordo, rgba(86,97,111,0.22));
}
.tessera.avviso { --ns-tessera-fondo: rgba(222,74,81,0.12); --ns-tessera-testo: #C93C43; --ns-tessera-bordo: rgba(222,74,81,0.35); }
.tessera.freddo { --ns-tessera-fondo: rgba(60,132,198,0.12); --ns-tessera-testo: #2F6FA8; --ns-tessera-bordo: rgba(60,132,198,0.35); }
.tessera.caldo  { --ns-tessera-fondo: rgba(227,155,50,0.14); --ns-tessera-testo: #B7761C; --ns-tessera-bordo: rgba(227,155,50,0.38); }
.tessera.buono  { --ns-tessera-fondo: rgba(46,158,107,0.12); --ns-tessera-testo: #2E9E6B; --ns-tessera-bordo: rgba(46,158,107,0.35); }
.tessera.allarme { animation: ns-pulsa 1.8s ease-in-out infinite; }

.scena {
  --ns-fondo: #F4F8FC;
  --ns-riquadro: #FFFFFF;
  --ns-bordo: #E1E6EC;
  --ns-testo: #1F2933;
  --ns-etichetta: #56616F;
  --ns-metallo-chiaro: #FFFFFF;
  --ns-metallo: #E9EDF2;
  --ns-metallo-scuro: #DCE2E9;
  --ns-interno: #EEF2F6;
  --ns-bordo-metallo: #C5CED8;
  --ns-linea: #8C98A5;
  --ns-muro: #F1F4F8;
  --ns-vetro: #E3EDF7;
}
.scena.scuro {
  --ns-fondo: #151B22;
  --ns-riquadro: #1E262F;
  --ns-bordo: #2E3945;
  --ns-testo: #E8ECF1;
  --ns-etichetta: #9AA5B1;
  --ns-metallo-chiaro: #2B343E;
  --ns-metallo: #232B34;
  --ns-metallo-scuro: #1B222A;
  --ns-interno: #273039;
  --ns-bordo-metallo: #3A4653;
  --ns-linea: #6B7A89;
  --ns-muro: #222A33;
  --ns-vetro: #26313D;
}

.avviso-mappa { padding: 18px 20px; color: var(--secondary-text-color, #56616F); line-height: 1.5; }
.riquadro { cursor: pointer; }
.riquadro .sfondo { transition: stroke 0.15s ease; }
.riquadro:hover .sfondo { stroke: var(--ns-linea); }
.riquadro[hidden] { display: none; }

.flusso { stroke-dasharray: 18 26; stroke-linecap: round; opacity: 0; }
.flusso.in-moto { opacity: 1; animation: ns-scorri 1.2s linear infinite; }
.flusso.contro.in-moto { animation-direction: reverse; }
@keyframes ns-scorri { to { stroke-dashoffset: -${PERIODO_TRATTEGGIO}; } }

.ventola { transform-box: fill-box; transform-origin: center; }
.ventola.in-moto { animation: ns-gira 1.2s linear infinite; }
@keyframes ns-gira { to { transform: rotate(360deg); } }

.raggi { transform-box: fill-box; transform-origin: center; }
.raggi.in-moto { animation: ns-gira 40s linear infinite; }

.respira.in-moto { animation: ns-respira 2.6s ease-in-out infinite; }
@keyframes ns-respira { 0%, 100% { opacity: 0.45; } 50% { opacity: 1; } }
@keyframes ns-pulsa { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }

.spia.acceso { animation: ns-pulsa 2.2s ease-in-out infinite; }

@media (prefers-reduced-motion: reduce) {
  .flusso.in-moto, .ventola.in-moto, .raggi.in-moto, .respira.in-moto,
  .spia.acceso, .tessera.allarme { animation: none; }
  .respira.in-moto { opacity: 1; }
}
.senza-moto .flusso.in-moto, .senza-moto .ventola.in-moto, .senza-moto .raggi.in-moto,
.senza-moto .respira.in-moto, .senza-moto .spia.acceso { animation: none; }
.senza-moto .respira.in-moto { opacity: 1; }
`;

// -----------------------------------------------------------------------------
// Pezzi di disegno comuni
// -----------------------------------------------------------------------------
const DEFS_COMUNI = `
  <linearGradient id="ns-lamiera" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" style="stop-color:var(--ns-metallo-chiaro)"/>
    <stop offset="1" style="stop-color:var(--ns-metallo)"/>
  </linearGradient>
  <filter id="ns-ombra" x="-20%" y="-20%" width="140%" height="160%">
    <feDropShadow dx="0" dy="3" stdDeviation="5" flood-color="#1F2933" flood-opacity="0.09"/>
  </filter>
  <g id="ns-freccia">
    <path d="M-6 -8 L4 0 L-6 8" fill="none" stroke="#FFFFFF" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round"/>
  </g>`;

/** Un riquadro di valore: etichetta in alto, numero sotto, tutto cliccabile. */
function riquadro({ slot, x, y, larghezza, altezza, etichetta, colore, coloreEtichetta, piccolo }) {
  const dimEtichetta = piccolo ? 19 : 24;
  const dimValore = piccolo ? 27 : 34;
  const baseEtichetta = y + (piccolo ? 30 : 36);
  const baseValore = y + (piccolo ? 66 : 78);
  return `
  <g class="riquadro" data-slot="${slot}">
    <rect class="sfondo" x="${x}" y="${y}" width="${larghezza}" height="${altezza}" rx="16"
          fill="var(--ns-riquadro)" stroke="var(--ns-bordo)" stroke-width="2" filter="url(#ns-ombra)"/>
    <rect x="${x}" y="${y + 16}" width="6" height="${altezza - 32}" rx="3" fill="${colore}"/>
    <text x="${x + 22}" y="${baseEtichetta}" font-size="${dimEtichetta}" font-weight="700"
          letter-spacing="1.2" fill="${coloreEtichetta || colore}">${etichetta}</text>
    <text class="valore" data-valore="${slot}" x="${x + 22}" y="${baseValore}" font-size="${dimValore}"
          font-weight="700" fill="var(--ns-testo)" data-dim="${dimValore}" data-min="${piccolo ? 13 : 15}"
          data-spazio="${larghezza - 40}">&#8212;</text>
  </g>`;
}

// -----------------------------------------------------------------------------
// Scena: pompa di calore (centrale termica)
// -----------------------------------------------------------------------------
const MANDATA_D = "M330 300 H400 V150 H960 V550 H900 M600 150 V320 H672";
const RITORNO_D = "M330 450 H430 V700 H680 M520 700 V375 H672";

function scenaPompaDiCalore() {
  return `
<svg viewBox="0 0 1000 880" preserveAspectRatio="xMidYMid meet" xmlns="http://www.w3.org/2000/svg"
     font-family="var(--ha-font-family-body, Roboto, system-ui, sans-serif)">
  <defs>
    ${DEFS_COMUNI}
    <linearGradient id="ns-bollitore" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" style="stop-color:var(--ns-metallo-scuro)"/>
      <stop offset="0.35" style="stop-color:var(--ns-metallo-chiaro)"/>
      <stop offset="1" style="stop-color:var(--ns-metallo-scuro)"/>
    </linearGradient>
  </defs>

  <rect width="1000" height="880" rx="12" fill="var(--ns-fondo)"/>

  <!-- Tubazioni: mandata (rosso) sopra e a destra, ritorno (blu) sotto e al centro -->
  <g fill="none" stroke-linecap="round" stroke-linejoin="round">
    <path d="${MANDATA_D}" stroke="#DE4A51" stroke-width="16"/>
    <path d="${MANDATA_D}" stroke="#FF9EA2" stroke-width="4" opacity="0.55"/>
    <path class="flusso" data-flusso="mandata" d="${MANDATA_D}" stroke="#FFE1E2" stroke-width="9"/>
    <path d="${RITORNO_D}" stroke="#3C84C6" stroke-width="16"/>
    <path d="${RITORNO_D}" stroke="#A3CBF0" stroke-width="4" opacity="0.55"/>
    <path class="flusso contro" data-flusso="ritorno" d="${RITORNO_D}" stroke="#DCEDFC" stroke-width="9"/>
  </g>
  <use href="#ns-freccia" transform="translate(400 225) rotate(-90)"/>
  <use href="#ns-freccia" transform="translate(720 150)"/>
  <use href="#ns-freccia" transform="translate(880 150)"/>
  <use href="#ns-freccia" transform="translate(960 360) rotate(90)"/>
  <use href="#ns-freccia" transform="translate(600 238) rotate(90)"/>
  <use href="#ns-freccia" transform="translate(600 375) rotate(180)"/>
  <use href="#ns-freccia" transform="translate(520 540) rotate(90)"/>
  <use href="#ns-freccia" transform="translate(620 700) rotate(180)"/>
  <use href="#ns-freccia" transform="translate(478 700) rotate(180)"/>
  <use href="#ns-freccia" transform="translate(430 580) rotate(-90)"/>

  <!-- Pompa di calore, unita' esterna -->
  <text x="185" y="212" text-anchor="middle" font-size="25" font-weight="700" letter-spacing="1.5" fill="var(--ns-etichetta)">POMPA DI CALORE</text>
  <ellipse cx="185" cy="514" rx="150" ry="11" fill="#1F2933" opacity="0.07"/>
  <rect x="68" y="490" width="42" height="16" rx="4" fill="var(--ns-bordo-metallo)"/>
  <rect x="262" y="490" width="42" height="16" rx="4" fill="var(--ns-bordo-metallo)"/>
  <rect x="40" y="240" width="290" height="252" rx="20" fill="url(#ns-lamiera)" stroke="var(--ns-bordo-metallo)" stroke-width="3"/>
  <circle cx="150" cy="366" r="84" fill="var(--ns-interno)" stroke="var(--ns-bordo-metallo)" stroke-width="3"/>
  <g transform="translate(150 366)">
    <g class="ventola" data-ventola="pdc">
      <circle r="70" fill="none"/>
      <g fill="var(--ns-bordo-metallo)">
        <path d="M0 -8 C 20 -40, 58 -44, 64 -20 C 44 -18, 20 -12, 0 -8 Z"/>
        <path d="M0 -8 C 20 -40, 58 -44, 64 -20 C 44 -18, 20 -12, 0 -8 Z" transform="rotate(120)"/>
        <path d="M0 -8 C 20 -40, 58 -44, 64 -20 C 44 -18, 20 -12, 0 -8 Z" transform="rotate(240)"/>
      </g>
    </g>
    <circle r="66" fill="none" stroke="var(--ns-bordo-metallo)" stroke-width="2" opacity="0.7"/>
    <circle r="44" fill="none" stroke="var(--ns-bordo-metallo)" stroke-width="2" opacity="0.7"/>
    <circle r="13" fill="var(--ns-linea)"/>
  </g>
  <rect x="252" y="264" width="58" height="204" rx="9" fill="var(--ns-interno)" stroke="var(--ns-bordo-metallo)" stroke-width="2"/>
  <g stroke="var(--ns-bordo-metallo)" stroke-width="5" stroke-linecap="round">
    <line x1="266" y1="290" x2="296" y2="290"/>
    <line x1="266" y1="312" x2="296" y2="312"/>
    <line x1="266" y1="334" x2="296" y2="334"/>
    <line x1="266" y1="356" x2="296" y2="356"/>
    <line x1="266" y1="378" x2="296" y2="378"/>
    <line x1="266" y1="400" x2="296" y2="400"/>
    <line x1="266" y1="422" x2="296" y2="422"/>
    <line x1="266" y1="444" x2="296" y2="444"/>
  </g>
  <circle class="spia" data-spia="compressore" cx="72" cy="272" r="9" fill="var(--ns-bordo-metallo)"/>
  <circle cx="330" cy="300" r="10" fill="var(--ns-linea)"/>
  <circle cx="330" cy="450" r="10" fill="var(--ns-linea)"/>

  <!-- Riscaldamento: casa con pavimento radiante -->
  <path d="M656 294 L770 210 L884 294 Z" fill="var(--ns-muro)" stroke="var(--ns-linea)" stroke-width="4" stroke-linejoin="round"/>
  <rect x="672" y="286" width="196" height="116" rx="6" fill="var(--ns-metallo-chiaro)" stroke="var(--ns-bordo-metallo)" stroke-width="3"/>
  <path class="respira" data-respira="pavimento" d="M690 390 H850 V376 H690 V362 H850" fill="none" stroke="#EE8A8F" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>
  <g class="respira" data-respira="calore" fill="none" stroke="#F4A7AA" stroke-width="4" stroke-linecap="round">
    <path d="M745 346 q-8 -9 0 -18 q8 -9 0 -18"/>
    <path d="M770 346 q-8 -9 0 -18 q8 -9 0 -18"/>
    <path d="M795 346 q-8 -9 0 -18 q8 -9 0 -18"/>
  </g>
  <text x="770" y="440" text-anchor="middle" font-size="24" font-weight="700" letter-spacing="1.5" fill="var(--ns-etichetta)">RISCALDAMENTO</text>

  <!-- Accumulo ACS -->
  <ellipse cx="790" cy="772" rx="112" ry="9" fill="#1F2933" opacity="0.07"/>
  <rect x="680" y="462" width="220" height="304" rx="72" fill="url(#ns-bollitore)" stroke="var(--ns-bordo-metallo)" stroke-width="3"/>
  <rect data-acqua="acs" x="684" y="466" width="212" height="296" rx="70" fill="#3C84C6" opacity="0"/>
  <path d="M712 690 L868 704 L712 718 L868 732" fill="none" stroke="#F2B3B6" stroke-width="5" stroke-linecap="round" stroke-linejoin="round" opacity="0.9"/>
  <text x="790" y="524" text-anchor="middle" font-size="22" font-weight="700" letter-spacing="1.2" fill="var(--ns-etichetta)">ACCUMULO ACS</text>
  <circle cx="900" cy="550" r="9" fill="var(--ns-linea)"/>
  <circle cx="680" cy="700" r="9" fill="var(--ns-linea)"/>

  ${riquadro({ slot: "esterna", x: 80, y: 30, larghezza: 210, altezza: 96, etichetta: "ESTERNA", colore: "#2E9E6B" })}
  ${riquadro({ slot: "mandata", x: 420, y: 30, larghezza: 210, altezza: 96, etichetta: "MANDATA", colore: "#DE4A51", coloreEtichetta: "#C93C43" })}
  ${riquadro({ slot: "cop_riscaldamento", x: 640, y: 24, larghezza: 145, altezza: 84, etichetta: "COP RISC.", colore: "#E07A2F", coloreEtichetta: "#B7761C", piccolo: true })}
  ${riquadro({ slot: "cop_sanitario", x: 800, y: 24, larghezza: 145, altezza: 84, etichetta: "COP ACS", colore: "#E07A2F", coloreEtichetta: "#B7761C", piccolo: true })}
  ${riquadro({ slot: "compressore", x: 40, y: 540, larghezza: 330, altezza: 96, etichetta: "COMPRESSORE", colore: "#56616F", coloreEtichetta: "var(--ns-etichetta)" })}
  ${riquadro({ slot: "frequenza", x: 40, y: 648, larghezza: 330, altezza: 96, etichetta: "FREQUENZA", colore: "#56616F", coloreEtichetta: "var(--ns-etichetta)" })}
  ${riquadro({ slot: "portata", x: 40, y: 756, larghezza: 330, altezza: 96, etichetta: "PORTATA", colore: "#3C84C6", coloreEtichetta: "#2F6FA8" })}
  ${riquadro({ slot: "ritorno", x: 455, y: 730, larghezza: 210, altezza: 96, etichetta: "RITORNO", colore: "#3C84C6", coloreEtichetta: "#2F6FA8" })}
  ${riquadro({ slot: "accumulo", x: 694, y: 584, larghezza: 192, altezza: 84, etichetta: "ACCUMULO", colore: "#E07A2F", coloreEtichetta: "#B7761C", piccolo: true })}
</svg>`;
}

// -----------------------------------------------------------------------------
// Aiuti sul disegno
// -----------------------------------------------------------------------------
function muovi(nodo, durata) {
  if (!nodo) return;
  if (durata) {
    nodo.style.animationDuration = `${durata}s`;
    nodo.classList.add("in-moto");
  } else {
    nodo.classList.remove("in-moto");
    nodo.style.removeProperty("animation-duration");
  }
}

function perDato(radice, dato) {
  const mappa = {};
  radice.querySelectorAll(`[data-${dato}]`).forEach((n) => {
    mappa[n.dataset[dato]] = n;
  });
  return mappa;
}

function riferimenti(radice) {
  return {
    valori: perDato(radice, "valore"),
    riquadri: perDato(radice, "slot"),
    flussi: perDato(radice, "flusso"),
    ventole: perDato(radice, "ventola"),
    respiri: perDato(radice, "respira"),
    spie: perDato(radice, "spia"),
    acque: perDato(radice, "acqua"),
    versi: perDato(radice, "verso"),
    livelli: perDato(radice, "livello"),
    sole: perDato(radice, "sole"),
    raggi: perDato(radice, "raggi"),
    blocchi: perDato(radice, "blocco"),
    lucidi: Array.from(radice.querySelectorAll(".lucido")),
    finestre: Array.from(radice.querySelectorAll('[data-respira^="finestra"]')),
  };
}

/**
 * Scrive il valore nel riquadro. Restituisce false se non si e' potuto misurare.
 *
 * Il disegno scala con la card, quindi su un telefono un numero da 34 unita'
 * arriverebbe a una decina di pixel. `unitaPerPixel` (quante unita' del disegno
 * stanno in un pixel) fa crescere il carattere quel tanto che basta a non
 * scendere sotto la soglia leggibile; poi, se non ci sta nel riquadro, si
 * rimpicciolisce comunque.
 */
function scriviValore(nodo, testo, unitaPerPixel = 0) {
  if (!nodo) return;
  nodo.textContent = testo;
  const minimo = Number(nodo.dataset.min) || 0;
  const base = Math.max(Number(nodo.dataset.dim) || 34, unitaPerPixel > 0 ? minimo * unitaPerPixel : 0);
  const spazio = Number(nodo.dataset.spazio) || 200;
  nodo.setAttribute("font-size", String(Math.round(base * 10) / 10));
  let larghezza = 0;
  try {
    larghezza = nodo.getComputedTextLength();
  } catch (errore) {
    larghezza = 0;
  }
  // Finche' la card non e' a video il testo non si puo' misurare: si dice a chi
  // chiama che questa misura non vale, e si riprova al primo disegno utile.
  if (larghezza <= 0) return testo === "" ;
  if (larghezza > spazio) {
    nodo.setAttribute("font-size", String(Math.max(13, Math.floor((base * spazio) / larghezza))));
  }
  return true;
}


// -----------------------------------------------------------------------------
// Come i valori muovono il disegno
// -----------------------------------------------------------------------------
const RIFERIMENTO_PREDEFINITO = 20; // L/min di fondo scala per la velocita' del flusso

function firmaScena() {
  return "pompa_di_calore";
}

function disegnaScena() {
  return scenaPompaDiCalore();
}

function aggiornaScena(ctx) {
  const { rif } = ctx;
  const compressoreAcceso = ctx.acceso("compressore");
  const portata = ctx.num("portata");
  const riferimento = ctx.riferimento();

  // Il flusso si muove se scorre acqua. Senza sensore di portata ci si affida
  // al compressore: e' meno preciso, e una tessera lo dice.
  const durata =
    portata !== null
      ? durataFlusso(portata, riferimento, 0)
      : compressoreAcceso
        ? durataFlusso(riferimento / 2, riferimento, 0)
        : null;
  muovi(rif.flussi.mandata, durata);
  muovi(rif.flussi.ritorno, durata);

  muovi(rif.ventole.pdc, durataVentola(ctx.stato("frequenza"), compressoreAcceso));

  const spia = rif.spie.compressore;
  if (spia) {
    spia.setAttribute("fill", compressoreAcceso ? "#2E9E6B" : "var(--ns-bordo-metallo)");
    spia.classList.toggle("acceso", compressoreAcceso);
  }

  // Il salto termico lo calcola l'integrazione: e' lo stesso numero del suo sensore.
  const salto = numero(ctx.derivata("salto_termico"));
  const scalda = Boolean(durata) && salto !== null && salto > 0.3;
  muovi(rif.respiri.pavimento, scalda ? 2.6 : null);
  muovi(rif.respiri.calore, scalda ? 2.6 : null);

  const acqua = rif.acque.acs;
  const colore = coloreAcs(ctx.stato("accumulo"));
  if (acqua) {
    acqua.setAttribute("fill", colore || "#3C84C6");
    acqua.setAttribute("opacity", colore ? "0.22" : "0");
  }

  if (ctx.acceso("sbrinamento")) ctx.tessera("Sbrinamento in corso", "freddo allarme");
  if (ctx.acceso("guasto")) ctx.tessera("Guasto della pompa di calore", "avviso allarme");
  if (ctx.acceso("boost")) ctx.tessera("Boost ACS", "caldo");
  if (ctx.acceso("vacanza")) ctx.tessera("Modalita' vacanza");
  if (salto !== null) {
    ctx.tessera(`Salto termico ${ctx.numeroTesto(salto, 1)} \u00B0C`, salto > 0.3 ? "caldo" : "");
  }
  if (!ctx.entita.portata && compressoreAcceso) {
    ctx.tessera("Flusso stimato dal compressore");
  }
}

// -----------------------------------------------------------------------------
// La card: tutto quello che serve lo legge dal sensore «Mappa impianto»
// -----------------------------------------------------------------------------
function testoSicuro(testo) {
  return String(testo).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);
}

/** Il sensore «Mappa impianto» di questa integrazione, se in Home Assistant ce n'e' uno. */
export function trovaMappa(hass) {
  const stati = (hass && hass.states) || {};
  return Object.keys(stati).find((id) => stati[id].attributes && stati[id].attributes.ruolo === RUOLO_MAPPA) || "";
}

class NexusPompaCaloreCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._firma = null;
    this._rif = null;
  }

  static getConfigElement() {
    return document.createElement("nexus-pompa-calore-card-editor");
  }

  static getStubConfig(hass) {
    return { entity: trovaMappa(hass) };
  }

  setConfig(config) {
    if (!config || !config.entity) {
      throw new Error(`Indica il sensore «Mappa impianto» di ${NOME_INTEGRAZIONE}`);
    }
    this._config = { ...config };
    this._firma = null;
    this._firmaTessere = null;
    this._rif = null;
    this.shadowRoot.innerHTML = "";
    if (this._hass) this._aggiorna();
  }

  set hass(hass) {
    this._hass = hass;
    this._aggiorna();
  }

  getCardSize() {
    return 12;
  }

  getGridOptions() {
    return { columns: 12, min_columns: 6, rows: "auto" };
  }

  disconnectedCallback() {
    if (this._osservatore) this._osservatore.disconnect();
  }

  connectedCallback() {
    if (this._osservatore && this._scena) this._osservatore.observe(this._scena);
    // Appena attaccata la card ha una larghezza: i numeri si rimisurano subito,
    // senza aspettare un disegno che in una scheda in secondo piano non arriva.
    this._riscriviValori();
  }

  _mappa() {
    const stato = this._hass && this._config ? this._hass.states[this._config.entity] : null;
    if (!stato || !stato.attributes || stato.attributes.ruolo !== RUOLO_MAPPA) return null;
    return stato.attributes;
  }

  _entita() {
    const mappa = this._mappa();
    return (mappa && mappa.entita) || {};
  }

  _stato(slot) {
    const id = this._entita()[slot];
    if (!id || !this._hass) return null;
    const stato = this._hass.states[id];
    return valido(stato) ? stato : null;
  }

  _testo(slot) {
    const id = this._entita()[slot];
    if (!id) return "\u2014";
    const stato = this._hass ? this._hass.states[id] : null;
    if (!stato) return "assente";
    // Anche «non disponibile» e «sconosciuto» passano da Home Assistant: e' lui
    // che li traduce nella lingua giusta.
    if (typeof this._hass.formatEntityState === "function") {
      try {
        return this._hass.formatEntityState(stato);
      } catch (errore) {
        /* si continua col ripiego */
      }
    }
    if (!valido(stato)) return "\u2014";
    const unita = stato.attributes.unit_of_measurement;
    return unita ? `${stato.state} ${unita}` : String(stato.state);
  }

  _numeroTesto(valore, decimali) {
    const lingua = (this._hass && this._hass.locale && this._hass.locale.language) || "it";
    try {
      return Number(valore).toLocaleString(lingua, { minimumFractionDigits: decimali, maximumFractionDigits: decimali });
    } catch (errore) {
      return String(valore);
    }
  }

  _titolo(mappa) {
    if (this._config.title !== undefined && this._config.title !== null) return String(this._config.title);
    return (mappa && mappa.nome) || "";
  }

  _avviso(testo) {
    const firma = `avviso|${testo}`;
    if (this._firma === firma) return;
    if (this._osservatore) this._osservatore.disconnect();
    this._firma = firma;
    this._firmaTessere = null;
    this._rif = null;
    this._scena = null;
    this.shadowRoot.innerHTML = `<style>${STILE}</style><ha-card><div class="avviso-mappa">${testoSicuro(testo)}</div></ha-card>`;
  }

  _costruisci(mappa) {
    const titolo = this._titolo(mappa);
    const radice = this.shadowRoot;
    radice.innerHTML = `<style>${STILE}</style>
      <ha-card>
        ${titolo ? `<div class="testata">${testoSicuro(titolo)}</div>` : ""}
        <div class="corpo">
          <div class="scena">${disegnaScena(mappa)}</div>
          <div class="tessere"></div>
        </div>
      </ha-card>`;
    this._scena = radice.querySelector(".scena");
    this._tessere = radice.querySelector(".tessere");
    this._firmaTessere = null;
    this._rif = riferimenti(this._scena);
    Object.entries(this._rif.riquadri).forEach(([slot, nodo]) => {
      nodo.addEventListener("click", () => this._apri(slot));
    });
    if (this._osservatore) this._osservatore.disconnect();
    if (typeof ResizeObserver !== "undefined") {
      this._osservatore = new ResizeObserver(() => this._riscriviValori());
      this._osservatore.observe(this._scena);
    }
  }

  /** Quante unita' del disegno stanno in un pixel: 0 se la card non e' ancora a video. */
  _unitaPerPixel() {
    const larghezza = this._scena ? this._scena.clientWidth : 0;
    return larghezza > 0 ? 1000 / larghezza : 0;
  }

  _riscriviValori() {
    if (!this._rif || !this._config) return;
    const entita = this._entita();
    const scala = this._unitaPerPixel();
    let misurati = true;
    Object.entries(this._rif.riquadri).forEach(([slot, nodo]) => {
      const configurato = Boolean(entita[slot]);
      nodo.hidden = !configurato;
      if (configurato && !scriviValore(this._rif.valori[slot], this._testo(slot), scala)) misurati = false;
    });
    if (this._rif.valori.soc) {
      const testo = entita.soc ? this._testo("soc") : "\u2014";
      if (!scriviValore(this._rif.valori.soc, testo, scala)) misurati = false;
    }
    // Card non ancora a video: si riprova al disegno successivo, una volta sola.
    if (!misurati && !this._attesaMisura && typeof requestAnimationFrame === "function") {
      this._attesaMisura = true;
      requestAnimationFrame(() => {
        this._attesaMisura = false;
        this._riscriviValori();
      });
    }
  }

  _apri(slot) {
    const id = this._entita()[slot];
    if (!id) return;
    // Un'entita' ritirata dal gateway non ha piu' una finestra da aprire: il
    // dialogo verrebbe su vuoto e sembrerebbe un guasto della scheda. Si
    // guarda lo stato e non il registro, perche' qui e' tutto cio' che c'e'.
    if (!this._hass || !this._hass.states[id]) return;
    this.dispatchEvent(new CustomEvent("hass-more-info", { detail: { entityId: id }, bubbles: true, composed: true }));
  }

  _aggiorna() {
    if (!this._config || !this._hass) return;
    const mappa = this._mappa();
    if (!mappa) {
      const stato = this._hass.states[this._config.entity];
      if (!stato) {
        this._avviso(`${this._config.entity} non esiste: controlla l'integrazione ${NOME_INTEGRAZIONE}.`);
      } else if (stato.attributes && stato.attributes.ruolo) {
        this._avviso(`${this._config.entity} non e' una mappa di ${NOME_INTEGRAZIONE}.`);
      } else {
        this._avviso(`Mappa non disponibile: l'integrazione ${NOME_INTEGRAZIONE} non e' caricata.`);
      }
      return;
    }

    const firma = `${firmaScena(mappa)}|${this._titolo(mappa)}`;
    if (firma !== this._firma) {
      this._firma = firma;
      this._costruisci(mappa);
    }

    this._scena.classList.toggle("scuro", Boolean(this._hass.themes && this._hass.themes.darkMode));
    this._scena.classList.toggle("senza-moto", this._config.animazioni === false);
    this._riscriviValori();

    const tessere = [];
    const opzioni = mappa.opzioni || {};
    const ctx = {
      hass: this._hass,
      mappa,
      rif: this._rif,
      entita: mappa.entita || {},
      stato: (slot) => this._stato(slot),
      num: (slot) => numero(this._stato(slot)),
      acceso: (slot) => acceso(this._stato(slot)),
      derivata: (nome) => {
        const derivate = mappa.derivate || {};
        return derivate[nome] === undefined ? null : derivate[nome];
      },
      riferimento: () => {
        const scelto = Number(opzioni.riferimento);
        return Number.isFinite(scelto) && scelto > 0 ? scelto : RIFERIMENTO_PREDEFINITO;
      },
      numeroTesto: (valore, decimali) => this._numeroTesto(valore, decimali),
      tessera: (testo, classe) => tessere.push({ testo, classe: classe || "" }),
    };

    try {
      aggiornaScena(ctx);
    } catch (errore) {
      console.error(`${NOME_INTEGRAZIONE}: disegno non aggiornato`, errore);
    }
    this._disegnaTessere(tessere);
  }

  _disegnaTessere(tessere) {
    const firma = tessere.map((t) => `${t.testo}|${t.classe}`).join("\u00A7");
    if (firma === this._firmaTessere) return;
    this._firmaTessere = firma;
    this._tessere.innerHTML = tessere
      .map((t) => `<span class="tessera ${t.classe}">${testoSicuro(t.testo)}</span>`)
      .join("");
  }
}

// -----------------------------------------------------------------------------
// Editor
// -----------------------------------------------------------------------------
const SCHEMA_EDITOR = [
  { name: "entity", required: true, selector: { entity: { integration: DOMINIO, domain: "sensor" } } },
  { name: "title", selector: { text: {} } },
  { name: "animazioni", selector: { boolean: {} } },
];
const ETICHETTE_EDITOR = {
  entity: "Mappa impianto",
  title: "Titolo (vuoto: il nome dato all'integrazione)",
  animazioni: "Animazioni",
};

class NexusPompaCaloreCardEditor extends HTMLElement {
  setConfig(config) {
    this._config = config;
    this._aggiorna();
  }

  set hass(hass) {
    this._hass = hass;
    this._aggiorna();
  }

  _aggiorna() {
    if (!this._config || !this._hass) return;
    if (!this._form) {
      this._form = document.createElement("ha-form");
      this._form.schema = SCHEMA_EDITOR;
      this._form.computeLabel = (voce) => ETICHETTE_EDITOR[voce.name] || voce.name;
      this._form.addEventListener("value-changed", (evento) => {
        const valore = { ...evento.detail.value };
        if (valore.animazioni !== false) delete valore.animazioni;
        if (!valore.title) delete valore.title;
        this.dispatchEvent(new CustomEvent("config-changed", { detail: { config: valore }, bubbles: true, composed: true }));
      });
      this.appendChild(this._form);
    }
    this._form.hass = this._hass;
    this._form.data = { ...this._config, animazioni: this._config.animazioni !== false };
  }
}

// -----------------------------------------------------------------------------
// Registrazione: idempotente e non fatale
// -----------------------------------------------------------------------------
try {
  if (!customElements.get("nexus-pompa-calore-card")) {
    customElements.define("nexus-pompa-calore-card", NexusPompaCaloreCard);
    customElements.define("nexus-pompa-calore-card-editor", NexusPompaCaloreCardEditor);
    window.customCards = window.customCards || [];
    window.customCards.push({
      type: "nexus-pompa-calore-card",
      name: NOME_INTEGRAZIONE,
      description: DESCRIZIONE_CARD,
      preview: true,
      documentationURL: `https://github.com/Pacco24626/${DOMINIO}`,
    });
    console.info(
      `%c NEXUS-POMPA-CALORE-CARD %c ${VERSIONE_CARD} `,
      "color:#fff;background:#E07A2F;font-weight:700;",
      "color:#E07A2F;background:#FDF0E3;font-weight:700;"
    );
  }
} catch (errore) {
  console.error(`${NOME_INTEGRAZIONE}: registrazione della card non riuscita`, errore);
}

export { NexusPompaCaloreCard, NexusPompaCaloreCardEditor, VERSIONE_CARD, RUOLO_MAPPA, muovi, scriviValore };
