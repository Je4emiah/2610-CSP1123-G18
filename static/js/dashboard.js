let myChart = null;
let navChart = null;
let allLabels = [], allMoodData = [], allTelemetryData = [];
let leftIndex = 0, rightIndex = 0;

async function updateDashboard() {
    const canvas = document.getElementById('moodChart');
    if (!canvas) return;
    
    const counterElement = document.getElementById('dataCounter');
    const labelElement = document.getElementById('rangeLabel');
    const username = canvas.dataset.username;
    const milestoneMarkers = JSON.parse(canvas.dataset.milestones || '[]');
    const ctx = canvas.getContext('2d');

    if (counterElement) counterElement.innerText = "Refreshing...";

    // Format current month for display text
    const monthNames = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
    if (labelElement) {
        labelElement.innerText = `${monthNames[state.month - 1]} ${state.year}`;
    }

    // Update logger panel elements and privacy mode markers based on current privacy state
    const loggerPanel = document.querySelector('.logger-module');
    const moodFormInputs = document.querySelectorAll('#moodForm input, #moodForm textarea, #moodForm button');
    const marker = document.getElementById('privacyStatusMarker');
    const hint = document.getElementById('privacyHintText');
    
    if (state.privacyMode) {
        if (loggerPanel) loggerPanel.classList.add('disabled-form-section');
        moodFormInputs.forEach(input => input.disabled = true);
        if (marker) {
            marker.innerText = "Global Mode";
            marker.className = "badge privacy-status-marker privacy-status-marker--global bg-danger";
        }
        if (hint) hint.innerText = "Locked user tracking. Hooked entirely into anonymous community aggregates.";
    } else {
        if (loggerPanel) loggerPanel.classList.remove('disabled-form-section');
        moodFormInputs.forEach(input => input.disabled = false);
        if (marker) {
            marker.innerText = "Local Tracker";
            marker.className = "badge privacy-status-marker privacy-status-marker--local bg-secondary";
        }
        if (hint) hint.innerText = "Showing personalized mood & telemetry metrics.";
    }

    try {
        const paddedMonth = String(state.month).padStart(2, '0');
        // Route network query based on privacy setting
        const queryUrl = state.privacyMode
            ? `/api/telemetry_data/global?year=${state.year}&month=${paddedMonth}&metric_type=${state.metricType}`
            : `/api/telemetry_data/${username}?year=${state.year}&month=${paddedMonth}&metric_type=${state.metricType}`;
            
        const response = await fetch(queryUrl);
        const data = await response.json();

        // Update Counter display metadata based on mood data entries
        if (counterElement && data.mood_data) {
            const count = data.mood_data.filter(val => val !== null).length;
            counterElement.innerText = `${count} logs found`;
            counterElement.style.color = count === 0 ? "#ef4444" : "#94a3b8";
        }

        // Render calendar with mood colors
        renderCalendar(data);

        // Cleanup checking if an existing canvas chart component is active
        if (myChart) { 
            myChart.destroy(); 
            myChart = null;
        }

        // Store full data for navigator
        allLabels = data.labels ? data.labels.map(l => l.split(' ')[0] || l) : [];
        allMoodData = data.mood_data || [];
        allTelemetryData = data.telemetry_data || [];
        leftIndex = 0;
        rightIndex = Math.max(0, allLabels.length - 1);

        const milestoneDates = new Set(milestoneMarkers.map(m => m.date));

        // Prepare Chart datasets
        const gradient = ctx.createLinearGradient(0, 0, 0, 400);
        gradient.addColorStop(0, 'rgba(0, 212, 255, 0.4)');
        gradient.addColorStop(1, 'rgba(0, 212, 255, 0)');

        const datasets = [{
            label: 'Mood Level',
            data: allMoodData.slice(),
            borderColor: '#00D4FF',
            backgroundColor: gradient,
            borderWidth: 4,
            pointBackgroundColor: '#ffffff',
            pointBorderColor: '#00D4FF',
            pointRadius: 5,
            tension: 0.4,
            fill: true,
            spanGaps: true,
            yAxisID: 'y'
        }];

        // Multi-axis logic mapping a secondary linear trend line
        if (state.metricType !== 'none' && allTelemetryData.length) {
            let telemetryLabel = 'Metric';
            let color = '#2563eb';
            if (state.metricType === 'steps') { telemetryLabel = 'Step Count'; color = '#10b981'; }
            else if (state.metricType === 'active_hours') { telemetryLabel = 'Active Hours'; color = '#f59e0b'; }
            else if (state.metricType === 'sleep_cycles') { telemetryLabel = 'Sleep Cycles'; color = '#8b5cf6'; }

            datasets.push({
                label: telemetryLabel,
                data: allTelemetryData.slice(),
                borderColor: color,
                backgroundColor: 'transparent',
                borderWidth: 3,
                borderDash: [5, 5],
                pointBackgroundColor: '#ffffff',
                pointBorderColor: color,
                pointRadius: 4,
                tension: 0.4,
                fill: false,
                spanGaps: true,
                yAxisID: 'y1'
            });
        }

        // Configure Chart.js multi-axis scales
        const scales = {
            y: {
                min: 0,
                max: 6,
                ticks: { stepSize: 1, color: '#94a3b8' },
                title: { display: true, text: 'Mood Score (1-5)', color: '#94a3b8' }
            },
            x: { 
                ticks: { color: '#94a3b8' } 
            }
        };

        if (state.metricType !== 'none') {
            let y1Title = 'Value';
            if (state.metricType === 'steps') y1Title = 'Steps';
            if (state.metricType === 'active_hours') y1Title = 'Active Hours';
            if (state.metricType === 'sleep_cycles') y1Title = 'Hours / Cycles';

            scales.y1 = {
                position: 'right',
                min: 0,
                grid: { drawOnChartArea: false },
                ticks: { color: '#94a3b8' },
                title: { display: true, text: y1Title, color: '#94a3b8' }
            };
        }

        const pointRadius = allLabels.map(l => milestoneDates.has(l) ? 9 : 5);
        const pointHoverRadius = allLabels.map(l => milestoneDates.has(l) ? 11 : 7);
        const pointBg = allLabels.map(l => milestoneDates.has(l) ? '#f59e0b' : '#ffffff');
        const pointBc = allLabels.map(l => milestoneDates.has(l) ? '#f59e0b' : '#00D4FF');
        const pointStyle = allLabels.map(l => milestoneDates.has(l) ? 'star' : 'circle');

        datasets[0].pointRadius = pointRadius;
        datasets[0].pointHoverRadius = pointHoverRadius;
        datasets[0].pointBackgroundColor = pointBg;
        datasets[0].pointBorderColor = pointBc;
        datasets[0].pointStyle = pointStyle;

        myChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: allLabels.slice(),
                datasets: datasets
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: true, labels: { color: '#94a3b8' } } },
                scales: scales
            }
        });

        // --- Navigator (mini range slider) ---
        initNavigator(allLabels, allMoodData);

    } catch (error) {
        console.error('Chart failed to load:', error);
        if (counterElement) counterElement.innerText = "Error loading data";
    }
}

function initNavigator(labels, moodData) {
    const navigatorEl = document.getElementById('chartNavigator');
    const navCanvas = document.getElementById('navigatorCanvas');
    const handleL = document.getElementById('navHandleLeft');
    const handleR = document.getElementById('navHandleRight');
    const selection = document.getElementById('navSelection');
    if (!navigatorEl || !navCanvas) return;

    if (navChart) { navChart.destroy(); navChart = null; }

    // Create mini line chart
    const navCtx = navCanvas.getContext('2d');
    navChart = new Chart(navCtx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                data: moodData,
                borderColor: 'rgba(0, 212, 255, 0.5)',
                backgroundColor: 'rgba(0, 212, 255, 0.05)',
                borderWidth: 1.5,
                pointRadius: 0,
                tension: 0.3,
                fill: true
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false }, tooltip: { enabled: false } },
            scales: {
                x: { display: false },
                y: { display: false, min: 0, max: 6 }
            },
            events: []
        }
    });

    leftIndex = 0;
    rightIndex = Math.max(0, labels.length - 1);
    updateNavSelection();
    setupHandleDrag(handleL, true, navigatorEl);
    setupHandleDrag(handleR, false, navigatorEl);
}

function setupHandleDrag(handle, isLeft, navEl) {
    handle.addEventListener('mousedown', startDrag);
    handle.addEventListener('touchstart', startDrag, { passive: false });

    function startDrag(e) {
        e.preventDefault();
        const startClientX = e.touches ? e.touches[0].clientX : e.clientX;
        const startLeft = parseFloat(handle.style.left) || 0;
        const navWidth = navEl.offsetWidth;
        const handleW = 10;

        function onMove(e) {
            const clientX = e.touches ? e.touches[0].clientX : e.clientX;
            const dx = clientX - startClientX;
            let newLeft = startLeft + dx;
            newLeft = Math.max(0, Math.min(navWidth - handleW, newLeft));
            handle.style.left = newLeft + 'px';

            // Convert pixel to index
            const ratio = newLeft / (navWidth - handleW);
            const idx = Math.round(ratio * (allLabels.length - 1));

            if (isLeft) {
                leftIndex = Math.min(idx, rightIndex - 1);
            } else {
                rightIndex = Math.max(idx, leftIndex + 1);
            }
            updateNavSelection();
            updateMainChartRange();
        }

        function onEnd() {
            document.removeEventListener('mousemove', onMove);
            document.removeEventListener('mouseup', onEnd);
            document.removeEventListener('touchmove', onMove);
            document.removeEventListener('touchend', onEnd);
        }

        document.addEventListener('mousemove', onMove);
        document.addEventListener('mouseup', onEnd);
        document.addEventListener('touchmove', onMove, { passive: false });
        document.addEventListener('touchend', onEnd);
    }
}

function updateNavSelection() {
    const navEl = document.getElementById('chartNavigator');
    const handleL = document.getElementById('navHandleLeft');
    const handleR = document.getElementById('navHandleRight');
    const selection = document.getElementById('navSelection');
    if (!navEl) return;

    const navWidth = navEl.offsetWidth;
    const handleW = 10;
    const usable = navWidth - handleW;
    const maxIdx = Math.max(allLabels.length - 1, 1);

    const leftPx = (leftIndex / maxIdx) * usable;
    const rightPx = (rightIndex / maxIdx) * usable;

    handleL.style.left = leftPx + 'px';
    handleR.style.left = rightPx + 'px';
    selection.style.left = leftPx + 'px';
    selection.style.width = Math.max(0, rightPx - leftPx + handleW) + 'px';
}

function updateMainChartRange() {
    if (!myChart) return;
    const slicedLabels = allLabels.slice(leftIndex, rightIndex + 1);
    const slicedMood = allMoodData.slice(leftIndex, rightIndex + 1);

    myChart.data.labels = slicedLabels;
    myChart.data.datasets[0].data = slicedMood;

    if (myChart.data.datasets[1] && allTelemetryData.length) {
        myChart.data.datasets[1].data = allTelemetryData.slice(leftIndex, rightIndex + 1);
    }

    // Rebuild milestone point styles for sliced labels
    const milestoneDates = new Set(JSON.parse(document.getElementById('moodChart').dataset.milestones || '[]').map(m => m.date));
    myChart.data.datasets[0].pointRadius = slicedLabels.map(l => milestoneDates.has(l) ? 9 : 5);
    myChart.data.datasets[0].pointHoverRadius = slicedLabels.map(l => milestoneDates.has(l) ? 11 : 7);
    myChart.data.datasets[0].pointBackgroundColor = slicedLabels.map(l => milestoneDates.has(l) ? '#f59e0b' : '#ffffff');
    myChart.data.datasets[0].pointBorderColor = slicedLabels.map(l => milestoneDates.has(l) ? '#f59e0b' : '#00D4FF');
    myChart.data.datasets[0].pointStyle = slicedLabels.map(l => milestoneDates.has(l) ? 'star' : 'circle');

    myChart.update('none');
}

function resetZoom() {
    leftIndex = 0;
    rightIndex = Math.max(0, allLabels.length - 1);
    updateNavSelection();
    updateMainChartRange();
}

// Auto-Initialize strictly in the correct order on page load
document.addEventListener('DOMContentLoaded', () => {
    initFilterSelectors(); // 1. Align the UI dropdown elements first
    updateDashboard();     // 2. Fetch the current calendar date data immediately
    initInsightSidebar();   // 3. Seed the sidebar preview widgets
    bindImportExport();     // 4. Wire up Export / Import buttons
    initMoodSlider();       // 5. Wire up the mood slider
    initNoteToggle();       // 6. Wire up the Add Note toggle
    initViewToggle();       // 7. Wire up Calendar/Chart toggle
});

function initNoteToggle() {
    const btn = document.getElementById('toggleNoteBtn');
    const collapse = document.getElementById('noteCollapse');
    if (!btn || !collapse) return;
    btn.addEventListener('click', () => {
        const isOpen = collapse.classList.toggle('open');
        btn.querySelector('span').textContent = isOpen ? '- Remove Note' : '+ Add Note';
    });
}

function initMoodSlider() {
    const slider = document.getElementById('moodScore');
    const label = document.getElementById('moodValueLabel');
    if (!slider || !label) return;
    const labels = {1:'Terrible', 2:'Bad', 3:'Neutral', 4:'Good', 5:'Great'};
    const colors = {1:'#dc3545', 2:'#e8672c', 3:'#ffc107', 4:'#28a745', 5:'#1a9e3f'};
    const update = () => {
        label.textContent = labels[slider.value] || 'Neutral';
        label.style.color = colors[slider.value] || '#94a3b8';
    };
    slider.addEventListener('input', update);
    update();
}
// Global State Management
const state = {
    year: new Date().getFullYear(),
    month: new Date().getMonth() + 1,
    metricType: 'none',
    privacyMode: false,
    viewMode: 'calendar'
};

function initFilterSelectors() {
    const yearSelect = document.getElementById('yearSelect');
    const monthSelect = document.getElementById('monthSelect');
    const metricSelect = document.getElementById('metricSelect');
    const privacyToggle = document.getElementById('privacyToggle');

    // Sync UI from State
    if(monthSelect) monthSelect.value = String(state.month).padStart(2, '0');
    if(yearSelect) yearSelect.value = state.year;
    if(metricSelect) metricSelect.value = state.metricType;
    if(privacyToggle) privacyToggle.checked = state.privacyMode;
}

function adjustMonth(step) {
    state.month += step;
    if (state.month > 12) { state.month = 1; state.year += 1; }
    else if (state.month < 1) { state.month = 12; state.year -= 1; }

    document.getElementById('monthSelect').value = String(state.month).padStart(2, '0');
    document.getElementById('yearSelect').value = state.year;

    updateDashboard();
}

function handleDropdownChange() {
    state.month = parseInt(document.getElementById('monthSelect').value);
    state.year = parseInt(document.getElementById('yearSelect').value);
    state.metricType = document.getElementById('metricSelect').value;
    updateDashboard();
}

function handlePrivacyToggleChange() {
    state.privacyMode = document.getElementById('privacyToggle').checked;
    updateDashboard();
}

function renderCalendar(data) {
    const container = document.getElementById('calendarView');
    if (!container) return;

    const year = state.year;
    const month = state.month;
    const daysInMonth = new Date(year, month, 0).getDate();
    const firstDayOfWeek = new Date(year, month - 1, 1).getDay();

    const moodByDay = {};
    data.labels.forEach((label, i) => {
        if (data.mood_data[i] !== null) {
            const dayNum = parseInt(label.split('-')[2]);
            moodByDay[dayNum] = data.mood_data[i];
        }
    });

    const dayNames = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
    const today = new Date();
    const todayStr = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`;

    let html = '<div class="cal-header"><div class="cal-day-names">';
    dayNames.forEach(name => { html += `<span>${name}</span>`; });
    html += '</div></div><div class="cal-grid">';

    for (let i = 0; i < firstDayOfWeek; i++) {
        html += '<div class="cal-cell cal-empty"></div>';
    }

    for (let day = 1; day <= daysInMonth; day++) {
        const dateStr = `${year}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
        const score = moodByDay[day];
        const isToday = dateStr === todayStr;

        let moodClass = '';
        if (score !== undefined) {
            if (score >= 4) moodClass = 'cal-mood-good';
            else if (score >= 3) moodClass = 'cal-mood-neutral';
            else moodClass = 'cal-mood-bad';
        }

        let classes = 'cal-cell';
        if (moodClass) classes += ` ${moodClass}`;
        if (isToday) classes += ' cal-today';

        const scoreText = score !== undefined ? `Mood: ${score.toFixed(1)}` : 'No entry';

        html += `<div class="${classes}" title="${scoreText}"><span class="cal-day-num">${day}</span></div>`;
    }

    html += '</div>';
    container.innerHTML = html;
}

function initViewToggle() {
    const calendarBtn = document.getElementById('viewCalendarBtn');
    const chartBtn = document.getElementById('viewChartBtn');
    const calendarView = document.getElementById('calendarView');
    const chartCanvas = document.getElementById('moodChart');
    const navigator = document.getElementById('chartNavigator');
    if (!calendarBtn || !chartBtn) return;

    calendarBtn.addEventListener('click', () => {
        state.viewMode = 'calendar';
        calendarBtn.classList.add('active');
        chartBtn.classList.remove('active');
        if (calendarView) calendarView.classList.remove('d-none');
        if (chartCanvas) chartCanvas.classList.add('d-none');
        if (navigator) navigator.classList.add('d-none');
    });

    chartBtn.addEventListener('click', () => {
        state.viewMode = 'chart';
        chartBtn.classList.add('active');
        calendarBtn.classList.remove('active');
        if (calendarView) calendarView.classList.add('d-none');
        if (chartCanvas) chartCanvas.classList.remove('d-none');
        if (navigator && allLabels.length > 1) navigator.classList.remove('d-none');
    });

    // Default to calendar
    calendarBtn.click();
}

function getMoodColor(score) {
    if (score === undefined || score === null) return 'transparent';
    if (score >= 4) return '#28a745';
    if (score >= 3) return '#ffc107';
    return '#dc3545';
}

function getWeeklyInsightData() {
    const insightDataElement = document.getElementById('weeklyInsightData');
    if (!insightDataElement) return null;

    try {
        return JSON.parse(insightDataElement.textContent || '{}');
    } catch (error) {
        console.error('Failed to parse weekly insight data:', error);
        return null;
    }
}

function createChatBubble(role, label, messageText, emoji) {
    const message = document.createElement('div');
    message.className = `chat-message chat-message--${role}`;

    const avatar = document.createElement('div');
    avatar.className = 'chat-message-avatar';
    avatar.textContent = emoji || (role === 'assistant' ? 'G' : 'U');

    const bubble = document.createElement('div');
    bubble.className = 'chat-message-bubble';

    const title = document.createElement('strong');
    title.textContent = label;

    const body = document.createElement('p');
    body.textContent = messageText;

    bubble.append(title, body);
    message.append(avatar, bubble);
    return message;
}

function renderInsightPanel(insight) {
    const emojiNode = document.getElementById('aiEmoji');
    const textNode = document.getElementById('insightText');
    const cacheDateNode = document.getElementById('insightCacheDate');
    const panel = document.getElementById('section-insight');

    if (emojiNode) emojiNode.textContent = insight.emoji || '';
    if (textNode) textNode.textContent = insight.review || '';
    if (cacheDateNode && insight.cached_date) {
        cacheDateNode.textContent = `Refreshed ${insight.cached_date}`;
    }
    if (panel && insight.cached_date) {
        panel.dataset.cachedDate = insight.cached_date;
    }
}

function seedChatPreview(insight, forceReset = false) {
    const thread = document.getElementById('chatPreviewThread');
    if (!thread) return;

    if (forceReset) {
        thread.innerHTML = '';
        thread.dataset.initialized = '';
    }

    if (thread.dataset.initialized === 'true') return;

    thread.appendChild(createChatBubble('assistant', 'Gemini', 'Try asking about your mood trends, badge progress, or habits. Click a suggestion above to get started.', 'G'));
    thread.dataset.initialized = 'true';
    thread.scrollTop = thread.scrollHeight;
}

function appendPreviewMessage(role, label, messageText, emoji) {
    const thread = document.getElementById('chatPreviewThread');
    if (!thread) return;

    thread.appendChild(createChatBubble(role, label, messageText, emoji));
    thread.scrollTop = thread.scrollHeight;
}

// --- Insight Refresh with 5-min cooldown ---
async function handleRefreshInsight() {
    const btn = document.getElementById('refreshInsightBtn');
    const cooldownEl = document.getElementById('insightCooldown');
    if (!btn) return;

    btn.disabled = true;
    btn.textContent = 'Refreshing...';

    try {
        const response = await fetch('/api/daily_insight?force=true');
        const data = await response.json();

        if (response.status === 429) {
            const remaining = data.cooldown_remaining || 300;
            btn.textContent = 'Refresh';
            btn.disabled = true;
            cooldownEl.classList.remove('d-none');
            startCountdown(remaining, btn, cooldownEl);
            return;
        }

        if (data.error) {
            console.error('Insight refresh error:', data.error);
            btn.textContent = 'Refresh';
            btn.disabled = false;
            return;
        }

        renderInsightPanel(data);
        seedChatPreview(data, true);
        btn.textContent = 'Refresh';
        btn.disabled = false;
    } catch (error) {
        console.error('Insight refresh failed:', error);
        btn.textContent = 'Refresh';
        btn.disabled = false;
    }
}

function startCountdown(seconds, btn, el) {
    let remaining = seconds;
    const origLabel = btn ? btn.textContent : '';
    el.textContent = `Cooldown ${remaining}s`;
    el.classList.remove('d-none');
    if (btn) btn.textContent = `Wait ${remaining}s`;

    const interval = setInterval(() => {
        remaining--;
        if (remaining <= 0) {
            clearInterval(interval);
            el.classList.add('d-none');
            if (btn) {
                btn.disabled = false;
                btn.textContent = origLabel;
            }
        } else {
            el.textContent = `Cooldown ${remaining}s`;
            if (btn) btn.textContent = `Wait ${remaining}s`;
        }
    }, 1000);
}

// --- Real Gemini Chat with 2-min cooldown ---
async function sendChatMessage(message) {
    const thread = document.getElementById('chatPreviewThread');
    const sendBtn = document.getElementById('chatSendBtn');
    const cooldownEl = document.getElementById('chatCooldown');
    if (!thread) return;

    const typingBubble = createChatBubble('assistant', 'Gemini', 'Thinking...', 'G');
    thread.appendChild(typingBubble);
    thread.scrollTop = thread.scrollHeight;

    sendBtn.disabled = true;

    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message })
        });
        const data = await response.json();

        if (typingBubble.parentNode) typingBubble.remove();

        if (response.status === 429) {
            const remaining = data.cooldown_remaining || 120;
            startCountdown(remaining, sendBtn, cooldownEl);
            return;
        }

        if (data.error) {
            appendPreviewMessage('assistant', 'Gemini', data.error, 'G');
            sendBtn.disabled = false;
            return;
        }

        appendPreviewMessage('assistant', 'Gemini', data.reply, 'G');
        sendBtn.disabled = false;
    } catch (error) {
        if (typingBubble.parentNode) typingBubble.remove();
        appendPreviewMessage('assistant', 'Gemini', 'Connection error. Please try again.', 'G');
        sendBtn.disabled = false;
    }
}

function bindChatInteractions(insight) {
    const form = document.getElementById('chatPreviewForm');
    const input = document.getElementById('chatPreviewInput');
    const suggestionButtons = document.querySelectorAll('.chat-suggestion-chip');

    if (!form || !input) return;
    if (form.dataset.bound === 'true') return;
    form.dataset.bound = 'true';

    form.addEventListener('submit', event => {
        event.preventDefault();
        const messageText = input.value.trim();
        if (!messageText) return;
        input.value = '';
        sendChatMessage(messageText);
    });

    suggestionButtons.forEach(button => {
        button.addEventListener('click', () => {
            input.value = button.dataset.previewPrompt || button.textContent || '';
            input.focus();
        });
    });
}

async function refreshDailyInsight() {
    try {
        const response = await fetch('/api/daily_insight');
        if (!response.ok) return;

        const insight = await response.json();
        if (!insight || insight.error) return;

        renderInsightPanel(insight);
        seedChatPreview(insight, true);
    } catch (error) {
        console.error('Daily insight refresh failed:', error);
    }
}

function startDailyInsightTimer() {
    const panel = document.getElementById('section-insight');
    if (!panel) return;

    const checkInsightDate = () => {
        const cachedDate = panel.dataset.cachedDate;
        const now = new Date();
        const today = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
        if (cachedDate && cachedDate === today) return;
        refreshDailyInsight();
    };

    checkInsightDate();
    window.setInterval(checkInsightDate, 60000);
}

function bindImportExport() {
    const exportBtn = document.getElementById('exportBtn');
    const importBtn = document.getElementById('importBtn');
    const importInput = document.getElementById('importFileInput');
    if (!exportBtn || !importBtn || !importInput) return;

    exportBtn.addEventListener('click', async () => {
        try {
            const res = await fetch('/api/export');
            const data = await res.json();
            if (data.error) { alert(data.error); return; }
            const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `mindmetric-export-${new Date().toISOString().split('T')[0]}.json`;
            a.click();
            URL.revokeObjectURL(url);
        } catch (e) {
            alert('Export failed.');
        }
    });

    importBtn.addEventListener('click', () => importInput.click());

    importInput.addEventListener('change', async (e) => {
        const file = e.target.files[0];
        if (!file) return;
        try {
            const text = await file.text();
            const data = JSON.parse(text);
            const res = await fetch('/api/import', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            const result = await res.json();
            if (result.error) {
                alert(result.error);
            } else {
                alert(`Imported: ${result.imported.mood_logs} mood logs, ${result.imported.telemetry_logs} telemetry logs.`);
            }
        } catch (e) {
            alert('Import failed. Check the file format.');
        }
        importInput.value = '';
        updateDashboard();
    });
}

function initInsightSidebar() {
    const insight = getWeeklyInsightData();
    if (!insight) return;

    renderInsightPanel(insight);
    seedChatPreview(insight);
    bindChatInteractions(insight);
    startDailyInsightTimer();
}