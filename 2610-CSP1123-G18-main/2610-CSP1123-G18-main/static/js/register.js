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
            
            // 🔒 MANDATORY REQUIRMENT REGEX: 
            // Min 6 characters, 1 lowercase, 1 uppercase, 1 digit, 1 special character
            const strongPasswordRegex = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[!@#$%^&*(),.?":{}|<> ]).{6,}$/;
            const errorBanner = document.getElementById('form-error-banner');

            if (errorBanner) {
                // Clear state and hide on a fresh form submission attempt
                errorBanner.classList.add('d-none'); 
                errorBanner.style.display = 'none';
                errorBanner.innerHTML = '';
            }

            // Check complexity guidelines
            if (passwordInput && !strongPasswordRegex.test(val)) {
                e.preventDefault(); // Stop form submission to Flask backend immediately
                if (errorBanner) {
                    errorBanner.innerHTML = '⚠️ <strong>Security Fault:</strong> Password must be at least 6 characters long and contain uppercase, lowercase, a number, and a special character (e.g., !, @, #, $, %).';
                    
                    // FIX: Strip d-none class structural layout constraints so it instantly pops up!
                    errorBanner.classList.remove('d-none');
                    errorBanner.style.display = 'block';
                    errorBanner.scrollIntoView({ behavior: 'smooth', block: 'center' });
                }
                return false;
            }
        
            // Check if confirmation input matches primary password field
            if (passwordInput && confirmInput && val !== confirmInput.value) {
                e.preventDefault();
                if (errorBanner) {
                    errorBanner.innerHTML = '⚠️ <strong>Verification Fault:</strong> Password inputs do not match.';
                    
                    errorBanner.classList.remove('d-none');
                    errorBanner.style.display = 'block';
                    errorBanner.scrollIntoView({ behavior: 'smooth', block: 'center' });
                }
                return false;
            }
            return true;
        };
    }
});