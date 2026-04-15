const state = {
  personas: [],
  sessionId: null,
  currentAudio: null,
};

const personaSelect = document.getElementById("persona-select");
const playerNameInput = document.getElementById("player-name");
const locationInput = document.getElementById("location");
const speakToggle = document.getElementById("speak-toggle");
const chatLog = document.getElementById("chat-log");
const chatForm = document.getElementById("chat-form");
const messageInput = document.getElementById("message");

function appendMessage(role, text) {
  const wrapper = document.createElement("article");
  wrapper.className = `message message--${role}`;

  const badge = document.createElement("div");
  badge.className = "message__badge";
  badge.textContent = role === "user" ? "You" : "Persona";

  const body = document.createElement("div");
  body.className = "message__body";
  body.textContent = text;

  wrapper.appendChild(badge);
  wrapper.appendChild(body);
  chatLog.appendChild(wrapper);
  chatLog.scrollTop = chatLog.scrollHeight;
}

async function loadPersonas() {
  const response = await fetch("/api/personas");
  const payload = await response.json();
  state.personas = payload.personas;
  personaSelect.innerHTML = "";

  for (const persona of state.personas) {
    const option = document.createElement("option");
    option.value = persona.persona_id;
    option.textContent = persona.display_name;
    personaSelect.appendChild(option);
  }
}

async function sendMessage(text) {
  const response = await fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      persona_id: personaSelect.value,
      session_id: state.sessionId,
      player_name: playerNameInput.value,
      location: locationInput.value,
      speak: speakToggle.checked,
      message: text,
    }),
  });

  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.error || "Request failed");
  }

  state.sessionId = payload.session_id;
  appendMessage("assistant", payload.reply);

  if (payload.audio_url) {
    if (state.currentAudio) {
      state.currentAudio.pause();
    }
    state.currentAudio = new Audio(payload.audio_url);
    state.currentAudio.play().catch(() => {});
  }
}

chatForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const text = messageInput.value.trim();
  if (!text) {
    return;
  }

  appendMessage("user", text);
  messageInput.value = "";

  try {
    await sendMessage(text);
  } catch (error) {
    appendMessage("assistant", `Error: ${error.message}`);
  }
});

loadPersonas().catch((error) => {
  appendMessage("assistant", `Failed to load personas: ${error.message}`);
});
