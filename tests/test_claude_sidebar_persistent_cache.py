import json

def test_restart_index_avoids_parse_but_detects_edits(tmp_path, monkeypatch):
    from api import models
    root=tmp_path/"claude";project=root/"p";project.mkdir(parents=True)
    source=project/"s.jsonl"
    source.write_text(json.dumps({"message":{"role":"user","content":"first"}})+"\n")
    monkeypatch.setattr(models._cfg,"STATE_DIR",tmp_path/"state")
    monkeypatch.setattr(models,"get_last_workspace",lambda:tmp_path)
    original=models._parse_claude_code_jsonl
    calls=[]
    def parse(*a,**kw):calls.append(1);return original(*a,**kw)
    monkeypatch.setattr(models,"_parse_claude_code_jsonl",parse)
    first=models.get_claude_code_sessions(root)
    models.clear_claude_code_parse_cache()  # model fresh process-local state
    second=models.get_claude_code_sessions(root)
    assert first==second and len(calls)==1
    cache=tmp_path/"state/claude-sidebar-index.json"
    assert cache.stat().st_mode & 0o777 == 0o600
    data=json.loads(cache.read_text())
    assert all(set(entry["row"])=={"title","message_count","first_ts","last_ts"} for entry in data["entries"].values())
    source.write_text(json.dumps({"message":{"role":"user","content":"second changed"}})+"\n")
    assert models.get_claude_code_sessions(root)[0]["title"]=="second changed"
    assert len(calls)==2
    source.unlink()
    assert models.get_claude_code_sessions(root)==[]

def test_corrupt_index_is_disposable(tmp_path, monkeypatch):
    from api import models
    root=tmp_path/"claude";project=root/"p";project.mkdir(parents=True)
    (project/"s.jsonl").write_text(json.dumps({"message":{"role":"user","content":"retained"}})+"\n")
    state=tmp_path/"state";state.mkdir()
    (state/"claude-sidebar-index.json").write_text("not json")
    monkeypatch.setattr(models._cfg,"STATE_DIR",state)
    monkeypatch.setattr(models,"get_last_workspace",lambda:tmp_path)
    assert models.get_claude_code_sessions(root)[0]["title"]=="retained"


def test_concurrent_sidebar_build_parses_once(tmp_path, monkeypatch):
    from api import models
    from concurrent.futures import ThreadPoolExecutor
    import time
    root=tmp_path/"claude";project=root/"p";project.mkdir(parents=True)
    (project/"s.jsonl").write_text(json.dumps({"message":{"role":"user","content":"shared"}})+"\n")
    monkeypatch.setattr(models._cfg,"STATE_DIR",tmp_path/"state")
    monkeypatch.setattr(models,"get_last_workspace",lambda:tmp_path)
    original=models._parse_claude_code_jsonl;calls=[]
    def parse(*a,**kw):
        calls.append(1);time.sleep(.03);return original(*a,**kw)
    monkeypatch.setattr(models,"_parse_claude_code_jsonl",parse)
    with ThreadPoolExecutor(max_workers=8) as workers:
        results=list(workers.map(lambda _:models.get_claude_code_sessions(root),range(8)))
    assert len(calls)==1 and all(row==results[0] for row in results)
