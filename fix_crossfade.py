import re

with open('app.py', 'r') as f:
    content = f.read()

# 1. Add crossfade_id to player_state
old_state = """    'active_channel_id': 0,
    'last_crossfade_time': 0.0,"""
new_state = """    'active_channel_id': 0,
    'last_crossfade_time': 0.0,
    'crossfade_id': 0,"""
content = content.replace(old_state, new_state)

# 2. Modify crossfade_to_next
old_crossfade = """    def fade_in_out(curr, nxt, duration_sec):
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
    player_state['last_play_resume_time'] = now"""

new_crossfade = """    player_state['crossfade_id'] += 1
    current_cf_id = player_state['crossfade_id']

    def fade_in_out(curr, nxt, duration_sec, cf_id):
        steps = 20
        sleep_time = duration_sec / steps
        for i in range(steps):
            if player_state.get('crossfade_id') != cf_id:
                return # Stop thread if a new crossfade started
            vol_out = max(0, 100 - int((i / steps) * 100))
            vol_in = min(100, int((i / steps) * 100))
            try:
                curr.volume = vol_out
                nxt.volume = vol_in
            except: pass
            time.sleep(sleep_time)
            
        if player_state.get('crossfade_id') == cf_id:
            try:
                curr.stop()
                curr.volume = 100
            except: pass

    threading.Thread(target=fade_in_out, args=(current_channel, next_channel, fade_sec, current_cf_id), daemon=True).start()
    
    player_state['current_track'] = next_path
    player_state['active_channel_id'] = next_idx
    player_state['next_track_queued'] = None
    player_state['last_crossfade_time'] = now
    player_state['current_duration_sec'] = duration
    player_state['last_play_resume_time'] = now"""

content = content.replace(old_crossfade, new_crossfade)

# 3. Update the fallback logic in audio_engine_loop to also update last_crossfade_time to avoid infinite loops when queue is empty
old_fallback = """                if getattr(current_channel, 'eof_reached', False) or getattr(current_channel, 'core_idle', False):
                    now = time.time()
                    if now - player_state.get('last_crossfade_time', 0) >= 2.0:
                        crossfade_to_next()"""
new_fallback = """                if getattr(current_channel, 'eof_reached', False) or getattr(current_channel, 'core_idle', False):
                    now = time.time()
                    if now - player_state.get('last_crossfade_time', 0) >= 2.0:
                        player_state['last_crossfade_time'] = now # Prevent instant retry
                        crossfade_to_next()"""
content = content.replace(old_fallback, new_fallback)

# 4. Same for the normal crossfade point
old_cf_point = """                    if dur_sec > fade_sec and pos_sec >= (dur_sec - fade_sec):
                        now = time.time()
                        if now - player_state.get('last_crossfade_time', 0) >= 2.0:
                            print(f"[Automix] Raggiunto punto di crossfade ({pos_sec:.1f}s / {dur_sec:.1f}s).")
                            crossfade_to_next()"""
new_cf_point = """                    if dur_sec > fade_sec and pos_sec >= (dur_sec - fade_sec):
                        now = time.time()
                        if now - player_state.get('last_crossfade_time', 0) >= 2.0:
                            player_state['last_crossfade_time'] = now # Prevent instant retry
                            print(f"[Automix] Raggiunto punto di crossfade ({pos_sec:.1f}s / {dur_sec:.1f}s).")
                            crossfade_to_next()"""
content = content.replace(old_cf_point, new_cf_point)


with open('app.py', 'w') as f:
    f.write(content)
