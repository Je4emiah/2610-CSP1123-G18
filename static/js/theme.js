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

        // TRIGGER HAPTIC FEEDBACK (ClickUp Task: Universal Feedback System)
        const modeText = newTheme === 'light' ? 'Light Mode' : 'Dark Mode';
        showToast(`Switched to ${modeText}`, 'info'); 
    });

    function updateIcon(theme) {
        if (themeIcon) {
            themeIcon.innerText = theme === 'light' ? '🌙' : '☀️';
        }
    }
});

/**
 * UNIVERSAL FEEDBACK SYSTEM (Haptic Web)
 * This function is global and can be called from any other script
 * Example: showToast("Entry Saved Successfully!", "success")
 */
function showToast(message, type = 'primary') {
    const toastElement = document.getElementById('liveToast');
    const toastMessage = document.getElementById('toastMessage');
    
    // Safety check to ensure the toast HTML exists in base.html
    if (!toastElement || !toastMessage) {
        console.warn("Toast element not found. Make sure the toast container is in base.html");
        return; 
    }

    // Set the background color based on type (success, danger, info, etc.)
    toastElement.className = `toast align-items-center text-white bg-${type} border-0`;
    toastMessage.innerText = message;
    
    // Initialize and show the Bootstrap Toast
    const toast = new bootstrap.Toast(toastElement);
    toast.show();
}