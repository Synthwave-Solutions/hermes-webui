"""An approved secret folder must open the files in it, in the form the engine matches."""
import os

from api.grant_requests import apply_grant_to_policy


def _policy():
    return {"users": {"yaser@example.test": {"grants": {"files": {"denied_globs": ["/x/**"]}}}}}


def _apply(value):
    raw = _policy()
    apply_grant_to_policy(raw, {"email": "yaser@example.test", "gkind": "secret_glob", "value": value})
    return raw["users"]["yaser@example.test"]["grants"]["files"]["allow_globs"]


def test_existing_directory_also_grants_its_contents(tmp_path):
    d = tmp_path / "ccc"
    d.mkdir()
    assert _apply(str(d)) == [str(d), f"{d}/**"]


def test_trailing_slash_marks_a_directory_before_it_exists(tmp_path):
    d = tmp_path / "ivcb"
    assert _apply(f"{d}/") == [str(d), f"{d}/**"]


def test_tilde_is_expanded_to_the_real_home():
    import pwd
    home = pwd.getpwuid(os.getuid()).pw_dir
    assert _apply("~/.config/does-not-exist.env") == [f"{home}/.config/does-not-exist.env"]


def test_single_file_stays_a_single_exact_path(tmp_path):
    f = tmp_path / "key.json"
    f.write_text("{}")
    assert _apply(str(f)) == [str(f)]


def test_existing_glob_is_kept_as_is():
    assert _apply("/x/clients/ccc/**") == ["/x/clients/ccc/**"]
