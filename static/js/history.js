document.addEventListener('DOMContentLoaded', () => {
    initializeTextSearch();
});

/**
 * 1. LIVE TEXT SEARCH FILTER
 * Scans through thought strings, numeric scores, and timestamps.
 */
function initializeTextSearch() {
    const searchInput = document.getElementById('diarySearchInput');
    if (!searchInput) return;

    searchInput.addEventListener('keyup', function () {
        const filter = this.value.toLowerCase().trim();
        const cards = document.querySelectorAll('.diary-card');

        cards.forEach(card => {
            const thoughtText = card.querySelector('.diary-thought-quote') ? card.querySelector('.diary-thought-quote').textContent.toLowerCase() : '';
            const scoreText = card.querySelector('.diary-score-value') ? card.querySelector('.diary-score-value').textContent.toLowerCase().trim() : '';
            const timestampText = card.querySelector('.diary-timestamps') ? card.querySelector('.diary-timestamps').textContent.toLowerCase() : '';

            const searchableContent = `${thoughtText} ${scoreText} ${timestampText}`;

            if (searchableContent.includes(filter)) {
                card.style.setProperty('display', 'block', 'important');
            } else {
                card.style.setProperty('display', 'none', 'important');
            }
        });
    });
}

/**
 * 2. MOOD CATEGORY BUTTON FILTER
 * Switches active class configurations and filters feed cards by categorical states.
 * @param {string} type - The filter category target ('all', 'good', 'neutral', 'bad')
 * @param {HTMLElement} element - The clicked button node trigger
 */
function filterMood(type, element) {
    // Remove active state overrides from all buttons
    document.querySelectorAll('.filter-tab').forEach(btn => {
        btn.classList.remove('active-all', 'active-good', 'active-neutral', 'active-bad');
    });

    // Set the specific layout class based on the chosen category
    if (type === 'all') element.classList.add('active-all');
    else if (type === 'good') element.classList.add('active-good');
    else if (type === 'neutral') element.classList.add('active-neutral');
    else if (type === 'bad') element.classList.add('active-bad');

    // Filter cards programmatically
    const cards = document.querySelectorAll('.diary-card');
    cards.forEach(card => {
        const scoreElement = card.querySelector('.diary-score-value');
        if (!scoreElement) return;

        const score = parseInt(scoreElement.textContent.trim(), 10);

        if (type === 'all') {
            card.style.setProperty('display', 'block', 'important');
        } else if (type === 'good' && score >= 4) {
            card.style.setProperty('display', 'block', 'important');
        } else if (type === 'neutral' && score === 3) {
            card.style.setProperty('display', 'block', 'important');
        } else if (type === 'bad' && score <= 2) {
            card.style.setProperty('display', 'block', 'important');
        } else {
            card.style.setProperty('display', 'none', 'important');
        }
    });
}

/**
 * 3. ASYNCHRONOUS DATA PURGE PIPELINE
 * Dispatches a background POST sequence to drop a targeted record by its identity tracking signature.
 * @param {number|string} logId - The precise database row integer identification key
 * @param {HTMLElement} btn - The clicked delete element element reference
 */
function deleteEntry(logId, btn) {
    if (!confirm("Permanently delete this entry?")) return;

    fetch(`/delete_entry/${logId}`, { method: 'POST' })
        .then(res => {
            if (res.ok) {
                // Find the parent item vector and remove it cleanly from view
                const targetCard = btn.closest('.diary-card');
                if (targetCard) targetCard.remove();

                // Decrement structural badge counter context strings smoothly
                const badge = document.querySelector('.diary-counter-badge');
                if (badge) {
                    const currentCount = parseInt(badge.innerText, 10) || 0;
                    badge.innerText = `${Math.max(0, currentCount - 1)} entries`;
                }
            } else {
                alert("Delete operation failed on backend engine targets.");
            }
        })
        .catch(err => {
            console.error("Network structural error parsing deletion telemetry:", err);
            alert("Network error: Could not reach server application layers.");
        });
}