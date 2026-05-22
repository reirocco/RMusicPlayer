import re

with open('app.py', 'r') as f:
    content = f.read()

# 1. Imports
content = content.replace('import pygame', 'import mpv')

# 2. Config Audio
old_config = """pygame.mixer.pre_init(44100, -16, 2, 4096)
pygame.init()
pygame.mixer.init()
pygame.mixer.set_num_channels(8)

FADE_TIME_MS = 4000
MIN_DURATION_FOR_CROSSFADE = 10
DB_RELOAD_INTERVAL_SEC = 5

CHANNEL_END_EVENTS = {
    0: pygame.USEREVENT + 0,
    1: pygame.USEREVENT + 1
}
MUSIC_END_EVENT = pygame.USEREVENT + 2"""

new_config = """mpv_player_a = mpv.MPV(ytdl=False, video=False)
mpv_player_b = mpv.MPV(ytdl=False, video=False)
channels = {0: mpv_player_a, 1: mpv_player_b}

FADE_TIME_MS = 4000
MIN_DURATION_FOR_CROSSFADE = 10
DB_RELOAD_INTERVAL_SEC = 5"""
content = content.replace(old_config, new_config)

# 3. Player state
old_state = """player_state = {
    'current_track': None, 
    'next_track_queued': None, 
    'next_wav_path': None,
    'folder': None, 
    'is_playing': False, 
    'is_paused': False, 
    'playlist': [],      
    'queue': [],         
    'explicit_queue': [],
    'active_channel_id': 0,
    'last_crossfade_time': 0.0,
    'is_folder_loop_active': False,
    'current_folder_source': None,
    'is_music_active': False,
    'next_is_long': False,
    'force_crossfade_now': False
}"""

new_state = """player_state = {
    'current_track': None, 
    'next_track_queued': None, 
    'folder': None, 
    'is_playing': False, 
    'is_paused': False, 
    'playlist': [],      
    'queue': [],         
    'explicit_queue': [],
    'active_channel_id': 0,
    'last_crossfade_time': 0.0,
    'is_folder_loop_active': False,
    'current_folder_source': None,
}"""
content = content.replace(old_state, new_state)

# 4. Remove Temp Cleanups
content = re.sub(r'def clean_startup_temps\(\):.*?clean_startup_temps\(\)', '', content, flags=re.DOTALL)
content = re.sub(r'def cleanup_old_wavs\(\):.*?except Exception as e: print\(f"\[System\] Impossibile pulire wav: \{e\}"\)', '', content, flags=re.DOTALL)

# 5. Preload Worker
old_preload_worker = r'def preload_worker\(.*?print\(f"\[Worker\] Errore: \{e\}"\)'
content = re.sub(old_preload_worker, '', content, flags=re.DOTALL)

# 6. Schedule Preload
old_schedule = r'def schedule_preload\(\):.*?p\.start\(\)'
new_schedule = """def schedule_preload():
    with audio_lock:
        if not player_state['playlist'] and not player_state['queue'] and not player_state['explicit_queue']: return
        if player_state.get('next_track_queued'): return

        next_track_path = pop_next_track()
        if not next_track_path: return

        player_state['next_track_queued'] = next_track_path
        print(f"[Scheduler] Prossima traccia in coda: '{next_track_path}'")"""
content = re.sub(old_schedule, new_schedule, content, flags=re.DOTALL)

# 7. Crossfade
old_crossfade = r'def crossfade_to_next\(\):.*?threading\.Thread\(target=schedule_preload, daemon=True\)\.start\(\)'
new_crossfade = """def crossfade_to_next():
    global player_state
    now = time.time()
    if now - player_state.get('last_crossfade_time', 0) < 2.0: return
    
    current_idx = player_state['active_channel_id']
    next_idx = 1 - current_idx 
    
    current_channel = channels[current_idx]
    next_channel = channels[next_idx]

    next_path = player_state.get('next_track_queued')
    if not next_path:
        schedule_preload()
        return

    full_mp3_path = os.path.join(MUSIC_ROOT_DIR, next_path)
    track_info = music_db.get(next_path, {})
    duration = track_info.get('duration', 0.0)
    gain = track_info.get('gain', 0.0)
    trim_start = track_info.get('trim_start', 0.0)
    
    fade_sec = FADE_TIME_MS / 1000.0 if duration > MIN_DURATION_FOR_CROSSFADE else 0.5
    
    print(f"[Automix] Crossfade verso '{next_path}' (Dur: {duration:.1f}s, Gain: {gain}dB)")
    
    if gain != 0.0:
        next_channel.command('set', 'options/af', f'volume={gain}dB')
    else:
        next_channel.command('set', 'options/af', 'volume=0dB')
        
    next_channel.play(full_mp3_path)
    if trim_start > 0:
        next_channel.time_pos = trim_start
        
    def fade_in_out(curr, nxt, duration_sec):
        steps = 20
        sleep_time = duration_sec / steps
        for i in range(steps):
            vol_out = max(0, 100 - int((i / steps) * 100))
            vol_in = min(100, int((i / steps) * 100))
            try:
                curr.volume = vol_out
                nxt.volume = vol_in
            except: pass
            time.sleep(sleep_time)
        try:
            curr.stop()
            curr.volume = 100
        except: pass

    threading.Thread(target=fade_in_out, args=(current_channel, next_channel, fade_sec), daemon=True).start()
    
    player_state['current_track'] = next_path
    player_state['active_channel_id'] = next_idx
    player_state['next_track_queued'] = None
    player_state['last_crossfade_time'] = now
    player_state['current_duration_sec'] = duration
    player_state['last_play_resume_time'] = now
    
    threading.Thread(target=schedule_preload, daemon=True).start()"""
content = re.sub(old_crossfade, new_crossfade, content, flags=re.DOTALL)

# 8. Audio Engine Loop
old_engine = r'def audio_engine_loop\(\):.*?time\.sleep\(0\.1\)'
new_engine = """def audio_engine_loop():
    while True:
        try:
            if player_state['is_playing'] and not player_state['is_paused']:
                current_channel = channels[player_state['active_channel_id']]
                
                # Check MPV properties
                if current_channel.time_pos is not None:
                    pos_sec = current_channel.time_pos
                    dur_sec = player_state.get('current_duration_sec', 0.0)
                    fade_sec = FADE_TIME_MS / 1000.0
                    
                    if dur_sec > fade_sec and pos_sec >= (dur_sec - fade_sec):
                        now = time.time()
                        if now - player_state.get('last_crossfade_time', 0) >= 2.0:
                            print(f"[Automix] Raggiunto punto di crossfade ({pos_sec:.1f}s / {dur_sec:.1f}s).")
                            crossfade_to_next()
                
                # Fallback se ha smesso di suonare improvvisamente
                if getattr(current_channel, 'eof_reached', False) or getattr(current_channel, 'core_idle', False):
                    now = time.time()
                    if now - player_state.get('last_crossfade_time', 0) >= 2.0:
                        crossfade_to_next()

            if player_state['is_playing'] and not player_state.get('next_track_queued'):
                schedule_preload()
                
        except Exception as e:
            pass
        time.sleep(0.1)"""
content = re.sub(old_engine, new_engine, content, flags=re.DOTALL)

# 9. Play folder API overrides
content = content.replace("tmp_wav = os.path.join(BASE_DIR, f\"temp_first_{uuid.uuid4().hex}.wav\")", "")
content = content.replace("player_state['next_wav_path'] = None", "")
content = content.replace("player_state['force_crossfade_now'] = True", "")

old_play_folder = r'if not is_already_playing:.*?p\.start\(\)'
new_play_folder = """if not is_already_playing:
                        channels[player_state['active_channel_id']].stop()
                    
                    print(f"[Automix] Avvio prima traccia: {first_track}")
                    crossfade_to_next()"""
content = re.sub(old_play_folder, new_play_folder, content, flags=re.DOTALL)

# 10. Queue add
content = content.replace("if not player_state['is_playing'] and not pygame.mixer.get_busy():", "if not player_state['is_playing']:")
content = re.sub(r'end_event_id = CHANNEL_END_EVENTS.*?pygame\.event\.post\(pygame\.event\.Event\(end_event_id\)\)', 'crossfade_to_next()', content, flags=re.DOTALL)

# 11. Next track
old_next_track = r'def next_track\(\):.*?return jsonify\(\{"status": "stopped"\}\)'
new_next_track = """def next_track():
    if player_state['is_playing']:
        crossfade_to_next()
        return jsonify({"status": "fading"})
    return jsonify({"status": "stopped"})"""
content = re.sub(old_next_track, new_next_track, content, flags=re.DOTALL)

# 12. Toggle Playback
old_toggle = r'def toggle_playback\(\):.*?return jsonify\(\{"status": "ok"\}\)'
new_toggle = """def toggle_playback():
    if player_state['is_paused']:
        channels[player_state['active_channel_id']].pause = False
        player_state['last_play_resume_time'] = time.time()
    else:
        channels[player_state['active_channel_id']].pause = True
        elapsed = time.time() - player_state.get('last_play_resume_time', time.time())
        player_state['track_pos_sec'] = player_state.get('track_pos_sec', 0.0) + elapsed
    player_state['is_paused'] = not player_state['is_paused']
    return jsonify({"status": "ok"})"""
content = re.sub(old_toggle, new_toggle, content, flags=re.DOTALL)

# 13. Status
old_status = r'pos = player_state\.get.*?time\.time\(\)\)'
new_status = """if player_state.get('is_playing') and not player_state.get('is_paused'):
        curr = channels[player_state['active_channel_id']]
        if curr.time_pos is not None:
            pos = curr.time_pos
        else:
            pos = 0.0
    else:
        pos = player_state.get('track_pos_sec', 0.0)"""
content = re.sub(old_status, new_status, content, flags=re.DOTALL)

# 14. Freeze support pydub remove
content = re.sub(r'try: from pydub import AudioSegment.*?except ImportError: sys\.exit\(1\)', '', content, flags=re.DOTALL)

with open('app_new.py', 'w') as f:
    f.write(content)
