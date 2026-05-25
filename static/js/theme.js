document.addEventListener('DOMContentLoaded', () => {
    const themeToggle = document.getElementById('themeToggle');
    const htmlElement = document.documentElement;
    const themeIcon = document.getElementById('themeIcon');

    if (!themeToggle) return; // Safety check in case the button isn't on the page

    // 1. Load saved theme
    const savedTheme = localStorage.getItem('theme') || 'light';
    htmlElement.setAttribute('data-bs-theme', savedTheme);
    updateIcon(savedTheme);

    // 2. Toggle logic
    themeToggle.addEventListener('click', (e) => {
        e.preventDefault(); // Stop the menu from closing immediately
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
});