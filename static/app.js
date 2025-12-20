async function loadId() {
  const r = await fetch("/id");
  const data = await r.json();
  document.getElementById("empl-id").textContent =
    `EMPL_ID: ${data.EMPL_ID} (${data.LAST_NAME})`;
}

function showStatus(message, type) {
  const box = document.getElementById("status-message");
  box.style.display = "block";
  box.className = ""; // reset
  if (type === "error") box.classList.add("error");
  if (type === "loading") box.classList.add("loading");
  box.textContent = message;
}

function hideStatus() {
  const box = document.getElementById("status-message");
  box.style.display = "none";
  box.textContent = "";
  box.className = "";
}

function showRecipe(show) {
  document.getElementById("recipe-output").style.display = show ? "block" : "none";
}

async function suggestRecipe() {
  const desc = document.getElementById("recipe-query").value.trim() || "chicken";
  const time = parseInt(document.getElementById("max-time").value || "60", 10);

  showRecipe(false);
  showStatus("Loading... calling APIs and generating output.", "loading");

  const r = await fetch("/recipe", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ description: desc, max_time: time })
  });

  const data = await r.json();
  if (!r.ok) {
    showStatus(data.detail || "Request failed.", "error");
    return;
  }

  // Title + time + meta
  document.getElementById("recipe-title").textContent = data.title;
  document.getElementById("total-time").textContent = data.total_time_minutes;
  document.getElementById("ai-blurb").textContent = data.ai_blurb;
  document.getElementById("api-used").textContent = data.api_used;

  // Image
  document.getElementById("recipe-image").src = data.image_url;

  // Source link
  const link = document.getElementById("source-link");
  if (data.source_url) {
    link.href = data.source_url;
    link.style.display = "inline";
  } else {
    link.style.display = "none";
  }

  // Ingredients
  const ingList = document.getElementById("ingredient-list");
  ingList.innerHTML = "";
  (data.ingredients || []).forEach((ing) => {
    const li = document.createElement("li");
    li.textContent = ing.amount;
    ingList.appendChild(li);
  });

  // Instructions
  const instList = document.getElementById("instruction-list");
  instList.innerHTML = "";
  (data.instructions || []).forEach((step) => {
    const li = document.createElement("li");
    li.textContent = step;
    instList.appendChild(li);
  });

  hideStatus();
  showRecipe(true);
}

document.getElementById("suggest-btn").addEventListener("click", suggestRecipe);
loadId();
