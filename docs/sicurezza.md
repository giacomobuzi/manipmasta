# Sicurezza e conformità

Questa è una macchina con un rullo motorizzato che scende verso il piano: il **punto di schiacciamento/trascinamento tra rullo e
piano** è il pericolo principale (mani sotto il rullo). Il progetto lo affronta così:

| Pericolo | Misura nel progetto |
|---|---|
| Mani sotto il rullo in movimento | Barriera fotoelettrica di sicurezza sui lati lunghi che agisce sui contattori (non solo sul firmware); velocità di lavoro bassa (default 60 mm/s, consigliato ≤ 60); ripresa solo con comando esplicito |
| Avvio inatteso | Driver disabilitati all'accensione (pull-up su ENA), homing obbligatorio, RUN solo con portale in sede, emergenza e barriera OK |
| Caduta del rullo | Viti trapezie TR16×4 autobloccanti; homing verso l'alto |
| Portale non agganciato | Perni di centraggio + perni a sfere su A1/A2 + 2 sensori "in sede": senza, nessun movimento |
| Emergenza | Fungo 2NC → relè di sicurezza cat. 3 → KM1+KM2 in serie sull'alimentazione dei driver, reset manuale con retroazione |
| Comando remoto | L'app e la UI web **non sono** dispositivi di sicurezza: lo STOP remoto è un arresto funzionale. L'emergenza è solo quella fisica |
| Rete | Arduino su VLAN IoT isolata, broker MQTT con utenti/ACL raggiungibile solo dalla VLAN, UI esposta solo via HTTPS con token |
| Igiene | Materiali a contatto alimentare (Reg. CE 1935/2004), superfici lisce, nessuna cavità aperta, grasso H1 |

## Norme di riferimento

- Direttiva Macchine 2006/42/CE; dal **20 gennaio 2027** si applica il Regolamento Macchine (UE) 2023/1230.
- EN ISO 12100 (valutazione del rischio), EN ISO 13849-1 (parti di comando legate alla sicurezza, PL d raccomandato per la barriera),
  EN ISO 13857 (distanze di sicurezza), CEI EN 60204-1 (equipaggiamento elettrico).
- Per macchine alimentari: EN 1672-2 (requisiti di igiene).

Se la macchina viene usata in un laboratorio con dipendenti, va trattata come una macchina "costruita in proprio": serve la
valutazione dei rischi, il fascicolo tecnico e la marcatura CE, oppure va inserita nel DVR con le misure equivalenti.
Fai verificare il progetto a un tecnico abilitato prima dell'uso produttivo.
