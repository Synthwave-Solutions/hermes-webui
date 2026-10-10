"""Current per-person banks remain private even when another viewer is an admin."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent / "fixtures" / "memdash"))
import memdash_harness as H
from api import config, personal_context


def test_current_personal_bank_is_primary_and_foreign_admin_gets_404(monkeypatch, tmp_path):
    env = H.Env(monkeypatch, tmp_path)
    monkeypatch.setattr(config, "STATE_DIR", env.state)
    try:
        for email, count in [(H.MICHAEL, 4), (H.YASER, 2)]:
            path = personal_context.home({"email": email}) / "mnemosyne" / "private.db"
            H.make_bank(path, owner=email.split("@")[0], memories=count)
        env.as_user(H.MICHAEL)
        banks = env.banks()
        primary = next(s for s in banks["stores"] if s["ref"] == banks["me"])
        assert primary["label"] == "Personal memories"
        assert env.view("me", "stats").body["counts"]["working_memory"] == 4
        private_ref = primary["ref"]
        env.as_user(H.YASER)
        assert private_ref not in {s["ref"] for s in env.banks()["stores"]}
        assert env.view(private_ref, "stats").status == 404
        assert env.view("me", "stats").body["counts"]["working_memory"] == 2
    finally:
        env.close()


def test_personal_registry_refuses_symlinked_banks(monkeypatch, tmp_path):
    env = H.Env(monkeypatch, tmp_path)
    monkeypatch.setattr(config, "STATE_DIR", env.state)
    try:
        directory = personal_context.home({"email": H.MICHAEL}) / "mnemosyne"
        directory.mkdir(parents=True)
        foreign = H.make_bank(tmp_path / "foreign.db", owner="foreign")
        (directory / "private.db").symlink_to(foreign)
        env.as_user(H.MICHAEL)
        assert not env.banks()["available"]
    finally:
        env.close()
