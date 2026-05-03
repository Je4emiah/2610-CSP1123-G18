let currentOffset = 0;
let currentRange = 'day';
let myChart = null; // Store the chart instance globally

// 1. Logic for moving between "pages" (Previous/Next)
function movePage(step) {
    currentOffset += step;
    if (currentOffset < 0) currentOffset = 0;
    document.getElementById('nextBtn').disabled = (currentOffset === 0);
    updateDashboard();
}

// 2. Logic for changing the time scale (Day/Week/Month/All)
function changeRange(range) {
    currentRange = range;
    currentOffset = 0; 
    
    const pagingControls = document.getElementById('pagingControls');
    if (range === 'all') {
        pagingControls.style.opacity = '0.3';
        pagingControls.style.pointerEvents = 'none';
    } else {
        pagingControls.style.opacity = '1';
        pagingControls.style.pointerEvents = 'auto';
        document.getElementById('nextBtn').disabled = true;
    }
    updateDashboard();
}

// 3. The "Master" function that fetches data and draws/updates the chart
async function updateDashboard() {
    const canvas = document.getElementById('moodChart');
    const username = canvas.dataset.username;
    const ctx = canvas.getContext('2d');

    try {
        const response = await fetch(`/api/mood_data/${username}?range=${currentRange}&offset=${currentOffset}`);
        const data = await response.json();

        // Debugging: Check if data is actually coming through
        if (data.data.length === 0) {
            console.warn("No data found for this range. Check SQL timezones.");
        }

        if (myChart) { myChart.destroy(); }

        // Create a vertical gradient for the "Better Version" look
        const gradient = ctx.createLinearGradient(0, 0, 0, 400);
        gradient.addColorStop(0, 'rgba(0, 212, 255, 0.4)');
        gradient.addColorStop(1, 'rgba(0, 212, 255, 0)');

        myChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: data.labels.map(label => label.split(' ')[1] || label), // Shorten timestamps
                datasets: [{
                    label: 'Mood Level',
                    data: data.data,
                    borderColor: '#00D4FF',
                    backgroundColor: gradient, // Use the gradient
                    borderWidth: 4,
                    pointBackgroundColor: '#ffffff',
                    pointBorderColor: '#00D4FF',
                    pointRadius: 5,
                    pointHoverRadius: 8,
                    tension: 0.4, // Smooth curves
                    fill: true
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false }, // Hide legend for cleaner look
                    tooltip: {
                        backgroundColor: '#1e293b',
                        titleColor: '#00D4FF',
                        bodyColor: '#f8fafc',
                        cornerRadius: 8,
                        padding: 12
                    }
                },
                scales: {
                    y: { 
                        min: 0, max: 6, // Padding at top and bottom
                        ticks: { stepSize: 1, color: '#94a3b8' },
                        grid: { color: 'rgba(148, 163, 184, 0.1)' }
                    },
                    x: {
                        ticks: { color: '#94a3b8' },
                        grid: { display: false }
                    }
                }
            }
        });
    } catch (error) {
        console.error('Chart failed to load:', error);
    }
}

// 4. Function to save a new mood
async function saveMood() {
    const score = document.getElementById('moodScore').value;
    const thought = document.getElementById('thoughtText').value;
    const username = document.getElementById('moodChart').dataset.username;

    try {
        const response = await fetch('/api/log_mood', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                username: username,
                mood_score: parseInt(score),
                thought_text: thought
            })
        });

        const result = await response.json();
        if (result.status === 'success') {
            document.getElementById('thoughtText').value = '';
            // Refresh the current view
            updateDashboard();
        }
    } catch (error) {
        console.error('Connection failed:', error);
    }
}

// 5. Initialize when page loads
document.addEventListener('DOMContentLoaded', () => {
    updateDashboard();
});