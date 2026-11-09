import importlib.util
import json
import os
import stat
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "apps/voice/maki"
SPEC = importlib.util.spec_from_file_location("install_plugin", ROOT / "apps/voice/install_plugin.py")
INSTALLER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(INSTALLER)


def test_installer_idempotent_and_refuses_unvalidated_config(tmp_path):
    assert len(INSTALLER.install(tmp_path)) == 3
    assert INSTALLER.install(tmp_path) == []
    init = tmp_path / ".maki/init.lua"
    init.write_text("custom setup", encoding="utf-8")
    with pytest.raises(ValueError, match="integração manual"):
        INSTALLER.install(tmp_path)
    assert init.read_text() == "custom setup"


def test_installer_rejects_broad_permissions_before_copy(tmp_path):
    target = tmp_path / ".maki"
    target.mkdir()
    (target / "plugin.toml").write_text("[permissions]\nrun = true\n")
    with pytest.raises(ValueError, match="Permissões"):
        INSTALLER.install(tmp_path)
    assert not (target / "lua/conclave.lua").exists()


@pytest.fixture
def runtime():
    lupa = pytest.importorskip("lupa")
    lua = lupa.LuaRuntime(unpack_returned_tuples=True)

    def to_lua(value):
        if isinstance(value, dict):
            return lua.table_from({key: to_lua(item) for key, item in value.items()})
        if isinstance(value, list):
            return lua.table_from([to_lua(item) for item in value])
        return value

    def to_python(value):
        if lupa.lua_type(value) == "table":
            pairs = list(value.items())
            if not pairs:
                return []
            if all(isinstance(key, int) for key, _ in pairs):
                return [to_python(value[i]) for i in range(1, len(pairs) + 1)]
            return {key: to_python(item) for key, item in pairs}
        return value

    lua.globals().json_encode = lambda value: json.dumps(to_python(value), ensure_ascii=False)
    lua.globals().json_decode = lambda value: to_lua(json.loads(value))
    lua.globals().catalog_text = (ROOT / "apps/voice/catalog.json").read_text(encoding="utf-8")
    lua.execute('''
        tools, commands, events, reads, sessions, requests, hooks = {}, {}, {}, {}, {}, {}, {}
        mode, current, transport = "valid", "session-a", "ok"
        clock, permits_acquired, permits_released = 100000, 0, 0
        os.time = function() return clock end
        loading, catalog_reads, catalog_mode, timers = true, 0, "ok", {}
        maki = {
            json = {encode = json_encode, decode = json_decode},
            fs = {read = function(path)
                assert(not loading, "filesystem I/O during require")
                if path:find("catalog.json", 1, true) then
                    catalog_reads = catalog_reads + 1
                    if catalog_mode == "missing" then return nil, "missing" end
                    if catalog_mode == "invalid" then return "{" end
                    if catalog_mode == "shape" then return '{}' end
                    return catalog_text
                end
                if path:find("bridge-token", 1, true) then return "private_token" end
                reads[#reads+1] = path
                return "entry evidence source\\n2026 factual limits"
            end},
            api = {
                register_tool = function(spec) tools[spec.name] = spec end,
                register_command = function(spec) commands[spec.name] = spec end,
                register_prompt_hint = function(spec) hint = spec.content end,
                create_autocmd = function(event, spec) events[event] = spec.callback end,
            },
            session = {current = function() return current end},
            notify = function(message) notice = message end,
            defer_fn = function(callback, ms)
                local timer = {stopped=false, delay=ms}
                function timer:stop() self.stopped = true end
                function timer:fire() if not self.stopped then callback() end end
                timers[#timers+1] = timer
                timer_callback = function() timer:fire() end
                if ms == 0 then timer:fire() end
                return timer
            end,
            async = {
                semaphore = function(n)
                    assert(n == 3)
                    return {acquire=function()
                        permits_acquired = permits_acquired + 1
                        local released = false
                        return {release=function()
                            assert(not released, "double permit release")
                            released = true
                            permits_released = permits_released + 1
                        end}
                    end}
                end,
                on_cancel = function(callback) hooks[#hooks+1] = callback end,
                join = function(limit, jobs) concurrency = limit; for _, job in ipairs(jobs) do job() end end,
                run = function(fn) fn() end,
                spawn = function(fn)
                    sweeper = {thread=coroutine.create(fn), fn=fn, cancelled=false}
                    function sweeper:tick()
                        if self.cancelled then return end
                        local ok, delay = coroutine.resume(self.thread)
                        assert(ok, delay)
                        assert(delay == 30000)
                    end
                    function sweeper:cancel() self.cancelled = true end
                    return sweeper
                end,
                sleep = function(ms) assert(not loading); coroutine.yield(ms) end,
            },
            agent = {session = function(ctx, opts)
                assert(opts.mcp == false and #opts.tools == 0 and opts.model_spec == nil)
                assert(opts.local_tools.brain_read and opts.local_tools.batch == nil)
                local s = {closed = false, calls = 0, opts = opts}
                function s:close()
                    assert(not self.closed, "double session close")
                    self.closed = true
                end
                function s:prompt(message)
                    self.calls = self.calls + 1
                    if mode == "session_end" then
                        events.SessionEnd({data={session_id=current}})
                        return nil, "cancelled"
                    end
                    if mode == "throw" then error("provider failure") end
                    if mode == "cancel" then for _, h in ipairs(hooks) do h("cancelled") end; return {text="partial"}, "cancelled" end
                    local read = opts.local_tools.brain_read.handler
                    if self.calls == 1 then assert(read({file="books.md"}) == nil) end
                    assert(read({file="../../data/bridge-token"}) == nil)
                    if mode ~= "no_hot" then read({file="_hot.md"}) end
                    if mode ~= "no_voice" then read({file="voice.md"}) end
                    local uses_sources = mode ~= "limited" and mode ~= "limited_reads_sources"
                    if mode ~= "missing_sources" and mode ~= "limited" then read({file="sources.md", query="evidence"}) end
                    if mode == "invalid" or (mode == "retry" and self.calls == 1) then return {text="invalid"} end
                    return {text=json_encode({text="Real analysis", confidence=0.8, evidence=uses_sources and "entry evidence source; local only" or "No sourced brain claims; evidence limited to delegated context; review with external research.", uses_brain_sources=uses_sources, recommendation="Review", disagreements="None"})}
                end
                sessions[#sessions+1] = s
                return s
            end},
            net = {connect = function(host, port, opts)
                assert(host == "127.0.0.1" and port == 8765 and opts.timeout == 5)
                if transport == "connect" then return nil, "denied" end
                if transport == "connect_timeout" then timer_callback() end
                local c = {closed=false}
                connection = c
                function c:close() self.closed = true end
                function c:write(request)
                    requests[#requests+1] = request
                    if transport == "write" then error("private error") end
                    if transport == "write_timeout" then timer_callback(); return nil, "closed" end
                    return true
                end
                function c:read()
                    if self.read_done then return nil end
                    self.read_done = true
                    if transport == "timeout" then timer_callback(); return nil, "closed" end
                    if transport == "cancel" then for _, h in ipairs(hooks) do h("cancelled") end; return nil, "cancelled" end
                    if transport == "oversize" then return "HTTP/1.1 200 OK\\r\\nContent-Length: 131073\\r\\n\\r\\n" end
                    if transport == "status" then return "HTTP/1.1 503 Error\\r\\nContent-Length: 2\\r\\n\\r\\n{}" end
                    return "HTTP/1.1 201 Created\\r\\nContent-Length: 2\\r\\n\\r\\n{}"
                end
                return c
            end},
        }
        ctx = {session_id=function() return current end, task_id=function() return "main" end}
    ''')
    lua.execute((SOURCE / "conclave.lua").read_text(encoding="utf-8"))
    lua.execute("loading = false")

    def call(name, args):
        lua.execute("hooks = {}")
        result = lua.globals().tools[name].handler(to_lua(args), lua.globals().ctx)
        raw = result.llm_output
        try:
            return json.loads(raw), result.is_error
        except json.JSONDecodeError:
            return raw, result.is_error

    return lua, call


def consult(call, specialists=None):
    value, error = call("council_consult", dict(project_id="QG-BRAINS-01", title="Review", objective="Inspect", context="Internal", restrictions="Read only", acceptance="Evidence", specialists=specialists or ["hater"]))
    assert not error
    return value


def publish(call, round_id):
    return call("council_publish", dict(round_id=round_id, synthesis="Main Maestro synthesis", counterpoint_not_needed_reason="No material disagreement"))


@pytest.mark.parametrize("mode,expected,calls", [("valid", None, 1), ("retry", None, 2), ("invalid", "invalid_response", 2), ("throw", "error", 1), ("cancel", "cancelled", 1)])
def test_real_sessions_close_all_paths(runtime, mode, expected, calls):
    lua, call = runtime
    lua.globals().mode = mode
    value = consult(call)
    assert lua.globals().sessions[1].closed
    assert lua.globals().sessions[1].calls == calls
    assert lua.globals().concurrency == 3
    if expected:
        assert value["failures"][0]["code"] == expected
        assert value["results"] == []
    else:
        assert value["results"][0]["text"] == "Real analysis"


def test_publish_actual_envelope_idempotent_and_owned(runtime):
    lua, call = runtime
    value = consult(call)
    rid = value["round_id"]
    lua.globals().current = "session-b"
    assert publish(call, rid)[1]
    lua.globals().current = "session-a"
    result, error = publish(call, rid)
    assert not error and result["published"]
    request = lua.globals().requests[1]
    envelope = json.loads(request.split("\r\n\r\n", 1)[1])
    assert envelope["interventions"][0]["text"] == "Real analysis"
    assert "counterpoint_not_needed_reason" not in envelope
    assert "private_token" not in json.dumps(result)
    assert lua.globals().connection.closed
    assert publish(call, rid)[0]["published"]
    assert len(lua.globals().requests) == 1


@pytest.mark.parametrize("transport", ["write", "write_timeout", "status", "oversize", "timeout", "connect_timeout", "cancel", "connect"])
def test_transport_errors_close_and_retry_without_inference(runtime, transport):
    lua, call = runtime
    rid = consult(call)["round_id"]
    lua.globals().transport = transport
    result, error = publish(call, rid)
    assert error and not result["published"]
    if transport != "connect":
        assert lua.globals().connection.closed
    lua.globals().transport = "ok"
    result, error = publish(call, rid)
    assert not error and result["published"]
    assert len(lua.globals().sessions) == 1


def test_counterpoint_links_one_phase_and_deterministic_order(runtime):
    lua, call = runtime
    rid = consult(call, ["hater", "tio-patinhas"])["round_id"]
    args = dict(round_id=rid, participants=[dict(specialist_id="hater", reply_to=[rid + ":analysis:tio-patinhas"], argument="Review cost")])
    assert not call("council_counterpoint", args)[1]
    assert call("council_counterpoint", args)[1]
    result, _ = publish(call, rid)
    items = result["envelope"]["interventions"]
    assert [item["specialist_id"] for item in items] == ["hater", "tio-patinhas", "hater"]
    assert [item["order"] for item in items] == [0, 1, 2]
    assert all(lua.globals().sessions[i].closed for i in range(1, 4))


def test_read_scope_sequence_optional_limit_and_sources_targeting(runtime):
    lua, call = runtime
    consult(call)
    read = lua.globals().sessions[1].opts.local_tools.brain_read.handler
    assert read(lua.table_from({"file": "../../data/bridge-token"}))[0] is None
    for name in ["books.md", "principles.md"]:
        assert isinstance(read(lua.table_from({"file": name})), str)
    assert read(lua.table_from({"file": "frameworks.md"}))[0] is None
    assert read(lua.table_from({"file": "sources.md"}))[0] is None
    assert all("brains/hater/" in lua.globals().reads[i] for i in range(1, len(lua.globals().reads) + 1))
    assert lua.globals().reads[1].endswith("/_hot.md")
    assert lua.globals().reads[2].endswith("/voice.md")


def test_cleanup_and_partial_status(runtime):
    lua, call = runtime
    lua.globals().mode = "invalid"
    rid = consult(call)["round_id"]
    result, _ = publish(call, rid)
    assert result["envelope"]["status"] == "partial"
    assert result["envelope"]["interventions"] == []
    lua.execute('events.SessionEnd({data={session_id="session-a", reason="reload"}})')
    assert publish(call, rid)[1]


def test_retry_budget_rationale_and_unknown_links(runtime):
    lua, call = runtime
    rid = consult(call)["round_id"]
    assert call("council_publish", dict(round_id=rid, synthesis="Summary"))[1]
    args = dict(round_id=rid, participants=[dict(specialist_id="hater", reply_to=["unknown"], argument="Review")])
    assert call("council_counterpoint", args)[1]
    lua.globals().transport = "status"
    for _ in range(4):
        assert publish(call, rid)[1]
    assert len(lua.globals().requests) == 3
    assert len(lua.globals().sessions) == 1


def test_load_defers_catalog_io_and_caches_at_tool_runtime(runtime):
    lua, call = runtime
    assert lua.globals().catalog_reads == 0
    assert lua.globals().tools.council_consult is not None
    consult(call)
    consult(call)
    assert lua.globals().catalog_reads == 1


@pytest.mark.parametrize("catalog_mode", ["missing", "invalid", "shape"])
def test_catalog_failure_is_recoverable_tool_error(runtime, catalog_mode):
    lua, call = runtime
    lua.globals().catalog_mode = catalog_mode
    args = dict(project_id="QG-BRAINS-01", title="Review", objective="Inspect", context="Internal", restrictions="Read only", acceptance="Evidence", specialists=["hater"])
    result, error = call("council_consult", args)
    assert error and "Catálogo" in result
    assert len(lua.globals().sessions) == 0
    lua.globals().catalog_mode = "ok"
    assert consult(call)["results"]


@pytest.mark.parametrize("mode,valid", [("limited", True), ("limited_reads_sources", True), ("missing_sources", False), ("no_hot", False), ("no_voice", False)])
def test_evidence_limit_and_conditional_sources_preserve_required_reads(runtime, mode, valid):
    lua, call = runtime
    lua.globals().mode = mode
    value = consult(call)
    assert bool(value["results"]) == valid
    if valid:
        assert "evidence limited" in value["results"][0]["evidence"]
    else:
        assert value["failures"][0]["code"] == "invalid_response"
    if mode == "limited":
        assert len(lua.globals().reads) == 2


@pytest.mark.parametrize("transport", ["ok", "write", "connect", "timeout", "cancel"])
def test_transport_timer_is_stopped_and_late_callback_is_harmless(runtime, transport):
    lua, call = runtime
    rid = consult(call)["round_id"]
    lua.globals().transport = transport
    publish(call, rid)
    timer = lua.globals().timers[len(lua.globals().timers)]
    assert timer.delay == 15000 and timer.stopped
    lua.execute("timer_callback()")
    lua.globals().transport = "ok"
    assert publish(call, rid)[0]["published"]


def test_session_capacity_is_bounded(runtime):
    _, call = runtime
    for _ in range(10):
        consult(call)
    _, error = call("council_consult", dict(project_id="QG-BRAINS-01", title="Review", objective="Inspect", context="Internal", restrictions="Read only", acceptance="Evidence", specialists=["hater"]))
    assert error


@pytest.mark.parametrize("component", [".maki", ".maki/lua", ".maki/init.lua", ".maki/plugin.toml", ".maki/lua/conclave.lua"])
def test_installer_rejects_reparse_components_before_target_read(tmp_path, monkeypatch, component):
    INSTALLER.install(tmp_path)
    blocked = tmp_path / component
    original_stat = Path.lstat
    original_read = Path.read_bytes

    def reparse_stat(path, *args, **kwargs):
        result = original_stat(path, *args, **kwargs)
        if path == blocked:
            return SimpleNamespace(st_mode=result.st_mode, st_file_attributes=stat.FILE_ATTRIBUTE_REPARSE_POINT)
        return result

    def guarded_read(path):
        assert not path.is_relative_to(tmp_path / ".maki"), "target read before validation"
        return original_read(path)

    monkeypatch.setattr(Path, "lstat", reparse_stat)
    monkeypatch.setattr(Path, "read_bytes", guarded_read)
    with pytest.raises(ValueError, match="reparse"):
        INSTALLER.install(tmp_path)


@pytest.mark.skipif(os.name != "nt", reason="Windows junction regression")
@pytest.mark.parametrize("component", [".maki", ".maki/lua"])
def test_installer_rejects_real_windows_junction(tmp_path, component):
    project, outside = tmp_path / "project", tmp_path / "outside"
    project.mkdir()
    outside.mkdir()
    junction = project / component
    junction.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["cmd", "/c", "mklink", "/J", str(junction), str(outside)], check=True, capture_output=True)
    try:
        with pytest.raises(ValueError, match="reparse"):
            INSTALLER.install(project)
        assert list(outside.iterdir()) == []
    finally:
        junction.rmdir()


def test_cancel_cannot_freeze_round_before_join_collection(runtime):
    lua, call = runtime
    lua.execute('''
        local join = maki.async.join
        maki.async.join = function(limit, jobs)
            join(limit, {jobs[1]})
            mode = "cancel"
            join(limit, {jobs[2]})
            local rid = sessions[1].opts.name:match("(council-%S+) analysis")
            during_cancel = tools.council_publish.handler({round_id=rid, synthesis="Too early", counterpoint_not_needed_reason="None"}, ctx)
        end
    ''')
    result = consult(call, ["hater", "tio-patinhas"])
    assert lua.globals().during_cancel.is_error
    assert result["status"] == "partial"
    assert len(result["results"]) == 1
    assert result["failures"][0]["code"] == "cancelled"
    published, error = publish(call, result["round_id"])
    assert not error
    assert len(published["envelope"]["interventions"]) == 1
    assert len(published["envelope"]["failures"]) == 1
    assert lua.globals().permits_acquired == lua.globals().permits_released == 2


def test_session_end_and_final_cleanup_close_release_once(runtime):
    lua, call = runtime
    lua.globals().mode = "session_end"
    consult(call)
    assert lua.globals().sessions[1].closed
    assert lua.globals().permits_acquired == lua.globals().permits_released == 1


@pytest.mark.parametrize("published", [False, True])
def test_periodic_ttl_purges_without_tool_activity_and_stops_on_unload(runtime, published):
    lua, call = runtime
    rid = consult(call)["round_id"]
    if published:
        publish(call, rid)
    lua.execute("sweeper:tick(); clock = clock + 7200; sweeper:tick()")
    assert lua.eval('''function()
        for i=1,20 do
            local name, fn = debug.getupvalue(sweeper.fn, i)
            if name == "purge" then
                for j=1,20 do
                    local key, value = debug.getupvalue(fn, j)
                    if key == "rounds" then return next(value) == nil end
                end
            end
            if not name then break end
        end
        return false
    end''')()
    assert publish(call, rid)[1]
    lua.execute("sweeper:cancel(); sweeper:tick()")
    assert lua.globals().sweeper.cancelled


def test_frozen_rounds_keep_fixed_reservation_including_rationale(runtime):
    lua, call = runtime
    for _ in range(10):
        rid = consult(call)["round_id"]
        result, error = call("council_publish", dict(round_id=rid, synthesis="Summary", counterpoint_not_needed_reason="é" * 2000))
        assert not error and result["counterpoint_not_needed_reason"] == "é" * 2000
    args = dict(project_id="QG-BRAINS-01", title="Review", objective="Inspect", context="Internal", restrictions="Read only", acceptance="Evidence", specialists=["hater"])
    assert call("council_consult", args)[1]
    lua.execute("clock = clock + 7200")
    assert not call("council_consult", args)[1]
