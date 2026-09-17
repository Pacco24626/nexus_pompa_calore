<img src="icons/logo.png" alt="Nexus Pompa di Calore" width="420">

# Nexus Pompa di Calore

Il sinottico animato della centrale termica in Home Assistant: colleghi una volta le
entità della pompa di calore e ottieni un dispositivo con i sensori calcolati e una card
che disegna l'impianto e lo muove con i valori veri.

L'integrazione non parla con la pompa di calore: usa entità che Home Assistant ha già
(eBUS, Modbus, MQTT, cloud del produttore, quello che hai). Funziona con qualunque marca.

## Cosa nasce

Un dispositivo col nome che scegli (predefinito «Centrale Termica») e tre sensori:

| Sensore | Cosa dice |
|---|---|
| **Stato** | `guasto`, `sbrinamento`, `in_marcia` o `fermo`. Guasto e sbrinamento hanno la precedenza; poi decide il compressore, se manca la frequenza, se manca la portata. Se nessuna fonte si legge lo stato è sconosciuto, non «fermo». |
| **Salto termico** | mandata meno ritorno, al decimo. Negativo quando il ritorno è più caldo (sbrinamento). Da Home Assistant 2025.12 usa la classe «differenza di temperatura», che non si converte in Fahrenheit sbagliando lo zero. |
| **Mappa impianto** | diagnostico: le entità collegate, le opzioni e i valori calcolati. È il sensore da indicare nella card. |

## La card

Unità esterna, riscaldamento e accumulo ACS, con le tubazioni di mandata e ritorno.

- l'acqua scorre nelle tubazioni alla velocità della **portata**;
- la ventola gira alla **frequenza del compressore** (un giro in 28/Hz secondi, fra mezzo
  secondo e quattro);
- il bollitore cambia colore con la **temperatura dell'accumulo**;
- il pavimento radiante pulsa quando c'è flusso e il salto termico è positivo;
- sotto il disegno, le tessere: sbrinamento, guasto, boost ACS, vacanza, salto termico.

Segue il tema chiaro o scuro, ingrandisce i numeri quando la card è stretta (telefono) e li
rimpicciolisce se non ci stanno. Un tocco su un riquadro apre l'entità. I riquadri delle
voci non collegate non compaiono.

```yaml
type: custom:nexus-pompa-calore-card
entity: sensor.centrale_termica_mappa_impianto
title: Centrale Termica   # facoltativo: senza, il nome dato all'integrazione; "" per nasconderlo
animazioni: true          # facoltativo: false ferma il disegno
```

Si aggiunge anche dall'editor delle plance cercando **Nexus Pompa di Calore**. La card la
serve e la registra l'integrazione: nessuna risorsa da aggiungere a mano.

## Installazione

1. HACS → menu ⋮ → **Repository personalizzate**
2. URL `https://github.com/Pacco24626/nexus_pompa_calore`, categoria **Integration**
3. Installa e **riavvia Home Assistant**
4. **Impostazioni → Dispositivi e servizi → Aggiungi integrazione → Nexus Pompa di Calore**

## Configurazione

Il modulo arriva già compilato con le entità riconosciute dal nome. Tre sezioni:

| Sezione | Voci |
|---|---|
| Temperature | **mandata**, **ritorno** (obbligatorie), esterna, accumulo ACS |
| Funzionamento | compressore attivo, frequenza del compressore, portata dell'acqua, sbrinamento |
| Rendimento e segnalazioni | COP riscaldamento, COP sanitario, boost ACS, vacanza, guasto |

Da **Configura** si cambiano le entità e il **fondo scala** delle animazioni (predefinito
20 L/min: oltre, l'acqua disegnata non corre più veloce). Il nome si cambia rinominando la voce.

Se rinomini un'entità collegata, il collegamento si aggiorna da solo.

## Cosa non fa

- **Non inventa la modalità.** La card mostra il flusso e le temperature, non un'etichetta
  «sanitario» o «riscaldamento» indovinata.
- **Senza sensore di portata** il flusso si muove a velocità fissa quando il compressore
  gira, e una tessera lo dichiara.

## Prove

```bash
python tests/test_logica.py
python tests/test_impianto.py
python tests/test_config_flow.py
node tests/test_card.mjs
```

La card si collauda in un browser vero servendo la cartella (`python -m http.server`) e
aprendo `tests/card/prova_card.html`: in fondo alla pagina c'è l'esito dei controlli.

## Licenza

Apache 2.0
