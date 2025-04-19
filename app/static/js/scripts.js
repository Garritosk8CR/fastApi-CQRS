function showAlert(message, isError = false) {
    const alertBox = document.getElementById("alert-box");
    const alertMessage = document.getElementById("alert-message");
    
    alertMessage.textContent = message;
    alertBox.style.display = "block";
    alertBox.style.backgroundColor = isError ? "#ffcccc" : "#ccffcc";
    alertBox.style.color = "#333";
    alertBox.style.padding = "10px";
    alertBox.style.border = "1px solid #999";
}
