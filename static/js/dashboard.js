// Global State Management
let currentOffset = 0;
let currentRange = 'day';
let myChart = null; 

//1. Logic for moving between "pages" (Previous/Next)
function movePage(step) {
    currentOffset += step;
    if (currentOffset < 0) currentOffset = 0;
    
    // Disable "Next" if users are at the most recent page
    document.getElementById('nextBtn').disabled = (currentOffset === 0);
    updateDashboard();
}

//2. Logic for changing the time scale (24h / Week / All)
function changeRange(range) {
    currentRange = range;
    currentOffset = 0; 
    
    const label = document.getElementById('rangeLabel');
    const pagingControls = document.getElementById('pagingControls');

    // Update the sub-header text
    const labels = { 'day': 'Last 24 Hours', 'week': 'This Week', 'all': 'Full History' };
    label.innerText = labels[range] || 'Overview';

    // Disable paging buttons if viewing "All" data
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

//Master function to fetch data and render the Cha0rt
async function updateDashboard() {
    const canvas = document.getElementById('moodChart');
    const counterElement = document.getElementById('dataCounter');
    const username = canvas.dataset.username;
    const ctx = canvas.getContext('2d');

    // Visual feedback
    if (counterElement) counterElement.innerText = "Refreshing...";

    try {
        const response = await fetch(`/api/mood_data/${username}?range=${currentRange}&offset=${currentOffset}`);
        const data = await response.json();

        // Update Counter
        if (counterElement) {
            const count = data.data.length;
            counterElement.innerText = `${count} entries found`;
            
            // Toggle red color if empty
            if (count === 0) {
                counterElement.style.color = "#ef4444";
            } else {
                counterElement.style.color = "#94a3b8";
            }
        }

        if (myChart) { myChart.destroy(); }

        // Create a vertical gradient for the line area
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
        if (counterElement) counterElement.innerText = "Error loading data";
    }
}

// 4. Logic for the Mood Input Form
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
            // Immediately refresh the current view
            updateDashboard();
        }
    } catch (error) {
        console.error('Submission failed:', error);
    }
}

// 5. Auto-Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    updateDashboard();
});

function generateInsight(data) {
    if (data.length === 0) return "Start logging to see insights!";

    // Calculate the average score
    const avg = data.reduce((a, b) => a + b, 0) / data.length;
    
    // The "Dictionary" logic
    const insights = {
        5: "You're on fire! Keep doing what makes you happy. 🌟",
        4: "Looking good! A steady week so far. 👍",
        3: "A bit of a neutral week. Maybe try a new hobby? ☕",
        2: "Things seem tough. Don't forget to take a break. 🌿",
        1: "It's okay to have bad days. Reach out to a friend. ❤️"
    };

    // Round the average to the nearest whole number to match the dictionary keys
    const scoreKey = Math.round(avg);
    return insights[scoreKey] || "Keep tracking to find your pattern!";
}

// Then, inside updateDashboard, after fetching 'data':
const insightBox = document.getElementById('insightBox');
const insightText = document.getElementById('insightText');

if (currentRange === 'week' && data.data.length > 0) {
    insightBox.style.display = 'block';
    insightText.innerText = generateInsight(data.data);
} else {
    insightBox.style.display = 'none';
}