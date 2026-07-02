document.addEventListener('DOMContentLoaded', () => {
    const themeToggle = document.getElementById('themeToggle');
    const htmlElement = document.documentElement;
    const themeIcon = document.getElementById('themeIcon');

    if (!themeToggle) return;

    // 1. Load saved theme
    const savedTheme = localStorage.getItem('theme') || 'light';
    htmlElement.setAttribute('data-bs-theme', savedTheme);
    updateIcon(savedTheme);

    // 2. Toggle logic
    themeToggle.addEventListener('click', (e) => {
        e.preventDefault();
        const currentTheme = htmlElement.getAttribute('data-bs-theme');
        const newTheme = currentTheme === 'light' ? 'dark' : 'light';

        htmlElement.setAttribute('data-bs-theme', newTheme);
        localStorage.setItem('theme', newTheme);
        updateIcon(newTheme);
    });

    function updateIcon(theme) {
        if (themeIcon) {
            themeIcon.innerText = theme === 'light' ? '🌙' : '☀️';
        }
    }

    // 3. Privacy Shield toggle
    const shieldToggle = document.getElementById('privacyShieldToggle');
    const shieldIcon = document.getElementById('privacyShieldIcon');
    const body = document.body;

    if (shieldToggle) {
        const savedShield = localStorage.getItem('privacyShield') === 'active';
        if (savedShield) {
            body.setAttribute('data-privacy-shield', 'active');
            if (shieldIcon) shieldIcon.textContent = '👁‍🗨';
        }

        shieldToggle.addEventListener('click', (e) => {
            e.preventDefault();
            const isActive = body.getAttribute('data-privacy-shield') === 'active';
            if (isActive) {
                body.removeAttribute('data-privacy-shield');
                localStorage.setItem('privacyShield', 'off');
                if (shieldIcon) shieldIcon.textContent = '👁';
            } else {
                body.setAttribute('data-privacy-shield', 'active');
                localStorage.setItem('privacyShield', 'active');
                if (shieldIcon) shieldIcon.textContent = '👁‍🗨';
            }
        });
    }
});