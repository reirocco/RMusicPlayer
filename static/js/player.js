let currentPath = "";
let pathHistory = [];
const ITEMS_PER_PAGE = 12;
let currentPage = 1;
let currentFoldersList = [];

function encodePath(path) {
    if (!path) return "";
    return path.split('/').map(encodeURIComponent).join('/');
}

document.addEventListener("DOMContentLoaded", () => {
    checkAnalysisStatus();
    setInterval(updateServerStatus, 1500);
});

function checkAnalysisStatus() {
    fetch('/api/analysis_status')
        .then(res => res.json())
        .then(data => {
            if (data.is_running) {
                document.getElementById('analysis-progress-bar').style.width = data.progress + "%";
                document.getElementById('analysis-text').innerText = data.text;
                setTimeout(checkAnalysisStatus, 500);
            } else {
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

function fetchFolders(path) {
    let url = path ? `/api/folders/${encodePath(path)}` : `/api/folders`;
    fetch(url)
        .then(response => response.json())
        .then(folders => {
            currentPage = 1;
            currentFoldersList = folders;
            renderNavAndFolders(path);
        });
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
    renderCurrentPage();
}

function renderCurrentPage() {
    const container = document.getElementById('folder-container');
    container.innerHTML = '';

    const startIndex = (currentPage - 1) * ITEMS_PER_PAGE;
    const endIndex = startIndex + ITEMS_PER_PAGE;
    const pageItems = currentFoldersList.slice(startIndex, endIndex);

    pageItems.forEach(folder => {
        const col = document.createElement('div');
        col.className = 'col-6 col-md-4 col-lg-3';

        const pad = document.createElement('div');
        pad.className = 'glass-panel glass-card ' + (folder.has_subfolders ? 'folder' : 'playlist');

        const iconClass = folder.has_subfolders ? 'bi-folder2-open' : 'bi-music-note-list';

        pad.innerHTML = `
            <i class="bi ${iconClass}"></i>
            <span class="card-title">${folder.name}</span>
        `;

        pad.onclick = () => {
            if (folder.has_subfolders) {
                pathHistory.push(currentPath);
                currentPath = folder.path;
                fetchFolders(currentPath);
            } else {
                startServerAutomix(folder.path);
            }
        };

        col.appendChild(pad);
        container.appendChild(col);
    });

    renderPaginationControls();
}

function changePage(delta) {
    currentPage += delta;
    window.scrollTo(0,0);
    renderCurrentPage();
}

function renderPaginationControls() {
    const pagContainer = document.getElementById('pagination-container');
    if (!pagContainer) return;
    pagContainer.innerHTML = '';

    const totalPages = Math.ceil(currentFoldersList.length / ITEMS_PER_PAGE);

    if (totalPages > 1) {
        pagContainer.style.display = 'flex';

        if (currentPage > 1) {
            const btnPrev = document.createElement('button');
            btnPrev.className = 'btn-glass';
            btnPrev.innerHTML = '<i class="bi bi-chevron-left"></i>';
            btnPrev.onclick = () => changePage(-1);
            pagContainer.appendChild(btnPrev);
        }

        const indicator = document.createElement('span');
        indicator.className = 'mx-3 fw-bold';
        indicator.innerText = `${currentPage} / ${totalPages}`;
        pagContainer.appendChild(indicator);

        if (currentPage < totalPages) {
            const btnNext = document.createElement('button');
            btnNext.className = 'btn-glass';
            btnNext.innerHTML = '<i class="bi bi-chevron-right"></i>';
            btnNext.onclick = () => changePage(1);
            pagContainer.appendChild(btnNext);
        }
    } else {
        pagContainer.style.display = 'none';
    }
}

function goBack() {
    if (pathHistory.length > 0) {
        currentPath = pathHistory.pop();
        fetchFolders(currentPath);
    } else {
        currentPath = "";
        fetchFolders("");
    }
}

function startServerAutomix(folderPath) {
    fetch('/api/play_folder', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ folder: folderPath })
    })
    .then(response => response.json())
    .then(data => {
        if(data.status === "error") alert(data.message);
    });
}

function updateServerStatus() {
    fetch('/api/status')
        .then(res => res.json())
        .then(data => {
            let trackText = document.getElementById('deck-track');
            let bpmText = document.getElementById('deck-bpm');
            let keyText = document.getElementById('deck-key');
            let playPauseBtn = document.getElementById('playPauseBtn');
            let playPauseIcon = document.getElementById('playPauseIcon');

            if(data.is_playing && data.current_track) {
                trackText.innerText = data.current_track.split('/').pop().replace('.mp3', '');
                bpmText.innerText = data.bpm ? Math.round(data.bpm) : "---";
                keyText.innerText = data.key || "--";
                playPauseBtn.disabled = false;

                if (data.is_paused) {
                    document.getElementById('deck-status').innerText = "In Pausa";
                    playPauseIcon.className = "bi bi-play-fill";
                    playPauseBtn.classList.remove('playing');
                } else {
                    document.getElementById('deck-status').innerText = "In Riproduzione";
                    playPauseIcon.className = "bi bi-pause-fill";
                    playPauseBtn.classList.add('playing');
                }
            }
        })
        .catch(() => {});
}

function togglePlayPause() {
    fetch('/api/toggle_playback', { method: 'POST' });
}