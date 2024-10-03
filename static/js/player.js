let currentSongs = [];
let currentIndex = 0;
let folderName = '';

function loadSongs(folder) {
    fetch(`/get_songs/${folder}`)
        .then(response => response.json())
        .then(mp3_files => {
            if (mp3_files.length > 0) {
                currentSongs = mp3_files;
                folderName = folder;
                currentIndex = 0;
                playSong(currentIndex);
            } else {
                alert("Nessun file MP3 trovato in questa cartella.");
            }
        })
        .catch(error => console.error('Errore durante il caricamento delle canzoni:', error));
}

function playSong(index) {
    let audioPlayer = document.getElementById('audioPlayer');
    let currentTrackInfo = document.getElementById('currentTrackInfo');

    if (index < currentSongs.length) {
        audioPlayer.src = `/serve_music/${folderName}/${currentSongs[index]}`;
        audioPlayer.play();

        let currentTrackName = currentSongs[index];
        let nextTrackName = (index + 1 < currentSongs.length) ? currentSongs[index + 1] : currentSongs[0];
        currentTrackInfo.innerHTML = `Traccia ${index + 1} di ${currentSongs.length} <br> In riproduzione: <span>${currentTrackName}</span> <br> Prossima traccia: <span>${nextTrackName}</span>`;
    }

    audioPlayer.onended = function() {
        currentIndex++;
        if (currentIndex >= currentSongs.length) {
            currentIndex = 0;
        }
        playSong(currentIndex);
    };
}
