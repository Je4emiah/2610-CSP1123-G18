let myChart = null;

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
    const moodFormInputs = document.querySelectorAll('#moodForm select, #moodForm textarea, #moodForm button');
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

        // Cleanup checking if an existing canvas chart component is active
        if (myChart) { 
            myChart.destroy(); 
            myChart = null;
        }

        const gradient = ctx.createLinearGradient(0, 0, 0, 400);
        gradient.addColorStop(0, 'rgba(0, 212, 255, 0.4)');
        gradient.addColorStop(1, 'rgba(0, 212, 255, 0)');

        // Prepare Chart datasets
        const datasets = [{
            label: 'Mood Level',
            data: data.mood_data || [],
            borderColor: '#00D4FF',
            backgroundColor: gradient,
            borderWidth: 4,
            pointBackgroundColor: '#ffffff',
            pointBorderColor: '#00D4FF',
            pointRadius: 5,
            tension: 0.4,
            fill: true,
            yAxisID: 'y'
        }];

        // Multi-axis logic mapping a secondary linear trend line
        if (state.metricType !== 'none' && data.telemetry_data) {
            let telemetryLabel = 'Metric';
            let color = '#2563eb';
            if (state.metricType === 'steps') {
                telemetryLabel = 'Step Count';
                color = '#10b981'; // Sleek Emerald
            } else if (state.metricType === 'active_hours') {
                telemetryLabel = 'Active Hours';
                color = '#f59e0b'; // Sleek Amber
            } else if (state.metricType === 'sleep_cycles') {
                telemetryLabel = 'Sleep Cycles';
                color = '#8b5cf6'; // Sleek Purple
            }

            datasets.push({
                label: telemetryLabel,
                data: data.telemetry_data,
                borderColor: color,
                backgroundColor: 'transparent',
                borderWidth: 3,
                borderDash: [5, 5],
                pointBackgroundColor: '#ffffff',
                pointBorderColor: color,
                pointRadius: 4,
                tension: 0.4,
                fill: false,
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

        const labels = data.labels ? data.labels.map(label => label.split(' ')[0] || label) : [];
        const milestoneDates = new Set(milestoneMarkers.map(marker => marker.date));
        const pointRadius = labels.map(label => milestoneDates.has(label) ? 9 : 5);
        const pointHoverRadius = labels.map(label => milestoneDates.has(label) ? 11 : 7);
        const pointBackgroundColor = labels.map(label => milestoneDates.has(label) ? '#f59e0b' : '#ffffff');
        const pointBorderColor = labels.map(label => milestoneDates.has(label) ? '#f59e0b' : '#00D4FF');
        const pointStyle = labels.map(label => milestoneDates.has(label) ? 'star' : 'circle');

        datasets[0].pointRadius = pointRadius;
        datasets[0].pointHoverRadius = pointHoverRadius;
        datasets[0].pointBackgroundColor = pointBackgroundColor;
        datasets[0].pointBorderColor = pointBorderColor;
        datasets[0].pointStyle = pointStyle;

        myChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: datasets
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: true, labels: { color: '#94a3b8' } } },
                scales: scales
            }
        });
    } catch (error) {
        console.error('Chart failed to load:', error);
        if (counterElement) counterElement.innerText = "Error loading data";
    }
}

// Auto-Initialize strictly in the correct order on page load
document.addEventListener('DOMContentLoaded', () => {
    initFilterSelectors(); // 1. Align the UI dropdown elements first
    updateDashboard();     // 2. Fetch the current calendar date data immediately
    initInsightSidebar();   // 3. Seed the sidebar preview widgets
    bindImportExport();     // 4. Wire up Export / Import buttons
});
// Global State Management
const state = {
    year: new Date().getFullYear(),
    month: new Date().getMonth() + 1,
    metricType: 'none',
    privacyMode: false
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
    avatar.textContent = emoji || (role === 'assistant' ? '🤖' : '🙂');

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

    if (emojiNode) emojiNode.textContent = insight.emoji || '🤔';
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

    thread.appendChild(createChatBubble('assistant', 'Gemini', '💡 Try asking about your mood trends, badge progress, or habits! Click a suggestion above to get started.', '💡'));
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
            btn.textContent = '↻ Refresh';
            btn.disabled = true;
            cooldownEl.classList.remove('d-none');
            startCountdown(remaining, btn, cooldownEl);
            return;
        }

        if (data.error) {
            console.error('Insight refresh error:', data.error);
            btn.textContent = '↻ Refresh';
            btn.disabled = false;
            return;
        }

        renderInsightPanel(data);
        seedChatPreview(data, true);
        btn.textContent = '↻ Refresh';
        btn.disabled = false;
    } catch (error) {
        console.error('Insight refresh failed:', error);
        btn.textContent = '↻ Refresh';
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

    const typingBubble = createChatBubble('assistant', 'Gemini', 'Thinking...', '🤖');
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
            appendPreviewMessage('assistant', 'Gemini', data.error, '⚠️');
            sendBtn.disabled = false;
            return;
        }

        appendPreviewMessage('assistant', 'Gemini', data.reply, '🤖');
        sendBtn.disabled = false;
    } catch (error) {
        if (typingBubble.parentNode) typingBubble.remove();
        appendPreviewMessage('assistant', 'Gemini', 'Connection error. Please try again.', '⚠️');
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