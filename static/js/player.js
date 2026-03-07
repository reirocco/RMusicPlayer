let currentSongs = [];
let currentIndex = 0;
let folderName = '';
let currentPath = "";
let pathHistory = [];

// Funzione d'aiuto per codificare correttamente i percorsi senza rompere gli slash (/)
function encodePath(path) {
    if (!path) return "";
    return path.split('/').map(encodeURIComponent).join('/');
}

// Carica le cartelle principali all'avvio della pagina
document.addEventListener("DOMContentLoaded", () => {
    fetchFolders("");
});

// Richiede le cartelle dal backend
function fetchFolders(path) {
    let url = path ? `/api/folders/${encodePath(path)}` : `/api/folders`;
    fetch(url)
        .then(response => {
            if (!response.ok) throw new Error("Errore rete");
            return response.json();
        })
        .then(folders => {
            renderFolders(folders, path);
        })
        .catch(error => console.error("Errore nel caricamento cartelle:", error));
}

// Genera i bottoni a schermo
function renderFolders(folders, path) {
    const container = document.getElementById('folder-container');
    container.innerHTML = ''; // Svuota i bottoni precedenti

    const navBar = document.getElementById('navigation-bar');
    if (path) {
        navBar.style.display = 'block'; // Mostra il tasto indietro
        document.getElementById('current-path-display').innerText = "Cartella: " + path;
    } else {
        navBar.style.display = 'none'; // Nasconde se siamo nella home
    }

    folders.forEach(folder => {
        const col = document.createElement('div');
        col.className = 'col-md-4';

        const btn = document.createElement('button');
        // Se la cartella contiene sottocartelle usa btn-danger (rosso), altrimenti btn-primary (blu)
        btn.className = `btn ${folder.has_subfolders ? 'btn-danger' : 'btn-primary'} folder-button`;
        btn.innerText = folder.name;

        btn.onclick = () => {
            if (folder.has_subfolders) {
                // Salva il percorso attuale nella cronologia ed entra nella sottocartella
                pathHistory.push(currentPath);
                currentPath = folder.path;
                fetchFolders(currentPath);
            } else {
                // È l'ultimo livello: carica la musica!
                loadSongs(folder.path);
            }
        };

        col.appendChild(btn);
        container.appendChild(col);
    });
}

// Funzione del bottone Indietro
function goBack() {
    if (pathHistory.length > 0) {
        currentPath = pathHistory.pop();
        fetchFolders(currentPath);
    } else {
        currentPath = "";
        fetchFolders("");
    }
}

// Caricamento dei brani
function loadSongs(folderPath) {
    fetch(`/get_songs/${encodePath(folderPath)}`)
        .then(response => response.json())
        .then(mp3_files => {
            if (mp3_files.length > 0) {
                currentSongs = mp3_files;
                folderName = folderPath;
                currentIndex = 0;
                playSong(currentIndex);
            } else {
                alert("Nessun file MP3 trovato in questa cartella.");
            }
        })
        .catch(error => console.error('Errore durante il caricamento delle canzoni:', error));
}

// Riproduzione Brano
function playSong(index) {
    let audioPlayer = document.getElementById('audioPlayer');
    let currentTrackInfo = document.getElementById('currentTrackInfo');

    if (index < currentSongs.length) {
        // Codifica in modo sicuro percorso e nome del file
        let encodedFilePath = encodePath(`${folderName}/${currentSongs[index]}`);
        audioPlayer.src = `/serve_music/${encodedFilePath}`;
        audioPlayer.play();

        let currentTrackName = currentSongs[index];
        let nextTrackName = (index + 1 < currentSongs.length) ? currentSongs[index + 1] : currentSongs[0];
        currentTrackInfo.innerHTML = `Traccia ${index + 1} di ${currentSongs.length} <br> In riproduzione: <span>${currentTrackName}</span> - Prossima traccia: <span>${nextTrackName}</span>`;
    }

    audioPlayer.onended = function() {
        currentIndex++;
        if (currentIndex >= currentSongs.length) {
            currentIndex = 0;
        }
        playSong(currentIndex);
    };
}