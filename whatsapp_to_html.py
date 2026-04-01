import os
import re
import shutil
import json
from datetime import datetime

def clean_text(text):
    return re.sub(r'[\u200e\u200f\u202a-\u202e]', '', text).strip()

def extract_number(filename):
    match = re.search(r'(\d+)', filename)
    return match.group(1) if match else None

def generate_html(chat_txt_path, media_folder, output_html, your_name):
    output_dir = os.path.dirname(output_html) or '.'
    media_output_dir = os.path.join(output_dir, 'media')
    os.makedirs(media_output_dir, exist_ok=True)

    media_by_number = {}
    for root, dirs, files in os.walk(media_folder):
        for f in files:
            num = extract_number(f)
            if num:
                media_by_number[num] = os.path.join(root, f)
    print(f"Найдено медиафайлов с числовыми идентификаторами: {len(media_by_number)}")

    with open(chat_txt_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    print(f"Прочитано строк в чате: {len(lines)}")

    pattern = re.compile(r'\[(\d{1,2}[./]\d{1,2}[./]\d{2,4}), (\d{1,2}:\d{1,2}:\d{1,2})\] ([^:]+): (.*)')
    messages = []
    debug_count = 0

    for raw_line in lines:
        line = clean_text(raw_line)
        if not line:
            continue
        match = pattern.match(line)
        if match:
            date_str, time_str, author, content = match.groups()
            date_str = date_str.replace('/', '.')
            parts = date_str.split('.')
            if len(parts) == 3:
                month, day, year = parts[0], parts[1], parts[2]
                if int(month) > 12:
                    day, month = month, day
                if len(year) == 2:
                    year = '20' + year
                try:
                    dt = datetime.strptime(f"{month}.{day}.{year} {time_str}", "%m.%d.%Y %H:%M:%S")
                except:
                    try:
                        dt = datetime.strptime(f"{day}.{month}.{year} {time_str}", "%d.%m.%Y %H:%M:%S")
                    except:
                        continue
            else:
                continue

            date_label = dt.strftime("%d %B %Y")
            file_html = ""

            attach_pattern = re.compile(r'<прикреплено:\s*([^>]+)>', re.IGNORECASE)
            match_attach = attach_pattern.search(content)
            if match_attach:
                raw_filename = match_attach.group(1).strip()
                filename = clean_text(raw_filename)
                num = extract_number(filename)
                if debug_count < 5:
                    print(f"DEBUG: ищем файл по числу '{num}' (исходное имя: {filename})")
                if num and num in media_by_number:
                    src_path = media_by_number[num]
                    dst_filename = os.path.basename(src_path)
                    dst_path = os.path.join(media_output_dir, dst_filename)
                    if not os.path.exists(dst_path):
                        shutil.copy2(src_path, dst_path)
                    ext = os.path.splitext(dst_filename)[1].lower()
                    if ext in ['.jpg', '.jpeg', '.png', '.gif']:
                        file_html = f'<img src="media/{dst_filename}" class="media-image">'
                    elif ext in ['.mp4', '.mov']:
                        file_html = f'''
                        <div class="video-placeholder" data-src="media/{dst_filename}">
                            <button class="load-video">▶ Загрузить видео</button>
                        </div>
                        '''
                    elif ext == '.opus':
                        file_html = f'''
                        <div class="audio-placeholder" data-src="media/{dst_filename}">
                            <button class="load-audio">▶ Воспроизвести аудио</button>
                        </div>
                        '''
                    elif ext == '.pdf':
                        file_html = f'''
                        <div class="pdf-placeholder" data-src="media/{dst_filename}">
                            <button class="load-pdf">📄 Просмотреть PDF</button>
                        </div>
                        '''
                    else:
                        file_html = f'<a href="media/{dst_filename}" target="_blank" class="media-doc">📄 {dst_filename}</a>'
                    if debug_count < 5:
                        print(f"DEBUG: найден файл {dst_filename}, скопирован")
                else:
                    if debug_count < 5:
                        print(f"DEBUG: файл НЕ найден (число: {num})")
                    file_html = f'<span class="media-missing">❌ Файл не найден: {filename}</span>'
                content = attach_pattern.sub('', content).strip()
                debug_count += 1
            elif "<media omitted>" in content:
                file_html = '<span class="media-omitted">Медиа-файл пропущен (не экспортирован)</span>'
                content = content.replace('<media omitted>', '').strip()
            elif "image omitted" in content.lower():
                file_html = '<span class="media-omitted">Изображение пропущено</span>'
                content = content.replace('image omitted', '').strip()

            messages.append({
                'datetime': dt,
                'timestamp': dt.timestamp(),
                'date_label': date_label,
                'author': author,
                'text': content,
                'media': file_html,
                'time': dt.strftime('%H:%M')
            })

    print(f"Обработано сообщений: {len(messages)}")

    messages_for_json = []
    for msg in messages:
        messages_for_json.append({
            'timestamp': msg['timestamp'],
            'date_label': msg['date_label'],
            'author': msg['author'],
            'text': msg['text'],
            'media': msg['media'],
            'time': msg['time']
        })

    messages_json_str = json.dumps(messages_for_json, ensure_ascii=False)
    your_name_json = json.dumps(your_name, ensure_ascii=False)

    html_template = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
    <title>WhatsApp Chat</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/flatpickr/dist/flatpickr.min.css">
    <script src="https://cdn.jsdelivr.net/npm/flatpickr"></script>
    <style>
        :root {
            --wa-bg: #e5ddd5;
            --wa-panel: #f0f2f5;
            --wa-bubble-out: #dcf8c5;
            --wa-bubble-in: #ffffff;
            --wa-text: #111b21;
            --wa-secondary: #667781;
            --wa-blue: #53bdeb;
            --wa-green: #00a884;
        }
        * { box-sizing: border-box; -webkit-tap-highlight-color: transparent; }
        body, html {
            margin: 0; padding: 0; height: 100%; width: 100%;
            overflow: hidden; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background-color: var(--wa-bg);
        }
        body { display: flex; flex-direction: column; }
        .search-panel {
            flex: 0 0 auto; background-color: var(--wa-panel);
            padding: 10px 15px; display: flex; align-items: center;
            justify-content: space-between; gap: 10px; z-index: 1000;
        }
        .search-panel input {
            flex: 1; padding: 8px; border-radius: 8px; border: 1px solid #ccc; font-size: 14px;
        }
        .chat-wrapper {
            flex: 1; overflow-y: auto; -webkit-overflow-scrolling: touch;
            display: flex; flex-direction: column;
            background-image: url('https://user-images.githubusercontent.com/15075759/28719144-86dc0f70-73b1-11e7-911d-60d70fcded21.png');
            background-repeat: repeat;
        }
        .chat-container { width: 100%; max-width: 800px; margin: 0 auto; padding: 10px 0; }
        .date-divider {
            text-align: center;
            margin: 15px 0;
        }
        .date-divider span {
            background-color: #ffffff; padding: 5px 12px; border-radius: 8px;
            font-size: 12px; color: var(--wa-secondary); box-shadow: 0 1px 0.5px rgba(0,0,0,0.13);
        }
        .message { display: flex; margin: 4px 16px; }
        .message-right { justify-content: flex-end; }
        .bubble {
            max-width: 85%; padding: 8px; border-radius: 8px;
            position: relative; box-shadow: 0 1px 0.5px rgba(0,0,0,0.13);
        }
        .bubble-right { background-color: var(--wa-bubble-out); }
        .bubble-left { background-color: var(--wa-bubble-in); }
        .text { font-size: 15px; line-height: 1.4; color: var(--wa-text); white-space: pre-wrap; }
        .time { font-size: 11px; color: var(--wa-secondary); text-align: right; margin-top: 4px; }
        .voice-player {
            display: flex; align-items: center; gap: 10px;
            padding: 5px; min-width: 220px; user-select: none;
        }
        .play-btn {
            width: 40px; height: 40px; border-radius: 50%;
            border: none; background: transparent; cursor: pointer;
            display: flex; align-items: center; justify-content: center;
            font-size: 24px; color: var(--wa-secondary);
        }
        .player-controls { flex: 1; display: flex; flex-direction: column; gap: 4px; }
        .progress-bar {
            width: 100%; height: 4px; background: rgba(0,0,0,0.1);
            border-radius: 2px; position: relative; cursor: pointer;
        }
        .progress-fill {
            height: 100%; background: var(--wa-blue);
            width: 0%; border-radius: 2px; position: relative;
        }
        .progress-fill::after {
            content: ''; position: absolute; right: -4px; top: -3px;
            width: 10px; height: 10px; background: var(--wa-blue);
            border-radius: 50%;
        }
        .player-info { display: flex; justify-content: space-between; font-size: 11px; color: var(--wa-secondary); }
        .speed-badge {
            background: #e1f3fb; color: #128c7e; padding: 2px 6px;
            border-radius: 10px; font-weight: bold; cursor: pointer;
            font-size: 10px; border: 1px solid #b3e0f2;
        }
        .media-image { max-width: 100%; border-radius: 6px; margin: 4px 0; }
        .video-placeholder, .pdf-placeholder {
            background: #000;
            color: #fff;
            padding: 20px;
            text-align: center;
            border-radius: 8px;
            margin: 8px 0;
        }
        .pdf-placeholder {
            background: #f0f2f5;
            color: #111b21;
            border: 1px dashed #ccc;
        }
        .audio-placeholder { margin: 4px 0; }
        .load-audio, .load-video, .load-pdf {
            background: #25D366;
            border: none;
            border-radius: 16px;
            padding: 6px 12px;
            color: white;
            font-size: 12px;
            cursor: pointer;
            display: inline-block;
            margin: 4px;
        }
        .load-pdf {
            background: #dcf8c5;
            color: #075e54;
        }
        .media-doc { display: inline-block; background: #e9ecef; padding: 4px 8px; border-radius: 6px; text-decoration: none; color: #0669de; }
        .media-missing { color: red; font-size: 12px; }
        .media-omitted { color: #888; font-style: italic; font-size: 12px; }
        .flatpickr-calendar {
            background: white;
            border-radius: 12px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .flatpickr-day.disabled, .flatpickr-day.disabled:hover {
            background: #f0f0f0;
            color: #ccc;
            text-decoration: line-through;
            cursor: default;
        }
        .flatpickr-day.selected {
            background: var(--wa-green);
            border-color: var(--wa-green);
        }
        /* Скрываем оригинальный input для года и стрелки */
        .flatpickr-current-year .numInput.cur-year,
        .flatpickr-current-year .arrowUp,
        .flatpickr-current-year .arrowDown {
            display: none !important;
        }
        .flatpickr-year-select {
            font-size: inherit;
            padding: 2px 4px;
            border-radius: 4px;
            border: 1px solid #ccc;
            background: white;
            margin: 0 2px;
        }
        /* Модальное окно для PDF (десктоп) */
        .pdf-modal-overlay {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.8);
            z-index: 10000;
            display: flex;
            justify-content: center;
            align-items: center;
            cursor: pointer;
        }
        .pdf-modal-content {
            width: 95%;
            height: 95%;
            background: #fff;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 4px 20px rgba(0,0,0,0.5);
            position: relative;
            cursor: default;
        }
        .pdf-modal-content iframe {
            width: 100%;
            height: 100%;
            border: none;
        }
        .pdf-modal-close {
            position: absolute;
            top: 12px;
            right: 20px;
            font-size: 32px;
            font-weight: bold;
            color: #fff;
            background: rgba(0,0,0,0.5);
            width: 40px;
            height: 40px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            z-index: 10001;
            transition: background 0.2s;
        }
        .pdf-modal-close:hover {
            background: rgba(0,0,0,0.8);
        }
        @media (max-width: 768px) {
            .pdf-modal-content {
                width: 100%;
                height: 100%;
                border-radius: 0;
            }
            .pdf-modal-close {
                top: 8px;
                right: 8px;
                width: 32px;
                height: 32px;
                font-size: 24px;
            }
        }
    </style>
</head>
<body>

<div class="search-panel">
    <input type="text" id="date-search" placeholder="Выберите дату">
</div>

<div class="chat-wrapper" id="scroll-wrapper">
    <div class="chat-container" id="messages"></div>
</div>

<script>
    const messages = {messages_json};
    const yourName = {your_name_json};
    const container = document.getElementById('messages');

    function createVoicePlayer(src) {
        const id = 'player-' + Math.random().toString(36).substr(2, 9);
        return `
            <div class="voice-player" id="${id}">
                <button class="play-btn" onclick="togglePlay('${id}', '${src}')">▶</button>
                <div class="player-controls">
                    <div class="progress-bar" onclick="seek(event, '${id}')">
                        <div class="progress-fill" id="${id}-progress"></div>
                    </div>
                    <div class="player-info">
                        <span id="${id}-time">0:00</span>
                        <span class="speed-badge" onclick="changeSpeed('${id}')" id="${id}-speed">1x</span>
                    </div>
                </div>
                <audio id="${id}-audio" src="${src}" ontimeupdate="updateProgress('${id}')" onended="resetPlayer('${id}')"></audio>
            </div>
        `;
    }

    let currentAudioId = null;

    window.togglePlay = (id, src) => {
        const audio = document.getElementById(id + '-audio');
        const btn = document.querySelector('#' + id + ' .play-btn');
        if (audio.paused) {
            if (currentAudioId && currentAudioId !== id) {
                const prevAudio = document.getElementById(currentAudioId + '-audio');
                if (prevAudio && !prevAudio.paused) {
                    prevAudio.pause();
                    const prevBtn = document.querySelector('#' + currentAudioId + ' .play-btn');
                    if (prevBtn) prevBtn.textContent = '▶';
                }
            }
            audio.play().catch(e => console.error("Ошибка воспроизведения:", e));
            btn.textContent = '⏸';
            currentAudioId = id;
        } else {
            audio.pause();
            btn.textContent = '▶';
            if (currentAudioId === id) currentAudioId = null;
        }
    };

    window.updateProgress = (id) => {
        const audio = document.getElementById(id + '-audio');
        const progress = document.getElementById(id + '-progress');
        const timeDisplay = document.getElementById(id + '-time');
        if (audio && progress && timeDisplay && audio.duration) {
            const percent = (audio.currentTime / audio.duration) * 100;
            progress.style.width = percent + '%';
            const mins = Math.floor(audio.currentTime / 60);
            const secs = Math.floor(audio.currentTime % 60);
            timeDisplay.textContent = mins + ':' + (secs < 10 ? '0' : '') + secs;
        }
    };

    window.resetPlayer = (id) => {
        const btn = document.querySelector('#' + id + ' .play-btn');
        if (btn) btn.textContent = '▶';
        const progress = document.getElementById(id + '-progress');
        if (progress) progress.style.width = '0%';
        if (currentAudioId === id) currentAudioId = null;
    };

    window.changeSpeed = (id) => {
        const audio = document.getElementById(id + '-audio');
        const badge = document.getElementById(id + '-speed');
        if (!audio) return;
        const speeds = [1, 1.5, 2];
        let current = speeds.indexOf(audio.playbackRate);
        let next = speeds[(current + 1) % speeds.length];
        audio.playbackRate = next;
        badge.textContent = next + 'x';
    };

    window.seek = (event, id) => {
        const audio = document.getElementById(id + '-audio');
        const bar = event.currentTarget;
        const rect = bar.getBoundingClientRect();
        const pos = (event.clientX - rect.left) / rect.width;
        if (audio.duration) audio.currentTime = pos * audio.duration;
    };

    function setupAudioPlaceholders() {
        document.querySelectorAll('.audio-placeholder').forEach(placeholder => {
            const btn = placeholder.querySelector('.load-audio');
            if (!btn) return;
            btn.removeEventListener('click', audioClickHandler);
            btn.addEventListener('click', audioClickHandler);
            function audioClickHandler(e) {
                e.stopPropagation();
                const existingPlayer = placeholder.querySelector('.voice-player');
                if (existingPlayer) {
                    existingPlayer.remove();
                    btn.style.display = 'inline-block';
                    return;
                }
                const src = placeholder.getAttribute('data-src');
                if (!src) return;
                const playerHtml = createVoicePlayer(src);
                btn.style.display = 'none';
                placeholder.insertAdjacentHTML('beforeend', playerHtml);
            }
        });
    }

    function setupVideoPlaceholders() {
        document.querySelectorAll('.video-placeholder').forEach(placeholder => {
            const btn = placeholder.querySelector('.load-video');
            if (!btn) return;
            btn.removeEventListener('click', videoClickHandler);
            btn.addEventListener('click', videoClickHandler);
            function videoClickHandler(e) {
                e.stopPropagation();
                const existingVideo = placeholder.querySelector('video');
                if (existingVideo) {
                    existingVideo.remove();
                    btn.style.display = 'inline-block';
                    return;
                }
                const src = placeholder.getAttribute('data-src');
                if (!src) return;
                const video = document.createElement('video');
                video.src = src;
                video.controls = true;
                video.preload = 'metadata';
                video.style.maxWidth = '100%';
                video.style.borderRadius = '8px';
                video.style.marginTop = '8px';
                btn.style.display = 'none';
                placeholder.appendChild(video);
                video.play().catch(e => console.error("Ошибка воспроизведения видео:", e));
            }
        });
    }

    function setupPdfPlaceholders() {
        document.querySelectorAll('.pdf-placeholder').forEach(placeholder => {
            const btn = placeholder.querySelector('.load-pdf');
            if (!btn) return;
            btn.removeEventListener('click', pdfClickHandler);
            btn.addEventListener('click', pdfClickHandler);
            function pdfClickHandler(e) {
                e.stopPropagation();
                const src = placeholder.getAttribute('data-src');
                if (!src) return;

                const isMobile = window.innerWidth <= 768;
                if (isMobile) {
                    // На мобильных – открываем PDF в новой вкладке (нативный просмотрщик)
                    window.open(src, '_blank');
                } else {
                    // На десктопе – модальное окно с iframe
                    const existingModal = document.querySelector('.pdf-modal-overlay');
                    if (existingModal) {
                        existingModal.remove();
                        return;
                    }
                    const overlay = document.createElement('div');
                    overlay.className = 'pdf-modal-overlay';
                    const content = document.createElement('div');
                    content.className = 'pdf-modal-content';
                    const iframe = document.createElement('iframe');
                    iframe.src = src;
                    iframe.setAttribute('allowfullscreen', '');
                    content.appendChild(iframe);
                    overlay.appendChild(content);
                    const closeBtn = document.createElement('div');
                    closeBtn.className = 'pdf-modal-close';
                    closeBtn.innerHTML = '×';
                    closeBtn.onclick = () => overlay.remove();
                    overlay.appendChild(closeBtn);
                    overlay.onclick = (e) => {
                        if (e.target === overlay) overlay.remove();
                    };
                    document.body.appendChild(overlay);
                    document.body.style.overflow = 'hidden';
                    overlay.addEventListener('remove', () => {
                        document.body.style.overflow = '';
                    });
                }
            }
        });
    }

    let lastDate = null;
    messages.forEach(msg => {
        if (lastDate !== msg.date_label) {
            const div = document.createElement('div');
            div.className = 'date-divider';
            const dateId = new Date(msg.timestamp * 1000).toISOString().split('T')[0];
            div.id = 'date-' + dateId;
            div.innerHTML = `<span>${msg.date_label}</span>`;
            container.appendChild(div);
            lastDate = msg.date_label;
        }
        const isMe = msg.author === yourName;
        const msgDiv = document.createElement('div');
        msgDiv.className = `message ${isMe ? 'message-right' : ''}`;
        let mediaHtml = msg.media || "";
        msgDiv.innerHTML = `
            <div class="bubble ${isMe ? 'bubble-right' : 'bubble-left'}">
                ${!isMe ? `<div style="font-weight:bold; font-size:12px; color:#d62976; margin-bottom:4px;">${msg.author}</div>` : ''}
                ${msg.text ? `<div class="text">${msg.text}</div>` : ''}
                ${mediaHtml}
                <div class="time">${msg.time}</div>
            </div>
        `;
        container.appendChild(msgDiv);
    });

    setupAudioPlaceholders();
    setupVideoPlaceholders();
    setupPdfPlaceholders();

    // === КАЛЕНДАРЬ С ВЫПАДАЮЩИМ СПИСКОМ ДЛЯ ГОДА ===
    const availableDatesSet = new Set();
    messages.forEach(msg => {
        const d = new Date(msg.timestamp * 1000);
        const yyyy = d.getFullYear();
        const mm = String(d.getMonth() + 1).padStart(2, '0');
        const dd = String(d.getDate()).padStart(2, '0');
        availableDatesSet.add(`${yyyy}-${mm}-${dd}`);
    });

    const firstDate = new Date(messages[0].timestamp * 1000);
    const lastDateMsg = new Date(messages[messages.length-1].timestamp * 1000);
    const minDate = new Date(firstDate.getFullYear(), firstDate.getMonth(), firstDate.getDate());
    const maxDate = new Date(lastDateMsg.getFullYear(), lastDateMsg.getMonth(), lastDateMsg.getDate());

    const disabledDates = [];
    let current = new Date(minDate);
    while (current <= maxDate) {
        const yyyy = current.getFullYear();
        const mm = String(current.getMonth() + 1).padStart(2, '0');
        const dd = String(current.getDate()).padStart(2, '0');
        const dateStr = `${yyyy}-${mm}-${dd}`;
        if (!availableDatesSet.has(dateStr)) {
            disabledDates.push(dateStr);
        }
        current.setDate(current.getDate() + 1);
    }

    function replaceYearInputWithSelect(fpInstance) {
        const calendar = fpInstance.calendarContainer;
        if (!calendar) return;
        const arrows = calendar.querySelectorAll('.arrowUp, .arrowDown');
        arrows.forEach(arrow => arrow.remove());
        let existingSelect = calendar.querySelector('.flatpickr-year-select');
        if (existingSelect) {
            if (existingSelect.value != fpInstance.currentYear) {
                existingSelect.value = fpInstance.currentYear;
            }
            return;
        }
        const yearInput = calendar.querySelector('.numInput.cur-year');
        if (!yearInput || yearInput.tagName !== 'INPUT') return;
        const select = document.createElement('select');
        select.className = 'flatpickr-year-select';
        const startYear = minDate.getFullYear();
        const endYear = maxDate.getFullYear();
        for (let y = startYear; y <= endYear; y++) {
            const option = document.createElement('option');
            option.value = y;
            option.textContent = y;
            if (y === fpInstance.currentYear) option.selected = true;
            select.appendChild(option);
        }
        select.addEventListener('change', (e) => {
            const year = parseInt(e.target.value);
            let newDate = new Date(fpInstance.currentDate);
            newDate.setFullYear(year);
            if (newDate < minDate) newDate = minDate;
            if (newDate > maxDate) newDate = maxDate;
            fpInstance.setDate(newDate);
        });
        yearInput.parentNode.replaceChild(select, yearInput);
    }

    const fp = flatpickr("#date-search", {
        dateFormat: "Y-m-d",
        minDate: minDate,
        maxDate: maxDate,
        disable: disabledDates,
        onChange: function(selectedDates, dateStr, instance) {
            if (dateStr) {
                const target = document.getElementById('date-' + dateStr);
                if (target) {
                    const wrapper = document.getElementById('scroll-wrapper');
                    const targetRect = target.getBoundingClientRect();
                    const wrapperRect = wrapper.getBoundingClientRect();
                    let targetTop = targetRect.top - wrapperRect.top + wrapper.scrollTop;
                    targetTop -= 10;
                    wrapper.scrollTop = targetTop;
                }
            }
        },
        onMonthChange: function(selectedDates, dateStr, instance) {
            const select = instance.calendarContainer.querySelector('.flatpickr-year-select');
            if (select && select.value != instance.currentYear) {
                select.value = instance.currentYear;
            }
        },
        onOpen: function(selectedDates, dateStr, instance) {
            replaceYearInputWithSelect(instance);
        },
        placeholder: "Выберите дату"
    });

    if (fp.isOpen) {
        replaceYearInputWithSelect(fp);
    }
</script>
</body>
</html>
"""

    html_content = html_template.replace('{messages_json}', messages_json_str).replace('{your_name_json}', your_name_json)

    with open(output_html, 'w', encoding='utf-8') as f:
        f.write(html_content)

    print(f"HTML успешно сохранён в {output_html}")
    print(f"Медиафайлы скопированы в папку: {media_output_dir}")

if __name__ == '__main__':
    import sys
    import traceback

    print("Скрипт запущен")
    print("Аргументы:", sys.argv)

    try:
        if len(sys.argv) < 4:
            print("Использование: python whatsapp_to_html.py <путь_к_папке_с_чатом> <ваше_имя> <выходной_файл.html>")
            sys.exit(1)

        folder = sys.argv[1]
        your_name = sys.argv[2]
        output = sys.argv[3]

        print(f"Папка: {folder}")
        print(f"Имя: {your_name}")
        print(f"Выходной файл: {output}")

        chat_txt = None
        for f in os.listdir(folder):
            if f.endswith('_chat.txt') or f.endswith('chat.txt'):
                chat_txt = os.path.join(folder, f)
                break
        if not chat_txt:
            print("Не найден файл _chat.txt или chat.txt")
            sys.exit(1)
        print(f"Найден файл чата: {chat_txt}")

        generate_html(chat_txt, folder, output, your_name)
        print("Готово!")
    except Exception as e:
        print("Ошибка:")
        traceback.print_exc()
        sys.exit(1)