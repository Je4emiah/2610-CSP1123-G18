// Global State Management - Set immediately using the system clock
const initialDate = new Date();
const state = {
    year: initialDate.getFullYear(),
    month: initialDate.getMonth() + 1, // JS months are 0-11, so we add 1
    metricType: 'steps',
    privacyMode: false
};
let myChart = null; 

// Initialize UI elements to match the current month/year on start
function initFilterSelectors() {
    const yearSelect = document.getElementById('yearSelect');
    if (!yearSelect) return;
    
    // Safely inject a new option into the Year dropdown if the current year isn't listed yet
    const yearExists = Array.from(yearSelect.options).some(option => parseInt(option.value) === state.year);
    if (!yearExists) {
        const newYearOption = document.createElement('option');
        newYearOption.value = state.year;
        newYearOption.innerText = state.year;
        yearSelect.appendChild(newYearOption);
    }

    // Force the dropdown menus to visually match our current global state variables
    const monthSelect = document.getElementById('monthSelect');
    if (monthSelect) monthSelect.value = String(state.month).padStart(2, '0');
    yearSelect.value = state.year;
    
    const metricSelect = document.getElementById('metricSelect');
    if (metricSelect) metricSelect.value = state.metricType;
    
    const privacyToggle = document.getElementById('privacyToggle');
    if (privacyToggle) privacyToggle.checked = state.privacyMode;
}

// Triggered when a dropdown filter is manually changed by the user
function handleDropdownChange() {
    const monthSelect = document.getElementById('monthSelect');
    const yearSelect = document.getElementById('yearSelect');
    
    if (monthSelect) state.month = parseInt(monthSelect.value);
    if (yearSelect) state.year = parseInt(yearSelect.value);
    
    const metricSelect = document.getElementById('metricSelect');
    if (metricSelect) state.metricType = metricSelect.value;
    
    updateDashboard();
}

// Triggered when privacy toggle is flipped
function handlePrivacyToggleChange() {
    const privacyToggle = document.getElementById('privacyToggle');
    if (privacyToggle) state.privacyMode = privacyToggle.checked;
    updateDashboard();
}

// Logic for stepping backward (-1) or forward (+1) through months
function adjustMonth(step) {
    state.month += step;
    
    // Overflow roll-overs (Handles switching years seamlessly)
    if (state.month > 12) {
        state.month = 1;
        state.year += 1;
    } else if (state.month < 1) {
        state.month = 12;
        state.year -= 1;
    }

    // Sync state values back to the DOM dropdowns
    const monthSelect = document.getElementById('monthSelect');
    const yearSelect = document.getElementById('yearSelect');
    
    if (monthSelect) monthSelect.value = String(state.month).padStart(2, '0');
    if (yearSelect) yearSelect.value = state.year;

    updateDashboard();
}

// Master function to fetch data and render Chart.js
async function updateDashboard() {
    const canvas = document.getElementById('moodChart');
    if (!canvas) return;
    
    const counterElement = document.getElementById('dataCounter');
    const labelElement = document.getElementById('rangeLabel');
    const username = canvas.dataset.username;
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
            marker.className = "badge bg-danger";
        }
        if (hint) hint.innerText = "Locked user tracking. Hooked entirely into anonymous community aggregates.";
    } else {
        if (loggerPanel) loggerPanel.classList.remove('disabled-form-section');
        moodFormInputs.forEach(input => input.disabled = false);
        if (marker) {
            marker.innerText = "Local Tracker";
            marker.className = "badge bg-secondary";
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
        if (counterElement) {
            const chartDataArray = data.mood_data || data.data || [];
            const count = chartDataArray.filter(val => val !== null).length;
            counterElement.innerText = `${count} entries found`;
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
            data: data.mood_data || data.data || [],
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
                color = '#10b981'; 
            } else if (state.metricType === 'active_hours') {
                telemetryLabel = 'Active Hours';
                color = '#f59e0b'; 
            } else if (state.metricType === 'sleep_cycles') {
                telemetryLabel = 'Sleep Cycles';
                color = '#8b5cf6'; 
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

        if (state.metricType !== 'none' && data.telemetry_data) {
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
});
