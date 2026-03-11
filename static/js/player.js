let currentPath = "";
let pathHistory = [];
const ITEMS_PER_PAGE = 1000;
let currentPage = 1;
let currentFoldersList = [];
let hasFilesHere = false;
let analysisRunning = true;

function encodePath(path) {
    if (!path) return "";
    return path.split('/').map(encodeURIComponent).join('/');
}

document.addEventListener("DOMContentLoaded", () => {
    checkAnalysisStatus();
    setInterval(updateServerStatus, 1500);
    setInterval(checkPing, 2000);
});

function formatTime(seconds) {
    if (seconds === null || seconds === undefined) return "--:--";
    let m = Math.floor(seconds / 60);
    let s = Math.floor(seconds % 60);
    return `${m}m ${s}s`;
}

function checkAnalysisStatus() {
    if (!analysisRunning) return;

    fetch('/api/analysis_status')
        .then(res => res.json())
        .then(data => {
            if (data.is_running) {
                let bar = document.getElementById('analysis-progress-bar');
                let text = document.getElementById('analysis-text');
                let etaText = document.getElementById('eta-text');

                document.getElementById('loading-screen').style.display = 'flex';

                if (bar) bar.style.width = data.progress + "%";
                if (text) text.innerText = data.text;
                if (etaText && data.eta_seconds !== undefined) {
                    etaText.innerText = "Tempo stimato: " + formatTime(data.eta_seconds);
                }
                setTimeout(checkAnalysisStatus, 1000);
            } else {
                analysisRunning = false;
                document.getElementById('loading-screen').style.display = 'none';
                document.getElementById('main-content').style.display = 'block';
                fetchFolders("");
            }
        })
        .catch(err => {
            console.error("Errore stato analisi", err);
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
        const typeClass = item.has_subfolders ? 'folder' : 'playlist';
        pad.className = `glass-panel glass-card ${typeClass}`;
        const iconClass = item.has_subfolders ? 'bi-folder2-open' : 'bi-music-note-list';
        const icon = document.createElement('i');
        icon.className = `bi ${iconClass}`;
        const title = document.createElement('span');
        title.className = 'card-title';
        title.innerText = item.name;
        pad.appendChild(icon);
        pad.appendChild(title);
        if (!item.has_subfolders && item.track_count !== undefined) {
            const count = document.createElement('span');
            count.className = 'text-muted small mt-1';
            count.innerText = item.track_count + ' brani';
            pad.appendChild(count);
        }
        pad.onclick = () => {
            if (item.has_subfolders) {
                pathHistory.push(currentPath);
                fetchFolders(item.path);
            } else {
                startServerAutomix(item.path);
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

            } else {
                statusText.innerText = "Standby";
                playPauseBtn.classList.remove('playing');
                if(nextBtn) nextBtn.disabled = true;
                if(queueBtn) queueBtn.disabled = true;
                if(queueBadge) queueBadge.style.display = 'none';
            }
        })
        .catch(() => {});
}

function togglePlayPause() {
    fetch('/api/toggle_playback', { method: 'POST' });
}

function triggerNextTrack() {
    fetch('/api/next_track', { method: 'POST' });
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
            if (data.queue && data.queue.length > 0) {
                const limit = 500;
                data.queue.slice(0, limit).forEach(path => {
                    let li = document.createElement('li');
                    li.className = 'queue-item-full';
                    let icon = document.createElement('i');
                    icon.className = 'bi bi-music-note-beamed';
                    let nameSpan = document.createElement('span');
                    nameSpan.innerText = path.split('/').pop().replace('.mp3', '');
                    li.appendChild(icon);
                    li.appendChild(nameSpan);
                    listEl.appendChild(li);
                });
                if(data.queue.length > limit) {
                    let li = document.createElement('li');
                    li.className = 'queue-item-full text-center fst-italic';
                    li.innerText = `...e altri ${data.queue.length - limit} brani`;
                    listEl.appendChild(li);
                }
            } else {
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
    // Reset view
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

    fetch('/api/admin/reanalyze', { method: 'POST' })
        .then(res => res.json())
        .then(data => {
            bootstrap.Modal.getInstance(document.getElementById('settingsModal')).hide();
            analysisRunning = true;
            checkAnalysisStatus();
        });
}

function triggerScanNew() {
    fetch('/api/admin/scan_new', { method: 'POST' })
        .then(res => res.json())
        .then(data => {
            bootstrap.Modal.getInstance(document.getElementById('settingsModal')).hide();
            analysisRunning = true;
            document.getElementById('loading-screen').style.display = 'flex';
            document.getElementById('analysis-text').innerText = "Scansione nuovi file...";
            checkAnalysisStatus();
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