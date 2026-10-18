# Pacchetti per artigiani e fornitori

Prima di mandare qualsiasi cosa: aggiornare `cad/params.json` con le misure reali del tavolo, rigenerare
(`python3 cad/model.py && python3 cad/drawings.py && python3 bom/bom.py`) e controllare le forature marcate **[V]**
sui datasheet dei componenti effettivamente comprati. Ordine consigliato: **prima si comprano i componenti commerciali,
poi si lavorano le piastre** (le forature dei pattini/supporti si ricavano dai pezzi in mano).

| Artigiano | Cosa consegnare | Pezzi | Note per la richiesta d'offerta |
|---|---|---|---|
| **Tornitore / fresatore** | Tav. 03, 04, 05, 12 | ANC-01, ANC-02, ANC-03 ×2, PER-01 ×4, RUL-01, ASS-X, DIS-01 ×8 | Rullo: rettifica + lucidatura Ra ≤ 0,8 µm, nessuna porosità nelle saldature (contatto alimentare). Ancoraggi e perni sono accoppiamenti H7/g6: chiedere controllo con tampone. |
| **Taglio laser + officina** | Tav. 06–11 + `cad/dxf/*.dxf` | CAR-01 ×2, ZPL-01 ×2, ZSL-01, ZSL-02, PIE-01 ×4, STM-01 ×4, CTP-01 ×4 | Inox 304, fori filettati sul layer `FORI_FILETTARE` già a diametro di preforo, da maschiare. Piastre "speculari" = stessa lamiera, montate ruotate. |
| **Carpenteria inox (TIG)** | Tav. 01, 02 | TEL-01, PON-01, SQZ-01 ×2 | Saldare il telaio **sopra il tavolo** con gli ancoraggi già posati e i perni infilati: così i 4 piedi cadono esattamente negli ancoraggi. Decapaggio e passivazione finali. |
| **Plastica** | Tav. 12 | RAS-01 ×2 | POM-C con certificato di idoneità al contatto alimentare. |
| **Quadrista / elettricista** | `wiring/out/schemi_elettrici.pdf`, `wiring/README.md`, `wiring/out/elenco_fili.csv` | QE-01 | Chiedere verifica CEI EN 60204-1 e dichiarazione di conformità del quadro. |

## Acquisti a cura tua

Foglio **Acquisti** di `bom/ManipMasta_distinta.xlsx` (anche `bom/acquisti.csv`): guide, pattini, supporti, viti, cuscinetti,
pulegge e cinghie, motori closed-loop con driver, sensori, Arduino, alimentatori, componenti di sicurezza e connettori.
I prezzi sono stime per fare il budget, non preventivi.

## Materiali e igiene

- Tutto ciò che sta sopra o tocca l'impasto: AISI 304 (o 316) passivato, POM-C/PE-HD alimentare, grasso NSF H1.
- Guide, cinghie e viti stanno sopra il piano: prevedere carter/raccogli-gocce sotto i longheroni se si usa grasso.
- Fornitori di parti a contatto: chiedere dichiarazione di conformità MOCA (Reg. CE 1935/2004).
