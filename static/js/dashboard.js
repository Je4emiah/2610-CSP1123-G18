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
    const label = document.getElementById('rangeLabel');

    // Update the UI Title
    if (currentRange === 'all') {
        label.innerText = "Total History";
    } else {
        const unit = currentRange.charAt(0).toUpperCase() + currentRange.slice(1);
        label.innerText = currentOffset === 0 ? `Current ${unit}` : `${currentOffset} ${unit}(s) Ago`;
    }

    try {
        const response = await fetch(`/api/mood_data/${username}?range=${currentRange}&offset=${currentOffset}`);
        const data = await response.json();
        const ctx = canvas.getContext('2d');

        // Destroy old chart to prevent "ghosting" when hovering
        if (myChart) {
            myChart.destroy();
        }

        myChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: data.labels,
                datasets: [{
                    label: 'Mood Score',
                    data: data.data,
                    borderColor: '#00D4FF',
                    backgroundColor: 'rgba(0, 212, 255, 0.1)',
                    borderWidth: 3,
                    tension: 0.3,
                    fill: true
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: { min: 1, max: 5, ticks: { stepSize: 1 } }
                }
            }
        });
    } catch (error) {
        console.error('Error loading chart:', error);
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