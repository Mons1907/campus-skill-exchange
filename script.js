
document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll("form[data-confirm]").forEach(function (form) {
        form.addEventListener("submit", function (event) {
            if (!window.confirm(form.dataset.confirm)) {
                event.preventDefault();
            }
        });
    });

    const chatBox = document.getElementById("chat-box");

    if (!chatBox) {
        return;
    }

    const requestId = chatBox.dataset.requestId;
    const currentId = Number(chatBox.dataset.currentId);
    let lastMessageId = -1;

    function displayMessages(messages) {
        const newestId = messages.length
            ? Number(messages[messages.length - 1].id)
            : 0;

        if (newestId === lastMessageId) {
            return;
        }

        const nearBottom =
            chatBox.scrollHeight - chatBox.scrollTop - chatBox.clientHeight < 70;

        chatBox.replaceChildren();

        messages.forEach(function (item) {
            const line = document.createElement("div");
            line.className = "chat-line " +
                (Number(item.sender_id) === currentId ? "mine" : "theirs");

            const bubble = document.createElement("div");
            bubble.className = "chat-bubble";

            const messageText = document.createElement("span");
            messageText.textContent = item.message;

            const time = document.createElement("small");
            time.textContent = item.sent_at;

            bubble.append(messageText, time);
            line.appendChild(bubble);
            chatBox.appendChild(line);
        });

        lastMessageId = newestId;

        if (nearBottom) {
            chatBox.scrollTop = chatBox.scrollHeight;
        }
    }

    async function refreshMessages() {
        try {
            const response = await fetch(
                "/api/messages/" + encodeURIComponent(requestId)
            );

            if (response.ok) {
                displayMessages(await response.json());
            }
        } catch (error) {
            // The next refresh will retry.
        }
    }

    chatBox.scrollTop = chatBox.scrollHeight;
    refreshMessages();
    window.setInterval(refreshMessages, 3000);
});
