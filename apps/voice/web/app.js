const $ = (id) => document.getElementById(id);
const profiles = new Map();
const queue = [];
let names = {};
let catalog;
let selectedRound = null;
let playbackRound = null;
let roundList = [];
let polling = false;
let selectionVersion = 0;
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
  $("playRound").disabled = !ready || busy || !selectedRound;
  $("deleteRound").disabled = !selectedRound;
  $("roundSelect").disabled = busy;
  $("roundMode").disabled = busy;
}

function resetAudio() {
  document.querySelectorAll("audio").forEach((audio) => audio.pause());
  const audio = $("audio");
  audio.onended = null;
  audio.onerror = null;
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
  playbackRound = null;
  renderQueue();
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
    text.textContent = `${names[item.specialist_id]} · ${item.voice || "perfil salvo"} · ${item.text.slice(0, 120)}${item.text.length > 120 ? "…" : ""}`;
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

async function run(items, roundId = null) {
  stop();
  playbackRound = roundId;
  const token = generation;
  busy = true;
  renderQueue();
  try {
    for (let index = 0; index < items.length; index += 1) {
      if (token !== generation) return;
      const item = items[index];
      resetAudio();
      controller = new AbortController();
      status(`Gerando ${index + 1}/${items.length}: ${names[item.specialist_id]} · ${item.voice || "perfil salvo"}…`);
      const response = await fetch("/api/speech", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify(item), signal: controller.signal,
      });
      if (!response.ok) {
        if (roundId && response.status === 404) {
          invalidateRound(roundId);
          return;
        }
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
      status(`Ouvindo ${index + 1}/${items.length}: ${names[item.specialist_id]} · ${item.voice || "perfil salvo"}`);
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
  profiles.set($("specialist").value, { voice: $("voice").value, speed: Number($("speed").value) });
  $("profileStatus").textContent = "Alterações não salvas.";
}

async function requestJSON(url, options) {
  const response = await fetch(url, options);
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(typeof error.detail === "string" ? error.detail : "Falha na solicitação local.");
  }
  return response.json();
}

async function persistProfiles(reset = false) {
  if (!reset && !$("speed").reportValidity()) return;
  const controls = [$("saveProfiles"), $("resetProfiles"), $("specialist"), $("voice"), $("speed")];
  controls.forEach((control) => { control.disabled = true; });
  try {
    const values = reset
      ? Object.fromEntries(catalog.specialists.map((item) => [item.id, { ...item.defaults }]))
      : Object.fromEntries(profiles);
    const saved = await requestJSON("/api/profiles", {
      method: "PUT", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ schema_version: 1, profiles: values }),
    });
    Object.entries(saved.profiles).forEach(([id, profile]) => profiles.set(id, profile));
    $("specialist").onchange();
    $("profileStatus").textContent = reset ? "Padrões restaurados e salvos." : "Perfis salvos no serviço local.";
  } catch (error) {
    $("profileStatus").textContent = `${error.message} Edições preservadas.`;
  } finally {
    controls.forEach((control) => { control.disabled = false; });
  }
}

// Array.from counts Unicode code points, matching Python string offsets rather
// than UTF-16 code units. Do not trim/normalize: round references require exact slices.
function chunks(text) {
  const points = Array.from(text);
  const result = [];
  let start = 0;
  while (start < points.length) {
    let end = Math.min(start + 900, points.length);
    if (end < points.length) {
      for (let i = end - 1; i >= start + 450; i -= 1) {
        if (/\s/u.test(points[i])) { end = i + 1; break; }
      }
      if (points.slice(end).join("").trim() === "") end = points.length;
    }
    if (!points.slice(start, end).join("").trim()) end = points.length;
    result.push({ text: points.slice(start, end).join(""), text_start: start });
    start = end;
  }
  return result;
}

function roundItems(round) {
  const interventions = $("roundMode").value === "synthesis" ? [round.synthesis] : [...round.interventions, round.synthesis];
  return interventions.flatMap((item) => chunks(item.text).map((chunk) => ({
    ...chunk, specialist_id: item.specialist_id,
    round_id: round.round_id, intervention_id: item.intervention_id,
  })));
}

function renderRound() {
  $("roundDetail").replaceChildren();
  if (!selectedRound) { buttons(); return; }
  const round = selectedRound;
  const heading = document.createElement("h3");
  heading.textContent = `${round.title} · ${round.project_id} · ${round.status === "complete" ? "Completa" : "Parcial"}`;
  $("roundDetail").append(heading);
  const items = [...round.interventions, round.synthesis];
  const phases = { analysis: "Análise", counterpoint: "Contraponto", synthesis: "Síntese" };
  for (const item of items) {
    const article = document.createElement("article");
    article.className = item.phase;
    const title = document.createElement("h3");
    title.textContent = `${names[item.specialist_id]} · ${phases[item.phase]}`;
    const text = document.createElement("p");
    text.textContent = item.text;
    article.append(title);
    if (item.reply_to.length) {
      const links = document.createElement("p");
      links.className = "muted";
      links.textContent = `Responde a: ${item.reply_to.map((id) => {
        const target = items.find((entry) => entry.intervention_id === id);
        return target ? `${names[target.specialist_id]} (${phases[target.phase]})` : id;
      }).join(", ")}`;
      article.append(links);
    }
    article.append(text);
    $("roundDetail").append(article);
  }
  for (const failure of round.failures) {
    const text = document.createElement("p");
    text.textContent = `Falha: ${names[failure.specialist_id]} · ${phases[failure.phase]} · ${failure.code}`;
    $("roundDetail").append(text);
  }
  buttons();
}

function invalidateRound(id) {
  selectionVersion += 1;
  if (playbackRound === id) {
    stop();
    status("Rodada excluída ou expirada: reprodução interrompida e áudio descartado.", true);
  }
  if (selectedRound?.round_id === id || $("roundSelect").value === id) {
    selectedRound = null;
    $("roundSelect").value = "";
    renderRound();
  }
  $("roundStatus").textContent = "Rodada excluída ou expirada. Texto descartado desta página.";
}

function expireRounds() {
  const expired = roundList.filter((item) => item.expires_at * 1000 <= Date.now());
  for (const item of expired) {
    if (selectedRound?.round_id === item.round_id || playbackRound === item.round_id) invalidateRound(item.round_id);
    const option = Array.from($("roundSelect").options).find((entry) => entry.value === item.round_id);
    if (option) option.remove();
  }
  roundList = roundList.filter((item) => !expired.includes(item));
}

async function pollRounds() {
  if (polling || document.hidden) return;
  polling = true;
  try {
    const data = await requestJSON("/api/rounds");
    const selectedId = $("roundSelect").value;
    for (const id of new Set([selectedId, playbackRound].filter(Boolean))) {
      if (!data.rounds.some((item) => item.round_id === id)) invalidateRound(id);
    }
    roundList = data.rounds;
    $("roundSelect").replaceChildren(new Option("Selecione uma rodada", ""));
    for (const item of roundList) {
      $("roundSelect").add(new Option(`${item.title} · ${item.project_id} · ${item.status === "complete" ? "Completa" : "Parcial"}`, item.round_id));
    }
    $("roundSelect").value = roundList.some((item) => item.round_id === selectedId) ? selectedId : "";
    $("roundStatus").textContent = roundList.length ? `${roundList.length} rodada(s) disponível(is). Selecione e clique para ouvir.` : "Nenhuma rodada em memória. Não há histórico persistido.";
    $("retention").textContent = `Somente em memória: até ${data.retention.max_rounds} rodadas, ${data.retention.ttl_seconds / 3600} horas e ${data.retention.max_bytes} bytes no total. Reiniciar o serviço descarta tudo. Exclusão/expiração interrompe áudio e descarta o texto.`;
    expireRounds();
  } catch (error) {
    $("roundStatus").textContent = error.message;
  } finally { polling = false; buttons(); }
}

async function selectRound() {
  if (busy) { $("roundSelect").value = selectedRound?.round_id || ""; return; }
  const id = $("roundSelect").value;
  const version = ++selectionVersion;
  selectedRound = null;
  renderRound();
  if (!id) return;
  try {
    const round = await requestJSON(`/api/rounds/${encodeURIComponent(id)}`);
    if (version !== selectionVersion || busy) return;
    selectedRound = round;
    renderRound();
  } catch (error) {
    if (version === selectionVersion) $("roundStatus").textContent = error.message;
  }
}

async function deleteRound() {
  const id = selectedRound?.round_id;
  if (!id) return;
  try {
    const response = await fetch(`/api/rounds/${encodeURIComponent(id)}`, { method: "DELETE" });
    if (!response.ok && response.status !== 404) throw new Error("Não foi possível excluir a rodada.");
    invalidateRound(id);
    await pollRounds();
  } catch (error) { $("roundStatus").textContent = error.message; }
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
  const response = await fetch("/api/catalog");
  if (!response.ok) throw new Error("Não foi possível carregar os perfis.");
  const data = await response.json();
  catalog = data;
  names = Object.fromEntries(data.specialists.map((item) => [item.id, item.name]));
  const saved = await requestJSON("/api/profiles");
  Object.entries(saved.profiles).forEach(([id, profile]) => profiles.set(id, profile));
  $("profileStatus").textContent = saved.load_error ? "Falha ao ler perfis salvos. Arquivo preservado; recuperar no serviço antes de salvar." : "Perfis salvos carregados.";
  Object.entries(names).forEach(([id, name]) => $("specialist").add(new Option(name, id)));
  data.voices.forEach((voice) => $("voice").add(new Option(voice, voice)));
  $("specialist").onchange = () => {
    const profile = profiles.get($("specialist").value);
    $("voice").value = profile.voice;
    $("speed").value = profile.speed;
  };
  $("specialist").onchange();
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
  await pollRounds();
  setInterval(() => { if (!document.hidden) { void health(); void pollRounds(); } }, 3000);
  setInterval(expireRounds, 1000);
  document.addEventListener("visibilitychange", () => { if (!document.hidden) { void health(); void pollRounds(); } });
}

$("saveProfiles").onclick = () => void persistProfiles();
$("resetProfiles").onclick = () => void persistProfiles(true);
$("roundSelect").onchange = () => void selectRound();
$("deleteRound").onclick = () => void deleteRound();
$("playRound").onclick = () => {
  expireRounds();
  if (selectedRound) void run(roundItems(selectedRound), selectedRound.round_id);
};
$("text").oninput = () => { $("count").textContent = `${Array.from($("text").value).length} / 6000 caracteres`; };
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
