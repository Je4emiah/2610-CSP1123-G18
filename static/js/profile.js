/**
 * MindMetric Profile Security Constraints Assertion
 * Handles client-side verification for the three-tier password reset logic.
 */
document.addEventListener('DOMContentLoaded', () => {
    const passwordForm = document.getElementById('passwordUpdateForm');

    if (passwordForm) {
        passwordForm.onsubmit = function (event) {
            const currentPassword = document.getElementById('current_password').value;
            const newPassword = document.getElementById('new_password').value;
            const confirmPassword = document.getElementById('confirm_password').value;

            // Only run password checks if the user typed something in the new password field
            if (newPassword.trim() !== "") {
                
                // Check 1: Prevent setting a new password that matches the current one
                if (currentPassword === newPassword) {
                    event.preventDefault();
                    alert('Security Fault: Your new password cannot be the same as your current password.');
                    return false;
                }

                // Check 2: Verify confirmation input matches the new password entry
                if (newPassword !== confirmPassword) {
                    event.preventDefault();
                    alert('Verification check failed: Your new password inputs do not match.');
                    return false;
                }

                // Check 3: Enforce strict 6+ character complexity parameters (with Special Characters)
                const strongPasswordRegex = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[!@#$%^&*(),.?":{}|<> ]).{6,}$/;
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