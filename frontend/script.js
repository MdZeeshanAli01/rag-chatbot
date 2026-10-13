const API_URL = (window.location.port === "8000") ? "" : "http://127.0.0.1:8000";

// Upload PDF
async function uploadPDF() {
    const fileInput = document.getElementById("pdfFile");
    const uploadBtn = document.querySelector(".upload-box button");

    if (fileInput.files.length === 0) {
        alert("Please select a PDF file first.");
        return;
    }

    const file = fileInput.files[0];
    const formData = new FormData();
    formData.append("file", file);

    const originalBtnText = uploadBtn ? uploadBtn.innerText : "Upload PDF";
    if (uploadBtn) {
        uploadBtn.disabled = true;
        uploadBtn.innerText = "⏳ Processing PDF... (please wait)";
    }

    try {
        const response = await fetch(`${API_URL}/upload`, {
            method: "POST",
            body: formData
        });

        const data = await response.json();

        if (!response.ok) {
            alert("Upload failed: " + (data.detail || "Error processing file."));
            return;
        }

        alert(data.message || "PDF uploaded and processed successfully!");

    } catch (error) {
        alert("Upload error: " + (error.message || "Connection failed. Make sure the backend is running."));
        console.error("Upload error:", error);
    } finally {
        if (uploadBtn) {
            uploadBtn.disabled = false;
            uploadBtn.innerText = originalBtnText;
        }
    }
}


// Ask Question
async function askQuestion() {
    const input = document.getElementById("question");
    const question = input.value.trim();

    if (question === "") return;

    const chatBox = document.getElementById("chatBox");

    chatBox.innerHTML += `
        <div class="message">
            <div class="user">You:</div>
            <div>${escapeHTML(question)}</div>
        </div>
    `;

    input.value = "";

    // Show temporary typing indicator
    const loadingId = "loading-" + Date.now();
    chatBox.innerHTML += `
        <div class="message" id="${loadingId}">
            <div class="bot">Bot:</div>
            <div><em>Thinking...</em></div>
        </div>
    `;
    chatBox.scrollTop = chatBox.scrollHeight;

    try {
        const response = await fetch(
            `${API_URL}/ask?query=${encodeURIComponent(question)}`
        );

        const data = await response.json();
        const loadingElem = document.getElementById(loadingId);

        if (!response.ok) {
            const errText = data.detail || "Server error";
            if (loadingElem) {
                loadingElem.innerHTML = `
                    <div class="bot">Bot:</div>
                    <div style="color: #ff6b6b;">Error: ${escapeHTML(errText)}</div>
                `;
            }
            return;
        }

        if (loadingElem) {
            loadingElem.innerHTML = `
                <div class="bot">Bot:</div>
                <div>${escapeHTML(data.answer || "No response received.")}</div>
            `;
        }

        chatBox.scrollTop = chatBox.scrollHeight;

    } catch (error) {
        const loadingElem = document.getElementById(loadingId);
        if (loadingElem) {
            loadingElem.innerHTML = `
                <div class="bot">Bot:</div>
                <div style="color: #ff6b6b;">Failed to connect to backend server.</div>
            </div>
            `;
        }
        console.error(error);
    }
}

// Allow Enter key to submit questions
document.addEventListener("DOMContentLoaded", () => {
    const input = document.getElementById("question");
    if (input) {
        input.addEventListener("keydown", (event) => {
            if (event.key === "Enter") {
                event.preventDefault();
                askQuestion();
            }
        });
    }
});

function escapeHTML(str) {
    return str
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}