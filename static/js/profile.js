/**
 * MindMetric Profile Security Constraints Assertion
 * Handles client-side verification and UI interactions for profile credential management.
 */
document.addEventListener('DOMContentLoaded', () => {
    
    // 1. Core Password Visibility Toggler Function
    const togglePasswordVisibility = (inputId, iconElement) => {
        const targetInput = document.getElementById(inputId);
        if (targetInput) {
            if (targetInput.type === "password") {
                targetInput.type = "text";
                iconElement.textContent = "🙈"; // Change to monkey emoji when visible
            } else {
                targetInput.type = "password";
                iconElement.textContent = "👁️";  // Change back to eye when hidden
            }
        }
    };

    // 2. Attach Click Listeners to all password-toggle items automatically
    const togglers = document.querySelectorAll('.password-toggle');
    togglers.forEach(toggler => {
        toggler.addEventListener('click', function() {
            const associatedInput = this.parentElement.querySelector('input');
            if (associatedInput) {
                togglePasswordVisibility(associatedInput.id, this);
            }
        });
    });

    // 3. Password Validation Rules Implementation
    const passwordForm = document.getElementById('passwordUpdateForm');
    if (passwordForm) {
        passwordForm.onsubmit = function (event) {
            const currentPassword = document.getElementById('current_password').value;
            const newPassword = document.getElementById('new_password').value;
            const confirmPassword = document.getElementById('confirm_password').value;

            // Only run validation checks if the user is attempting to alter their password
            if (newPassword.trim() !== "") {
                
                // Constraint Check A: Block old password replication matches
                if (currentPassword === newPassword) {
                    event.preventDefault();
                    alert('Security Fault: Your new password cannot be the same as your current password.');
                    return false;
                }

                // Constraint Check B: Confirm matching password integrity fields
                if (newPassword !== confirmPassword) {
                    event.preventDefault();
                    alert('Verification check failed: Your new password inputs do not match.');
                    return false;
                }

                // Constraint Check C: Uniform application criteria (6+ chars, casing, numbers, special tokens)
                const strongPasswordRegex = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[!@#$%^&*(),.?\":{}|<> ]).{6,}$/;
                if (!strongPasswordRegex.test(newPassword)) {
                    event.preventDefault();
                    alert('Security Fault: Your new password must be at least 6 characters long and contain uppercase, lowercase, a number, and a special character (e.g., !, @, #, $, %).');
                    return false;
                }
            }
            return true;
        };
    }
}); 