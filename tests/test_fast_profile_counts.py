import time
from types import SimpleNamespace


def test_fast_counts_queue_once_and_revalidate_freshness(tmp_path, monkeypatch):
    from api import profiles as p
    starts=[]
    monkeypatch.setattr(p,"_FAST_SKILL_QUEUE",[])
    monkeypatch.setattr(p,"_FAST_SKILL_PENDING",set())
    monkeypatch.setattr(p,"_FAST_SKILL_WORKER_RUNNING",False)
    monkeypatch.setattr(p,"_SKILLS_STATS_CACHE",{})
    monkeypatch.setattr(p.threading,"Thread",lambda **kw:SimpleNamespace(start=lambda:starts.append(kw)))
    monkeypatch.setattr(p,"_skill_tree_max_mtime_ns",lambda *a:5)
    for _ in range(8):assert p._list_skill_stats(tmp_path)==(None,None)
    assert len(starts)==1 and len(p._FAST_SKILL_QUEUE)==1
    p._SKILLS_STATS_CACHE[tmp_path]=(3,4,5,time.time()+60)
    assert p._list_skill_stats(tmp_path)==(3,4)
    monkeypatch.setattr(p,"_skill_tree_max_mtime_ns",lambda *a:6)
    assert p._list_skill_stats(tmp_path)==(None,None)


def test_fast_list_keeps_isolation_and_does_not_use_full_cache(monkeypatch,tmp_path):
    from api import profiles as p
    seen=[]
    monkeypatch.setattr(p,"_is_isolated_profile_mode",lambda:True)
    monkeypatch.setattr(p,"_isolated_profile_name",lambda:"one")
    monkeypatch.setattr(p,"_INITIAL_HERMES_HOME",str(tmp_path))
    def rows(**kw):
        seen.append(kw)
        return [{"name":"one","skill_count":None,"enabled_skills":None,"total_skills":None,"skill_counts_pending":True}]
    monkeypatch.setattr(p,"_build_profile_rows_fast",rows)
    result=p.list_profiles_api(fast=True)
    assert seen==[{"deferred_counts":True,"isolated":(tmp_path,"one"),"include_skill_counts":True}]
    assert result[0]["is_active"] and result[0]["skill_count"] is None
