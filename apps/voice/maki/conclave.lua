local ROOT = "D:/conclave/"
local MAX = 128 * 1024
local rounds, order, active = {}, {}, {}
local sequence = 0
local slots = maki.async.semaphore(3)
local epoch = tostring(os.time()) .. tostring({}):gsub("[^%w]", "")
local specialists
-- require() cannot yield; filesystem access belongs to a tool coroutine.
local function load_specialists()
    if specialists then return true end
    local content = maki.fs.read(ROOT .. "apps/voice/catalog.json")
    if not content then return false end
    local ok, catalog = pcall(maki.json.decode, content)
    if not ok or type(catalog) ~= "table" or type(catalog.specialists) ~= "table" then return false end
    local loaded = {}
    for _, item in ipairs(catalog.specialists) do
        if type(item) ~= "table" or type(item.id) ~= "string" or type(item.name) ~= "string" or type(item.responsibility) ~= "string" then return false end
        loaded[item.id] = item
    end
    specialists = loaded
    return true
end

local function array(t)
    if #t == 0 then return maki.json.decode("[]") end
    return t
end
local function output(value, failed)
    return { llm_output = type(value) == "string" and value or maki.json.encode(value), is_error = failed or false }
end
local function text(value, limit)
    if type(value) ~= "string" or not value:match("%S") then return false end
    local n = 0
    for _ in value:gmatch("[^\128-\191]") do n = n + 1 end
    return n <= limit
end
local function identifier(value)
    return type(value) == "string" and #value <= 128 and value:match("^[A-Za-z0-9][A-Za-z0-9_.:%-]*$")
end
local function owner(ctx)
    if not ctx or ctx:task_id() ~= "main" then return nil end
    local sid = ctx:session_id()
    if identifier(sid) then return sid end
end
local function purge()
    local kept = {}
    for _, id in ipairs(order) do
        local r = rounds[id]
        if r and os.time() - r.created < 7200 then kept[#kept + 1] = id else rounds[id] = nil end
    end
    order = kept
end
-- spawn starts after require and is cancelled automatically when the plugin unloads.
-- No filesystem/network work is performed by this idle TTL sweep.
maki.async.spawn(function()
    while true do
        maki.async.sleep(30000)
        purge()
    end
end)
local function lookup(id, sid)
    purge()
    local r = rounds[id]
    if r and r.session_id == sid then return r end
end
local function read_brain(slug, state, args)
    local file = args.file
    if not state.hot and file ~= "_hot.md" then return nil, "Leia _hot.md primeiro." end
    if state.hot and not state.voice and file ~= "voice.md" then return nil, "Leia voice.md em seguida." end
    local optional = { ["principles.md"] = true, ["frameworks.md"] = true, ["books.md"] = true, ["positions.md"] = true, ["stories.md"] = true }
    if file ~= "_hot.md" and file ~= "voice.md" and file ~= "sources.md" and not optional[file] then return nil, "Arquivo não permitido." end
    if optional[file] and not state.files[file] and state.count >= 2 then return nil, "Limite de dois arquivos adicionais." end
    if file == "sources.md" and not text(args.query, 200) then return nil, "Informe trecho literal específico em query." end
    local content = maki.fs.read(ROOT .. "brains/" .. slug .. "/" .. file)
    if not content then return nil, "Leitura indisponível." end
    if file == "_hot.md" then state.hot = true end
    if file == "voice.md" then state.voice = true end
    if optional[file] and not state.files[file] then state.count = state.count + 1; state.files[file] = true end
    if file == "sources.md" then
        local lines, matches = {}, {}
        for line in (content .. "\n"):gmatch("(.-)\n") do lines[#lines + 1] = line end
        for i, line in ipairs(lines) do
            if line:lower():find(args.query:lower(), 1, true) then
                for j = math.max(1, i - 2), math.min(#lines, i + 8) do matches[#matches + 1] = lines[j] end
            end
        end
        content = table.concat(matches, "\n")
        if #content == 0 or #content > 24000 then return nil, "Consulta sem entrada ou ampla demais; refine query." end
        state.sources = true
    end
    return content
end
local function valid_result(raw, state)
    if type(raw) ~= "string" or #raw > 32000 then return nil end
    local ok, result = pcall(maki.json.decode, raw)
    if not ok or type(result) ~= "table" or not state.hot or not state.voice then return nil end
    if type(result.uses_brain_sources) ~= "boolean" or (result.uses_brain_sources and not state.sources) then return nil end
    if not text(result.text, 6000) or not text(result.recommendation, 6000) or not text(result.evidence, 6000) or not text(result.disagreements, 6000) then return nil end
    if type(result.confidence) ~= "number" or result.confidence ~= result.confidence or result.confidence < 0 or result.confidence > 1 then return nil end
    if #maki.json.encode(result) > 6000 then return nil end
    return { text = result.text, confidence = result.confidence, evidence = result.evidence, recommendation = result.recommendation, disagreements = result.disagreements }
end
local function analyze(ctx, r, slug, phase, links, arguments)
    local state = { files = {}, count = 0 }
    local session, cancelled, permit
    local function release()
        local held = permit
        permit = nil
        if held then held:release() end
    end
    local function close()
        local closing = session
        session = nil
        if closing then
            active[closing] = nil
            pcall(function() closing:close() end)
        end
    end
    maki.async.on_cancel(function()
        cancelled = true
        maki.defer_fn(function() close(); release() end, 0)
    end)
    local code = "error"
    local ok, result = pcall(function()
        permit = slots:acquire()
        if cancelled then return nil end
        session = maki.agent.session(ctx, {
            name = specialists[slug].name .. " " .. r.round_id .. " " .. phase,
            tools = {}, mcp = false,
            system = "Você é " .. specialists[slug].name .. ", especialidade: " .. specialists[slug].responsibility .. ". Não imite pessoas. Sem execução/escrita/pesquisa externa. Separe fatos, hipóteses e limites. Responda somente JSON com text (até 6000 caracteres), confidence (0–1), evidence (fontes/data/limites/condição de revisão), uses_brain_sources (booleano: usa afirmações fundamentadas no brain), recommendation, disagreements. Leia o brain pela ferramenta: _hot.md primeiro, voice.md na primeira atuação, no máximo dois arquivos opcionais na sessão. Se usar afirmações fundamentadas no brain, marque uses_brain_sources=true e consulte as entradas específicas de sources.md que as sustentam. Sem essas afirmações, marque false e declare explicitamente em evidence a limitação de evidências; não invente fontes. Não afirme acesso não realizado.",
            local_tools = { brain_read = {
                description = "Leitura restrita do próprio brain; sources.md exige query literal específica.",
                input_schema = { type = "object", properties = { file = { type = "string" }, query = { type = "string" } }, required = { "file" }, additionalProperties = false },
                handler = function(args) return read_brain(slug, state, args) end,
            } },
        })
        if not session then code = "unavailable"; return nil end
        active[session] = { session_id = r.session_id, cleanup = function() close(); release() end }
        local prompt = maki.json.encode({ project_id = r.project_id, title = r.title, objective = r.input.objective, context = r.input.context, restrictions = r.input.restrictions, acceptance = r.input.acceptance, scope = "Análise independente; apenas leitura do brain próprio. Sem alterações ou execução.", components = ROOT .. "brains/" .. slug .. "/", dependencies = "Somente contexto delegado e fontes locais; sem pesquisa externa disponível.", responsible = slug, validation = "JSON válido, confiança, condições de revisão e limitação explícita de evidências; fontes específicas em sources.md quando usar afirmações fundamentadas no brain", phase = phase, arguments = arguments or "Nenhuma análise alheia na primeira fase." })
        for attempt = 1, 2 do
            local response, err = session:prompt(attempt == 1 and prompt or "Retorno inválido. Complete as leituras obrigatórias e devolva somente o JSON solicitado, sem markdown.")
            if err then code = (err == "cancelled" or err == "stopped by user") and "cancelled" or "error"; return nil end
            local value = response and valid_result(response.text, state)
            if value then return value end
            code = "invalid_response"
        end
    end)
    close()
    release()
    if cancelled then code = "cancelled"; result = nil end
    if not ok or not result then return { failure = { specialist_id = slug, phase = phase, code = code } } end
    result.specialist_id = slug
    return { result = result, intervention = { intervention_id = r.round_id .. ":" .. phase .. ":" .. slug, specialist_id = slug, phase = phase, text = result.text, reply_to = array(links or {}), order = 0 } }
end
local function run_phase(ctx, r, requests, phase)
    r.busy = true
    local results, jobs = {}, {}
    for i, request in ipairs(requests) do
        local index, item = i, request
        jobs[#jobs + 1] = function() results[index] = analyze(ctx, r, item.specialist_id, phase, item.reply_to, item.arguments) end
    end
    -- Cancellation is not completion: publication must wait for join and collection.
    maki.async.on_cancel(function() r.cancelled = true end)
    local ok = pcall(maki.async.join, 3, jobs)
    for i, request in ipairs(requests) do
        local item = results[i] or { failure = { specialist_id = request.specialist_id, phase = phase, code = r.cancelled and "cancelled" or "error" } }
        if item.failure then r.failures[#r.failures + 1] = item.failure else
            item.intervention.order = #r.interventions
            r.interventions[#r.interventions + 1] = item.intervention
            r.results[#r.results + 1] = item.result
        end
    end
    r.busy = false
    return output({ round_id = r.round_id, results = array(r.results), failures = array(r.failures), status = (#r.failures > 0 or not ok) and "partial" or "ready", next_step = "Maestro: avaliar contraponto; depois sintetizar e chamar council_publish automaticamente." })
end
local function send(r)
    if r.published then return true end
    if r.sending or r.attempts >= 3 then return false end
    r.sending = true; r.attempts = r.attempts + 1
    local conn, timer, stopped, finished
    local function close_connection()
        if conn then
            local closing = conn
            conn = nil
            pcall(function() closing:close() end)
        end
    end
    local function cleanup()
        finished = true
        -- defer_fn returns a maki.Timer; :stop() cancels a pending callback.
        if timer then timer:stop(); timer = nil end
        close_connection()
        r.sending = false
    end
    maki.async.on_cancel(function() stopped = true; cleanup() end)
    local ok, success = pcall(function()
        local token = maki.fs.read(ROOT .. "apps/voice/data/bridge-token")
        if not token or not token:match("^[A-Za-z0-9_%-]+$") or #token > 512 then return false end
        timer = maki.defer_fn(function()
            if finished then return end
            stopped = true
            close_connection()
        end, 15000)
        conn = maki.net.connect("127.0.0.1", 8765, { timeout = 5 })
        if not conn or stopped then return false end
        local written = conn:write("POST /api/rounds HTTP/1.1\r\nHost: 127.0.0.1:8765\r\nAuthorization: Bearer " .. token .. "\r\nContent-Type: application/json\r\nContent-Length: " .. #r.body .. "\r\nConnection: close\r\n\r\n" .. r.body)
        token = nil
        if not written or stopped then return false end
        local response, header_end, length = "", nil, nil
        while not stopped do
            local chunk, err = conn:read()
            if err then return false end
            if not chunk then break end
            response = response .. chunk
            if #response > MAX + 8192 then return false end
            header_end = response:find("\r\n\r\n", 1, true)
            if not header_end and #response > 8192 then return false end
            if header_end then
                if header_end > 8192 then return false end
                local headers = response:sub(1, header_end):lower()
                if headers:find("transfer%-encoding:") then return false end
                length = tonumber(headers:match("\r\ncontent%-length:%s*(%d+)"))
                if not length or length > MAX then return false end
                if #response >= header_end + 3 + length then break end
            end
        end
        local status = tonumber(response:match("^HTTP/1%.[01] (%d%d%d) "))
        return not stopped and header_end and length and #response == header_end + 3 + length and status and status >= 200 and status < 300
    end)
    cleanup()
    if ok and success then r.published = true; return true end
    return false
end
local function register(name, description, properties, required, handler, timeout)
    maki.api.register_tool({ name = name, description = description, audiences = { "main" }, timeout = timeout or 300, schema = { type = "object", properties = properties, required = required, additionalProperties = false }, handler = handler })
end
local string_schema = { type = "string" }
register("council_consult", "Abra rodada com especialistas selecionados reais; retorne análises independentes. Maestro deve sintetizar e publicar ao terminar.", {
    project_id = string_schema, title = string_schema, objective = string_schema, context = string_schema, restrictions = string_schema, acceptance = string_schema,
    specialists = { type = "array", minItems = 1, maxItems = 9, uniqueItems = true, items = string_schema },
}, { "project_id", "title", "objective", "context", "restrictions", "acceptance", "specialists" }, function(input, ctx)
    local sid = owner(ctx)
    if not sid or not identifier(input.project_id) or not text(input.title, 200) then return output("Projeto/título/sessão inválidos.", true) end
    for _, key in ipairs({ "objective", "context", "restrictions", "acceptance" }) do if not text(input[key], 12000) then return output("Campo inválido: " .. key, true) end end
    if type(input.specialists) ~= "table" or #input.specialists < 1 or #input.specialists > 9 then return output("Selecione 1–9 especialistas.", true) end
    if not load_specialists() then return output("Catálogo de especialistas indisponível ou inválido.", true) end
    local seen, requests = {}, {}
    for _, slug in ipairs(input.specialists) do
        if slug == "maestro" or not specialists[slug] or seen[slug] then return output("Especialista inválido/duplicado.", true) end
        seen[slug] = true; requests[#requests + 1] = { specialist_id = slug }
    end
    if #maki.json.encode(input) > 32000 then return output("Contexto delegado excede 32000 bytes.", true) end
    purge()
    local used = 0
    -- Reserve 256 KiB throughout each round's lifetime, including frozen rounds:
    -- body plus rationale/metadata (or input/results before freezing). Never shrink
    -- accounting to body size alone: retained rationale is extra to the envelope.
    for _ in pairs(rounds) do
        used = used + 256 * 1024
    end
    if #order >= 20 or used + 256 * 1024 > 20 * MAX then return output("Buffer volátil cheio; aguarde expiração ou encerre a sessão.", true) end
    sequence = sequence + 1
    local id = "council-" .. epoch .. "-" .. sequence
    local r = { round_id = id, project_id = input.project_id, title = input.title, session_id = sid, input = input, created = os.time(), interventions = {}, failures = {}, results = {}, attempts = 0 }
    rounds[id] = r; order[#order + 1] = id
    return run_phase(ctx, r, requests, "analysis")
end)
register("council_counterpoint", "Uma única etapa de contraponto: até dois autores de análises reais respondem a análises anteriores com autoria explícita.", {
    round_id = string_schema, participants = { type = "array", minItems = 1, maxItems = 2, items = { type = "object", properties = { specialist_id = string_schema, reply_to = { type = "array", minItems = 1, maxItems = 9, items = string_schema }, argument = string_schema }, required = { "specialist_id", "reply_to", "argument" }, additionalProperties = false } },
}, { "round_id", "participants" }, function(input, ctx)
    local r = lookup(input.round_id, owner(ctx))
    if not r or r.busy or r.body or r.counterpoint or r.cancelled then return output("Rodada indisponível para contraponto.", true) end
    if type(input.participants) ~= "table" or #input.participants < 1 or #input.participants > 2 then return output("Selecione 1–2 participantes.", true) end
    local analyses, authors, seen, requests = {}, {}, {}, {}
    for _, item in ipairs(r.interventions) do analyses[item.intervention_id] = item; authors[item.specialist_id] = true end
    for _, p in ipairs(input.participants) do
        if not authors[p.specialist_id] or seen[p.specialist_id] or not text(p.argument, 6000) or type(p.reply_to) ~= "table" or #p.reply_to < 1 or #p.reply_to > 9 then return output("Contraponto inválido.", true) end
        local links, targets = {}, {}
        for _, id in ipairs(p.reply_to) do
            if not analyses[id] or links[id] then return output("reply_to inválido/duplicado.", true) end
            links[id] = true; targets[#targets + 1] = analyses[id]
        end
        seen[p.specialist_id] = true
        requests[#requests + 1] = { specialist_id = p.specialist_id, reply_to = p.reply_to, arguments = { direction = p.argument, original = targets } }
    end
    r.counterpoint = true
    return run_phase(ctx, r, requests, "counterpoint")
end)
register("council_publish", "Conclua automaticamente com síntese fiel do Maestro. Publica apenas intervenções reais armazenadas; sem contraponto exige justificativa explícita. Falha mantém texto no Maki; /conclave-retry reenvia sem inferência.", { round_id = string_schema, synthesis = string_schema, counterpoint_not_needed_reason = string_schema }, { "round_id", "synthesis" }, function(input, ctx)
    local r = lookup(input.round_id, owner(ctx))
    if not r or r.busy then return output("Rodada indisponível.", true) end
    if not r.body then
        if not text(input.synthesis, 6000) then return output("Síntese inválida.", true) end
        if not r.counterpoint and not text(input.counterpoint_not_needed_reason, 2000) then return output("Explique por que contraponto não é necessário.", true) end
        local envelope = { schema_version = 1, round_id = r.round_id, project_id = r.project_id, title = r.title, session_id = r.session_id, status = (#r.failures > 0 or #r.interventions == 0) and "partial" or "complete", interventions = array(r.interventions), failures = array(r.failures), synthesis = { intervention_id = r.round_id .. ":synthesis", specialist_id = "maestro", phase = "synthesis", text = input.synthesis, reply_to = array({}), order = #r.interventions } }
        local body = maki.json.encode(envelope)
        if #body > MAX then return output("Envelope excede 128 KiB; sem truncamento.", true) end
        r.body = body; r.rationale = input.counterpoint_not_needed_reason
        r.input = nil; r.results = nil; r.interventions = nil; r.failures = nil
    end
    local sent = send(r)
    return output({ round_id = r.round_id, published = sent, counterpoint_not_needed_reason = r.rationale, envelope = maki.json.decode(r.body), notice = sent and "Texto publicado; áudio exige clique na mesa web." or "Ponte indisponível; texto preservado no Maki. /conclave-retry; buffer volátil." }, not sent)
end, 20)
maki.api.register_prompt_hint({ slot = "tool_usage", content = "Você é Maestro, coordenador independente do Conclave. Use council_consult apenas quando pertinente, com contexto mínimo e aceite explícito. Compare divergências reais, sem votos. council_counterpoint é opcional e limitado a uma etapa; sem ele registre justificativa. Após retornos efetivos, sintetize convergências, divergências, incertezas e próximo passo, indicando falhas/parcialidade; chame council_publish automaticamente sem novo pedido do usuário. Não invente pareceres, pesquisa ou testes live. Subagentes usam provedor configurado; somente TTS é local. Texto permanece no Maki se ponte falhar; áudio sempre exige clique." })
maki.api.register_command({ name = "/conclave-status", description = "Pendências voláteis desta sessão.", handler = function()
    purge()
    local sid, lines = maki.session.current(), {}
    for _, id in ipairs(order) do local r = rounds[id]; if r.session_id == sid then lines[#lines + 1] = id .. ": " .. (r.published and "publicada" or r.body and "reenvio pendente" or "síntese/publicação pendente") end end
    maki.notify(#lines > 0 and table.concat(lines, "\n") or "Sem rodadas nesta sessão.")
end })
maki.api.register_command({ name = "/conclave-retry", nargs = 1, description = "Reenvie ID concluído desta sessão, sem nova inferência (máximo três envios).", handler = function(opts)
    local r = lookup(opts.args, maki.session.current())
    if not r or not r.body then maki.notify("Rodada concluída não encontrada nesta sessão."); return end
    maki.async.run(function() maki.notify(send(r) and "Rodada publicada; reprodução manual." or "Reenvio indisponível; texto preservado no Maki.") end)
end })
maki.api.create_autocmd("TurnEnd", { callback = function(ev)
    for _, r in pairs(rounds) do if r.session_id == ev.data.session_id and not r.published then maki.notify("Conclave: síntese/publicação pendente; /conclave-status. Buffer volátil."); break end end
end })
maki.api.create_autocmd("SessionEnd", { callback = function(ev)
    local sid, pending = ev.data.session_id, false
    for _, entry in pairs(active) do if entry.session_id == sid then entry.cleanup() end end
    for id, r in pairs(rounds) do if r.session_id == sid then pending = pending or not r.published; rounds[id] = nil end end
    purge()
    if pending then maki.notify("Conclave: pendências voláteis descartadas ao encerrar/recarregar; texto já retornado permanece no Maki.") end
end })
return {}
