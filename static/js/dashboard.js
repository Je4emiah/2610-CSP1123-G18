// Global State Management - Set immediately using the system clock
const initialDate = new Date();
let currentYear = initialDate.getFullYear();
let currentMonth = initialDate.getMonth() + 1; // JS months are 0-11, so we add 1
let myChart = null; 

// Initialize UI elements to match the current month/year on start
function initFilterSelectors() {
    const yearSelect = document.getElementById('yearSelect');
    
    // Safely inject a new option into the Year dropdown if the current year isn't listed yet
    const yearExists = Array.from(yearSelect.options).some(option => parseInt(option.value) === currentYear);
    if (!yearExists) {
        const newYearOption = document.createElement('option');
        newYearOption.value = currentYear;
        newYearOption.innerText = currentYear;
        yearSelect.appendChild(newYearOption);
    }

    // Force the dropdown menus to visually match our current global state variables
    document.getElementById('monthSelect').value = String(currentMonth).padStart(2, '0');
    yearSelect.value = currentYear;
}

// Triggered when a dropdown filter is manually changed by the user
function handleDropdownChange() {
    currentMonth = parseInt(document.getElementById('monthSelect').value);
    currentYear = parseInt(document.getElementById('yearSelect').value);
    updateDashboard();
}

// Logic for stepping backward (-1) or forward (+1) through months
function adjustMonth(step) {
    currentMonth += step;
    
    // Overflow roll-overs (Handles switching years seamlessly)
    if (currentMonth > 12) {
        currentMonth = 1;
        currentYear += 1;
    } else if (currentMonth < 1) {
        currentMonth = 12;
        currentYear -= 1;
    }

    // Sync state values back to the DOM dropdowns
    document.getElementById('monthSelect').value = String(currentMonth).padStart(2, '0');
    document.getElementById('yearSelect').value = currentYear;

    updateDashboard();
}

// Master function to fetch data and render Chart.js
async function updateDashboard() {
    const canvas = document.getElementById('moodChart');
    const counterElement = document.getElementById('dataCounter');
    const labelElement = document.getElementById('rangeLabel');
    const username = canvas.dataset.username;
    const ctx = canvas.getContext('2d');

    if (counterElement) counterElement.innerText = "Refreshing...";

    // Format current month for display text
    const monthNames = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
    if (labelElement) {
        labelElement.innerText = `${monthNames[currentMonth - 1]} ${currentYear}`;
    }

    try {
        const paddedMonth = String(currentMonth).padStart(2, '0');
        const response = await fetch(`/api/mood_data/${username}?year=${currentYear}&month=${paddedMonth}`);
        const data = await response.json();

        // Update Counter display metadata
        if (counterElement) {
            const count = data.data.length;
            counterElement.innerText = `${count} entries found`;
            counterElement.style.color = count === 0 ? "#ef4444" : "#94a3b8";
        }

        if (myChart) { myChart.destroy(); }

        const gradient = ctx.createLinearGradient(0, 0, 0, 400);
        gradient.addColorStop(0, 'rgba(0, 212, 255, 0.4)');
        gradient.addColorStop(1, 'rgba(0, 212, 255, 0)');

        myChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: data.labels.map(label => {
                    // Pulls only the date string portion for a cleaner monthly axis
                    return label.split(' ')[0] || label; 
                }),
                datasets: [{
                    label: 'Mood Level',
                    data: data.data,
                    borderColor: '#00D4FF',
                    backgroundColor: gradient,
                    borderWidth: 4,
                    pointBackgroundColor: '#ffffff',
                    pointBorderColor: '#00D4FF',
                    pointRadius: 5,
                    tension: 0.4,
                    fill: true
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    y: { min: 0, max: 6, ticks: { stepSize: 1, color: '#94a3b8' } },
                    x: { ticks: { color: '#94a3b8' } }
                }
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