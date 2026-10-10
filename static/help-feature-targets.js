// Audited inert navigation metadata for the complete WebUI feature catalogue.
// A selector is a candidate, never evidence of current visibility or permission.
// Empty targets mean explanatory fallback: no exact parent-DOM hook is available.
// No clicks, callbacks, network URLs, mutations or iframe traversal belong here.
(function () {
  'use strict';
  const entries = {
  "webui.help.navigation": {
    "panel": "chat",
    "targets": [
      "#btnHamburger",
      "#railExpandToggle"
    ]
  },
  "webui.help.tour": {
    "panel": "settings",
    "section": "help",
    "targets": [
      "#helpCardStartTour"
    ]
  },
  "webui.help.org_tour": {
    "panel": "settings",
    "section": "help",
    "targets": [
      "#helpCardStartOrgTour"
    ]
  },
  "webui.help.page": {
    "panel": "chat",
    "targets": [
      "#btnPageHelp"
    ]
  },
  "webui.help.guide": {
    "panel": "settings",
    "section": "help",
    "targets": [
      "#helpCardGuide"
    ]
  },
  "webui.help.confirm": {
    "panel": "chat",
    "targets": [
      "#appDialogClose",
      "#appDialogInput",
      "#appDialogCancel",
      "#appDialogConfirm"
    ]
  },
  "webui.chat.send": {
    "panel": "chat",
    "targets": [
      "#msg",
      "#btnSend"
    ]
  },
  "webui.chat.normal": {
    "panel": "chat",
    "targets": [
      "#chatModeNormal"
    ]
  },
  "webui.chat.super": {
    "panel": "chat",
    "targets": [
      "#chatModeSuper"
    ]
  },
  "webui.chat.model": {
    "panel": "chat",
    "targets": [
      "#composerModelChip",
      "#modelSelect",
      "#composerMobileModelAction"
    ]
  },
  "webui.chat.reasoning": {
    "panel": "chat",
    "targets": [
      "#composerReasoningChip",
      "#composerMobileReasoningAction"
    ]
  },
  "webui.chat.quota": {
    "panel": "chat",
    "targets": [
      "#providerQuotaChip",
      "#composerMobileQuotaAction"
    ]
  },
  "webui.chat.context": {
    "panel": "chat",
    "targets": [
      "#ctxIndicator",
      "#ctxCompressBtn",
      "#composerMobileCtxCompressBtn"
    ]
  },
  "webui.chat.tools": {
    "panel": "chat",
    "targets": [
      "#composerToolsetsChip",
      "#toolsetsInput",
      "#toolsetsApplyBtn",
      "#toolsetsClearBtn"
    ]
  },
  "webui.chat.attach": {
    "panel": "chat",
    "targets": [
      "#fileInput",
      "#btnAttach"
    ]
  },
  "webui.chat.prompts": {
    "panel": "chat",
    "targets": [
      "#btnSavedPrompts"
    ]
  },
  "webui.chat.people": {
    "panel": "chat",
    "targets": [
      "#composerPeopleChip",
      "#groupPeopleFilter",
      "#groupPeopleModalSubmit"
    ]
  },
  "webui.chat.mentions": {
    "panel": "chat",
    "targets": [
      "#msg"
    ]
  },
  "webui.chat.scroll": {
    "panel": "chat",
    "targets": [
      "#jumpToSessionStartBtn",
      "#scrollToBottomBtn",
      "#outlineToggleBtn"
    ]
  },
  "webui.chat.copy": {
    "panel": "chat",
    "targets": [
      ".msg-copy-btn"
    ]
  },
  "webui.chat.edit": {
    "panel": "chat",
    "targets": [
      ".msg-edit-area"
    ]
  },
  "webui.chat.undo": {
    "panel": "chat",
    "targets": []
  },
  "webui.chat.retry": {
    "panel": "chat",
    "targets": []
  },
  "webui.chat.fork": {
    "panel": "chat",
    "targets": []
  },
  "webui.chat.activity": {
    "panel": "chat",
    "targets": [
      ".tool-call-group-summary",
      ".tool-worklog-tool-group-head"
    ]
  },
  "webui.chat.svg": {
    "panel": "chat",
    "targets": [
      ".svg-visual-block",
      ".msg-media-svg"
    ]
  },
  "webui.chat.replay": {
    "panel": "chat",
    "targets": []
  },
  "webui.chat.mobile": {
    "panel": "chat",
    "targets": [
      "#composerMobileConfigBtn"
    ]
  },
  "webui.sessions.new": {
    "panel": "chat",
    "targets": [
      "#btnTitlebarNewChat",
      "#btnNewChat"
    ]
  },
  "webui.sessions.search": {
    "panel": "chat",
    "targets": [
      "#sessionSearch",
      "#sessionSearchClear"
    ]
  },
  "webui.sessions.split": {
    "panel": "chat",
    "targets": [
      "#btnSplitView",
      "#btnSplitExit"
    ]
  },
  "webui.sessions.transcript": {
    "panel": "settings",
    "section": "conversation",
    "targets": [
      "#btnDownload"
    ]
  },
  "webui.sessions.json": {
    "panel": "settings",
    "section": "conversation",
    "targets": [
      "#btnExportJSON",
      "#btnImportJSON",
      "#importFileInput"
    ]
  },
  "webui.sessions.html": {
    "panel": "settings",
    "section": "conversation",
    "targets": [
      "#btnExportHTML"
    ]
  },
  "webui.sessions.share": {
    "panel": "settings",
    "section": "conversation",
    "targets": [
      "#btnShareSession",
      "#btnStopSharingSession"
    ]
  },
  "webui.sessions.clear": {
    "panel": "settings",
    "section": "conversation",
    "targets": [
      "#btnClearConvModal"
    ]
  },
  "webui.sessions.organize": {
    "panel": "chat",
    "targets": [
      ".session-actions-trigger"
    ]
  },
  "webui.voice.dictation": {
    "panel": "chat",
    "targets": [
      "#btnMic"
    ]
  },
  "webui.voice.read": {
    "panel": "chat",
    "targets": [
      ".msg-tts-btn"
    ]
  },
  "webui.voice.loop": {
    "panel": "chat",
    "targets": [
      "#btnVoiceMode"
    ]
  },
  "webui.voice.realtime": {
    "panel": "chat",
    "targets": [
      "#realtimeVoiceEnd",
      "#btnRealtimeVoice"
    ]
  },
  "webui.voice.hold": {
    "panel": "chat",
    "targets": [
      "#realtimeVoiceHold",
      "#realtimeVoiceMic",
      "#realtimeVoiceInterrupt"
    ]
  },
  "webui.tasks.create": {
    "panel": "tasks",
    "targets": [
      "[data-tour='tasks-new']",
      "#cronFormName"
    ]
  },
  "webui.tasks.prompt": {
    "panel": "tasks",
    "targets": [
      "#cronFormPrompt"
    ]
  },
  "webui.tasks.script": {
    "panel": "tasks",
    "targets": [
      "#cronFormScript"
    ]
  },
  "webui.tasks.skills": {
    "panel": "tasks",
    "targets": [
      "#cronFormSkillSearch"
    ]
  },
  "webui.tasks.schedule": {
    "panel": "tasks",
    "targets": [
      "#cronFormSchedulePreset",
      "#cronFormScheduleWeekday",
      "#cronFormScheduleMonthDay",
      "#cronFormScheduleTime",
      "#cronFormScheduleMinute",
      "#cronFormSchedule"
    ]
  },
  "webui.tasks.profile": {
    "panel": "tasks",
    "targets": [
      "#cronFormProfile",
      "#cronFormModel"
    ]
  },
  "webui.tasks.delivery": {
    "panel": "tasks",
    "targets": [
      "#cronFormDeliver"
    ]
  },
  "webui.tasks.notify": {
    "panel": "tasks",
    "targets": [
      "[data-tour='tasks-notify']"
    ]
  },
  "webui.tasks.mute": {
    "panel": "tasks",
    "targets": [
      ".cron-notify-mute-btn",
      ".cron-notify-mine"
    ]
  },
  "webui.tasks.run": {
    "panel": "tasks",
    "targets": [
      "#btnRunTaskDetail"
    ]
  },
  "webui.tasks.pause": {
    "panel": "tasks",
    "targets": [
      "#btnPauseTaskDetail",
      "#btnResumeTaskDetail"
    ]
  },
  "webui.tasks.share": {
    "panel": "tasks",
    "targets": [
      "#btnShareTaskDetail",
      "#cronShareExtra",
      "#cronShareCancel",
      "#cronShareSave"
    ]
  },
  "webui.tasks.edit": {
    "panel": "tasks",
    "targets": [
      "#btnEditTaskDetail",
      "#btnDuplicateTaskDetail",
      "#btnDeleteTaskDetail"
    ]
  },
  "webui.tasks.labels": {
    "panel": "tasks",
    "targets": [
      "#cronEmojiCustom",
      "#cronCategoryPick",
      "#cronFormEmoji",
      "#cronFormCategory",
      "#cronFormDiagram"
    ]
  },
  "webui.tasks.results": {
    "panel": "tasks",
    "targets": [
      "#cronRefreshBtn"
    ]
  },
  "webui.files.workspace": {
    "panel": "chat",
    "targets": [
      "#composerWorkspaceChip",
      "#composerMobileWorkspaceAction"
    ]
  },
  "webui.files.manage": {
    "panel": "workspaces",
    "targets": [
      "#btnEditWorkspaceDetail",
      "#btnDeleteWorkspaceDetail",
      "#btnCancelWorkspaceDetail",
      "#btnSaveWorkspaceDetail"
    ]
  },
  "webui.files.access": {
    "panel": "workspaces",
    "targets": [
      "#wsAssignOwner",
      "#wsAssignMembers",
      "#wsAssignSaveBtn"
    ]
  },
  "webui.files.browse": {
    "panel": "chat",
    "targets": [
      "#btnWorkspacePanelToggle",
      "#btnWorkspacePanelEdgeToggle",
      "#btnUpDir",
      "#btnRefreshPanel",
      "#btnClearPreview",
      "#workspaceFilesTab"
    ]
  },
  "webui.files.create": {
    "panel": "chat",
    "targets": [
      "#btnNewFile",
      "#btnNewFolder"
    ]
  },
  "webui.files.upload": {
    "panel": "chat",
    "targets": [
      "#btnUploadWorkspace",
      "#workspaceFileInput"
    ]
  },
  "webui.files.preview": {
    "panel": "chat",
    "targets": [
      "#btnRenderMarkdownAnyway"
    ]
  },
  "webui.files.edit": {
    "panel": "chat",
    "targets": [
      "#btnEditFile",
      "#previewEditArea"
    ]
  },
  "webui.files.download": {
    "panel": "chat",
    "targets": [
      "#btnOpenInBrowser",
      "#btnDownloadFile"
    ]
  },
  "webui.files.path": {
    "panel": "chat",
    "targets": [
      "#btnCopyPreviewRelPath"
    ]
  },
  "webui.files.artifacts": {
    "panel": "chat",
    "targets": [
      "#workspaceArtifactsTab"
    ]
  },
  "webui.files.todos": {
    "panel": "chat",
    "targets": [
      "#workspaceTodosTab"
    ]
  },
  "webui.files.preferences": {
    "panel": "chat",
    "targets": [
      "#btnWorkspacePrefs"
    ]
  },
  "webui.boards.create": {
    "panel": "kanban",
    "targets": [
      "#kanbanNewTaskBtn",
      "#kanbanNewTaskTitle",
      "#kanbanTaskModalTitleInput",
      "#kanbanTaskModalBody",
      "#kanbanTaskModalSubmit"
    ]
  },
  "webui.boards.status": {
    "panel": "kanban",
    "targets": [
      "#kanbanTaskModalStatus",
      "#kanbanTaskModalPriority"
    ]
  },
  "webui.boards.assignment": {
    "panel": "kanban",
    "targets": [
      "#kanbanTaskModalAssignee",
      "#kanbanTaskModalTenant"
    ]
  },
  "webui.boards.runtime": {
    "panel": "kanban",
    "targets": [
      "#kanbanTaskModalWorkspaceKind",
      "#kanbanTaskModalWorkspacePath",
      "#kanbanTaskModalSkills",
      "#kanbanTaskModalMaxRuntimeSeconds"
    ]
  },
  "webui.boards.links": {
    "panel": "kanban",
    "targets": [
      "#kanbanTaskModalParents",
      "#kanbanDependencyInput"
    ]
  },
  "webui.boards.comments": {
    "panel": "kanban",
    "targets": [
      "#kanbanCommentInput"
    ]
  },
  "webui.boards.block": {
    "panel": "kanban",
    "targets": [
      "#kanbanTaskModalStatus"
    ]
  },
  "webui.boards.filter": {
    "panel": "kanban",
    "targets": [
      "#kanbanRefreshBtn",
      "#kanbanSearch",
      "#kanbanAssigneeFilter",
      "#kanbanTenantFilter",
      "#kanbanIncludeArchived",
      "#kanbanOnlyMine"
    ]
  },
  "webui.boards.bulk": {
    "panel": "kanban",
    "targets": [
      "#kanbanBulkStatus"
    ]
  },
  "webui.boards.dispatch": {
    "panel": "kanban",
    "targets": [
      "#btnKanbanPreviewDispatcher",
      "#btnKanbanRunDispatcher"
    ]
  },
  "webui.boards.boards": {
    "panel": "kanban",
    "targets": [
      "#kanbanBoardSwitcherToggle",
      "#btnKanbanCreateBoard",
      "#kanbanBoardModalMode",
      "#kanbanBoardModalSlug",
      "#kanbanBoardModalName",
      "#kanbanBoardModalSlugInput",
      "#kanbanBoardModalDesc",
      "#kanbanBoardModalIcon",
      "#kanbanBoardModalColor",
      "#kanbanBoardModalSubmit"
    ]
  },
  "webui.boards.consolidated": {
    "panel": "kanban",
    "targets": [
      "#btnKanbanViewToggle"
    ]
  },
  "webui.memory.personal": {
    "panel": "memory",
    "targets": [
      "#btnEditMemoryDetail",
      "#btnCancelMemoryDetail",
      "#btnSaveMemoryDetail",
      "#memEditContent"
    ]
  },
  "webui.memory.company": {
    "panel": "memory",
    "targets": [
      "#memoryPanel button[title='All agents can use this knowledge · Admin management']"
    ]
  },
  "webui.memory.project": {
    "panel": "memory",
    "targets": [
      "#memoryPanel button[title='Shared with project members · Read only']"
    ]
  },
  "webui.memory.identity": {
    "panel": "memory",
    "targets": []
  },
  "webui.memory.external": {
    "panel": "memory",
    "targets": [
      "#externalNotesSource",
      "#externalNotesQuery"
    ]
  },
  "webui.memory.explorer": {
    "panel": "memory",
    "targets": [
      "#memdashPicker",
      "[data-memdash='explorer']"
    ]
  },
  "webui.memory.search": {
    "panel": "memory",
    "targets": []
  },
  "webui.memory.audit": {
    "panel": "memory",
    "targets": [
      "[data-memdash='access']"
    ]
  },
  "webui.skills.browse": {
    "panel": "skills",
    "targets": [
      "#skillsSearch"
    ]
  },
  "webui.skills.edit": {
    "panel": "skills",
    "targets": [
      "#btnEditSkillDetail",
      "#btnCancelSkillDetail",
      "#btnSaveSkillDetail",
      "#skillFormName",
      "#skillFormCategory",
      "#skillFormContent"
    ]
  },
  "webui.skills.delete": {
    "panel": "skills",
    "targets": [
      "#btnDeleteSkillDetail"
    ]
  },
  "webui.skills.wiki": {
    "panel": "skills",
    "targets": [
      "#wikiBrowserSearch"
    ]
  },
  "webui.bots.select": {
    "panel": "chat",
    "targets": [
      "#profileChip",
      "#titlebarProfileBtn"
    ]
  },
  "webui.bots.create": {
    "panel": "profiles",
    "targets": [
      "[data-tour='bots-new']",
      "#builderName"
    ]
  },
  "webui.bots.identity": {
    "panel": "profiles",
    "targets": [
      "#builderName",
      "#builderTitle",
      "#builderDescription"
    ]
  },
  "webui.bots.instructions": {
    "panel": "profiles",
    "targets": [
      "#builderPrompt"
    ]
  },
  "webui.bots.skills": {
    "panel": "profiles",
    "targets": [
      "[data-selection='skills']",
      "[data-filter='skills']"
    ]
  },
  "webui.bots.tools": {
    "panel": "profiles",
    "targets": [
      "[data-selection='mcp_servers']",
      "[data-selection='cli_tools']"
    ]
  },
  "webui.bots.memory": {
    "panel": "profiles",
    "targets": [
      "#builderMemory"
    ]
  },
  "webui.bots.knowledge": {
    "panel": "profiles",
    "targets": [
      "#builderKnowledge [data-knowledge-save]",
      "#builderKnowledge"
    ]
  },
  "webui.bots.access": {
    "panel": "profiles",
    "targets": [
      "[data-selection='allowed_users']",
      "[data-selection='allowed_groups']"
    ]
  },
  "webui.bots.appearance": {
    "panel": "profiles",
    "targets": [
      "#builderPhoto",
      "#botTitle",
      "#botDescription",
      "#botShape",
      "#botColor",
      "#botCategory",
      "#botAvatarFile"
    ]
  },
  "webui.bots.manage": {
    "panel": "profiles",
    "targets": [
      "#btnDeleteProfileDetail",
      "#btnCancelProfileDetail",
      "#btnSaveProfileDetail"
    ]
  },
  "webui.projects.create": {
    "panel": "projects",
    "targets": [
      "#projNewName",
      "#projNewCategory",
      "#projCreateButton"
    ]
  },
  "webui.projects.team": {
    "panel": "projects",
    "targets": [
      "#projPeopleSearch",
      "#projCategory",
      "#projSaveTeam"
    ]
  },
  "webui.projects.chat": {
    "panel": "projects",
    "targets": [
      "#projStartChat"
    ]
  },
  "webui.projects.files": {
    "panel": "projects",
    "targets": [
      "#projUpload"
    ]
  },
  "webui.projects.archive": {
    "panel": "projects",
    "targets": [
      "#projArchiveTeam"
    ]
  },
  "webui.connections.providers": {
    "panel": "integrations",
    "targets": [
      "#integrationsRefreshBtn",
      "#intgSearch"
    ]
  },
  "webui.connections.channel": {
    "panel": "integrations",
    "targets": [
      ".intg-card[data-channel]"
    ]
  },
  "webui.connections.publish": {
    "panel": "integrations",
    "targets": [
      ".ch-public"
    ]
  },
  "webui.connections.people": {
    "panel": "integrations",
    "targets": [
      "#chAddPlatform",
      "#chAddUserId"
    ]
  },
  "webui.connections.personal": {
    "panel": "integrations",
    "targets": [
      "[data-mine-field]"
    ]
  },
  "webui.connections.link": {
    "panel": "integrations",
    "targets": [
      "#chMinePlatform",
      "#chMineOtherId"
    ]
  },
  "webui.connections.mcp": {
    "panel": "settings",
    "targets": [
      "#mcpServerList"
    ],
    "section": "system"
  },
  "webui.connections.catalog": {
    "panel": "settings",
    "section": "system",
    "targets": [
      "#mcpToolSearch"
    ]
  },
  "webui.governance.once": {
    "panel": "chat",
    "targets": [
      "#approvalBtnOnce"
    ]
  },
  "webui.governance.session": {
    "panel": "chat",
    "targets": [
      "#approvalBtnSession"
    ]
  },
  "webui.governance.always": {
    "panel": "chat",
    "targets": [
      "#approvalBtnAlways"
    ]
  },
  "webui.governance.deny": {
    "panel": "chat",
    "targets": [
      "#approvalCollapse",
      "#approvalBtnDeny"
    ]
  },
  "webui.governance.skip": {
    "panel": "chat",
    "targets": [
      "#approvalSkipAll",
      "#yoloPill"
    ]
  },
  "webui.governance.clarify": {
    "panel": "chat",
    "targets": [
      "#clarifyCollapse",
      "#clarifyInput",
      "#clarifySubmit"
    ]
  },
  "webui.governance.requests": {
    "panel": "approvals",
    "targets": [
      "#btnMyApprovalsRefresh"
    ]
  },
  "webui.governance.resume": {
    "panel": "settings",
    "targets": [
      "#accessRequestsList > label input[type=\"checkbox\"]",
      "#accessRequestsList [data-operation-id]"
    ],
    "section": "access"
  },
  "webui.governance.users": {
    "panel": "governance",
    "targets": [
      "#govUserEmail",
      "#govUserSave",
      "#govUserAccessLevel",
      "#govUserAccessMode",
      "#govUserApprovalMode"
    ]
  },
  "webui.governance.mcp_map": {
    "panel": "governance",
    "targets": [
      "#govUserMcpTools",
      "#govUserDenyMcpTools"
    ]
  },
  "webui.governance.groups": {
    "panel": "governance",
    "targets": [
      "#govGroupName",
      "#govGroupDesc",
      "#govGroupSso",
      "#govGroupRoles"
    ]
  },
  "webui.governance.preview": {
    "panel": "governance",
    "targets": [
      "#govPreviewEmail",
      "#govPreviewGroups"
    ]
  },
  "webui.governance.audit": {
    "panel": "governance",
    "targets": [
      "#governanceRefreshBtn"
    ]
  },
  "webui.governance.workspace_filter": {
    "panel": "governance",
    "targets": [
      "#govWsUserFilter"
    ]
  },
  "webui.governance.organisation": {
    "panel": "governance",
    "targets": []
  },
  "webui.operations.refresh": {
    "panel": "chat",
    "targets": [
      "#btnReload",
      "#btnStaleClientRefresh",
      "#offlineCheckNow"
    ]
  },
  "webui.operations.health": {
    "panel": "chat",
    "targets": [
      "#agentHealthDismiss",
      "#btnRestartGateway"
    ]
  },
  "webui.operations.terminal": {
    "panel": "chat",
    "targets": [
      "#btnTerminalClear",
      "#btnTerminalCopy",
      "#btnTerminalRestart",
      "#btnTerminalCollapse",
      "#btnTerminalClose",
      "#btnTerminalExpand",
      "#btnTerminalDockClose"
    ]
  },
  "webui.operations.logs": {
    "panel": "logs",
    "targets": [
      "#logsRefreshBtn",
      "#logsFile",
      "#logsTail",
      "#logsSeverityFilter",
      "#logsAutoRefresh",
      "#logsWrap",
      "#logsCopyAll"
    ]
  },
  "webui.operations.insights": {
    "panel": "insights",
    "targets": [
      "#insightsRefreshBtn",
      "#insightsPeriod"
    ]
  },
  "webui.operations.capacity": {
    "panel": "settings",
    "targets": [
      "#capacityPollSeconds",
      "#capacityCooldownSeconds",
      "#capacityThresholds",
      "#capacityDestination",
      "#btnCapacitySave"
    ],
    "section": "system"
  },
  "webui.operations.updates": {
    "panel": "settings",
    "targets": [
      "#btnCheckUpdatesNow"
    ],
    "section": "system"
  },
  "webui.operations.errors": {
    "panel": "chat",
    "targets": []
  },
  "webui.operations.extensions": {
    "panel": "settings",
    "targets": [
      "#extensionsCopyDiagnosticsBtn"
    ],
    "section": "extensions"
  },
  "webui.operations.dashboard": {
    "panel": "chat",
    "targets": [
      "#dashboardRailBtn",
      "#dashboardMobileBtn"
    ]
  },
  "webui.settings.theme": {
    "panel": "settings",
    "section": "appearance",
    "targets": [
      "#themePickerGrid"
    ]
  },
  "webui.settings.skin": {
    "panel": "settings",
    "section": "appearance",
    "targets": [
      "#skinPickerGrid"
    ]
  },
  "webui.settings.font_size": {
    "panel": "settings",
    "section": "appearance",
    "targets": [
      "#fontSizePickerGrid"
    ]
  },
  "webui.settings.workspace_panel_open": {
    "panel": "settings",
    "section": "appearance",
    "targets": [
      "#settingsWorkspacePanelOpen"
    ]
  },
  "webui.settings.workspace_todos_tab": {
    "panel": "settings",
    "section": "appearance",
    "targets": [
      "#settingsWorkspaceTodosTab"
    ]
  },
  "webui.settings.session_jump_buttons": {
    "panel": "settings",
    "section": "appearance",
    "targets": [
      "#settingsSessionJumpButtons"
    ]
  },
  "webui.settings.session_endless_scroll": {
    "panel": "settings",
    "section": "appearance",
    "targets": [
      "#settingsSessionEndlessScroll"
    ]
  },
  "webui.settings.chat_activity_display_mode": {
    "panel": "settings",
    "section": "appearance",
    "targets": [
      "#settingsChatActivityDisplayMode"
    ]
  },
  "webui.settings.transparent_event_timestamps": {
    "panel": "settings",
    "section": "appearance",
    "targets": [
      "#settingsTransparentEventTimestamps"
    ]
  },
  "webui.settings.auto_scroll_follow": {
    "panel": "settings",
    "section": "appearance",
    "targets": [
      "#settingsAutoScrollFollow"
    ]
  },
  "webui.settings.render_user_markdown": {
    "panel": "settings",
    "section": "appearance",
    "targets": [
      "#settingsRenderUserMarkdown"
    ]
  },
  "webui.settings.large_text_paste_as_attachment": {
    "panel": "settings",
    "section": "appearance",
    "targets": [
      "#settingsLargeTextPasteAsAttachment"
    ]
  },
  "webui.settings.project_quick_create": {
    "panel": "settings",
    "section": "appearance",
    "targets": [
      "#settingsProjectQuickCreate"
    ]
  },
  "webui.settings.structured_code_mode": {
    "panel": "settings",
    "section": "appearance",
    "targets": [
      "#settingsStructuredCodeMode"
    ]
  },
  "webui.settings.structured_code_auto_lines": {
    "panel": "settings",
    "section": "appearance",
    "targets": [
      "#settingsStructuredCodeAutoLines"
    ]
  },
  "webui.settings.show_titlebar_profile": {
    "panel": "settings",
    "section": "appearance",
    "targets": [
      "#settingsShowTitlebarProfile"
    ]
  },
  "webui.settings.worklog_details_expanded_default": {
    "panel": "settings",
    "section": "appearance",
    "targets": [
      "#settingsWorklogDetailsExpandedDefault"
    ]
  },
  "webui.settings.advanced_chat_controls": {
    "panel": "settings",
    "section": "appearance",
    "targets": [
      "#settingsAdvancedChatControls"
    ]
  },
  "webui.settings.model": {
    "panel": "settings",
    "section": "preferences",
    "targets": [
      "#settingsModelChip",
      "#settingsModel"
    ]
  },
  "webui.settings.hide_suggestions": {
    "panel": "settings",
    "section": "preferences",
    "targets": [
      "#settingsHideSuggestions"
    ]
  },
  "webui.settings.hide_empty_state_panel": {
    "panel": "settings",
    "section": "preferences",
    "targets": [
      "#settingsHideEmptyStatePanel"
    ]
  },
  "webui.settings.virtualize_transcript": {
    "panel": "settings",
    "section": "preferences",
    "targets": [
      "#settingsVirtualizeTranscript"
    ]
  },
  "webui.settings.send_key": {
    "panel": "settings",
    "section": "preferences",
    "targets": [
      "#settingsSendKey"
    ]
  },
  "webui.settings.language": {
    "panel": "settings",
    "section": "preferences",
    "targets": [
      "#settingsLanguage"
    ]
  },
  "webui.settings.rtl": {
    "panel": "settings",
    "section": "preferences",
    "targets": [
      "#settingsRtl"
    ]
  },
  "webui.settings.sound_enabled": {
    "panel": "settings",
    "section": "preferences",
    "targets": [
      "#settingsSoundEnabled"
    ]
  },
  "webui.settings.tts_enabled": {
    "panel": "settings",
    "section": "preferences",
    "targets": [
      "#settingsTtsEnabled"
    ]
  },
  "webui.settings.tts_auto_read": {
    "panel": "settings",
    "section": "preferences",
    "targets": [
      "#settingsTtsAutoRead"
    ]
  },
  "webui.settings.voice_mode_enabled": {
    "panel": "settings",
    "section": "preferences",
    "targets": [
      "#settingsVoiceModeEnabled"
    ]
  },
  "webui.settings.raw_audio": {
    "panel": "settings",
    "section": "preferences",
    "targets": [
      "#settingsRawAudio"
    ]
  },
  "webui.settings.dictation_append": {
    "panel": "settings",
    "section": "preferences",
    "targets": [
      "#settingsDictationAppend"
    ]
  },
  "webui.settings.tts_engine": {
    "panel": "settings",
    "section": "preferences",
    "targets": [
      "#settingsTtsEngine"
    ]
  },
  "webui.settings.tts_voice": {
    "panel": "settings",
    "section": "preferences",
    "targets": [
      "#settingsTtsVoice"
    ]
  },
  "webui.settings.tts_rate": {
    "panel": "settings",
    "section": "preferences",
    "targets": [
      "#settingsTtsRate"
    ]
  },
  "webui.settings.tts_pitch": {
    "panel": "settings",
    "section": "preferences",
    "targets": [
      "#settingsTtsPitch"
    ]
  },
  "webui.settings.notifications_enabled": {
    "panel": "settings",
    "section": "preferences",
    "targets": [
      "#settingsNotificationsEnabled"
    ]
  },
  "webui.settings.show_token_usage": {
    "panel": "settings",
    "section": "preferences",
    "targets": [
      "#settingsShowTokenUsage"
    ]
  },
  "webui.settings.max_tokens": {
    "panel": "settings",
    "section": "preferences",
    "targets": [
      "#settingsMaxTokens"
    ]
  },
  "webui.settings.show_quota_chip": {
    "panel": "settings",
    "section": "preferences",
    "targets": [
      "#settingsShowQuotaChip"
    ]
  },
  "webui.settings.show_conversation_outline": {
    "panel": "settings",
    "section": "preferences",
    "targets": [
      "#settingsShowConversationOutline"
    ]
  },
  "webui.settings.show_tps": {
    "panel": "settings",
    "section": "preferences",
    "targets": [
      "#settingsShowTps"
    ]
  },
  "webui.settings.fade_text_effect": {
    "panel": "settings",
    "section": "preferences",
    "targets": [
      "#settingsFadeTextEffect"
    ]
  },
  "webui.settings.terminal_auto_expand": {
    "panel": "settings",
    "section": "preferences",
    "targets": [
      "#settingsTerminalAutoExpand"
    ]
  },
  "webui.settings.api_redact": {
    "panel": "settings",
    "section": "preferences",
    "targets": [
      "#settingsApiRedact"
    ]
  },
  "webui.settings.sidebar_density": {
    "panel": "settings",
    "section": "preferences",
    "targets": [
      "#settingsSidebarDensity"
    ]
  },
  "webui.settings.pinned_sessions_limit": {
    "panel": "settings",
    "section": "preferences",
    "targets": [
      "#settingsPinnedSessionsLimit"
    ]
  },
  "webui.settings.auto_title_refresh": {
    "panel": "settings",
    "section": "preferences",
    "targets": [
      "#settingsAutoTitleRefresh"
    ]
  },
  "webui.settings.default_message_mode": {
    "panel": "settings",
    "section": "preferences",
    "targets": [
      "#settingsDefaultMessageMode"
    ]
  },
  "webui.settings.show_busy_placeholder_hint": {
    "panel": "settings",
    "section": "preferences",
    "targets": [
      "#settingsShowBusyPlaceholderHint"
    ]
  },
  "webui.settings.new_chat_on_workspace_switch": {
    "panel": "settings",
    "section": "preferences",
    "targets": [
      "#settingsNewChatOnWorkspaceSwitch"
    ]
  },
  "webui.settings.show_cli_sessions": {
    "panel": "settings",
    "section": "preferences",
    "targets": [
      "#settingsShowCliSessions"
    ]
  },
  "webui.settings.show_cron_sessions": {
    "panel": "settings",
    "section": "preferences",
    "targets": [
      "#settingsShowCronSessions"
    ]
  },
  "webui.settings.show_claude_code_sessions": {
    "panel": "settings",
    "section": "preferences",
    "targets": [
      "#settingsShowClaudeCodeSessions"
    ]
  },
  "webui.settings.show_webhook_sessions": {
    "panel": "settings",
    "section": "preferences",
    "targets": [
      "#settingsShowWebhookSessions"
    ]
  },
  "webui.settings.show_previous_messaging_sessions": {
    "panel": "settings",
    "section": "preferences",
    "targets": [
      "#settingsShowPreviousMessagingSessions"
    ]
  },
  "webui.settings.sync_insights": {
    "panel": "settings",
    "section": "preferences",
    "targets": [
      "#settingsSyncInsights"
    ]
  },
  "webui.settings.check_updates": {
    "panel": "settings",
    "section": "preferences",
    "targets": [
      "#settingsCheckUpdates"
    ]
  },
  "webui.settings.update_channel": {
    "panel": "settings",
    "section": "preferences",
    "targets": [
      "#settingsUpdateChannel"
    ]
  },
  "webui.settings.ignore_agent_updates": {
    "panel": "settings",
    "section": "preferences",
    "targets": [
      "#settingsIgnoreAgentUpdates"
    ]
  },
  "webui.settings.whats_new_summary": {
    "panel": "settings",
    "section": "preferences",
    "targets": [
      "#settingsWhatsNewSummary"
    ]
  },
  "webui.settings.bot_name": {
    "panel": "settings",
    "section": "preferences",
    "targets": [
      "#settingsBotName"
    ]
  },
  "webui.settings.dashboard_mode": {
    "panel": "settings",
    "section": "system",
    "targets": [
      "#settingsDashboardMode"
    ]
  },
  "webui.settings.dashboard_url": {
    "panel": "settings",
    "section": "system",
    "targets": [
      "#settingsDashboardUrl"
    ]
  },
  "webui.settings.save": {
    "panel": "settings",
    "targets": [
      "#settingsPanePreferences [data-i18n='settings_save_btn']"
    ],
    "section": "preferences"
  },
  "webui.settings.photo": {
    "panel": "settings",
    "section": "appearance",
    "targets": [
      ".profile-photo-upload",
      "#profilePhotoRemoveBtn"
    ]
  },
  "webui.settings.interaction": {
    "panel": "settings",
    "section": "preferences",
    "targets": [
      "#interactionUserMode",
      "#interactionTaskMode",
      "#interactionSave",
      "#interactionReload"
    ]
  },
  "webui.settings.aux_models": {
    "panel": "settings",
    "targets": [
      "#btnResetAuxModels",
      "#btnApplyAuxModels"
    ],
    "section": "preferences"
  },
  "webui.settings.advanced_model": {
    "panel": "settings",
    "targets": [
      "#settingsModelChip",
      "#mainAdvancedBtn",
      "#auxAdvancedClose",
      "#auxAdvancedCancel",
      "#auxAdvancedSave",
      "#auxAdvancedServiceTier",
      "#auxAdvancedExtraBody",
      "#auxAdvancedApiKeyClear"
    ],
    "section": "preferences"
  },
  "webui.settings.notification_permission": {
    "panel": "settings",
    "section": "preferences",
    "targets": [
      "#notificationPermissionButton"
    ]
  },
  "webui.settings.password": {
    "panel": "settings",
    "section": "system",
    "targets": [
      "#settingsPassword",
      "#settingsCurrentPassword"
    ]
  },
  "webui.settings.passkey": {
    "panel": "settings",
    "section": "system",
    "targets": [
      "#btnRegisterPasskey"
    ]
  },
  "webui.settings.passwordless": {
    "panel": "settings",
    "section": "system",
    "targets": [
      "#btnGoPasswordless"
    ]
  },
  "webui.settings.disable_auth": {
    "panel": "settings",
    "section": "system",
    "targets": [
      "#settingsAuthDisabledAck",
      "#btnDisableAuth"
    ]
  },
  "webui.settings.signout": {
    "panel": "settings",
    "section": "system",
    "targets": [
      "#btnSignOut"
    ]
  },
  "webui.settings.shutdown": {
    "panel": "settings",
    "section": "system",
    "targets": [
      "#btnShutdownServer"
    ]
  },
  "webui.settings.composer_visibility": {
    "panel": "settings",
    "targets": [
      "#composerControlsChips",
      "#composerSituationalControlsChips"
    ],
    "section": "appearance"
  },
  "webui.settings.navigation": {
    "panel": "settings",
    "targets": [
      "#tabVisibilityChips"
    ],
    "section": "appearance"
  },
  "webui.connections.onboarding": {
    "panel": "chat",
    "targets": [
      "#onboardingBackBtn",
      "#onboardingSkipBtn",
      "#onboardingNextBtn",
      "#onboardingBaseUrlInput",
      "#onboardingApiKeyInput",
      "#onboardingModelInput",
      "#onboardingModelSelect",
      "#onboardingProviderSelect",
      "#onboardingWorkspaceSelect",
      "#onboardingWorkspaceInput",
      "#onboardingPasswordInput"
    ]
  },
  "webui.connections.oauth": {
    "panel": "settings",
    "targets": [
      "#anthropicOAuthBtn",
      "#codexOAuthBtn"
    ],
    "section": "providers"
  },
  "webui.planned.gateway": {
    "panel": "settings",
    "section": "system",
    "targets": []
  },
  "webui.planned.reporter": {
    "panel": "settings",
    "section": "system",
    "targets": []
  },
  "webui.planned.central_memory": {
    "panel": "settings",
    "section": "system",
    "targets": []
  },
  "webui.sessions.rename": {
    "panel": "chat",
    "targets": []
  },
  "webui.sessions.pin": {
    "panel": "chat",
    "targets": []
  },
  "webui.sessions.move_project": {
    "panel": "chat",
    "targets": []
  },
  "webui.sessions.archive": {
    "panel": "chat",
    "targets": []
  },
  "webui.sessions.delete": {
    "panel": "chat",
    "targets": []
  },
  "webui.sessions.regenerate_title": {
    "panel": "chat",
    "targets": []
  },
  "webui.sessions.link": {
    "panel": "chat",
    "targets": []
  },
  "webui.chat.save_prompt": {
    "panel": "chat",
    "targets": [
      "#btnSavedPrompts"
    ]
  },
  "webui.bots.knowledge_upload": {
    "panel": "profiles",
    "targets": [
      "[data-knowledge-upload]"
    ]
  },
  "webui.bots.knowledge_legacy": {
    "panel": "profiles",
    "targets": [
      "#builderKnowledge details"
    ]
  },
  "webui.memory.overview": {
    "panel": "memory",
    "targets": []
  },
  "webui.memory.today": {
    "panel": "memory",
    "targets": []
  },
  "webui.memory.visualiser": {
    "panel": "memory",
    "targets": []
  },
  "webui.memory.review": {
    "panel": "memory",
    "targets": []
  },
  "webui.memory.profile": {
    "panel": "memory",
    "targets": []
  },
  "webui.memory.lifecycle": {
    "panel": "memory",
    "targets": []
  },
  "webui.memory.graph": {
    "panel": "memory",
    "targets": []
  },
  "webui.memory.triples": {
    "panel": "memory",
    "targets": []
  },
  "webui.memory.recall": {
    "panel": "memory",
    "targets": []
  },
  "webui.memory.timeline": {
    "panel": "memory",
    "targets": []
  },
  "webui.memory.consolidations": {
    "panel": "memory",
    "targets": []
  },
  "webui.memory.structured_overview": {
    "panel": "memory",
    "targets": []
  },
  "webui.memory.facts": {
    "panel": "memory",
    "targets": []
  },
  "webui.memory.structured_timelines": {
    "panel": "memory",
    "targets": []
  },
  "webui.memory.instructions": {
    "panel": "memory",
    "targets": []
  },
  "webui.memory.structured_graph": {
    "panel": "memory",
    "targets": []
  },
  "webui.memory.preferences": {
    "panel": "memory",
    "targets": []
  },
  "webui.settings.search": {
    "panel": "settings",
    "targets": [
      "#settingsSearch"
    ],
    "section": "preferences"
  },
  "webui.files.hidden": {
    "panel": "chat",
    "targets": [
      "#workspaceShowHiddenFiles"
    ]
  },
  "webui.governance.approval_prompt": {
    "panel": "governance",
    "targets": [
      "#govUserApprovalPrompt"
    ]
  },
  "webui.governance.effective_grants": {
    "panel": "governance",
    "targets": [
      "#govUserEffective"
    ]
  },
  "webui.governance.group_template": {
    "panel": "governance",
    "targets": [
      ".gov-chip-role"
    ]
  },
  "webui.governance.integration_approval": {
    "panel": "governance",
    "targets": []
  },
  "webui.operations.extension_gallery": {
    "panel": "settings",
    "targets": [
      "#extensionsGallery"
    ],
    "section": "extensions"
  },
  "webui.operations.extension_installed": {
    "panel": "settings",
    "targets": [
      "#extensionsInstalled"
    ],
    "section": "extensions"
  },
  "webui.chat.slash": {
    "panel": "chat",
    "targets": [
      "#msg"
    ]
  },
  "webui.chat.goal": {
    "panel": "chat",
    "targets": [
      "#msg"
    ]
  },
  "webui.chat.queue": {
    "panel": "chat",
    "targets": [
      "#queuePill",
      "#queueCard",
      "#msg"
    ]
  },
  "webui.chat.interrupt": {
    "panel": "chat",
    "targets": [
      "#msg"
    ]
  },
  "webui.chat.steer": {
    "panel": "chat",
    "targets": [
      "#msg"
    ]
  },
  "webui.chat.aside": {
    "panel": "chat",
    "targets": [
      "#msg"
    ]
  },
  "webui.chat.background": {
    "panel": "chat",
    "targets": [
      "#bgBadge",
      "#msg"
    ]
  },
  "webui.chat.status": {
    "panel": "chat",
    "targets": [
      "#msg"
    ]
  },
  "webui.chat.personality": {
    "panel": "chat",
    "targets": [
      "#msg"
    ]
  },
  "webui.skills.use": {
    "panel": "chat",
    "targets": [
      "#msg"
    ]
  },
  "webui.modules.apps": {
    "panel": "chat",
    "targets": [
      "#btnApps"
    ]
  },
  "webui.modules.overview": {
    "panel": "modules",
    "targets": [
      "#mainModules .modules-intro"
    ]
  },
  "webui.modules.budget": {
    "panel": "modules",
    "targets": [
      "#mainModules .module-meta"
    ]
  },
  "webui.modules.connections": {
    "panel": "modules",
    "targets": [
      "#mainModules .module-card details:has(ul) > summary"
    ]
  },
  "webui.modules.request": {
    "panel": "modules",
    "targets": [
      "#mainModules .module-card details:not(:has(ul)) > summary"
    ]
  },
  "webui.modules.language": {
    "panel": "modules",
    "targets": [
      "#mainModules .module-language select"
    ]
  }
};
  for (const entry of Object.values(entries)) {
    Object.freeze(entry.targets);
    Object.freeze(entry);
  }
  window.SynthPulseFeatureTargets = Object.freeze(entries);
})();
