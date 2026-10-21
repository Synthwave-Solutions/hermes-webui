# Skill save-notice snapshot performance

Before and after a run, the WebUI reads fresh memory and skill file signatures
for save notices. Directory traversal identifies already-visited directories by
device and inode, following symlinks once and stopping cycles without resolving
every ancestor repeatedly. Filesystems that report no inode use canonical paths.
Relative skill names, hidden-directory exclusions, traversal limits and personal
versus profile memory homes retain their existing semantics.

No snapshot is reused between turns: edits in symlinked skill categories remain
visible immediately. This only optimizes observation for save notices; it does
not change the skills, tools or memory presented to the model.

Validate with `./scripts/test.sh tests/test_skill_snapshot_latency.py` and the
snapshot test in `tests/test_skill_learning_activity.py`.
