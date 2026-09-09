# Focused backend verification

Browser run: `20260909-184341-281192000`. These are selected release checks, not global CI.

## webui

749 passed, 0 failed, 0 skipped across 65 source files at `90cc10318788db857464663b1874d28eb1e50430`.

Full listed files except auxiliary settings: HTML and JS classes only; session jump buttons: explicit full-history/start/virtual-window behavior selector only. Unchanged auxiliary backend/catalog and locale-contract failures were separately baseline-qualified.

Runner: `./scripts/test.sh`. Exact test arguments:

```text
tests/test_continuation_authority.py
tests/test_dashboard_plugin_asset_auth.py
tests/test_e2e_isolation.py
tests/test_governance_agent_context.py
tests/test_governance_catalog_coverage.py
tests/test_governance_resource_scope.py
tests/test_issue1823_kanban_not_found.py
tests/test_issue6174_public_share_media_embed.py
tests/test_issue6220_id_linked_tool_anchor_hydration.py
tests/test_kanban_bridge.py
tests/test_kanban_manual_completion.py
tests/test_live_tool_callback_events.py
tests/test_personal_file_guard.py
tests/test_plugin_page_runtime.py
tests/test_public_share_security.py
tests/test_realtime_voice.py
tests/test_realtime_voice_frontend.py
tests/test_realtime_voice_runtime.py
tests/test_realtime_voice_tls.py
tests/test_requester_grant_ingestion.py
tests/test_session_delegation_status.py
tests/test_session_ops.py
tests/test_session_progress.py
tests/test_session_public_share.py
tests/test_session_public_share_static.py
tests/test_tool_call_persistence.py
tests/test_tool_failure_reporting.py
tests/test_upload_request_visibility.py
tests/test_workspace_acl_ceiling.py
tests/test_workspace_ownership.py
tests/test_workspace_upload.py
tests/test_xterm_vendored_assets.py
tests/test_chat_worker_identity_dispatch.py
tests/test_session_import_workspace_validation.py
tests/test_csv_table_rendering.py
tests/test_user_appearance_store.py
tests/test_implicit_workspace_authority.py
tests/test_full_history_request_races.py
tests/test_gateway_watcher_profile.py
tests/test_mcp_catalog_governance.py
tests/test_cli_approval_restriction_preview.py
tests/test_issue5169_profile_active_default_workspace.py
tests/test_issue_edit_regenerate_absolute_keep_count.py
tests/test_issue5924_post_failure_recovery_model_pick.py
tests/test_issue4183_regenerate_materialize.py
tests/test_extension_sidecar_proxy.py
tests/test_cron_editor_validation.py
tests/test_cron_model_override.py
tests/test_e2e_cron_disabled_create.py
tests/test_kanban_board_focus.py
tests/test_start_navigation_ownership.py
tests/test_issue1937_endless_scroll_jumpstart_race.py
tests/test_tars_scroll_reset_regressions.py
tests/test_issue1690_scroll_completion.py
tests/test_new_chat_activation_ownership.py
tests/test_composer_draft_restore_intent.py
tests/test_cached_agent_interrupt_reset.py
tests/test_worker_ownership.py
tests/test_kanban_dependency_draft.py
tests/test_stream_reconnect_ownership.py
tests/test_dock_follow_ownership.py
tests/test_kanban_edit_focus_ownership.py
tests/test_cron_skill_picker_focus.py
tests/test_auxiliary_models_settings.py::TestAuxiliaryModelsHTML
tests/test_auxiliary_models_settings.py::TestAuxiliaryModelsJS
tests/test_session_jump_buttons.py::test_jump_to_session_start_button_loads_full_history_and_scrolls_top
```

## engine

453 passed, 0 failed, 0 skipped across 32 source files at `b0aaa74f9dcfe9e7caa4692656b4535ce04104e1`.

All tests in the listed files.

Runner: `scripts/run_tests.sh`. Exact test arguments:

```text
tests/hermes_cli/test_bot_access_ceiling.py
tests/hermes_cli/test_dashboard_governance_audit.py
tests/hermes_cli/test_dashboard_governance_cli.py
tests/hermes_cli/test_dashboard_governance_deny.py
tests/hermes_cli/test_dashboard_governance_enforcement.py
tests/hermes_cli/test_dashboard_governance_loader.py
tests/hermes_cli/test_dashboard_governance_resolver.py
tests/hermes_cli/test_dashboard_governance_route_catalog.py
tests/hermes_cli/test_dashboard_governance_usage.py
tests/hermes_cli/test_dashboard_governance_web.py
tests/hermes_cli/test_grant_operation_provenance.py
tests/hermes_cli/test_kanban_block_kinds.py
tests/hermes_cli/test_kanban_blocked_sticky.py
tests/hermes_cli/test_kanban_lifecycle_hooks.py
tests/hermes_cli/test_kanban_manual_pending_completion.py
tests/hermes_cli/test_kanban_manual_todo_block.py
tests/hermes_cli/test_kanban_parent_reopen_invalidation.py
tests/hermes_cli/test_kanban_review_lifecycle.py
tests/hermes_cli/test_kanban_review_lifecycle_complete.py
tests/hermes_cli/test_kanban_task_updated_hook.py
tests/hermes_cli/test_project_file_scope.py
tests/run_agent/test_dashboard_governance_model_runtime.py
tests/test_governance_continuation_context.py
tests/test_governance_per_user_actions.py
tests/test_governance_tool_runtime.py
tests/tools/test_async_delegation.py
tests/tools/test_async_delegation_continuation_ref.py
tests/tools/test_async_delegation_fd_leak.py
tests/tools/test_async_delegation_pending.py
tests/test_governance_mcp_names.py
tests/test_governance_cli_approval_commands.py
tests/test_hermes_state_readonly_preflight.py
```

## Separate baseline qualifications

The first supplemental backend bundle reported 644 passes and one old inline-locale assertion failure. That exact failure was reproduced on deployed 6d67853c. Other separately inspected legacy contracts include two auxiliary retired-slot expectations, three profile-cache overrides, and old inline-locale assumptions in Cron/Kanban. They were not silently converted into release passes. The selected final bundle records its exact scope above.

## Current GitHub CI qualification

# Exact-head CI qualification

Reviewed WebUI `90cc10318788db857464663b1874d28eb1e50430`. Six substantive checks and two routing checks passed. All 15 broad shards failed during collection on the same ten unchanged missing-contract imports. Every latest shard log was independently parsed, and exact test bytes/imports plus absent module symbols were checked at this head against the recorded 571c, 6d and 0ded baselines. Their merged checkout tree equals the reviewed head. Runtime tests after collection did not run; global CI is not green.

The original normal-lifecycle job was cancelled during dependency installation before its test step ran. One authorized exact-job rerun produced workflow attempt 2; the normal test then executed and passed. The original cancellation, log hashes, step timing and separate replay remain in the qualification JSON. No source, workflow deadline or test assertion changed for that replay.

The broad jobs checked out engine `49bf59875c41e84baf5ac53bd1194859d54be94d`, distinct from the paired supplemental engine `b0aaa74f9dcfe9e7caa4692656b4535ce04104e1`. The paired local backend and full-browser evidence therefore remain separate. Engine PR11 statuses were inspected without a fresh engine-log audit; three checks were still queued in that snapshot.

Raw logs remain private under work. The delivered CI JSON records check links, source/tree proof, all fifteen log hashes and preserved earlier qualifications. Later source commits do not automatically inherit this qualification.
