const $ = (id) => document.getElementById(id);
const profiles = new Map();
const queue = [];
let names = {};
let ready = false;
let busy = false;
let generation = 0;
let controller = null;
let currentUrl = null;
let resolvePlayback = null;

function status(message, error = false) {
  $("status").textContent = message;
  $("status").classList.toggle("error", error);
}

function buttons() {
  $("generate").disabled = !ready || busy;
  $("playQueue").disabled = !ready || busy || !queue.length;
  $("enqueue").disabled = busy;
  $("clear").disabled = busy;
}

function resetAudio() {
  document.querySelectorAll("audio").forEach((audio) => audio.pause());
  const audio = $("audio");
  audio.removeAttribute("src");
  audio.load();
  if (currentUrl) URL.revokeObjectURL(currentUrl);
  currentUrl = null;
  $("download").hidden = true;
  $("download").removeAttribute("href");
  if (resolvePlayback) resolvePlayback();
  resolvePlayback = null;
}

function stop() {
  generation += 1;
  if (controller) controller.abort();
  controller = null;
  resetAudio();
  busy = false;
  buttons();
  status("Reprodução interrompida. Solicitações pendentes foram canceladas.");
}

function selected() {
  const text = $("text").value.trim();
  if (!text) throw new Error("Insira um texto antes de continuar.");
  return { text, specialist_id: $("specialist").value, voice: $("voice").value, speed: Number($("speed").value) };
}

function renderQueue() {
  $("queue").replaceChildren();
  queue.forEach((item, index) => {
    const li = document.createElement("li");
    const text = document.createElement("span");
    text.textContent = `${names[item.specialist_id]} · ${item.voice} · ${item.text.slice(0, 120)}${item.text.length > 120 ? "…" : ""}`;
    const remove = document.createElement("button");
    remove.textContent = "Remover";
    remove.className = "secondary";
    remove.disabled = busy;
    remove.onclick = () => { queue.splice(index, 1); renderQueue(); buttons(); };
    li.append(text, remove);
    $("queue").append(li);
  });
  buttons();
}

async function run(items) {
  stop();
  const token = generation;
  busy = true;
  renderQueue();
  try {
    for (let index = 0; index < items.length; index += 1) {
      if (token !== generation) return;
      const item = items[index];
      resetAudio();
      controller = new AbortController();
      status(`Gerando ${index + 1}/${items.length}: ${names[item.specialist_id]} · ${item.voice}…`);
      const response = await fetch("/api/speech", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify(item), signal: controller.signal,
      });
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || "Não foi possível gerar áudio.");
      }
      const blob = await response.blob();
      if (token !== generation) return;
      currentUrl = URL.createObjectURL(blob);
      const audio = $("audio");
      audio.src = currentUrl;
      $("download").href = currentUrl;
      $("download").hidden = false;
      status(`Ouvindo ${index + 1}/${items.length}: ${names[item.specialist_id]} · ${item.voice}`);
      const ended = new Promise((resolve, reject) => {
        resolvePlayback = resolve;
        audio.onended = resolve;
        audio.onerror = () => reject(new Error("O navegador não conseguiu reproduzir o áudio."));
      });
      try { await audio.play(); }
      catch { status("Áudio pronto. Clique em reproduzir no player para continuar."); }
      await ended;
      resolvePlayback = null;
    }
    if (token === generation) status("Reprodução concluída. O último áudio está disponível para download.");
  } catch (error) {
    if (error.name !== "AbortError" && token === generation) status(error.message, true);
  } finally {
    if (token === generation) { busy = false; controller = null; renderQueue(); }
  }
}

function saveProfile() {
  profiles.set($("specialist").value, { voice: $("voice").value, speed: $("speed").value });
}

async function health() {
  try {
    const response = await fetch("/api/health");
    if (!response.ok) throw new Error();
    const data = await response.json();
    ready = data.status === "ready";
    $("health").textContent = ready ? `Modelo pronto · CPU · pt-BR · ${data.pending} solicitação(ões) pendente(s)` : data.error || "Carregando e verificando modelo…";
    $("health").classList.toggle("error", data.status === "unavailable");
  } catch {
    ready = false;
    $("health").textContent = "Serviço indisponível. Verifique o terminal e reinicie o servidor.";
  }
  buttons();
}

async function initialize() {
  const response = await fetch("/api/voices");
  if (!response.ok) throw new Error("Não foi possível carregar os perfis.");
  const data = await response.json();
  names = data.specialists;
  Object.entries(names).forEach(([id, name]) => $("specialist").add(new Option(name, id)));
  data.voices.forEach((voice) => $("voice").add(new Option(voice, voice)));
  $("specialist").onchange = () => {
    const profile = profiles.get($("specialist").value) || { voice: data.default_voice, speed: "1" };
    $("voice").value = profile.voice;
    $("speed").value = profile.speed;
  };
  $("voice").onchange = saveProfile;
  $("speed").onchange = saveProfile;
  const samplesResponse = await fetch("/api/samples");
  const samples = await samplesResponse.json();
  for (const voice of data.voices) {
    const card = document.createElement("div");
    card.className = "sample";
    const heading = document.createElement("h3");
    heading.textContent = voice;
    card.append(heading);
    for (const row of samples.results.filter((entry) => entry.file.startsWith(voice))) {
      const label = document.createElement("label");
      label.textContent = `${row.file.split("-")[1].replace(".wav", "")} · ${row.audio_seconds}s`;
      const audio = document.createElement("audio");
      audio.controls = true;
      audio.preload = "none";
      audio.src = `/samples/${encodeURIComponent(row.file)}`;
      label.append(audio);
      card.append(label);
    }
    $("samples").append(card);
  }
  document.addEventListener("play", (event) => {
    if (event.target.tagName !== "AUDIO") return;
    if (event.target !== $("audio") && busy) stop();
    document.querySelectorAll("audio").forEach((audio) => { if (audio !== event.target) audio.pause(); });
  }, true);
  await health();
  setInterval(health, 3000);
}

$("text").oninput = () => { $("count").textContent = `${$("text").value.length} / 6000 caracteres`; };
$("generate").onclick = () => { try { void run([selected()]); } catch (error) { status(error.message, true); } };
$("enqueue").onclick = () => {
  try {
    if (queue.length >= 20) throw new Error("A sequência aceita no máximo 20 intervenções.");
    queue.push(selected()); renderQueue(); status("Intervenção adicionada à sequência.");
  } catch (error) { status(error.message, true); }
};
$("playQueue").onclick = () => void run(queue.map((item) => ({ ...item })));
$("clear").onclick = () => { queue.length = 0; renderQueue(); };
$("stop").onclick = stop;
window.addEventListener("beforeunload", stop);
initialize().catch((error) => status(error.message, true));
