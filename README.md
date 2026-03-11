# 🎵 RMusicPlayer - Professional Automix System

RMusicPlayer è un player musicale web-based avanzato, progettato per **automatizzare il mixaggio** tra brani musicali con la stessa fluidità di un DJ professionista.

Utilizzando algoritmi di **Digital Signal Processing (DSP)**, il sistema analizza la tua libreria musicale locale per calcolare BPM, chiave armonica e volume, creando transizioni (crossfade) perfette e armoniche senza interruzioni.

---

## ✨ Funzionalità Principali

### 🎧 Motore Automix Intelligente
*   **Analisi BPM e Chiave Armonica (Camelot Wheel):** Il sistema sceglie automaticamente il prossimo brano compatibile musicalmente con quello attuale.
*   **Cue Point Automatico:** Rileva e taglia automaticamente i silenzi iniziali, facendo partire ogni brano esattamente sul primo colpo di cassa.
*   **Normalizzazione Volume (Gain):** Calcola il volume medio di ogni traccia e applica un guadagno dinamico per livellare tutte le canzoni allo stesso standard (-14 dBFS).
*   **True Crossfade:** Sovrappone fisicamente l'uscita della traccia vecchia con l'entrata della nuova per una transizione senza pause.

### 📂 Gestione Libreria
*   **Scansione Ricorsiva:** Legge file MP3 da tutte le sottocartelle.
*   **Coda a Consumo:** Garantisce che tutte le canzoni di una cartella vengano suonate prima di ripetere, evitando loop indesiderati.
*   **Pre-loading in Background:** Utilizza processi paralleli a bassa priorità per preparare il mix successivo, garantendo zero lag nell'interfaccia.

### 💻 Interfaccia Moderna
*   **Glassmorphism UI:** Design elegante e reattivo.
*   **Pannello di Controllo:** Gestione completa di playback, coda e impostazioni.
*   **System Tools:** Backup del database, rianalisi forzata e monitoraggio stato.

---

## 🚀 Installazione

### Requisiti
*   **Python 3.8+**
*   **FFmpeg** (necessario per l'elaborazione audio di pydub)
    *   *Linux (Debian/Ubuntu):* `sudo apt install ffmpeg`
    *   *macOS:* `brew install ffmpeg`
    *   *Windows:* Scaricare i binari e aggiungerli al PATH.

### Setup Rapido

1.  **Clona il repository:**
    ```bash
    git clone https://github.com/tuo-user/RMusicPlayer.git
    cd RMusicPlayer
    ```

2.  **Crea un ambiente virtuale (consigliato):**
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate  # Su Windows: .venv\Scripts\activate
    ```

3.  **Installa le dipendenze:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Prepara la tua musica:**
    *   Crea una cartella `RMusicPlayer` nella tua home directory utente:
        *   *Linux/Mac:* `~/RMusicPlayer`
        *   *Windows:* `C:\Users\TuoNome\RMusicPlayer`
    *   Inserisci lì le tue cartelle con i file MP3.

5.  **Avvia il server:**
    ```bash
    python app.py
    ```

6.  **Apri il browser:**
    Vai su `http://localhost:5000`

---

## ⚙️ Primo Utilizzo

Al primo avvio, il sistema inizierà automaticamente ad analizzare la tua libreria.
*   L'analisi calcola BPM, Chiave, Volume e Cue Point per ogni file.
*   Puoi monitorare il progresso dalla barra di caricamento.
*   **Nota:** La prima analisi può richiedere tempo se hai migliaia di brani. Le esecuzioni successive saranno istantanee grazie al caching (hash).

Se aggiungi nuovi file o vuoi ricalcolare i volumi, vai su **Impostazioni (⚙️) -> Rianalisi Completa**.

---

## ⚠️ Disclaimer Legale e Limitazione di Responsabilità
**LEGGERE ATTENTAMENTE PRIMA DELL'USO**

Questo software ("RMusicPlayer") è fornito **"AS IS"** (così com'è), senza garanzie di alcun tipo, esplicite o implicite, incluse – ma non limitate a – garanzie di commerciabilità, idoneità a scopi specifici o non violazione dei diritti altrui.

* **Uso Personale:** Questo software è inteso esclusivamente per uso personale, privato e domestico.
* **Copyright e Conformità:** L'utente è l'unico responsabile per l'acquisizione legale dei file musicali utilizzati con questo software. Lo sviluppatore non promuove, facilita né incoraggia in alcun modo la pirateria musicale o la violazione della proprietà intellettuale.
* **Esecuzione Pubblica:** L'utilizzo di questo software per la diffusione di musica in luoghi pubblici, eventi commerciali o locali (es. bar, discoteche, negozi, ecc.) è rigorosamente soggetto alle leggi sul diritto d'autore del proprio Paese (es. licenza SIAE e/o SCF in Italia). L'utente è l'unico responsabile dell'ottenimento e del pagamento delle necessarie licenze.
* **Sviluppo assistito da IA:** Questo progetto è stato sviluppato con il supporto di strumenti di Intelligenza Artificiale. Sebbene il codice sia stato revisionato e testato dallo sviluppatore, l'utente finale resta responsabile per la verifica della sua idoneità e sicurezza prima dell'utilizzo.
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