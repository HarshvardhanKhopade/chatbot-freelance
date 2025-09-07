function sendMessage() {
    let userInput = document.getElementById("user-input");
    let message = userInput.value.trim();
    if (message === "") return;

    // Show user message
    let chatBox = document.getElementById("chat-box");
    chatBox.innerHTML += `<div class='message user'>${message}</div>`;

    // Call backend
    fetch(`/get-response/?msg=${message}`)
        .then(res => res.json())
        .then(data => {
            let botMessage = `<div class='message bot'>${data.reply}</div>`;
            if (data.img) {
                botMessage += `<div class='message bot'><img src="${data.img}" width="150"></div>`;
            }
            chatBox.innerHTML += botMessage;
            chatBox.scrollTop = chatBox.scrollHeight;
        });

    userInput.value = "";
}
