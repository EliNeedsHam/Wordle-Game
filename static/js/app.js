const state = {
  profiles: [],
  currentProfileId: null,
  currentProfileName: "",
  game: null,
  draft: "",
  toastTimer: null,
};

const board = document.querySelector("#board");
const keyboard = document.querySelector("#keyboard");
const statusEl = document.querySelector("#status");
const profileForm = document.querySelector("#profile-form");
const profileName = document.querySelector("#profile-name");
const profileSelect = document.querySelector("#profile-select");
const playerHeading = document.querySelector("#player-heading");
const newGameButton = document.querySelector("#new-game");
const toast = document.querySelector("#toast");
const resultPanel = document.querySelector("#result-panel");
const resultKicker = document.querySelector("#result-kicker");
const resultTitle = document.querySelector("#result-title");
const resultCopy = document.querySelector("#result-copy");
const resultGif = document.querySelector("#result-gif");
const emojiBurst = document.querySelector("#emoji-burst");

const rows = ["QWERTYUIOP", "ASDFGHJKL", "ZXCVBNM"];

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    credentials: "same-origin",
    ...options,
  });
  const data = await response.json();
  if (!response.ok) {
    const error = new Error(data.error || "Something went wrong.");
    error.payload = data;
    throw error;
  }
  return data;
}

function showToast(message) {
  toast.textContent = message;
  toast.classList.add("show");
  clearTimeout(state.toastTimer);
  state.toastTimer = setTimeout(() => toast.classList.remove("show"), 2200);
}

function setStatus(message) {
  statusEl.textContent = message;
}

function renderProfiles() {
  profileSelect.innerHTML = "";
  if (!state.profiles.length) {
    const option = document.createElement("option");
    option.textContent = "No profiles yet";
    option.value = "";
    profileSelect.append(option);
    profileSelect.disabled = true;
    return;
  }
  profileSelect.disabled = false;
  if (!state.currentProfileId) {
    const placeholder = document.createElement("option");
    placeholder.textContent = "Choose a profile";
    placeholder.value = "";
    placeholder.selected = true;
    profileSelect.append(placeholder);
  }
  for (const profile of state.profiles) {
    const option = document.createElement("option");
    option.value = profile.id;
    option.textContent = profile.name;
    option.selected = profile.id === state.currentProfileId;
    profileSelect.append(option);
  }
}

function renderBoard() {
  board.innerHTML = "";
  const guesses = state.game?.guesses || [];
  const activeRow = guesses.length;
  const complete = state.game && state.game.status !== "active";

  for (let rowIndex = 0; rowIndex < 6; rowIndex += 1) {
    const row = document.createElement("div");
    row.className = "row";
    if (complete && state.game.status === "won" && rowIndex === guesses.length - 1) {
      row.classList.add("win");
    }

    for (let colIndex = 0; colIndex < 5; colIndex += 1) {
      const tile = document.createElement("div");
      tile.className = "tile";
      const guess = guesses[rowIndex];
      let letter = "";
      if (guess) {
        letter = guess.word[colIndex];
        tile.classList.add(guess.pattern[colIndex], "reveal");
        tile.style.animationDelay = `${colIndex * 90}ms`;
      } else if (rowIndex === activeRow && !complete) {
        letter = state.draft[colIndex] || "";
        if (letter) tile.classList.add("filled");
      }
      tile.textContent = letter;
      row.append(tile);
    }
    board.append(row);
  }
}

function renderKeyboard() {
  keyboard.innerHTML = "";
  const keyboardState = state.game?.keyboard || {};
  rows.forEach((letters, rowIndex) => {
    const keyRow = document.createElement("div");
    keyRow.className = "key-row";

    if (rowIndex === 2) keyRow.append(makeKey("Enter", "ENTER", true));
    for (const letter of letters) {
      keyRow.append(makeKey(letter, letter, false, keyboardState[letter.toLowerCase()]));
    }
    if (rowIndex === 2) keyRow.append(makeKey("Back", "BACKSPACE", true));
    keyboard.append(keyRow);
  });
}

function makeKey(label, value, wide, quality) {
  const button = document.createElement("button");
  button.className = `key${wide ? " wide" : ""}${quality ? ` ${quality}` : ""}`;
  button.type = "button";
  button.textContent = label;
  button.dataset.key = value;
  button.addEventListener("click", () => handleKey(value));
  return button;
}

function renderStats(stats = null) {
  const fallback = {
    games_played: 0,
    win_percentage: 0,
    current_streak: 0,
    max_streak: 0,
    guess_distribution: { 1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0 },
  };
  const data = stats || fallback;
  document.querySelector("#stat-played").textContent = data.games_played;
  document.querySelector("#stat-win-rate").textContent = `${data.win_percentage}%`;
  document.querySelector("#stat-streak").textContent = data.current_streak;
  document.querySelector("#stat-max-streak").textContent = data.max_streak;

  const max = Math.max(1, ...Object.values(data.guess_distribution).map(Number));
  const distribution = document.querySelector("#distribution");
  distribution.innerHTML = "";
  for (let index = 1; index <= 6; index += 1) {
    const count = Number(data.guess_distribution[index] || 0);
    const row = document.createElement("div");
    row.className = "bar";
    row.innerHTML = `
      <span>${index}</span>
      <span class="bar-track"><span class="bar-fill" style="width:${(count / max) * 100}%"></span></span>
      <span>${count}</span>
    `;
    distribution.append(row);
  }
}

function renderResult() {
  if (!state.game || state.game.status === "active") {
    resultPanel.hidden = true;
    resultPanel.className = "result-panel";
    resultGif.removeAttribute("src");
    resultGif.alt = "";
    emojiBurst.innerHTML = "";
    return;
  }

  const won = state.game.status === "won";
  const answer = state.game.answer.toUpperCase();
  const emojis = won ? ["🎉", "✨", "🔥", "🏆", "💫", "🚀"] : ["💥", "😵", "🌧️", "🫠", "⚡", "🎭"];
  resultPanel.hidden = false;
  resultPanel.className = `result-panel ${won ? "win" : "loss"}`;
  resultKicker.textContent = won ? "Victory unlocked" : "Word revealed";
  resultTitle.textContent = won ? `Congratulations! ${answer}!` : `So close. It was ${answer}.`;
  resultCopy.textContent = won
    ? `Solved in ${state.game.guess_count} ${state.game.guess_count === 1 ? "guess" : "guesses"}.`
    : "Take the reveal, reload your courage, and run it back.";

  if (state.game.gif_url) {
    resultGif.hidden = false;
    resultGif.src = state.game.gif_url;
    resultGif.alt = `${state.game.answer} GIF`;
  } else {
    resultGif.hidden = true;
    resultGif.removeAttribute("src");
    resultGif.alt = "";
  }

  emojiBurst.innerHTML = emojis
    .map(
      (emoji, index) =>
        `<span style="--x:${12 + index * 14}%; --delay:${index * 90}ms">${emoji}</span>`
    )
    .join("");
}

function renderAll() {
  renderProfiles();
  renderBoard();
  renderKeyboard();
  renderResult();
  newGameButton.disabled = !state.currentProfileId;
  playerHeading.textContent = state.currentProfileName || "Choose a profile";
}

async function loadProfiles() {
  const data = await api("/api/profiles");
  state.profiles = data.profiles;
  const saved = Number(localStorage.getItem("wordforgeProfileId"));
  state.currentProfileId = data.current_profile_id || saved || null;
  const selected = state.profiles.find((profile) => profile.id === state.currentProfileId);
  state.currentProfileName = selected?.name || "";
  if (!selected) {
    state.currentProfileId = null;
    localStorage.removeItem("wordforgeProfileId");
  }
  renderAll();
  if (selected && !data.current_profile_id) {
    await selectProfile(selected.id);
    return;
  }
  if (selected) await loadGameAndStats();
}

async function selectProfile(profileId) {
  const data = await api("/api/session/profile", {
    method: "POST",
    body: JSON.stringify({ profile_id: Number(profileId) }),
  });
  state.currentProfileId = data.profile.id;
  state.currentProfileName = data.profile.name;
  localStorage.setItem("wordforgeProfileId", data.profile.id);
  state.draft = "";
  await loadGameAndStats();
}

async function loadGameAndStats() {
  const [gameData, statsData] = await Promise.all([
    api("/api/games/current"),
    api("/api/stats"),
  ]);
  state.game = gameData.game;
  state.draft = "";
  renderStats(statsData.stats);
  updateGameStatus();
  renderAll();
}

async function startNewGame() {
  if (!state.currentProfileId) return;
  const data = await api("/api/games", { method: "POST", body: "{}" });
  state.game = data.game;
  state.draft = "";
  setStatus("Fresh word loaded.");
  renderAll();
}

async function submitGuess() {
  if (!state.game || state.game.status !== "active") return;
  if (state.draft.length !== 5) {
    shakeActiveRow();
    showToast("Type five letters first.");
    return;
  }
  try {
    const data = await api("/api/games/current/guesses", {
      method: "POST",
      body: JSON.stringify({ guess: state.draft }),
    });
    state.game = data.game;
    state.draft = "";
    updateGameStatus();
    renderAll();
    if (state.game.status !== "active") {
      const statsData = await api("/api/stats");
      renderStats(statsData.stats);
    }
  } catch (error) {
    shakeActiveRow();
    showToast(error.message);
  }
}

function updateGameStatus() {
  if (!state.currentProfileId) {
    setStatus("Create a profile to begin.");
    return;
  }
  if (!state.game) {
    setStatus("Start a new game.");
    return;
  }
  if (state.game.status === "won") {
    const guessLabel = state.game.guess_count === 1 ? "guess" : "guesses";
    setStatus(
      `Solved in ${state.game.guess_count} ${guessLabel}. The word was ${state.game.answer.toUpperCase()}.`
    );
  } else if (state.game.status === "lost") {
    setStatus(`The word was ${state.game.answer.toUpperCase()}. New game when ready.`);
  } else {
    setStatus(`${6 - state.game.guess_count} guesses remaining.`);
  }
}

function shakeActiveRow() {
  const row = board.children[state.game?.guess_count || 0];
  if (!row) return;
  row.classList.remove("shake");
  void row.offsetWidth;
  row.classList.add("shake");
}

function handleKey(key) {
  if (!state.currentProfileId || !state.game || state.game.status !== "active") return;
  if (key === "ENTER") {
    submitGuess();
    return;
  }
  if (key === "BACKSPACE") {
    state.draft = state.draft.slice(0, -1);
    renderBoard();
    return;
  }
  if (/^[A-Z]$/.test(key) && state.draft.length < 5) {
    state.draft += key.toLowerCase();
    renderBoard();
  }
}

profileForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    const data = await api("/api/profiles", {
      method: "POST",
      body: JSON.stringify({ name: profileName.value }),
    });
    profileName.value = "";
    await loadProfiles();
    await selectProfile(data.profile.id);
    showToast(`Profile ready: ${data.profile.name}`);
  } catch (error) {
    showToast(error.message);
  }
});

profileSelect.addEventListener("change", () => {
  if (profileSelect.value) selectProfile(profileSelect.value);
});

newGameButton.addEventListener("click", startNewGame);

document.addEventListener("keydown", (event) => {
  const target = event.target;
  if (target instanceof HTMLInputElement || target instanceof HTMLSelectElement) return;
  if (event.key === "Enter") handleKey("ENTER");
  else if (event.key === "Backspace") handleKey("BACKSPACE");
  else if (/^[a-zA-Z]$/.test(event.key)) handleKey(event.key.toUpperCase());
});

loadProfiles().catch((error) => showToast(error.message));
