let state = null;
let selectedTokenId = null;
let advantageMode = "normal";

const terrainClass = {
  wall: "wall",
  water: "water",
  difficult: "difficult",
};

const $ = (selector) => document.querySelector(selector);

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.error || "request failed");
  }
  return payload;
}

async function loadState() {
  state = await api("/api/state");
  render();
}

function render() {
  renderSession();
  renderMap();
  renderCharacters();
  renderEvents();
}

function renderSession() {
  $("#session-title").textContent = state.session.title;
  $("#session-mode").textContent = state.session.mode;
  $("#session-round").textContent = `Round ${state.session.round}`;
  const current = state.tokens.find((token) => token.id === state.session.currentTurn);
  $("#session-turn").textContent = current ? `Turn ${current.name}` : "Turn";
  $("#map-title").textContent = state.map.name;
}

function renderMap() {
  const grid = $("#map-grid");
  grid.style.setProperty("--cols", state.map.width);
  grid.style.setProperty("--rows", state.map.height);
  grid.innerHTML = "";

  for (let y = 0; y < state.map.height; y += 1) {
    for (let x = 0; x < state.map.width; x += 1) {
      const cell = document.createElement("button");
      cell.type = "button";
      cell.className = "cell";
      cell.dataset.x = x;
      cell.dataset.y = y;
      cell.setAttribute("aria-label", `grid ${x + 1}, ${y + 1}`);

      const terrain = state.map.terrain.find((item) => item.x === x && item.y === y);
      if (terrain) {
        cell.classList.add(terrainClass[terrain.type] || terrain.type);
      }
      if (selectedTokenId && !cell.classList.contains("wall")) {
        cell.classList.add("selected");
      }

      const annotation = state.map.annotations.find((item) => item.x === x && item.y === y);
      if (annotation) {
        const badge = document.createElement("span");
        badge.className = "annotation";
        badge.textContent = annotation.label;
        cell.appendChild(badge);
      }

      const token = state.tokens.find((item) => item.x === x && item.y === y);
      if (token) {
        const tokenButton = document.createElement("span");
        tokenButton.className = `token ${token.kind}`;
        tokenButton.textContent = token.name.slice(0, 1);
        tokenButton.title = token.name;
        if (selectedTokenId === token.id) {
          tokenButton.classList.add("active");
        }
        cell.appendChild(tokenButton);
      }

      cell.addEventListener("click", () => handleCellClick(x, y));
      grid.appendChild(cell);
    }
  }
}

async function handleCellClick(x, y) {
  const token = state.tokens.find((item) => item.x === x && item.y === y);
  if (token) {
    selectedTokenId = token.id === selectedTokenId ? null : token.id;
    renderMap();
    return;
  }
  if (!selectedTokenId) {
    return;
  }

  try {
    const payload = await api("/api/token/move", {
      method: "POST",
      body: JSON.stringify({ tokenId: selectedTokenId, x, y }),
    });
    state = payload.state;
    selectedTokenId = null;
    render();
  } catch (error) {
    pushLocalNotice(error.message);
  }
}

function renderCharacters() {
  const list = $("#character-list");
  list.innerHTML = "";
  state.characters.forEach((character) => {
    const card = document.createElement("article");
    card.className = "character-card";
    const hpPercent = Math.max(0, Math.min(100, (character.hp.current / character.hp.max) * 100));
    const stats = Object.entries(character.attributes)
      .map(([key, value]) => `<div class="stat"><span>${key}</span><strong>${value}</strong></div>`)
      .join("");
    const conditions = character.conditions.length ? character.conditions.join(" / ") : "无";

    card.innerHTML = `
      <div class="character-main">
        <div>
          <h3>${character.name}</h3>
          <p>${character.race} · ${character.class}</p>
        </div>
        <div class="pill">AC ${character.ac}</div>
        <div class="pill">${character.speed} ft</div>
      </div>
      <div class="character-body">
        <p class="stat-list">HP ${character.hp.current}/${character.hp.max} · Temp ${character.hp.temp}</p>
        <div class="hp-bar"><div class="hp-fill" style="width: ${hpPercent}%"></div></div>
        <div class="stat-grid">${stats}</div>
        <p class="detail-list">技能：${character.skills.join(" / ")}</p>
        <p class="detail-list">攻击：${character.attacks.join(" / ")}</p>
        <p class="detail-list">状态：${conditions}</p>
      </div>
    `;
    list.appendChild(card);
  });
}

function renderEvents() {
  const log = $("#event-log");
  log.innerHTML = "";
  state.events.forEach((event) => {
    const row = document.createElement("article");
    row.className = `event ${event.type}`;
    row.innerHTML = `
      <div class="event-meta">
        <span>${event.speaker}</span>
        <span>${event.time}</span>
      </div>
      <div>${event.text}</div>
    `;
    log.appendChild(row);
  });
  log.scrollTop = log.scrollHeight;
}

function pushLocalNotice(message) {
  const localState = {
    type: "system",
    speaker: "System",
    time: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    text: message,
  };
  state.events.push(localState);
  renderEvents();
}

async function handleChatSubmit(event) {
  event.preventDefault();
  const input = $("#chat-input");
  const message = input.value.trim();
  if (!message) {
    return;
  }
  input.value = "";
  try {
    const payload = await api("/api/chat", {
      method: "POST",
      body: JSON.stringify({ speaker: "玩家", message }),
    });
    state = payload.state;
    render();
  } catch (error) {
    pushLocalNotice(error.message);
  }
}

async function handleDiceSubmit(event) {
  event.preventDefault();
  try {
    const payload = await api("/api/dice", {
      method: "POST",
      body: JSON.stringify({
        expression: $("#dice-expression").value,
        reason: $("#dice-reason").value,
        advantage: advantageMode,
        rollerId: selectedTokenId || "manual",
      }),
    });
    state = payload.state;
    const result = payload.result;
    $("#dice-result").textContent = `${result.expression} -> ${result.total} | rolls ${result.rolls.join(", ")}`;
    render();
  } catch (error) {
    pushLocalNotice(error.message);
  }
}

function bindControls() {
  $("#chat-form").addEventListener("submit", handleChatSubmit);
  $("#dice-form").addEventListener("submit", handleDiceSubmit);
  $("#clear-selection").addEventListener("click", () => {
    selectedTokenId = null;
    renderMap();
  });

  document.querySelectorAll("[data-advantage]").forEach((button) => {
    button.addEventListener("click", () => {
      advantageMode = button.dataset.advantage;
      document.querySelectorAll("[data-advantage]").forEach((item) => item.classList.remove("active"));
      button.classList.add("active");
    });
  });
}

bindControls();
loadState().catch((error) => {
  document.body.innerHTML = `<main class="app-shell"><p>${error.message}</p></main>`;
});
