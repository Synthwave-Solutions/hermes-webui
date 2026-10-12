// Help content for Explain this page, the guided tours and What's new (plan 6.1, W4).
// Static strings only, keyed by locale (English and Dutch). The value below is
// plain JSON: keep double quotes and no trailing commas, so the coverage test
// can read it without a JavaScript engine. No HTML, no dashes, no internal
// component names (tests/test_help_content_coverage.py checks all of this).
// Structure per locale:
//   ui: labels the help panel needs beyond the locale keys of Appendix G.
//   pages: one entry per page (every data-panel of index.html plus virtual
//     pages). parent: the panel a virtual page lives on; audience: "admin" or
//     "org"; module or modules (all of): catalogue ids that must be enabled;
//     enabled_if: a selector that must be visible. Sections have an id, title,
//     body and an optional target ([data-tour='x'] or #id); dynamic: true
//     when the target is rendered at run time and not in index.html.
//   tour_steps: steps by id, with a target or nav (a data-panel id), an
//     optional page to switch to first, audience and module keys.
//   tours: tour id to its step ids, in order.
//   whats_new: WebUI version to the cards shown once after an upgrade.
window.SynthPulseHelpContent = {
  "version": 1,
  "locales": {
    "en": {
      "ui": {
        "feedback_thanks": "Thanks. We use this to improve the help.",
        "sections_heading": "On this page",
        "related_heading": "See also",
        "whats_new_version": "Version {0}"
      },
      "pages": {
        "chat": {
          "title": "Chats",
          "summary": "Talk with your AI assistant. Every conversation is saved, so you can pick it up again later.",
          "sections": [
            {
              "id": "new",
              "title": "Start a new chat",
              "body": "Use the plus button to start a fresh conversation. Your earlier chats stay in the list.",
              "target": "[data-tour='chat-new']"
            },
            {
              "id": "list",
              "title": "Your conversations",
              "body": "Your chats are listed here, newest first. Click one to continue where you left off.",
              "target": "[data-tour='chat-list']"
            },
            {
              "id": "search",
              "title": "Find a chat",
              "body": "Search by title or by words from the conversation.",
              "target": "[data-tour='chat-search']"
            },
            {
              "id": "composer",
              "title": "Write a message",
              "body": "Type your question or task and press Enter to send it. Shift and Enter start a new line.",
              "target": "[data-tour='chat-composer']"
            },
            {
              "id": "attach",
              "title": "Add files",
              "body": "Attach documents or images so the assistant can read them.",
              "target": "[data-tour='chat-attach']"
            },
            {
              "id": "bot",
              "title": "Pick a bot",
              "body": "Choose which bot answers. Each bot has its own instructions, skills and access.",
              "target": "[data-tour='chat-bot']"
            },
            {
              "id": "model",
              "title": "Model",
              "body": "Shows the AI model of this chat. Pick another one when a task needs a faster or a stronger model.",
              "target": "[data-tour='chat-model']"
            },
            {
              "id": "workspace",
              "title": "Files of this space",
              "body": "Open the files of the current space next to the chat.",
              "target": "[data-tour='chat-workspace']"
            }
          ],
          "related": [
            "group_chat",
            "profiles",
            "workspace_files"
          ]
        },
        "group_chat": {
          "title": "Group chats",
          "summary": "Invite colleagues and several bots into one conversation, so everyone works in the same chat.",
          "parent": "chat",
          "module": "group_chat",
          "sections": [
            {
              "id": "people",
              "title": "Who is in this chat",
              "body": "Add or remove colleagues. Each person's messages run under their own access, never under yours.",
              "target": "[data-tour='chat-people']"
            },
            {
              "id": "mention",
              "title": "Ask a specific bot",
              "body": "Type @ and the bot name to choose who answers. Without a mention, the conversation follows its configured default routing. Check the bot attribution on the reply.",
              "target": "[data-tour='chat-composer']"
            }
          ],
          "related": [
            "chat",
            "profiles"
          ]
        },
        "voice_mode": {
          "title": "Voice mode",
          "summary": "Talk instead of type. The assistant listens, answers out loud and keeps the text in the chat.",
          "parent": "chat",
          "sections": [
            {
              "id": "toggle",
              "title": "Start voice mode",
              "body": "Use the voice button next to the message box. Press it again to stop.",
              "target": "[data-tour='chat-voice-mode']"
            },
            {
              "id": "bar",
              "title": "While you talk",
              "body": "This bar shows whether the assistant is listening or speaking.",
              "target": "[data-tour='voice-mode-bar']"
            },
            {
              "id": "dictate",
              "title": "Dictate a message",
              "body": "Use the microphone to turn your speech into text in the message box. Check the text, then send it.",
              "target": "[data-tour='chat-dictate']"
            }
          ],
          "related": [
            "chat",
            "realtime_voice"
          ]
        },
        "realtime_voice": {
          "title": "Realtime voice",
          "summary": "Have a live spoken conversation when audio is configured and permitted. Availability depends on the provider, browser and installation policy.",
          "parent": "chat",
          "enabled_if": "[data-tour='chat-realtime-voice']",
          "sections": [
            {
              "id": "start",
              "title": "Start a live conversation",
              "body": "Use this button to start talking. Allow the microphone when your browser asks.",
              "target": "[data-tour='chat-realtime-voice']"
            },
            {
              "id": "bar",
              "title": "Live controls",
              "body": "Hold, mute the microphone, interrupt the assistant or end the conversation here.",
              "target": "[data-tour='realtime-voice-bar']"
            }
          ],
          "related": [
            "voice_mode",
            "chat"
          ]
        },
        "profiles": {
          "title": "Bots",
          "summary": "Bots are assistants with their own instructions, skills and access. Pick one for a chat or set up a new one.",
          "sections": [
            {
              "id": "new",
              "title": "Create a bot",
              "body": "Start the guided bot builder. It asks for a name, instructions, tools and who may use the bot.",
              "target": "[data-tour='bots-new']"
            },
            {
              "id": "list",
              "title": "Your bots",
              "body": "Open a bot to see what it does, who may use it and which skills it has.",
              "target": "[data-tour='bots-list']"
            }
          ],
          "related": [
            "bot_builder",
            "profile_switching",
            "skills"
          ]
        },
        "bot_builder": {
          "title": "Guided bot builder",
          "summary": "Set up a bot step by step. You can go back to any step before you save.",
          "parent": "profiles",
          "sections": [
            {
              "id": "identity",
              "title": "Identity",
              "body": "Give the bot a name, a title and a short description, so colleagues know when to use it."
            },
            {
              "id": "instructions",
              "title": "Instructions",
              "body": "Describe how the bot should work: its role, its tone and what it must never do."
            },
            {
              "id": "access",
              "title": "Access",
              "body": "Choose which people and groups may use the bot. Others do not see it."
            }
          ],
          "related": [
            "profiles",
            "skills"
          ]
        },
        "profile_switching": {
          "title": "Switching bots",
          "summary": "Switch the bot you work with. The bot you pick answers your next messages in this chat.",
          "parent": "chat",
          "sections": [
            {
              "id": "chip",
              "title": "Bot in the message box",
              "body": "Click the bot name under the message box to pick another bot.",
              "target": "[data-tour='chat-bot']"
            },
            {
              "id": "titlebar",
              "title": "Bot switcher at the top",
              "body": "When you turn it on in Settings, the bot switcher also sits at the top of the screen.",
              "target": "[data-tour='profile-switch']"
            }
          ],
          "related": [
            "profiles",
            "chat"
          ]
        },
        "tasks": {
          "title": "Scheduled tasks",
          "summary": "Run a prompt or a script on a schedule and get the result where you need it.",
          "sections": [
            {
              "id": "new",
              "title": "Create a task",
              "body": "Describe what should happen and when. A task can run once, every few hours or on a fixed schedule.",
              "target": "[data-tour='tasks-new']"
            },
            {
              "id": "list",
              "title": "Your tasks",
              "body": "See when each task runs next and how its last run went. Open a task for its runs and output.",
              "target": "[data-tour='tasks-list']"
            },
            {
              "id": "notify",
              "title": "Notifications",
              "body": "Choose who hears about a run: always, only when it fails, or never. The output is always kept here.",
              "target": "[data-tour='tasks-notify']",
              "dynamic": true
            }
          ],
          "related": [
            "kanban",
            "profiles"
          ]
        },
        "kanban": {
          "title": "Task board",
          "summary": "Plan work as cards on a board, assign them to people or bots and follow them from ready to done.",
          "sections": [
            {
              "id": "new",
              "title": "Add a task",
              "body": "Create a card for a piece of work. Give it a clear title so everyone knows what it is about.",
              "target": "[data-tour='kanban-new']"
            },
            {
              "id": "filters",
              "title": "Filter the board",
              "body": "Search, filter by person and choose to see only your own or archived tasks.",
              "target": "[data-tour='kanban-filters']"
            },
            {
              "id": "list",
              "title": "Tasks",
              "body": "Open a card to see its details, change its status or leave a comment.",
              "target": "[data-tour='kanban-list']"
            }
          ],
          "related": [
            "tasks",
            "todos"
          ]
        },
        "todos": {
          "title": "Current task list",
          "summary": "The to do list the assistant keeps for the current chat, so you can follow its plan and progress.",
          "sections": [
            {
              "id": "list",
              "title": "Plan and progress",
              "body": "Items are ticked off as the assistant finishes them. The list belongs to the chat you have open.",
              "target": "[data-tour='todos-list']"
            }
          ],
          "related": [
            "chat",
            "kanban"
          ]
        },
        "skills": {
          "title": "Skills library",
          "summary": "Skills are reusable instructions that teach a bot how to do a specific job the way your organisation does it.",
          "sections": [
            {
              "id": "new",
              "title": "Add a skill",
              "body": "Write down how a job should be done once, so every bot that has the skill does it the same way.",
              "target": "[data-tour='skills-new']"
            },
            {
              "id": "search",
              "title": "Find a skill",
              "body": "Search by name or description.",
              "target": "[data-tour='skills-search']"
            },
            {
              "id": "list",
              "title": "All skills",
              "body": "Open a skill to read it, change it or switch it on or off.",
              "target": "[data-tour='skills-list']"
            }
          ],
          "related": [
            "profiles",
            "projects"
          ]
        },
        "projects": {
          "title": "Projects",
          "summary": "Everything this workstation holds about a project in one place: chats, tasks, files and notes.",
          "sections": [
            {
              "id": "list",
              "title": "Your projects",
              "body": "Open a project to see all its chats, tasks and files together.",
              "target": "[data-tour='projects-list']"
            }
          ],
          "related": [
            "workspaces",
            "chat"
          ]
        },
        "workspaces": {
          "title": "Spaces",
          "summary": "A space is a folder of files that chats and bots can work in. Add a space and switch between spaces here.",
          "sections": [
            {
              "id": "add",
              "title": "Add a space",
              "body": "Point to a folder to use as a space. Chats in that space can read and write its files.",
              "target": "[data-tour='spaces-add']"
            },
            {
              "id": "list",
              "title": "Your spaces",
              "body": "Click a space to make it the space of your next chat.",
              "target": "[data-tour='spaces-list']"
            }
          ],
          "related": [
            "workspace_files",
            "projects"
          ]
        },
        "workspace_files": {
          "title": "Workspace files panel",
          "summary": "The panel next to the chat shows the files of the current space. Open, preview and upload files without leaving the chat.",
          "parent": "chat",
          "sections": [
            {
              "id": "open",
              "title": "Open the panel",
              "body": "Use this button to show or hide the files next to the chat.",
              "target": "[data-tour='chat-workspace']"
            },
            {
              "id": "panel",
              "title": "The panel",
              "body": "Browse folders, preview a file or upload new files here.",
              "target": "[data-tour='workspace-files']"
            },
            {
              "id": "tree",
              "title": "Files and folders",
              "body": "Click a file to preview it. Files the assistant made show up here too.",
              "target": "[data-tour='workspace-file-tree']"
            }
          ],
          "related": [
            "files",
            "workspaces"
          ]
        },
        "files": {
          "title": "Files",
          "summary": "Browse the files of your current space: open, preview, upload and download them.",
          "sections": [
            {
              "id": "tree",
              "title": "Files and folders",
              "body": "Click a folder to open it and a file to preview it.",
              "target": "[data-tour='workspace-file-tree']"
            },
            {
              "id": "tab",
              "title": "Files tab",
              "body": "Switch between your files and the documents the assistant made.",
              "target": "[data-tour='workspace-files-tab']"
            }
          ],
          "related": [
            "workspace_files",
            "workspaces"
          ]
        },
        "memory": {
          "title": "Personal memory",
          "summary": "What the assistant remembers about you and your work, so you do not have to repeat yourself. You can read and change it here.",
          "sections": [
            {
              "id": "sections",
              "title": "What is remembered",
              "body": "Open a section to read it. Change or remove anything that is wrong or out of date.",
              "target": "[data-tour='memory-sections']"
            }
          ],
          "related": [
            "profiles",
            "settings"
          ]
        },
        "integrations": {
          "title": "Connections",
          "summary": "Connect the services you use, such as mail, calendar or files, so your bots can work with them for you.",
          "sections": [
            {
              "id": "connect",
              "title": "Connect a service",
              "body": "Pick a service and sign in. Only your own chats and tasks use your connection, and you can disconnect at any time.",
              "target": "[data-tour='connections-intro']"
            }
          ],
          "related": [
            "approvals",
            "profiles"
          ]
        },
        "insights": {
          "title": "Insights",
          "summary": "See how you use the assistant: chats, messages, tools and costs over a period.",
          "sections": [
            {
              "id": "period",
              "title": "Choose a period",
              "body": "Show the last 7, 30, 90 or 365 days.",
              "target": "[data-tour='insights-period']"
            }
          ],
          "related": [
            "logs"
          ]
        },
        "approvals": {
          "title": "My approvals",
          "summary": "Requests you made that wait for an administrator, such as access to a bot or a connection. Only your own requests appear here.",
          "sections": [
            {
              "id": "intro",
              "title": "Your requests",
              "body": "Each request shows whether it is still open, approved or declined.",
              "target": "[data-tour='approvals-intro']"
            }
          ],
          "related": [
            "integrations",
            "settings"
          ]
        },
        "governance": {
          "title": "Governance",
          "summary": "Administrators decide here who may use which bots, skills, connections and spaces, and handle access requests.",
          "audience": "admin",
          "sections": [
            {
              "id": "intro",
              "title": "Roles and groups",
              "body": "Give people roles and groups. Their access follows from them, and every change is recorded.",
              "target": "[data-tour='governance-intro']"
            }
          ],
          "related": [
            "approvals",
            "logs"
          ]
        },
        "logs": {
          "title": "Logs",
          "summary": "Technical logs of this installation, for troubleshooting together with support.",
          "sections": [
            {
              "id": "controls",
              "title": "Choose what to see",
              "body": "Pick a log file, how many lines to show and which messages, and copy them for support.",
              "target": "[data-tour='logs-controls']"
            }
          ],
          "related": [
            "insights",
            "settings"
          ]
        },
        "settings": {
          "title": "Settings",
          "summary": "Change how SynthPulse looks and works for you.",
          "sections": [
            {
              "id": "search",
              "title": "Find a setting",
              "body": "Type a word to jump to the setting you need.",
              "target": "[data-tour='settings-search']"
            },
            {
              "id": "menu",
              "title": "Sections",
              "body": "Conversation, appearance, preferences and more, each on its own page.",
              "target": "[data-tour='settings-menu']"
            },
            {
              "id": "help",
              "title": "Help",
              "body": "Start the tour again or read the documentation.",
              "target": "[data-tour='settings-help']"
            }
          ],
          "related": [
            "plugins"
          ]
        },
        "plugins": {
          "title": "Plugins",
          "summary": "Plugins add features to SynthPulse. See which ones are installed and turn them on or off.",
          "parent": "settings",
          "sections": [
            {
              "id": "menu",
              "title": "Plugins in Settings",
              "body": "Open this section to see the installed plugins.",
              "target": "[data-tour='settings-plugins']"
            }
          ],
          "related": [
            "settings"
          ]
        },
        "modules": {
          "title": "Modules",
          "summary": "Review the local module configuration, model usage and possible connections. This screen activates nothing.",
          "sections": [
            {
              "id": "catalogue",
              "title": "Module overview",
              "body": "Organisation, billing and platform administrators can read this on an organisation installation. This screen is hidden at headquarters.",
              "target": "#mainModules"
            }
          ],
          "related": [
            "apps",
            "settings"
          ]
        },
        "apps": {
          "title": "Apps",
          "summary": "Open the available applications for your installation from Apps in navigation.",
          "sections": [
            {
              "id": "directory",
              "title": "Apps",
              "body": "Choose Apps in navigation. You must be signed in. Members see permitted apps for active modules; platform administrators also see configured management apps. Each application checks its own access.",
              "target": "#mainApps"
            }
          ],
          "related": [
            "modules",
            "integrations"
          ]
        },
        "msp": {
          "title": "Support",
          "summary": "See your actual support allowance, usage and app support subscriptions with your MSP.",
          "sections": [
            {
              "id": "overview",
              "title": "View support hours and subscriptions",
              "body": "See your actual support allowance, usage and app support subscriptions with your MSP. An installation without an active contract shows no invented allowance. App support does not automatically credit your hours balance.",
              "target": "#mspOverviewTab",
              "dynamic": true
            },
            {
              "id": "tickets",
              "title": "Create, track and reply to tickets",
              "body": "Send a question or incident to your MSP and follow open and completed tickets. Internal MSP notes remain hidden. A submitted request is not an approved change or payment order.",
              "target": "#mspTicketsTab",
              "dynamic": true
            },
            {
              "id": "billing",
              "title": "View payments",
              "body": "See payment requests and invoice statuses for your organisation. A configured payment provider and invoice are required for a payment link. Returning from Mollie does not by itself mark an invoice paid.",
              "target": "#mspBillingTab",
              "dynamic": true
            }
          ],
          "related": [
            "apps"
          ]
        }
      },
      "tour_steps": {
        "chat": {
          "title": "Start a chat",
          "body": "Type what you need here and press Enter. The assistant answers in this conversation.",
          "target": "[data-tour='chat-composer']",
          "page": "chat"
        },
        "bots": {
          "title": "Pick a bot",
          "body": "Choose which bot answers. Each bot has its own instructions, skills and access.",
          "target": "[data-tour='chat-bot']",
          "page": "chat"
        },
        "files": {
          "title": "Add a file",
          "body": "Attach documents or images to your message so the assistant can work with them.",
          "target": "[data-tour='chat-attach']",
          "page": "chat"
        },
        "spaces": {
          "title": "Work in a space",
          "body": "Spaces keep the files for a piece of work together. Open Spaces in the menu to add one.",
          "nav": "workspaces"
        },
        "tasks": {
          "title": "Schedule a task",
          "body": "Let the assistant do something on a schedule, such as a daily summary. Open Scheduled tasks in the menu.",
          "nav": "tasks"
        },
        "help": {
          "title": "Get help",
          "body": "Not sure what a page is for? This button explains the page you are on. You find this tour again under Settings, Help.",
          "target": "[data-tour='help-button']"
        },
        "organization": {
          "title": "Your organisation",
          "body": "See the people and departments of your organisation and who looks after them.",
          "nav": "organization",
          "audience": "org",
          "dynamic": true
        },
        "departments": {
          "title": "Departments",
          "body": "Each department has its own administrators and its own bots, spaces and tasks.",
          "target": "[data-tour='org-departments']",
          "page": "organization",
          "audience": "org",
          "dynamic": true
        },
        "plan": {
          "title": "Plan and usage",
          "body": "See your plan, the support hours included and how much of your model budget is used.",
          "target": "[data-tour='org-plan']",
          "page": "organization",
          "audience": "org",
          "dynamic": true
        },
        "support": {
          "title": "Support",
          "body": "Ask a question or report a problem. Your tickets and their status are listed here.",
          "nav": "support",
          "audience": "org",
          "dynamic": true
        }
      },
      "tours": {
        "first_run": [
          "chat",
          "bots",
          "files",
          "spaces",
          "tasks",
          "help"
        ],
        "org_admin": [
          "organization",
          "departments",
          "plan",
          "support"
        ]
      },
      "whats_new": {
        "0.53.0": [
          {
            "title": "Help on every page",
            "body": "Use the question mark at the top of the screen to see what the page you are on is for and how to use it."
          },
          {
            "title": "A short tour",
            "body": "New here, or want a refresher? Start the tour under Settings, Help, or type /tour in a chat."
          }
        ]
      }
    },
    "nl": {
      "ui": {
        "feedback_thanks": "Bedankt. We gebruiken dit om de uitleg te verbeteren.",
        "sections_heading": "Op deze pagina",
        "related_heading": "Zie ook",
        "whats_new_version": "Versie {0}"
      },
      "pages": {
        "chat": {
          "title": "Chats",
          "summary": "Praat met je AI-assistent. Elk gesprek wordt bewaard, zodat je het later weer kunt oppakken.",
          "sections": [
            {
              "id": "new",
              "title": "Nieuwe chat starten",
              "body": "Start met de plusknop een nieuw gesprek. Je eerdere chats blijven in de lijst staan.",
              "target": "[data-tour='chat-new']"
            },
            {
              "id": "list",
              "title": "Je gesprekken",
              "body": "Hier staan je chats, de nieuwste bovenaan. Klik op een chat om verder te gaan waar je gebleven was.",
              "target": "[data-tour='chat-list']"
            },
            {
              "id": "search",
              "title": "Een chat zoeken",
              "body": "Zoek op titel of op woorden uit het gesprek.",
              "target": "[data-tour='chat-search']"
            },
            {
              "id": "composer",
              "title": "Een bericht schrijven",
              "body": "Typ je vraag of opdracht en druk op Enter om te versturen. Met Shift en Enter begin je een nieuwe regel.",
              "target": "[data-tour='chat-composer']"
            },
            {
              "id": "attach",
              "title": "Bestanden toevoegen",
              "body": "Voeg documenten of afbeeldingen toe, zodat de assistent ze kan lezen.",
              "target": "[data-tour='chat-attach']"
            },
            {
              "id": "bot",
              "title": "Een bot kiezen",
              "body": "Kies welke bot antwoordt. Elke bot heeft eigen instructies, vaardigheden en toegang.",
              "target": "[data-tour='chat-bot']"
            },
            {
              "id": "model",
              "title": "Model",
              "body": "Het AI-model van deze chat. Kies een ander model als een taak sneller of sterker moet.",
              "target": "[data-tour='chat-model']"
            },
            {
              "id": "workspace",
              "title": "Bestanden van deze ruimte",
              "body": "Open de bestanden van de huidige ruimte naast de chat.",
              "target": "[data-tour='chat-workspace']"
            }
          ],
          "related": [
            "group_chat",
            "profiles",
            "workspace_files"
          ]
        },
        "group_chat": {
          "title": "Groepsgesprekken",
          "summary": "Nodig collega's en meerdere bots uit in één gesprek, zodat iedereen in dezelfde chat werkt.",
          "parent": "chat",
          "module": "group_chat",
          "sections": [
            {
              "id": "people",
              "title": "Wie er in deze chat zit",
              "body": "Voeg collega's toe of haal ze weg. Berichten van iedere deelnemer lopen onder diens eigen toegang, nooit onder die van jou.",
              "target": "[data-tour='chat-people']"
            },
            {
              "id": "mention",
              "title": "Een bepaalde bot vragen",
              "body": "Typ @ en de botnaam om te kiezen wie antwoordt. Zonder vermelding volgt het gesprek de ingestelde standaardroutering. Controleer de botvermelding bij het antwoord.",
              "target": "[data-tour='chat-composer']"
            }
          ],
          "related": [
            "chat",
            "profiles"
          ]
        },
        "voice_mode": {
          "title": "Spraakmodus",
          "summary": "Praat in plaats van te typen. De assistent luistert, antwoordt hardop en houdt de tekst bij in de chat.",
          "parent": "chat",
          "sections": [
            {
              "id": "toggle",
              "title": "Spraakmodus starten",
              "body": "Gebruik de spraakknop naast het berichtvak. Druk er nog eens op om te stoppen.",
              "target": "[data-tour='chat-voice-mode']"
            },
            {
              "id": "bar",
              "title": "Tijdens het praten",
              "body": "Deze balk laat zien of de assistent luistert of spreekt.",
              "target": "[data-tour='voice-mode-bar']"
            },
            {
              "id": "dictate",
              "title": "Een bericht dicteren",
              "body": "Gebruik de microfoon om je spraak om te zetten in tekst in het berichtvak. Controleer de tekst en verstuur hem daarna.",
              "target": "[data-tour='chat-dictate']"
            }
          ],
          "related": [
            "chat",
            "realtime_voice"
          ]
        },
        "realtime_voice": {
          "title": "Live spraak",
          "summary": "Voer een live gesproken gesprek wanneer audio is ingesteld en toegestaan. Beschikbaarheid hangt af van provider, browser en installatiebeleid.",
          "parent": "chat",
          "enabled_if": "[data-tour='chat-realtime-voice']",
          "sections": [
            {
              "id": "start",
              "title": "Een live gesprek starten",
              "body": "Start met deze knop het gesprek. Sta de microfoon toe als je browser erom vraagt.",
              "target": "[data-tour='chat-realtime-voice']"
            },
            {
              "id": "bar",
              "title": "Live bediening",
              "body": "Hier kun je het gesprek pauzeren, de microfoon dempen, de assistent onderbreken of het gesprek beëindigen.",
              "target": "[data-tour='realtime-voice-bar']"
            }
          ],
          "related": [
            "voice_mode",
            "chat"
          ]
        },
        "profiles": {
          "title": "Bots",
          "summary": "Bots zijn assistenten met eigen instructies, vaardigheden en toegang. Kies er een voor een chat of maak een nieuwe.",
          "sections": [
            {
              "id": "new",
              "title": "Een bot maken",
              "body": "Start de bouwhulp voor bots. Die vraagt om een naam, instructies, hulpmiddelen en wie de bot mag gebruiken.",
              "target": "[data-tour='bots-new']"
            },
            {
              "id": "list",
              "title": "Je bots",
              "body": "Open een bot om te zien wat hij doet, wie hem mag gebruiken en welke vaardigheden hij heeft.",
              "target": "[data-tour='bots-list']"
            }
          ],
          "related": [
            "bot_builder",
            "profile_switching",
            "skills"
          ]
        },
        "bot_builder": {
          "title": "Bouwhulp voor bots",
          "summary": "Stel een bot stap voor stap in. Je kunt naar elke stap terug voordat je opslaat.",
          "parent": "profiles",
          "sections": [
            {
              "id": "identity",
              "title": "Identiteit",
              "body": "Geef de bot een naam, een titel en een korte omschrijving, zodat collega's weten wanneer ze hem gebruiken."
            },
            {
              "id": "instructions",
              "title": "Instructies",
              "body": "Beschrijf hoe de bot moet werken: zijn rol, zijn toon en wat hij nooit mag doen."
            },
            {
              "id": "access",
              "title": "Toegang",
              "body": "Kies welke mensen en groepen de bot mogen gebruiken. Anderen zien hem niet."
            }
          ],
          "related": [
            "profiles",
            "skills"
          ]
        },
        "profile_switching": {
          "title": "Van bot wisselen",
          "summary": "Wissel van bot. De bot die je kiest beantwoordt je volgende berichten in deze chat.",
          "parent": "chat",
          "sections": [
            {
              "id": "chip",
              "title": "Bot bij het berichtvak",
              "body": "Klik op de botnaam onder het berichtvak om een andere bot te kiezen.",
              "target": "[data-tour='chat-bot']"
            },
            {
              "id": "titlebar",
              "title": "Botkeuze bovenin",
              "body": "Als je dat in Instellingen aanzet, staat de botkeuze ook bovenin het scherm.",
              "target": "[data-tour='profile-switch']"
            }
          ],
          "related": [
            "profiles",
            "chat"
          ]
        },
        "tasks": {
          "title": "Geplande taken",
          "summary": "Voer een prompt of een script volgens een schema uit en krijg het resultaat waar je het nodig hebt.",
          "sections": [
            {
              "id": "new",
              "title": "Een taak maken",
              "body": "Beschrijf wat er moet gebeuren en wanneer. Een taak kan één keer draaien, om de paar uur of volgens een vast schema.",
              "target": "[data-tour='tasks-new']"
            },
            {
              "id": "list",
              "title": "Je taken",
              "body": "Zie wanneer elke taak weer draait en hoe de laatste keer ging. Open een taak voor de uitvoeringen en de uitkomst.",
              "target": "[data-tour='tasks-list']"
            },
            {
              "id": "notify",
              "title": "Meldingen",
              "body": "Kies wie over een uitvoering hoort: altijd, alleen als het misgaat of nooit. De uitkomst blijft hier altijd bewaard.",
              "target": "[data-tour='tasks-notify']",
              "dynamic": true
            }
          ],
          "related": [
            "kanban",
            "profiles"
          ]
        },
        "kanban": {
          "title": "Takenbord",
          "summary": "Plan werk als kaarten op een bord, wijs ze toe aan mensen of bots en volg ze van klaar om te beginnen tot af.",
          "sections": [
            {
              "id": "new",
              "title": "Een taak toevoegen",
              "body": "Maak een kaart voor een stuk werk. Geef hem een duidelijke titel, zodat iedereen weet waar het om gaat.",
              "target": "[data-tour='kanban-new']"
            },
            {
              "id": "filters",
              "title": "Het bord filteren",
              "body": "Zoek, filter op persoon en kies of je alleen je eigen of ook gearchiveerde taken ziet.",
              "target": "[data-tour='kanban-filters']"
            },
            {
              "id": "list",
              "title": "Taken",
              "body": "Open een kaart om de details te zien, de status te wijzigen of een opmerking te plaatsen.",
              "target": "[data-tour='kanban-list']"
            }
          ],
          "related": [
            "tasks",
            "todos"
          ]
        },
        "todos": {
          "title": "Huidige takenlijst",
          "summary": "De takenlijst die de assistent voor de huidige chat bijhoudt, zodat je het plan en de voortgang kunt volgen.",
          "sections": [
            {
              "id": "list",
              "title": "Plan en voortgang",
              "body": "Onderdelen worden afgevinkt zodra de assistent ze af heeft. De lijst hoort bij de chat die je open hebt.",
              "target": "[data-tour='todos-list']"
            }
          ],
          "related": [
            "chat",
            "kanban"
          ]
        },
        "skills": {
          "title": "Vaardighedenbibliotheek",
          "summary": "Vaardigheden zijn herbruikbare instructies die een bot leren hoe hij een bepaalde taak doet zoals jouw organisatie dat wil.",
          "sections": [
            {
              "id": "new",
              "title": "Een vaardigheid toevoegen",
              "body": "Schrijf één keer op hoe een taak moet, zodat elke bot met deze vaardigheid het op dezelfde manier doet.",
              "target": "[data-tour='skills-new']"
            },
            {
              "id": "search",
              "title": "Een vaardigheid zoeken",
              "body": "Zoek op naam of omschrijving.",
              "target": "[data-tour='skills-search']"
            },
            {
              "id": "list",
              "title": "Alle vaardigheden",
              "body": "Open een vaardigheid om hem te lezen, te wijzigen of aan of uit te zetten.",
              "target": "[data-tour='skills-list']"
            }
          ],
          "related": [
            "profiles",
            "projects"
          ]
        },
        "projects": {
          "title": "Projecten",
          "summary": "Alles wat deze werkplek over een project weet op één plek: chats, taken, bestanden en notities.",
          "sections": [
            {
              "id": "list",
              "title": "Je projecten",
              "body": "Open een project om alle chats, taken en bestanden ervan bij elkaar te zien.",
              "target": "[data-tour='projects-list']"
            }
          ],
          "related": [
            "workspaces",
            "chat"
          ]
        },
        "workspaces": {
          "title": "Ruimtes",
          "summary": "Een ruimte is een map met bestanden waarin chats en bots kunnen werken. Voeg hier een ruimte toe en wissel tussen ruimtes.",
          "sections": [
            {
              "id": "add",
              "title": "Een ruimte toevoegen",
              "body": "Wijs een map aan die je als ruimte wilt gebruiken. Chats in die ruimte kunnen de bestanden lezen en schrijven.",
              "target": "[data-tour='spaces-add']"
            },
            {
              "id": "list",
              "title": "Je ruimtes",
              "body": "Klik op een ruimte om die voor je volgende chat te gebruiken.",
              "target": "[data-tour='spaces-list']"
            }
          ],
          "related": [
            "workspace_files",
            "projects"
          ]
        },
        "workspace_files": {
          "title": "Bestandenpaneel",
          "summary": "Het paneel naast de chat toont de bestanden van de huidige ruimte. Open, bekijk en upload bestanden zonder de chat te verlaten.",
          "parent": "chat",
          "sections": [
            {
              "id": "open",
              "title": "Het paneel openen",
              "body": "Gebruik deze knop om de bestanden naast de chat te tonen of te verbergen.",
              "target": "[data-tour='chat-workspace']"
            },
            {
              "id": "panel",
              "title": "Het paneel",
              "body": "Blader door mappen, bekijk een bestand of upload hier nieuwe bestanden.",
              "target": "[data-tour='workspace-files']"
            },
            {
              "id": "tree",
              "title": "Bestanden en mappen",
              "body": "Klik op een bestand om het te bekijken. Bestanden die de assistent maakte, staan hier ook.",
              "target": "[data-tour='workspace-file-tree']"
            }
          ],
          "related": [
            "files",
            "workspaces"
          ]
        },
        "files": {
          "title": "Bestanden",
          "summary": "Blader door de bestanden van je huidige ruimte: openen, bekijken, uploaden en downloaden.",
          "sections": [
            {
              "id": "tree",
              "title": "Bestanden en mappen",
              "body": "Klik op een map om hem te openen en op een bestand om het te bekijken.",
              "target": "[data-tour='workspace-file-tree']"
            },
            {
              "id": "tab",
              "title": "Tabblad Bestanden",
              "body": "Wissel tussen je bestanden en de documenten die de assistent maakte.",
              "target": "[data-tour='workspace-files-tab']"
            }
          ],
          "related": [
            "workspace_files",
            "workspaces"
          ]
        },
        "memory": {
          "title": "Persoonlijk geheugen",
          "summary": "Wat de assistent over jou en je werk onthoudt, zodat je niet alles hoeft te herhalen. Je kunt het hier lezen en aanpassen.",
          "sections": [
            {
              "id": "sections",
              "title": "Wat er onthouden wordt",
              "body": "Open een onderdeel om het te lezen. Pas aan of verwijder wat niet klopt of verouderd is.",
              "target": "[data-tour='memory-sections']"
            }
          ],
          "related": [
            "profiles",
            "settings"
          ]
        },
        "integrations": {
          "title": "Koppelingen",
          "summary": "Koppel de diensten die je gebruikt, zoals mail, agenda of bestanden, zodat je bots er voor jou mee kunnen werken.",
          "sections": [
            {
              "id": "connect",
              "title": "Een dienst koppelen",
              "body": "Kies een dienst en log in. Alleen je eigen chats en taken gebruiken je koppeling, en je kunt hem altijd weer loskoppelen.",
              "target": "[data-tour='connections-intro']"
            }
          ],
          "related": [
            "approvals",
            "profiles"
          ]
        },
        "insights": {
          "title": "Inzichten",
          "summary": "Zie hoe je de assistent gebruikt: chats, berichten, hulpmiddelen en kosten over een periode.",
          "sections": [
            {
              "id": "period",
              "title": "Een periode kiezen",
              "body": "Toon de afgelopen 7, 30, 90 of 365 dagen.",
              "target": "[data-tour='insights-period']"
            }
          ],
          "related": [
            "logs"
          ]
        },
        "approvals": {
          "title": "Mijn goedkeuringen",
          "summary": "Verzoeken die je deed en die op een beheerder wachten, zoals toegang tot een bot of een koppeling. Alleen je eigen verzoeken staan hier.",
          "sections": [
            {
              "id": "intro",
              "title": "Je verzoeken",
              "body": "Bij elk verzoek zie je of het nog open staat, is goedgekeurd of is afgewezen.",
              "target": "[data-tour='approvals-intro']"
            }
          ],
          "related": [
            "integrations",
            "settings"
          ]
        },
        "governance": {
          "title": "Beheer",
          "summary": "Beheerders bepalen hier wie welke bots, vaardigheden, koppelingen en ruimtes mag gebruiken, en handelen toegangsverzoeken af.",
          "audience": "admin",
          "sections": [
            {
              "id": "intro",
              "title": "Rollen en groepen",
              "body": "Geef mensen rollen en groepen. Hun toegang volgt daaruit, en elke wijziging wordt vastgelegd.",
              "target": "[data-tour='governance-intro']"
            }
          ],
          "related": [
            "approvals",
            "logs"
          ]
        },
        "logs": {
          "title": "Logboeken",
          "summary": "Technische logboeken van deze installatie, om samen met support problemen op te lossen.",
          "sections": [
            {
              "id": "controls",
              "title": "Kiezen wat je ziet",
              "body": "Kies een logbestand, hoeveel regels je ziet en welke meldingen, en kopieer ze voor support.",
              "target": "[data-tour='logs-controls']"
            }
          ],
          "related": [
            "insights",
            "settings"
          ]
        },
        "settings": {
          "title": "Instellingen",
          "summary": "Pas aan hoe SynthPulse eruitziet en voor jou werkt.",
          "sections": [
            {
              "id": "search",
              "title": "Een instelling zoeken",
              "body": "Typ een woord om direct naar de instelling te gaan die je zoekt.",
              "target": "[data-tour='settings-search']"
            },
            {
              "id": "menu",
              "title": "Onderdelen",
              "body": "Gesprek, weergave, voorkeuren en meer, elk op een eigen pagina.",
              "target": "[data-tour='settings-menu']"
            },
            {
              "id": "help",
              "title": "Hulp",
              "body": "Start de rondleiding opnieuw of lees de documentatie.",
              "target": "[data-tour='settings-help']"
            }
          ],
          "related": [
            "plugins"
          ]
        },
        "plugins": {
          "title": "Plug-ins",
          "summary": "Plug-ins voegen functies toe aan SynthPulse. Zie welke er geïnstalleerd zijn en zet ze aan of uit.",
          "parent": "settings",
          "sections": [
            {
              "id": "menu",
              "title": "Plug-ins in Instellingen",
              "body": "Open dit onderdeel om de geïnstalleerde plug-ins te zien.",
              "target": "[data-tour='settings-plugins']"
            }
          ],
          "related": [
            "settings"
          ]
        },
        "modules": {
          "title": "Modules",
          "summary": "Bekijk de lokale moduleconfiguratie, het modelgebruik en de mogelijke koppelingen. Dit scherm activeert niets.",
          "sections": [
            {
              "id": "catalogue",
              "title": "Moduleoverzicht",
              "body": "Organisatie-, facturatie- en platformbeheerders kunnen dit lezen op een organisatie-installatie. Op het centrale beheersysteem staat dit scherm uit.",
              "target": "#mainModules"
            }
          ],
          "related": [
            "apps",
            "settings"
          ]
        },
        "apps": {
          "title": "Apps",
          "summary": "Open de beschikbare toepassingen van je installatie vanuit Apps in de navigatie.",
          "sections": [
            {
              "id": "directory",
              "title": "Apps",
              "body": "Kies Apps in de navigatie. Je moet aangemeld zijn. Leden zien toegestane apps voor actieve modules; platformbeheerders zien ook ingestelde beheerapps. Iedere app controleert zelf de toegang.",
              "target": "#mainApps"
            }
          ],
          "related": [
            "modules",
            "integrations"
          ]
        },
        "msp": {
          "title": "Support",
          "summary": "Bekijk je echte urenbundel, verbruik en supportabonnementen bij jouw MSP.",
          "sections": [
            {
              "id": "overview",
              "title": "Supporturen en abonnementen bekijken",
              "body": "Bekijk je echte urenbundel, verbruik en supportabonnementen bij jouw MSP. Zonder actief contract zie je geen verzonnen uren. Support per app voegt niet automatisch uren toe aan je bundel.",
              "target": "#mspOverviewTab",
              "dynamic": true
            },
            {
              "id": "tickets",
              "title": "Tickets aanmaken, volgen en beantwoorden",
              "body": "Dien een vraag of storing rechtstreeks bij je MSP in en volg openstaande en afgehandelde tickets. Interne MSP-notities blijven verborgen. Een ingediende aanvraag is nog geen goedgekeurde wijziging of betaalopdracht.",
              "target": "#mspTicketsTab",
              "dynamic": true
            },
            {
              "id": "billing",
              "title": "Betalingen bekijken",
              "body": "Bekijk betaalverzoeken en factuurstatussen van je organisatie. Zonder geconfigureerde betaalprovider en factuur is er geen betaallink. Terugkeren uit Mollie betekent niet vanzelf dat een factuur betaald is.",
              "target": "#mspBillingTab",
              "dynamic": true
            }
          ],
          "related": [
            "apps"
          ]
        }
      },
      "tour_steps": {
        "chat": {
          "title": "Een chat starten",
          "body": "Typ hier wat je nodig hebt en druk op Enter. De assistent antwoordt in dit gesprek.",
          "target": "[data-tour='chat-composer']",
          "page": "chat"
        },
        "bots": {
          "title": "Een bot kiezen",
          "body": "Kies welke bot antwoordt. Elke bot heeft eigen instructies, vaardigheden en toegang.",
          "target": "[data-tour='chat-bot']",
          "page": "chat"
        },
        "files": {
          "title": "Een bestand toevoegen",
          "body": "Voeg documenten of afbeeldingen toe aan je bericht, zodat de assistent ermee kan werken.",
          "target": "[data-tour='chat-attach']",
          "page": "chat"
        },
        "spaces": {
          "title": "In een ruimte werken",
          "body": "Ruimtes houden de bestanden van een klus bij elkaar. Open Ruimtes in het menu om er een toe te voegen.",
          "nav": "workspaces"
        },
        "tasks": {
          "title": "Een taak plannen",
          "body": "Laat de assistent iets volgens een schema doen, zoals een dagelijkse samenvatting. Open Geplande taken in het menu.",
          "nav": "tasks"
        },
        "help": {
          "title": "Hulp krijgen",
          "body": "Weet je niet waar een pagina voor is? Deze knop legt de pagina uit waar je bent. Deze rondleiding vind je terug onder Instellingen, Hulp.",
          "target": "[data-tour='help-button']"
        },
        "organization": {
          "title": "Je organisatie",
          "body": "Zie de mensen en afdelingen van je organisatie en wie ze beheert.",
          "nav": "organization",
          "audience": "org",
          "dynamic": true
        },
        "departments": {
          "title": "Afdelingen",
          "body": "Elke afdeling heeft eigen beheerders en eigen bots, ruimtes en taken.",
          "target": "[data-tour='org-departments']",
          "page": "organization",
          "audience": "org",
          "dynamic": true
        },
        "plan": {
          "title": "Abonnement en gebruik",
          "body": "Zie je abonnement, de inbegrepen supporturen en hoeveel van je modelbudget is gebruikt.",
          "target": "[data-tour='org-plan']",
          "page": "organization",
          "audience": "org",
          "dynamic": true
        },
        "support": {
          "title": "Support",
          "body": "Stel een vraag of meld een probleem. Je tickets en hun status staan hier.",
          "nav": "support",
          "audience": "org",
          "dynamic": true
        }
      },
      "tours": {
        "first_run": [
          "chat",
          "bots",
          "files",
          "spaces",
          "tasks",
          "help"
        ],
        "org_admin": [
          "organization",
          "departments",
          "plan",
          "support"
        ]
      },
      "whats_new": {
        "0.53.0": [
          {
            "title": "Uitleg op elke pagina",
            "body": "Gebruik het vraagteken bovenin het scherm om te zien waar de pagina waar je bent voor is en hoe je hem gebruikt."
          },
          {
            "title": "Een korte rondleiding",
            "body": "Nieuw hier, of wil je het nog eens zien? Start de rondleiding onder Instellingen, Hulp, of typ /tour in een chat."
          }
        ]
      }
    }
  }
};
