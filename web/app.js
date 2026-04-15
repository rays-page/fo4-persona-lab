const state = {
  personas: [],
  sessionId: null,
  currentAudio: null,
  sending: false,
  lastRequestId: 0,
};

const personaSelect = document.getElementById("persona-select");
const personaMeta = document.getElementById("persona-meta");
const playerNameInput = document.getElementById("player-name");
const locationInput = document.getElementById("location");
const speakToggle = document.getElementById("speak-toggle");
const newSessionButton = document.getElementById("new-session");
const sessionBanner = document.getElementById("session-banner");
const chatLog = document.getElementById("chat-log");
const chatForm = document.getElementById("chat-form");
const messageInput = document.getElementById("message");

function setSessionBanner() {
  const shortId = state.sessionId ? state.sessionId.slice(0, 8) : "not started";
  sessionBanner.textContent = `Session: ${shortId}`;
}

function appendMessage(role, text, detail = "") {
  const wrapper = document.createElement("article");
  wrapper.className = `message message--${role}`;

  const badge = document.createElement("div");
  badge.className = "message__badge";
  if (role === "user") {
    badge.textContent = "You";
  } else if (role === "assistant") {
    badge.textContent = "Persona";
  } else {
    badge.textContent = "System";
  }

  const body = document.createElement("div");
  body.className = "message__body";
  body.textContent = detail ? `${text}\n${detail}` : text;

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

  if (!state.personas.length) {
    throw new Error("No personas found.");
  }

  await loadPersonaDetails(personaSelect.value);
}

async function loadPersonaDetails(personaId) {
  const response = await fetch(`/api/personas/${encodeURIComponent(personaId)}`);
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.error || "Failed to load persona");
  }

  const persona = payload.persona;
  const lines = [
    persona.short_bio,
    persona.fallout_role ? `Role: ${persona.fallout_role}` : "",
    `Hook: ${persona.fallout_hook}`,
  ].filter(Boolean);
  personaMeta.textContent = lines.join("\n");
}

async function createSession() {
  const response = await fetch("/api/sessions", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ persona_id: personaSelect.value }),
  });
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.error || "Failed to create session");
  }
  state.sessionId = payload.session_id;
  setSessionBanner();
}

async function sendMessage(text) {
  if (!state.sessionId) {
    await createSession();
  }

  state.lastRequestId += 1;
  const response = await fetch("/api/bridge/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      request_id: state.lastRequestId,
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
  if (!payload.accepted) {
    throw new Error(payload.error || `Bridge rejected request ${payload.request_id}`);
  }

  state.sessionId = payload.session_id;
  setSessionBanner();
  appendMessage("assistant", payload.reply);

  if (Array.isArray(payload.warnings)) {
    for (const warning of payload.warnings) {
      appendMessage("system", warning);
    }
  }

  if (payload.audio_url) {
    if (state.currentAudio) {
      state.currentAudio.pause();
    }
    state.currentAudio = new Audio(payload.audio_url);
    state.currentAudio.play().catch(() => {});
  }
}

function setSending(sending) {
  state.sending = sending;
  chatForm.querySelector("button[type='submit']").disabled = sending;
  newSessionButton.disabled = sending;
  messageInput.disabled = sending;
}

personaSelect.addEventListener("change", async () => {
  state.sessionId = null;
  setSessionBanner();
  try {
    await loadPersonaDetails(personaSelect.value);
    appendMessage("system", "Persona changed. Start a new thread when ready.");
  } catch (error) {
    appendMessage("system", `Persona load error: ${error.message}`);
  }
});

newSessionButton.addEventListener("click", async () => {
  try {
    setSending(true);
    await createSession();
    appendMessage("system", "New session started.");
  } catch (error) {
    appendMessage("system", `Session error: ${error.message}`);
  } finally {
    setSending(false);
  }
});

chatForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (state.sending) {
    return;
  }

  const text = messageInput.value.trim();
  if (!text) {
    return;
  }

  appendMessage("user", text);
  messageInput.value = "";

  try {
    setSending(true);
    await sendMessage(text);
  } catch (error) {
    appendMessage("system", `Error: ${error.message}`);
  } finally {
    setSending(false);
  }
});

loadPersonas().catch((error) => {
  appendMessage("system", `Failed to load personas: ${error.message}`);
});
setSessionBanner();
