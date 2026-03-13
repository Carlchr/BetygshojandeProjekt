const input = document.getElementById("messageInput");
const button = document.getElementById("sendButton");

const username = "{{ session['username'] }}";

button.addEventListener("click", () => {
    chatt.innerText += `${username}: ${input.value}\n`;
    input.value = "";
});
