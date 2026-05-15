# RMusicPlayer - Professional Automix System (V3.3)

RMusicPlayer è un player musicale web-based avanzato, progettato per **automatizzare il mixaggio** tra brani musicali con la stessa fluidità di un DJ professionista.

Utilizzando algoritmi di **Digital Signal Processing (DSP)**, il sistema analizza la tua libreria musicale locale per calcolare BPM, chiave armonica, volume ed energia, creando transizioni (crossfade) perfette e armoniche senza interruzioni.

---

## Funzionalità Principali

### Motore Automix Intelligente (v3.0)
*   **True Crossfade:** Sovrappone fisicamente l'uscita della traccia vecchia con l'entrata della nuova per una transizione senza pause (Gapless Playback puro).
*   **Loudness Normalization (EBU R128):** Livella automaticamente il volume di tutti i brani al target di -14 LUFS, rispettando lo standard del broadcasting moderno (Spotify/YouTube), ed include un limitatore di "True Peak" per prevenire qualsiasi saturazione (clipping).
*   **Smart Cue Points:** Rileva e taglia automaticamente i silenzi iniziali e finali tramite `pydub`, registrando metadati precisi per mix immediati.
*   **Analisi BPM & Camelot Key:** Mixaggio armonico automatico per evitare dissonanze.
*   **Energy Flow:** L'algoritmo sceglie il prossimo brano mantenendo un livello di energia costante per garantire un flusso musicale coerente.
*   **Pre-loading a Bassa Latenza:** Utilizza processi paralleli per preparare il mix successivo in background, garantendo zero lag al cambio traccia.

### Gestione Libreria & Coda
*   **Scansione Ricorsiva:** Naviga liberamente tra cartelle e sottocartelle.
*   **Loop Cartella Continuo (Automix Loop):** Quando la riproduzione in una cartella volge al termine, il sistema si riattiva silenziosamente in background:
    *   Effettua una ri-scansione della cartella per includere eventuali nuovi MP3.
    *   Scarta intelligentemente i file corrotti o non analizzati.
    *   Non ripete mai la canzone in onda.
    *   Rimescola in ordine casuale per generare una rotazione infinita garantendo una riproduzione che non si interrompe mai.
*   **Auto-Refill Armonico:** Con il loop infinito disabilitato, quando la coda finisce, il sistema ricarica staticamente e rimescola armonicamente la playlist corrente originaria.

### Interfaccia & Strumenti
*   **Ultra-Modern Neon UI:** Design Glassmorphism 2.0 con palette scura, animazioni fluide e logo SVG animato.
*   **Pannello Impostazioni:**
    *   **Rianalisi Incrementale:** Scansiona solo i nuovi file aggiunti (veloce).
    *   **Reset DB:** Rianalisi completa da zero.
    *   **Backup & Debug:** Scarica copie del database o visualizza i dati grezzi.
    *   **Console Log:** Visualizzatore di log in tempo reale integrato nell'interfaccia.
    *   **Riavvio Server:** Riavvia l'applicazione (Demone Systemd) direttamente dall'interfaccia web.
*   **Status Monitor:** Indicatore Ping e latenza server in tempo reale.

---

## Installazione (Linux Systemd User Service)

### Requisiti
*   **Python 3.8+**
*   **FFmpeg** (Fondamentale per il calcolo LUFS EBU R128)

### Installazione su Linux (Debian, Ubuntu, Arch, Fedora, Mint)

L'app non gira più come demone `root`, ma come servizio esclusivo del tuo **utente Linux**, per una maggiore stabilità col server audio (DBUS/PulseAudio/Pipewire).

1.  **Clona il repository:**
    ```bash
    git clone https://github.com/tuo-user/RMusicPlayer.git
    cd RMusicPlayer
    ```

2.  **Esegui l'installer universale:**
    ```bash
    bash install_service.sh
    ```
    *Questo script installerà automaticamente FFmpeg, Python venv, le dipendenze, e creerà il servizio utente `systemctl --user`.*

3.  **Controlli di base:**
    *   Riavvia: `systemctl --user restart rmusicplayer`
    *   Stato: `systemctl --user status rmusicplayer`

4.  **Accedi al player:**
    Apri il browser e vai su `http://localhost:5000` (o l'IP locale della macchina).

---

## Primo Utilizzo e Manutenzione

Al primo avvio, il sistema inizierà automaticamente ad analizzare la tua libreria usando `librosa` e `ffmpeg`.
*   **Nota:** La prima analisi può richiedere tempo se hai migliaia di brani. I dati vengono salvati localmente (database JSON) e **incapsulati direttamente nei Tag ID3** dei singoli file MP3, garantendone la conservazione.

### Aggiunta Nuova Musica
Dopo aver aggiunto nuovi file MP3 alla cartella `RMusicPlayer`:
1.  Clicca sull'icona **Ingranaggio**.
2.  Seleziona **Analizza Nuovi**.
3.  Il sistema scansionerà solo i file non analizzati confrontandone l'hash univoco.

---

## Disclaimer Legale e Sicurezza

**LEGGERE ATTENTAMENTE PRIMA DELL'USO**

*   **Sicurezza:** Il codice include protezioni contro vulnerabilità comuni (Path Traversal, XSS), ma non è certificato per l'uso su server pubblici esposti a Internet. Si raccomanda l'uso solo in rete locale (LAN) protetta.
*   **Copyright:** L'utente è l'unico responsabile per l'acquisizione legale dei file musicali.
*   **Esecuzione Pubblica:** L'utilizzo in luoghi pubblici è soggetto alle leggi sul diritto d'autore locali (SIAE/SCF).

**Utilizzando questo software, accetti integralmente queste condizioni e esoneri lo sviluppatore da qualsiasi responsabilità.**

---

## Tecnologie Usate

*   **Backend:** Flask (Python)
*   **Audio Engine:** Pygame Mixer-CE + Pydub + Librosa
*   **Analisi Metadati:** Mutagen (ID3)
*   **Frontend:** Bootstrap 5 + Vanilla JS
*   **Processing:** Python Multiprocessing (per analisi e pre-loading non bloccante)

---

Buon ascolto!