#!/usr/bin/env python3
"""Distinta base ManipMasta -> bom/ManipMasta_distinta.xlsx + CSV.

Prezzi: stime indicative (ottobre 2026, IVA esclusa, singolo pezzo) per budget, da sostituire con i preventivi reali.
"""
import csv
import os

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill, Border, Side
from openpyxl.utils import get_column_letter

HERE = os.path.dirname(os.path.abspath(__file__))

# (codice, descrizione, specifica / ricerca, q.tà, prezzo unitario stimato €, fornitore tipo, note)
ACQUISTI = [
    # --- Meccanica lineare
    ("M01", "Guida supportata SBR20 L=1800", "SBR20 albero Ø20 cromato (o inox) con base alluminio, L 1800", 2, 65, "Fornitore componenti lineari (es. negozio CNC, Misumi, RS)", "Montare con grasso alimentare NSF H1"),
    ("M02", "Pattino aperto SBR20UU", "SBR20UU, foratura 4×M6 [verificare interassi]", 4, 12, "idem", ""),
    ("M03", "Albero rettificato Ø16 h6 inox L=380", "AISI 440C / 304 cromato Ø16 h6", 4, 18, "idem", "Guide asse Z"),
    ("M04", "Supporto albero SK16", "SK16 alluminio", 8, 5, "idem", ""),
    ("M05", "Pattino chiuso SC16UU", "SC16UU con boccola LM16UU", 8, 9, "idem", "2 per albero"),
    ("M06", "Vite trapezia TR16×4 L=420 + chiocciola flangiata", "TR16x4 destra, chiocciola bronzo flangiata", 2, 35, "idem", "Autobloccante: il rullo non cade a motori spenti"),
    ("M07", "Supporti vite BK12 + BF12 (coppia)", "BK12/BF12 con estremità vite lavorata Ø12", 2, 30, "idem", "Lavorazione estremità vite: chiedere al fornitore della vite"),
    ("M08", "Giunto elastico 8→12", "giunto a soffietto/oldham Ø25 L30, foro 8 e 12", 2, 12, "idem", "Motori Z"),
    ("M09", "Giunto elastico 8→14", "giunto a soffietto Ø32, foro 8 e 14", 1, 15, "idem", "Motore X"),
    ("M10", "Cuscinetto inox S6204-2RS + seeger DIN 471 Ø20", "S6204-2RS Ø20×47×14 acciaio inox, schermato", 2, 22, "Ricambi cuscinetti / SKF-NTN rivenditore", "Nelle sedi delle slitte Z, chiusi da COP-01"),
    ("M11", "Supporto flangiato KFL002", "KFL002 foro 15 (o inox SFL202)", 4, 9, "idem", "Albero di sincronismo X"),
    ("M12", "Puleggia HTD-5M 20T per cinghia 15, foro 15 con cava", "HTD 5M 20T b15, foro finito 15H7 + cava 5", 2, 16, "Trasmissioni (es. Mädler, Misumi)", "Motrici asse X"),
    ("M13", "Puleggia folle HTD-5M 20T con cuscinetti", "rinvio 20T b15 con 2 cuscinetti, perno M8", 2, 18, "idem", "Rinvii asse X"),
    ("M14", "Cinghia aperta HTD-5M larghezza 15", "HTD-5M-15 aperta, 5 m (2 × 3,9 m)", 1, 45, "idem", "Fissata ai carrelli con morsetti"),
    ("M15", "Puleggia HTD-5M 20T foro 8 (motore R)", "HTD 5M 20T b15 foro 8 con grani", 1, 14, "idem", ""),
    ("M16", "Puleggia HTD-5M 40T foro 20 con cava (rullo)", "HTD 5M 40T b15 foro 20H7 + cava 6", 1, 28, "idem", ""),
    ("M17", "Cinghia chiusa HTD 425-5M-15", "HTD 425-5M larghezza 15", 1, 12, "idem", "Verificare lunghezza a montaggio (tendicinghia ±6 mm)"),
    ("M18", "Morsetto cinghia HTD-5M 15", "piastrina di bloccaggio dentata", 4, 6, "idem", ""),
    ("M19", "Perno a sfere Ø8 × 110 con anello", "ball lock pin Ø8 (es. GN 113 / KIPP K0790), inox", 2, 25, "Ganter / KIPP / Elesa", "Bloccaggio portale su A1 e A2"),
    ("M20", "Catena portacavi 15×30 R48", "igus E2 micro serie 15 o equivalente, 1,2 m + attacchi", 1, 45, "igus / rivenditore", ""),
    ("M21", "Viteria inox A2/A4 assortita", "M5, M6, M8, M12, rondelle, grani", 1, 60, "Ferramenta industriale", ""),
    ("M22", "Grasso alimentare NSF H1", "es. lubrificante H1 per guide", 1, 18, "idem", ""),
    # --- Motori e azionamenti
    ("A01", "Kit motore NEMA23 closed-loop 2 Nm + driver", "NEMA23 2 Nm encoder 1000 lin. + driver CL57T (o HSS57) + cavi", 4, 85, "StepperOnline / rivenditore CNC", "X, Z1, Z2, R"),
    # --- Sensori
    ("S01", "Sensore induttivo M12 PNP NO 24 V", "M12 Sn 4 mm schermato, 3 fili, cavo 2 m (o connettore M12)", 8, 14, "Automazione (es. Omron, Sick, Pepperl+Fuchs o equivalenti)", "X_MIN, X_MAX, Z1/Z2 HOME, Z1/Z2 LOW, SEAT A/B"),
    ("S02", "Barriera fotoelettrica di sicurezza (coppia)", "tipo 2 o 4, risoluzione 30 mm, altezza 300, OSSD PNP", 2, 380, "Automazione sicurezza", "Lati lunghi: consigliata per uso con operatori"),
    # --- Elettronica di controllo
    ("E01", "Arduino Mega 2560 Rev3 (originale)", "A000067", 1, 45, "store.arduino.cc / distributori", ""),
    ("E02", "Arduino Ethernet Shield 2", "A000024 (W5500)", 1, 30, "idem", ""),
    ("E03", "Screw shield / morsettiera per Mega", "proto shield con morsetti a vite", 1, 18, "idem", ""),
    ("E04", "Scheda ingressi optoisolati 8 canali 24→5 V", "PC817 8 canali", 2, 9, "Elettronica", "U6 sensori, U7 sicurezza/pulsanti"),
    ("E05", "Modulo 4 relè 5 V attivo ALTO", "4 relè 10 A, ingresso optoisolato, jumper livello", 1, 9, "Elettronica", "Bobine da U9"),
    ("E06", "Convertitore DC/DC 24→5 V 1 A (U9)", "modulo DIN o buck isolato", 1, 15, "Elettronica", ""),
    ("E07", "Buffer 74HCT245 su millefori (opz.)", "se l'assorbimento ingressi driver supera i limiti del Mega", 1, 6, "Elettronica", "Opzionale"),
    # --- Alimentazione e quadro
    ("Q01", "Alimentatore 48 V 480 W DIN", "Mean Well SDR-480-48", 1, 120, "Distributore Mean Well", "Driver motori"),
    ("Q02", "Alimentatore 24 V 60 W DIN", "Mean Well HDR-60-24", 1, 30, "idem", "Sensori, relè, colonna"),
    ("Q03", "Alimentatore 12 V 15 W DIN", "Mean Well HDR-15-12", 1, 15, "idem", "Vin Arduino"),
    ("Q04", "Interruttore magnetotermico 2P C10", "6 kA", 1, 25, "Materiale elettrico", ""),
    ("Q05", "Modulo relè di sicurezza 2 canali cat. 3", "es. Pilz PNOZ s4, Schneider XPS, Phoenix PSR", 1, 180, "Automazione sicurezza", ""),
    ("Q06", "Contattore 9 A bobina 24 V DC + contatto ausiliario NC", "es. Schneider LC1K09 + ausiliario", 2, 35, "Materiale elettrico", "KM1 + KM2 in serie"),
    ("Q07", "Fungo di emergenza 2NC ritenuta, testa Ø40", "con collare giallo", 1, 35, "idem", ""),
    ("Q08", "Pulsanti Ø22: START verde NO, STOP rosso NC, RESET blu NO", "", 3, 12, "idem", ""),
    ("Q09", "Colonna luminosa 24 V verde/giallo/rosso + buzzer", "", 1, 55, "idem", ""),
    ("Q10", "Portafusibili DIN + fusibili 5 A", "10×38", 4, 8, "idem", "Uno per driver"),
    ("Q11", "Cassetta inox IP65 500×400×250 con piastra", "AISI 304", 1, 260, "idem", ""),
    ("Q12", "Ventilazione filtrata IP54 + griglia", "24 V", 1, 45, "idem", ""),
    ("Q13", "Guida DIN, canaline, morsetti, capicorda, targhette", "", 1, 90, "idem", ""),
    ("Q14", "Connettore Harting Han-Modular 24B completo", "moduli EE 8p ×2 (fasi) + DD 12p ×2 (encoder) + PE, custodia e base", 1, 160, "Harting / distributore", "Motori: il portale si stacca"),
    ("Q15", "Connettore Harting Han 16E completo", "sensori e barriera", 1, 70, "idem", ""),
    ("Q16", "Cavo motore 4×1,0 schermato per catena (chainflex)", "metri", 16, 6, "igus / Lapp", ""),
    ("Q17", "Cavo encoder 6×0,25 schermato per catena", "metri", 16, 5, "idem", ""),
    ("Q18", "Cavo sensori 3×0,34 PUR", "metri", 25, 1.5, "idem", ""),
    ("Q19", "Cavo alimentazione H07RN-F 3G1,5 + spina", "3 m", 1, 18, "idem", ""),
    ("Q20", "Patch Ethernet Cat6 S/FTP", "verso switch VLAN IoT", 1, 10, "Informatica", ""),
]

# (codice, descrizione, materiale, q.tà, artigiano, tavola, lavorazioni, stima €/pz)
ARTIGIANI = [
    ("TEL-01", "Telaio portale saldato", "AISI 304 tubi 60×60×3, 80×40×3, 60×40×3", 1, "Carpenteria inox (TIG)", "Tav. 02",
     "taglio, saldatura TIG su dima con perni negli ancoraggi, fresatura/spessoramento piano guide, fori Ø17 albero, decapaggio e passivazione", 900),
    ("PON-01", "Traversa ponte", "AISI 304 tubo 40×40×2 L=830 con piastrine M8", 1, "Carpenteria inox (TIG)", "Tav. 01", "taglio, piastrine saldate, fori", 70),
    ("SQZ-01", "Squadra attacco piastra Z al carrello", "AISI 304 angolare 60×60×6 L=260", 2, "Carpenteria inox (TIG)", "Tav. 06-07", "taglio e foratura M8 accoppiata", 35),
    ("CAR-01", "Piastra carrello X", "AISI 304 sp. 12", 2, "Taglio laser + officina", "Tav. 06 · DXF", "laser, foratura e maschiatura, rettifica appoggi pattini", 90),
    ("ZPL-01", "Piastra Z fissa", "AISI 304 sp. 15", 2, "Taglio laser + officina", "Tav. 07 · DXF", "laser, maschiatura, fresatura appoggi supporti", 120),
    ("ZSL-01", "Slitta Z lato Y− con motore R", "AISI 304 sp. 16", 1, "Taglio laser + officina", "Tav. 09 · DXF", "laser, alesatura sede Ø47 H7, maschiatura, asole motore, bandierina saldata", 120),
    ("ZSL-02", "Slitta Z lato Y+", "AISI 304 sp. 16", 1, "Taglio laser + officina", "Tav. 08 · DXF", "laser, alesatura sede Ø47 H7, maschiatura, bandierina saldata", 110),
    ("COP-01", "Coperchio cuscinetto Ø72", "AISI 304 sp. 5", 2, "Taglio laser + tornitore", "Tav. 10 · DXF", "laser, tornitura contorno e spallamento Ø47", 20),
    ("PIE-01", "Piastra piede montante", "AISI 304 sp. 10", 4, "Taglio laser + officina", "Tav. 11 · DXF", "laser, alesatura Ø20 H7, filetto M12×1 su 2 pezzi", 25),
    ("STM-01", "Flangia motore NEMA23", "AISI 304 sp. 10", 4, "Taglio laser + officina", "Tav. 12 · DXF", "laser, foratura", 20),
    ("CTP-01", "Contropiastra sotto piano", "AISI 304 sp. 5", 4, "Taglio laser", "Tav. 13", "laser", 10),
    ("ANC-01", "Ancoraggio A1 riferimento", "AISI 304 barra quadra 100", 1, "Tornitore / fresatore", "Tav. 03", "fresatura, alesatura Ø20 H7, foro Ø8 H8 trasversale, 4×M8", 90),
    ("ANC-02", "Ancoraggio A2 asola", "AISI 304 barra quadra 100", 1, "Tornitore / fresatore", "Tav. 03", "fresatura asola 20 H7×26, foro Ø8 H8, 4×M8", 100),
    ("ANC-03", "Ancoraggio A3/A4 appoggio", "AISI 304 barra quadra 100", 2, "Tornitore / fresatore", "Tav. 03", "fresatura, foro Ø26, 4×M8", 70),
    ("PER-01", "Perno di centraggio", "AISI 420 temprato (o 304)", 4, "Tornitore", "Tav. 04", "tornitura Ø20 g6, punta conica, foro Ø8 H8 su 2 pezzi", 35),
    ("RUL-01", "Rullo di laminazione Ø100", "AISI 304 tubo Ø100×3 + testate + perni", 1, "Tornitore (rettifica)", "Tav. 05", "saldatura testate, tornitura tra le punte, rettifica e lucidatura Ra≤0,8, cava linguetta, equilibratura", 380),
    ("ASS-X", "Albero di sincronismo", "AISI 304 Ø16", 1, "Tornitore", "Tav. 13", "tornitura sedi Ø15 k6, 2 cave linguetta, estremità Ø14", 70),
    ("DIS-01", "Distanziali motore Z 40 mm", "AISI 304 Ø12 forato", 8, "Tornitore", "Tav. 13", "tornitura", 5),
    ("RAS-01", "Raschietto rullo", "POM-C alimentare sp. 10", 2, "Fresatura materie plastiche", "Tav. 13", "fresatura lama 20°, asole", 30),
    ("QE-01", "Cablaggio quadro elettrico + collaudo", "secondo wiring/schemi_elettrici.pdf", 1, "Quadrista / elettricista", "E01–E05", "montaggio, cablaggio, prove CEI EN 60204-1, dichiarazione", 600),
]


def main():
    wb = Workbook()
    hdr_fill = PatternFill("solid", fgColor="1F3A5F")
    hdr_font = Font(bold=True, color="FFFFFF")
    thin = Side(style="thin", color="B0B7C0")
    border = Border(top=thin, bottom=thin, left=thin, right=thin)

    def sheet(ws, header, rows, widths, money_cols, qty_col, price_col, total_col):
        ws.append(header)
        for c in ws[1]:
            c.fill, c.font, c.alignment = hdr_fill, hdr_font, Alignment(wrap_text=True, vertical="center")
        for i, r in enumerate(rows, start=2):
            ws.append(list(r) + [None])
            q, p = get_column_letter(qty_col), get_column_letter(price_col)
            ws.cell(row=i, column=total_col, value=f"={q}{i}*{p}{i}")
        n = len(rows) + 1
        ws.cell(row=n + 2, column=total_col - 1, value="Totale stimato").font = Font(bold=True)
        tc = get_column_letter(total_col)
        ws.cell(row=n + 2, column=total_col, value=f"=SUM({tc}2:{tc}{n})").font = Font(bold=True)
        for col, w in enumerate(widths, start=1):
            ws.column_dimensions[get_column_letter(col)].width = w
        for row in ws.iter_rows(min_row=1, max_row=n):
            for c in row:
                c.border = border
                c.alignment = Alignment(wrap_text=True, vertical="top")
        for col in money_cols:
            for r in range(2, n + 3):
                ws.cell(row=r, column=col).number_format = '#,##0.00 "€"'
        ws.freeze_panes = "A2"
        return n + 2

    ws = wb.active
    ws.title = "Acquisti"
    tot_a = sheet(ws, ["Codice", "Descrizione", "Specifica / ricerca", "Q.tà", "€ unit. stimato", "Fornitore tipo", "Note", "€ totale"],
                  ACQUISTI, (8, 42, 46, 7, 13, 34, 38, 13), (5, 8), 4, 5, 8)
    ws2 = wb.create_sheet("Artigiani")
    tot_b = sheet(ws2, ["Codice", "Descrizione", "Materiale", "Q.tà", "Artigiano", "Disegno", "Lavorazioni", "€/pz stimato", "€ totale"],
                  ARTIGIANI, (9, 34, 34, 6, 26, 14, 60, 13, 13), (8, 9), 4, 8, 9)
    ws3 = wb.create_sheet("Riepilogo")
    ws3["A1"] = "ManipMasta — riepilogo costi (stime indicative IVA esclusa, da sostituire con preventivi)"
    ws3["A1"].font = Font(bold=True, size=12)
    ws3["A3"], ws3["B3"] = "Componenti da acquistare", f"=Acquisti!H{tot_a}"
    ws3["A4"], ws3["B4"] = "Lavorazioni artigiani", f"=Artigiani!I{tot_b}"
    ws3["A5"], ws3["B5"] = "Imprevisti 10%", "=0.1*(B3+B4)"
    ws3["A6"], ws3["B6"] = "Totale", "=B3+B4+B5"
    ws3["A6"].font = ws3["B6"].font = Font(bold=True)
    for r in range(3, 7):
        ws3.cell(row=r, column=2).number_format = '#,##0 "€"'
    ws3.column_dimensions["A"].width = 34
    ws3.column_dimensions["B"].width = 16
    ws3["A8"] = "Per artigiano: filtrare il foglio 'Artigiani' sulla colonna Artigiano e allegare le tavole/DXF indicati."
    wb.save(os.path.join(HERE, "ManipMasta_distinta.xlsx"))

    with open(os.path.join(HERE, "acquisti.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["Codice", "Descrizione", "Specifica", "Qta", "EUR_unit_stima", "Fornitore", "Note"])
        w.writerows(ACQUISTI)
    with open(os.path.join(HERE, "artigiani.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["Codice", "Descrizione", "Materiale", "Qta", "Artigiano", "Disegno", "Lavorazioni", "EUR_pz_stima"])
        w.writerows(ARTIGIANI)
    a = sum(r[3] * r[4] for r in ACQUISTI)
    b = sum(r[3] * r[7] for r in ARTIGIANI)
    print(f"acquisti {a:.0f} €, artigiani {b:.0f} €, totale +10% {1.1 * (a + b):.0f} €")


if __name__ == "__main__":
    main()
