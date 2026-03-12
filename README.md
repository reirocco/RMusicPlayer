# 🎵 RMusicPlayer - Professional Automix System (V3.1)

RMusicPlayer è un player musicale web-based avanzato, progettato per **automatizzare il mixaggio** tra brani musicali con la stessa fluidità di un DJ professionista.

Utilizzando algoritmi di **Digital Signal Processing (DSP)**, il sistema analizza la tua libreria musicale locale per calcolare BPM, chiave armonica e volume, creando transizioni (crossfade) perfette e armoniche senza interruzioni.

---

## ✨ Funzionalità Principali

### 🎧 Motore Automix Intelligente
*   **True Crossfade:** Sovrappone fisicamente l'uscita della traccia vecchia con l'entrata della nuova (su due canali distinti) per una transizione senza pause.
*   **Analisi BPM e Chiave Armonica (Camelot Wheel):** Il sistema sceglie automaticamente il prossimo brano compatibile musicalmente con quello attuale.
*   **Cue Point Automatico:** Rileva e taglia automaticamente i silenzi iniziali, facendo partire ogni brano esattamente sul primo colpo di cassa.
*   **Normalizzazione Volume (Gain):** Calcola il volume medio di ogni traccia e applica un guadagno dinamico in tempo reale per livellare tutte le canzoni allo stesso standard (-14 dBFS).
*   **Pre-loading in Background:** Utilizza processi paralleli a bassa priorità per preparare il mix successivo, garantendo zero lag nell'interfaccia.

### 📂 Gestione Libreria & Coda
*   **Scansione Ricorsiva:** Naviga liberamente tra cartelle e sottocartelle.
*   **Smart Queue:** Coda dinamica a consumo. Una volta suonata, una canzone viene rimossa dalla lista per evitare ripetizioni fino al completamento della cartella.
*   **Play Here:** Funzione speciale per riprodurre file misti all'interno di cartelle che contengono anche sottocartelle.
*   **Pannello Coda:** Sidebar laterale per visualizzare le prossime tracce nel pool di mixaggio.

### 💻 Interfaccia & Strumenti
*   **Ultra-Modern Neon UI:** Design Glassmorphism 2.0 con palette scura e animazioni fluide.
*   **Pannello Impostazioni (⚙️):**
    *   **Rianalisi Incrementale:** Scansiona solo i nuovi file aggiunti (veloce).
    *   **Reset DB:** Rianalisi completa da zero.
    *   **Backup:** Scarica una copia di sicurezza del database.
    *   **Riavvio Server:** Riavvia l'applicazione direttamente dall'interfaccia.
    *   **Status Monitor:** Indicatore Ping e latenza server in tempo reale.

---

## 🚀 Installazione

### Requisiti
*   **Python 3.8+**
*   **FFmpeg** (Fondamentale per l'elaborazione audio di pydub)

### 🐧 Installazione su Linux (Debian, Ubuntu, Arch, Fedora)

1.  **Clona il repository:**
    ```bash
    git clone https://github.com/tuo-user/RMusicPlayer.git
    cd RMusicPlayer
    ```

2.  **Esegui l'installer universale:**
    ```bash
    sudo bash install_service.sh
    ```
    *Questo script installerà automaticamente FFmpeg, Python venv, le dipendenze e creerà un servizio systemd per l'avvio automatico.*

3.  **Accedi al player:**
    Apri il browser e vai su `http://localhost:5000` (o l'IP del server).

### 🪟 Installazione su Windows

1.  **Scarica e Installa FFmpeg:**
    *   Scarica da [ffmpeg.org](https://ffmpeg.org/download.html).
    *   Estrai `ffmpeg.exe` e copialo dentro la cartella di RMusicPlayer (oppure aggiungilo al PATH di sistema).

2.  **Esegui l'installer:**
    *   Fai doppio click su `install_windows.bat`.
    *   Segui le istruzioni a schermo. Ti chiederà se vuoi avviare il programma automaticamente all'accensione.

3.  **Avvio:**
    *   Usa il file `run.bat` creato sul desktop o nella cartella per lanciare il player.

---

## ⚙️ Primo Utilizzo e Manutenzione

Al primo avvio, il sistema inizierà automaticamente ad analizzare la tua libreria.
*   **Nota:** La prima analisi può richiedere tempo se hai migliaia di brani. Le esecuzioni successive saranno istantanee grazie al caching.

### Aggiunta Nuova Musica
Dopo aver aggiunto nuovi file MP3 alla cartella `RMusicPlayer`:
1.  Clicca sull'icona **Ingranaggio (⚙️)**.
2.  Seleziona **Analisi Database -> Analizza Nuovi**.
3.  Il sistema scansionerà solo i file aggiunti in pochi secondi.

---

## ⚠️ Disclaimer Legale e Limitazione di Responsabilità
**LEGGERE ATTENTAMENTE PRIMA DELL'USO**

Questo software ("RMusicPlayer") è fornito **"AS IS"** (così com'è), senza garanzie di alcun tipo, esplicite o implicite, incluse – ma non limitate a – garanzie di commerciabilità, idoneità a scopi specifici o non violazione dei diritti altrui.

* **Uso Personale:** Questo software è inteso esclusivamente per uso personale, privato e domestico.
* **Copyright e Conformità:** L'utente è l'unico responsabile per l'acquisizione legale dei file musicali utilizzati con questo software. Lo sviluppatore non promuove, facilita né incoraggia in alcun modo la pirateria musicale o la violazione della proprietà intellettuale.
* **Esecuzione Pubblica:** L'utilizzo di questo software per la diffusione di musica in luoghi pubblici, eventi commerciali o locali (es. bar, discoteche, negozi, ecc.) è rigorosamente soggetto alle leggi sul diritto d'autore del proprio Paese (es. licenza SIAE e/o SCF in Italia). L'utente è l'unico responsabile dell'ottenimento e del pagamento delle necessarie licenze.
* **Sicurezza:** Il codice include protezioni contro vulnerabilità comuni (Path Traversal, XSS), ma non è certificato per l'uso su server pubblici esposti a Internet. Si raccomanda l'uso solo in rete locale (LAN).
* **Declinazione di Responsabilità:** Lo sviluppatore declina ogni responsabilità per eventuali danni diretti o indiretti, perdite di dati, violazioni di copyright o sanzioni legali derivanti dall'uso proprio o improprio di questo software.

> **Utilizzando questo software, accetti integralmente queste condizioni e accetti di esonerare lo sviluppatore da qualsiasi responsabilità legale.**
---

## 🛠 Tecnologie Usate

*   **Backend:** Flask (Python)
*   **Audio Engine:** Pygame Mixer + Pydub + Librosa
*   **Frontend:** Bootstrap 5 + Vanilla JS
*   **Processing:** Python Multiprocessing (per analisi non bloccante)

---

Buon ascolto! 🎧