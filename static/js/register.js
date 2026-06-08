// Wait for the HTML elements to load in the browser
document.addEventListener('DOMContentLoaded', function () {
    const passwordInput = document.getElementById('password');
    const confirmInput = document.getElementById('confirm_password');
    const form = document.getElementById('registrationForm');

    // Form Submission Validation Guard
    if (form) {
        form.onsubmit = function (e) {
            const val = passwordInput.value;
            const strongPasswordRegex = /^(?=.*[a-z])(?=.*[A-Z])(?=.*[!@#$%^&*(),.?":{}|<> ]).{6,}$/;
            const errorBanner = document.getElementById('form-error-banner');

            // Reset the banner state on every submission attempt
            if (errorBanner) {
                errorBanner.style.display = 'none';
                errorBanner.innerHTML = '';
            }

            // Check complexity guidelines
            if (!strongPasswordRegex.test(val)) {
                e.preventDefault();
                if (errorBanner) {
                    errorBanner.innerHTML = ' Your password doesn\'t meet the complexity guidelines listed above.';
                    errorBanner.style.display = 'block';
                    errorBanner.scrollIntoView({ behavior: 'smooth', block: 'center' });
                }
                return false;
            }
        
            // Check if confirmation match matches
            if (val !== confirmInput.value) {
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