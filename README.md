# 🎵 RMusicPlayer - Professional Automix System (V3.2)

RMusicPlayer è un player musicale web-based avanzato, progettato per **automatizzare il mixaggio** tra brani musicali con la stessa fluidità di un DJ professionista.

Utilizzando algoritmi di **Digital Signal Processing (DSP)**, il sistema analizza la tua libreria musicale locale per calcolare BPM, chiave armonica, volume ed energia, creando transizioni (crossfade) perfette e armoniche senza interruzioni.

---

## ✨ Funzionalità Principali

### 🎧 Motore Automix Intelligente (v2.0)
*   **True Crossfade:** Sovrappone fisicamente l'uscita della traccia vecchia con l'entrata della nuova per una transizione senza pause.
*   **Analisi BPM & Camelot Key:** Mixaggio armonico automatico per evitare dissonanze.
*   **Energy Flow:** L'algoritmo sceglie il prossimo brano mantenendo un livello di energia costante (±2) per garantire un flusso musicale coerente.
*   **Smart Cue Points:** Rileva e taglia automaticamente i silenzi iniziali (Trim su Beat Detection).
*   **Gain Normalization:** Livella automaticamente il volume di tutti i brani a -14 dBFS.
*   **Pre-loading a Bassa Latenza:** Utilizza processi paralleli per preparare il mix successivo in background, garantendo zero lag al cambio traccia.

### 📂 Gestione Libreria & Coda
*   **Scansione Ricorsiva:** Naviga liberamente tra cartelle e sottocartelle.
*   **Play Here:** Funzione speciale per riprodurre file misti all'interno di cartelle che contengono anche sottocartelle.
*   **Smart Queue:** Coda dinamica a consumo con visualizzazione laterale.
*   **Auto-Refill:** Quando la coda finisce, il sistema ricarica e mescola automaticamente la playlist corrente.

### 💻 Interfaccia & Strumenti
*   **Ultra-Modern Neon UI:** Design Glassmorphism 2.0 con palette scura, animazioni fluide e logo SVG animato.
*   **Pannello Impostazioni (⚙️):**
    *   **Rianalisi Incrementale:** Scansiona solo i nuovi file aggiunti (veloce).
    *   **Reset DB:** Rianalisi completa da zero.
    *   **Backup & Debug:** Scarica copie del database o visualizza i dati grezzi.
    *   **Console Log:** Visualizzatore di log in tempo reale integrato nell'interfaccia.
    *   **Riavvio Server:** Riavvia l'applicazione direttamente dall'interfaccia.
*   **Status Monitor:** Indicatore Ping e latenza server in tempo reale.

---

## 🚀 Installazione

### Requisiti
*   **Python 3.8+**
*   **FFmpeg** (Fondamentale per l'elaborazione audio)

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
    *   Segui le istruzioni a schermo.

3.  **Avvio:**
    *   Usa il file `run.bat` creato sul desktop o nella cartella per lanciare il player.

---

## ⚙️ Primo Utilizzo e Manutenzione

Al primo avvio, il sistema inizierà automaticamente ad analizzare la tua libreria.
*   **Nota:** La prima analisi può richiedere tempo se hai migliaia di brani. Le esecuzioni successive saranno istantanee grazie al caching (hash).

### Aggiunta Nuova Musica
Dopo aver aggiunto nuovi file MP3 alla cartella `RMusicPlayer`:
1.  Clicca sull'icona **Ingranaggio (⚙️)**.
2.  Seleziona **Analisi Database -> Analizza Nuovi**.
3.  Il sistema scansionerà solo i file aggiunti in pochi secondi.

---

## ⚠️ Disclaimer Legale e Sicurezza

**LEGGERE ATTENTAMENTE PRIMA DELL'USO**

*   **Sicurezza:** Il codice include protezioni contro vulnerabilità comuni (Path Traversal, XSS), ma non è certificato per l'uso su server pubblici esposti a Internet. Si raccomanda l'uso solo in rete locale (LAN) protetta.
*   **Copyright:** L'utente è l'unico responsabile per l'acquisizione legale dei file musicali.
*   **Esecuzione Pubblica:** L'utilizzo in luoghi pubblici è soggetto alle leggi sul diritto d'autore locali (SIAE/SCF).

**Utilizzando questo software, accetti integralmente queste condizioni e esoneri lo sviluppatore da qualsiasi responsabilità.**

---

## 🛠 Tecnologie Usate

*   **Backend:** Flask (Python)
*   **Audio Engine:** Pygame Mixer + Pydub + Librosa
*   **Frontend:** Bootstrap 5 + Vanilla JS
*   **Processing:** Python Multiprocessing (per analisi non bloccante)

---

Buon ascolto! 🎧