// Wait for the HTML elements to load in the browser
document.addEventListener('DOMContentLoaded', function () {
    const passwordInput = document.getElementById('password');
    const confirmInput = document.getElementById('confirm_password');
    const form = document.getElementById('registrationForm');

// Global reusable toggle handler (Fixed Icon Mapping)
    window.togglePasswordVisibility = function (inputId, iconElement) {
        const targetInput = document.getElementById(inputId);
        if (targetInput) {
            if (targetInput.type === "password") {
                targetInput.type = "text";
                iconElement.textContent = "🙈"; // Text is visible -> Click to hide it
            } else {
                targetInput.type = "password";
                iconElement.textContent = "👁️"; // Text is hidden dots -> Click to see it
            }
        }
    };

    // Form Submission Validation Guard
    if (form) {
        form.onsubmit = function (e) {
            const val = passwordInput ? passwordInput.value : '';
            const strongPasswordRegex = /^(?=.*[a-z])(?=.*[A-Z])(?=.*[!@#$%^&*(),.?":{}|<> ]).{6,}$/;
            const errorBanner = document.getElementById('form-error-banner');

            if (errorBanner) {
                errorBanner.style.display = 'none';
                errorBanner.innerHTML = '';
            }

            // Check complexity guidelines
            if (passwordInput && !strongPasswordRegex.test(val)) {
                e.preventDefault();
                if (errorBanner) {
                    errorBanner.innerHTML = '⚠️ <strong>Security Fault:</strong> Your password doesn\'t meet the complexity guidelines listed above.';
                    errorBanner.style.display = 'block';
                    errorBanner.scrollIntoView({ behavior: 'smooth', block: 'center' });
                }
                return false;
            }
        
            // Check if confirmation match matches
            if (passwordInput && confirmInput && val !== confirmInput.value) {
                e.preventDefault();
                if (errorBanner) {
                    errorBanner.innerHTML = '⚠️ <strong>Verification Fault:</strong> Password inputs do not match.';
                    errorBanner.style.display = 'block';
                    errorBanner.scrollIntoView({ behavior: 'smooth', block: 'center' });
                }
                return false;
            }
            return true;
        };
    }
});