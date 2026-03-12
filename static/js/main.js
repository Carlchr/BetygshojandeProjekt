const input = document.getElementById("messageInput");
const button = document.getElementById("sendButton");

button.addEventListener("click", () => {
    chatt.innerText += `{{username}}: ${input.value}\n`;
    input.value = "";
});
