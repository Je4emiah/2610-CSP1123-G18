function togglePasswordVisibility(fieldId, iconElement) {
    const input = document.getElementById(fieldId);
    if (input.type === "password") {
        input.type = "text";
        iconElement.textContent = "🙈";
    } else {
        input.type = "password";
        iconElement.textContent = "👁️";
    }
}