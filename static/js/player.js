let currentPath = "";
let pathHistory = [];
const ITEMS_PER_PAGE = 1000;
let currentPage = 1;
let currentFoldersList = [];
let hasFilesHere = false;
let analysisRunning = true;
let logInterval = null;

let localTrackPos = 0;
let localTrackDur = 0;
let localIsPlaying = false;
let localLastSyncTime = Date.now();

function encodePath(path) {
    if (!path) return "";
    return path.split('/').map(encodeURIComponent).join('/');
}

document.addEventListener("DOMContentLoaded", () => {
    checkAnalysisStatus();
    setInterval(updateServerStatus, 1500);
    setInterval(checkPing, 2000);

    const consoleModal = document.getElementById('consoleModal');
    consoleModal.addEventListener('hidden.bs.modal', () => {
        if (logInterval) clearInterval(logInterval);
    });
});

function triggerNormalizeMixes() {
    if (confirm("Vuoi normalizzare in modo permanente il volume di tutti i mix lunghi? Questo processo modificherà i file MP3 originali e potrebbe richiedere molto tempo.")) {
        fetch('/api/admin/normalize_mixes', { method: 'POST' })
            .then(res => res.json())
            .then(data => {
                alert(data.message);
                checkAnalysisStatus();
            })
            .catch(err => alert("Errore di rete"));
    }
}

function formatTime(seconds) {
    if (seconds === null || seconds === undefined) return "--:--";
    let m = Math.floor(seconds / 60);
    let s = Math.floor(seconds % 60);
    return `${m}m ${s}s`;
}

function checkAnalysisStatus() {
    fetch('/api/analysis_status')
        .then(res => res.json())
        .then(data => {
            const fullLoader = document.getElementById('full-loading-screen');
            const miniLoader = document.getElementById('loading-panel');

            if (data.is_running) {
                analysisRunning = true;

                // Aggiorna i testi e le barre PRIMA di mostrare, per evitare sfarfallii
                let bar = document.getElementById('analysis-progress-bar');
                let text = document.getElementById('analysis-text');
                let etaText = document.getElementById('eta-text');

                if (bar) bar.style.width = data.progress + "%";
                if (text) text.innerText = data.text;
                if (etaText && data.eta_seconds !== undefined) {
                    etaText.innerText = "Tempo stimato: " + formatTime(data.eta_seconds);
                }

                // Aggiorna la progress bar della schermata Full Screen
                let fullBar = document.getElementById('full-analysis-progress-bar');
                let fullSubtext = document.getElementById('full-analysis-subtext');
                let fullEtaText = document.getElementById('full-eta-text');
                let fullMainText = document.getElementById('full-loading-text');

                if (fullBar) fullBar.style.width = data.progress + "%";
                if (fullSubtext) fullSubtext.innerText = data.text;
                if (fullEtaText && data.eta_seconds !== undefined) {
                    fullEtaText.innerText = "Tempo stimato: " + formatTime(data.eta_seconds);
                }
                if (fullMainText) {
                    fullMainText.innerText = "Analisi in corso: " + data.progress + "%";
                }

                // Logica di visualizzazione intelligente
                // Se non c'è nulla caricato nel main content (primo avvio), usa Full Screen
                if (currentFoldersList.length === 0 && document.getElementById('main-content').style.display === 'none') {
                    fullLoader.style.display = 'flex';
                    miniLoader.style.display = 'none';
                } else {
                    // Altrimenti (uso normale), usa il Mini Loader
                    fullLoader.style.display = 'none';
                    miniLoader.style.display = 'block';
                }

                // Continua il polling
                setTimeout(checkAnalysisStatus, 1000);
            } else {
                if (analysisRunning) {
                    // Se stava correndo e ora ha finito:
                    analysisRunning = false;
                    fullLoader.style.display = 'none';
                    miniLoader.style.display = 'none';
                    document.getElementById('main-content').style.display = 'block';
                    fetchFolders(""); // Ricarica le cartelle aggiornate
                }
            }
        })
        .catch(err => {
            // In caso di errore di rete, riprova con calma
            setTimeout(checkAnalysisStatus, 2000);
        });
}

function checkPing() {
    const start = Date.now();
    fetch('/api/ping')
        .then(res => res.json())
        .then(() => {
            const ms = Date.now() - start;
            const dot = document.getElementById('ping-dot');
            const text = document.getElementById('ping-text');
            if(dot && text) {
                text.innerText = ms + " ms";
                dot.className = 'status-dot';
                if (ms < 50) dot.classList.add('success');
                else if (ms < 200) dot.classList.add('yellow');
                else dot.classList.add('red');
            }
        })
        .catch(() => {
            if(document.getElementById('ping-dot')) {
                document.getElementById('ping-dot').className = 'status-dot red';
                document.getElementById('ping-text').innerText = "Offline";
            }
        });
}

function fetchFolders(path) {
    let url = path ? `/api/folders/${encodePath(path)}` : `/api/folders`;

    fetch(url)
        .then(response => response.json())
        .then(data => {
            currentFoldersList = data.folders || [];
            hasFilesHere = data.has_files || false;
            currentPage = 1;
            renderNavAndFolders(path);

            // Se abbiamo caricato le cartelle, mostra il contenuto principale
            document.getElementById('main-content').style.display = 'block';
            document.getElementById('full-loading-screen').style.display = 'none';
        })
        .catch(err => console.error("Errore fetch folders", err));
}

function renderNavAndFolders(path) {
    const navBar = document.getElementById('navigation-bar');
    if (path) {
        navBar.style.display = 'flex';
        let folderNameOnly = path.split('/').pop();
        document.getElementById('current-path-display').innerText = folderNameOnly;
    } else {
        navBar.style.display = 'none';
    }

    currentPath = path;
    renderCurrentPage();
}

function renderCurrentPage() {
    const container = document.getElementById('folder-container');
    container.innerHTML = '';

    const startIndex = (currentPage - 1) * ITEMS_PER_PAGE;
    const endIndex = startIndex + ITEMS_PER_PAGE;
    const pageItems = currentFoldersList.slice(startIndex, endIndex);

    if (hasFilesHere && currentPage === 1) {
        const col = document.createElement('div');
        col.className = 'col-6 col-md-4 col-lg-3';
        const pad = document.createElement('div');
        pad.className = 'glass-panel glass-card playlist';
        pad.style.borderColor = 'var(--accent-color)';
        pad.innerHTML = `
            <i class="bi bi-play-circle-fill" style="color:var(--accent-color); font-size: 3.5rem;"></i>
            <span class="card-title text-uppercase" style="letter-spacing:1px; font-size:0.9rem;">Riproduci Cartella</span>
            <span class="text-muted small mt-1">Brani misti</span>
        `;
        pad.onclick = () => startServerAutomix(currentPath);
        col.appendChild(pad);
        container.appendChild(col);
    }

    pageItems.forEach(item => {
        const col = document.createElement('div');
        col.className = 'col-6 col-md-4 col-lg-3';
        
        const pad = document.createElement('div');
        let typeClass = item.is_folder ? (item.has_subfolders ? 'folder' : 'playlist') : 'file';
        pad.className = `glass-panel glass-card ${typeClass}`;
        
        if (!item.is_folder) {
            pad.style.background = 'linear-gradient(145deg, rgba(139, 92, 246, 0.1) 0%, rgba(139, 92, 246, 0.02) 100%)';
            pad.style.borderColor = 'rgba(139, 92, 246, 0.2)';
            pad.style.minHeight = '130px';
        }
        
        const iconClass = item.is_folder ? (item.has_subfolders ? 'bi-folder2-open' : 'bi-music-note-list') : 'bi-music-note';
        const icon = document.createElement('i');
        icon.className = `bi ${iconClass}`;
        if (!item.is_folder) {
            icon.style.fontSize = '2.5rem';
            icon.style.color = '#cbd5e1';
            icon.style.marginBottom = '5px';
        }
        
        const title = document.createElement('span');
        title.className = 'card-title';
        title.innerText = item.name.replace('.mp3', '');
        if (!item.is_folder) title.style.fontSize = '0.9rem';
        
        pad.appendChild(icon);
        pad.appendChild(title);
        
        if (item.is_folder && item.track_count !== undefined) {
            const count = document.createElement('span');
            count.className = 'text-muted small mt-1';
            count.innerText = item.track_count + ' brani';
            pad.appendChild(count);
        }
        
        const addBtn = document.createElement('button');
        addBtn.className = 'btn btn-sm btn-outline-light position-absolute top-0 end-0 m-2 rounded-circle';
        addBtn.innerHTML = '<i class="bi bi-plus-lg"></i>';
        addBtn.style.zIndex = '10';
        addBtn.style.width = '32px';
        addBtn.style.height = '32px';
        addBtn.style.display = 'flex';
        addBtn.style.alignItems = 'center';
        addBtn.style.justifyContent = 'center';
        addBtn.style.border = 'none';
        addBtn.style.background = 'rgba(255,255,255,0.1)';
        addBtn.onclick = (e) => {
            e.stopPropagation();
            addToQueue(item.path, item.is_folder);
            addBtn.innerHTML = '<i class="bi bi-check-lg text-success"></i>';
            setTimeout(() => addBtn.innerHTML = '<i class="bi bi-plus-lg"></i>', 1000);
        };
        pad.appendChild(addBtn);
        
        pad.onclick = () => {
            if (item.is_folder) {
                if (item.has_subfolders) {
                    pathHistory.push(currentPath);
                    fetchFolders(item.path);
                } else {
                    startServerAutomix(item.path);
                }
            } else {
                addToQueue(item.path, false);
                let iconEl = pad.querySelector('i.bi-music-note');
                if (iconEl) {
                    iconEl.className = 'bi bi-check-circle-fill text-success';
                    setTimeout(() => iconEl.className = 'bi bi-music-note', 1000);
                }
            }
        };
        col.appendChild(pad);
        container.appendChild(col);
    });
    renderPaginationControls();
}

function renderPaginationControls() {
    const pagContainer = document.getElementById('pagination-container');
    if (!pagContainer) return;
    pagContainer.innerHTML = '';
    const totalPages = Math.ceil(currentFoldersList.length / ITEMS_PER_PAGE);
    if (totalPages > 1) {
        pagContainer.style.display = 'flex';
    } else {
        pagContainer.style.display = 'none';
    }
}

function goBack() {
    if (pathHistory.length > 0) {
        let prev = pathHistory.pop();
        fetchFolders(prev);
    } else {
        fetchFolders("");
    }
}

function startServerAutomix(folderPath) {
    fetch('/api/play_folder', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ folder: folderPath })
    })
    .then(res => res.json())
    .then(data => {
        if(data.status === "error") alert("Errore: " + data.message);
    });
}

function addToQueue(path, isFolder) {
    fetch('/api/queue/add', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: path, is_folder: isFolder })
    })
    .then(res => res.json())
    .then(data => {
        if(data.status === "error") alert("Errore: " + data.message);
        else updateServerStatus();
    });
}

function updateServerStatus() {
    fetch('/api/status')
        .then(res => res.json())
        .then(data => {
            const trackText = document.getElementById('deck-track');
            const bpmText = document.getElementById('deck-bpm');
            const keyText = document.getElementById('deck-key');
            const playPauseBtn = document.getElementById('playPauseBtn');
            const playPauseIcon = document.getElementById('playPauseIcon');
            const statusText = document.getElementById('deck-status');
            const nextBtn = document.getElementById('nextBtn');
            const queueBtn = document.getElementById('queueBtn');
            const queueBadge = document.getElementById('queue-badge');

            if(data.is_playing) {
                playPauseBtn.disabled = false;
                if(nextBtn) nextBtn.disabled = false;
                if(queueBtn) queueBtn.disabled = false;

                if (data.current_track) {
                    trackText.innerText = data.current_track.split('/').pop().replace('.mp3', '');
                }

                bpmText.innerText = data.bpm ? Math.round(data.bpm) : "---";
                let keyDisplay = data.key || "--";
                if (data.camelot) {
                    keyDisplay += ` (${data.camelot})`;
                }
                keyText.innerText = keyDisplay;

                if (data.is_paused) {
                    statusText.innerText = "In Pausa";
                    playPauseIcon.className = "bi bi-play-fill";
                    playPauseBtn.classList.remove('playing');
                } else {
                    statusText.innerText = "In Riproduzione";
                    playPauseIcon.className = "bi bi-pause-fill";
                    playPauseBtn.classList.add('playing');
                }

                if (data.queue_count !== undefined) {
                    queueBadge.innerText = data.queue_count;
                    queueBadge.style.display = 'inline-block';
                }

                const loopBtn = document.getElementById('automixLoopBtn');
                const loopIcon = document.getElementById('automixLoopIcon');
                if (loopBtn && loopIcon) {
                    if (data.is_folder_loop_active) {
                        loopIcon.className = "bi bi-infinity";
                        loopIcon.style.color = "var(--accent-color)";
                        loopBtn.style.borderColor = "var(--accent-color)";
                    } else {
                        loopIcon.className = "bi bi-infinity";
                        loopIcon.style.color = "";
                        loopBtn.style.borderColor = "rgba(255,255,255,0.1)";
                    }
                }

                localIsPlaying = !data.is_paused;

            } else {
                statusText.innerText = "Standby";
                playPauseBtn.classList.remove('playing');
                if(nextBtn) nextBtn.disabled = true;
                if(queueBtn) queueBtn.disabled = true;
                if(queueBadge) queueBadge.style.display = 'none';
                
                localIsPlaying = false;
                localTrackDur = 0;
                localTrackPos = 0;
            }
        })
        .catch(() => {});
}

function formatDuration(sec) {
    if (!sec || isNaN(sec) || sec < 0) return "0:00";
    let m = Math.floor(sec / 60);
    let s = Math.floor(sec % 60);
    return `${m}:${s < 10 ? '0' : ''}${s}`;
}

function togglePlayPause() {
    fetch('/api/toggle_playback', { method: 'POST' });
}

function triggerNextTrack() {
    fetch('/api/next_track', { method: 'POST' });
}

function toggleAutomixLoop() {
    fetch('/api/toggle_loop', { method: 'POST' })
        .then(res => res.json())
        .then(data => {
            updateServerStatus();
        });
}

function openQueue() {
    const offcanvasEl = document.getElementById('queueOffcanvas');
    const offcanvas = new bootstrap.Offcanvas(offcanvasEl);
    offcanvas.show();
    const listEl = document.getElementById('full-queue-list');
    listEl.innerText = 'Caricamento...';
    fetch('/api/queue')
        .then(res => res.json())
        .then(data => {
            listEl.innerHTML = '';
            
            if (data.explicit_queue && data.explicit_queue.length > 0) {
                let header = document.createElement('li');
                header.className = 'queue-item-full fw-bold text-uppercase';
                header.style.color = 'var(--accent-color)';
                header.style.background = 'rgba(217, 70, 239, 0.1)';
                header.innerText = 'Prossimi Brani (Manuale)';
                listEl.appendChild(header);
                
                data.explicit_queue.forEach(path => {
                    let li = document.createElement('li');
                    li.className = 'queue-item-full';
                    let icon = document.createElement('i');
                    icon.className = 'bi bi-music-note-list me-3 text-warning';
                    let nameSpan = document.createElement('span');
                    nameSpan.innerText = path.split('/').pop().replace('.mp3', '');
                    li.appendChild(icon);
                    li.appendChild(nameSpan);
                    listEl.appendChild(li);
                });
            }
            
            if (data.automix_queue && data.automix_queue.length > 0) {
                let header = document.createElement('li');
                header.className = 'queue-item-full fw-bold text-uppercase mt-3';
                header.style.color = '#a78bfa';
                header.innerText = 'Coda Automix';
                listEl.appendChild(header);
                
                const limit = 300;
                data.automix_queue.slice(0, limit).forEach(path => {
                    let li = document.createElement('li');
                    li.className = 'queue-item-full';
                    let icon = document.createElement('i');
                    icon.className = 'bi bi-music-note-beamed me-3 text-secondary';
                    let nameSpan = document.createElement('span');
                    nameSpan.innerText = path.split('/').pop().replace('.mp3', '');
                    li.appendChild(icon);
                    li.appendChild(nameSpan);
                    listEl.appendChild(li);
                });
                if(data.automix_queue.length > limit) {
                    let li = document.createElement('li');
                    li.className = 'queue-item-full text-center fst-italic';
                    li.innerText = `...e altri ${data.automix_queue.length - limit} brani`;
                    listEl.appendChild(li);
                }
            } else if (!data.explicit_queue || data.explicit_queue.length === 0) {
                listEl.innerText = 'Coda vuota';
            }
        })
        .catch(err => {
            listEl.innerText = 'Errore caricamento';
        });
}

function openSettings() {
    const modalEl = document.getElementById('settingsModal');
    const modal = new bootstrap.Modal(modalEl);
    modal.show();
    hideAnalysisOptions();
}

function showAnalysisOptions() {
    document.getElementById('settings-grid').style.display = 'none';
    document.getElementById('analysis-options').style.display = 'block';
}

function hideAnalysisOptions() {
    document.getElementById('analysis-options').style.display = 'none';
    document.getElementById('settings-grid').style.display = 'grid';
}

function triggerReanalyze() {
    if(!confirm("ATTENZIONE: Questo cancellerà l'intero database e rianalizzerà tutto da zero. Ci vorrà tempo. Continuare?")) return;

    // Mostra subito il loader FULL SCREEN per feedback immediato
    document.getElementById('full-loading-screen').style.display = 'flex';
    document.getElementById('main-content').style.display = 'none';

    bootstrap.Modal.getInstance(document.getElementById('settingsModal')).hide();

    fetch('/api/admin/reanalyze', { method: 'POST' })
        .then(res => res.json())
        .then(data => {
            window.location.reload();
        });
}

function triggerScanNew() {
    // Mostra subito il MINI loader per feedback immediato
    document.getElementById('loading-panel').style.display = 'block';
    document.getElementById('analysis-text').innerText = "Avvio scansione...";

    bootstrap.Modal.getInstance(document.getElementById('settingsModal')).hide();

    fetch('/api/admin/scan_new', { method: 'POST' })
        .then(res => res.json())
        .then(data => {
            window.location.reload();
        });
}

function stopAnalysis() {
    if(!confirm("Sei sicuro di voler interrompere l'analisi in corso?")) return;
    
    fetch('/api/admin/stop_analysis', { method: 'POST' })
        .then(res => res.json())
        .then(data => {
            alert(data.message || "Richiesta di interruzione inviata.");
        })
        .catch(err => {
            alert("Errore durante l'interruzione.");
        });
}

function triggerRestart() {
    if(!confirm("Riavviare il server RMusicPlayer? La musica si interromperà.")) return;
    fetch('/api/admin/restart', { method: 'POST' })
        .then(() => {
            bootstrap.Modal.getInstance(document.getElementById('settingsModal')).hide();
            alert("Server in riavvio. La pagina si ricaricherà tra 5 secondi.");
            setTimeout(() => window.location.reload(), 5000);
        });
}

function downloadBackup() {
    window.location.href = '/api/admin/backup';
}

function viewDbContent() {
    window.open('/api/admin/db_content', '_blank');
}

function openConsoleModal() {
    const modalEl = document.getElementById('consoleModal');
    const modal = new bootstrap.Modal(modalEl);
    modal.show();

    const settingsEl = document.getElementById('settingsModal');
    const settingsModal = bootstrap.Modal.getInstance(settingsEl);
    if(settingsModal) settingsModal.hide();

    if (logInterval) {
        clearInterval(logInterval);
    }
    fetchLogs();
    logInterval = setInterval(fetchLogs, 1000);
}

function fetchLogs() {
    fetch('/api/admin/logs')
        .then(res => res.json())
        .then(data => {
            const container = document.getElementById('log-container');
            container.innerHTML = '';

            data.logs.forEach(line => {
                const div = document.createElement('div');
                div.className = 'log-entry';
                div.innerText = line;
                container.appendChild(div);
            });
            container.scrollTop = container.scrollHeight;
        });
}