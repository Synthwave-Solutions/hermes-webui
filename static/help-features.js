// Static public feature documentation. No user or deployment data.
window.SynthPulseFeatureCatalog = {
  "schema_version": 1,
  "product": "webui",
  "areas": {
    "chat": {
      "en": "Chat",
      "nl": "Chat"
    },
    "sessions": {
      "en": "Conversations",
      "nl": "Gesprekken"
    },
    "voice": {
      "en": "Voice and audio",
      "nl": "Spraak en audio"
    },
    "files": {
      "en": "Files and workspaces",
      "nl": "Bestanden en werkruimten"
    },
    "tasks": {
      "en": "Scheduled tasks",
      "nl": "Geplande taken"
    },
    "boards": {
      "en": "Task boards",
      "nl": "Taakborden"
    },
    "skills": {
      "en": "Skills",
      "nl": "Skills"
    },
    "memory": {
      "en": "Memory and knowledge",
      "nl": "Geheugen en kennis"
    },
    "bots": {
      "en": "Bots",
      "nl": "Bots"
    },
    "projects": {
      "en": "Projects",
      "nl": "Projecten"
    },
    "connections": {
      "en": "Connections and channels",
      "nl": "Koppelingen en kanalen"
    },
    "governance": {
      "en": "Access and approvals",
      "nl": "Toegang en goedkeuringen"
    },
    "settings": {
      "en": "Settings",
      "nl": "Instellingen"
    },
    "operations": {
      "en": "Status and maintenance",
      "nl": "Status en onderhoud"
    },
    "help": {
      "en": "Help and navigation",
      "nl": "Hulp en navigatie"
    },
    "planned": {
      "en": "Prepared capabilities",
      "nl": "Voorbereide mogelijkheden"
    },
    "modules": {
      "nl": "Modules",
      "en": "Modules"
    },
    "apps": {
      "nl": "Apps",
      "en": "Apps"
    }
  },
  "features": [
    {
      "id": "webui.help.navigation",
      "area": "help",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.help.navigation",
        "#btnHamburger",
        "#railExpandToggle"
      ],
      "source_refs": [
        "static/governance.js:2067",
        "static/index.html:1057",
        "static/index.html:126",
        "static/index.html:164",
        "static/index.html:165",
        "static/index.html:166",
        "static/index.html:167",
        "static/index.html:168",
        "static/index.html:169",
        "static/index.html:170",
        "static/index.html:171",
        "static/index.html:173",
        "static/index.html:175",
        "static/index.html:176",
        "static/index.html:177",
        "static/index.html:178",
        "static/index.html:180",
        "static/index.html:181",
        "static/index.html:184",
        "static/index.html:188",
        "static/index.html:189",
        "static/index.html:190",
        "static/index.html:191",
        "static/index.html:192",
        "static/index.html:193",
        "static/index.html:194",
        "static/index.html:195",
        "static/index.html:197",
        "static/index.html:199",
        "static/index.html:200",
        "static/index.html:201",
        "static/index.html:202",
        "static/index.html:204",
        "static/projects.js:232"
      ],
      "related": [
        "webui.help.tour",
        "webui.help.org_tour",
        "webui.help.page"
      ],
      "locales": {
        "en": {
          "title": "Navigate between sections",
          "purpose": "Open chat, tasks, memory and other sections from the navigation rail.",
          "when": "When you want to understand a control before changing application state.",
          "steps": [
            "Open the menu on mobile.",
            "Choose a section; expand labels if needed."
          ],
          "permissions": "Reading this static guide needs no extra permission. Described features retain their own access checks.",
          "limits": "This guide describes capabilities, not your current permissions or live service health. Search stays in this browser.",
          "example": "Open Memory without leaving the application."
        },
        "nl": {
          "title": "Tussen onderdelen navigeren",
          "purpose": "Open chat, taken, geheugen en andere onderdelen via de navigatiebalk.",
          "when": "Wanneer je een bediening wilt begrijpen voordat je de toepassing wijzigt.",
          "steps": [
            "Open het menu op mobiel.",
            "Kies een onderdeel; klap zo nodig de labels uit."
          ],
          "permissions": "Deze statische gids lezen vereist geen extra rechten. Beschreven functies behouden hun eigen toegangscontrole.",
          "limits": "Deze gids beschrijft mogelijkheden, niet je huidige rechten of actuele servicestatus. Zoeken blijft in deze browser.",
          "example": "Open Geheugen zonder de toepassing te verlaten."
        }
      }
    },
    {
      "id": "webui.help.tour",
      "area": "help",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.help.tour",
        "#helpCardStartTour"
      ],
      "source_refs": [
        "static/commands.js",
        "static/index.html:1897"
      ],
      "related": [
        "webui.help.navigation",
        "webui.help.org_tour",
        "webui.help.page"
      ],
      "locales": {
        "en": {
          "title": "Getting started tour",
          "purpose": "Follow a short guided introduction using the controls currently visible to you.",
          "when": "When you want to understand a control before changing application state.",
          "steps": [
            "Open Settings, Help.",
            "Choose Getting started; use Next, Back or Close.",
            "Composer shortcut: /tour. Review any required arguments in the command suggestions."
          ],
          "permissions": "Reading this static guide needs no extra permission. Described features retain their own access checks.",
          "limits": "This guide describes capabilities, not your current permissions or live service health. Search stays in this browser.",
          "example": "Learn where to start a conversation."
        },
        "nl": {
          "title": "Rondleiding voor beginners",
          "purpose": "Volg een korte introductie langs de bediening die voor jou zichtbaar is.",
          "when": "Wanneer je een bediening wilt begrijpen voordat je de toepassing wijzigt.",
          "steps": [
            "Open Instellingen, Hulp.",
            "Kies Aan de slag; gebruik Volgende, Terug of Sluiten.",
            "Snelopdracht in het berichtveld: /tour. Controleer eventuele argumenten in de opdrachtsuggesties."
          ],
          "permissions": "Deze statische gids lezen vereist geen extra rechten. Beschreven functies behouden hun eigen toegangscontrole.",
          "limits": "Deze gids beschrijft mogelijkheden, niet je huidige rechten of actuele servicestatus. Zoeken blijft in deze browser.",
          "example": "Leer waar je een gesprek begint."
        }
      }
    },
    {
      "id": "webui.help.org_tour",
      "area": "help",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.help.org_tour",
        "#helpCardStartOrgTour"
      ],
      "source_refs": [
        "static/index.html:1898"
      ],
      "related": [
        "webui.help.navigation",
        "webui.help.tour",
        "webui.help.page"
      ],
      "locales": {
        "en": {
          "title": "Organisation tour",
          "purpose": "Review the organisation management controls available to your role.",
          "when": "When you want to understand a control before changing application state.",
          "steps": [
            "Open Settings, Help.",
            "If offered, choose the organisation admin tour."
          ],
          "permissions": "Reading this static guide needs no extra permission. Described features retain their own access checks.",
          "limits": "This guide describes capabilities, not your current permissions or live service health. Search stays in this browser.",
          "example": "Review access controls before adding a colleague."
        },
        "nl": {
          "title": "Rondleiding voor organisatiebeheer",
          "purpose": "Bekijk de organisatiebediening die voor jouw rol beschikbaar is.",
          "when": "Wanneer je een bediening wilt begrijpen voordat je de toepassing wijzigt.",
          "steps": [
            "Open Instellingen, Hulp.",
            "Kies indien beschikbaar de rondleiding voor organisatiebeheerders."
          ],
          "permissions": "Deze statische gids lezen vereist geen extra rechten. Beschreven functies behouden hun eigen toegangscontrole.",
          "limits": "Deze gids beschrijft mogelijkheden, niet je huidige rechten of actuele servicestatus. Zoeken blijft in deze browser.",
          "example": "Bekijk toegangsbeheer voordat je een collega toevoegt."
        }
      }
    },
    {
      "id": "webui.help.page",
      "area": "help",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.help.page",
        "#btnPageHelp",
        "#helpCardExplain"
      ],
      "source_refs": [
        "static/commands.js",
        "static/index.html:148",
        "static/index.html:1909"
      ],
      "related": [
        "webui.help.navigation",
        "webui.help.tour",
        "webui.help.org_tour"
      ],
      "locales": {
        "en": {
          "title": "Explain this page",
          "purpose": "Walk through interactive explanations of every documented feature associated with the current page.",
          "when": "When you want to understand a control before changing application state.",
          "steps": [
            "Choose the question-mark help button.",
            "Use Next feature or choose a topic directly. Switch between Dutch and English and read the complete explanation.",
            "Visible controls are highlighted. For a missing control, the guide explains the context or prerequisites that may be needed.",
            "Composer shortcut: /explain. Review any required arguments in the command suggestions."
          ],
          "permissions": "Reading this static guide needs no extra permission. Described features retain their own access checks.",
          "limits": "This guide describes capabilities, not your current permissions or live service health. Search stays in this browser.",
          "example": "Understand the task screen before editing a schedule."
        },
        "nl": {
          "title": "Leg deze pagina uit",
          "purpose": "Doorloop interactieve uitleg van alle gedocumenteerde functies die bij de huidige pagina horen.",
          "when": "Wanneer je een bediening wilt begrijpen voordat je de toepassing wijzigt.",
          "steps": [
            "Kies de hulpknop met het vraagteken.",
            "Doorloop de functies met Volgende functie of kies direct een onderwerp. Wissel tussen Nederlands en Engels en lees de volledige uitleg.",
            "Zichtbare bedieningen worden aangewezen. Bij een ontbrekende bediening lees je welke context of voorwaarden nodig kunnen zijn.",
            "Snelopdracht in het berichtveld: /explain. Controleer eventuele argumenten in de opdrachtsuggesties."
          ],
          "permissions": "Deze statische gids lezen vereist geen extra rechten. Beschreven functies behouden hun eigen toegangscontrole.",
          "limits": "Deze gids beschrijft mogelijkheden, niet je huidige rechten of actuele servicestatus. Zoeken blijft in deze browser.",
          "example": "Begrijp het takenscherm voordat je een planning wijzigt."
        }
      }
    },
    {
      "id": "webui.help.guide",
      "area": "help",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.help.guide",
        "#helpCardGuide"
      ],
      "source_refs": [
        "static/index.html:1911"
      ],
      "related": [
        "webui.help.navigation",
        "webui.help.tour",
        "webui.help.org_tour"
      ],
      "locales": {
        "en": {
          "title": "Search the feature guide",
          "purpose": "Find individual controls, examples and availability in Dutch or English.",
          "when": "When you want to understand a control before changing application state.",
          "steps": [
            "Open Feature guide in Help.",
            "Search, filter by area or availability, then choose a result.",
            "Choose Start interactive guide for a feature, or Guide through these results for the filtered selection.",
            "Use Previous, Next feature and Choose a feature; each topic includes instructions, access, limits and an example.",
            "Switch language or download the catalog."
          ],
          "permissions": "Reading this static guide needs no extra permission. Described features retain their own access checks.",
          "limits": "This guide describes capabilities, not your current permissions or live service health. Search stays in this browser. The tour does not perform the instructions. Choosing a topic opens its relevant section. For controls in a closed form or menu, the guide points to the entry and explains the next step. Unsaved edits are preserved; planned controls are explained without highlighting.",
          "example": "Search for notification mute and read its limits."
        },
        "nl": {
          "title": "Zoeken in de functiegids",
          "purpose": "Vind afzonderlijke bedieningen, voorbeelden en beschikbaarheid in Nederlands of Engels.",
          "when": "Wanneer je een bediening wilt begrijpen voordat je de toepassing wijzigt.",
          "steps": [
            "Open Functiegids bij Hulp.",
            "Zoek, filter op onderdeel of beschikbaarheid en kies een resultaat.",
            "Kies Interactieve uitleg starten bij de functie, of Rondleiding langs deze resultaten voor je selectie.",
            "Gebruik Vorige, Volgende functie en Kies een functie; lees per functie ook de stappen, toegang, grenzen en het voorbeeld.",
            "Wissel van taal of download de catalogus."
          ],
          "permissions": "Deze statische gids lezen vereist geen extra rechten. Beschreven functies behouden hun eigen toegangscontrole.",
          "limits": "Deze gids beschrijft mogelijkheden, niet je huidige rechten of actuele servicestatus. Zoeken blijft in deze browser. De rondleiding voert geen stappen uit. Een onderwerp kiezen opent het bijbehorende onderdeel. Bij een gesloten formulier of menu wijst de gids de ingang aan en legt de vervolgstap uit. Niet-opgeslagen wijzigingen blijven behouden; geplande bedieningen krijgen uitleg zonder markering.",
          "example": "Zoek naar meldingen dempen en lees de beperkingen."
        }
      }
    },
    {
      "id": "webui.help.confirm",
      "area": "help",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.help.confirm",
        "#appDialogClose",
        "#appDialogInput",
        "#appDialogCancel",
        "#appDialogConfirm"
      ],
      "source_refs": [
        "static/index.html:2023",
        "static/index.html:2028",
        "static/index.html:2030",
        "static/index.html:2031"
      ],
      "related": [
        "webui.help.navigation",
        "webui.help.tour",
        "webui.help.org_tour"
      ],
      "locales": {
        "en": {
          "title": "Confirm or cancel an action",
          "purpose": "Review a dialog before accepting a change.",
          "when": "When you want to understand a control before changing application state.",
          "steps": [
            "Read the action and any requested value.",
            "Confirm to proceed or cancel to leave it unchanged."
          ],
          "permissions": "Reading this static guide needs no extra permission. Described features retain their own access checks.",
          "limits": "This guide describes capabilities, not your current permissions or live service health. Search stays in this browser.",
          "example": "Cancel deletion when the wrong conversation is selected."
        },
        "nl": {
          "title": "Een actie bevestigen of annuleren",
          "purpose": "Bekijk een dialoog voordat je een wijziging accepteert.",
          "when": "Wanneer je een bediening wilt begrijpen voordat je de toepassing wijzigt.",
          "steps": [
            "Lees de actie en een eventueel gevraagde waarde.",
            "Bevestig om door te gaan of annuleer om niets te wijzigen."
          ],
          "permissions": "Deze statische gids lezen vereist geen extra rechten. Beschreven functies behouden hun eigen toegangscontrole.",
          "limits": "Deze gids beschrijft mogelijkheden, niet je huidige rechten of actuele servicestatus. Zoeken blijft in deze browser.",
          "example": "Annuleer verwijderen wanneer het verkeerde gesprek is gekozen."
        }
      }
    },
    {
      "id": "webui.chat.send",
      "area": "chat",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.chat.send",
        "#queuePill",
        "#msg",
        "#btnSend"
      ],
      "source_refs": [
        "static/commands.js",
        "static/index.html:621",
        "static/index.html:646",
        "static/index.html:780"
      ],
      "related": [
        "webui.chat.normal",
        "webui.chat.super",
        "webui.chat.model"
      ],
      "locales": {
        "en": {
          "title": "Send, stop and queue messages",
          "purpose": "Send your draft to the active conversation and manage a running response.",
          "when": "While preparing a request or reviewing a response in the active conversation.",
          "steps": [
            "Wait for the conversation to load.",
            "Write a message and choose Send.",
            "While busy, use the offered queue or interruption action; inspect the queue pill.",
            "Composer shortcut: /stop. Review any required arguments in the command suggestions."
          ],
          "permissions": "Work in a conversation you can access. Tools and models still follow your permissions.",
          "limits": "Model output may be wrong. Review results before using them.",
          "example": "Ask for a summary, then queue a follow-up."
        },
        "nl": {
          "title": "Berichten sturen, stoppen en in de wachtrij zetten",
          "purpose": "Stuur je concept naar het actieve gesprek en beheer een lopend antwoord.",
          "when": "Bij het voorbereiden van een verzoek of beoordelen van een antwoord in het actieve gesprek.",
          "steps": [
            "Wacht tot het gesprek geladen is.",
            "Schrijf een bericht en kies Versturen.",
            "Gebruik tijdens uitvoering de aangeboden wachtrij- of onderbreekactie; bekijk de wachtrijknop.",
            "Snelopdracht in het berichtveld: /stop. Controleer eventuele argumenten in de opdrachtsuggesties."
          ],
          "permissions": "Werk in een gesprek waartoe je toegang hebt. Tools en modellen blijven gebonden aan je rechten.",
          "limits": "Modeluitvoer kan onjuist zijn. Controleer resultaten voor gebruik.",
          "example": "Vraag om een samenvatting en zet daarna een vervolgvraag klaar."
        }
      }
    },
    {
      "id": "webui.chat.normal",
      "area": "chat",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.chat.normal",
        "#chatModeNormal"
      ],
      "source_refs": [
        "static/index.html:459"
      ],
      "related": [
        "webui.chat.send",
        "webui.chat.super",
        "webui.chat.model"
      ],
      "locales": {
        "en": {
          "title": "Normal bot mode",
          "purpose": "Work with the selected bot and its configured instructions.",
          "when": "While preparing a request or reviewing a response in the active conversation.",
          "steps": [
            "Select Normal.",
            "Check the bot name before sending your message."
          ],
          "permissions": "Work in a conversation you can access. Tools and models still follow your permissions.",
          "limits": "Model output may be wrong. Review results before using them.",
          "example": "Ask the selected finance bot to explain a report."
        },
        "nl": {
          "title": "Normale botmodus",
          "purpose": "Werk met de gekozen bot en de ingestelde instructies.",
          "when": "Bij het voorbereiden van een verzoek of beoordelen van een antwoord in het actieve gesprek.",
          "steps": [
            "Kies Normaal.",
            "Controleer de botnaam voordat je het bericht verstuurt."
          ],
          "permissions": "Werk in een gesprek waartoe je toegang hebt. Tools en modellen blijven gebonden aan je rechten.",
          "limits": "Modeluitvoer kan onjuist zijn. Controleer resultaten voor gebruik.",
          "example": "Vraag de gekozen financiële bot om een rapport uit te leggen."
        }
      }
    },
    {
      "id": "webui.chat.super",
      "area": "chat",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.chat.super",
        "#chatModeSuper"
      ],
      "source_refs": [
        "static/index.html:460"
      ],
      "related": [
        "webui.chat.send",
        "webui.chat.normal",
        "webui.chat.model"
      ],
      "locales": {
        "en": {
          "title": "Super mode",
          "purpose": "Use the broader agent mode instead of a single selected bot.",
          "when": "While preparing a request or reviewing a response in the active conversation.",
          "steps": [
            "Select Super if available.",
            "Review the mode and tool access before sending."
          ],
          "permissions": "Work in a conversation you can access. Tools and models still follow your permissions.",
          "limits": "Model output may be wrong. Review results before using them.",
          "example": "Coordinate a task that crosses several toolsets."
        },
        "nl": {
          "title": "Supermodus",
          "purpose": "Gebruik de bredere agentmodus in plaats van één gekozen bot.",
          "when": "Bij het voorbereiden van een verzoek of beoordelen van een antwoord in het actieve gesprek.",
          "steps": [
            "Kies Super indien beschikbaar.",
            "Controleer de modus en tooltoegang voordat je verstuurt."
          ],
          "permissions": "Werk in een gesprek waartoe je toegang hebt. Tools en modellen blijven gebonden aan je rechten.",
          "limits": "Modeluitvoer kan onjuist zijn. Controleer resultaten voor gebruik.",
          "example": "Coördineer een taak die meerdere toolsets gebruikt."
        }
      }
    },
    {
      "id": "webui.chat.model",
      "area": "chat",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.chat.model",
        "#composerModelChip",
        "#modelSelect",
        "#composerMobileModelAction"
      ],
      "source_refs": [
        "static/commands.js",
        "static/index.html:703",
        "static/index.html:708",
        "static/index.html:789"
      ],
      "related": [
        "webui.chat.send",
        "webui.chat.normal",
        "webui.chat.super"
      ],
      "locales": {
        "en": {
          "title": "Conversation model",
          "purpose": "Choose the model used for this conversation.",
          "when": "While preparing a request or reviewing a response in the active conversation.",
          "steps": [
            "Open the model chip or mobile configuration.",
            "Choose an available model and verify the selected label.",
            "Composer shortcut: /model. Review any required arguments in the command suggestions."
          ],
          "permissions": "Work in a conversation you can access. Tools and models still follow your permissions.",
          "limits": "Model output may be wrong. Review results before using them.",
          "example": "Use a faster model for a short rewrite."
        },
        "nl": {
          "title": "Gespreksmodel",
          "purpose": "Kies het model voor dit gesprek.",
          "when": "Bij het voorbereiden van een verzoek of beoordelen van een antwoord in het actieve gesprek.",
          "steps": [
            "Open de modelknop of mobiele configuratie.",
            "Kies een beschikbaar model en controleer het label.",
            "Snelopdracht in het berichtveld: /model. Controleer eventuele argumenten in de opdrachtsuggesties."
          ],
          "permissions": "Werk in een gesprek waartoe je toegang hebt. Tools en modellen blijven gebonden aan je rechten.",
          "limits": "Modeluitvoer kan onjuist zijn. Controleer resultaten voor gebruik.",
          "example": "Gebruik een sneller model voor een korte herschrijving."
        }
      }
    },
    {
      "id": "webui.chat.reasoning",
      "area": "chat",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.chat.reasoning",
        "#composerReasoningChip",
        "#composerMobileReasoningAction"
      ],
      "source_refs": [
        "static/commands.js",
        "static/index.html:735",
        "static/index.html:797"
      ],
      "related": [
        "webui.chat.send",
        "webui.chat.normal",
        "webui.chat.super"
      ],
      "locales": {
        "en": {
          "title": "Reasoning effort",
          "purpose": "Choose a supported reasoning level for the selected model.",
          "when": "While preparing a request or reviewing a response in the active conversation.",
          "steps": [
            "Open the reasoning chip.",
            "Select an offered level; unsupported models may hide it.",
            "Composer shortcut: /reasoning. Review any required arguments in the command suggestions."
          ],
          "permissions": "Work in a conversation you can access. Tools and models still follow your permissions.",
          "limits": "Model output may be wrong. Review results before using them.",
          "example": "Use a higher level for a complex comparison."
        },
        "nl": {
          "title": "Redeneerniveau",
          "purpose": "Kies een ondersteund redeneerniveau voor het gekozen model.",
          "when": "Bij het voorbereiden van een verzoek of beoordelen van een antwoord in het actieve gesprek.",
          "steps": [
            "Open de redeneerknop.",
            "Kies een aangeboden niveau; niet-ondersteunde modellen kunnen dit verbergen.",
            "Snelopdracht in het berichtveld: /reasoning. Controleer eventuele argumenten in de opdrachtsuggesties."
          ],
          "permissions": "Werk in een gesprek waartoe je toegang hebt. Tools en modellen blijven gebonden aan je rechten.",
          "limits": "Modeluitvoer kan onjuist zijn. Controleer resultaten voor gebruik.",
          "example": "Gebruik een hoger niveau voor een complexe vergelijking."
        }
      }
    },
    {
      "id": "webui.chat.quota",
      "area": "chat",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.chat.quota",
        "#providerQuotaChip",
        "#composerMobileQuotaAction"
      ],
      "source_refs": [
        "static/index.html:730",
        "static/index.html:793"
      ],
      "related": [
        "webui.chat.send",
        "webui.chat.normal",
        "webui.chat.super"
      ],
      "locales": {
        "en": {
          "title": "Provider quota",
          "purpose": "Inspect the available provider quota information.",
          "when": "While preparing a request or reviewing a response in the active conversation.",
          "steps": [
            "Open the quota chip.",
            "Read the provider and refresh time before interpreting the values."
          ],
          "permissions": "Work in a conversation you can access. Tools and models still follow your permissions.",
          "limits": "Model output may be wrong. Review results before using them.",
          "example": "Check quota when requests are being limited."
        },
        "nl": {
          "title": "Providerquota",
          "purpose": "Bekijk de beschikbare informatie over providerquota.",
          "when": "Bij het voorbereiden van een verzoek of beoordelen van een antwoord in het actieve gesprek.",
          "steps": [
            "Open de quotaknop.",
            "Lees provider en ververstijd voordat je de waarden interpreteert."
          ],
          "permissions": "Werk in een gesprek waartoe je toegang hebt. Tools en modellen blijven gebonden aan je rechten.",
          "limits": "Modeluitvoer kan onjuist zijn. Controleer resultaten voor gebruik.",
          "example": "Controleer quota wanneer verzoeken worden beperkt."
        }
      }
    },
    {
      "id": "webui.chat.context",
      "area": "chat",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.chat.context",
        "#ctxIndicator",
        "#ctxCompressBtn",
        "#composerMobileCtxCompressBtn"
      ],
      "source_refs": [
        "static/commands.js",
        "static/index.html:759",
        "static/index.html:775",
        "static/index.html:809",
        "static/ui.js:765"
      ],
      "related": [
        "webui.chat.send",
        "webui.chat.normal",
        "webui.chat.super"
      ],
      "locales": {
        "en": {
          "title": "Context usage and compression",
          "purpose": "Inspect context usage and request compression of older conversation content.",
          "when": "While preparing a request or reviewing a response in the active conversation.",
          "steps": [
            "Open the context indicator.",
            "Choose Compress when appropriate and wait for completion.",
            "Use recovery if compression reports a recoverable failure.",
            "Composer shortcut: /compress. Review any required arguments in the command suggestions.",
            "Composer shortcut: /compact. Review any required arguments in the command suggestions."
          ],
          "permissions": "Work in a conversation you can access. Tools and models still follow your permissions.",
          "limits": "Model output may be wrong. Review results before using them.",
          "example": "Make room in a long conversation before a new task."
        },
        "nl": {
          "title": "Contextgebruik en comprimeren",
          "purpose": "Bekijk contextgebruik en vraag om oudere gespreksinhoud te comprimeren.",
          "when": "Bij het voorbereiden van een verzoek of beoordelen van een antwoord in het actieve gesprek.",
          "steps": [
            "Open de contextindicator.",
            "Kies Comprimeren wanneer passend en wacht op voltooiing.",
            "Gebruik herstel als comprimeren een herstelbare fout meldt.",
            "Snelopdracht in het berichtveld: /compress. Controleer eventuele argumenten in de opdrachtsuggesties.",
            "Snelopdracht in het berichtveld: /compact. Controleer eventuele argumenten in de opdrachtsuggesties."
          ],
          "permissions": "Werk in een gesprek waartoe je toegang hebt. Tools en modellen blijven gebonden aan je rechten.",
          "limits": "Modeluitvoer kan onjuist zijn. Controleer resultaten voor gebruik.",
          "example": "Maak ruimte in een lang gesprek voor een nieuwe taak."
        }
      }
    },
    {
      "id": "webui.chat.tools",
      "area": "chat",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.chat.tools",
        "#composerToolsetsChip",
        "#toolsetsInput",
        "#toolsetsApplyBtn",
        "#toolsetsClearBtn"
      ],
      "source_refs": [
        "static/index.html:748",
        "static/index.html:827",
        "static/index.html:830",
        "static/index.html:831"
      ],
      "related": [
        "webui.chat.send",
        "webui.chat.normal",
        "webui.chat.super"
      ],
      "locales": {
        "en": {
          "title": "Session toolsets",
          "purpose": "Limit which configured toolsets are requested for the session.",
          "when": "While preparing a request or reviewing a response in the active conversation.",
          "steps": [
            "Open Toolsets.",
            "Select or enter available toolsets and apply.",
            "Clear the override to return to the configured default."
          ],
          "permissions": "Work in a conversation you can access. Tools and models still follow your permissions.",
          "limits": "Model output may be wrong. Review results before using them.",
          "example": "Keep a writing conversation limited to the tools it needs."
        },
        "nl": {
          "title": "Toolsets voor het gesprek",
          "purpose": "Beperk welke ingestelde toolsets voor het gesprek worden aangevraagd.",
          "when": "Bij het voorbereiden van een verzoek of beoordelen van een antwoord in het actieve gesprek.",
          "steps": [
            "Open Toolsets.",
            "Kies of vul beschikbare toolsets in en pas toe.",
            "Wis de afwijkende instelling om naar de ingestelde standaard terug te gaan."
          ],
          "permissions": "Werk in een gesprek waartoe je toegang hebt. Tools en modellen blijven gebonden aan je rechten.",
          "limits": "Modeluitvoer kan onjuist zijn. Controleer resultaten voor gebruik.",
          "example": "Beperk een schrijfgesprek tot de benodigde tools."
        }
      }
    },
    {
      "id": "webui.chat.attach",
      "area": "chat",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.chat.attach",
        "#fileInput",
        "#btnAttach"
      ],
      "source_refs": [
        "static/index.html:649",
        "static/index.html:650"
      ],
      "related": [
        "webui.chat.send",
        "webui.chat.normal",
        "webui.chat.super"
      ],
      "locales": {
        "en": {
          "title": "Attach files",
          "purpose": "Add files as context for the next message.",
          "when": "While preparing a request or reviewing a response in the active conversation.",
          "steps": [
            "Choose Attach and select files.",
            "Review attachment names and remove unwanted files before sending."
          ],
          "permissions": "Work in a conversation you can access. Tools and models still follow your permissions.",
          "limits": "Model output may be wrong. Review results before using them.",
          "example": "Attach a report and ask for its key points."
        },
        "nl": {
          "title": "Bestanden bijvoegen",
          "purpose": "Voeg bestanden toe als context voor het volgende bericht.",
          "when": "Bij het voorbereiden van een verzoek of beoordelen van een antwoord in het actieve gesprek.",
          "steps": [
            "Kies Bijvoegen en selecteer bestanden.",
            "Controleer bestandsnamen en verwijder ongewenste bestanden voordat je verstuurt."
          ],
          "permissions": "Werk in een gesprek waartoe je toegang hebt. Tools en modellen blijven gebonden aan je rechten.",
          "limits": "Modeluitvoer kan onjuist zijn. Controleer resultaten voor gebruik.",
          "example": "Voeg een rapport toe en vraag naar de hoofdpunten."
        }
      }
    },
    {
      "id": "webui.chat.prompts",
      "area": "chat",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.chat.prompts",
        "#btnSavedPrompts"
      ],
      "source_refs": [
        "static/index.html:653"
      ],
      "related": [
        "webui.chat.send",
        "webui.chat.normal",
        "webui.chat.super"
      ],
      "locales": {
        "en": {
          "title": "Saved prompts",
          "purpose": "Reuse a saved instruction in the composer.",
          "when": "While preparing a request or reviewing a response in the active conversation.",
          "steps": [
            "Open Saved prompts.",
            "Select a prompt, review the inserted text and fill in its details before sending."
          ],
          "permissions": "Work in a conversation you can access. Tools and models still follow your permissions.",
          "limits": "Model output may be wrong. Review results before using them.",
          "example": "Reuse your weekly summary format."
        },
        "nl": {
          "title": "Opgeslagen prompts",
          "purpose": "Gebruik een opgeslagen instructie opnieuw in het berichtveld.",
          "when": "Bij het voorbereiden van een verzoek of beoordelen van een antwoord in het actieve gesprek.",
          "steps": [
            "Open Opgeslagen prompts.",
            "Kies een prompt, controleer de ingevoegde tekst en vul details aan voordat je verstuurt."
          ],
          "permissions": "Werk in een gesprek waartoe je toegang hebt. Tools en modellen blijven gebonden aan je rechten.",
          "limits": "Modeluitvoer kan onjuist zijn. Controleer resultaten voor gebruik.",
          "example": "Gebruik je vaste indeling voor een weeksamenvatting."
        }
      }
    },
    {
      "id": "webui.chat.people",
      "area": "chat",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.chat.people",
        "#composerPeopleChip",
        "#groupPeopleFilter",
        "#groupPeopleModalSubmit"
      ],
      "source_refs": [
        "static/index.html:2083",
        "static/index.html:2088",
        "static/index.html:2089",
        "static/index.html:742"
      ],
      "related": [
        "webui.chat.send",
        "webui.chat.normal",
        "webui.chat.super"
      ],
      "locales": {
        "en": {
          "title": "Group participants",
          "purpose": "Manage the people participating in a shared conversation.",
          "when": "While preparing a request or reviewing a response in the active conversation.",
          "steps": [
            "Open People.",
            "Search permitted colleagues, review the selection and save."
          ],
          "permissions": "Work in a conversation you can access. Tools and models still follow your permissions.",
          "limits": "Model output may be wrong. Review results before using them.",
          "example": "Invite a project colleague to the discussion."
        },
        "nl": {
          "title": "Deelnemers aan een groepsgesprek",
          "purpose": "Beheer de mensen die deelnemen aan een gedeeld gesprek.",
          "when": "Bij het voorbereiden van een verzoek of beoordelen van een antwoord in het actieve gesprek.",
          "steps": [
            "Open Personen.",
            "Zoek toegestane collega’s, controleer de selectie en sla op."
          ],
          "permissions": "Werk in een gesprek waartoe je toegang hebt. Tools en modellen blijven gebonden aan je rechten.",
          "limits": "Modeluitvoer kan onjuist zijn. Controleer resultaten voor gebruik.",
          "example": "Nodig een projectcollega uit voor het gesprek."
        }
      }
    },
    {
      "id": "webui.chat.mentions",
      "area": "chat",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.chat.mentions"
      ],
      "source_refs": [
        "static/messages.js"
      ],
      "related": [
        "webui.chat.send",
        "webui.chat.normal",
        "webui.chat.super"
      ],
      "locales": {
        "en": {
          "title": "Bot mentions and default routing",
          "purpose": "Direct a group message to a bot using its mention; unmentioned messages follow the conversation’s configured default routing.",
          "when": "While preparing a request or reviewing a response in the active conversation.",
          "steps": [
            "Type the bot mention and select the matching bot.",
            "Check the recipient before sending; read the attribution on the reply."
          ],
          "permissions": "Work in a conversation you can access. Tools and models still follow your permissions.",
          "limits": "Model output may be wrong. Review results before using them.",
          "example": "Ask a named bot a question without changing the group’s default."
        },
        "nl": {
          "title": "Botvermeldingen en standaardroutering",
          "purpose": "Richt een groepsbericht aan een bot via een vermelding; berichten zonder vermelding volgen de ingestelde standaardroutering van het gesprek.",
          "when": "Bij het voorbereiden van een verzoek of beoordelen van een antwoord in het actieve gesprek.",
          "steps": [
            "Typ de botvermelding en kies de passende bot.",
            "Controleer de ontvanger voor versturen; lees de toeschrijving bij het antwoord."
          ],
          "permissions": "Werk in een gesprek waartoe je toegang hebt. Tools en modellen blijven gebonden aan je rechten.",
          "limits": "Modeluitvoer kan onjuist zijn. Controleer resultaten voor gebruik.",
          "example": "Stel een genoemde bot een vraag zonder de groepsstandaard te wijzigen."
        }
      }
    },
    {
      "id": "webui.chat.scroll",
      "area": "chat",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.chat.scroll",
        "#jumpToSessionStartBtn",
        "#scrollToBottomBtn",
        "#outlineToggleBtn"
      ],
      "source_refs": [
        "static/index.html:2210",
        "static/index.html:474",
        "static/index.html:475",
        "static/index.html:477",
        "static/outline.js:226",
        "static/ui.js:1971"
      ],
      "related": [
        "webui.chat.send",
        "webui.chat.normal",
        "webui.chat.super"
      ],
      "locales": {
        "en": {
          "title": "Conversation navigation",
          "purpose": "Move to the first message, latest message or a specific turn.",
          "when": "While preparing a request or reviewing a response in the active conversation.",
          "steps": [
            "Use the start and end jump buttons.",
            "Select a question in the conversation outline to jump to that turn."
          ],
          "permissions": "Work in a conversation you can access. Tools and models still follow your permissions.",
          "limits": "Model output may be wrong. Review results before using them.",
          "example": "Find the original request in a long thread."
        },
        "nl": {
          "title": "Door het gesprek navigeren",
          "purpose": "Ga naar het eerste bericht, laatste bericht of een specifieke beurt.",
          "when": "Bij het voorbereiden van een verzoek of beoordelen van een antwoord in het actieve gesprek.",
          "steps": [
            "Gebruik de knoppen voor begin en einde.",
            "Kies een vraag in het gespreksoverzicht om naar die beurt te gaan."
          ],
          "permissions": "Werk in een gesprek waartoe je toegang hebt. Tools en modellen blijven gebonden aan je rechten.",
          "limits": "Modeluitvoer kan onjuist zijn. Controleer resultaten voor gebruik.",
          "example": "Vind het oorspronkelijke verzoek in een lang gesprek."
        }
      }
    },
    {
      "id": "webui.chat.copy",
      "area": "chat",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.chat.copy"
      ],
      "source_refs": [
        "static/ui.js:15404",
        "static/ui.js:17389"
      ],
      "related": [
        "webui.chat.send",
        "webui.chat.normal",
        "webui.chat.super"
      ],
      "locales": {
        "en": {
          "title": "Copy a message",
          "purpose": "Copy a message’s text for use elsewhere.",
          "when": "While preparing a request or reviewing a response in the active conversation.",
          "steps": [
            "Open the message actions.",
            "Choose Copy and review the destination before pasting."
          ],
          "permissions": "Work in a conversation you can access. Tools and models still follow your permissions.",
          "limits": "Model output may be wrong. Review results before using them.",
          "example": "Copy a reviewed draft into your editor."
        },
        "nl": {
          "title": "Een bericht kopiëren",
          "purpose": "Kopieer de tekst van een bericht voor gebruik elders.",
          "when": "Bij het voorbereiden van een verzoek of beoordelen van een antwoord in het actieve gesprek.",
          "steps": [
            "Open de berichtacties.",
            "Kies Kopiëren en controleer de bestemming voordat je plakt."
          ],
          "permissions": "Werk in een gesprek waartoe je toegang hebt. Tools en modellen blijven gebonden aan je rechten.",
          "limits": "Modeluitvoer kan onjuist zijn. Controleer resultaten voor gebruik.",
          "example": "Kopieer een gecontroleerd concept naar je editor."
        }
      }
    },
    {
      "id": "webui.chat.edit",
      "area": "chat",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.chat.edit"
      ],
      "source_refs": [
        "static/ui.js:17386"
      ],
      "related": [
        "webui.chat.send",
        "webui.chat.normal",
        "webui.chat.super"
      ],
      "locales": {
        "en": {
          "title": "Edit a sent message",
          "purpose": "Change an earlier request using the offered edit workflow.",
          "when": "While preparing a request or reviewing a response in the active conversation.",
          "steps": [
            "Choose Edit on the message.",
            "Review the changed text and the confirmation before submitting."
          ],
          "permissions": "Work in a conversation you can access. Tools and models still follow your permissions.",
          "limits": "Model output may be wrong. Review results before using them.",
          "example": "Correct a mistaken date in your request."
        },
        "nl": {
          "title": "Een verstuurd bericht bewerken",
          "purpose": "Wijzig een eerder verzoek via de aangeboden bewerkfunctie.",
          "when": "Bij het voorbereiden van een verzoek of beoordelen van een antwoord in het actieve gesprek.",
          "steps": [
            "Kies Bewerken bij het bericht.",
            "Controleer de gewijzigde tekst en bevestiging voordat je indient."
          ],
          "permissions": "Werk in een gesprek waartoe je toegang hebt. Tools en modellen blijven gebonden aan je rechten.",
          "limits": "Modeluitvoer kan onjuist zijn. Controleer resultaten voor gebruik.",
          "example": "Corrigeer een verkeerde datum in je verzoek."
        }
      }
    },
    {
      "id": "webui.chat.undo",
      "area": "chat",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.chat.undo"
      ],
      "source_refs": [
        "static/commands.js",
        "static/ui.js:17387"
      ],
      "related": [
        "webui.chat.send",
        "webui.chat.normal",
        "webui.chat.super"
      ],
      "locales": {
        "en": {
          "title": "Undo the last exchange",
          "purpose": "Remove the last conversation exchange through the offered undo action.",
          "when": "While preparing a request or reviewing a response in the active conversation.",
          "steps": [
            "Choose Undo on the latest exchange.",
            "Read the confirmation; external actions already performed are not rolled back.",
            "Composer shortcut: /undo. Review any required arguments in the command suggestions."
          ],
          "permissions": "Work in a conversation you can access. Tools and models still follow your permissions.",
          "limits": "Model output may be wrong. Review results before using them.",
          "example": "Remove an accidental question and response."
        },
        "nl": {
          "title": "De laatste uitwisseling ongedaan maken",
          "purpose": "Verwijder de laatste gespreksuitwisseling via de aangeboden herstelactie.",
          "when": "Bij het voorbereiden van een verzoek of beoordelen van een antwoord in het actieve gesprek.",
          "steps": [
            "Kies Ongedaan maken bij de laatste uitwisseling.",
            "Lees de bevestiging; al uitgevoerde externe acties worden niet teruggedraaid.",
            "Snelopdracht in het berichtveld: /undo. Controleer eventuele argumenten in de opdrachtsuggesties."
          ],
          "permissions": "Werk in een gesprek waartoe je toegang hebt. Tools en modellen blijven gebonden aan je rechten.",
          "limits": "Modeluitvoer kan onjuist zijn. Controleer resultaten voor gebruik.",
          "example": "Verwijder een per ongeluk gestelde vraag en antwoord."
        }
      }
    },
    {
      "id": "webui.chat.retry",
      "area": "chat",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.chat.retry"
      ],
      "source_refs": [
        "static/commands.js",
        "static/ui.js:17388"
      ],
      "related": [
        "webui.chat.send",
        "webui.chat.normal",
        "webui.chat.super"
      ],
      "locales": {
        "en": {
          "title": "Regenerate a response",
          "purpose": "Ask for another response to the selected request.",
          "when": "While preparing a request or reviewing a response in the active conversation.",
          "steps": [
            "Choose Regenerate.",
            "Review any warning about rerunning tools or replacing the response.",
            "Composer shortcut: /retry. Review any required arguments in the command suggestions."
          ],
          "permissions": "Work in a conversation you can access. Tools and models still follow your permissions.",
          "limits": "Model output may be wrong. Review results before using them.",
          "example": "Try another wording for a draft."
        },
        "nl": {
          "title": "Een antwoord opnieuw genereren",
          "purpose": "Vraag om een nieuw antwoord op het gekozen verzoek.",
          "when": "Bij het voorbereiden van een verzoek of beoordelen van een antwoord in het actieve gesprek.",
          "steps": [
            "Kies Opnieuw genereren.",
            "Controleer waarschuwingen over opnieuw uitgevoerde tools of vervanging van het antwoord.",
            "Snelopdracht in het berichtveld: /retry. Controleer eventuele argumenten in de opdrachtsuggesties."
          ],
          "permissions": "Werk in een gesprek waartoe je toegang hebt. Tools en modellen blijven gebonden aan je rechten.",
          "limits": "Modeluitvoer kan onjuist zijn. Controleer resultaten voor gebruik.",
          "example": "Probeer een andere formulering voor een concept."
        }
      }
    },
    {
      "id": "webui.chat.fork",
      "area": "chat",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.chat.fork"
      ],
      "source_refs": [
        "static/commands.js",
        "static/ui.js:17396"
      ],
      "related": [
        "webui.chat.send",
        "webui.chat.normal",
        "webui.chat.super"
      ],
      "locales": {
        "en": {
          "title": "Fork from a message",
          "purpose": "Start a separate conversation branch from a selected point.",
          "when": "While preparing a request or reviewing a response in the active conversation.",
          "steps": [
            "Open the message actions and choose Fork.",
            "Check the new conversation before continuing.",
            "Composer shortcut: /branch. Review any required arguments in the command suggestions."
          ],
          "permissions": "Work in a conversation you can access. Tools and models still follow your permissions.",
          "limits": "Model output may be wrong. Review results before using them.",
          "example": "Explore a different solution without continuing the same branch."
        },
        "nl": {
          "title": "Een gesprek afsplitsen vanaf een bericht",
          "purpose": "Begin een afzonderlijke gesprekstak vanaf een gekozen punt.",
          "when": "Bij het voorbereiden van een verzoek of beoordelen van een antwoord in het actieve gesprek.",
          "steps": [
            "Open de berichtacties en kies Afsplitsen.",
            "Controleer het nieuwe gesprek voordat je verdergaat.",
            "Snelopdracht in het berichtveld: /branch. Controleer eventuele argumenten in de opdrachtsuggesties."
          ],
          "permissions": "Werk in een gesprek waartoe je toegang hebt. Tools en modellen blijven gebonden aan je rechten.",
          "limits": "Modeluitvoer kan onjuist zijn. Controleer resultaten voor gebruik.",
          "example": "Verken een andere oplossing in een eigen gesprekstak."
        }
      }
    },
    {
      "id": "webui.chat.activity",
      "area": "chat",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.chat.activity"
      ],
      "source_refs": [
        "static/ui.js:14802",
        "static/ui.js:14881",
        "static/ui.js:18984"
      ],
      "related": [
        "webui.chat.send",
        "webui.chat.normal",
        "webui.chat.super"
      ],
      "locales": {
        "en": {
          "title": "Tool activity and work log",
          "purpose": "Inspect grouped tool activity and available result details.",
          "when": "While preparing a request or reviewing a response in the active conversation.",
          "steps": [
            "Expand an activity or work-log group.",
            "Read its status and output; a started action is not proof of success."
          ],
          "permissions": "Work in a conversation you can access. Tools and models still follow your permissions.",
          "limits": "Model output may be wrong. Review results before using them.",
          "example": "Check which tool produced a file."
        },
        "nl": {
          "title": "Toolactiviteit en werklog",
          "purpose": "Bekijk gegroepeerde toolactiviteit en beschikbare resultaatdetails.",
          "when": "Bij het voorbereiden van een verzoek of beoordelen van een antwoord in het actieve gesprek.",
          "steps": [
            "Klap een activiteit of werkloggroep open.",
            "Lees status en uitvoer; een gestarte actie bewijst geen succes."
          ],
          "permissions": "Werk in een gesprek waartoe je toegang hebt. Tools en modellen blijven gebonden aan je rechten.",
          "limits": "Modeluitvoer kan onjuist zijn. Controleer resultaten voor gebruik.",
          "example": "Controleer welke tool een bestand heeft gemaakt."
        }
      }
    },
    {
      "id": "webui.chat.svg",
      "area": "chat",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.chat.svg"
      ],
      "source_refs": [
        "static/messages.js"
      ],
      "related": [
        "webui.chat.send",
        "webui.chat.normal",
        "webui.chat.super"
      ],
      "locales": {
        "en": {
          "title": "Inline diagrams",
          "purpose": "View supported SVG diagrams rendered with safety restrictions.",
          "when": "While preparing a request or reviewing a response in the active conversation.",
          "steps": [
            "Open the diagram in the response.",
            "Use the accompanying text if unsupported content is removed."
          ],
          "permissions": "Work in a conversation you can access. Tools and models still follow your permissions.",
          "limits": "Model output may be wrong. Review results before using them.",
          "example": "Read a simple process diagram alongside its explanation."
        },
        "nl": {
          "title": "Diagrammen in het gesprek",
          "purpose": "Bekijk ondersteunde SVG-diagrammen met veiligheidsbeperkingen.",
          "when": "Bij het voorbereiden van een verzoek of beoordelen van een antwoord in het actieve gesprek.",
          "steps": [
            "Bekijk het diagram in het antwoord.",
            "Gebruik de begeleidende tekst als niet-ondersteunde inhoud is verwijderd."
          ],
          "permissions": "Werk in een gesprek waartoe je toegang hebt. Tools en modellen blijven gebonden aan je rechten.",
          "limits": "Modeluitvoer kan onjuist zijn. Controleer resultaten voor gebruik.",
          "example": "Lees een eenvoudig procesdiagram naast de uitleg."
        }
      }
    },
    {
      "id": "webui.chat.replay",
      "area": "chat",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.chat.replay"
      ],
      "source_refs": [
        "static/messages.js"
      ],
      "related": [
        "webui.chat.send",
        "webui.chat.normal",
        "webui.chat.super"
      ],
      "locales": {
        "en": {
          "title": "Restored activity timeline",
          "purpose": "Restore stored conversation activity after reopening or reconnecting.",
          "when": "While preparing a request or reviewing a response in the active conversation.",
          "steps": [
            "Reopen the conversation and wait for loading.",
            "Inspect restored messages and activity before continuing."
          ],
          "permissions": "Work in a conversation you can access. Tools and models still follow your permissions.",
          "limits": "Model output may be wrong. Review results before using them.",
          "example": "Return to a conversation after a browser refresh."
        },
        "nl": {
          "title": "Herstelde activiteitstijdlijn",
          "purpose": "Herstel opgeslagen gespreksactiviteit na opnieuw openen of verbinden.",
          "when": "Bij het voorbereiden van een verzoek of beoordelen van een antwoord in het actieve gesprek.",
          "steps": [
            "Open het gesprek opnieuw en wacht op laden.",
            "Bekijk herstelde berichten en activiteit voordat je verdergaat."
          ],
          "permissions": "Werk in een gesprek waartoe je toegang hebt. Tools en modellen blijven gebonden aan je rechten.",
          "limits": "Modeluitvoer kan onjuist zijn. Controleer resultaten voor gebruik.",
          "example": "Keer terug naar een gesprek na het vernieuwen van de browser."
        }
      }
    },
    {
      "id": "webui.chat.mobile",
      "area": "chat",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.chat.mobile",
        "#composerMobileConfigBtn"
      ],
      "source_refs": [
        "static/index.html:699"
      ],
      "related": [
        "webui.chat.send",
        "webui.chat.normal",
        "webui.chat.super"
      ],
      "locales": {
        "en": {
          "title": "Mobile composer options",
          "purpose": "Access model, workspace, quota, reasoning and context controls on a narrow screen.",
          "when": "While preparing a request or reviewing a response in the active conversation.",
          "steps": [
            "Open the composer configuration button.",
            "Choose the setting you need and return to your draft."
          ],
          "permissions": "Work in a conversation you can access. Tools and models still follow your permissions.",
          "limits": "Model output may be wrong. Review results before using them.",
          "example": "Change the model while using a phone."
        },
        "nl": {
          "title": "Mobiele berichtopties",
          "purpose": "Bereik model-, werkruimte-, quota-, redeneer- en contextopties op een smal scherm.",
          "when": "Bij het voorbereiden van een verzoek of beoordelen van een antwoord in het actieve gesprek.",
          "steps": [
            "Open de configuratieknop bij het berichtveld.",
            "Kies de gewenste instelling en keer terug naar je concept."
          ],
          "permissions": "Werk in een gesprek waartoe je toegang hebt. Tools en modellen blijven gebonden aan je rechten.",
          "limits": "Modeluitvoer kan onjuist zijn. Controleer resultaten voor gebruik.",
          "example": "Wijzig het model op een telefoon."
        }
      }
    },
    {
      "id": "webui.sessions.new",
      "area": "sessions",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.sessions.new",
        "#btnTitlebarNewChat",
        "#btnNewChat"
      ],
      "source_refs": [
        "static/commands.js",
        "static/index.html:136",
        "static/index.html:216"
      ],
      "related": [
        "webui.sessions.search",
        "webui.sessions.split",
        "webui.sessions.transcript"
      ],
      "locales": {
        "en": {
          "title": "New conversation",
          "purpose": "Start a separate conversation with fresh message history.",
          "when": "When organising, revisiting or transferring work from a conversation.",
          "steps": [
            "Choose New conversation.",
            "Check bot, workspace and mode before sending.",
            "Composer shortcut: /new. Review any required arguments in the command suggestions."
          ],
          "permissions": "You need access to the conversation. Sharing and deletion can require additional rights.",
          "limits": "Exported or shared content may contain conversation details. Review the destination and recipients.",
          "example": "Keep a new project question separate from an earlier topic."
        },
        "nl": {
          "title": "Nieuw gesprek",
          "purpose": "Begin een afzonderlijk gesprek met een nieuwe berichtgeschiedenis.",
          "when": "Bij het ordenen, terugvinden of overdragen van werk uit een gesprek.",
          "steps": [
            "Kies Nieuw gesprek.",
            "Controleer bot, werkruimte en modus voordat je verstuurt.",
            "Snelopdracht in het berichtveld: /new. Controleer eventuele argumenten in de opdrachtsuggesties."
          ],
          "permissions": "Je hebt toegang tot het gesprek nodig. Delen en verwijderen kunnen extra rechten vereisen.",
          "limits": "Geëxporteerde of gedeelde inhoud kan gespreksgegevens bevatten. Controleer bestemming en ontvangers.",
          "example": "Houd een nieuwe projectvraag gescheiden van een eerder onderwerp."
        }
      }
    },
    {
      "id": "webui.sessions.search",
      "area": "sessions",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.sessions.search",
        "#sessionSearch",
        "#sessionSearchClear"
      ],
      "source_refs": [
        "static/index.html:221"
      ],
      "related": [
        "webui.sessions.new",
        "webui.sessions.split",
        "webui.sessions.transcript"
      ],
      "locales": {
        "en": {
          "title": "Find conversations",
          "purpose": "Filter the conversations visible to your account.",
          "when": "When organising, revisiting or transferring work from a conversation.",
          "steps": [
            "Type in the conversation search box.",
            "Choose a result or clear the filter to see the full list."
          ],
          "permissions": "You need access to the conversation. Sharing and deletion can require additional rights.",
          "limits": "Exported or shared content may contain conversation details. Review the destination and recipients.",
          "example": "Find an earlier conversation by title."
        },
        "nl": {
          "title": "Gesprekken vinden",
          "purpose": "Filter de gesprekken die voor jouw account zichtbaar zijn.",
          "when": "Bij het ordenen, terugvinden of overdragen van werk uit een gesprek.",
          "steps": [
            "Typ in het zoekveld voor gesprekken.",
            "Kies een resultaat of wis het filter voor de volledige lijst."
          ],
          "permissions": "Je hebt toegang tot het gesprek nodig. Delen en verwijderen kunnen extra rechten vereisen.",
          "limits": "Geëxporteerde of gedeelde inhoud kan gespreksgegevens bevatten. Controleer bestemming en ontvangers.",
          "example": "Vind een eerder gesprek op titel."
        }
      }
    },
    {
      "id": "webui.sessions.split",
      "area": "sessions",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.sessions.split",
        "#btnSplitView",
        "#btnSplitExit"
      ],
      "source_refs": [
        "static/index.html:142",
        "static/split.js:121"
      ],
      "related": [
        "webui.sessions.new",
        "webui.sessions.search",
        "webui.sessions.transcript"
      ],
      "locales": {
        "en": {
          "title": "Split conversation view",
          "purpose": "View conversations side by side when the layout supports it.",
          "when": "When organising, revisiting or transferring work from a conversation.",
          "steps": [
            "Choose Split view.",
            "Select the second conversation; exit split view when finished."
          ],
          "permissions": "You need access to the conversation. Sharing and deletion can require additional rights.",
          "limits": "Exported or shared content may contain conversation details. Review the destination and recipients.",
          "example": "Compare two drafts without repeatedly switching."
        },
        "nl": {
          "title": "Gesplitste gespreksweergave",
          "purpose": "Bekijk gesprekken naast elkaar wanneer de indeling dit ondersteunt.",
          "when": "Bij het ordenen, terugvinden of overdragen van werk uit een gesprek.",
          "steps": [
            "Kies Gesplitste weergave.",
            "Kies het tweede gesprek; sluit de gesplitste weergave na afloop."
          ],
          "permissions": "Je hebt toegang tot het gesprek nodig. Delen en verwijderen kunnen extra rechten vereisen.",
          "limits": "Geëxporteerde of gedeelde inhoud kan gespreksgegevens bevatten. Controleer bestemming en ontvangers.",
          "example": "Vergelijk twee concepten zonder steeds te wisselen."
        }
      }
    },
    {
      "id": "webui.sessions.transcript",
      "area": "sessions",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.sessions.transcript",
        "#btnDownload"
      ],
      "source_refs": [
        "static/index.html:1120"
      ],
      "related": [
        "webui.sessions.new",
        "webui.sessions.search",
        "webui.sessions.split"
      ],
      "locales": {
        "en": {
          "title": "Download transcript",
          "purpose": "Save a readable transcript of the selected conversation.",
          "when": "When organising, revisiting or transferring work from a conversation.",
          "steps": [
            "Open conversation actions.",
            "Choose Download transcript and inspect the downloaded file."
          ],
          "permissions": "You need access to the conversation. Sharing and deletion can require additional rights.",
          "limits": "Exported or shared content may contain conversation details. Review the destination and recipients.",
          "example": "Keep a reviewed meeting summary locally."
        },
        "nl": {
          "title": "Gesprekstekst downloaden",
          "purpose": "Sla een leesbare tekstversie van het gekozen gesprek op.",
          "when": "Bij het ordenen, terugvinden of overdragen van werk uit een gesprek.",
          "steps": [
            "Open de gespreksacties.",
            "Kies Gesprekstekst downloaden en controleer het bestand."
          ],
          "permissions": "Je hebt toegang tot het gesprek nodig. Delen en verwijderen kunnen extra rechten vereisen.",
          "limits": "Geëxporteerde of gedeelde inhoud kan gespreksgegevens bevatten. Controleer bestemming en ontvangers.",
          "example": "Bewaar een gecontroleerde vergadersamenvatting lokaal."
        }
      }
    },
    {
      "id": "webui.sessions.json",
      "area": "sessions",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.sessions.json",
        "#btnExportJSON",
        "#btnImportJSON",
        "#importFileInput"
      ],
      "source_refs": [
        "static/index.html:1121",
        "static/index.html:1125",
        "static/index.html:1128"
      ],
      "related": [
        "webui.sessions.new",
        "webui.sessions.search",
        "webui.sessions.split"
      ],
      "locales": {
        "en": {
          "title": "Export and import conversation JSON",
          "purpose": "Transfer supported conversation data using a JSON file.",
          "when": "When organising, revisiting or transferring work from a conversation.",
          "steps": [
            "Export JSON from the selected conversation.",
            "To import, choose Import JSON and select a trusted compatible file.",
            "Check the imported conversation before continuing."
          ],
          "permissions": "You need access to the conversation. Sharing and deletion can require additional rights.",
          "limits": "Exported or shared content may contain conversation details. Review the destination and recipients.",
          "example": "Move an exported conversation into a supported installation."
        },
        "nl": {
          "title": "Gesprekken als JSON exporteren en importeren",
          "purpose": "Zet ondersteunde gespreksgegevens over via een JSON-bestand.",
          "when": "Bij het ordenen, terugvinden of overdragen van werk uit een gesprek.",
          "steps": [
            "Exporteer JSON van het gekozen gesprek.",
            "Kies voor importeren JSON importeren en selecteer een vertrouwd compatibel bestand.",
            "Controleer het geïmporteerde gesprek voordat je verdergaat."
          ],
          "permissions": "Je hebt toegang tot het gesprek nodig. Delen en verwijderen kunnen extra rechten vereisen.",
          "limits": "Geëxporteerde of gedeelde inhoud kan gespreksgegevens bevatten. Controleer bestemming en ontvangers.",
          "example": "Zet een geëxporteerd gesprek over naar een ondersteunde installatie."
        }
      }
    },
    {
      "id": "webui.sessions.html",
      "area": "sessions",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.sessions.html",
        "#btnExportHTML"
      ],
      "source_refs": [
        "static/index.html:1124"
      ],
      "related": [
        "webui.sessions.new",
        "webui.sessions.search",
        "webui.sessions.split"
      ],
      "locales": {
        "en": {
          "title": "Export conversation as HTML",
          "purpose": "Save a readable HTML version of the selected conversation.",
          "when": "When organising, revisiting or transferring work from a conversation.",
          "steps": [
            "Choose Export HTML.",
            "Review the file before sharing or storing it outside the application."
          ],
          "permissions": "You need access to the conversation. Sharing and deletion can require additional rights.",
          "limits": "Exported or shared content may contain conversation details. Review the destination and recipients.",
          "example": "Archive a completed explanation as a readable page."
        },
        "nl": {
          "title": "Een gesprek als HTML exporteren",
          "purpose": "Sla een leesbare HTML-versie van het gekozen gesprek op.",
          "when": "Bij het ordenen, terugvinden of overdragen van werk uit een gesprek.",
          "steps": [
            "Kies HTML exporteren.",
            "Controleer het bestand voordat je het buiten de toepassing deelt of bewaart."
          ],
          "permissions": "Je hebt toegang tot het gesprek nodig. Delen en verwijderen kunnen extra rechten vereisen.",
          "limits": "Geëxporteerde of gedeelde inhoud kan gespreksgegevens bevatten. Controleer bestemming en ontvangers.",
          "example": "Archiveer een afgeronde uitleg als leesbare pagina."
        }
      }
    },
    {
      "id": "webui.sessions.share",
      "area": "sessions",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.sessions.share",
        "#btnShareSession",
        "#btnStopSharingSession"
      ],
      "source_refs": [
        "static/index.html:1122",
        "static/index.html:1123"
      ],
      "related": [
        "webui.sessions.new",
        "webui.sessions.search",
        "webui.sessions.split"
      ],
      "locales": {
        "en": {
          "title": "Share and revoke a conversation",
          "purpose": "Create or revoke a supported sharing link for the selected conversation.",
          "when": "When organising, revisiting or transferring work from a conversation.",
          "steps": [
            "Choose Share and review the audience.",
            "Copy the link only after confirming its scope.",
            "Choose Stop sharing to revoke future access through that link."
          ],
          "permissions": "You need access to the conversation. Sharing and deletion can require additional rights.",
          "limits": "Exported or shared content may contain conversation details. Review the destination and recipients.",
          "example": "Share a reviewed explanation with a permitted colleague."
        },
        "nl": {
          "title": "Een gesprek delen en delen intrekken",
          "purpose": "Maak een ondersteunde deellink voor het gekozen gesprek of trek deze in.",
          "when": "Bij het ordenen, terugvinden of overdragen van werk uit een gesprek.",
          "steps": [
            "Kies Delen en controleer de doelgroep.",
            "Kopieer de link pas nadat je de scope hebt gecontroleerd.",
            "Kies Delen stoppen om toekomstige toegang via die link in te trekken."
          ],
          "permissions": "Je hebt toegang tot het gesprek nodig. Delen en verwijderen kunnen extra rechten vereisen.",
          "limits": "Geëxporteerde of gedeelde inhoud kan gespreksgegevens bevatten. Controleer bestemming en ontvangers.",
          "example": "Deel een gecontroleerde uitleg met een toegestane collega."
        }
      }
    },
    {
      "id": "webui.sessions.clear",
      "area": "sessions",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.sessions.clear",
        "#btnClearConvModal"
      ],
      "source_refs": [
        "static/commands.js",
        "static/index.html:1126"
      ],
      "related": [
        "webui.sessions.new",
        "webui.sessions.search",
        "webui.sessions.split"
      ],
      "locales": {
        "en": {
          "title": "Clear conversation",
          "purpose": "Clear the selected conversation using its confirmation workflow.",
          "when": "When organising, revisiting or transferring work from a conversation.",
          "steps": [
            "Choose Clear conversation.",
            "Verify the conversation name and confirm only when its content is no longer needed.",
            "Composer shortcut: /clear. Review any required arguments in the command suggestions."
          ],
          "permissions": "You need access to the conversation. Sharing and deletion can require additional rights.",
          "limits": "Exported or shared content may contain conversation details. Review the destination and recipients.",
          "example": "Remove a disposable test conversation’s content."
        },
        "nl": {
          "title": "Een gesprek leegmaken",
          "purpose": "Maak het gekozen gesprek leeg via de bevestigingsprocedure.",
          "when": "Bij het ordenen, terugvinden of overdragen van werk uit een gesprek.",
          "steps": [
            "Kies Gesprek leegmaken.",
            "Controleer de gespreksnaam en bevestig alleen wanneer de inhoud niet meer nodig is.",
            "Snelopdracht in het berichtveld: /clear. Controleer eventuele argumenten in de opdrachtsuggesties."
          ],
          "permissions": "Je hebt toegang tot het gesprek nodig. Delen en verwijderen kunnen extra rechten vereisen.",
          "limits": "Geëxporteerde of gedeelde inhoud kan gespreksgegevens bevatten. Controleer bestemming en ontvangers.",
          "example": "Verwijder de inhoud van een tijdelijk testgesprek."
        }
      }
    },
    {
      "id": "webui.sessions.organize",
      "area": "sessions",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.sessions.organize"
      ],
      "source_refs": [
        "static/sessions.js"
      ],
      "related": [
        "webui.sessions.new",
        "webui.sessions.search",
        "webui.sessions.split"
      ],
      "locales": {
        "en": {
          "title": "Rename, pin, archive and delete",
          "purpose": "Organize conversations through their row menu.",
          "when": "When organising, revisiting or transferring work from a conversation.",
          "steps": [
            "Open a conversation’s menu.",
            "Choose the offered rename, pin, archive or delete action and review its confirmation."
          ],
          "permissions": "You need access to the conversation. Sharing and deletion can require additional rights.",
          "limits": "Exported or shared content may contain conversation details. Review the destination and recipients.",
          "example": "Pin an ongoing project and archive a completed topic."
        },
        "nl": {
          "title": "Hernoemen, vastzetten, archiveren en verwijderen",
          "purpose": "Orden gesprekken via het menu bij de gespreksregel.",
          "when": "Bij het ordenen, terugvinden of overdragen van werk uit een gesprek.",
          "steps": [
            "Open het menu van een gesprek.",
            "Kies de aangeboden actie voor hernoemen, vastzetten, archiveren of verwijderen en controleer de bevestiging."
          ],
          "permissions": "Je hebt toegang tot het gesprek nodig. Delen en verwijderen kunnen extra rechten vereisen.",
          "limits": "Geëxporteerde of gedeelde inhoud kan gespreksgegevens bevatten. Controleer bestemming en ontvangers.",
          "example": "Zet een lopend project vast en archiveer een afgerond onderwerp."
        }
      }
    },
    {
      "id": "webui.voice.dictation",
      "area": "voice",
      "status": "conditional",
      "conditions": [
        "audio-provider",
        "browser-support",
        "policy"
      ],
      "anchors": [
        "?help_feature=webui.voice.dictation",
        "#btnMic"
      ],
      "source_refs": [
        "static/index.html:657"
      ],
      "related": [
        "webui.voice.read",
        "webui.voice.loop",
        "webui.voice.realtime"
      ],
      "locales": {
        "en": {
          "title": "Dictate a draft",
          "purpose": "Convert microphone speech into text in the composer.",
          "when": "When speaking or listening is more convenient than typing and your environment is suitable for audio.",
          "steps": [
            "Choose the microphone and grant browser permission if requested.",
            "Speak, stop recording and review the transcript before sending."
          ],
          "permissions": "Microphone permission and a configured audio provider may be needed.",
          "limits": "Availability varies by browser, device, provider and installation. Audio may be processed by the configured provider.",
          "example": "Dictate a question while keeping the final text editable."
        },
        "nl": {
          "title": "Een concept dicteren",
          "purpose": "Zet gesproken microfoonaudio om naar tekst in het berichtveld.",
          "when": "Wanneer spreken of luisteren handiger is dan typen en je omgeving geschikt is voor audio.",
          "steps": [
            "Kies de microfoon en geef zo nodig browsertoestemming.",
            "Spreek, stop de opname en controleer de tekst voordat je verstuurt."
          ],
          "permissions": "Microfoontoestemming en een ingestelde audioprovider kunnen nodig zijn.",
          "limits": "Beschikbaarheid verschilt per browser, apparaat, provider en installatie. Audio kan door de ingestelde provider worden verwerkt.",
          "example": "Dicteer een vraag en houd de uiteindelijke tekst bewerkbaar."
        }
      }
    },
    {
      "id": "webui.voice.read",
      "area": "voice",
      "status": "conditional",
      "conditions": [
        "audio-provider",
        "browser-support",
        "policy"
      ],
      "anchors": [
        "?help_feature=webui.voice.read"
      ],
      "source_refs": [
        "static/ui.js:17397"
      ],
      "related": [
        "webui.voice.dictation",
        "webui.voice.loop",
        "webui.voice.realtime"
      ],
      "locales": {
        "en": {
          "title": "Read a message aloud",
          "purpose": "Play an available speech rendering of a response.",
          "when": "When speaking or listening is more convenient than typing and your environment is suitable for audio.",
          "steps": [
            "Choose Speak on the message.",
            "Use your selected speech settings and stop playback when finished."
          ],
          "permissions": "Microphone permission and a configured audio provider may be needed.",
          "limits": "Availability varies by browser, device, provider and installation. Audio may be processed by the configured provider.",
          "example": "Listen to a long explanation."
        },
        "nl": {
          "title": "Een bericht laten voorlezen",
          "purpose": "Speel een beschikbare gesproken versie van een antwoord af.",
          "when": "Wanneer spreken of luisteren handiger is dan typen en je omgeving geschikt is voor audio.",
          "steps": [
            "Kies Voorlezen bij het bericht.",
            "Gebruik je gekozen spraakinstellingen en stop afspelen na afloop."
          ],
          "permissions": "Microfoontoestemming en een ingestelde audioprovider kunnen nodig zijn.",
          "limits": "Beschikbaarheid verschilt per browser, apparaat, provider en installatie. Audio kan door de ingestelde provider worden verwerkt.",
          "example": "Luister naar een lange uitleg."
        }
      }
    },
    {
      "id": "webui.voice.loop",
      "area": "voice",
      "status": "conditional",
      "conditions": [
        "audio-provider",
        "browser-support",
        "policy"
      ],
      "anchors": [
        "?help_feature=webui.voice.loop",
        "#btnVoiceMode"
      ],
      "source_refs": [
        "static/commands.js",
        "static/index.html:665"
      ],
      "related": [
        "webui.voice.dictation",
        "webui.voice.read",
        "webui.voice.realtime"
      ],
      "locales": {
        "en": {
          "title": "Voice conversation mode",
          "purpose": "Use the configured voice interaction flow for spoken input and responses.",
          "when": "When speaking or listening is more convenient than typing and your environment is suitable for audio.",
          "steps": [
            "Enable voice mode if offered.",
            "Review microphone and speech settings, then speak when the interface is ready.",
            "Composer shortcut: /voice. Review any required arguments in the command suggestions."
          ],
          "permissions": "Microphone permission and a configured audio provider may be needed.",
          "limits": "Availability varies by browser, device, provider and installation. Audio may be processed by the configured provider.",
          "example": "Discuss a draft hands-free on a supported device."
        },
        "nl": {
          "title": "Spraakgespreksmodus",
          "purpose": "Gebruik de ingestelde spraakinteractie voor gesproken invoer en antwoorden.",
          "when": "Wanneer spreken of luisteren handiger is dan typen en je omgeving geschikt is voor audio.",
          "steps": [
            "Schakel spraakmodus in indien aangeboden.",
            "Controleer microfoon- en spraakinstellingen en spreek wanneer de interface klaar is.",
            "Snelopdracht in het berichtveld: /voice. Controleer eventuele argumenten in de opdrachtsuggesties."
          ],
          "permissions": "Microfoontoestemming en een ingestelde audioprovider kunnen nodig zijn.",
          "limits": "Beschikbaarheid verschilt per browser, apparaat, provider en installatie. Audio kan door de ingestelde provider worden verwerkt.",
          "example": "Bespreek een concept zonder typen op een ondersteund apparaat."
        }
      }
    },
    {
      "id": "webui.voice.realtime",
      "area": "voice",
      "status": "conditional",
      "conditions": [
        "audio-provider",
        "browser-support",
        "policy"
      ],
      "anchors": [
        "?help_feature=webui.voice.realtime",
        "#realtimeVoiceEnd",
        "#btnRealtimeVoice"
      ],
      "source_refs": [
        "static/index.html:637",
        "static/index.html:656"
      ],
      "related": [
        "webui.voice.dictation",
        "webui.voice.read",
        "webui.voice.loop"
      ],
      "locales": {
        "en": {
          "title": "Realtime voice session",
          "purpose": "Start a low-latency audio session when the provider and policy allow it.",
          "when": "When speaking or listening is more convenient than typing and your environment is suitable for audio.",
          "steps": [
            "Choose Realtime voice.",
            "Wait for the connection indicator and microphone permission.",
            "End the session explicitly when finished."
          ],
          "permissions": "Microphone permission and a configured audio provider may be needed.",
          "limits": "Availability varies by browser, device, provider and installation. Audio may be processed by the configured provider.",
          "example": "Have a spoken exchange on a configured audio installation."
        },
        "nl": {
          "title": "Realtime spraaksessie",
          "purpose": "Start een audiosessie met lage vertraging wanneer provider en beleid dit toestaan.",
          "when": "Wanneer spreken of luisteren handiger is dan typen en je omgeving geschikt is voor audio.",
          "steps": [
            "Kies Realtime spraak.",
            "Wacht op de verbindingsindicator en microfoontoestemming.",
            "Beëindig de sessie expliciet na afloop."
          ],
          "permissions": "Microfoontoestemming en een ingestelde audioprovider kunnen nodig zijn.",
          "limits": "Beschikbaarheid verschilt per browser, apparaat, provider en installatie. Audio kan door de ingestelde provider worden verwerkt.",
          "example": "Voer een gesproken gesprek op een ingestelde audio-installatie."
        }
      }
    },
    {
      "id": "webui.voice.hold",
      "area": "voice",
      "status": "conditional",
      "conditions": [
        "audio-provider",
        "browser-support",
        "policy"
      ],
      "anchors": [
        "?help_feature=webui.voice.hold",
        "#realtimeVoiceHold",
        "#realtimeVoiceMic",
        "#realtimeVoiceInterrupt"
      ],
      "source_refs": [
        "static/index.html:634",
        "static/index.html:635",
        "static/index.html:636"
      ],
      "related": [
        "webui.voice.dictation",
        "webui.voice.read",
        "webui.voice.loop"
      ],
      "locales": {
        "en": {
          "title": "Hold, mute and interrupt voice",
          "purpose": "Control microphone input and the current spoken response separately.",
          "when": "When speaking or listening is more convenient than typing and your environment is suitable for audio.",
          "steps": [
            "Use Hold to pause the interaction or Mic to mute input.",
            "Choose Interrupt to stop the current response; End closes the session."
          ],
          "permissions": "Microphone permission and a configured audio provider may be needed.",
          "limits": "Availability varies by browser, device, provider and installation. Audio may be processed by the configured provider.",
          "example": "Stop a long spoken answer before asking a follow-up."
        },
        "nl": {
          "title": "Spraak pauzeren, dempen en onderbreken",
          "purpose": "Bedien microfooninvoer en het huidige gesproken antwoord afzonderlijk.",
          "when": "Wanneer spreken of luisteren handiger is dan typen en je omgeving geschikt is voor audio.",
          "steps": [
            "Gebruik Pauze voor de interactie of Microfoon om invoer te dempen.",
            "Kies Onderbreken om het huidige antwoord te stoppen; Beëindigen sluit de sessie."
          ],
          "permissions": "Microfoontoestemming en een ingestelde audioprovider kunnen nodig zijn.",
          "limits": "Beschikbaarheid verschilt per browser, apparaat, provider en installatie. Audio kan door de ingestelde provider worden verwerkt.",
          "example": "Stop een lang gesproken antwoord voordat je een vervolgvraag stelt."
        }
      }
    },
    {
      "id": "webui.tasks.create",
      "area": "tasks",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.tasks.create",
        "#btnCancelTaskDetail",
        "#btnSaveTaskDetail",
        "#cronFormName"
      ],
      "source_refs": [
        "static/index.html:230",
        "static/index.html:884",
        "static/index.html:885",
        "static/panels.js:2464"
      ],
      "related": [
        "webui.tasks.prompt",
        "webui.tasks.script",
        "webui.tasks.skills"
      ],
      "locales": {
        "en": {
          "title": "Create a scheduled task",
          "purpose": "Save a recurring or one-off automation with a named owner and execution settings.",
          "when": "When work should run independently of an open chat or an existing automation needs adjustment.",
          "steps": [
            "Open Tasks and choose New job.",
            "Enter a clear name, prompt or script, schedule and delivery settings.",
            "Save and inspect the next run."
          ],
          "permissions": "Only permitted owners and managers may change or run jobs. Visibility alone does not grant write access.",
          "limits": "A saved schedule does not guarantee successful execution or delivery. Check run results and notification policy.",
          "example": "Prepare a daily internal summary."
        },
        "nl": {
          "title": "Een geplande taak maken",
          "purpose": "Sla een terugkerende of eenmalige automatisering op met een eigenaar en uitvoeringsinstellingen.",
          "when": "Wanneer werk onafhankelijk van een open chat moet draaien of een automatisering moet worden aangepast.",
          "steps": [
            "Open Taken en kies Nieuwe taak.",
            "Vul een duidelijke naam, prompt of script, planning en bezorginstellingen in.",
            "Sla op en controleer de volgende uitvoering."
          ],
          "permissions": "Alleen bevoegde eigenaren en beheerders mogen taken wijzigen of uitvoeren. Zichtbaarheid geeft geen schrijfrechten.",
          "limits": "Een opgeslagen planning garandeert geen geslaagde uitvoering of bezorging. Controleer resultaten en meldingsbeleid.",
          "example": "Stel een dagelijkse interne samenvatting in."
        }
      }
    },
    {
      "id": "webui.tasks.prompt",
      "area": "tasks",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.tasks.prompt",
        "#cronFormPrompt"
      ],
      "source_refs": [
        "static/panels.js:1949",
        "static/panels.js:2440"
      ],
      "related": [
        "webui.tasks.create",
        "webui.tasks.script",
        "webui.tasks.skills"
      ],
      "locales": {
        "en": {
          "title": "Task prompt",
          "purpose": "Describe what an agent task must do each time it runs.",
          "when": "When work should run independently of an open chat or an existing automation needs adjustment.",
          "steps": [
            "Edit the task prompt.",
            "State the input, required output and boundaries; save the task."
          ],
          "permissions": "Only permitted owners and managers may change or run jobs. Visibility alone does not grant write access.",
          "limits": "A saved schedule does not guarantee successful execution or delivery. Check run results and notification policy.",
          "example": "Ask for a short summary with links to its sources."
        },
        "nl": {
          "title": "Taakprompt",
          "purpose": "Beschrijf wat een agenttaak bij elke uitvoering moet doen.",
          "when": "Wanneer werk onafhankelijk van een open chat moet draaien of een automatisering moet worden aangepast.",
          "steps": [
            "Bewerk de taakprompt.",
            "Noem invoer, gewenste uitvoer en grenzen; sla de taak op."
          ],
          "permissions": "Alleen bevoegde eigenaren en beheerders mogen taken wijzigen of uitvoeren. Zichtbaarheid geeft geen schrijfrechten.",
          "limits": "Een opgeslagen planning garandeert geen geslaagde uitvoering of bezorging. Controleer resultaten en meldingsbeleid.",
          "example": "Vraag om een korte samenvatting met bronverwijzingen."
        }
      }
    },
    {
      "id": "webui.tasks.script",
      "area": "tasks",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.tasks.script",
        "#cronFormScript"
      ],
      "source_refs": [
        "static/panels.js:2445"
      ],
      "related": [
        "webui.tasks.create",
        "webui.tasks.prompt",
        "webui.tasks.skills"
      ],
      "locales": {
        "en": {
          "title": "Script task",
          "purpose": "Run an approved script within the governed execution policy.",
          "when": "When work should run independently of an open chat or an existing automation needs adjustment.",
          "steps": [
            "Choose the script task option and enter its allowed path.",
            "Check ownership and permitted execution scope before saving and running."
          ],
          "permissions": "Only permitted owners and managers may change or run jobs. Visibility alone does not grant write access.",
          "limits": "A saved schedule does not guarantee successful execution or delivery. Check run results and notification policy.",
          "example": "Run a maintained local reporting script."
        },
        "nl": {
          "title": "Scripttaak",
          "purpose": "Voer een toegestaan script uit binnen het uitvoeringsbeleid.",
          "when": "Wanneer werk onafhankelijk van een open chat moet draaien of een automatisering moet worden aangepast.",
          "steps": [
            "Kies de scripttaakoptie en vul het toegestane pad in.",
            "Controleer eigenaarschap en toegestane uitvoering voordat je opslaat en uitvoert."
          ],
          "permissions": "Alleen bevoegde eigenaren en beheerders mogen taken wijzigen of uitvoeren. Zichtbaarheid geeft geen schrijfrechten.",
          "limits": "Een opgeslagen planning garandeert geen geslaagde uitvoering of bezorging. Controleer resultaten en meldingsbeleid.",
          "example": "Voer een beheerd lokaal rapportagescript uit."
        }
      }
    },
    {
      "id": "webui.tasks.skills",
      "area": "tasks",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.tasks.skills",
        "#cronFormSkillSearch"
      ],
      "source_refs": [
        "static/panels.js:2452"
      ],
      "related": [
        "webui.tasks.create",
        "webui.tasks.prompt",
        "webui.tasks.script"
      ],
      "locales": {
        "en": {
          "title": "Task skills",
          "purpose": "Attach available skills to an agent task’s instructions.",
          "when": "When work should run independently of an open chat or an existing automation needs adjustment.",
          "steps": [
            "Search the task skill selector.",
            "Select the required skills and save; verify the task still has the necessary tool permissions."
          ],
          "permissions": "Only permitted owners and managers may change or run jobs. Visibility alone does not grant write access.",
          "limits": "A saved schedule does not guarantee successful execution or delivery. Check run results and notification policy.",
          "example": "Reuse a reporting skill for a scheduled summary."
        },
        "nl": {
          "title": "Skills voor een taak",
          "purpose": "Voeg beschikbare skills toe aan de instructies van een agenttaak.",
          "when": "Wanneer werk onafhankelijk van een open chat moet draaien of een automatisering moet worden aangepast.",
          "steps": [
            "Zoek in de skillkiezer van de taak.",
            "Kies de benodigde skills en sla op; controleer of de taak de nodige toolrechten heeft."
          ],
          "permissions": "Alleen bevoegde eigenaren en beheerders mogen taken wijzigen of uitvoeren. Zichtbaarheid geeft geen schrijfrechten.",
          "limits": "Een opgeslagen planning garandeert geen geslaagde uitvoering of bezorging. Controleer resultaten en meldingsbeleid.",
          "example": "Gebruik een rapportageskill voor een geplande samenvatting."
        }
      }
    },
    {
      "id": "webui.tasks.schedule",
      "area": "tasks",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.tasks.schedule",
        "#cronFormSchedulePreset",
        "#cronFormScheduleWeekday",
        "#cronFormScheduleMonthDay",
        "#cronFormScheduleTime",
        "#cronFormScheduleMinute",
        "#cronFormSchedule"
      ],
      "source_refs": [
        "static/panels.js:2484",
        "static/panels.js:2490",
        "static/panels.js:2502",
        "static/panels.js:2508",
        "static/panels.js:2512",
        "static/panels.js:2520"
      ],
      "related": [
        "webui.tasks.create",
        "webui.tasks.prompt",
        "webui.tasks.script"
      ],
      "locales": {
        "en": {
          "title": "Schedule presets and expressions",
          "purpose": "Set when a task should run using a preset or supported expression.",
          "when": "When work should run independently of an open chat or an existing automation needs adjustment.",
          "steps": [
            "Select the schedule preset.",
            "Set weekday, month day, time or interval as shown; advanced users can enter an expression.",
            "Check the displayed next run and timezone."
          ],
          "permissions": "Only permitted owners and managers may change or run jobs. Visibility alone does not grant write access.",
          "limits": "A saved schedule does not guarantee successful execution or delivery. Check run results and notification policy.",
          "example": "Schedule a weekday report at the intended local time."
        },
        "nl": {
          "title": "Planningskeuzes en expressies",
          "purpose": "Stel in wanneer een taak draait via een vaste keuze of ondersteunde expressie.",
          "when": "Wanneer werk onafhankelijk van een open chat moet draaien of een automatisering moet worden aangepast.",
          "steps": [
            "Kies het type planning.",
            "Stel weekdag, maanddag, tijd of interval in; ervaren gebruikers kunnen een expressie invullen.",
            "Controleer de getoonde volgende uitvoering en tijdzone."
          ],
          "permissions": "Alleen bevoegde eigenaren en beheerders mogen taken wijzigen of uitvoeren. Zichtbaarheid geeft geen schrijfrechten.",
          "limits": "Een opgeslagen planning garandeert geen geslaagde uitvoering of bezorging. Controleer resultaten en meldingsbeleid.",
          "example": "Plan een rapport op werkdagen op de bedoelde lokale tijd."
        }
      }
    },
    {
      "id": "webui.tasks.profile",
      "area": "tasks",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.tasks.profile",
        "#cronFormProfile",
        "#cronFormModel"
      ],
      "source_refs": [
        "static/panels.js:2542",
        "static/panels.js:2549"
      ],
      "related": [
        "webui.tasks.create",
        "webui.tasks.prompt",
        "webui.tasks.script"
      ],
      "locales": {
        "en": {
          "title": "Task bot and model",
          "purpose": "Choose the execution profile and optional model override for a task.",
          "when": "When work should run independently of an open chat or an existing automation needs adjustment.",
          "steps": [
            "Choose a permitted profile and available model.",
            "Save and verify the task details before running."
          ],
          "permissions": "Only permitted owners and managers may change or run jobs. Visibility alone does not grant write access.",
          "limits": "A saved schedule does not guarantee successful execution or delivery. Check run results and notification policy.",
          "example": "Run a reporting task under its dedicated bot."
        },
        "nl": {
          "title": "Bot en model voor een taak",
          "purpose": "Kies het uitvoeringsprofiel en een eventuele modelafwijking voor een taak.",
          "when": "Wanneer werk onafhankelijk van een open chat moet draaien of een automatisering moet worden aangepast.",
          "steps": [
            "Kies een toegestaan profiel en beschikbaar model.",
            "Sla op en controleer de taakdetails voordat je uitvoert."
          ],
          "permissions": "Alleen bevoegde eigenaren en beheerders mogen taken wijzigen of uitvoeren. Zichtbaarheid geeft geen schrijfrechten.",
          "limits": "Een opgeslagen planning garandeert geen geslaagde uitvoering of bezorging. Controleer resultaten en meldingsbeleid.",
          "example": "Voer een rapportagetaak onder de bijbehorende bot uit."
        }
      }
    },
    {
      "id": "webui.tasks.delivery",
      "area": "tasks",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.tasks.delivery",
        "#cronFormDeliver"
      ],
      "source_refs": [
        "static/panels.js:2534"
      ],
      "related": [
        "webui.tasks.create",
        "webui.tasks.prompt",
        "webui.tasks.script"
      ],
      "locales": {
        "en": {
          "title": "Task delivery destination",
          "purpose": "Choose where eligible task results should be delivered.",
          "when": "When work should run independently of an open chat or an existing automation needs adjustment.",
          "steps": [
            "Set the task’s delivery destination.",
            "Check the destination identity and notification policy before saving."
          ],
          "permissions": "Only permitted owners and managers may change or run jobs. Visibility alone does not grant write access.",
          "limits": "A saved schedule does not guarantee successful execution or delivery. Check run results and notification policy.",
          "example": "Send an approved summary to its configured channel."
        },
        "nl": {
          "title": "Bezorgbestemming van een taak",
          "purpose": "Kies waar taakresultaten die voor bezorging in aanmerking komen naartoe gaan.",
          "when": "Wanneer werk onafhankelijk van een open chat moet draaien of een automatisering moet worden aangepast.",
          "steps": [
            "Stel de bezorgbestemming van de taak in.",
            "Controleer de bestemmingsidentiteit en het meldingsbeleid voordat je opslaat."
          ],
          "permissions": "Alleen bevoegde eigenaren en beheerders mogen taken wijzigen of uitvoeren. Zichtbaarheid geeft geen schrijfrechten.",
          "limits": "Een opgeslagen planning garandeert geen geslaagde uitvoering of bezorging. Controleer resultaten en meldingsbeleid.",
          "example": "Stuur een goedgekeurde samenvatting naar het ingestelde kanaal."
        }
      }
    },
    {
      "id": "webui.tasks.notify",
      "area": "tasks",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.tasks.notify"
      ],
      "source_refs": [
        "static/panels.js:1737",
        "static/panels.js:1767",
        "static/panels.js:1768"
      ],
      "related": [
        "webui.tasks.create",
        "webui.tasks.prompt",
        "webui.tasks.script"
      ],
      "locales": {
        "en": {
          "title": "Notification policy",
          "purpose": "Control which task outcomes are eligible for delivery.",
          "when": "When work should run independently of an open chat or an existing automation needs adjustment.",
          "steps": [
            "Open the task notification options.",
            "Choose the offered policy and save.",
            "Inspect run results separately from delivery status."
          ],
          "permissions": "Only permitted owners and managers may change or run jobs. Visibility alone does not grant write access.",
          "limits": "A saved schedule does not guarantee successful execution or delivery. Check run results and notification policy. A script that sends its own messages must honor its supplied delivery policy; muting delivery does not stop execution.",
          "example": "Keep failure alerts while suppressing routine success messages."
        },
        "nl": {
          "title": "Meldingsbeleid",
          "purpose": "Bepaal welke taakuitkomsten voor bezorging in aanmerking komen.",
          "when": "Wanneer werk onafhankelijk van een open chat moet draaien of een automatisering moet worden aangepast.",
          "steps": [
            "Open de meldingsopties van de taak.",
            "Kies het aangeboden beleid en sla op.",
            "Bekijk uitvoeringsresultaten afzonderlijk van de bezorgstatus."
          ],
          "permissions": "Alleen bevoegde eigenaren en beheerders mogen taken wijzigen of uitvoeren. Zichtbaarheid geeft geen schrijfrechten.",
          "limits": "Een opgeslagen planning garandeert geen geslaagde uitvoering of bezorging. Controleer resultaten en meldingsbeleid. Een script dat zelf berichten verstuurt moet het aangeleverde bezorgbeleid volgen; bezorging dempen stopt de uitvoering niet.",
          "example": "Behoud foutmeldingen en onderdruk gewone succesberichten."
        }
      }
    },
    {
      "id": "webui.tasks.mute",
      "area": "tasks",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.tasks.mute"
      ],
      "source_refs": [
        "static/panels.js:1739",
        "static/panels.js:1756"
      ],
      "related": [
        "webui.tasks.create",
        "webui.tasks.prompt",
        "webui.tasks.script"
      ],
      "locales": {
        "en": {
          "title": "Mute task notifications for yourself",
          "purpose": "Suppress your own task notifications without pausing the task for everyone.",
          "when": "When work should run independently of an open chat or an existing automation needs adjustment.",
          "steps": [
            "Use the task’s personal mute control.",
            "Toggle it again to restore your notifications; check the task remains scheduled."
          ],
          "permissions": "Only permitted owners and managers may change or run jobs. Visibility alone does not grant write access.",
          "limits": "A saved schedule does not guarantee successful execution or delivery. Check run results and notification policy.",
          "example": "Quiet a shared task’s notifications during focused work."
        },
        "nl": {
          "title": "Taakmeldingen voor jezelf dempen",
          "purpose": "Onderdruk je eigen taakmeldingen zonder de taak voor iedereen te pauzeren.",
          "when": "Wanneer werk onafhankelijk van een open chat moet draaien of een automatisering moet worden aangepast.",
          "steps": [
            "Gebruik de persoonlijke dempknop van de taak.",
            "Schakel opnieuw om meldingen te herstellen; controleer dat de planning actief blijft."
          ],
          "permissions": "Alleen bevoegde eigenaren en beheerders mogen taken wijzigen of uitvoeren. Zichtbaarheid geeft geen schrijfrechten.",
          "limits": "Een opgeslagen planning garandeert geen geslaagde uitvoering of bezorging. Controleer resultaten en meldingsbeleid.",
          "example": "Demp meldingen van een gedeelde taak tijdens geconcentreerd werken."
        }
      }
    },
    {
      "id": "webui.tasks.run",
      "area": "tasks",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.tasks.run",
        "#btnRunTaskDetail"
      ],
      "source_refs": [
        "static/index.html:877",
        "static/panels.js:2044"
      ],
      "related": [
        "webui.tasks.create",
        "webui.tasks.prompt",
        "webui.tasks.script"
      ],
      "locales": {
        "en": {
          "title": "Run a task now",
          "purpose": "Request an immediate governed execution of the selected task.",
          "when": "When work should run independently of an open chat or an existing automation needs adjustment.",
          "steps": [
            "Open the task and choose Run now.",
            "Wait for the result and inspect any refusal or failure reason."
          ],
          "permissions": "Only permitted owners and managers may change or run jobs. Visibility alone does not grant write access.",
          "limits": "A saved schedule does not guarantee successful execution or delivery. Check run results and notification policy.",
          "example": "Validate an edited task before its next scheduled run."
        },
        "nl": {
          "title": "Een taak nu uitvoeren",
          "purpose": "Vraag om een directe uitvoering van de gekozen taak binnen het beleid.",
          "when": "Wanneer werk onafhankelijk van een open chat moet draaien of een automatisering moet worden aangepast.",
          "steps": [
            "Open de taak en kies Nu uitvoeren.",
            "Wacht op het resultaat en lees een eventuele weigering of foutreden."
          ],
          "permissions": "Alleen bevoegde eigenaren en beheerders mogen taken wijzigen of uitvoeren. Zichtbaarheid geeft geen schrijfrechten.",
          "limits": "Een opgeslagen planning garandeert geen geslaagde uitvoering of bezorging. Controleer resultaten en meldingsbeleid.",
          "example": "Controleer een gewijzigde taak voor de volgende geplande uitvoering."
        }
      }
    },
    {
      "id": "webui.tasks.pause",
      "area": "tasks",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.tasks.pause",
        "#btnPauseTaskDetail",
        "#btnResumeTaskDetail"
      ],
      "source_refs": [
        "static/index.html:878",
        "static/index.html:879",
        "static/panels.js:2043"
      ],
      "related": [
        "webui.tasks.create",
        "webui.tasks.prompt",
        "webui.tasks.script"
      ],
      "locales": {
        "en": {
          "title": "Pause or resume a task",
          "purpose": "Control future scheduled runs without deleting the task.",
          "when": "When work should run independently of an open chat or an existing automation needs adjustment.",
          "steps": [
            "Choose Pause or Resume on the selected task.",
            "Verify its displayed status and next run."
          ],
          "permissions": "Only permitted owners and managers may change or run jobs. Visibility alone does not grant write access.",
          "limits": "A saved schedule does not guarantee successful execution or delivery. Check run results and notification policy.",
          "example": "Pause a holiday-period report and resume it later."
        },
        "nl": {
          "title": "Een taak pauzeren of hervatten",
          "purpose": "Bedien toekomstige geplande uitvoeringen zonder de taak te verwijderen.",
          "when": "Wanneer werk onafhankelijk van een open chat moet draaien of een automatisering moet worden aangepast.",
          "steps": [
            "Kies Pauzeren of Hervatten bij de gekozen taak.",
            "Controleer de weergegeven status en volgende uitvoering."
          ],
          "permissions": "Alleen bevoegde eigenaren en beheerders mogen taken wijzigen of uitvoeren. Zichtbaarheid geeft geen schrijfrechten.",
          "limits": "Een opgeslagen planning garandeert geen geslaagde uitvoering of bezorging. Controleer resultaten en meldingsbeleid.",
          "example": "Pauzeer een rapport tijdens vakantie en hervat het later."
        }
      }
    },
    {
      "id": "webui.tasks.share",
      "area": "tasks",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.tasks.share",
        "#btnShareTaskDetail",
        "#cronShareExtra",
        "#cronShareCancel",
        "#cronShareSave"
      ],
      "source_refs": [
        "static/index.html:880",
        "static/panels.js:1348",
        "static/panels.js:1413",
        "static/panels.js:1880",
        "static/panels.js:1883",
        "static/panels.js:1884"
      ],
      "related": [
        "webui.tasks.create",
        "webui.tasks.prompt",
        "webui.tasks.script"
      ],
      "locales": {
        "en": {
          "title": "Task visibility and sharing",
          "purpose": "Choose who may see a task through supported sharing controls.",
          "when": "When work should run independently of an open chat or an existing automation needs adjustment.",
          "steps": [
            "Open Share on the task.",
            "Review the selected people or scope and save; sharing does not transfer ownership."
          ],
          "permissions": "Only permitted owners and managers may change or run jobs. Visibility alone does not grant write access.",
          "limits": "A saved schedule does not guarantee successful execution or delivery. Check run results and notification policy.",
          "example": "Let a colleague inspect a shared report task."
        },
        "nl": {
          "title": "Zichtbaarheid en delen van taken",
          "purpose": "Kies wie een taak mag zien via de ondersteunde deelopties.",
          "when": "Wanneer werk onafhankelijk van een open chat moet draaien of een automatisering moet worden aangepast.",
          "steps": [
            "Open Delen bij de taak.",
            "Controleer de gekozen personen of scope en sla op; delen draagt geen eigenaarschap over."
          ],
          "permissions": "Alleen bevoegde eigenaren en beheerders mogen taken wijzigen of uitvoeren. Zichtbaarheid geeft geen schrijfrechten.",
          "limits": "Een opgeslagen planning garandeert geen geslaagde uitvoering of bezorging. Controleer resultaten en meldingsbeleid.",
          "example": "Laat een collega een gedeelde rapportagetaak bekijken."
        }
      }
    },
    {
      "id": "webui.tasks.edit",
      "area": "tasks",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.tasks.edit",
        "#btnEditTaskDetail",
        "#btnDuplicateTaskDetail",
        "#btnDeleteTaskDetail"
      ],
      "source_refs": [
        "static/index.html:881",
        "static/index.html:882",
        "static/index.html:883"
      ],
      "related": [
        "webui.tasks.create",
        "webui.tasks.prompt",
        "webui.tasks.script"
      ],
      "locales": {
        "en": {
          "title": "Edit, duplicate and delete tasks",
          "purpose": "Maintain an existing task or create a separate copy.",
          "when": "When work should run independently of an open chat or an existing automation needs adjustment.",
          "steps": [
            "Select the task and choose Edit or Duplicate.",
            "Review name, schedule and destination before saving.",
            "For deletion, verify the task in the confirmation."
          ],
          "permissions": "Only permitted owners and managers may change or run jobs. Visibility alone does not grant write access.",
          "limits": "A saved schedule does not guarantee successful execution or delivery. Check run results and notification policy.",
          "example": "Copy a report task for a different schedule."
        },
        "nl": {
          "title": "Taken bewerken, dupliceren en verwijderen",
          "purpose": "Onderhoud een bestaande taak of maak een afzonderlijke kopie.",
          "when": "Wanneer werk onafhankelijk van een open chat moet draaien of een automatisering moet worden aangepast.",
          "steps": [
            "Kies de taak en kies Bewerken of Dupliceren.",
            "Controleer naam, planning en bestemming voordat je opslaat.",
            "Controleer bij verwijderen de taak in de bevestiging."
          ],
          "permissions": "Alleen bevoegde eigenaren en beheerders mogen taken wijzigen of uitvoeren. Zichtbaarheid geeft geen schrijfrechten.",
          "limits": "Een opgeslagen planning garandeert geen geslaagde uitvoering of bezorging. Controleer resultaten en meldingsbeleid.",
          "example": "Kopieer een rapportagetaak voor een andere planning."
        }
      }
    },
    {
      "id": "webui.tasks.labels",
      "area": "tasks",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.tasks.labels",
        "#cronEmojiCustom",
        "#cronCategoryPick",
        "#cronFormEmoji",
        "#cronFormCategory",
        "#cronFormDiagram"
      ],
      "source_refs": [
        "static/panels.js:1416",
        "static/panels.js:1438",
        "static/panels.js:1439",
        "static/panels.js:1440",
        "static/panels.js:1441",
        "static/panels.js:1545",
        "static/panels.js:1547",
        "static/panels.js:1548",
        "static/panels.js:2010",
        "static/panels.js:2469",
        "static/panels.js:2470",
        "static/panels.js:2471",
        "static/panels.js:2478",
        "static/panels.js:2528"
      ],
      "related": [
        "webui.tasks.create",
        "webui.tasks.prompt",
        "webui.tasks.script"
      ],
      "locales": {
        "en": {
          "title": "Task category, icon and diagram",
          "purpose": "Organize task presentation using labels and an optional diagram.",
          "when": "When work should run independently of an open chat or an existing automation needs adjustment.",
          "steps": [
            "Set the category and icon in task details or the editor.",
            "Add an optional diagram if supported and save."
          ],
          "permissions": "Only permitted owners and managers may change or run jobs. Visibility alone does not grant write access.",
          "limits": "A saved schedule does not guarantee successful execution or delivery. Check run results and notification policy.",
          "example": "Group reporting jobs under one category."
        },
        "nl": {
          "title": "Taakcategorie, pictogram en diagram",
          "purpose": "Orden de taakweergave met labels en een eventueel diagram.",
          "when": "Wanneer werk onafhankelijk van een open chat moet draaien of een automatisering moet worden aangepast.",
          "steps": [
            "Stel categorie en pictogram in bij taakdetails of de editor.",
            "Voeg eventueel een ondersteund diagram toe en sla op."
          ],
          "permissions": "Alleen bevoegde eigenaren en beheerders mogen taken wijzigen of uitvoeren. Zichtbaarheid geeft geen schrijfrechten.",
          "limits": "Een opgeslagen planning garandeert geen geslaagde uitvoering of bezorging. Controleer resultaten en meldingsbeleid.",
          "example": "Groepeer rapportagetaken onder één categorie."
        }
      }
    },
    {
      "id": "webui.tasks.results",
      "area": "tasks",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.tasks.results",
        "#cronRefreshBtn"
      ],
      "source_refs": [
        "static/index.html:229",
        "static/panels.js:2045",
        "static/panels.js:2165"
      ],
      "related": [
        "webui.tasks.create",
        "webui.tasks.prompt",
        "webui.tasks.script"
      ],
      "locales": {
        "en": {
          "title": "Task results and diagnostics",
          "purpose": "Inspect a job’s state and copy diagnostic details for investigation.",
          "when": "When work should run independently of an open chat or an existing automation needs adjustment.",
          "steps": [
            "Refresh the job list and open the task.",
            "Read its latest result; copy diagnostics only after reviewing them."
          ],
          "permissions": "Only permitted owners and managers may change or run jobs. Visibility alone does not grant write access.",
          "limits": "A saved schedule does not guarantee successful execution or delivery. Check run results and notification policy.",
          "example": "Investigate why a scheduled result was not delivered."
        },
        "nl": {
          "title": "Taakresultaten en diagnostiek",
          "purpose": "Bekijk de taakstatus en kopieer diagnostische gegevens voor onderzoek.",
          "when": "Wanneer werk onafhankelijk van een open chat moet draaien of een automatisering moet worden aangepast.",
          "steps": [
            "Ververs de takenlijst en open de taak.",
            "Lees het laatste resultaat; kopieer diagnostiek pas na controle."
          ],
          "permissions": "Alleen bevoegde eigenaren en beheerders mogen taken wijzigen of uitvoeren. Zichtbaarheid geeft geen schrijfrechten.",
          "limits": "Een opgeslagen planning garandeert geen geslaagde uitvoering of bezorging. Controleer resultaten en meldingsbeleid.",
          "example": "Onderzoek waarom een gepland resultaat niet is bezorgd."
        }
      }
    },
    {
      "id": "webui.files.workspace",
      "area": "files",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.files.workspace",
        "#composerWorkspaceChip",
        "#composerMobileWorkspaceAction",
        "#btnActivateWorkspaceDetail",
        "#workspaceFormName",
        "#workspaceFormPath",
        "#workspaceFormCategory"
      ],
      "source_refs": [
        "static/commands.js",
        "static/index.html:324",
        "static/index.html:693",
        "static/index.html:785",
        "static/index.html:950",
        "static/panels.js:7331",
        "static/panels.js:7336",
        "static/panels.js:7343"
      ],
      "related": [
        "webui.files.manage",
        "webui.files.access",
        "webui.files.browse"
      ],
      "locales": {
        "en": {
          "title": "Create and select a workspace",
          "purpose": "Group work under a named directory and choose the active workspace.",
          "when": "When the task needs documents or directories in a specific workspace.",
          "steps": [
            "Open Workspaces and create or select an entry.",
            "Check its name, path and category; choose Use workspace to activate it.",
            "Composer shortcut: /workspace. Review any required arguments in the command suggestions."
          ],
          "permissions": "Workspace access and file permissions apply. Selecting a workspace does not grant access.",
          "limits": "Changes affect the selected workspace. Check the path and retain a copy before replacing important content.",
          "example": "Keep a report project in its own workspace."
        },
        "nl": {
          "title": "Een werkruimte maken en kiezen",
          "purpose": "Groepeer werk onder een benoemde map en kies de actieve werkruimte.",
          "when": "Wanneer de taak documenten of mappen in een bepaalde werkruimte nodig heeft.",
          "steps": [
            "Open Werkruimten en maak of kies een item.",
            "Controleer naam, pad en categorie; kies Werkruimte gebruiken om deze te activeren.",
            "Snelopdracht in het berichtveld: /workspace. Controleer eventuele argumenten in de opdrachtsuggesties."
          ],
          "permissions": "Toegang tot de werkruimte en bestandsrechten gelden. Een werkruimte kiezen geeft geen extra toegang.",
          "limits": "Wijzigingen gelden voor de gekozen werkruimte. Controleer het pad en bewaar een kopie voordat je belangrijke inhoud vervangt.",
          "example": "Houd een rapportageproject in een eigen werkruimte."
        }
      }
    },
    {
      "id": "webui.files.manage",
      "area": "files",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.files.manage",
        "#btnEditWorkspaceDetail",
        "#btnDeleteWorkspaceDetail",
        "#btnCancelWorkspaceDetail",
        "#btnSaveWorkspaceDetail"
      ],
      "source_refs": [
        "static/index.html:951",
        "static/index.html:952",
        "static/index.html:953",
        "static/index.html:954"
      ],
      "related": [
        "webui.files.workspace",
        "webui.files.access",
        "webui.files.browse"
      ],
      "locales": {
        "en": {
          "title": "Edit or remove a workspace entry",
          "purpose": "Maintain the named workspace registration.",
          "when": "When the task needs documents or directories in a specific workspace.",
          "steps": [
            "Open workspace details and choose Edit.",
            "Save the revised details or use Remove after reading the confirmation."
          ],
          "permissions": "Workspace access and file permissions apply. Selecting a workspace does not grant access.",
          "limits": "Changes affect the selected workspace. Check the path and retain a copy before replacing important content.",
          "example": "Correct the displayed workspace name."
        },
        "nl": {
          "title": "Een werkruimtevermelding bewerken of verwijderen",
          "purpose": "Beheer de benoemde werkruimteregistratie.",
          "when": "Wanneer de taak documenten of mappen in een bepaalde werkruimte nodig heeft.",
          "steps": [
            "Open werkruimtedetails en kies Bewerken.",
            "Sla wijzigingen op of kies Verwijderen na het lezen van de bevestiging."
          ],
          "permissions": "Toegang tot de werkruimte en bestandsrechten gelden. Een werkruimte kiezen geeft geen extra toegang.",
          "limits": "Wijzigingen gelden voor de gekozen werkruimte. Controleer het pad en bewaar een kopie voordat je belangrijke inhoud vervangt.",
          "example": "Corrigeer de weergegeven naam van een werkruimte."
        }
      }
    },
    {
      "id": "webui.files.access",
      "area": "files",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.files.access",
        "#wsAssignOwner",
        "#wsAssignMembers",
        "#wsAssignSaveBtn"
      ],
      "source_refs": [
        "static/governance.js:1385",
        "static/governance.js:1390",
        "static/governance.js:1395",
        "static/governance.js:1398",
        "static/governance.js:1401",
        "static/panels.js:7176",
        "static/panels.js:7177",
        "static/panels.js:7178"
      ],
      "related": [
        "webui.files.workspace",
        "webui.files.manage",
        "webui.files.browse"
      ],
      "locales": {
        "en": {
          "title": "Workspace owner and members",
          "purpose": "Assign workspace access within the allowed governance scope.",
          "when": "When the task needs documents or directories in a specific workspace.",
          "steps": [
            "Open the assignment controls.",
            "Select owner and permitted members, then save and verify the resulting access."
          ],
          "permissions": "Workspace access and file permissions apply. Selecting a workspace does not grant access.",
          "limits": "Changes affect the selected workspace. Check the path and retain a copy before replacing important content.",
          "example": "Give a project team access to its shared workspace."
        },
        "nl": {
          "title": "Eigenaar en leden van een werkruimte",
          "purpose": "Wijs werkruimtetoegang toe binnen de toegestane beleidsscope.",
          "when": "Wanneer de taak documenten of mappen in een bepaalde werkruimte nodig heeft.",
          "steps": [
            "Open de toewijzingsopties.",
            "Kies eigenaar en toegestane leden, sla op en controleer de resulterende toegang."
          ],
          "permissions": "Toegang tot de werkruimte en bestandsrechten gelden. Een werkruimte kiezen geeft geen extra toegang.",
          "limits": "Wijzigingen gelden voor de gekozen werkruimte. Controleer het pad en bewaar een kopie voordat je belangrijke inhoud vervangt.",
          "example": "Geef een projectteam toegang tot de gedeelde werkruimte."
        }
      }
    },
    {
      "id": "webui.files.browse",
      "area": "files",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.files.browse",
        "#btnWorkspacePanelToggle",
        "#btnWorkspacePanelEdgeToggle",
        "#btnUpDir",
        "#btnRefreshPanel",
        "#btnClearPreview",
        "#workspaceFilesTab"
      ],
      "source_refs": [
        "static/index.html:172",
        "static/index.html:1943",
        "static/index.html:1952",
        "static/index.html:1955",
        "static/index.html:1958",
        "static/index.html:196",
        "static/index.html:1963",
        "static/index.html:690"
      ],
      "related": [
        "webui.files.workspace",
        "webui.files.manage",
        "webui.files.access"
      ],
      "locales": {
        "en": {
          "title": "Browse files and folders",
          "purpose": "Explore the selected workspace and preview its files.",
          "when": "When the task needs documents or directories in a specific workspace.",
          "steps": [
            "Open Files or the workspace panel.",
            "Choose a folder or file; use Up to return to the parent and Refresh for recent changes."
          ],
          "permissions": "Workspace access and file permissions apply. Selecting a workspace does not grant access.",
          "limits": "Changes affect the selected workspace. Check the path and retain a copy before replacing important content.",
          "example": "Read a generated report in the workspace."
        },
        "nl": {
          "title": "Bestanden en mappen bekijken",
          "purpose": "Verken de gekozen werkruimte en bekijk bestandsvoorbeelden.",
          "when": "Wanneer de taak documenten of mappen in een bepaalde werkruimte nodig heeft.",
          "steps": [
            "Open Bestanden of het werkruimtepaneel.",
            "Kies een map of bestand; gebruik Omhoog voor de bovenliggende map en Verversen voor recente wijzigingen."
          ],
          "permissions": "Toegang tot de werkruimte en bestandsrechten gelden. Een werkruimte kiezen geeft geen extra toegang.",
          "limits": "Wijzigingen gelden voor de gekozen werkruimte. Controleer het pad en bewaar een kopie voordat je belangrijke inhoud vervangt.",
          "example": "Lees een gegenereerd rapport in de werkruimte."
        }
      }
    },
    {
      "id": "webui.files.create",
      "area": "files",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.files.create",
        "#btnNewFile",
        "#btnNewFolder"
      ],
      "source_refs": [
        "static/index.html:1953",
        "static/index.html:1954"
      ],
      "related": [
        "webui.files.workspace",
        "webui.files.manage",
        "webui.files.access"
      ],
      "locales": {
        "en": {
          "title": "Create a file or folder",
          "purpose": "Add a named file or folder inside the current permitted directory.",
          "when": "When the task needs documents or directories in a specific workspace.",
          "steps": [
            "Navigate to the intended directory.",
            "Choose New file or New folder and enter a valid name."
          ],
          "permissions": "Workspace access and file permissions apply. Selecting a workspace does not grant access.",
          "limits": "Changes affect the selected workspace. Check the path and retain a copy before replacing important content.",
          "example": "Create a notes folder for project research."
        },
        "nl": {
          "title": "Een bestand of map maken",
          "purpose": "Voeg een benoemd bestand of map toe in de huidige toegestane map.",
          "when": "Wanneer de taak documenten of mappen in een bepaalde werkruimte nodig heeft.",
          "steps": [
            "Ga naar de bedoelde map.",
            "Kies Nieuw bestand of Nieuwe map en vul een geldige naam in."
          ],
          "permissions": "Toegang tot de werkruimte en bestandsrechten gelden. Een werkruimte kiezen geeft geen extra toegang.",
          "limits": "Wijzigingen gelden voor de gekozen werkruimte. Controleer het pad en bewaar een kopie voordat je belangrijke inhoud vervangt.",
          "example": "Maak een notitiemap voor projectonderzoek."
        }
      }
    },
    {
      "id": "webui.files.upload",
      "area": "files",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.files.upload",
        "#btnUploadWorkspace",
        "#workspaceFileInput"
      ],
      "source_refs": [
        "static/index.html:1956",
        "static/index.html:1961"
      ],
      "related": [
        "webui.files.workspace",
        "webui.files.manage",
        "webui.files.access"
      ],
      "locales": {
        "en": {
          "title": "Upload workspace files",
          "purpose": "Copy selected local files into the current workspace.",
          "when": "When the task needs documents or directories in a specific workspace.",
          "steps": [
            "Check the current directory and choose Upload.",
            "Select files and confirm any overwrite prompt carefully."
          ],
          "permissions": "Workspace access and file permissions apply. Selecting a workspace does not grant access.",
          "limits": "Changes affect the selected workspace. Check the path and retain a copy before replacing important content.",
          "example": "Add source documents to a project folder."
        },
        "nl": {
          "title": "Bestanden naar een werkruimte uploaden",
          "purpose": "Kopieer gekozen lokale bestanden naar de huidige werkruimte.",
          "when": "Wanneer de taak documenten of mappen in een bepaalde werkruimte nodig heeft.",
          "steps": [
            "Controleer de huidige map en kies Uploaden.",
            "Selecteer bestanden en controleer een eventuele overschrijfmelding zorgvuldig."
          ],
          "permissions": "Toegang tot de werkruimte en bestandsrechten gelden. Een werkruimte kiezen geeft geen extra toegang.",
          "limits": "Wijzigingen gelden voor de gekozen werkruimte. Controleer het pad en bewaar een kopie voordat je belangrijke inhoud vervangt.",
          "example": "Voeg brondocumenten toe aan een projectmap."
        }
      }
    },
    {
      "id": "webui.files.preview",
      "area": "files",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.files.preview",
        "#btnRenderMarkdownAnyway"
      ],
      "source_refs": [
        "static/index.html:1978"
      ],
      "related": [
        "webui.files.workspace",
        "webui.files.manage",
        "webui.files.access"
      ],
      "locales": {
        "en": {
          "title": "File preview and rich Markdown",
          "purpose": "Read supported file previews and optionally render a large Markdown file.",
          "when": "When the task needs documents or directories in a specific workspace.",
          "steps": [
            "Select a file.",
            "If a large file is shown as text, choose rich Markdown only when needed.",
            "Close the preview to return to the file list."
          ],
          "permissions": "Workspace access and file permissions apply. Selecting a workspace does not grant access.",
          "limits": "Changes affect the selected workspace. Check the path and retain a copy before replacing important content.",
          "example": "Read headings and tables in a generated report."
        },
        "nl": {
          "title": "Bestandsvoorbeeld en rijke Markdown",
          "purpose": "Lees ondersteunde bestandsvoorbeelden en geef eventueel een groot Markdown-bestand rijk weer.",
          "when": "Wanneer de taak documenten of mappen in een bepaalde werkruimte nodig heeft.",
          "steps": [
            "Kies een bestand.",
            "Kies alleen indien nodig rijke Markdown als een groot bestand als tekst wordt getoond.",
            "Sluit het voorbeeld om terug te keren naar de lijst."
          ],
          "permissions": "Toegang tot de werkruimte en bestandsrechten gelden. Een werkruimte kiezen geeft geen extra toegang.",
          "limits": "Wijzigingen gelden voor de gekozen werkruimte. Controleer het pad en bewaar een kopie voordat je belangrijke inhoud vervangt.",
          "example": "Lees koppen en tabellen in een gegenereerd rapport."
        }
      }
    },
    {
      "id": "webui.files.edit",
      "area": "files",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.files.edit",
        "#btnEditFile",
        "#previewEditArea"
      ],
      "source_refs": [
        "static/index.html:1980",
        "static/index.html:1992"
      ],
      "related": [
        "webui.files.workspace",
        "webui.files.manage",
        "webui.files.access"
      ],
      "locales": {
        "en": {
          "title": "Edit a workspace file",
          "purpose": "Update an editable file through the workspace editor.",
          "when": "When the task needs documents or directories in a specific workspace.",
          "steps": [
            "Open the file and choose Edit.",
            "Review changes in the editor and use its save or cancel action."
          ],
          "permissions": "Workspace access and file permissions apply. Selecting a workspace does not grant access.",
          "limits": "Changes affect the selected workspace. Check the path and retain a copy before replacing important content.",
          "example": "Correct a typo in a project note."
        },
        "nl": {
          "title": "Een werkruimtebestand bewerken",
          "purpose": "Wijzig een bewerkbaar bestand via de werkruimte-editor.",
          "when": "Wanneer de taak documenten of mappen in een bepaalde werkruimte nodig heeft.",
          "steps": [
            "Open het bestand en kies Bewerken.",
            "Controleer wijzigingen in de editor en gebruik Opslaan of Annuleren."
          ],
          "permissions": "Toegang tot de werkruimte en bestandsrechten gelden. Een werkruimte kiezen geeft geen extra toegang.",
          "limits": "Wijzigingen gelden voor de gekozen werkruimte. Controleer het pad en bewaar een kopie voordat je belangrijke inhoud vervangt.",
          "example": "Corrigeer een typefout in een projectnotitie."
        }
      }
    },
    {
      "id": "webui.files.download",
      "area": "files",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.files.download",
        "#btnOpenInBrowser",
        "#btnDownloadFile"
      ],
      "source_refs": [
        "static/index.html:1977",
        "static/index.html:1979"
      ],
      "related": [
        "webui.files.workspace",
        "webui.files.manage",
        "webui.files.access"
      ],
      "locales": {
        "en": {
          "title": "Download or open a file",
          "purpose": "Download the previewed file or open a supported browser preview.",
          "when": "When the task needs documents or directories in a specific workspace.",
          "steps": [
            "Choose Download to save locally.",
            "Use Open in browser for a separate supported preview and check the file first."
          ],
          "permissions": "Workspace access and file permissions apply. Selecting a workspace does not grant access.",
          "limits": "Changes affect the selected workspace. Check the path and retain a copy before replacing important content.",
          "example": "Save a completed document to your device."
        },
        "nl": {
          "title": "Een bestand downloaden of openen",
          "purpose": "Download het getoonde bestand of open een ondersteund browsertabblad.",
          "when": "Wanneer de taak documenten of mappen in een bepaalde werkruimte nodig heeft.",
          "steps": [
            "Kies Downloaden om lokaal op te slaan.",
            "Gebruik Openen in browser voor een afzonderlijk ondersteund voorbeeld en controleer eerst het bestand."
          ],
          "permissions": "Toegang tot de werkruimte en bestandsrechten gelden. Een werkruimte kiezen geeft geen extra toegang.",
          "limits": "Wijzigingen gelden voor de gekozen werkruimte. Controleer het pad en bewaar een kopie voordat je belangrijke inhoud vervangt.",
          "example": "Bewaar een afgerond document op je apparaat."
        }
      }
    },
    {
      "id": "webui.files.path",
      "area": "files",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.files.path",
        "#btnCopyPreviewRelPath"
      ],
      "source_refs": [
        "static/index.html:1976"
      ],
      "related": [
        "webui.files.workspace",
        "webui.files.manage",
        "webui.files.access"
      ],
      "locales": {
        "en": {
          "title": "Copy a relative file path",
          "purpose": "Copy the previewed file’s path relative to its workspace.",
          "when": "When the task needs documents or directories in a specific workspace.",
          "steps": [
            "Select the file and choose Copy relative path.",
            "Paste the path where the workspace context is known."
          ],
          "permissions": "Workspace access and file permissions apply. Selecting a workspace does not grant access.",
          "limits": "Changes affect the selected workspace. Check the path and retain a copy before replacing important content.",
          "example": "Refer to a source file in a follow-up message."
        },
        "nl": {
          "title": "Een relatief bestandspad kopiëren",
          "purpose": "Kopieer het pad van het getoonde bestand ten opzichte van de werkruimte.",
          "when": "Wanneer de taak documenten of mappen in een bepaalde werkruimte nodig heeft.",
          "steps": [
            "Kies het bestand en kies Relatief pad kopiëren.",
            "Plak het pad waar de werkruimtecontext bekend is."
          ],
          "permissions": "Toegang tot de werkruimte en bestandsrechten gelden. Een werkruimte kiezen geeft geen extra toegang.",
          "limits": "Wijzigingen gelden voor de gekozen werkruimte. Controleer het pad en bewaar een kopie voordat je belangrijke inhoud vervangt.",
          "example": "Verwijs in een vervolgbericht naar een bronbestand."
        }
      }
    },
    {
      "id": "webui.files.artifacts",
      "area": "files",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.files.artifacts",
        "#workspaceArtifactsTab"
      ],
      "source_refs": [
        "static/index.html:1964",
        "static/workspace.js:738"
      ],
      "related": [
        "webui.files.workspace",
        "webui.files.manage",
        "webui.files.access"
      ],
      "locales": {
        "en": {
          "title": "Generated artifacts",
          "purpose": "Find files associated with agent output.",
          "when": "When the task needs documents or directories in a specific workspace.",
          "steps": [
            "Open the Artifacts tab or a file link in a response.",
            "Inspect the resolved workspace path and preview the file."
          ],
          "permissions": "Workspace access and file permissions apply. Selecting a workspace does not grant access.",
          "limits": "Changes affect the selected workspace. Check the path and retain a copy before replacing important content.",
          "example": "Open a document produced by a conversation."
        },
        "nl": {
          "title": "Gegenereerde bestanden",
          "purpose": "Vind bestanden die bij agentuitvoer horen.",
          "when": "Wanneer de taak documenten of mappen in een bepaalde werkruimte nodig heeft.",
          "steps": [
            "Open het tabblad Resultaten of een bestandslink in een antwoord.",
            "Controleer het werkruimtepad en bekijk het bestand."
          ],
          "permissions": "Toegang tot de werkruimte en bestandsrechten gelden. Een werkruimte kiezen geeft geen extra toegang.",
          "limits": "Wijzigingen gelden voor de gekozen werkruimte. Controleer het pad en bewaar een kopie voordat je belangrijke inhoud vervangt.",
          "example": "Open een document dat in een gesprek is gemaakt."
        }
      }
    },
    {
      "id": "webui.files.todos",
      "area": "files",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.files.todos",
        "#workspaceTodosTab"
      ],
      "source_refs": [
        "static/index.html:1965"
      ],
      "related": [
        "webui.files.workspace",
        "webui.files.manage",
        "webui.files.access"
      ],
      "locales": {
        "en": {
          "title": "Workspace todos",
          "purpose": "View the todo list exposed for the current workspace.",
          "when": "When the task needs documents or directories in a specific workspace.",
          "steps": [
            "Open the Todos tab if enabled.",
            "Read the listed work and current status in the selected workspace."
          ],
          "permissions": "Workspace access and file permissions apply. Selecting a workspace does not grant access.",
          "limits": "Changes affect the selected workspace. Check the path and retain a copy before replacing important content.",
          "example": "Review the remaining items for the current workspace."
        },
        "nl": {
          "title": "Werkruimtetaken",
          "purpose": "Bekijk de takenlijst voor de huidige werkruimte.",
          "when": "Wanneer de taak documenten of mappen in een bepaalde werkruimte nodig heeft.",
          "steps": [
            "Open het tabblad Taken indien ingeschakeld.",
            "Lees het vermelde werk en de huidige status in de gekozen werkruimte."
          ],
          "permissions": "Toegang tot de werkruimte en bestandsrechten gelden. Een werkruimte kiezen geeft geen extra toegang.",
          "limits": "Wijzigingen gelden voor de gekozen werkruimte. Controleer het pad en bewaar een kopie voordat je belangrijke inhoud vervangt.",
          "example": "Bekijk resterende punten voor de huidige werkruimte."
        }
      }
    },
    {
      "id": "webui.files.preferences",
      "area": "files",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.files.preferences",
        "#btnWorkspacePrefs"
      ],
      "source_refs": [
        "static/index.html:1957"
      ],
      "related": [
        "webui.files.workspace",
        "webui.files.manage",
        "webui.files.access"
      ],
      "locales": {
        "en": {
          "title": "Workspace panel options",
          "purpose": "Adjust the file panel’s available display options.",
          "when": "When the task needs documents or directories in a specific workspace.",
          "steps": [
            "Open Workspace options.",
            "Select the desired presentation option and verify the panel."
          ],
          "permissions": "Workspace access and file permissions apply. Selecting a workspace does not grant access.",
          "limits": "Changes affect the selected workspace. Check the path and retain a copy before replacing important content.",
          "example": "Adjust file browsing to suit the current task."
        },
        "nl": {
          "title": "Opties voor het werkruimtepaneel",
          "purpose": "Pas beschikbare weergaveopties van het bestandspaneel aan.",
          "when": "Wanneer de taak documenten of mappen in een bepaalde werkruimte nodig heeft.",
          "steps": [
            "Open Werkruimteopties.",
            "Kies de gewenste weergaveoptie en controleer het paneel."
          ],
          "permissions": "Toegang tot de werkruimte en bestandsrechten gelden. Een werkruimte kiezen geeft geen extra toegang.",
          "limits": "Wijzigingen gelden voor de gekozen werkruimte. Controleer het pad en bewaar een kopie voordat je belangrijke inhoud vervangt.",
          "example": "Pas bestandsnavigatie aan de huidige taak aan."
        }
      }
    },
    {
      "id": "webui.boards.create",
      "area": "boards",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.boards.create",
        "#kanbanNewTaskBtn",
        "#kanbanNewTaskTitle",
        "#kanbanTaskModalTitleInput",
        "#kanbanTaskModalBody",
        "#kanbanTaskModalSubmit"
      ],
      "source_refs": [
        "static/index.html:2133",
        "static/index.html:2137",
        "static/index.html:2196",
        "static/index.html:2197",
        "static/index.html:241",
        "static/index.html:259",
        "static/index.html:260",
        "static/panels.js:3113",
        "static/panels.js:4698",
        "static/panels.js:4700"
      ],
      "related": [
        "webui.boards.status",
        "webui.boards.assignment",
        "webui.boards.runtime"
      ],
      "locales": {
        "en": {
          "title": "Create and edit a board task",
          "purpose": "Record a task with a title and clear acceptance criteria.",
          "when": "When coordinating ownership, prerequisites and progress of work on a board.",
          "steps": [
            "Choose New task or open a task and choose Edit.",
            "Fill in title and description, review the fields and save."
          ],
          "permissions": "Board and task permissions apply. Automated execution also needs an allowed worker.",
          "limits": "Board status is a coordination record; it is not proof that external work has completed.",
          "example": "Define a report task with its expected deliverable."
        },
        "nl": {
          "title": "Een bordtaak maken en bewerken",
          "purpose": "Leg een taak vast met een titel en duidelijke acceptatiecriteria.",
          "when": "Bij het afstemmen van eigenaarschap, voorwaarden en voortgang op een taakbord.",
          "steps": [
            "Kies Nieuwe taak of open een taak en kies Bewerken.",
            "Vul titel en beschrijving in, controleer de velden en sla op."
          ],
          "permissions": "Bord- en taakrechten gelden. Automatische uitvoering vereist ook een toegestane uitvoerder.",
          "limits": "Bordstatus is een werkregistratie en geen bewijs dat extern werk voltooid is.",
          "example": "Beschrijf een rapportagetaak met het verwachte resultaat."
        }
      }
    },
    {
      "id": "webui.boards.status",
      "area": "boards",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.boards.status",
        "#kanbanTaskModalStatus",
        "#kanbanTaskModalPriority"
      ],
      "source_refs": [
        "static/index.html:2143",
        "static/index.html:2151",
        "static/panels.js:3333",
        "static/panels.js:3334",
        "static/panels.js:4695"
      ],
      "related": [
        "webui.boards.create",
        "webui.boards.assignment",
        "webui.boards.runtime"
      ],
      "locales": {
        "en": {
          "title": "Task status and priority",
          "purpose": "Record progress and urgency for a board task.",
          "when": "When coordinating ownership, prerequisites and progress of work on a board.",
          "steps": [
            "Select the status and priority in the task editor.",
            "Save, or use an offered quick status action and verify the card."
          ],
          "permissions": "Board and task permissions apply. Automated execution also needs an allowed worker.",
          "limits": "Board status is a coordination record; it is not proof that external work has completed.",
          "example": "Mark a reviewed task as complete."
        },
        "nl": {
          "title": "Taakstatus en prioriteit",
          "purpose": "Leg voortgang en urgentie van een bordtaak vast.",
          "when": "Bij het afstemmen van eigenaarschap, voorwaarden en voortgang op een taakbord.",
          "steps": [
            "Kies status en prioriteit in de taakeditor.",
            "Sla op of gebruik een aangeboden snelle statusactie en controleer de kaart."
          ],
          "permissions": "Bord- en taakrechten gelden. Automatische uitvoering vereist ook een toegestane uitvoerder.",
          "limits": "Bordstatus is een werkregistratie en geen bewijs dat extern werk voltooid is.",
          "example": "Markeer een gecontroleerde taak als voltooid."
        }
      }
    },
    {
      "id": "webui.boards.assignment",
      "area": "boards",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.boards.assignment",
        "#kanbanTaskModalAssignee",
        "#kanbanTaskModalTenant"
      ],
      "source_refs": [
        "static/index.html:2157",
        "static/index.html:2164"
      ],
      "related": [
        "webui.boards.create",
        "webui.boards.status",
        "webui.boards.runtime"
      ],
      "locales": {
        "en": {
          "title": "Assignee and tenant",
          "purpose": "Associate a task with an allowed assignee and optional project or team label.",
          "when": "When coordinating ownership, prerequisites and progress of work on a board.",
          "steps": [
            "Choose the assignee and enter the optional tenant label.",
            "Save and check who is expected to perform the work."
          ],
          "permissions": "Board and task permissions apply. Automated execution also needs an allowed worker.",
          "limits": "Board status is a coordination record; it is not proof that external work has completed.",
          "example": "Assign a project task to its responsible worker."
        },
        "nl": {
          "title": "Uitvoerder en tenant",
          "purpose": "Koppel een taak aan een toegestane uitvoerder en eventueel project- of teamlabel.",
          "when": "Bij het afstemmen van eigenaarschap, voorwaarden en voortgang op een taakbord.",
          "steps": [
            "Kies de uitvoerder en vul eventueel een tenantlabel in.",
            "Sla op en controleer wie het werk moet uitvoeren."
          ],
          "permissions": "Bord- en taakrechten gelden. Automatische uitvoering vereist ook een toegestane uitvoerder.",
          "limits": "Bordstatus is een werkregistratie en geen bewijs dat extern werk voltooid is.",
          "example": "Wijs een projecttaak toe aan de verantwoordelijke uitvoerder."
        }
      }
    },
    {
      "id": "webui.boards.runtime",
      "area": "boards",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.boards.runtime",
        "#kanbanTaskModalWorkspaceKind",
        "#kanbanTaskModalWorkspacePath",
        "#kanbanTaskModalSkills",
        "#kanbanTaskModalMaxRuntimeSeconds"
      ],
      "source_refs": [
        "static/index.html:2169",
        "static/index.html:2177",
        "static/index.html:2182",
        "static/index.html:2186"
      ],
      "related": [
        "webui.boards.create",
        "webui.boards.status",
        "webui.boards.assignment"
      ],
      "locales": {
        "en": {
          "title": "Workspace, skills and runtime limit",
          "purpose": "Specify the execution context and time limit for an automated board task.",
          "when": "When coordinating ownership, prerequisites and progress of work on a board.",
          "steps": [
            "Choose workspace kind and path.",
            "Select required skills and a suitable maximum runtime; save."
          ],
          "permissions": "Board and task permissions apply. Automated execution also needs an allowed worker.",
          "limits": "Board status is a coordination record; it is not proof that external work has completed.",
          "example": "Constrain a worker task to the project workspace."
        },
        "nl": {
          "title": "Werkruimte, skills en tijdslimiet",
          "purpose": "Bepaal uitvoeringscontext en tijdslimiet van een automatische bordtaak.",
          "when": "Bij het afstemmen van eigenaarschap, voorwaarden en voortgang op een taakbord.",
          "steps": [
            "Kies werkruimtetype en pad.",
            "Kies benodigde skills en een passende maximale looptijd; sla op."
          ],
          "permissions": "Bord- en taakrechten gelden. Automatische uitvoering vereist ook een toegestane uitvoerder.",
          "limits": "Bordstatus is een werkregistratie en geen bewijs dat extern werk voltooid is.",
          "example": "Beperk een uitvoertaak tot de projectwerkruimte."
        }
      }
    },
    {
      "id": "webui.boards.links",
      "area": "boards",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.boards.links",
        "#kanbanTaskModalParents",
        "#kanbanDependencyInput"
      ],
      "source_refs": [
        "static/index.html:2191",
        "static/panels.js:4051",
        "static/panels.js:4060",
        "static/panels.js:4062"
      ],
      "related": [
        "webui.boards.create",
        "webui.boards.status",
        "webui.boards.assignment"
      ],
      "locales": {
        "en": {
          "title": "Parents and dependencies",
          "purpose": "Describe which tasks belong together or must finish first.",
          "when": "When coordinating ownership, prerequisites and progress of work on a board.",
          "steps": [
            "Set a parent task in the editor or add a dependency by task ID.",
            "Remove an incorrect dependency and recheck the order."
          ],
          "permissions": "Board and task permissions apply. Automated execution also needs an allowed worker.",
          "limits": "Board status is a coordination record; it is not proof that external work has completed.",
          "example": "Make review depend on completion of the draft."
        },
        "nl": {
          "title": "Bovenliggende taken en afhankelijkheden",
          "purpose": "Leg vast welke taken samenhoren of eerst gereed moeten zijn.",
          "when": "Bij het afstemmen van eigenaarschap, voorwaarden en voortgang op een taakbord.",
          "steps": [
            "Stel een bovenliggende taak in of voeg een afhankelijkheid toe via taak-ID.",
            "Verwijder een onjuiste afhankelijkheid en controleer de volgorde."
          ],
          "permissions": "Bord- en taakrechten gelden. Automatische uitvoering vereist ook een toegestane uitvoerder.",
          "limits": "Bordstatus is een werkregistratie en geen bewijs dat extern werk voltooid is.",
          "example": "Laat beoordeling afhangen van voltooiing van het concept."
        }
      }
    },
    {
      "id": "webui.boards.comments",
      "area": "boards",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.boards.comments",
        "#kanbanCommentInput"
      ],
      "source_refs": [
        "static/panels.js:4713",
        "static/panels.js:4714"
      ],
      "related": [
        "webui.boards.create",
        "webui.boards.status",
        "webui.boards.assignment"
      ],
      "locales": {
        "en": {
          "title": "Task comments",
          "purpose": "Record progress notes and coordination details on a task.",
          "when": "When coordinating ownership, prerequisites and progress of work on a board.",
          "steps": [
            "Open task details.",
            "Write a concise comment and post it; avoid credentials or unrelated private data."
          ],
          "permissions": "Board and task permissions apply. Automated execution also needs an allowed worker.",
          "limits": "Board status is a coordination record; it is not proof that external work has completed.",
          "example": "Explain why a task needs another review."
        },
        "nl": {
          "title": "Taakreacties",
          "purpose": "Leg voortgangsnotities en afstemming vast bij een taak.",
          "when": "Bij het afstemmen van eigenaarschap, voorwaarden en voortgang op een taakbord.",
          "steps": [
            "Open taakdetails.",
            "Schrijf een korte reactie en plaats deze; vermijd inloggegevens en onnodige privégegevens."
          ],
          "permissions": "Bord- en taakrechten gelden. Automatische uitvoering vereist ook een toegestane uitvoerder.",
          "limits": "Bordstatus is een werkregistratie en geen bewijs dat extern werk voltooid is.",
          "example": "Leg uit waarom een taak opnieuw beoordeeld moet worden."
        }
      }
    },
    {
      "id": "webui.boards.block",
      "area": "boards",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.boards.block"
      ],
      "source_refs": [
        "static/panels.js:4696"
      ],
      "related": [
        "webui.boards.create",
        "webui.boards.status",
        "webui.boards.assignment"
      ],
      "locales": {
        "en": {
          "title": "Block and unblock work",
          "purpose": "Mark a task as blocked when a prerequisite is missing.",
          "when": "When coordinating ownership, prerequisites and progress of work on a board.",
          "steps": [
            "Choose Block and record the reason if requested.",
            "Choose Unblock after the prerequisite is resolved."
          ],
          "permissions": "Board and task permissions apply. Automated execution also needs an allowed worker.",
          "limits": "Board status is a coordination record; it is not proof that external work has completed.",
          "example": "Pause a task while waiting for required access."
        },
        "nl": {
          "title": "Werk blokkeren en deblokkeren",
          "purpose": "Markeer een taak als geblokkeerd wanneer een voorwaarde ontbreekt.",
          "when": "Bij het afstemmen van eigenaarschap, voorwaarden en voortgang op een taakbord.",
          "steps": [
            "Kies Blokkeren en vermeld zo nodig de reden.",
            "Kies Deblokkeren nadat de voorwaarde is vervuld."
          ],
          "permissions": "Bord- en taakrechten gelden. Automatische uitvoering vereist ook een toegestane uitvoerder.",
          "limits": "Bordstatus is een werkregistratie en geen bewijs dat extern werk voltooid is.",
          "example": "Pauzeer een taak in afwachting van benodigde toegang."
        }
      }
    },
    {
      "id": "webui.boards.filter",
      "area": "boards",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.boards.filter",
        "#kanbanRefreshBtn",
        "#kanbanSearch",
        "#kanbanAssigneeFilter",
        "#kanbanTenantFilter",
        "#kanbanIncludeArchived",
        "#kanbanOnlyMine"
      ],
      "source_refs": [
        "static/index.html:242",
        "static/index.html:246",
        "static/index.html:247",
        "static/index.html:248",
        "static/index.html:249",
        "static/index.html:250",
        "static/panels.js:3455"
      ],
      "related": [
        "webui.boards.create",
        "webui.boards.status",
        "webui.boards.assignment"
      ],
      "locales": {
        "en": {
          "title": "Search and filter board tasks",
          "purpose": "Narrow the task list by text, assignee, tenant, archive status or your own tasks.",
          "when": "When coordinating ownership, prerequisites and progress of work on a board.",
          "steps": [
            "Set the search text and desired filters.",
            "Refresh for current data or clear filters to restore the full view."
          ],
          "permissions": "Board and task permissions apply. Automated execution also needs an allowed worker.",
          "limits": "Board status is a coordination record; it is not proof that external work has completed.",
          "example": "Show only your open project tasks."
        },
        "nl": {
          "title": "Bordtaken zoeken en filteren",
          "purpose": "Beperk de takenlijst op tekst, uitvoerder, tenant, archiefstatus of eigen taken.",
          "when": "Bij het afstemmen van eigenaarschap, voorwaarden en voortgang op een taakbord.",
          "steps": [
            "Stel zoektekst en gewenste filters in.",
            "Ververs voor actuele gegevens of wis filters voor het volledige overzicht."
          ],
          "permissions": "Bord- en taakrechten gelden. Automatische uitvoering vereist ook een toegestane uitvoerder.",
          "limits": "Bordstatus is een werkregistratie en geen bewijs dat extern werk voltooid is.",
          "example": "Toon alleen je eigen open projecttaken."
        }
      }
    },
    {
      "id": "webui.boards.bulk",
      "area": "boards",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.boards.bulk",
        "#kanbanBulkStatus"
      ],
      "source_refs": [
        "static/index.html:253",
        "static/index.html:254"
      ],
      "related": [
        "webui.boards.create",
        "webui.boards.status",
        "webui.boards.assignment"
      ],
      "locales": {
        "en": {
          "title": "Bulk status change",
          "purpose": "Apply a status change to selected tasks together.",
          "when": "When coordinating ownership, prerequisites and progress of work on a board.",
          "steps": [
            "Select the intended tasks and desired bulk status.",
            "Review the selection before applying the change."
          ],
          "permissions": "Board and task permissions apply. Automated execution also needs an allowed worker.",
          "limits": "Board status is a coordination record; it is not proof that external work has completed.",
          "example": "Move several reviewed tasks to the same status."
        },
        "nl": {
          "title": "Status van meerdere taken wijzigen",
          "purpose": "Pas een statuswijziging toe op meerdere gekozen taken tegelijk.",
          "when": "Bij het afstemmen van eigenaarschap, voorwaarden en voortgang op een taakbord.",
          "steps": [
            "Kies de bedoelde taken en gewenste gezamenlijke status.",
            "Controleer de selectie voordat je de wijziging toepast."
          ],
          "permissions": "Bord- en taakrechten gelden. Automatische uitvoering vereist ook een toegestane uitvoerder.",
          "limits": "Bordstatus is een werkregistratie en geen bewijs dat extern werk voltooid is.",
          "example": "Verplaats meerdere gecontroleerde taken naar dezelfde status."
        }
      }
    },
    {
      "id": "webui.boards.dispatch",
      "area": "boards",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.boards.dispatch",
        "#btnKanbanPreviewDispatcher",
        "#btnKanbanRunDispatcher"
      ],
      "source_refs": [
        "static/index.html:255",
        "static/index.html:256",
        "static/index.html:914",
        "static/index.html:915"
      ],
      "related": [
        "webui.boards.create",
        "webui.boards.status",
        "webui.boards.assignment"
      ],
      "locales": {
        "en": {
          "title": "Preview and run dispatch",
          "purpose": "Inspect or request task dispatch to eligible workers.",
          "when": "When coordinating ownership, prerequisites and progress of work on a board.",
          "steps": [
            "Use Preview dispatcher to inspect the plan.",
            "Choose Run only after reviewing eligible tasks and execution scope."
          ],
          "permissions": "Board and task permissions apply. Automated execution also needs an allowed worker.",
          "limits": "Board status is a coordination record; it is not proof that external work has completed.",
          "example": "Check which queued tasks would be picked up."
        },
        "nl": {
          "title": "Toewijzing vooraf bekijken en uitvoeren",
          "purpose": "Bekijk of start taaktoewijzing aan geschikte uitvoerders.",
          "when": "Bij het afstemmen van eigenaarschap, voorwaarden en voortgang op een taakbord.",
          "steps": [
            "Gebruik Toewijzing bekijken om het plan te controleren.",
            "Kies Uitvoeren pas na controle van geschikte taken en uitvoeringsscope."
          ],
          "permissions": "Bord- en taakrechten gelden. Automatische uitvoering vereist ook een toegestane uitvoerder.",
          "limits": "Bordstatus is een werkregistratie en geen bewijs dat extern werk voltooid is.",
          "example": "Controleer welke wachtende taken opgepakt zouden worden."
        }
      }
    },
    {
      "id": "webui.boards.boards",
      "area": "boards",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.boards.boards",
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
      ],
      "source_refs": [
        "static/index.html:2096",
        "static/index.html:2097",
        "static/index.html:2100",
        "static/index.html:2104",
        "static/index.html:2108",
        "static/index.html:2113",
        "static/index.html:2117",
        "static/index.html:2122",
        "static/index.html:2123",
        "static/index.html:901",
        "static/index.html:912",
        "static/panels.js:4946",
        "static/panels.js:4959",
        "static/panels.js:4963",
        "static/panels.js:4967"
      ],
      "related": [
        "webui.boards.create",
        "webui.boards.status",
        "webui.boards.assignment"
      ],
      "locales": {
        "en": {
          "title": "Create, switch, rename and archive boards",
          "purpose": "Organize tasks into named boards with their own presentation.",
          "when": "When coordinating ownership, prerequisites and progress of work on a board.",
          "steps": [
            "Open the board switcher or choose New board.",
            "Set name, slug, description, icon and color; save.",
            "Use the board menu to rename or archive the selected board."
          ],
          "permissions": "Board and task permissions apply. Automated execution also needs an allowed worker.",
          "limits": "Board status is a coordination record; it is not proof that external work has completed.",
          "example": "Keep operations work separate from project delivery."
        },
        "nl": {
          "title": "Borden maken, wisselen, hernoemen en archiveren",
          "purpose": "Orden taken in benoemde borden met een eigen weergave.",
          "when": "Bij het afstemmen van eigenaarschap, voorwaarden en voortgang op een taakbord.",
          "steps": [
            "Open de bordkiezer of kies Nieuw bord.",
            "Stel naam, slug, beschrijving, pictogram en kleur in; sla op.",
            "Gebruik het bordmenu om het gekozen bord te hernoemen of archiveren."
          ],
          "permissions": "Bord- en taakrechten gelden. Automatische uitvoering vereist ook een toegestane uitvoerder.",
          "limits": "Bordstatus is een werkregistratie en geen bewijs dat extern werk voltooid is.",
          "example": "Houd operationeel werk gescheiden van projectuitvoering."
        }
      }
    },
    {
      "id": "webui.boards.consolidated",
      "area": "boards",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.boards.consolidated",
        "#btnKanbanViewToggle"
      ],
      "source_refs": [
        "static/index.html:913"
      ],
      "related": [
        "webui.boards.create",
        "webui.boards.status",
        "webui.boards.assignment"
      ],
      "locales": {
        "en": {
          "title": "Consolidated board view",
          "purpose": "Inspect tasks across permitted boards together.",
          "when": "When coordinating ownership, prerequisites and progress of work on a board.",
          "steps": [
            "Choose the consolidated view toggle.",
            "Use filters and inspect the board label before changing a task."
          ],
          "permissions": "Board and task permissions apply. Automated execution also needs an allowed worker.",
          "limits": "Board status is a coordination record; it is not proof that external work has completed.",
          "example": "Review workload across several project boards."
        },
        "nl": {
          "title": "Gecombineerd bordoverzicht",
          "purpose": "Bekijk taken van toegestane borden samen.",
          "when": "Bij het afstemmen van eigenaarschap, voorwaarden en voortgang op een taakbord.",
          "steps": [
            "Kies de knop voor het gecombineerde overzicht.",
            "Gebruik filters en controleer het bordlabel voordat je een taak wijzigt."
          ],
          "permissions": "Bord- en taakrechten gelden. Automatische uitvoering vereist ook een toegestane uitvoerder.",
          "limits": "Bordstatus is een werkregistratie en geen bewijs dat extern werk voltooid is.",
          "example": "Bekijk de werklast over meerdere projectborden."
        }
      }
    },
    {
      "id": "webui.memory.personal",
      "area": "memory",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.memory.personal",
        "#btnEditMemoryDetail",
        "#btnCancelMemoryDetail",
        "#btnSaveMemoryDetail",
        "#memEditContent"
      ],
      "source_refs": [
        "static/index.html:861",
        "static/index.html:862",
        "static/index.html:863",
        "static/panels.js:6472"
      ],
      "related": [
        "webui.memory.company",
        "webui.memory.project",
        "webui.memory.identity"
      ],
      "locales": {
        "en": {
          "title": "My notes and personal context",
          "purpose": "Keep personal context separate from shared company or bot knowledge.",
          "when": "When checking stored context, its source or the audience allowed to read it.",
          "steps": [
            "Open Memory and choose your personal notes or profile entry.",
            "Read its scope before editing; save only information appropriate for that scope."
          ],
          "permissions": "Only stores and documents permitted for your identity are available. Admin status does not open another person’s private memory.",
          "limits": "Keep sensitive personal information in the correct private scope. Shared knowledge is visible to its permitted audience.",
          "example": "Record your preferred response style in your own context."
        },
        "nl": {
          "title": "Mijn notities en persoonlijke context",
          "purpose": "Houd persoonlijke context gescheiden van gedeelde bedrijfs- of botkennis.",
          "when": "Bij het controleren van opgeslagen context, de bron of de doelgroep die deze mag lezen.",
          "steps": [
            "Open Geheugen en kies je persoonlijke notities of profielitem.",
            "Lees de scope voordat je bewerkt; bewaar alleen passende informatie."
          ],
          "permissions": "Alleen opslag en documenten die voor jouw identiteit zijn toegestaan zijn beschikbaar. Beheerdersrechten openen geen privégeheugen van een ander.",
          "limits": "Bewaar gevoelige persoonlijke informatie in de juiste privéscope. Gedeelde kennis is zichtbaar voor de toegestane doelgroep.",
          "example": "Leg je voorkeursstijl voor antwoorden vast in je eigen context."
        }
      }
    },
    {
      "id": "webui.memory.company",
      "area": "memory",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.memory.company"
      ],
      "source_refs": [
        "static/panels.js"
      ],
      "related": [
        "webui.memory.personal",
        "webui.memory.project",
        "webui.memory.identity"
      ],
      "locales": {
        "en": {
          "title": "Company knowledge",
          "purpose": "Read or maintain shared organisational context when your role permits it.",
          "when": "When checking stored context, its source or the audience allowed to read it.",
          "steps": [
            "Select the company knowledge entry.",
            "Review the shared audience before saving a change."
          ],
          "permissions": "Only stores and documents permitted for your identity are available. Admin status does not open another person’s private memory.",
          "limits": "Keep sensitive personal information in the correct private scope. Shared knowledge is visible to its permitted audience.",
          "example": "Keep an approved company description consistent."
        },
        "nl": {
          "title": "Bedrijfskennis",
          "purpose": "Lees of onderhoud gedeelde organisatiecontext wanneer je rol dit toestaat.",
          "when": "Bij het controleren van opgeslagen context, de bron of de doelgroep die deze mag lezen.",
          "steps": [
            "Kies het bedrijfskennisitem.",
            "Controleer de gedeelde doelgroep voordat je een wijziging opslaat."
          ],
          "permissions": "Alleen opslag en documenten die voor jouw identiteit zijn toegestaan zijn beschikbaar. Beheerdersrechten openen geen privégeheugen van een ander.",
          "limits": "Bewaar gevoelige persoonlijke informatie in de juiste privéscope. Gedeelde kennis is zichtbaar voor de toegestane doelgroep.",
          "example": "Houd een goedgekeurde bedrijfsbeschrijving consistent."
        }
      }
    },
    {
      "id": "webui.memory.project",
      "area": "memory",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.memory.project"
      ],
      "source_refs": [
        "static/panels.js"
      ],
      "related": [
        "webui.memory.personal",
        "webui.memory.company",
        "webui.memory.identity"
      ],
      "locales": {
        "en": {
          "title": "Project memory",
          "purpose": "Use project-scoped context for ongoing shared work.",
          "when": "When checking stored context, its source or the audience allowed to read it.",
          "steps": [
            "Select the project and its memory entry.",
            "Check membership and scope before reading or updating context."
          ],
          "permissions": "Only stores and documents permitted for your identity are available. Admin status does not open another person’s private memory.",
          "limits": "Keep sensitive personal information in the correct private scope. Shared knowledge is visible to its permitted audience.",
          "example": "Keep decisions next to the project they belong to."
        },
        "nl": {
          "title": "Projectgeheugen",
          "purpose": "Gebruik projectgebonden context voor doorlopend gedeeld werk.",
          "when": "Bij het controleren van opgeslagen context, de bron of de doelgroep die deze mag lezen.",
          "steps": [
            "Kies het project en het geheugenitem.",
            "Controleer lidmaatschap en scope voordat je context leest of wijzigt."
          ],
          "permissions": "Alleen opslag en documenten die voor jouw identiteit zijn toegestaan zijn beschikbaar. Beheerdersrechten openen geen privégeheugen van een ander.",
          "limits": "Bewaar gevoelige persoonlijke informatie in de juiste privéscope. Gedeelde kennis is zichtbaar voor de toegestane doelgroep.",
          "example": "Bewaar besluiten bij het project waarop ze betrekking hebben."
        }
      }
    },
    {
      "id": "webui.memory.identity",
      "area": "memory",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.memory.identity"
      ],
      "source_refs": [
        "static/panels.js"
      ],
      "related": [
        "webui.memory.personal",
        "webui.memory.company",
        "webui.memory.project"
      ],
      "locales": {
        "en": {
          "title": "Bot identity and user profile",
          "purpose": "Distinguish the bot’s identity instructions from your personal profile.",
          "when": "When checking stored context, its source or the audience allowed to read it.",
          "steps": [
            "Read the selected entry’s title and scope.",
            "Edit only the intended instructions or profile and verify the saved entry."
          ],
          "permissions": "Only stores and documents permitted for your identity are available. Admin status does not open another person’s private memory.",
          "limits": "Keep sensitive personal information in the correct private scope. Shared knowledge is visible to its permitted audience.",
          "example": "Change personal preferences without rewriting a shared bot’s role."
        },
        "nl": {
          "title": "Botidentiteit en gebruikersprofiel",
          "purpose": "Onderscheid de identiteitsinstructies van de bot van je persoonlijke profiel.",
          "when": "Bij het controleren van opgeslagen context, de bron of de doelgroep die deze mag lezen.",
          "steps": [
            "Lees titel en scope van het gekozen item.",
            "Bewerk alleen de bedoelde instructies of het profiel en controleer het opgeslagen item."
          ],
          "permissions": "Alleen opslag en documenten die voor jouw identiteit zijn toegestaan zijn beschikbaar. Beheerdersrechten openen geen privégeheugen van een ander.",
          "limits": "Bewaar gevoelige persoonlijke informatie in de juiste privéscope. Gedeelde kennis is zichtbaar voor de toegestane doelgroep.",
          "example": "Wijzig persoonlijke voorkeuren zonder de rol van een gedeelde bot te herschrijven."
        }
      }
    },
    {
      "id": "webui.memory.external",
      "area": "memory",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.memory.external",
        "#externalNotesSource",
        "#externalNotesQuery"
      ],
      "source_refs": [
        "static/panels.js:6360",
        "static/panels.js:6366",
        "static/panels.js:6389",
        "static/panels.js:6390"
      ],
      "related": [
        "webui.memory.personal",
        "webui.memory.company",
        "webui.memory.project"
      ],
      "locales": {
        "en": {
          "title": "External notes browser",
          "purpose": "Search and preview notes from an enabled external source.",
          "when": "When checking stored context, its source or the audience allowed to read it.",
          "steps": [
            "Choose the notes source and enter a search.",
            "Open a result preview and check the source context."
          ],
          "permissions": "Only stores and documents permitted for your identity are available. Admin status does not open another person’s private memory.",
          "limits": "Keep sensitive personal information in the correct private scope. Shared knowledge is visible to its permitted audience.",
          "example": "Find an existing reference note before duplicating it."
        },
        "nl": {
          "title": "Externe notities bekijken",
          "purpose": "Zoek en bekijk notities uit een ingeschakelde externe bron.",
          "when": "Bij het controleren van opgeslagen context, de bron of de doelgroep die deze mag lezen.",
          "steps": [
            "Kies de notitiebron en vul een zoekopdracht in.",
            "Open een resultaatvoorbeeld en controleer de broncontext."
          ],
          "permissions": "Alleen opslag en documenten die voor jouw identiteit zijn toegestaan zijn beschikbaar. Beheerdersrechten openen geen privégeheugen van een ander.",
          "limits": "Bewaar gevoelige persoonlijke informatie in de juiste privéscope. Gedeelde kennis is zichtbaar voor de toegestane doelgroep.",
          "example": "Vind een bestaande referentienotitie voordat je een duplicaat maakt."
        }
      }
    },
    {
      "id": "webui.memory.explorer",
      "area": "memory",
      "status": "conditional",
      "conditions": [
        "hq-memory-reader",
        "explicit-bank-scope",
        "access-audit"
      ],
      "anchors": [
        "?help_feature=webui.memory.explorer"
      ],
      "source_refs": [
        "static/memory_dashboard.js",
        "api/memdash_scope.py",
        "api/memdash_views.py"
      ],
      "related": [
        "webui.memory.personal",
        "webui.memory.company",
        "webui.memory.project"
      ],
      "locales": {
        "en": {
          "title": "Memory explorer banks",
          "purpose": "Read the memory banks explicitly available to your signed-in identity.",
          "when": "When checking stored context, its source or the audience allowed to read it.",
          "steps": [
            "Open Memory, then Memory explorer.",
            "Choose an available bank and inspect its scope and source label."
          ],
          "permissions": "Only stores and documents permitted for your identity are available. Admin status does not open another person’s private memory.",
          "limits": "The explorer is read-only. Legacy sources are labeled separately; a failed required access-log write blocks the read. Private banks remain owner-only, including for other administrators.",
          "example": "Inspect your personal store without opening another person’s bank."
        },
        "nl": {
          "title": "Geheugenbanken verkennen",
          "purpose": "Lees de geheugenbanken die expliciet voor jouw ingelogde identiteit beschikbaar zijn.",
          "when": "Bij het controleren van opgeslagen context, de bron of de doelgroep die deze mag lezen.",
          "steps": [
            "Open Geheugen en daarna Geheugenverkenner.",
            "Kies een beschikbare bank en bekijk scope en bronlabel."
          ],
          "permissions": "Alleen opslag en documenten die voor jouw identiteit zijn toegestaan zijn beschikbaar. Beheerdersrechten openen geen privégeheugen van een ander.",
          "limits": "De verkenner is alleen-lezen. Oudere bronnen hebben een eigen label; als verplichte toegangsregistratie mislukt wordt lezen geblokkeerd. Privébanken blijven alleen voor de eigenaar, ook tegenover andere beheerders.",
          "example": "Bekijk je persoonlijke opslag zonder de bank van een ander te openen."
        }
      }
    },
    {
      "id": "webui.memory.search",
      "area": "memory",
      "status": "conditional",
      "conditions": [
        "hq-memory-reader",
        "explicit-bank-scope",
        "access-audit"
      ],
      "anchors": [
        "?help_feature=webui.memory.search"
      ],
      "source_refs": [
        "static/memory_dashboard.js",
        "api/memdash_scope.py",
        "api/memdash_views.py"
      ],
      "related": [
        "webui.memory.personal",
        "webui.memory.company",
        "webui.memory.project"
      ],
      "locales": {
        "en": {
          "title": "Search and inspect memory records",
          "purpose": "Find records within a permitted memory bank without editing them.",
          "when": "When checking stored context, its source or the audience allowed to read it.",
          "steps": [
            "Select a bank and enter a query.",
            "Inspect record details, timestamps and source information; clear the query to browse again."
          ],
          "permissions": "Only stores and documents permitted for your identity are available. Admin status does not open another person’s private memory.",
          "limits": "The explorer is read-only. Legacy sources are labeled separately; a failed required access-log write blocks the read. Private banks remain owner-only, including for other administrators.",
          "example": "Find the stored context behind a remembered preference."
        },
        "nl": {
          "title": "Geheugenrecords zoeken en bekijken",
          "purpose": "Vind records in een toegestane geheugenbank zonder ze te wijzigen.",
          "when": "Bij het controleren van opgeslagen context, de bron of de doelgroep die deze mag lezen.",
          "steps": [
            "Kies een bank en vul een zoekopdracht in.",
            "Bekijk recorddetails, tijdstippen en broninformatie; wis de zoekopdracht om weer te bladeren."
          ],
          "permissions": "Alleen opslag en documenten die voor jouw identiteit zijn toegestaan zijn beschikbaar. Beheerdersrechten openen geen privégeheugen van een ander.",
          "limits": "De verkenner is alleen-lezen. Oudere bronnen hebben een eigen label; als verplichte toegangsregistratie mislukt wordt lezen geblokkeerd. Privébanken blijven alleen voor de eigenaar, ook tegenover andere beheerders.",
          "example": "Vind opgeslagen context achter een onthouden voorkeur."
        }
      }
    },
    {
      "id": "webui.memory.audit",
      "area": "memory",
      "status": "conditional",
      "conditions": [
        "hq-memory-reader",
        "explicit-bank-scope",
        "access-audit"
      ],
      "anchors": [
        "?help_feature=webui.memory.audit"
      ],
      "source_refs": [
        "static/memory_dashboard.js",
        "api/memdash_scope.py",
        "api/memdash_views.py"
      ],
      "related": [
        "webui.memory.personal",
        "webui.memory.company",
        "webui.memory.project"
      ],
      "locales": {
        "en": {
          "title": "Memory access and read-only limits",
          "purpose": "Understand why a bank can be unavailable and why explorer reads are audited.",
          "when": "When checking stored context, its source or the audience allowed to read it.",
          "steps": [
            "Read the bank scope and availability notice.",
            "Use permitted access-log views if offered; ask an operator about an unavailable bank without copying its private contents."
          ],
          "permissions": "Only stores and documents permitted for your identity are available. Admin status does not open another person’s private memory.",
          "limits": "The explorer is read-only. Legacy sources are labeled separately; a failed required access-log write blocks the read. Private banks remain owner-only, including for other administrators.",
          "example": "Investigate a denied explorer read while preserving owner privacy."
        },
        "nl": {
          "title": "Geheugentoegang en alleen-lezenbeperkingen",
          "purpose": "Begrijp waarom een bank onbeschikbaar kan zijn en waarom lezen wordt geregistreerd.",
          "when": "Bij het controleren van opgeslagen context, de bron of de doelgroep die deze mag lezen.",
          "steps": [
            "Lees scope en beschikbaarheidsmelding van de bank.",
            "Gebruik toegestane toegangslogboeken indien aangeboden; vraag een beheerder naar een onbeschikbare bank zonder privé-inhoud te kopiëren."
          ],
          "permissions": "Alleen opslag en documenten die voor jouw identiteit zijn toegestaan zijn beschikbaar. Beheerdersrechten openen geen privégeheugen van een ander.",
          "limits": "De verkenner is alleen-lezen. Oudere bronnen hebben een eigen label; als verplichte toegangsregistratie mislukt wordt lezen geblokkeerd. Privébanken blijven alleen voor de eigenaar, ook tegenover andere beheerders.",
          "example": "Onderzoek een geweigerde leesactie met behoud van eigenaarprivacy."
        }
      }
    },
    {
      "id": "webui.skills.browse",
      "area": "skills",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.skills.browse",
        "#skillsSearch"
      ],
      "source_refs": [
        "static/commands.js",
        "static/index.html:274"
      ],
      "related": [
        "webui.skills.edit",
        "webui.skills.delete",
        "webui.skills.wiki"
      ],
      "locales": {
        "en": {
          "title": "Find and read a skill",
          "purpose": "Inspect available instruction packages before using them.",
          "when": "When reusable instructions need to be found or maintained for a repeatable task.",
          "steps": [
            "Open Skills and search by name or subject.",
            "Select a skill and read its instructions and scope.",
            "Composer shortcut: /skills. Review any required arguments in the command suggestions."
          ],
          "permissions": "Viewing and editing skills require the corresponding skill permissions.",
          "limits": "A skill supplies instructions, not additional permissions or credentials.",
          "example": "Find the reporting instructions used by a bot."
        },
        "nl": {
          "title": "Een skill vinden en lezen",
          "purpose": "Bekijk beschikbare instructiepakketten voordat je ze gebruikt.",
          "when": "Wanneer herbruikbare instructies voor een terugkerende taak gezocht of onderhouden moeten worden.",
          "steps": [
            "Open Skills en zoek op naam of onderwerp.",
            "Kies een skill en lees instructies en scope.",
            "Snelopdracht in het berichtveld: /skills. Controleer eventuele argumenten in de opdrachtsuggesties."
          ],
          "permissions": "Bekijken en bewerken van skills vereist de bijbehorende rechten.",
          "limits": "Een skill levert instructies, geen extra rechten of inloggegevens.",
          "example": "Vind de rapportage-instructies die een bot gebruikt."
        }
      }
    },
    {
      "id": "webui.skills.edit",
      "area": "skills",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.skills.edit",
        "#btnEditSkillDetail",
        "#btnCancelSkillDetail",
        "#btnSaveSkillDetail",
        "#skillFormName",
        "#skillFormCategory",
        "#skillFormContent"
      ],
      "source_refs": [
        "static/index.html:271",
        "static/index.html:844",
        "static/index.html:846",
        "static/index.html:847",
        "static/panels.js:6132",
        "static/panels.js:6137",
        "static/panels.js:6142"
      ],
      "related": [
        "webui.skills.browse",
        "webui.skills.delete",
        "webui.skills.wiki"
      ],
      "locales": {
        "en": {
          "title": "Create and edit skills",
          "purpose": "Maintain reusable instructions with a name and category.",
          "when": "When reusable instructions need to be found or maintained for a repeatable task.",
          "steps": [
            "Choose New skill or Edit.",
            "Set a valid name, category and clear instructions; save or cancel the edit."
          ],
          "permissions": "Viewing and editing skills require the corresponding skill permissions.",
          "limits": "A skill supplies instructions, not additional permissions or credentials.",
          "example": "Create a reusable review checklist."
        },
        "nl": {
          "title": "Skills maken en bewerken",
          "purpose": "Beheer herbruikbare instructies met een naam en categorie.",
          "when": "Wanneer herbruikbare instructies voor een terugkerende taak gezocht of onderhouden moeten worden.",
          "steps": [
            "Kies Nieuwe skill of Bewerken.",
            "Stel een geldige naam, categorie en duidelijke instructies in; sla op of annuleer."
          ],
          "permissions": "Bekijken en bewerken van skills vereist de bijbehorende rechten.",
          "limits": "Een skill levert instructies, geen extra rechten of inloggegevens.",
          "example": "Maak een herbruikbare controlelijst voor beoordelingen."
        }
      }
    },
    {
      "id": "webui.skills.delete",
      "area": "skills",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.skills.delete",
        "#btnDeleteSkillDetail"
      ],
      "source_refs": [
        "static/index.html:845"
      ],
      "related": [
        "webui.skills.browse",
        "webui.skills.edit",
        "webui.skills.wiki"
      ],
      "locales": {
        "en": {
          "title": "Delete a skill",
          "purpose": "Remove a skill through its confirmation workflow.",
          "when": "When reusable instructions need to be found or maintained for a repeatable task.",
          "steps": [
            "Select the skill and choose Delete.",
            "Check whether active bots or tasks still refer to it before confirming."
          ],
          "permissions": "Viewing and editing skills require the corresponding skill permissions.",
          "limits": "A skill supplies instructions, not additional permissions or credentials.",
          "example": "Remove an obsolete instruction package."
        },
        "nl": {
          "title": "Een skill verwijderen",
          "purpose": "Verwijder een skill via de bevestigingsprocedure.",
          "when": "Wanneer herbruikbare instructies voor een terugkerende taak gezocht of onderhouden moeten worden.",
          "steps": [
            "Kies de skill en kies Verwijderen.",
            "Controleer voor bevestigen of actieve bots of taken er nog naar verwijzen."
          ],
          "permissions": "Bekijken en bewerken van skills vereist de bijbehorende rechten.",
          "limits": "Een skill levert instructies, geen extra rechten of inloggegevens.",
          "example": "Verwijder een verouderd instructiepakket."
        }
      }
    },
    {
      "id": "webui.skills.wiki",
      "area": "skills",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.skills.wiki",
        "#wikiBrowserSearch"
      ],
      "source_refs": [
        "static/panels.js:14586",
        "static/panels.js:5493",
        "static/panels.js:5519",
        "static/panels.js:5522",
        "static/panels.js:5554",
        "static/panels.js:5557",
        "static/panels.js:5560"
      ],
      "related": [
        "webui.skills.browse",
        "webui.skills.edit",
        "webui.skills.delete"
      ],
      "locales": {
        "en": {
          "title": "Browse skill reference material",
          "purpose": "Search the available skill reference browser.",
          "when": "When reusable instructions need to be found or maintained for a repeatable task.",
          "steps": [
            "Open the wiki or reference browser.",
            "Search and read a result; use Back to return to the list."
          ],
          "permissions": "Viewing and editing skills require the corresponding skill permissions.",
          "limits": "A skill supplies instructions, not additional permissions or credentials.",
          "example": "Read reference material while preparing a skill."
        },
        "nl": {
          "title": "Skillreferenties bekijken",
          "purpose": "Zoek in de beschikbare referentiebrowser voor skills.",
          "when": "Wanneer herbruikbare instructies voor een terugkerende taak gezocht of onderhouden moeten worden.",
          "steps": [
            "Open de wiki- of referentiebrowser.",
            "Zoek en lees een resultaat; gebruik Terug voor de lijst."
          ],
          "permissions": "Bekijken en bewerken van skills vereist de bijbehorende rechten.",
          "limits": "Een skill levert instructies, geen extra rechten of inloggegevens.",
          "example": "Lees referenties bij het voorbereiden van een skill."
        }
      }
    },
    {
      "id": "webui.bots.select",
      "area": "bots",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.bots.select",
        "#titlebarProfileBtn",
        "#profileChip",
        "#btnActivateProfileDetail"
      ],
      "source_refs": [
        "static/index.html:121",
        "static/index.html:682",
        "static/index.html:968"
      ],
      "related": [
        "webui.bots.create",
        "webui.bots.identity",
        "webui.bots.instructions"
      ],
      "locales": {
        "en": {
          "title": "Select the active bot",
          "purpose": "Choose which permitted bot handles the conversation’s normal mode.",
          "when": "When preparing or maintaining a specialist assistant for a defined role.",
          "steps": [
            "Open the title-bar or composer bot picker.",
            "Select a bot and check its displayed identity before sending."
          ],
          "permissions": "Bot visibility, editing rights and permitted tools are checked separately.",
          "limits": "A bot cannot grant itself permissions or make unavailable connections usable.",
          "example": "Switch to the project’s specialist bot."
        },
        "nl": {
          "title": "De actieve bot kiezen",
          "purpose": "Kies welke toegestane bot het gesprek in normale modus afhandelt.",
          "when": "Bij het voorbereiden of onderhouden van een specialistische assistent met een duidelijke rol.",
          "steps": [
            "Open de botkiezer in de titelbalk of bij het berichtveld.",
            "Kies een bot en controleer de getoonde identiteit voordat je verstuurt."
          ],
          "permissions": "Zichtbaarheid van bots, bewerkrechten en toegestane tools worden afzonderlijk gecontroleerd.",
          "limits": "Een bot kan zichzelf geen rechten geven of onbeschikbare koppelingen bruikbaar maken.",
          "example": "Wissel naar de gespecialiseerde projectbot."
        }
      }
    },
    {
      "id": "webui.bots.create",
      "area": "bots",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.bots.create",
        "#builderBack",
        "#builderNext"
      ],
      "source_refs": [
        "static/bot-builder.js:108",
        "static/index.html:335"
      ],
      "related": [
        "webui.bots.select",
        "webui.bots.identity",
        "webui.bots.instructions"
      ],
      "locales": {
        "en": {
          "title": "Create a bot step by step",
          "purpose": "Build a bot from identity, instructions, permitted tools and review steps.",
          "when": "When preparing or maintaining a specialist assistant for a defined role.",
          "steps": [
            "Choose New bot.",
            "Complete each step using Continue and Back.",
            "Review the configuration and choose Create bot."
          ],
          "permissions": "Bot visibility, editing rights and permitted tools are checked separately.",
          "limits": "A bot cannot grant itself permissions or make unavailable connections usable.",
          "example": "Create a specialist that helps review documents."
        },
        "nl": {
          "title": "Stap voor stap een bot maken",
          "purpose": "Bouw een bot via identiteit, instructies, toegestane tools en controle.",
          "when": "Bij het voorbereiden of onderhouden van een specialistische assistent met een duidelijke rol.",
          "steps": [
            "Kies Nieuwe bot.",
            "Doorloop de stappen met Doorgaan en Terug.",
            "Controleer de configuratie en kies Bot maken."
          ],
          "permissions": "Zichtbaarheid van bots, bewerkrechten en toegestane tools worden afzonderlijk gecontroleerd.",
          "limits": "Een bot kan zichzelf geen rechten geven of onbeschikbare koppelingen bruikbaar maken.",
          "example": "Maak een specialist die helpt documenten te beoordelen."
        }
      }
    },
    {
      "id": "webui.bots.identity",
      "area": "bots",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.bots.identity"
      ],
      "source_refs": [
        "static/bot-builder.js"
      ],
      "related": [
        "webui.bots.select",
        "webui.bots.create",
        "webui.bots.instructions"
      ],
      "locales": {
        "en": {
          "title": "Bot ID, name and description",
          "purpose": "Give a bot a stable identifier and understandable purpose.",
          "when": "When preparing or maintaining a specialist assistant for a defined role.",
          "steps": [
            "Enter a valid lowercase bot ID when creating.",
            "Set a clear display name and description in the identity step."
          ],
          "permissions": "Bot visibility, editing rights and permitted tools are checked separately.",
          "limits": "A bot cannot grant itself permissions or make unavailable connections usable.",
          "example": "Name a bot so colleagues know when to use it."
        },
        "nl": {
          "title": "Bot-ID, naam en beschrijving",
          "purpose": "Geef een bot een vaste identificatie en begrijpelijk doel.",
          "when": "Bij het voorbereiden of onderhouden van een specialistische assistent met een duidelijke rol.",
          "steps": [
            "Vul bij aanmaken een geldige bot-ID in kleine letters in.",
            "Stel een duidelijke weergavenaam en beschrijving in bij Identiteit."
          ],
          "permissions": "Zichtbaarheid van bots, bewerkrechten en toegestane tools worden afzonderlijk gecontroleerd.",
          "limits": "Een bot kan zichzelf geen rechten geven of onbeschikbare koppelingen bruikbaar maken.",
          "example": "Geef een bot een naam die collega’s helpt kiezen."
        }
      }
    },
    {
      "id": "webui.bots.instructions",
      "area": "bots",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.bots.instructions"
      ],
      "source_refs": [
        "static/bot-builder.js"
      ],
      "related": [
        "webui.bots.select",
        "webui.bots.create",
        "webui.bots.identity"
      ],
      "locales": {
        "en": {
          "title": "Bot instructions",
          "purpose": "Set the bot’s role, expected output and boundaries.",
          "when": "When preparing or maintaining a specialist assistant for a defined role.",
          "steps": [
            "Open the instructions step or tab.",
            "Write the system instructions and review them before saving."
          ],
          "permissions": "Bot visibility, editing rights and permitted tools are checked separately.",
          "limits": "A bot cannot grant itself permissions or make unavailable connections usable.",
          "example": "Require a review bot to explain each proposed change."
        },
        "nl": {
          "title": "Botinstructies",
          "purpose": "Stel rol, verwachte uitvoer en grenzen van de bot in.",
          "when": "Bij het voorbereiden of onderhouden van een specialistische assistent met een duidelijke rol.",
          "steps": [
            "Open de instructiestap of het instructietabblad.",
            "Schrijf systeeminstructies en controleer ze voordat je opslaat."
          ],
          "permissions": "Zichtbaarheid van bots, bewerkrechten en toegestane tools worden afzonderlijk gecontroleerd.",
          "limits": "Een bot kan zichzelf geen rechten geven of onbeschikbare koppelingen bruikbaar maken.",
          "example": "Laat een beoordelingsbot elke voorgestelde wijziging uitleggen."
        }
      }
    },
    {
      "id": "webui.bots.skills",
      "area": "bots",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.bots.skills"
      ],
      "source_refs": [
        "static/bot-builder.js"
      ],
      "related": [
        "webui.bots.select",
        "webui.bots.create",
        "webui.bots.identity"
      ],
      "locales": {
        "en": {
          "title": "Bot skills",
          "purpose": "Select reusable instructions available to the bot owner.",
          "when": "When preparing or maintaining a specialist assistant for a defined role.",
          "steps": [
            "Open the skill choices in the bot editor.",
            "Filter and select the relevant skills, then save the bot."
          ],
          "permissions": "Bot visibility, editing rights and permitted tools are checked separately.",
          "limits": "A bot cannot grant itself permissions or make unavailable connections usable.",
          "example": "Attach a writing checklist to a document bot."
        },
        "nl": {
          "title": "Botskills",
          "purpose": "Kies herbruikbare instructies die voor de boteigenaar beschikbaar zijn.",
          "when": "Bij het voorbereiden of onderhouden van een specialistische assistent met een duidelijke rol.",
          "steps": [
            "Open de skillkeuzes in de boteditor.",
            "Filter en kies relevante skills en sla de bot op."
          ],
          "permissions": "Zichtbaarheid van bots, bewerkrechten en toegestane tools worden afzonderlijk gecontroleerd.",
          "limits": "Een bot kan zichzelf geen rechten geven of onbeschikbare koppelingen bruikbaar maken.",
          "example": "Koppel een schrijfcontrolelijst aan een documentbot."
        }
      }
    },
    {
      "id": "webui.bots.tools",
      "area": "bots",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.bots.tools"
      ],
      "source_refs": [
        "static/bot-builder.js"
      ],
      "related": [
        "webui.bots.select",
        "webui.bots.create",
        "webui.bots.identity"
      ],
      "locales": {
        "en": {
          "title": "Bot connections and CLI tools",
          "purpose": "Choose permitted connections and tools without exposing their credentials.",
          "when": "When preparing or maintaining a specialist assistant for a defined role.",
          "steps": [
            "Open the tools step or tab.",
            "Select available MCP connections and CLI tools; review unavailable previous selections before saving."
          ],
          "permissions": "Bot visibility, editing rights and permitted tools are checked separately.",
          "limits": "A bot cannot grant itself permissions or make unavailable connections usable.",
          "example": "Limit a bot to the tools needed for its role."
        },
        "nl": {
          "title": "Botkoppelingen en CLI-tools",
          "purpose": "Kies toegestane koppelingen en tools zonder inloggegevens zichtbaar te maken.",
          "when": "Bij het voorbereiden of onderhouden van een specialistische assistent met een duidelijke rol.",
          "steps": [
            "Open de toolstap of het tooltabblad.",
            "Kies beschikbare MCP-koppelingen en CLI-tools; controleer eerder gekozen onbeschikbare opties voor opslaan."
          ],
          "permissions": "Zichtbaarheid van bots, bewerkrechten en toegestane tools worden afzonderlijk gecontroleerd.",
          "limits": "Een bot kan zichzelf geen rechten geven of onbeschikbare koppelingen bruikbaar maken.",
          "example": "Beperk een bot tot de tools die bij de rol passen."
        }
      }
    },
    {
      "id": "webui.bots.memory",
      "area": "bots",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.bots.memory"
      ],
      "source_refs": [
        "static/bot-builder.js"
      ],
      "related": [
        "webui.bots.select",
        "webui.bots.create",
        "webui.bots.identity"
      ],
      "locales": {
        "en": {
          "title": "Shared bot memory",
          "purpose": "Maintain context shared with the users of this bot.",
          "when": "When preparing or maintaining a specialist assistant for a defined role.",
          "steps": [
            "Open the bot’s Memory tab.",
            "Edit bot memory and save the bot; keep personal notes in personal memory."
          ],
          "permissions": "Bot visibility, editing rights and permitted tools are checked separately.",
          "limits": "A bot cannot grant itself permissions or make unavailable connections usable.",
          "example": "Record terminology used by everyone working with the bot."
        },
        "nl": {
          "title": "Gedeeld botgeheugen",
          "purpose": "Beheer context die met gebruikers van deze bot wordt gedeeld.",
          "when": "Bij het voorbereiden of onderhouden van een specialistische assistent met een duidelijke rol.",
          "steps": [
            "Open het tabblad Geheugen van de bot.",
            "Bewerk botgeheugen en sla de bot op; houd persoonlijke notities in persoonlijk geheugen."
          ],
          "permissions": "Zichtbaarheid van bots, bewerkrechten en toegestane tools worden afzonderlijk gecontroleerd.",
          "limits": "Een bot kan zichzelf geen rechten geven of onbeschikbare koppelingen bruikbaar maken.",
          "example": "Leg termen vast die alle botgebruikers hanteren."
        }
      }
    },
    {
      "id": "webui.bots.knowledge",
      "area": "bots",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.bots.knowledge"
      ],
      "source_refs": [
        "static/bot-builder.js",
        "static/bot-knowledge.js"
      ],
      "related": [
        "webui.bots.select",
        "webui.bots.create",
        "webui.bots.identity"
      ],
      "locales": {
        "en": {
          "title": "Bot knowledge files",
          "purpose": "Select files used as shared bot knowledge through the knowledge control.",
          "when": "When preparing or maintaining a specialist assistant for a defined role.",
          "steps": [
            "Open the bot’s knowledge section.",
            "Review the selected files and use Save knowledge separately from Save bot."
          ],
          "permissions": "Bot visibility, editing rights and permitted tools are checked separately.",
          "limits": "A bot cannot grant itself permissions or make unavailable connections usable.",
          "example": "Attach approved reference documents to a specialist bot."
        },
        "nl": {
          "title": "Kennisbestanden van een bot",
          "purpose": "Kies bestanden die via de kennisoptie als gedeelde botkennis dienen.",
          "when": "Bij het voorbereiden of onderhouden van een specialistische assistent met een duidelijke rol.",
          "steps": [
            "Open het kennisgedeelte van de bot.",
            "Controleer de gekozen bestanden en gebruik Kennis opslaan los van Bot opslaan."
          ],
          "permissions": "Zichtbaarheid van bots, bewerkrechten en toegestane tools worden afzonderlijk gecontroleerd.",
          "limits": "Een bot kan zichzelf geen rechten geven of onbeschikbare koppelingen bruikbaar maken.",
          "example": "Koppel goedgekeurde referentiedocumenten aan een specialistische bot."
        }
      }
    },
    {
      "id": "webui.bots.access",
      "area": "bots",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.bots.access"
      ],
      "source_refs": [
        "static/bot-builder.js"
      ],
      "related": [
        "webui.bots.select",
        "webui.bots.create",
        "webui.bots.identity"
      ],
      "locales": {
        "en": {
          "title": "Bot users and groups",
          "purpose": "Define which allowed people and groups may use a bot.",
          "when": "When preparing or maintaining a specialist assistant for a defined role.",
          "steps": [
            "Open the Access tab.",
            "Select permitted users and groups, review the audience and save."
          ],
          "permissions": "Bot visibility, editing rights and permitted tools are checked separately.",
          "limits": "A bot cannot grant itself permissions or make unavailable connections usable.",
          "example": "Make a team bot available to its intended group."
        },
        "nl": {
          "title": "Botgebruikers en groepen",
          "purpose": "Bepaal welke toegestane personen en groepen een bot mogen gebruiken.",
          "when": "Bij het voorbereiden of onderhouden van een specialistische assistent met een duidelijke rol.",
          "steps": [
            "Open het tabblad Toegang.",
            "Kies toegestane gebruikers en groepen, controleer de doelgroep en sla op."
          ],
          "permissions": "Zichtbaarheid van bots, bewerkrechten en toegestane tools worden afzonderlijk gecontroleerd.",
          "limits": "Een bot kan zichzelf geen rechten geven of onbeschikbare koppelingen bruikbaar maken.",
          "example": "Maak een teambot beschikbaar voor de bedoelde groep."
        }
      }
    },
    {
      "id": "webui.bots.appearance",
      "area": "bots",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.bots.appearance",
        "#builderPhoto",
        "#botTitle",
        "#botDescription",
        "#botShape",
        "#botColor",
        "#botCategory",
        "#botAvatarFile"
      ],
      "source_refs": [
        "static/bot-builder.js:81",
        "static/panels.js:7972",
        "static/panels.js:7973",
        "static/panels.js:7974",
        "static/panels.js:7975",
        "static/panels.js:7976",
        "static/panels.js:7977"
      ],
      "related": [
        "webui.bots.select",
        "webui.bots.create",
        "webui.bots.identity"
      ],
      "locales": {
        "en": {
          "title": "Bot photo and appearance",
          "purpose": "Customize the bot’s visible name, photo, icon shape, color and category.",
          "when": "When preparing or maintaining a specialist assistant for a defined role.",
          "steps": [
            "Open bot details or the identity editor.",
            "Choose supported image and appearance values, then save."
          ],
          "permissions": "Bot visibility, editing rights and permitted tools are checked separately.",
          "limits": "A bot cannot grant itself permissions or make unavailable connections usable.",
          "example": "Give a specialist a recognizable team identity."
        },
        "nl": {
          "title": "Botfoto en weergave",
          "purpose": "Pas zichtbare naam, foto, pictogramvorm, kleur en categorie van de bot aan.",
          "when": "Bij het voorbereiden of onderhouden van een specialistische assistent met een duidelijke rol.",
          "steps": [
            "Open botdetails of de identiteitseditor.",
            "Kies een ondersteunde afbeelding en weergavewaarden en sla op."
          ],
          "permissions": "Zichtbaarheid van bots, bewerkrechten en toegestane tools worden afzonderlijk gecontroleerd.",
          "limits": "Een bot kan zichzelf geen rechten geven of onbeschikbare koppelingen bruikbaar maken.",
          "example": "Geef een specialist een herkenbare teamidentiteit."
        }
      }
    },
    {
      "id": "webui.bots.manage",
      "area": "bots",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.bots.manage",
        "#btnDeleteProfileDetail",
        "#btnCancelProfileDetail",
        "#btnSaveProfileDetail",
        "#builderTab"
      ],
      "source_refs": [
        "static/bot-builder.js:106",
        "static/index.html:969",
        "static/index.html:970",
        "static/index.html:971",
        "static/panels.js:7961",
        "static/panels.js:7962",
        "static/panels.js:7963",
        "static/panels.js:7964",
        "static/panels.js:7965",
        "static/panels.js:7980"
      ],
      "related": [
        "webui.bots.select",
        "webui.bots.create",
        "webui.bots.identity"
      ],
      "locales": {
        "en": {
          "title": "Edit or delete a bot",
          "purpose": "Maintain bot configuration or remove an obsolete bot.",
          "when": "When preparing or maintaining a specialist assistant for a defined role.",
          "steps": [
            "Open Configure and choose the relevant tab.",
            "Save or cancel changes; verify the bot before confirming deletion."
          ],
          "permissions": "Bot visibility, editing rights and permitted tools are checked separately.",
          "limits": "A bot cannot grant itself permissions or make unavailable connections usable.",
          "example": "Update a bot’s instructions after a process change."
        },
        "nl": {
          "title": "Een bot bewerken of verwijderen",
          "purpose": "Beheer botconfiguratie of verwijder een verouderde bot.",
          "when": "Bij het voorbereiden of onderhouden van een specialistische assistent met een duidelijke rol.",
          "steps": [
            "Open Configureren en kies het juiste tabblad.",
            "Sla wijzigingen op of annuleer; controleer de bot voordat je verwijderen bevestigt."
          ],
          "permissions": "Zichtbaarheid van bots, bewerkrechten en toegestane tools worden afzonderlijk gecontroleerd.",
          "limits": "Een bot kan zichzelf geen rechten geven of onbeschikbare koppelingen bruikbaar maken.",
          "example": "Werk botinstructies bij na een proceswijziging."
        }
      }
    },
    {
      "id": "webui.projects.create",
      "area": "projects",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.projects.create",
        "#projNewName",
        "#projNewCategory",
        "#projCreateButton"
      ],
      "source_refs": [
        "static/projects.js:95"
      ],
      "related": [
        "webui.projects.team",
        "webui.projects.chat",
        "webui.projects.files"
      ],
      "locales": {
        "en": {
          "title": "Create a project",
          "purpose": "Group related work under a named project and category.",
          "when": "When conversations, documents and colleagues belong to the same body of work.",
          "steps": [
            "Open Projects and choose the creation control.",
            "Enter a name and category, then create the project."
          ],
          "permissions": "Project membership and workspace permissions govern access.",
          "limits": "Archiving or changing membership can affect collaboration. Check the selected project first.",
          "example": "Create a dedicated space for a new engagement."
        },
        "nl": {
          "title": "Een project maken",
          "purpose": "Groepeer samenhangend werk onder een projectnaam en categorie.",
          "when": "Wanneer gesprekken, documenten en collega’s bij hetzelfde werk horen.",
          "steps": [
            "Open Projecten en kies de aanmaakoptie.",
            "Vul naam en categorie in en maak het project."
          ],
          "permissions": "Projectlidmaatschap en werkruimterechten bepalen de toegang.",
          "limits": "Archiveren of lidmaatschap wijzigen kan samenwerking beïnvloeden. Controleer eerst het gekozen project.",
          "example": "Maak een eigen plek voor een nieuwe opdracht."
        }
      }
    },
    {
      "id": "webui.projects.team",
      "area": "projects",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.projects.team",
        "#projPeopleSearch",
        "#projCategory",
        "#projSaveTeam"
      ],
      "source_refs": [
        "static/projects.js:421",
        "static/projects.js:424",
        "static/projects.js:425"
      ],
      "related": [
        "webui.projects.create",
        "webui.projects.chat",
        "webui.projects.files"
      ],
      "locales": {
        "en": {
          "title": "Project team and category",
          "purpose": "Manage the people and category associated with a project.",
          "when": "When conversations, documents and colleagues belong to the same body of work.",
          "steps": [
            "Open project details and search for people.",
            "Review membership and category, then save the team."
          ],
          "permissions": "Project membership and workspace permissions govern access.",
          "limits": "Archiving or changing membership can affect collaboration. Check the selected project first.",
          "example": "Add a permitted colleague to project collaboration."
        },
        "nl": {
          "title": "Projectteam en categorie",
          "purpose": "Beheer de personen en categorie van een project.",
          "when": "Wanneer gesprekken, documenten en collega’s bij hetzelfde werk horen.",
          "steps": [
            "Open projectdetails en zoek personen.",
            "Controleer lidmaatschap en categorie en sla het team op."
          ],
          "permissions": "Projectlidmaatschap en werkruimterechten bepalen de toegang.",
          "limits": "Archiveren of lidmaatschap wijzigen kan samenwerking beïnvloeden. Controleer eerst het gekozen project.",
          "example": "Voeg een toegestane collega toe aan het project."
        }
      }
    },
    {
      "id": "webui.projects.chat",
      "area": "projects",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.projects.chat",
        "#projStartChat"
      ],
      "source_refs": [
        "static/projects.js:395"
      ],
      "related": [
        "webui.projects.create",
        "webui.projects.team",
        "webui.projects.files"
      ],
      "locales": {
        "en": {
          "title": "Start a project conversation",
          "purpose": "Start a conversation associated with the selected project.",
          "when": "When conversations, documents and colleagues belong to the same body of work.",
          "steps": [
            "Open the intended project and choose Start chat.",
            "Check project, workspace and bot before sending."
          ],
          "permissions": "Project membership and workspace permissions govern access.",
          "limits": "Archiving or changing membership can affect collaboration. Check the selected project first.",
          "example": "Discuss the next deliverable in its project context."
        },
        "nl": {
          "title": "Een projectgesprek beginnen",
          "purpose": "Begin een gesprek dat aan het gekozen project is gekoppeld.",
          "when": "Wanneer gesprekken, documenten en collega’s bij hetzelfde werk horen.",
          "steps": [
            "Open het bedoelde project en kies Chat starten.",
            "Controleer project, werkruimte en bot voordat je verstuurt."
          ],
          "permissions": "Projectlidmaatschap en werkruimterechten bepalen de toegang.",
          "limits": "Archiveren of lidmaatschap wijzigen kan samenwerking beïnvloeden. Controleer eerst het gekozen project.",
          "example": "Bespreek het volgende resultaat binnen de projectcontext."
        }
      }
    },
    {
      "id": "webui.projects.files",
      "area": "projects",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.projects.files",
        "#projUpload"
      ],
      "source_refs": [
        "static/projects.js:427"
      ],
      "related": [
        "webui.projects.create",
        "webui.projects.team",
        "webui.projects.chat"
      ],
      "locales": {
        "en": {
          "title": "Project uploads",
          "purpose": "Add files through the selected project’s upload flow.",
          "when": "When conversations, documents and colleagues belong to the same body of work.",
          "steps": [
            "Open the project and choose Upload.",
            "Check file names and destination before completing the upload."
          ],
          "permissions": "Project membership and workspace permissions govern access.",
          "limits": "Archiving or changing membership can affect collaboration. Check the selected project first.",
          "example": "Add the project brief to the shared work."
        },
        "nl": {
          "title": "Projectbestanden uploaden",
          "purpose": "Voeg bestanden toe via de uploadfunctie van het gekozen project.",
          "when": "Wanneer gesprekken, documenten en collega’s bij hetzelfde werk horen.",
          "steps": [
            "Open het project en kies Uploaden.",
            "Controleer bestandsnamen en bestemming voordat je uploadt."
          ],
          "permissions": "Projectlidmaatschap en werkruimterechten bepalen de toegang.",
          "limits": "Archiveren of lidmaatschap wijzigen kan samenwerking beïnvloeden. Controleer eerst het gekozen project.",
          "example": "Voeg de projectbriefing toe aan het gedeelde werk."
        }
      }
    },
    {
      "id": "webui.projects.archive",
      "area": "projects",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.projects.archive",
        "#projArchiveTeam"
      ],
      "source_refs": [
        "static/index.html:313",
        "static/index.html:930",
        "static/projects.js:425"
      ],
      "related": [
        "webui.projects.create",
        "webui.projects.team",
        "webui.projects.chat"
      ],
      "locales": {
        "en": {
          "title": "Archive and refresh projects",
          "purpose": "Retire a project from active work and reload project information.",
          "when": "When conversations, documents and colleagues belong to the same body of work.",
          "steps": [
            "Choose Archive on the intended project and review the confirmation.",
            "Refresh the project list to inspect its current state."
          ],
          "permissions": "Project membership and workspace permissions govern access.",
          "limits": "Archiving or changing membership can affect collaboration. Check the selected project first.",
          "example": "Archive a completed project after reviewing its contents."
        },
        "nl": {
          "title": "Projecten archiveren en verversen",
          "purpose": "Haal een project uit actief werk en laad projectinformatie opnieuw.",
          "when": "Wanneer gesprekken, documenten en collega’s bij hetzelfde werk horen.",
          "steps": [
            "Kies Archiveren bij het bedoelde project en controleer de bevestiging.",
            "Ververs de projectlijst om de actuele toestand te bekijken."
          ],
          "permissions": "Projectlidmaatschap en werkruimterechten bepalen de toegang.",
          "limits": "Archiveren of lidmaatschap wijzigen kan samenwerking beïnvloeden. Controleer eerst het gekozen project.",
          "example": "Archiveer een afgerond project na controle van de inhoud."
        }
      }
    },
    {
      "id": "webui.connections.providers",
      "area": "connections",
      "status": "conditional",
      "conditions": [
        "connection-configuration",
        "integration-permissions"
      ],
      "anchors": [
        "?help_feature=webui.connections.providers",
        "#integrationsRefreshBtn",
        "#intgSearch"
      ],
      "source_refs": [
        "static/index.html:1067",
        "static/index.html:1095",
        "static/index.html:388"
      ],
      "related": [
        "webui.connections.channel",
        "webui.connections.publish",
        "webui.connections.people"
      ],
      "locales": {
        "en": {
          "title": "Find and connect a provider",
          "purpose": "Browse available integrations and start the supported connection workflow.",
          "when": "When a task needs an approved external account, channel or tool connection.",
          "steps": [
            "Open Connections and search for a provider.",
            "Review requested permissions before completing the offered connection flow.",
            "Refresh to inspect the resulting status."
          ],
          "permissions": "Provider setup, channel management and account linking may require different rights.",
          "limits": "Connecting an account can expose its permitted data and actions to tools. Never paste credentials into chat or help search.",
          "example": "Connect an approved document source for your work."
        },
        "nl": {
          "title": "Een provider vinden en koppelen",
          "purpose": "Bekijk beschikbare integraties en start de ondersteunde koppeling.",
          "when": "Wanneer een taak een goedgekeurd extern account, kanaal of toolkoppeling nodig heeft.",
          "steps": [
            "Open Koppelingen en zoek een provider.",
            "Controleer gevraagde rechten voordat je de aangeboden koppelprocedure afrondt.",
            "Ververs om de resulterende status te bekijken."
          ],
          "permissions": "Providerinstellingen, kanaalbeheer en accountkoppeling kunnen verschillende rechten vereisen.",
          "limits": "Een account koppelen kan de toegestane gegevens en acties beschikbaar maken voor tools. Plak nooit inloggegevens in chat of de hulpzoekfunctie.",
          "example": "Koppel een goedgekeurde documentbron voor je werk."
        }
      }
    },
    {
      "id": "webui.connections.channel",
      "area": "connections",
      "status": "conditional",
      "conditions": [
        "connection-configuration",
        "integration-permissions"
      ],
      "anchors": [
        "?help_feature=webui.connections.channel"
      ],
      "source_refs": [
        "static/index.html:1082",
        "static/integrations.js:924"
      ],
      "related": [
        "webui.connections.providers",
        "webui.connections.publish",
        "webui.connections.people"
      ],
      "locales": {
        "en": {
          "title": "Configure a messaging channel",
          "purpose": "Set up an available messaging channel and inspect its gateway state.",
          "when": "When a task needs an approved external account, channel or tool connection.",
          "steps": [
            "Open the channel’s Configure action.",
            "Review the required settings and credentials through the protected setup form.",
            "Restart the gateway only when the interface requires it."
          ],
          "permissions": "Provider setup, channel management and account linking may require different rights.",
          "limits": "Connecting an account can expose its permitted data and actions to tools. Never paste credentials into chat or help search.",
          "example": "Prepare a permitted team messaging channel."
        },
        "nl": {
          "title": "Een berichtenkanaal instellen",
          "purpose": "Stel een beschikbaar berichtenkanaal in en bekijk de gatewaystatus.",
          "when": "Wanneer een taak een goedgekeurd extern account, kanaal of toolkoppeling nodig heeft.",
          "steps": [
            "Open Configureren bij het kanaal.",
            "Controleer instellingen en inloggegevens via het beschermde formulier.",
            "Herstart de gateway alleen wanneer de interface dit vereist."
          ],
          "permissions": "Providerinstellingen, kanaalbeheer en accountkoppeling kunnen verschillende rechten vereisen.",
          "limits": "Een account koppelen kan de toegestane gegevens en acties beschikbaar maken voor tools. Plak nooit inloggegevens in chat of de hulpzoekfunctie.",
          "example": "Bereid een toegestaan teamberichtenkanaal voor."
        }
      }
    },
    {
      "id": "webui.connections.publish",
      "area": "connections",
      "status": "conditional",
      "conditions": [
        "connection-configuration",
        "integration-permissions"
      ],
      "anchors": [
        "?help_feature=webui.connections.publish"
      ],
      "source_refs": [
        "static/integrations.js:911",
        "static/integrations.js:913",
        "static/integrations.js:925"
      ],
      "related": [
        "webui.connections.providers",
        "webui.connections.channel",
        "webui.connections.people"
      ],
      "locales": {
        "en": {
          "title": "Publish or disable a channel",
          "purpose": "Control the offered channel access link and availability.",
          "when": "When a task needs an approved external account, channel or tool connection.",
          "steps": [
            "Review the channel configuration before Publish.",
            "Copy the offered link for its intended audience; Disable when the channel should stop being available."
          ],
          "permissions": "Provider setup, channel management and account linking may require different rights.",
          "limits": "Connecting an account can expose its permitted data and actions to tools. Never paste credentials into chat or help search.",
          "example": "Withdraw an obsolete channel invitation."
        },
        "nl": {
          "title": "Een kanaal publiceren of uitschakelen",
          "purpose": "Bedien de aangeboden kanaaltoegangslink en beschikbaarheid.",
          "when": "Wanneer een taak een goedgekeurd extern account, kanaal of toolkoppeling nodig heeft.",
          "steps": [
            "Controleer kanaalinstellingen voordat je Publiceren kiest.",
            "Kopieer de aangeboden link voor de bedoelde doelgroep; kies Uitschakelen wanneer het kanaal niet beschikbaar moet blijven."
          ],
          "permissions": "Providerinstellingen, kanaalbeheer en accountkoppeling kunnen verschillende rechten vereisen.",
          "limits": "Een account koppelen kan de toegestane gegevens en acties beschikbaar maken voor tools. Plak nooit inloggegevens in chat of de hulpzoekfunctie.",
          "example": "Trek een verouderde kanaaluitnodiging in."
        }
      }
    },
    {
      "id": "webui.connections.people",
      "area": "connections",
      "status": "conditional",
      "conditions": [
        "connection-configuration",
        "integration-permissions"
      ],
      "anchors": [
        "?help_feature=webui.connections.people",
        "#chAddPlatform",
        "#chAddUserId"
      ],
      "source_refs": [
        "static/integrations.js:1036",
        "static/integrations.js:1066",
        "static/integrations.js:1072",
        "static/integrations.js:1073",
        "static/integrations.js:1075"
      ],
      "related": [
        "webui.connections.providers",
        "webui.connections.channel",
        "webui.connections.publish"
      ],
      "locales": {
        "en": {
          "title": "Approve and manage channel people",
          "purpose": "Manage external platform identities allowed to use a channel.",
          "when": "When a task needs an approved external account, channel or tool connection.",
          "steps": [
            "Review pending requests before approving.",
            "To add a person, select the platform and enter the verified platform user ID.",
            "Remove access when no longer needed."
          ],
          "permissions": "Provider setup, channel management and account linking may require different rights.",
          "limits": "Connecting an account can expose its permitted data and actions to tools. Never paste credentials into chat or help search.",
          "example": "Approve a verified colleague’s channel identity."
        },
        "nl": {
          "title": "Kanaalgebruikers goedkeuren en beheren",
          "purpose": "Beheer externe platformidentiteiten die een kanaal mogen gebruiken.",
          "when": "Wanneer een taak een goedgekeurd extern account, kanaal of toolkoppeling nodig heeft.",
          "steps": [
            "Controleer wachtende verzoeken voordat je goedkeurt.",
            "Kies voor toevoegen het platform en vul de gecontroleerde platformgebruikers-ID in.",
            "Verwijder toegang wanneer die niet meer nodig is."
          ],
          "permissions": "Providerinstellingen, kanaalbeheer en accountkoppeling kunnen verschillende rechten vereisen.",
          "limits": "Een account koppelen kan de toegestane gegevens en acties beschikbaar maken voor tools. Plak nooit inloggegevens in chat of de hulpzoekfunctie.",
          "example": "Keur de gecontroleerde kanaalidentiteit van een collega goed."
        }
      }
    },
    {
      "id": "webui.connections.personal",
      "area": "connections",
      "status": "conditional",
      "conditions": [
        "connection-configuration",
        "integration-permissions"
      ],
      "anchors": [
        "?help_feature=webui.connections.personal"
      ],
      "source_refs": [
        "static/integrations.js:1157",
        "static/integrations.js:1158"
      ],
      "related": [
        "webui.connections.providers",
        "webui.connections.channel",
        "webui.connections.publish"
      ],
      "locales": {
        "en": {
          "title": "Personal channel bot",
          "purpose": "Save or remove your permitted personal bot configuration.",
          "when": "When a task needs an approved external account, channel or tool connection.",
          "steps": [
            "Open the personal bot controls.",
            "Review the configuration and choose Save or Remove as appropriate."
          ],
          "permissions": "Provider setup, channel management and account linking may require different rights.",
          "limits": "Connecting an account can expose its permitted data and actions to tools. Never paste credentials into chat or help search.",
          "example": "Maintain your own supported messaging bot connection."
        },
        "nl": {
          "title": "Persoonlijke kanaalbot",
          "purpose": "Bewaar of verwijder je toegestane persoonlijke botconfiguratie.",
          "when": "Wanneer een taak een goedgekeurd extern account, kanaal of toolkoppeling nodig heeft.",
          "steps": [
            "Open de opties voor je persoonlijke bot.",
            "Controleer de configuratie en kies Opslaan of Verwijderen."
          ],
          "permissions": "Providerinstellingen, kanaalbeheer en accountkoppeling kunnen verschillende rechten vereisen.",
          "limits": "Een account koppelen kan de toegestane gegevens en acties beschikbaar maken voor tools. Plak nooit inloggegevens in chat of de hulpzoekfunctie.",
          "example": "Beheer je eigen ondersteunde berichtenbotkoppeling."
        }
      }
    },
    {
      "id": "webui.connections.link",
      "area": "connections",
      "status": "conditional",
      "conditions": [
        "connection-configuration",
        "integration-permissions"
      ],
      "anchors": [
        "?help_feature=webui.connections.link",
        "#chMinePlatform",
        "#chMineOtherId"
      ],
      "source_refs": [
        "static/integrations.js:1160",
        "static/integrations.js:1164",
        "static/integrations.js:1167",
        "static/integrations.js:1169"
      ],
      "related": [
        "webui.connections.providers",
        "webui.connections.channel",
        "webui.connections.publish"
      ],
      "locales": {
        "en": {
          "title": "Link your platform identity",
          "purpose": "Associate your verified messaging identity with your account.",
          "when": "When a task needs an approved external account, channel or tool connection.",
          "steps": [
            "Choose Link me or select the platform and verified ID.",
            "Complete the offered verification; use Unlink to remove the association."
          ],
          "permissions": "Provider setup, channel management and account linking may require different rights.",
          "limits": "Connecting an account can expose its permitted data and actions to tools. Never paste credentials into chat or help search.",
          "example": "Connect your own channel identity to the correct account."
        },
        "nl": {
          "title": "Je platformidentiteit koppelen",
          "purpose": "Koppel je gecontroleerde berichtenidentiteit aan je account.",
          "when": "Wanneer een taak een goedgekeurd extern account, kanaal of toolkoppeling nodig heeft.",
          "steps": [
            "Kies Mij koppelen of selecteer platform en gecontroleerde ID.",
            "Rond de aangeboden controle af; gebruik Ontkoppelen om de koppeling te verwijderen."
          ],
          "permissions": "Providerinstellingen, kanaalbeheer en accountkoppeling kunnen verschillende rechten vereisen.",
          "limits": "Een account koppelen kan de toegestane gegevens en acties beschikbaar maken voor tools. Plak nooit inloggegevens in chat of de hulpzoekfunctie.",
          "example": "Verbind je eigen kanaalidentiteit met het juiste account."
        }
      }
    },
    {
      "id": "webui.connections.mcp",
      "area": "connections",
      "status": "conditional",
      "conditions": [
        "connection-configuration",
        "integration-permissions"
      ],
      "anchors": [
        "?help_feature=webui.connections.mcp"
      ],
      "source_refs": [
        "static/panels.js:14327"
      ],
      "related": [
        "webui.connections.providers",
        "webui.connections.channel",
        "webui.connections.publish"
      ],
      "locales": {
        "en": {
          "title": "MCP server inventory and enablement",
          "purpose": "Inspect configured MCP servers and the enablement control offered to your role.",
          "when": "When a task needs an approved external account, channel or tool connection.",
          "steps": [
            "Open Settings, System and inspect the server list.",
            "Use an available toggle only with the required rights; follow any restart instruction."
          ],
          "permissions": "Provider setup, channel management and account linking may require different rights.",
          "limits": "Connecting an account can expose its permitted data and actions to tools. Never paste credentials into chat or help search.",
          "example": "Check whether an approved connection is enabled."
        },
        "nl": {
          "title": "MCP-serveroverzicht en inschakeling",
          "purpose": "Bekijk ingestelde MCP-servers en de inschakeloptie die je rol krijgt.",
          "when": "Wanneer een taak een goedgekeurd extern account, kanaal of toolkoppeling nodig heeft.",
          "steps": [
            "Open Instellingen, Systeem en bekijk de serverlijst.",
            "Gebruik een beschikbare schakelaar alleen met de nodige rechten; volg eventuele herstartinstructies."
          ],
          "permissions": "Providerinstellingen, kanaalbeheer en accountkoppeling kunnen verschillende rechten vereisen.",
          "limits": "Een account koppelen kan de toegestane gegevens en acties beschikbaar maken voor tools. Plak nooit inloggegevens in chat of de hulpzoekfunctie.",
          "example": "Controleer of een goedgekeurde koppeling actief is."
        }
      }
    },
    {
      "id": "webui.connections.catalog",
      "area": "connections",
      "status": "conditional",
      "conditions": [
        "connection-configuration",
        "integration-permissions"
      ],
      "anchors": [
        "?help_feature=webui.connections.catalog",
        "#mcpToolSearch"
      ],
      "source_refs": [
        "static/index.html:1873",
        "static/panels.js:14377",
        "static/panels.js:14392",
        "static/panels.js:14394"
      ],
      "related": [
        "webui.connections.providers",
        "webui.connections.channel",
        "webui.connections.publish"
      ],
      "locales": {
        "en": {
          "title": "Search known MCP tools",
          "purpose": "Search the already-known active tool inventory without probing new servers.",
          "when": "When a task needs an approved external account, channel or tool connection.",
          "steps": [
            "Search by tool, server or description.",
            "Adjust page size or move through result pages as needed."
          ],
          "permissions": "Provider setup, channel management and account linking may require different rights.",
          "limits": "Connecting an account can expose its permitted data and actions to tools. Never paste credentials into chat or help search.",
          "example": "Find which available connection exposes a required action."
        },
        "nl": {
          "title": "Bekende MCP-tools zoeken",
          "purpose": "Zoek in de al bekende actieve toolinventaris zonder nieuwe servers te onderzoeken.",
          "when": "Wanneer een taak een goedgekeurd extern account, kanaal of toolkoppeling nodig heeft.",
          "steps": [
            "Zoek op tool, server of beschrijving.",
            "Pas paginagrootte aan of blader door resultaten."
          ],
          "permissions": "Providerinstellingen, kanaalbeheer en accountkoppeling kunnen verschillende rechten vereisen.",
          "limits": "Een account koppelen kan de toegestane gegevens en acties beschikbaar maken voor tools. Plak nooit inloggegevens in chat of de hulpzoekfunctie.",
          "example": "Vind welke beschikbare koppeling een benodigde actie biedt."
        }
      }
    },
    {
      "id": "webui.governance.once",
      "area": "governance",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.governance.once",
        "#approvalBtnOnce"
      ],
      "source_refs": [
        "static/index.html:542"
      ],
      "related": [
        "webui.governance.session",
        "webui.governance.always",
        "webui.governance.deny"
      ],
      "locales": {
        "en": {
          "title": "Approve a command once",
          "purpose": "Allow only the currently requested command approval.",
          "when": "When access or approval scope needs to be inspected before an action proceeds.",
          "steps": [
            "Read the exact command and context.",
            "Choose Allow once if the action is appropriate."
          ],
          "permissions": "Management actions require the specific governance permission. A preview does not grant access.",
          "limits": "Approval is scoped to the requested action. Do not approve commands you do not understand.",
          "example": "Approve one reviewed operation without creating a lasting rule."
        },
        "nl": {
          "title": "Een opdracht eenmalig goedkeuren",
          "purpose": "Sta alleen de huidige gevraagde opdrachtgoedkeuring toe.",
          "when": "Wanneer toegang of goedkeuringsscope moet worden gecontroleerd voordat een actie doorgaat.",
          "steps": [
            "Lees de exacte opdracht en context.",
            "Kies Eenmalig toestaan als de actie passend is."
          ],
          "permissions": "Beheeracties vereisen de specifieke beleidsrechten. Een voorbeeld geeft geen toegang.",
          "limits": "Goedkeuring geldt binnen de scope van de gevraagde actie. Keur geen opdrachten goed die je niet begrijpt.",
          "example": "Keur één gecontroleerde handeling goed zonder blijvende regel."
        }
      }
    },
    {
      "id": "webui.governance.session",
      "area": "governance",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.governance.session",
        "#approvalBtnSession"
      ],
      "source_refs": [
        "static/index.html:547"
      ],
      "related": [
        "webui.governance.once",
        "webui.governance.always",
        "webui.governance.deny"
      ],
      "locales": {
        "en": {
          "title": "Approve for this session",
          "purpose": "Use the offered session-scoped approval for the shown command scope.",
          "when": "When access or approval scope needs to be inspected before an action proceeds.",
          "steps": [
            "Review what the session approval covers.",
            "Choose Allow for this session only when repeat actions in this conversation are acceptable."
          ],
          "permissions": "Management actions require the specific governance permission. A preview does not grant access.",
          "limits": "Approval is scoped to the requested action. Do not approve commands you do not understand.",
          "example": "Permit a reviewed repetitive operation within the current session."
        },
        "nl": {
          "title": "Toestaan voor dit gesprek",
          "purpose": "Gebruik de aangeboden gespreksgebonden goedkeuring voor de getoonde opdrachtscope.",
          "when": "Wanneer toegang of goedkeuringsscope moet worden gecontroleerd voordat een actie doorgaat.",
          "steps": [
            "Controleer wat de gespreksgoedkeuring omvat.",
            "Kies Toestaan voor dit gesprek alleen als herhaling in dit gesprek acceptabel is."
          ],
          "permissions": "Beheeracties vereisen de specifieke beleidsrechten. Een voorbeeld geeft geen toegang.",
          "limits": "Goedkeuring geldt binnen de scope van de gevraagde actie. Keur geen opdrachten goed die je niet begrijpt.",
          "example": "Sta een gecontroleerde herhaalde handeling in het huidige gesprek toe."
        }
      }
    },
    {
      "id": "webui.governance.always",
      "area": "governance",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.governance.always",
        "#approvalBtnAlways"
      ],
      "source_refs": [
        "static/index.html:551"
      ],
      "related": [
        "webui.governance.once",
        "webui.governance.session",
        "webui.governance.deny"
      ],
      "locales": {
        "en": {
          "title": "Persistent command approval",
          "purpose": "Create an allowed command pattern when policy permits persistent approval.",
          "when": "When access or approval scope needs to be inspected before an action proceeds.",
          "steps": [
            "Inspect the exact command pattern and its breadth.",
            "Choose Always allow only when future matching operations should also be allowed."
          ],
          "permissions": "Management actions require the specific governance permission. A preview does not grant access.",
          "limits": "Approval is scoped to the requested action. Do not approve commands you do not understand.",
          "example": "Approve a narrowly scoped routine command pattern."
        },
        "nl": {
          "title": "Blijvende opdrachtgoedkeuring",
          "purpose": "Maak een toegestaan opdrachtpatroon wanneer het beleid blijvende goedkeuring toestaat.",
          "when": "Wanneer toegang of goedkeuringsscope moet worden gecontroleerd voordat een actie doorgaat.",
          "steps": [
            "Bekijk het exacte opdrachtpatroon en de reikwijdte.",
            "Kies Altijd toestaan alleen als toekomstige overeenkomende handelingen ook mogen."
          ],
          "permissions": "Beheeracties vereisen de specifieke beleidsrechten. Een voorbeeld geeft geen toegang.",
          "limits": "Goedkeuring geldt binnen de scope van de gevraagde actie. Keur geen opdrachten goed die je niet begrijpt.",
          "example": "Keur een nauw afgebakend patroon voor routineopdrachten goed."
        }
      }
    },
    {
      "id": "webui.governance.deny",
      "area": "governance",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.governance.deny",
        "#approvalCollapse",
        "#approvalBtnDeny"
      ],
      "source_refs": [
        "static/index.html:535",
        "static/index.html:536",
        "static/index.html:555"
      ],
      "related": [
        "webui.governance.once",
        "webui.governance.session",
        "webui.governance.always"
      ],
      "locales": {
        "en": {
          "title": "Deny or dismiss an approval",
          "purpose": "Refuse an operation or collapse its display without silently approving it.",
          "when": "When access or approval scope needs to be inspected before an action proceeds.",
          "steps": [
            "Choose Deny to refuse the requested operation.",
            "Collapse or dismiss the card only to manage the display; inspect pending approvals separately."
          ],
          "permissions": "Management actions require the specific governance permission. A preview does not grant access.",
          "limits": "Approval is scoped to the requested action. Do not approve commands you do not understand.",
          "example": "Refuse a command that targets the wrong directory."
        },
        "nl": {
          "title": "Een goedkeuring weigeren of sluiten",
          "purpose": "Weiger een handeling of klap de weergave dicht zonder deze stilzwijgend goed te keuren.",
          "when": "Wanneer toegang of goedkeuringsscope moet worden gecontroleerd voordat een actie doorgaat.",
          "steps": [
            "Kies Weigeren om de gevraagde handeling af te wijzen.",
            "Klap de kaart dicht of sluit deze alleen voor de weergave; controleer wachtende goedkeuringen afzonderlijk."
          ],
          "permissions": "Beheeracties vereisen de specifieke beleidsrechten. Een voorbeeld geeft geen toegang.",
          "limits": "Goedkeuring geldt binnen de scope van de gevraagde actie. Keur geen opdrachten goed die je niet begrijpt.",
          "example": "Weiger een opdracht die de verkeerde map raakt."
        }
      }
    },
    {
      "id": "webui.governance.skip",
      "area": "governance",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.governance.skip",
        "#approvalSkipAll",
        "#yoloPill"
      ],
      "source_refs": [
        "static/commands.js",
        "static/index.html:559",
        "static/index.html:677"
      ],
      "related": [
        "webui.governance.once",
        "webui.governance.session",
        "webui.governance.always"
      ],
      "locales": {
        "en": {
          "title": "Skip approval prompts and YOLO mode",
          "purpose": "Use an offered reduced-prompt mode subject to the installation’s policy.",
          "when": "When access or approval scope needs to be inspected before an action proceeds.",
          "steps": [
            "Read the scope and warning before using Skip all or YOLO.",
            "Return to the normal approval mode when the scoped work is complete.",
            "Composer shortcut: /yolo. Review any required arguments in the command suggestions."
          ],
          "permissions": "Management actions require the specific governance permission. A preview does not grant access.",
          "limits": "Approval is scoped to the requested action. Do not approve commands you do not understand.",
          "example": "Recognize that fewer prompts do not mean broader granted permissions."
        },
        "nl": {
          "title": "Goedkeuringsvragen overslaan en YOLO-modus",
          "purpose": "Gebruik een aangeboden modus met minder vragen binnen het installatiebeleid.",
          "when": "Wanneer toegang of goedkeuringsscope moet worden gecontroleerd voordat een actie doorgaat.",
          "steps": [
            "Lees scope en waarschuwing voordat je Alles overslaan of YOLO gebruikt.",
            "Keer terug naar normale goedkeuring nadat het afgebakende werk gereed is.",
            "Snelopdracht in het berichtveld: /yolo. Controleer eventuele argumenten in de opdrachtsuggesties."
          ],
          "permissions": "Beheeracties vereisen de specifieke beleidsrechten. Een voorbeeld geeft geen toegang.",
          "limits": "Goedkeuring geldt binnen de scope van de gevraagde actie. Keur geen opdrachten goed die je niet begrijpt.",
          "example": "Herken dat minder vragen geen ruimere verleende rechten betekenen."
        }
      }
    },
    {
      "id": "webui.governance.clarify",
      "area": "governance",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.governance.clarify",
        "#clarifyCollapse",
        "#clarifyInput",
        "#clarifySubmit"
      ],
      "source_refs": [
        "static/index.html:572",
        "static/index.html:577",
        "static/index.html:578",
        "static/messages.js:8376",
        "static/messages.js:8381",
        "static/messages.js:8382"
      ],
      "related": [
        "webui.governance.once",
        "webui.governance.session",
        "webui.governance.always"
      ],
      "locales": {
        "en": {
          "title": "Answer a clarification",
          "purpose": "Provide missing information requested by the running agent.",
          "when": "When access or approval scope needs to be inspected before an action proceeds.",
          "steps": [
            "Read the clarification question.",
            "Enter the needed detail and choose Send; collapse the card if you need more space."
          ],
          "permissions": "Management actions require the specific governance permission. A preview does not grant access.",
          "limits": "Approval is scoped to the requested action. Do not approve commands you do not understand.",
          "example": "Specify which of two documents should be used."
        },
        "nl": {
          "title": "Een verduidelijkingsvraag beantwoorden",
          "purpose": "Geef ontbrekende informatie waar de actieve agent om vraagt.",
          "when": "Wanneer toegang of goedkeuringsscope moet worden gecontroleerd voordat een actie doorgaat.",
          "steps": [
            "Lees de verduidelijkingsvraag.",
            "Vul het benodigde detail in en kies Versturen; klap de kaart dicht als je meer ruimte nodig hebt."
          ],
          "permissions": "Beheeracties vereisen de specifieke beleidsrechten. Een voorbeeld geeft geen toegang.",
          "limits": "Goedkeuring geldt binnen de scope van de gevraagde actie. Keur geen opdrachten goed die je niet begrijpt.",
          "example": "Geef aan welk van twee documenten gebruikt moet worden."
        }
      }
    },
    {
      "id": "webui.governance.requests",
      "area": "governance",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.governance.requests",
        "#btnMyApprovalsRefresh",
        "#btnAccessRequestsRefresh"
      ],
      "source_refs": [
        "static/index.html:1052",
        "static/index.html:1765"
      ],
      "related": [
        "webui.governance.once",
        "webui.governance.session",
        "webui.governance.always"
      ],
      "locales": {
        "en": {
          "title": "Your approvals and access requests",
          "purpose": "Review the approval and access requests visible to your account.",
          "when": "When access or approval scope needs to be inspected before an action proceeds.",
          "steps": [
            "Open the relevant approvals or access request section.",
            "Refresh, inspect each request and use only the decision actions permitted to your role."
          ],
          "permissions": "Management actions require the specific governance permission. A preview does not grant access.",
          "limits": "Approval is scoped to the requested action. Do not approve commands you do not understand.",
          "example": "Check whether a requested action is waiting for review."
        },
        "nl": {
          "title": "Je goedkeuringen en toegangsverzoeken",
          "purpose": "Bekijk goedkeuringen en toegangsverzoeken die voor jouw account zichtbaar zijn.",
          "when": "Wanneer toegang of goedkeuringsscope moet worden gecontroleerd voordat een actie doorgaat.",
          "steps": [
            "Open het onderdeel voor goedkeuringen of toegangsverzoeken.",
            "Ververs, bekijk elk verzoek en gebruik alleen beslisacties die je rol toestaat."
          ],
          "permissions": "Beheeracties vereisen de specifieke beleidsrechten. Een voorbeeld geeft geen toegang.",
          "limits": "Goedkeuring geldt binnen de scope van de gevraagde actie. Keur geen opdrachten goed die je niet begrijpt.",
          "example": "Controleer of een gevraagde actie op beoordeling wacht."
        }
      }
    },
    {
      "id": "webui.governance.resume",
      "area": "governance",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.governance.resume"
      ],
      "source_refs": [
        "static/panels.js:14729",
        "static/panels.js:14732"
      ],
      "related": [
        "webui.governance.once",
        "webui.governance.session",
        "webui.governance.always"
      ],
      "locales": {
        "en": {
          "title": "Resume after approval",
          "purpose": "Control the offered consent to resume work after an approval decision.",
          "when": "When access or approval scope needs to be inspected before an action proceeds.",
          "steps": [
            "Read the pending continuation and consent option.",
            "Allow the intended resume or cancel it when the context has changed."
          ],
          "permissions": "Management actions require the specific governance permission. A preview does not grant access.",
          "limits": "Approval is scoped to the requested action. Do not approve commands you do not understand.",
          "example": "Avoid resuming an old action after its purpose has changed."
        },
        "nl": {
          "title": "Hervatten na goedkeuring",
          "purpose": "Bedien de aangeboden toestemming om werk na een goedkeuringsbesluit te hervatten.",
          "when": "Wanneer toegang of goedkeuringsscope moet worden gecontroleerd voordat een actie doorgaat.",
          "steps": [
            "Lees de wachtende voortzetting en toestemmingsoptie.",
            "Sta de bedoelde hervatting toe of annuleer als de context veranderd is."
          ],
          "permissions": "Beheeracties vereisen de specifieke beleidsrechten. Een voorbeeld geeft geen toegang.",
          "limits": "Goedkeuring geldt binnen de scope van de gevraagde actie. Keur geen opdrachten goed die je niet begrijpt.",
          "example": "Voorkom hervatting van een oude actie nadat het doel is veranderd."
        }
      }
    },
    {
      "id": "webui.governance.users",
      "area": "governance",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.governance.users",
        "#govUserEmail",
        "#govUserSave",
        "#govUserAccessLevel",
        "#govUserAccessMode",
        "#govUserApprovalMode"
      ],
      "source_refs": [
        "static/governance.js:220",
        "static/governance.js:221",
        "static/governance.js:237",
        "static/governance.js:272",
        "static/governance.js:273",
        "static/governance.js:454",
        "static/governance.js:459",
        "static/governance.js:465"
      ],
      "related": [
        "webui.governance.once",
        "webui.governance.session",
        "webui.governance.always"
      ],
      "locales": {
        "en": {
          "title": "Manage user access",
          "purpose": "Maintain user-specific access level, mode and approval policy.",
          "when": "When access or approval scope needs to be inspected before an action proceeds.",
          "steps": [
            "Open Governance, Users and select or enter the verified email.",
            "Review access level, mode and approval settings, then save.",
            "Check the resulting policy before removing a user."
          ],
          "permissions": "Management actions require the specific governance permission. A preview does not grant access.",
          "limits": "Approval is scoped to the requested action. Do not approve commands you do not understand.",
          "example": "Give a colleague the specific access needed for their role."
        },
        "nl": {
          "title": "Gebruikerstoegang beheren",
          "purpose": "Beheer gebruikersgebonden toegangsniveau, modus en goedkeuringsbeleid.",
          "when": "Wanneer toegang of goedkeuringsscope moet worden gecontroleerd voordat een actie doorgaat.",
          "steps": [
            "Open Beleid, Gebruikers en kies of vul het gecontroleerde e-mailadres in.",
            "Controleer toegangsniveau, modus en goedkeuring en sla op.",
            "Controleer het resulterende beleid voordat je een gebruiker verwijdert."
          ],
          "permissions": "Beheeracties vereisen de specifieke beleidsrechten. Een voorbeeld geeft geen toegang.",
          "limits": "Goedkeuring geldt binnen de scope van de gevraagde actie. Keur geen opdrachten goed die je niet begrijpt.",
          "example": "Geef een collega de specifieke toegang voor de rol."
        }
      }
    },
    {
      "id": "webui.governance.mcp_map",
      "area": "governance",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.governance.mcp_map"
      ],
      "source_refs": [
        "static/governance.js:294"
      ],
      "related": [
        "webui.governance.once",
        "webui.governance.session",
        "webui.governance.always"
      ],
      "locales": {
        "en": {
          "title": "Governed MCP tool mapping",
          "purpose": "Refine permitted MCP tool access using the governance form.",
          "when": "When access or approval scope needs to be inspected before an action proceeds.",
          "steps": [
            "Open the tool mapping controls for the relevant rule.",
            "Add only the intended mapping and verify the effective permission preview."
          ],
          "permissions": "Management actions require the specific governance permission. A preview does not grant access.",
          "limits": "Approval is scoped to the requested action. Do not approve commands you do not understand.",
          "example": "Limit an integration to its approved tool subset."
        },
        "nl": {
          "title": "Beheerde MCP-tooltoewijzing",
          "purpose": "Verfijn toegestane MCP-tooltoegang via het beleidsformulier.",
          "when": "Wanneer toegang of goedkeuringsscope moet worden gecontroleerd voordat een actie doorgaat.",
          "steps": [
            "Open tooltoewijzing voor de relevante regel.",
            "Voeg alleen de bedoelde toewijzing toe en controleer de effectieve rechtenvoorvertoning."
          ],
          "permissions": "Beheeracties vereisen de specifieke beleidsrechten. Een voorbeeld geeft geen toegang.",
          "limits": "Goedkeuring geldt binnen de scope van de gevraagde actie. Keur geen opdrachten goed die je niet begrijpt.",
          "example": "Beperk een integratie tot de goedgekeurde toolselectie."
        }
      }
    },
    {
      "id": "webui.governance.groups",
      "area": "governance",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.governance.groups",
        "#govGroupName",
        "#govGroupDesc",
        "#govGroupSso",
        "#govGroupRoles"
      ],
      "source_refs": [
        "static/governance.js:1105",
        "static/governance.js:1106",
        "static/governance.js:1113",
        "static/governance.js:1123",
        "static/governance.js:1125",
        "static/governance.js:1127",
        "static/governance.js:1129",
        "static/governance.js:1134",
        "static/governance.js:1135"
      ],
      "related": [
        "webui.governance.once",
        "webui.governance.session",
        "webui.governance.always"
      ],
      "locales": {
        "en": {
          "title": "Manage governance groups",
          "purpose": "Define named groups, descriptions, SSO mapping and roles.",
          "when": "When access or approval scope needs to be inspected before an action proceeds.",
          "steps": [
            "Create or edit the group.",
            "Review group identity, SSO mapping and assigned roles before saving; confirm removals carefully."
          ],
          "permissions": "Management actions require the specific governance permission. A preview does not grant access.",
          "limits": "Approval is scoped to the requested action. Do not approve commands you do not understand.",
          "example": "Map a verified team group to its intended role."
        },
        "nl": {
          "title": "Beleidsgroepen beheren",
          "purpose": "Stel groepsnamen, beschrijvingen, SSO-koppeling en rollen in.",
          "when": "Wanneer toegang of goedkeuringsscope moet worden gecontroleerd voordat een actie doorgaat.",
          "steps": [
            "Maak of bewerk de groep.",
            "Controleer groepsidentiteit, SSO-koppeling en rollen voor opslaan; bevestig verwijderen zorgvuldig."
          ],
          "permissions": "Beheeracties vereisen de specifieke beleidsrechten. Een voorbeeld geeft geen toegang.",
          "limits": "Goedkeuring geldt binnen de scope van de gevraagde actie. Keur geen opdrachten goed die je niet begrijpt.",
          "example": "Koppel een gecontroleerde teamgroep aan de bedoelde rol."
        }
      }
    },
    {
      "id": "webui.governance.preview",
      "area": "governance",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.governance.preview",
        "#govPreviewEmail",
        "#govPreviewGroups"
      ],
      "source_refs": [
        "static/index.html:1034",
        "static/index.html:1036",
        "static/index.html:1040"
      ],
      "related": [
        "webui.governance.once",
        "webui.governance.session",
        "webui.governance.always"
      ],
      "locales": {
        "en": {
          "title": "Preview effective permissions",
          "purpose": "Inspect how current policy resolves for an email and supplied groups.",
          "when": "When access or approval scope needs to be inspected before an action proceeds.",
          "steps": [
            "Open the policy preview.",
            "Enter the identity and relevant groups and run the preview.",
            "Treat it as an inspection, not a permission change."
          ],
          "permissions": "Management actions require the specific governance permission. A preview does not grant access.",
          "limits": "Approval is scoped to the requested action. Do not approve commands you do not understand.",
          "example": "Check a role assignment before asking a colleague to retry."
        },
        "nl": {
          "title": "Effectieve rechten vooraf bekijken",
          "purpose": "Bekijk hoe het huidige beleid uitpakt voor een e-mailadres en opgegeven groepen.",
          "when": "Wanneer toegang of goedkeuringsscope moet worden gecontroleerd voordat een actie doorgaat.",
          "steps": [
            "Open de beleidsvoorvertoning.",
            "Vul identiteit en relevante groepen in en voer de controle uit.",
            "Behandel dit als inspectie, niet als een rechtenwijziging."
          ],
          "permissions": "Beheeracties vereisen de specifieke beleidsrechten. Een voorbeeld geeft geen toegang.",
          "limits": "Goedkeuring geldt binnen de scope van de gevraagde actie. Keur geen opdrachten goed die je niet begrijpt.",
          "example": "Controleer een roltoewijzing voordat een collega opnieuw probeert."
        }
      }
    },
    {
      "id": "webui.governance.audit",
      "area": "governance",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.governance.audit",
        "#governanceRefreshBtn"
      ],
      "source_refs": [
        "static/governance.js:2184",
        "static/index.html:1016",
        "static/index.html:1017",
        "static/index.html:1018",
        "static/index.html:1019",
        "static/index.html:1020",
        "static/index.html:1021",
        "static/index.html:1022",
        "static/index.html:378"
      ],
      "related": [
        "webui.governance.once",
        "webui.governance.session",
        "webui.governance.always"
      ],
      "locales": {
        "en": {
          "title": "Governance overview and audit",
          "purpose": "Inspect policy state and available recorded decisions.",
          "when": "When access or approval scope needs to be inspected before an action proceeds.",
          "steps": [
            "Open Governance and choose the relevant tab.",
            "Refresh or load the audit view and inspect the identity, action and outcome."
          ],
          "permissions": "Management actions require the specific governance permission. A preview does not grant access.",
          "limits": "Approval is scoped to the requested action. Do not approve commands you do not understand.",
          "example": "Trace why an action was refused."
        },
        "nl": {
          "title": "Beleidsoverzicht en audit",
          "purpose": "Bekijk beleidstoestand en beschikbare geregistreerde besluiten.",
          "when": "Wanneer toegang of goedkeuringsscope moet worden gecontroleerd voordat een actie doorgaat.",
          "steps": [
            "Open Beleid en kies het juiste tabblad.",
            "Ververs of laad het auditoverzicht en bekijk identiteit, actie en uitkomst."
          ],
          "permissions": "Beheeracties vereisen de specifieke beleidsrechten. Een voorbeeld geeft geen toegang.",
          "limits": "Goedkeuring geldt binnen de scope van de gevraagde actie. Keur geen opdrachten goed die je niet begrijpt.",
          "example": "Zoek uit waarom een actie is geweigerd."
        }
      }
    },
    {
      "id": "webui.governance.workspace_filter",
      "area": "governance",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.governance.workspace_filter",
        "#govWsUserFilter"
      ],
      "source_refs": [
        "static/governance.js:1416",
        "static/governance.js:1419",
        "static/governance.js:1420"
      ],
      "related": [
        "webui.governance.once",
        "webui.governance.session",
        "webui.governance.always"
      ],
      "locales": {
        "en": {
          "title": "Filter workspace assignments by user",
          "purpose": "Inspect the workspace assignments associated with a user.",
          "when": "When access or approval scope needs to be inspected before an action proceeds.",
          "steps": [
            "Enter the user filter and apply it.",
            "Inspect the assignment list; clear the filter for the full permitted overview."
          ],
          "permissions": "Management actions require the specific governance permission. A preview does not grant access.",
          "limits": "Approval is scoped to the requested action. Do not approve commands you do not understand.",
          "example": "Review which workspaces a colleague can use."
        },
        "nl": {
          "title": "Werkruimtetoewijzingen op gebruiker filteren",
          "purpose": "Bekijk werkruimtetoewijzingen die bij een gebruiker horen.",
          "when": "Wanneer toegang of goedkeuringsscope moet worden gecontroleerd voordat een actie doorgaat.",
          "steps": [
            "Vul het gebruikersfilter in en pas toe.",
            "Bekijk de toewijzingen; wis het filter voor het volledige toegestane overzicht."
          ],
          "permissions": "Beheeracties vereisen de specifieke beleidsrechten. Een voorbeeld geeft geen toegang.",
          "limits": "Goedkeuring geldt binnen de scope van de gevraagde actie. Keur geen opdrachten goed die je niet begrijpt.",
          "example": "Controleer welke werkruimten een collega kan gebruiken."
        }
      }
    },
    {
      "id": "webui.governance.organisation",
      "area": "governance",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.governance.organisation"
      ],
      "source_refs": [
        "static/governance.js"
      ],
      "related": [
        "webui.governance.once",
        "webui.governance.session",
        "webui.governance.always"
      ],
      "locales": {
        "en": {
          "title": "Organisation delegation overview",
          "purpose": "Inspect available organisation role and delegation information without editing it here.",
          "when": "When access or approval scope needs to be inspected before an action proceeds.",
          "steps": [
            "Open the organisation overview if offered.",
            "Read scope and assigned roles; contact the authorised manager for changes."
          ],
          "permissions": "Management actions require the specific governance permission. A preview does not grant access.",
          "limits": "Approval is scoped to the requested action. Do not approve commands you do not understand.",
          "example": "Understand who manages an organisational scope."
        },
        "nl": {
          "title": "Overzicht van organisatiedelegatie",
          "purpose": "Bekijk beschikbare organisatierollen en delegatie zonder deze hier te wijzigen.",
          "when": "Wanneer toegang of goedkeuringsscope moet worden gecontroleerd voordat een actie doorgaat.",
          "steps": [
            "Open het organisatieoverzicht indien aangeboden.",
            "Lees scope en toegewezen rollen; vraag de bevoegde beheerder om wijzigingen."
          ],
          "permissions": "Beheeracties vereisen de specifieke beleidsrechten. Een voorbeeld geeft geen toegang.",
          "limits": "Goedkeuring geldt binnen de scope van de gevraagde actie. Keur geen opdrachten goed die je niet begrijpt.",
          "example": "Begrijp wie een organisatiescope beheert."
        }
      }
    },
    {
      "id": "webui.operations.refresh",
      "area": "operations",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.operations.refresh",
        "#btnReload",
        "#btnStaleClientRefresh",
        "#offlineCheckNow"
      ],
      "source_refs": [
        "static/index.html:155",
        "static/index.html:469",
        "static/index.html:502",
        "static/index.html:503",
        "static/index.html:512",
        "static/panels.js:3609"
      ],
      "related": [
        "webui.operations.health",
        "webui.operations.terminal",
        "webui.operations.logs"
      ],
      "locales": {
        "en": {
          "title": "Reload and recover the client",
          "purpose": "Refresh stale client code or reload conversation state after an interruption.",
          "when": "When investigating service behaviour or preparing an authorised maintenance action.",
          "steps": [
            "Preserve important unsent text before a full reload.",
            "Use the offered Refresh or reconnect action and wait until the conversation is ready."
          ],
          "permissions": "Operational views and maintenance actions require the relevant management rights.",
          "limits": "Status is a snapshot, not a delivery guarantee. Diagnostic copies may contain operational details; review before sharing.",
          "example": "Recover the view after a network interruption."
        },
        "nl": {
          "title": "De client vernieuwen en herstellen",
          "purpose": "Ververs verouderde clientcode of laad gespreksstatus na een onderbreking opnieuw.",
          "when": "Bij onderzoek naar servicegedrag of voorbereiding van een toegestane onderhoudsactie.",
          "steps": [
            "Bewaar belangrijke niet-verstuurde tekst voor volledig herladen.",
            "Gebruik de aangeboden ververs- of verbindingsactie en wacht tot het gesprek gereed is."
          ],
          "permissions": "Operationele schermen en onderhoudsacties vereisen de bijbehorende beheerrechten.",
          "limits": "Status is een momentopname en geen bezorggarantie. Diagnostische kopieën kunnen operationele gegevens bevatten; controleer ze voor delen.",
          "example": "Herstel de weergave na een netwerkonderbreking."
        }
      }
    },
    {
      "id": "webui.operations.health",
      "area": "operations",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.operations.health",
        "#btnRestartGateway",
        "#agentHealthDismiss"
      ],
      "source_refs": [
        "static/index.html:520",
        "static/index.html:521",
        "static/panels.js:14468"
      ],
      "related": [
        "webui.operations.refresh",
        "webui.operations.terminal",
        "webui.operations.logs"
      ],
      "locales": {
        "en": {
          "title": "Agent and gateway status",
          "purpose": "Inspect runtime health and perform an offered gateway action with the required rights.",
          "when": "When investigating service behaviour or preparing an authorised maintenance action.",
          "steps": [
            "Read the status or alert details.",
            "Refresh or use the specific restart action only when needed; dismissing an alert does not fix its cause."
          ],
          "permissions": "Operational views and maintenance actions require the relevant management rights.",
          "limits": "Status is a snapshot, not a delivery guarantee. Diagnostic copies may contain operational details; review before sharing.",
          "example": "Check the gateway when a channel stops responding."
        },
        "nl": {
          "title": "Agent- en gatewaystatus",
          "purpose": "Bekijk runtimestatus en voer met de nodige rechten een aangeboden gatewayactie uit.",
          "when": "Bij onderzoek naar servicegedrag of voorbereiding van een toegestane onderhoudsactie.",
          "steps": [
            "Lees status- of waarschuwingsdetails.",
            "Ververs of gebruik de specifieke herstartactie alleen indien nodig; sluiten van een waarschuwing verhelpt de oorzaak niet."
          ],
          "permissions": "Operationele schermen en onderhoudsacties vereisen de bijbehorende beheerrechten.",
          "limits": "Status is een momentopname en geen bezorggarantie. Diagnostische kopieën kunnen operationele gegevens bevatten; controleer ze voor delen.",
          "example": "Controleer de gateway wanneer een kanaal niet meer reageert."
        }
      }
    },
    {
      "id": "webui.operations.terminal",
      "area": "operations",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.operations.terminal",
        "#btnTerminalClear",
        "#btnTerminalCopy",
        "#btnTerminalRestart",
        "#btnTerminalCollapse",
        "#btnTerminalClose",
        "#btnTerminalExpand",
        "#btnTerminalDockClose"
      ],
      "source_refs": [
        "static/commands.js",
        "static/index.html:593",
        "static/index.html:594",
        "static/index.html:595",
        "static/index.html:596",
        "static/index.html:597",
        "static/index.html:612",
        "static/index.html:613"
      ],
      "related": [
        "webui.operations.refresh",
        "webui.operations.health",
        "webui.operations.logs"
      ],
      "locales": {
        "en": {
          "title": "Terminal panel",
          "purpose": "Inspect an available terminal session and its output.",
          "when": "When investigating service behaviour or preparing an authorised maintenance action.",
          "steps": [
            "Open or expand the terminal panel.",
            "Copy output if needed; clear the display or restart only after checking the effect.",
            "Collapse or close the panel when finished.",
            "Composer shortcut: /terminal. Review any required arguments in the command suggestions."
          ],
          "permissions": "Operational views and maintenance actions require the relevant management rights.",
          "limits": "Status is a snapshot, not a delivery guarantee. Diagnostic copies may contain operational details; review before sharing.",
          "example": "Read command output related to the current task."
        },
        "nl": {
          "title": "Terminalpaneel",
          "purpose": "Bekijk een beschikbare terminalsessie en de uitvoer.",
          "when": "Bij onderzoek naar servicegedrag of voorbereiding van een toegestane onderhoudsactie.",
          "steps": [
            "Open het terminalpaneel of klap het uit.",
            "Kopieer zo nodig uitvoer; wis de weergave of herstart pas na controle van het effect.",
            "Klap het paneel dicht of sluit na afloop.",
            "Snelopdracht in het berichtveld: /terminal. Controleer eventuele argumenten in de opdrachtsuggesties."
          ],
          "permissions": "Operationele schermen en onderhoudsacties vereisen de bijbehorende beheerrechten.",
          "limits": "Status is een momentopname en geen bezorggarantie. Diagnostische kopieën kunnen operationele gegevens bevatten; controleer ze voor delen.",
          "example": "Lees opdrachtuitvoer die bij de huidige taak hoort."
        }
      }
    },
    {
      "id": "webui.operations.logs",
      "area": "operations",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.operations.logs",
        "#logsRefreshBtn",
        "#logsFile",
        "#logsTail",
        "#logsSeverityFilter",
        "#logsAutoRefresh",
        "#logsWrap",
        "#logsCopyAll"
      ],
      "source_refs": [
        "static/index.html:345",
        "static/index.html:350",
        "static/index.html:356",
        "static/index.html:363",
        "static/index.html:368",
        "static/index.html:369",
        "static/index.html:370",
        "static/index.html:998"
      ],
      "related": [
        "webui.operations.refresh",
        "webui.operations.health",
        "webui.operations.terminal"
      ],
      "locales": {
        "en": {
          "title": "Log file, tail and filters",
          "purpose": "Inspect permitted runtime logs with a bounded tail and severity filter.",
          "when": "When investigating service behaviour or preparing an authorised maintenance action.",
          "steps": [
            "Select the log file and tail length.",
            "Set severity, wrapping and automatic refresh as needed.",
            "Copy only reviewed log details for support."
          ],
          "permissions": "Operational views and maintenance actions require the relevant management rights.",
          "limits": "Status is a snapshot, not a delivery guarantee. Diagnostic copies may contain operational details; review before sharing.",
          "example": "Inspect recent errors while avoiding an entire log export."
        },
        "nl": {
          "title": "Logbestand, laatste regels en filters",
          "purpose": "Bekijk toegestane runtimelogboeken met een begrensd aantal laatste regels en ernstfilter.",
          "when": "Bij onderzoek naar servicegedrag of voorbereiding van een toegestane onderhoudsactie.",
          "steps": [
            "Kies logbestand en aantal laatste regels.",
            "Stel ernst, regelafbreking en automatisch verversen in.",
            "Kopieer alleen gecontroleerde loggegevens voor ondersteuning."
          ],
          "permissions": "Operationele schermen en onderhoudsacties vereisen de bijbehorende beheerrechten.",
          "limits": "Status is een momentopname en geen bezorggarantie. Diagnostische kopieën kunnen operationele gegevens bevatten; controleer ze voor delen.",
          "example": "Bekijk recente fouten zonder het volledige logboek te exporteren."
        }
      }
    },
    {
      "id": "webui.operations.insights",
      "area": "operations",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.operations.insights",
        "#insightsRefreshBtn",
        "#insightsPeriod"
      ],
      "source_refs": [
        "static/index.html:296",
        "static/index.html:300"
      ],
      "related": [
        "webui.operations.refresh",
        "webui.operations.health",
        "webui.operations.terminal"
      ],
      "locales": {
        "en": {
          "title": "Usage insights and period",
          "purpose": "Review available usage summaries for a selected time period.",
          "when": "When investigating service behaviour or preparing an authorised maintenance action.",
          "steps": [
            "Open Insights and choose the period.",
            "Refresh the view and read the units and timestamps before comparing values."
          ],
          "permissions": "Operational views and maintenance actions require the relevant management rights.",
          "limits": "Status is a snapshot, not a delivery guarantee. Diagnostic copies may contain operational details; review before sharing.",
          "example": "Compare recent usage with an earlier reporting period."
        },
        "nl": {
          "title": "Gebruiksinzichten en periode",
          "purpose": "Bekijk beschikbare gebruikssamenvattingen voor een gekozen periode.",
          "when": "Bij onderzoek naar servicegedrag of voorbereiding van een toegestane onderhoudsactie.",
          "steps": [
            "Open Inzichten en kies de periode.",
            "Ververs en lees eenheden en tijdstippen voordat je waarden vergelijkt."
          ],
          "permissions": "Operationele schermen en onderhoudsacties vereisen de bijbehorende beheerrechten.",
          "limits": "Status is een momentopname en geen bezorggarantie. Diagnostische kopieën kunnen operationele gegevens bevatten; controleer ze voor delen.",
          "example": "Vergelijk recent gebruik met een eerdere rapportageperiode."
        }
      }
    },
    {
      "id": "webui.operations.capacity",
      "area": "operations",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.operations.capacity",
        "#capacityPollSeconds",
        "#capacityCooldownSeconds",
        "#capacityThresholds",
        "#capacityDestination",
        "#btnCapacitySave"
      ],
      "source_refs": [
        "static/index.html:1788",
        "static/index.html:1790",
        "static/index.html:1792",
        "static/index.html:1794",
        "static/index.html:1797",
        "static/index.html:1798",
        "static/panels.js:14862"
      ],
      "related": [
        "webui.operations.refresh",
        "webui.operations.health",
        "webui.operations.terminal"
      ],
      "locales": {
        "en": {
          "title": "Capacity thresholds and alerts",
          "purpose": "Configure allowed quota polling and alert delivery settings.",
          "when": "When investigating service behaviour or preparing an authorised maintenance action.",
          "steps": [
            "Set poll interval, cooldown, provider thresholds and verified destination.",
            "Save and inspect current alerts; acknowledge an alert after reviewing it."
          ],
          "permissions": "Operational views and maintenance actions require the relevant management rights.",
          "limits": "Status is a snapshot, not a delivery guarantee. Diagnostic copies may contain operational details; review before sharing.",
          "example": "Receive an approved alert before a provider quota is exhausted."
        },
        "nl": {
          "title": "Capaciteitsgrenzen en waarschuwingen",
          "purpose": "Stel toegestane quota-opvraging en waarschuwingsbezorging in.",
          "when": "Bij onderzoek naar servicegedrag of voorbereiding van een toegestane onderhoudsactie.",
          "steps": [
            "Stel opvraaginterval, afkoeltijd, providergrenzen en gecontroleerde bestemming in.",
            "Sla op en bekijk actuele waarschuwingen; bevestig een waarschuwing na controle."
          ],
          "permissions": "Operationele schermen en onderhoudsacties vereisen de bijbehorende beheerrechten.",
          "limits": "Status is een momentopname en geen bezorggarantie. Diagnostische kopieën kunnen operationele gegevens bevatten; controleer ze voor delen.",
          "example": "Ontvang een goedgekeurde waarschuwing voordat providerquota op is."
        }
      }
    },
    {
      "id": "webui.operations.updates",
      "area": "operations",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.operations.updates",
        "#btnCheckUpdatesNow"
      ],
      "source_refs": [
        "static/index.html:1779"
      ],
      "related": [
        "webui.operations.refresh",
        "webui.operations.health",
        "webui.operations.terminal"
      ],
      "locales": {
        "en": {
          "title": "Check for updates",
          "purpose": "Inspect available update information without assuming an update has been installed.",
          "when": "When investigating service behaviour or preparing an authorised maintenance action.",
          "steps": [
            "Open the update section and choose Check now.",
            "Read the version and release information before following the offered update procedure."
          ],
          "permissions": "Operational views and maintenance actions require the relevant management rights.",
          "limits": "Status is a snapshot, not a delivery guarantee. Diagnostic copies may contain operational details; review before sharing.",
          "example": "Verify whether a reported fix is in an available release."
        },
        "nl": {
          "title": "Naar updates zoeken",
          "purpose": "Bekijk beschikbare update-informatie zonder aan te nemen dat een update geïnstalleerd is.",
          "when": "Bij onderzoek naar servicegedrag of voorbereiding van een toegestane onderhoudsactie.",
          "steps": [
            "Open het updategedeelte en kies Nu controleren.",
            "Lees versie- en release-informatie voordat je de aangeboden updateprocedure volgt."
          ],
          "permissions": "Operationele schermen en onderhoudsacties vereisen de bijbehorende beheerrechten.",
          "limits": "Status is een momentopname en geen bezorggarantie. Diagnostische kopieën kunnen operationele gegevens bevatten; controleer ze voor delen.",
          "example": "Controleer of een gemelde oplossing in een beschikbare release zit."
        }
      }
    },
    {
      "id": "webui.operations.errors",
      "area": "operations",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.operations.errors"
      ],
      "source_refs": [
        "static/panels.js:14252",
        "static/ui.js:731",
        "static/ui.js:9359"
      ],
      "related": [
        "webui.operations.refresh",
        "webui.operations.health",
        "webui.operations.terminal"
      ],
      "locales": {
        "en": {
          "title": "Error details and conversation link",
          "purpose": "Inspect a reported error and open the affected conversation when offered.",
          "when": "When investigating service behaviour or preparing an authorised maintenance action.",
          "steps": [
            "Read the error and use its conversation link for context.",
            "Copy the message only after review; dismiss it when finished."
          ],
          "permissions": "Operational views and maintenance actions require the relevant management rights.",
          "limits": "Status is a snapshot, not a delivery guarantee. Diagnostic copies may contain operational details; review before sharing.",
          "example": "Locate the conversation that encountered a failed request."
        },
        "nl": {
          "title": "Foutdetails en gesprekslink",
          "purpose": "Bekijk een gemelde fout en open het betreffende gesprek indien aangeboden.",
          "when": "Bij onderzoek naar servicegedrag of voorbereiding van een toegestane onderhoudsactie.",
          "steps": [
            "Lees de fout en gebruik de gesprekslink voor context.",
            "Kopieer de melding pas na controle; sluit deze na afloop."
          ],
          "permissions": "Operationele schermen en onderhoudsacties vereisen de bijbehorende beheerrechten.",
          "limits": "Status is een momentopname en geen bezorggarantie. Diagnostische kopieën kunnen operationele gegevens bevatten; controleer ze voor delen.",
          "example": "Vind het gesprek waarin een verzoek mislukte."
        }
      }
    },
    {
      "id": "webui.operations.extensions",
      "area": "operations",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.operations.extensions",
        "#extensionsCopyDiagnosticsBtn"
      ],
      "source_refs": [
        "static/index.html:1747"
      ],
      "related": [
        "webui.operations.refresh",
        "webui.operations.health",
        "webui.operations.terminal"
      ],
      "locales": {
        "en": {
          "title": "Extension status and diagnostics",
          "purpose": "Inspect installed extension status and the offered diagnostic summary.",
          "when": "When investigating service behaviour or preparing an authorised maintenance action.",
          "steps": [
            "Open Extensions in Settings.",
            "Read state and any configuration requirements; review diagnostics before copying them."
          ],
          "permissions": "Operational views and maintenance actions require the relevant management rights.",
          "limits": "Status is a snapshot, not a delivery guarantee. Diagnostic copies may contain operational details; review before sharing.",
          "example": "Check whether an extension is configured before relying on it."
        },
        "nl": {
          "title": "Extensiestatus en diagnostiek",
          "purpose": "Bekijk geïnstalleerde extensies en de aangeboden diagnostische samenvatting.",
          "when": "Bij onderzoek naar servicegedrag of voorbereiding van een toegestane onderhoudsactie.",
          "steps": [
            "Open Extensies in Instellingen.",
            "Lees toestand en configuratievereisten; controleer diagnostiek voordat je kopieert."
          ],
          "permissions": "Operationele schermen en onderhoudsacties vereisen de bijbehorende beheerrechten.",
          "limits": "Status is een momentopname en geen bezorggarantie. Diagnostische kopieën kunnen operationele gegevens bevatten; controleer ze voor delen.",
          "example": "Controleer of een extensie ingesteld is voordat je erop rekent."
        }
      }
    },
    {
      "id": "webui.operations.dashboard",
      "area": "operations",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.operations.dashboard",
        "#dashboardRailBtn",
        "#dashboardMobileBtn"
      ],
      "source_refs": [
        "static/index.html:174",
        "static/index.html:198"
      ],
      "related": [
        "webui.operations.refresh",
        "webui.operations.health",
        "webui.operations.terminal"
      ],
      "locales": {
        "en": {
          "title": "Open the configured dashboard",
          "purpose": "Open the dashboard view made available by the installation.",
          "when": "When investigating service behaviour or preparing an authorised maintenance action.",
          "steps": [
            "Choose Dashboard in navigation.",
            "If unavailable, check the configured dashboard mode with an administrator."
          ],
          "permissions": "Operational views and maintenance actions require the relevant management rights.",
          "limits": "Status is a snapshot, not a delivery guarantee. Diagnostic copies may contain operational details; review before sharing.",
          "example": "View the installation’s configured operational dashboard."
        },
        "nl": {
          "title": "Het ingestelde dashboard openen",
          "purpose": "Open de dashboardweergave die de installatie beschikbaar stelt.",
          "when": "Bij onderzoek naar servicegedrag of voorbereiding van een toegestane onderhoudsactie.",
          "steps": [
            "Kies Dashboard in de navigatie.",
            "Controleer bij onbeschikbaarheid de ingestelde dashboardmodus met een beheerder."
          ],
          "permissions": "Operationele schermen en onderhoudsacties vereisen de bijbehorende beheerrechten.",
          "limits": "Status is een momentopname en geen bezorggarantie. Diagnostische kopieën kunnen operationele gegevens bevatten; controleer ze voor delen.",
          "example": "Bekijk het ingestelde operationele dashboard van de installatie."
        }
      }
    },
    {
      "id": "webui.settings.theme",
      "area": "settings",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.settings.theme",
        "#settingsTheme"
      ],
      "source_refs": [
        "static/commands.js",
        "static/index.html:1158",
        "static/index.html:1164",
        "static/index.html:1170",
        "static/index.html:1177"
      ],
      "related": [
        "webui.settings.skin",
        "webui.settings.font_size",
        "webui.settings.workspace_panel_open"
      ],
      "locales": {
        "en": {
          "title": "Theme",
          "purpose": "Choose light, dark or system-following colors.",
          "when": "When the current configuration or presentation does not fit the intended workflow.",
          "steps": [
            "Open Settings and find Theme.",
            "Choose the desired value; use Save if offered, or wait for autosave confirmation.",
            "Composer shortcut: /theme. Review any required arguments in the command suggestions."
          ],
          "permissions": "Appearance preferences can be personal. Model, provider, security and server changes require configuration rights.",
          "limits": "Some options appear only when enabled by an administrator or supported by your browser. Save feedback determines whether the change was applied.",
          "example": "Follow your device’s dark mode."
        },
        "nl": {
          "title": "Thema",
          "purpose": "Kies lichte, donkere of systeemkleuren.",
          "when": "Wanneer de huidige instelling of weergave niet past bij de bedoelde werkwijze.",
          "steps": [
            "Open Instellingen en zoek Thema.",
            "Kies de gewenste waarde; gebruik Opslaan indien aangeboden of wacht op bevestiging van automatisch opslaan.",
            "Snelopdracht in het berichtveld: /theme. Controleer eventuele argumenten in de opdrachtsuggesties."
          ],
          "permissions": "Weergavevoorkeuren kunnen persoonlijk zijn. Model-, provider-, beveiligings- en serverwijzigingen vereisen configuratierechten.",
          "limits": "Sommige opties verschijnen alleen als een beheerder ze inschakelt of je browser ze ondersteunt. De opslagmelding bepaalt of de wijziging is toegepast.",
          "example": "Volg de donkere modus van je apparaat."
        }
      }
    },
    {
      "id": "webui.settings.skin",
      "area": "settings",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.settings.skin",
        "#settingsSkin"
      ],
      "source_refs": [
        "static/index.html:1183"
      ],
      "related": [
        "webui.settings.theme",
        "webui.settings.font_size",
        "webui.settings.workspace_panel_open"
      ],
      "locales": {
        "en": {
          "title": "Interface skin",
          "purpose": "Choose one of the installed visual skins.",
          "when": "When the current configuration or presentation does not fit the intended workflow.",
          "steps": [
            "Open Settings and find Interface skin.",
            "Choose the desired value; use Save if offered, or wait for autosave confirmation."
          ],
          "permissions": "Appearance preferences can be personal. Model, provider, security and server changes require configuration rights.",
          "limits": "Some options appear only when enabled by an administrator or supported by your browser. Save feedback determines whether the change was applied.",
          "example": "Use a calmer color treatment."
        },
        "nl": {
          "title": "Interfacevormgeving",
          "purpose": "Kies een van de geïnstalleerde visuele stijlen.",
          "when": "Wanneer de huidige instelling of weergave niet past bij de bedoelde werkwijze.",
          "steps": [
            "Open Instellingen en zoek Interfacevormgeving.",
            "Kies de gewenste waarde; gebruik Opslaan indien aangeboden of wacht op bevestiging van automatisch opslaan."
          ],
          "permissions": "Weergavevoorkeuren kunnen persoonlijk zijn. Model-, provider-, beveiligings- en serverwijzigingen vereisen configuratierechten.",
          "limits": "Sommige opties verschijnen alleen als een beheerder ze inschakelt of je browser ze ondersteunt. De opslagmelding bepaalt of de wijziging is toegepast.",
          "example": "Gebruik een rustigere kleurweergave."
        }
      }
    },
    {
      "id": "webui.settings.font_size",
      "area": "settings",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.settings.font_size",
        "#settingsFontSize"
      ],
      "source_refs": [
        "static/index.html:1188",
        "static/index.html:1194",
        "static/index.html:1200",
        "static/index.html:1206",
        "static/index.html:1213"
      ],
      "related": [
        "webui.settings.theme",
        "webui.settings.skin",
        "webui.settings.workspace_panel_open"
      ],
      "locales": {
        "en": {
          "title": "Font size",
          "purpose": "Change the reading size used by the interface.",
          "when": "When the current configuration or presentation does not fit the intended workflow.",
          "steps": [
            "Open Settings and find Font size.",
            "Choose the desired value; use Save if offered, or wait for autosave confirmation."
          ],
          "permissions": "Appearance preferences can be personal. Model, provider, security and server changes require configuration rights.",
          "limits": "Some options appear only when enabled by an administrator or supported by your browser. Save feedback determines whether the change was applied.",
          "example": "Increase text size on a small display."
        },
        "nl": {
          "title": "Lettergrootte",
          "purpose": "Wijzig de leesgrootte van de interface.",
          "when": "Wanneer de huidige instelling of weergave niet past bij de bedoelde werkwijze.",
          "steps": [
            "Open Instellingen en zoek Lettergrootte.",
            "Kies de gewenste waarde; gebruik Opslaan indien aangeboden of wacht op bevestiging van automatisch opslaan."
          ],
          "permissions": "Weergavevoorkeuren kunnen persoonlijk zijn. Model-, provider-, beveiligings- en serverwijzigingen vereisen configuratierechten.",
          "limits": "Sommige opties verschijnen alleen als een beheerder ze inschakelt of je browser ze ondersteunt. De opslagmelding bepaalt of de wijziging is toegepast.",
          "example": "Vergroot tekst op een klein scherm."
        }
      }
    },
    {
      "id": "webui.settings.workspace_panel_open",
      "area": "settings",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.settings.workspace_panel_open",
        "#settingsWorkspacePanelOpen"
      ],
      "source_refs": [
        "static/index.html:1217"
      ],
      "related": [
        "webui.settings.theme",
        "webui.settings.skin",
        "webui.settings.font_size"
      ],
      "locales": {
        "en": {
          "title": "Workspace panel visibility",
          "purpose": "Choose whether the workspace panel opens by default.",
          "when": "When the current configuration or presentation does not fit the intended workflow.",
          "steps": [
            "Open Settings and find Workspace panel visibility.",
            "Choose the desired value; use Save if offered, or wait for autosave confirmation."
          ],
          "permissions": "Appearance preferences can be personal. Model, provider, security and server changes require configuration rights.",
          "limits": "Some options appear only when enabled by an administrator or supported by your browser. Save feedback determines whether the change was applied.",
          "example": "Keep files visible while reviewing a document."
        },
        "nl": {
          "title": "Zichtbaarheid van het werkruimtepaneel",
          "purpose": "Kies of het werkruimtepaneel standaard opent.",
          "when": "Wanneer de huidige instelling of weergave niet past bij de bedoelde werkwijze.",
          "steps": [
            "Open Instellingen en zoek Zichtbaarheid van het werkruimtepaneel.",
            "Kies de gewenste waarde; gebruik Opslaan indien aangeboden of wacht op bevestiging van automatisch opslaan."
          ],
          "permissions": "Weergavevoorkeuren kunnen persoonlijk zijn. Model-, provider-, beveiligings- en serverwijzigingen vereisen configuratierechten.",
          "limits": "Sommige opties verschijnen alleen als een beheerder ze inschakelt of je browser ze ondersteunt. De opslagmelding bepaalt of de wijziging is toegepast.",
          "example": "Houd bestanden zichtbaar tijdens documentcontrole."
        }
      }
    },
    {
      "id": "webui.settings.workspace_todos_tab",
      "area": "settings",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.settings.workspace_todos_tab",
        "#settingsWorkspaceTodosTab"
      ],
      "source_refs": [
        "static/index.html:1224"
      ],
      "related": [
        "webui.settings.theme",
        "webui.settings.skin",
        "webui.settings.font_size"
      ],
      "locales": {
        "en": {
          "title": "Workspace todo tab",
          "purpose": "Show or hide the workspace todo tab.",
          "when": "When the current configuration or presentation does not fit the intended workflow.",
          "steps": [
            "Open Settings and find Workspace todo tab.",
            "Choose the desired value; use Save if offered, or wait for autosave confirmation."
          ],
          "permissions": "Appearance preferences can be personal. Model, provider, security and server changes require configuration rights.",
          "limits": "Some options appear only when enabled by an administrator or supported by your browser. Save feedback determines whether the change was applied.",
          "example": "Expose project todos beside the file list."
        },
        "nl": {
          "title": "Werkruimtetakentabblad",
          "purpose": "Toon of verberg het tabblad met werkruimtetaken.",
          "when": "Wanneer de huidige instelling of weergave niet past bij de bedoelde werkwijze.",
          "steps": [
            "Open Instellingen en zoek Werkruimtetakentabblad.",
            "Kies de gewenste waarde; gebruik Opslaan indien aangeboden of wacht op bevestiging van automatisch opslaan."
          ],
          "permissions": "Weergavevoorkeuren kunnen persoonlijk zijn. Model-, provider-, beveiligings- en serverwijzigingen vereisen configuratierechten.",
          "limits": "Sommige opties verschijnen alleen als een beheerder ze inschakelt of je browser ze ondersteunt. De opslagmelding bepaalt of de wijziging is toegepast.",
          "example": "Toon projecttaken naast de bestandenlijst."
        }
      }
    },
    {
      "id": "webui.settings.session_jump_buttons",
      "area": "settings",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.settings.session_jump_buttons",
        "#settingsSessionJumpButtons"
      ],
      "source_refs": [
        "static/index.html:1231"
      ],
      "related": [
        "webui.settings.theme",
        "webui.settings.skin",
        "webui.settings.font_size"
      ],
      "locales": {
        "en": {
          "title": "Conversation jump buttons",
          "purpose": "Show controls for jumping to the start or end of a conversation.",
          "when": "When the current configuration or presentation does not fit the intended workflow.",
          "steps": [
            "Open Settings and find Conversation jump buttons.",
            "Choose the desired value; use Save if offered, or wait for autosave confirmation."
          ],
          "permissions": "Appearance preferences can be personal. Model, provider, security and server changes require configuration rights.",
          "limits": "Some options appear only when enabled by an administrator or supported by your browser. Save feedback determines whether the change was applied.",
          "example": "Reach the latest response without scrolling through history."
        },
        "nl": {
          "title": "Sprongknoppen in gesprekken",
          "purpose": "Toon knoppen om naar begin of einde van een gesprek te springen.",
          "when": "Wanneer de huidige instelling of weergave niet past bij de bedoelde werkwijze.",
          "steps": [
            "Open Instellingen en zoek Sprongknoppen in gesprekken.",
            "Kies de gewenste waarde; gebruik Opslaan indien aangeboden of wacht op bevestiging van automatisch opslaan."
          ],
          "permissions": "Weergavevoorkeuren kunnen persoonlijk zijn. Model-, provider-, beveiligings- en serverwijzigingen vereisen configuratierechten.",
          "limits": "Sommige opties verschijnen alleen als een beheerder ze inschakelt of je browser ze ondersteunt. De opslagmelding bepaalt of de wijziging is toegepast.",
          "example": "Bereik het nieuwste antwoord zonder door de geschiedenis te scrollen."
        }
      }
    },
    {
      "id": "webui.settings.session_endless_scroll",
      "area": "settings",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.settings.session_endless_scroll",
        "#settingsSessionEndlessScroll"
      ],
      "source_refs": [
        "static/index.html:1238"
      ],
      "related": [
        "webui.settings.theme",
        "webui.settings.skin",
        "webui.settings.font_size"
      ],
      "locales": {
        "en": {
          "title": "Continuous history scrolling",
          "purpose": "Choose the supported continuous loading behavior for conversation history.",
          "when": "When the current configuration or presentation does not fit the intended workflow.",
          "steps": [
            "Open Settings and find Continuous history scrolling.",
            "Choose the desired value; use Save if offered, or wait for autosave confirmation."
          ],
          "permissions": "Appearance preferences can be personal. Model, provider, security and server changes require configuration rights.",
          "limits": "Some options appear only when enabled by an administrator or supported by your browser. Save feedback determines whether the change was applied.",
          "example": "Read older messages as you scroll upward."
        },
        "nl": {
          "title": "Doorlopend door geschiedenis scrollen",
          "purpose": "Kies het ondersteunde doorlopende laadgedrag voor gespreksgeschiedenis.",
          "when": "Wanneer de huidige instelling of weergave niet past bij de bedoelde werkwijze.",
          "steps": [
            "Open Instellingen en zoek Doorlopend door geschiedenis scrollen.",
            "Kies de gewenste waarde; gebruik Opslaan indien aangeboden of wacht op bevestiging van automatisch opslaan."
          ],
          "permissions": "Weergavevoorkeuren kunnen persoonlijk zijn. Model-, provider-, beveiligings- en serverwijzigingen vereisen configuratierechten.",
          "limits": "Sommige opties verschijnen alleen als een beheerder ze inschakelt of je browser ze ondersteunt. De opslagmelding bepaalt of de wijziging is toegepast.",
          "example": "Lees oudere berichten terwijl je omhoog scrolt."
        }
      }
    },
    {
      "id": "webui.settings.chat_activity_display_mode",
      "area": "settings",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.settings.chat_activity_display_mode",
        "#settingsChatActivityDisplayMode"
      ],
      "source_refs": [
        "static/index.html:1246",
        "static/index.html:1249",
        "static/index.html:1252",
        "static/index.html:1256"
      ],
      "related": [
        "webui.settings.theme",
        "webui.settings.skin",
        "webui.settings.font_size"
      ],
      "locales": {
        "en": {
          "title": "Activity display mode",
          "purpose": "Choose compact work-log or detailed activity presentation.",
          "when": "When the current configuration or presentation does not fit the intended workflow.",
          "steps": [
            "Open Settings and find Activity display mode.",
            "Choose the desired value; use Save if offered, or wait for autosave confirmation."
          ],
          "permissions": "Appearance preferences can be personal. Model, provider, security and server changes require configuration rights.",
          "limits": "Some options appear only when enabled by an administrator or supported by your browser. Save feedback determines whether the change was applied.",
          "example": "Use compact activity while focusing on the answer."
        },
        "nl": {
          "title": "Weergavemodus voor activiteit",
          "purpose": "Kies compacte werklogweergave of gedetailleerde activiteit.",
          "when": "Wanneer de huidige instelling of weergave niet past bij de bedoelde werkwijze.",
          "steps": [
            "Open Instellingen en zoek Weergavemodus voor activiteit.",
            "Kies de gewenste waarde; gebruik Opslaan indien aangeboden of wacht op bevestiging van automatisch opslaan."
          ],
          "permissions": "Weergavevoorkeuren kunnen persoonlijk zijn. Model-, provider-, beveiligings- en serverwijzigingen vereisen configuratierechten.",
          "limits": "Sommige opties verschijnen alleen als een beheerder ze inschakelt of je browser ze ondersteunt. De opslagmelding bepaalt of de wijziging is toegepast.",
          "example": "Gebruik compacte activiteit terwijl je op het antwoord focust."
        }
      }
    },
    {
      "id": "webui.settings.transparent_event_timestamps",
      "area": "settings",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.settings.transparent_event_timestamps",
        "#settingsTransparentEventTimestamps"
      ],
      "source_refs": [
        "static/index.html:1263"
      ],
      "related": [
        "webui.settings.theme",
        "webui.settings.skin",
        "webui.settings.font_size"
      ],
      "locales": {
        "en": {
          "title": "Activity timestamps",
          "purpose": "Show event times in the detailed activity stream.",
          "when": "When the current configuration or presentation does not fit the intended workflow.",
          "steps": [
            "Open Settings and find Activity timestamps.",
            "Choose the desired value; use Save if offered, or wait for autosave confirmation."
          ],
          "permissions": "Appearance preferences can be personal. Model, provider, security and server changes require configuration rights.",
          "limits": "Some options appear only when enabled by an administrator or supported by your browser. Save feedback determines whether the change was applied.",
          "example": "Compare when two tool events occurred."
        },
        "nl": {
          "title": "Tijdstippen bij activiteit",
          "purpose": "Toon gebeurtenistijden in de gedetailleerde activiteitsstroom.",
          "when": "Wanneer de huidige instelling of weergave niet past bij de bedoelde werkwijze.",
          "steps": [
            "Open Instellingen en zoek Tijdstippen bij activiteit.",
            "Kies de gewenste waarde; gebruik Opslaan indien aangeboden of wacht op bevestiging van automatisch opslaan."
          ],
          "permissions": "Weergavevoorkeuren kunnen persoonlijk zijn. Model-, provider-, beveiligings- en serverwijzigingen vereisen configuratierechten.",
          "limits": "Sommige opties verschijnen alleen als een beheerder ze inschakelt of je browser ze ondersteunt. De opslagmelding bepaalt of de wijziging is toegepast.",
          "example": "Vergelijk wanneer twee toolgebeurtenissen plaatsvonden."
        }
      }
    },
    {
      "id": "webui.settings.auto_scroll_follow",
      "area": "settings",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.settings.auto_scroll_follow",
        "#settingsAutoScrollFollow"
      ],
      "source_refs": [
        "static/index.html:1270"
      ],
      "related": [
        "webui.settings.theme",
        "webui.settings.skin",
        "webui.settings.font_size"
      ],
      "locales": {
        "en": {
          "title": "Follow new output",
          "purpose": "Choose whether the view follows incoming response content.",
          "when": "When the current configuration or presentation does not fit the intended workflow.",
          "steps": [
            "Open Settings and find Follow new output.",
            "Choose the desired value; use Save if offered, or wait for autosave confirmation."
          ],
          "permissions": "Appearance preferences can be personal. Model, provider, security and server changes require configuration rights.",
          "limits": "Some options appear only when enabled by an administrator or supported by your browser. Save feedback determines whether the change was applied.",
          "example": "Keep reading an earlier paragraph while output continues."
        },
        "nl": {
          "title": "Nieuwe uitvoer volgen",
          "purpose": "Kies of de weergave binnenkomende antwoordtekst volgt.",
          "when": "Wanneer de huidige instelling of weergave niet past bij de bedoelde werkwijze.",
          "steps": [
            "Open Instellingen en zoek Nieuwe uitvoer volgen.",
            "Kies de gewenste waarde; gebruik Opslaan indien aangeboden of wacht op bevestiging van automatisch opslaan."
          ],
          "permissions": "Weergavevoorkeuren kunnen persoonlijk zijn. Model-, provider-, beveiligings- en serverwijzigingen vereisen configuratierechten.",
          "limits": "Sommige opties verschijnen alleen als een beheerder ze inschakelt of je browser ze ondersteunt. De opslagmelding bepaalt of de wijziging is toegepast.",
          "example": "Blijf een eerdere alinea lezen terwijl uitvoer doorgaat."
        }
      }
    },
    {
      "id": "webui.settings.render_user_markdown",
      "area": "settings",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.settings.render_user_markdown",
        "#settingsRenderUserMarkdown"
      ],
      "source_refs": [
        "static/index.html:1277"
      ],
      "related": [
        "webui.settings.theme",
        "webui.settings.skin",
        "webui.settings.font_size"
      ],
      "locales": {
        "en": {
          "title": "Markdown in your messages",
          "purpose": "Render supported Markdown formatting in your own messages.",
          "when": "When the current configuration or presentation does not fit the intended workflow.",
          "steps": [
            "Open Settings and find Markdown in your messages.",
            "Choose the desired value; use Save if offered, or wait for autosave confirmation."
          ],
          "permissions": "Appearance preferences can be personal. Model, provider, security and server changes require configuration rights.",
          "limits": "Some options appear only when enabled by an administrator or supported by your browser. Save feedback determines whether the change was applied.",
          "example": "Display a checklist in your request."
        },
        "nl": {
          "title": "Markdown in je eigen berichten",
          "purpose": "Geef ondersteunde Markdown-opmaak in je eigen berichten weer.",
          "when": "Wanneer de huidige instelling of weergave niet past bij de bedoelde werkwijze.",
          "steps": [
            "Open Instellingen en zoek Markdown in je eigen berichten.",
            "Kies de gewenste waarde; gebruik Opslaan indien aangeboden of wacht op bevestiging van automatisch opslaan."
          ],
          "permissions": "Weergavevoorkeuren kunnen persoonlijk zijn. Model-, provider-, beveiligings- en serverwijzigingen vereisen configuratierechten.",
          "limits": "Sommige opties verschijnen alleen als een beheerder ze inschakelt of je browser ze ondersteunt. De opslagmelding bepaalt of de wijziging is toegepast.",
          "example": "Toon een controlelijst in je verzoek."
        }
      }
    },
    {
      "id": "webui.settings.large_text_paste_as_attachment",
      "area": "settings",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.settings.large_text_paste_as_attachment",
        "#settingsLargeTextPasteAsAttachment"
      ],
      "source_refs": [
        "static/index.html:1284"
      ],
      "related": [
        "webui.settings.theme",
        "webui.settings.skin",
        "webui.settings.font_size"
      ],
      "locales": {
        "en": {
          "title": "Large pasted text as attachment",
          "purpose": "Handle a large pasted text block as an attachment when enabled.",
          "when": "When the current configuration or presentation does not fit the intended workflow.",
          "steps": [
            "Open Settings and find Large pasted text as attachment.",
            "Choose the desired value; use Save if offered, or wait for autosave confirmation."
          ],
          "permissions": "Appearance preferences can be personal. Model, provider, security and server changes require configuration rights.",
          "limits": "Some options appear only when enabled by an administrator or supported by your browser. Save feedback determines whether the change was applied.",
          "example": "Keep the composer readable after pasting a long document."
        },
        "nl": {
          "title": "Grote geplakte tekst als bijlage",
          "purpose": "Verwerk een groot geplakt tekstblok als bijlage wanneer ingeschakeld.",
          "when": "Wanneer de huidige instelling of weergave niet past bij de bedoelde werkwijze.",
          "steps": [
            "Open Instellingen en zoek Grote geplakte tekst als bijlage.",
            "Kies de gewenste waarde; gebruik Opslaan indien aangeboden of wacht op bevestiging van automatisch opslaan."
          ],
          "permissions": "Weergavevoorkeuren kunnen persoonlijk zijn. Model-, provider-, beveiligings- en serverwijzigingen vereisen configuratierechten.",
          "limits": "Sommige opties verschijnen alleen als een beheerder ze inschakelt of je browser ze ondersteunt. De opslagmelding bepaalt of de wijziging is toegepast.",
          "example": "Houd het berichtveld leesbaar na het plakken van een lang document."
        }
      }
    },
    {
      "id": "webui.settings.project_quick_create",
      "area": "settings",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.settings.project_quick_create",
        "#settingsProjectQuickCreate"
      ],
      "source_refs": [
        "static/index.html:1291"
      ],
      "related": [
        "webui.settings.theme",
        "webui.settings.skin",
        "webui.settings.font_size"
      ],
      "locales": {
        "en": {
          "title": "Project quick-create controls",
          "purpose": "Show convenient project creation controls.",
          "when": "When the current configuration or presentation does not fit the intended workflow.",
          "steps": [
            "Open Settings and find Project quick-create controls.",
            "Choose the desired value; use Save if offered, or wait for autosave confirmation."
          ],
          "permissions": "Appearance preferences can be personal. Model, provider, security and server changes require configuration rights.",
          "limits": "Some options appear only when enabled by an administrator or supported by your browser. Save feedback determines whether the change was applied.",
          "example": "Start a new project from an available shortcut."
        },
        "nl": {
          "title": "Snelle projectaanmaak",
          "purpose": "Toon handige knoppen voor het snel maken van projecten.",
          "when": "Wanneer de huidige instelling of weergave niet past bij de bedoelde werkwijze.",
          "steps": [
            "Open Instellingen en zoek Snelle projectaanmaak.",
            "Kies de gewenste waarde; gebruik Opslaan indien aangeboden of wacht op bevestiging van automatisch opslaan."
          ],
          "permissions": "Weergavevoorkeuren kunnen persoonlijk zijn. Model-, provider-, beveiligings- en serverwijzigingen vereisen configuratierechten.",
          "limits": "Sommige opties verschijnen alleen als een beheerder ze inschakelt of je browser ze ondersteunt. De opslagmelding bepaalt of de wijziging is toegepast.",
          "example": "Begin een nieuw project via een beschikbare snelkoppeling."
        }
      }
    },
    {
      "id": "webui.settings.structured_code_mode",
      "area": "settings",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.settings.structured_code_mode",
        "#settingsStructuredCodeMode"
      ],
      "source_refs": [
        "static/index.html:1298"
      ],
      "related": [
        "webui.settings.theme",
        "webui.settings.skin",
        "webui.settings.font_size"
      ],
      "locales": {
        "en": {
          "title": "Structured code default view",
          "purpose": "Choose the default tree or code view for supported structured content.",
          "when": "When the current configuration or presentation does not fit the intended workflow.",
          "steps": [
            "Open Settings and find Structured code default view.",
            "Choose the desired value; use Save if offered, or wait for autosave confirmation."
          ],
          "permissions": "Appearance preferences can be personal. Model, provider, security and server changes require configuration rights.",
          "limits": "Some options appear only when enabled by an administrator or supported by your browser. Save feedback determines whether the change was applied.",
          "example": "Read a JSON result as a tree."
        },
        "nl": {
          "title": "Standaardweergave voor gestructureerde code",
          "purpose": "Kies de standaard boom- of codeweergave voor ondersteunde gestructureerde inhoud.",
          "when": "Wanneer de huidige instelling of weergave niet past bij de bedoelde werkwijze.",
          "steps": [
            "Open Instellingen en zoek Standaardweergave voor gestructureerde code.",
            "Kies de gewenste waarde; gebruik Opslaan indien aangeboden of wacht op bevestiging van automatisch opslaan."
          ],
          "permissions": "Weergavevoorkeuren kunnen persoonlijk zijn. Model-, provider-, beveiligings- en serverwijzigingen vereisen configuratierechten.",
          "limits": "Sommige opties verschijnen alleen als een beheerder ze inschakelt of je browser ze ondersteunt. De opslagmelding bepaalt of de wijziging is toegepast.",
          "example": "Lees een JSON-resultaat als boomstructuur."
        }
      }
    },
    {
      "id": "webui.settings.structured_code_auto_lines",
      "area": "settings",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.settings.structured_code_auto_lines",
        "#settingsStructuredCodeAutoLines"
      ],
      "source_refs": [
        "static/index.html:1305"
      ],
      "related": [
        "webui.settings.theme",
        "webui.settings.skin",
        "webui.settings.font_size"
      ],
      "locales": {
        "en": {
          "title": "Structured code size threshold",
          "purpose": "Set the line threshold used by automatic structured-code presentation.",
          "when": "When the current configuration or presentation does not fit the intended workflow.",
          "steps": [
            "Open Settings and find Structured code size threshold.",
            "Choose the desired value; use Save if offered, or wait for autosave confirmation."
          ],
          "permissions": "Appearance preferences can be personal. Model, provider, security and server changes require configuration rights.",
          "limits": "Some options appear only when enabled by an administrator or supported by your browser. Save feedback determines whether the change was applied.",
          "example": "Keep short structured snippets in the simpler view."
        },
        "nl": {
          "title": "Groottegrens voor gestructureerde code",
          "purpose": "Stel de regelgrens in voor automatische weergave van gestructureerde code.",
          "when": "Wanneer de huidige instelling of weergave niet past bij de bedoelde werkwijze.",
          "steps": [
            "Open Instellingen en zoek Groottegrens voor gestructureerde code.",
            "Kies de gewenste waarde; gebruik Opslaan indien aangeboden of wacht op bevestiging van automatisch opslaan."
          ],
          "permissions": "Weergavevoorkeuren kunnen persoonlijk zijn. Model-, provider-, beveiligings- en serverwijzigingen vereisen configuratierechten.",
          "limits": "Sommige opties verschijnen alleen als een beheerder ze inschakelt of je browser ze ondersteunt. De opslagmelding bepaalt of de wijziging is toegepast.",
          "example": "Houd korte gestructureerde fragmenten in de eenvoudigere weergave."
        }
      }
    },
    {
      "id": "webui.settings.show_titlebar_profile",
      "area": "settings",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.settings.show_titlebar_profile",
        "#settingsShowTitlebarProfile"
      ],
      "source_refs": [
        "static/index.html:1311"
      ],
      "related": [
        "webui.settings.theme",
        "webui.settings.skin",
        "webui.settings.font_size"
      ],
      "locales": {
        "en": {
          "title": "Bot name in title bar",
          "purpose": "Show the selected bot identity in the title bar.",
          "when": "When the current configuration or presentation does not fit the intended workflow.",
          "steps": [
            "Open Settings and find Bot name in title bar.",
            "Choose the desired value; use Save if offered, or wait for autosave confirmation."
          ],
          "permissions": "Appearance preferences can be personal. Model, provider, security and server changes require configuration rights.",
          "limits": "Some options appear only when enabled by an administrator or supported by your browser. Save feedback determines whether the change was applied.",
          "example": "Check which bot is active at a glance."
        },
        "nl": {
          "title": "Botnaam in de titelbalk",
          "purpose": "Toon de gekozen botidentiteit in de titelbalk.",
          "when": "Wanneer de huidige instelling of weergave niet past bij de bedoelde werkwijze.",
          "steps": [
            "Open Instellingen en zoek Botnaam in de titelbalk.",
            "Kies de gewenste waarde; gebruik Opslaan indien aangeboden of wacht op bevestiging van automatisch opslaan."
          ],
          "permissions": "Weergavevoorkeuren kunnen persoonlijk zijn. Model-, provider-, beveiligings- en serverwijzigingen vereisen configuratierechten.",
          "limits": "Sommige opties verschijnen alleen als een beheerder ze inschakelt of je browser ze ondersteunt. De opslagmelding bepaalt of de wijziging is toegepast.",
          "example": "Zie direct welke bot actief is."
        }
      }
    },
    {
      "id": "webui.settings.worklog_details_expanded_default",
      "area": "settings",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.settings.worklog_details_expanded_default",
        "#settingsWorklogDetailsExpandedDefault"
      ],
      "source_refs": [
        "static/index.html:1318"
      ],
      "related": [
        "webui.settings.theme",
        "webui.settings.skin",
        "webui.settings.font_size"
      ],
      "locales": {
        "en": {
          "title": "Expand work-log details",
          "purpose": "Choose whether work-log groups initially show their details.",
          "when": "When the current configuration or presentation does not fit the intended workflow.",
          "steps": [
            "Open Settings and find Expand work-log details.",
            "Choose the desired value; use Save if offered, or wait for autosave confirmation."
          ],
          "permissions": "Appearance preferences can be personal. Model, provider, security and server changes require configuration rights.",
          "limits": "Some options appear only when enabled by an administrator or supported by your browser. Save feedback determines whether the change was applied.",
          "example": "Start with tool details open during an investigation."
        },
        "nl": {
          "title": "Werklogdetails uitklappen",
          "purpose": "Kies of werkloggroepen hun details direct tonen.",
          "when": "Wanneer de huidige instelling of weergave niet past bij de bedoelde werkwijze.",
          "steps": [
            "Open Instellingen en zoek Werklogdetails uitklappen.",
            "Kies de gewenste waarde; gebruik Opslaan indien aangeboden of wacht op bevestiging van automatisch opslaan."
          ],
          "permissions": "Weergavevoorkeuren kunnen persoonlijk zijn. Model-, provider-, beveiligings- en serverwijzigingen vereisen configuratierechten.",
          "limits": "Sommige opties verschijnen alleen als een beheerder ze inschakelt of je browser ze ondersteunt. De opslagmelding bepaalt of de wijziging is toegepast.",
          "example": "Begin met geopende tooldetails tijdens onderzoek."
        }
      }
    },
    {
      "id": "webui.settings.advanced_chat_controls",
      "area": "settings",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.settings.advanced_chat_controls",
        "#settingsAdvancedChatControls"
      ],
      "source_refs": [
        "static/index.html:1329"
      ],
      "related": [
        "webui.settings.theme",
        "webui.settings.skin",
        "webui.settings.font_size"
      ],
      "locales": {
        "en": {
          "title": "Advanced chat controls",
          "purpose": "Expose additional composer controls without changing their permissions.",
          "when": "When the current configuration or presentation does not fit the intended workflow.",
          "steps": [
            "Open Settings and find Advanced chat controls.",
            "Choose the desired value; use Save if offered, or wait for autosave confirmation."
          ],
          "permissions": "Appearance preferences can be personal. Model, provider, security and server changes require configuration rights.",
          "limits": "Some options appear only when enabled by an administrator or supported by your browser. Save feedback determines whether the change was applied.",
          "example": "Make advanced conversation options easier to reach."
        },
        "nl": {
          "title": "Geavanceerde chatbediening",
          "purpose": "Toon extra berichtopties zonder hun rechten te wijzigen.",
          "when": "Wanneer de huidige instelling of weergave niet past bij de bedoelde werkwijze.",
          "steps": [
            "Open Instellingen en zoek Geavanceerde chatbediening.",
            "Kies de gewenste waarde; gebruik Opslaan indien aangeboden of wacht op bevestiging van automatisch opslaan."
          ],
          "permissions": "Weergavevoorkeuren kunnen persoonlijk zijn. Model-, provider-, beveiligings- en serverwijzigingen vereisen configuratierechten.",
          "limits": "Sommige opties verschijnen alleen als een beheerder ze inschakelt of je browser ze ondersteunt. De opslagmelding bepaalt of de wijziging is toegepast.",
          "example": "Maak geavanceerde gespreksopties beter bereikbaar."
        }
      }
    },
    {
      "id": "webui.settings.model",
      "area": "settings",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.settings.model",
        "#settingsModel"
      ],
      "source_refs": [
        "static/index.html:1374"
      ],
      "related": [
        "webui.settings.theme",
        "webui.settings.skin",
        "webui.settings.font_size"
      ],
      "locales": {
        "en": {
          "title": "Default conversation model",
          "purpose": "Set the configured default model where your configuration rights allow it.",
          "when": "When the current configuration or presentation does not fit the intended workflow.",
          "steps": [
            "Open Settings and find Default conversation model.",
            "Choose the desired value; use Save if offered, or wait for autosave confirmation."
          ],
          "permissions": "Appearance preferences can be personal. Model, provider, security and server changes require configuration rights.",
          "limits": "Some options appear only when enabled by an administrator or supported by your browser. Save feedback determines whether the change was applied.",
          "example": "Choose the default model for new work."
        },
        "nl": {
          "title": "Standaard gespreksmodel",
          "purpose": "Stel het standaardmodel in wanneer je configuratierechten dit toelaten.",
          "when": "Wanneer de huidige instelling of weergave niet past bij de bedoelde werkwijze.",
          "steps": [
            "Open Instellingen en zoek Standaard gespreksmodel.",
            "Kies de gewenste waarde; gebruik Opslaan indien aangeboden of wacht op bevestiging van automatisch opslaan."
          ],
          "permissions": "Weergavevoorkeuren kunnen persoonlijk zijn. Model-, provider-, beveiligings- en serverwijzigingen vereisen configuratierechten.",
          "limits": "Sommige opties verschijnen alleen als een beheerder ze inschakelt of je browser ze ondersteunt. De opslagmelding bepaalt of de wijziging is toegepast.",
          "example": "Kies het standaardmodel voor nieuw werk."
        }
      }
    },
    {
      "id": "webui.settings.hide_suggestions",
      "area": "settings",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.settings.hide_suggestions",
        "#settingsHideSuggestions"
      ],
      "source_refs": [
        "static/index.html:1391"
      ],
      "related": [
        "webui.settings.theme",
        "webui.settings.skin",
        "webui.settings.font_size"
      ],
      "locales": {
        "en": {
          "title": "Hide prompt suggestions",
          "purpose": "Show or hide suggested starter prompts.",
          "when": "When the current configuration or presentation does not fit the intended workflow.",
          "steps": [
            "Open Settings and find Hide prompt suggestions.",
            "Choose the desired value; use Save if offered, or wait for autosave confirmation."
          ],
          "permissions": "Appearance preferences can be personal. Model, provider, security and server changes require configuration rights.",
          "limits": "Some options appear only when enabled by an administrator or supported by your browser. Save feedback determines whether the change was applied.",
          "example": "Keep the empty chat screen uncluttered."
        },
        "nl": {
          "title": "Promptsuggesties verbergen",
          "purpose": "Toon of verberg voorgestelde startprompts.",
          "when": "Wanneer de huidige instelling of weergave niet past bij de bedoelde werkwijze.",
          "steps": [
            "Open Instellingen en zoek Promptsuggesties verbergen.",
            "Kies de gewenste waarde; gebruik Opslaan indien aangeboden of wacht op bevestiging van automatisch opslaan."
          ],
          "permissions": "Weergavevoorkeuren kunnen persoonlijk zijn. Model-, provider-, beveiligings- en serverwijzigingen vereisen configuratierechten.",
          "limits": "Sommige opties verschijnen alleen als een beheerder ze inschakelt of je browser ze ondersteunt. De opslagmelding bepaalt of de wijziging is toegepast.",
          "example": "Houd het lege chatscherm rustig."
        }
      }
    },
    {
      "id": "webui.settings.hide_empty_state_panel",
      "area": "settings",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.settings.hide_empty_state_panel",
        "#settingsHideEmptyStatePanel"
      ],
      "source_refs": [
        "static/index.html:1398"
      ],
      "related": [
        "webui.settings.theme",
        "webui.settings.skin",
        "webui.settings.font_size"
      ],
      "locales": {
        "en": {
          "title": "Hide empty-chat introduction",
          "purpose": "Show or hide the empty-conversation introduction panel.",
          "when": "When the current configuration or presentation does not fit the intended workflow.",
          "steps": [
            "Open Settings and find Hide empty-chat introduction.",
            "Choose the desired value; use Save if offered, or wait for autosave confirmation."
          ],
          "permissions": "Appearance preferences can be personal. Model, provider, security and server changes require configuration rights.",
          "limits": "Some options appear only when enabled by an administrator or supported by your browser. Save feedback determines whether the change was applied.",
          "example": "Use a minimal starting screen."
        },
        "nl": {
          "title": "Introductie in lege chat verbergen",
          "purpose": "Toon of verberg het introductiepaneel van een leeg gesprek.",
          "when": "Wanneer de huidige instelling of weergave niet past bij de bedoelde werkwijze.",
          "steps": [
            "Open Instellingen en zoek Introductie in lege chat verbergen.",
            "Kies de gewenste waarde; gebruik Opslaan indien aangeboden of wacht op bevestiging van automatisch opslaan."
          ],
          "permissions": "Weergavevoorkeuren kunnen persoonlijk zijn. Model-, provider-, beveiligings- en serverwijzigingen vereisen configuratierechten.",
          "limits": "Sommige opties verschijnen alleen als een beheerder ze inschakelt of je browser ze ondersteunt. De opslagmelding bepaalt of de wijziging is toegepast.",
          "example": "Gebruik een minimaal startscherm."
        }
      }
    },
    {
      "id": "webui.settings.virtualize_transcript",
      "area": "settings",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.settings.virtualize_transcript",
        "#settingsVirtualizeTranscript"
      ],
      "source_refs": [
        "static/index.html:1405"
      ],
      "related": [
        "webui.settings.theme",
        "webui.settings.skin",
        "webui.settings.font_size"
      ],
      "locales": {
        "en": {
          "title": "Long-transcript rendering",
          "purpose": "Use supported transcript virtualization to reduce rendering work.",
          "when": "When the current configuration or presentation does not fit the intended workflow.",
          "steps": [
            "Open Settings and find Long-transcript rendering.",
            "Choose the desired value; use Save if offered, or wait for autosave confirmation."
          ],
          "permissions": "Appearance preferences can be personal. Model, provider, security and server changes require configuration rights.",
          "limits": "Some options appear only when enabled by an administrator or supported by your browser. Save feedback determines whether the change was applied.",
          "example": "Improve responsiveness with a very long conversation."
        },
        "nl": {
          "title": "Lange gesprekken efficiënt weergeven",
          "purpose": "Gebruik ondersteunde virtualisatie om minder gespreksinhoud tegelijk weer te geven.",
          "when": "Wanneer de huidige instelling of weergave niet past bij de bedoelde werkwijze.",
          "steps": [
            "Open Instellingen en zoek Lange gesprekken efficiënt weergeven.",
            "Kies de gewenste waarde; gebruik Opslaan indien aangeboden of wacht op bevestiging van automatisch opslaan."
          ],
          "permissions": "Weergavevoorkeuren kunnen persoonlijk zijn. Model-, provider-, beveiligings- en serverwijzigingen vereisen configuratierechten.",
          "limits": "Sommige opties verschijnen alleen als een beheerder ze inschakelt of je browser ze ondersteunt. De opslagmelding bepaalt of de wijziging is toegepast.",
          "example": "Verbeter de reactiesnelheid bij een zeer lang gesprek."
        }
      }
    },
    {
      "id": "webui.settings.send_key",
      "area": "settings",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.settings.send_key",
        "#settingsSendKey"
      ],
      "source_refs": [
        "static/index.html:1412"
      ],
      "related": [
        "webui.settings.theme",
        "webui.settings.skin",
        "webui.settings.font_size"
      ],
      "locales": {
        "en": {
          "title": "Send keyboard shortcut",
          "purpose": "Choose which key combination sends a message.",
          "when": "When the current configuration or presentation does not fit the intended workflow.",
          "steps": [
            "Open Settings and find Send keyboard shortcut.",
            "Choose the desired value; use Save if offered, or wait for autosave confirmation."
          ],
          "permissions": "Appearance preferences can be personal. Model, provider, security and server changes require configuration rights.",
          "limits": "Some options appear only when enabled by an administrator or supported by your browser. Save feedback determines whether the change was applied.",
          "example": "Use Enter for new lines and a modifier to send."
        },
        "nl": {
          "title": "Sneltoets voor versturen",
          "purpose": "Kies welke toetsencombinatie een bericht verstuurt.",
          "when": "Wanneer de huidige instelling of weergave niet past bij de bedoelde werkwijze.",
          "steps": [
            "Open Instellingen en zoek Sneltoets voor versturen.",
            "Kies de gewenste waarde; gebruik Opslaan indien aangeboden of wacht op bevestiging van automatisch opslaan."
          ],
          "permissions": "Weergavevoorkeuren kunnen persoonlijk zijn. Model-, provider-, beveiligings- en serverwijzigingen vereisen configuratierechten.",
          "limits": "Sommige opties verschijnen alleen als een beheerder ze inschakelt of je browser ze ondersteunt. De opslagmelding bepaalt of de wijziging is toegepast.",
          "example": "Gebruik Enter voor nieuwe regels en een extra toets om te versturen."
        }
      }
    },
    {
      "id": "webui.settings.language",
      "area": "settings",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.settings.language",
        "#settingsLanguage"
      ],
      "source_refs": [
        "static/index.html:1420"
      ],
      "related": [
        "webui.settings.theme",
        "webui.settings.skin",
        "webui.settings.font_size"
      ],
      "locales": {
        "en": {
          "title": "Interface language",
          "purpose": "Choose an available interface language; this guide also has its own Dutch and English selector.",
          "when": "When the current configuration or presentation does not fit the intended workflow.",
          "steps": [
            "Open Settings and find Interface language.",
            "Choose the desired value; use Save if offered, or wait for autosave confirmation."
          ],
          "permissions": "Appearance preferences can be personal. Model, provider, security and server changes require configuration rights.",
          "limits": "Some options appear only when enabled by an administrator or supported by your browser. Save feedback determines whether the change was applied.",
          "example": "Read the guide in Dutch while using an English interface."
        },
        "nl": {
          "title": "Interfacetaal",
          "purpose": "Kies een beschikbare interfacetaal; deze gids heeft daarnaast een eigen Nederlandse en Engelse taalkiezer.",
          "when": "Wanneer de huidige instelling of weergave niet past bij de bedoelde werkwijze.",
          "steps": [
            "Open Instellingen en zoek Interfacetaal.",
            "Kies de gewenste waarde; gebruik Opslaan indien aangeboden of wacht op bevestiging van automatisch opslaan."
          ],
          "permissions": "Weergavevoorkeuren kunnen persoonlijk zijn. Model-, provider-, beveiligings- en serverwijzigingen vereisen configuratierechten.",
          "limits": "Sommige opties verschijnen alleen als een beheerder ze inschakelt of je browser ze ondersteunt. De opslagmelding bepaalt of de wijziging is toegepast.",
          "example": "Lees de gids in het Nederlands bij een Engelse interface."
        }
      }
    },
    {
      "id": "webui.settings.rtl",
      "area": "settings",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.settings.rtl",
        "#settingsRtl"
      ],
      "source_refs": [
        "static/index.html:1424"
      ],
      "related": [
        "webui.settings.theme",
        "webui.settings.skin",
        "webui.settings.font_size"
      ],
      "locales": {
        "en": {
          "title": "Right-to-left layout",
          "purpose": "Select the supported direction for interface text and layout.",
          "when": "When the current configuration or presentation does not fit the intended workflow.",
          "steps": [
            "Open Settings and find Right-to-left layout.",
            "Choose the desired value; use Save if offered, or wait for autosave confirmation."
          ],
          "permissions": "Appearance preferences can be personal. Model, provider, security and server changes require configuration rights.",
          "limits": "Some options appear only when enabled by an administrator or supported by your browser. Save feedback determines whether the change was applied.",
          "example": "Use the interface with right-to-left text."
        },
        "nl": {
          "title": "Indeling van rechts naar links",
          "purpose": "Kies de ondersteunde richting van interfacetekst en indeling.",
          "when": "Wanneer de huidige instelling of weergave niet past bij de bedoelde werkwijze.",
          "steps": [
            "Open Instellingen en zoek Indeling van rechts naar links.",
            "Kies de gewenste waarde; gebruik Opslaan indien aangeboden of wacht op bevestiging van automatisch opslaan."
          ],
          "permissions": "Weergavevoorkeuren kunnen persoonlijk zijn. Model-, provider-, beveiligings- en serverwijzigingen vereisen configuratierechten.",
          "limits": "Sommige opties verschijnen alleen als een beheerder ze inschakelt of je browser ze ondersteunt. De opslagmelding bepaalt of de wijziging is toegepast.",
          "example": "Gebruik de interface met tekst van rechts naar links."
        }
      }
    },
    {
      "id": "webui.settings.sound_enabled",
      "area": "settings",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.settings.sound_enabled",
        "#settingsSoundEnabled"
      ],
      "source_refs": [
        "static/index.html:1431"
      ],
      "related": [
        "webui.settings.theme",
        "webui.settings.skin",
        "webui.settings.font_size"
      ],
      "locales": {
        "en": {
          "title": "Interface sounds",
          "purpose": "Enable or disable supported interface sound cues.",
          "when": "When the current configuration or presentation does not fit the intended workflow.",
          "steps": [
            "Open Settings and find Interface sounds.",
            "Choose the desired value; use Save if offered, or wait for autosave confirmation."
          ],
          "permissions": "Appearance preferences can be personal. Model, provider, security and server changes require configuration rights.",
          "limits": "Some options appear only when enabled by an administrator or supported by your browser. Save feedback determines whether the change was applied.",
          "example": "Mute interface sounds during a meeting."
        },
        "nl": {
          "title": "Interfacegeluiden",
          "purpose": "Schakel ondersteunde geluidssignalen van de interface in of uit.",
          "when": "Wanneer de huidige instelling of weergave niet past bij de bedoelde werkwijze.",
          "steps": [
            "Open Instellingen en zoek Interfacegeluiden.",
            "Kies de gewenste waarde; gebruik Opslaan indien aangeboden of wacht op bevestiging van automatisch opslaan."
          ],
          "permissions": "Weergavevoorkeuren kunnen persoonlijk zijn. Model-, provider-, beveiligings- en serverwijzigingen vereisen configuratierechten.",
          "limits": "Sommige opties verschijnen alleen als een beheerder ze inschakelt of je browser ze ondersteunt. De opslagmelding bepaalt of de wijziging is toegepast.",
          "example": "Demp interfacegeluiden tijdens een vergadering."
        }
      }
    },
    {
      "id": "webui.settings.tts_enabled",
      "area": "settings",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.settings.tts_enabled",
        "#settingsTtsEnabled"
      ],
      "source_refs": [
        "static/index.html:1438"
      ],
      "related": [
        "webui.settings.theme",
        "webui.settings.skin",
        "webui.settings.font_size"
      ],
      "locales": {
        "en": {
          "title": "Speech output enabled",
          "purpose": "Enable supported text-to-speech playback controls.",
          "when": "When the current configuration or presentation does not fit the intended workflow.",
          "steps": [
            "Open Settings and find Speech output enabled.",
            "Choose the desired value; use Save if offered, or wait for autosave confirmation."
          ],
          "permissions": "Appearance preferences can be personal. Model, provider, security and server changes require configuration rights.",
          "limits": "Some options appear only when enabled by an administrator or supported by your browser. Save feedback determines whether the change was applied.",
          "example": "Listen to a response when speech is configured."
        },
        "nl": {
          "title": "Spraakuitvoer inschakelen",
          "purpose": "Schakel ondersteunde knoppen voor tekst-naar-spraak in.",
          "when": "Wanneer de huidige instelling of weergave niet past bij de bedoelde werkwijze.",
          "steps": [
            "Open Instellingen en zoek Spraakuitvoer inschakelen.",
            "Kies de gewenste waarde; gebruik Opslaan indien aangeboden of wacht op bevestiging van automatisch opslaan."
          ],
          "permissions": "Weergavevoorkeuren kunnen persoonlijk zijn. Model-, provider-, beveiligings- en serverwijzigingen vereisen configuratierechten.",
          "limits": "Sommige opties verschijnen alleen als een beheerder ze inschakelt of je browser ze ondersteunt. De opslagmelding bepaalt of de wijziging is toegepast.",
          "example": "Luister naar een antwoord wanneer spraak is ingesteld."
        }
      }
    },
    {
      "id": "webui.settings.tts_auto_read",
      "area": "settings",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.settings.tts_auto_read",
        "#settingsTtsAutoRead"
      ],
      "source_refs": [
        "static/index.html:1445"
      ],
      "related": [
        "webui.settings.theme",
        "webui.settings.skin",
        "webui.settings.font_size"
      ],
      "locales": {
        "en": {
          "title": "Automatically read responses",
          "purpose": "Choose whether eligible responses start speech playback automatically.",
          "when": "When the current configuration or presentation does not fit the intended workflow.",
          "steps": [
            "Open Settings and find Automatically read responses.",
            "Choose the desired value; use Save if offered, or wait for autosave confirmation."
          ],
          "permissions": "Appearance preferences can be personal. Model, provider, security and server changes require configuration rights.",
          "limits": "Some options appear only when enabled by an administrator or supported by your browser. Save feedback determines whether the change was applied.",
          "example": "Keep automatic speech off in a shared office."
        },
        "nl": {
          "title": "Antwoorden automatisch voorlezen",
          "purpose": "Kies of geschikte antwoorden automatisch worden voorgelezen.",
          "when": "Wanneer de huidige instelling of weergave niet past bij de bedoelde werkwijze.",
          "steps": [
            "Open Instellingen en zoek Antwoorden automatisch voorlezen.",
            "Kies de gewenste waarde; gebruik Opslaan indien aangeboden of wacht op bevestiging van automatisch opslaan."
          ],
          "permissions": "Weergavevoorkeuren kunnen persoonlijk zijn. Model-, provider-, beveiligings- en serverwijzigingen vereisen configuratierechten.",
          "limits": "Sommige opties verschijnen alleen als een beheerder ze inschakelt of je browser ze ondersteunt. De opslagmelding bepaalt of de wijziging is toegepast.",
          "example": "Houd automatisch voorlezen uit in een gedeeld kantoor."
        }
      }
    },
    {
      "id": "webui.settings.voice_mode_enabled",
      "area": "settings",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.settings.voice_mode_enabled",
        "#settingsVoiceModeEnabled"
      ],
      "source_refs": [
        "static/index.html:1452"
      ],
      "related": [
        "webui.settings.theme",
        "webui.settings.skin",
        "webui.settings.font_size"
      ],
      "locales": {
        "en": {
          "title": "Voice mode availability",
          "purpose": "Enable the supported voice interaction option.",
          "when": "When the current configuration or presentation does not fit the intended workflow.",
          "steps": [
            "Open Settings and find Voice mode availability.",
            "Choose the desired value; use Save if offered, or wait for autosave confirmation."
          ],
          "permissions": "Appearance preferences can be personal. Model, provider, security and server changes require configuration rights.",
          "limits": "Some options appear only when enabled by an administrator or supported by your browser. Save feedback determines whether the change was applied.",
          "example": "Expose voice mode on a configured installation."
        },
        "nl": {
          "title": "Beschikbaarheid van spraakmodus",
          "purpose": "Schakel de ondersteunde spraakinteractieoptie in.",
          "when": "Wanneer de huidige instelling of weergave niet past bij de bedoelde werkwijze.",
          "steps": [
            "Open Instellingen en zoek Beschikbaarheid van spraakmodus.",
            "Kies de gewenste waarde; gebruik Opslaan indien aangeboden of wacht op bevestiging van automatisch opslaan."
          ],
          "permissions": "Weergavevoorkeuren kunnen persoonlijk zijn. Model-, provider-, beveiligings- en serverwijzigingen vereisen configuratierechten.",
          "limits": "Sommige opties verschijnen alleen als een beheerder ze inschakelt of je browser ze ondersteunt. De opslagmelding bepaalt of de wijziging is toegepast.",
          "example": "Toon spraakmodus op een ingestelde installatie."
        }
      }
    },
    {
      "id": "webui.settings.raw_audio",
      "area": "settings",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.settings.raw_audio",
        "#settingsRawAudio"
      ],
      "source_refs": [
        "static/index.html:1459"
      ],
      "related": [
        "webui.settings.theme",
        "webui.settings.skin",
        "webui.settings.font_size"
      ],
      "locales": {
        "en": {
          "title": "Raw audio input",
          "purpose": "Choose the offered raw-audio input behavior where supported.",
          "when": "When the current configuration or presentation does not fit the intended workflow.",
          "steps": [
            "Open Settings and find Raw audio input.",
            "Choose the desired value; use Save if offered, or wait for autosave confirmation."
          ],
          "permissions": "Appearance preferences can be personal. Model, provider, security and server changes require configuration rights.",
          "limits": "Some options appear only when enabled by an administrator or supported by your browser. Save feedback determines whether the change was applied.",
          "example": "Use the configured audio input path for a supported model."
        },
        "nl": {
          "title": "Ruwe audio-invoer",
          "purpose": "Kies het aangeboden gedrag voor ruwe audio-invoer waar ondersteund.",
          "when": "Wanneer de huidige instelling of weergave niet past bij de bedoelde werkwijze.",
          "steps": [
            "Open Instellingen en zoek Ruwe audio-invoer.",
            "Kies de gewenste waarde; gebruik Opslaan indien aangeboden of wacht op bevestiging van automatisch opslaan."
          ],
          "permissions": "Weergavevoorkeuren kunnen persoonlijk zijn. Model-, provider-, beveiligings- en serverwijzigingen vereisen configuratierechten.",
          "limits": "Sommige opties verschijnen alleen als een beheerder ze inschakelt of je browser ze ondersteunt. De opslagmelding bepaalt of de wijziging is toegepast.",
          "example": "Gebruik het ingestelde audiopad voor een ondersteund model."
        }
      }
    },
    {
      "id": "webui.settings.dictation_append",
      "area": "settings",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.settings.dictation_append",
        "#settingsDictationAppend"
      ],
      "source_refs": [
        "static/index.html:1466"
      ],
      "related": [
        "webui.settings.theme",
        "webui.settings.skin",
        "webui.settings.font_size"
      ],
      "locales": {
        "en": {
          "title": "Append dictated text",
          "purpose": "Choose whether dictated text is added to the existing draft.",
          "when": "When the current configuration or presentation does not fit the intended workflow.",
          "steps": [
            "Open Settings and find Append dictated text.",
            "Choose the desired value; use Save if offered, or wait for autosave confirmation."
          ],
          "permissions": "Appearance preferences can be personal. Model, provider, security and server changes require configuration rights.",
          "limits": "Some options appear only when enabled by an administrator or supported by your browser. Save feedback determines whether the change was applied.",
          "example": "Add one spoken sentence to a typed draft."
        },
        "nl": {
          "title": "Gedicteerde tekst toevoegen",
          "purpose": "Kies of gedicteerde tekst aan het bestaande concept wordt toegevoegd.",
          "when": "Wanneer de huidige instelling of weergave niet past bij de bedoelde werkwijze.",
          "steps": [
            "Open Instellingen en zoek Gedicteerde tekst toevoegen.",
            "Kies de gewenste waarde; gebruik Opslaan indien aangeboden of wacht op bevestiging van automatisch opslaan."
          ],
          "permissions": "Weergavevoorkeuren kunnen persoonlijk zijn. Model-, provider-, beveiligings- en serverwijzigingen vereisen configuratierechten.",
          "limits": "Sommige opties verschijnen alleen als een beheerder ze inschakelt of je browser ze ondersteunt. De opslagmelding bepaalt of de wijziging is toegepast.",
          "example": "Voeg een gesproken zin toe aan een getypt concept."
        }
      }
    },
    {
      "id": "webui.settings.tts_engine",
      "area": "settings",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.settings.tts_engine",
        "#settingsTtsEngine"
      ],
      "source_refs": [
        "static/index.html:1472"
      ],
      "related": [
        "webui.settings.theme",
        "webui.settings.skin",
        "webui.settings.font_size"
      ],
      "locales": {
        "en": {
          "title": "Speech engine",
          "purpose": "Choose an available browser or provider speech engine.",
          "when": "When the current configuration or presentation does not fit the intended workflow.",
          "steps": [
            "Open Settings and find Speech engine.",
            "Choose the desired value; use Save if offered, or wait for autosave confirmation."
          ],
          "permissions": "Appearance preferences can be personal. Model, provider, security and server changes require configuration rights.",
          "limits": "Some options appear only when enabled by an administrator or supported by your browser. Save feedback determines whether the change was applied.",
          "example": "Select a speech engine supported by your installation."
        },
        "nl": {
          "title": "Spraakengine",
          "purpose": "Kies een beschikbare browser- of providerspraakengine.",
          "when": "Wanneer de huidige instelling of weergave niet past bij de bedoelde werkwijze.",
          "steps": [
            "Open Instellingen en zoek Spraakengine.",
            "Kies de gewenste waarde; gebruik Opslaan indien aangeboden of wacht op bevestiging van automatisch opslaan."
          ],
          "permissions": "Weergavevoorkeuren kunnen persoonlijk zijn. Model-, provider-, beveiligings- en serverwijzigingen vereisen configuratierechten.",
          "limits": "Sommige opties verschijnen alleen als een beheerder ze inschakelt of je browser ze ondersteunt. De opslagmelding bepaalt of de wijziging is toegepast.",
          "example": "Kies een spraakengine die je installatie ondersteunt."
        }
      }
    },
    {
      "id": "webui.settings.tts_voice",
      "area": "settings",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.settings.tts_voice",
        "#settingsTtsVoice"
      ],
      "source_refs": [
        "static/index.html:1473"
      ],
      "related": [
        "webui.settings.theme",
        "webui.settings.skin",
        "webui.settings.font_size"
      ],
      "locales": {
        "en": {
          "title": "Speech voice",
          "purpose": "Choose a voice offered by the selected speech engine.",
          "when": "When the current configuration or presentation does not fit the intended workflow.",
          "steps": [
            "Open Settings and find Speech voice.",
            "Choose the desired value; use Save if offered, or wait for autosave confirmation."
          ],
          "permissions": "Appearance preferences can be personal. Model, provider, security and server changes require configuration rights.",
          "limits": "Some options appear only when enabled by an administrator or supported by your browser. Save feedback determines whether the change was applied.",
          "example": "Use a voice suitable for the response language."
        },
        "nl": {
          "title": "Voorleesstem",
          "purpose": "Kies een stem die de gekozen spraakengine aanbiedt.",
          "when": "Wanneer de huidige instelling of weergave niet past bij de bedoelde werkwijze.",
          "steps": [
            "Open Instellingen en zoek Voorleesstem.",
            "Kies de gewenste waarde; gebruik Opslaan indien aangeboden of wacht op bevestiging van automatisch opslaan."
          ],
          "permissions": "Weergavevoorkeuren kunnen persoonlijk zijn. Model-, provider-, beveiligings- en serverwijzigingen vereisen configuratierechten.",
          "limits": "Sommige opties verschijnen alleen als een beheerder ze inschakelt of je browser ze ondersteunt. De opslagmelding bepaalt of de wijziging is toegepast.",
          "example": "Gebruik een stem die past bij de antwoordtaal."
        }
      }
    },
    {
      "id": "webui.settings.tts_rate",
      "area": "settings",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.settings.tts_rate",
        "#settingsTtsRate"
      ],
      "source_refs": [
        "static/index.html:1481"
      ],
      "related": [
        "webui.settings.theme",
        "webui.settings.skin",
        "webui.settings.font_size"
      ],
      "locales": {
        "en": {
          "title": "Speech rate",
          "purpose": "Adjust the supported speaking speed.",
          "when": "When the current configuration or presentation does not fit the intended workflow.",
          "steps": [
            "Open Settings and find Speech rate.",
            "Choose the desired value; use Save if offered, or wait for autosave confirmation."
          ],
          "permissions": "Appearance preferences can be personal. Model, provider, security and server changes require configuration rights.",
          "limits": "Some options appear only when enabled by an administrator or supported by your browser. Save feedback determines whether the change was applied.",
          "example": "Slow down a technical explanation."
        },
        "nl": {
          "title": "Voorleessnelheid",
          "purpose": "Pas de ondersteunde spreeksnelheid aan.",
          "when": "Wanneer de huidige instelling of weergave niet past bij de bedoelde werkwijze.",
          "steps": [
            "Open Instellingen en zoek Voorleessnelheid.",
            "Kies de gewenste waarde; gebruik Opslaan indien aangeboden of wacht op bevestiging van automatisch opslaan."
          ],
          "permissions": "Weergavevoorkeuren kunnen persoonlijk zijn. Model-, provider-, beveiligings- en serverwijzigingen vereisen configuratierechten.",
          "limits": "Sommige opties verschijnen alleen als een beheerder ze inschakelt of je browser ze ondersteunt. De opslagmelding bepaalt of de wijziging is toegepast.",
          "example": "Vertraag een technische uitleg."
        }
      }
    },
    {
      "id": "webui.settings.tts_pitch",
      "area": "settings",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.settings.tts_pitch",
        "#settingsTtsPitch"
      ],
      "source_refs": [
        "static/index.html:1488"
      ],
      "related": [
        "webui.settings.theme",
        "webui.settings.skin",
        "webui.settings.font_size"
      ],
      "locales": {
        "en": {
          "title": "Speech pitch",
          "purpose": "Adjust voice pitch where the speech engine supports it.",
          "when": "When the current configuration or presentation does not fit the intended workflow.",
          "steps": [
            "Open Settings and find Speech pitch.",
            "Choose the desired value; use Save if offered, or wait for autosave confirmation."
          ],
          "permissions": "Appearance preferences can be personal. Model, provider, security and server changes require configuration rights.",
          "limits": "Some options appear only when enabled by an administrator or supported by your browser. Save feedback determines whether the change was applied.",
          "example": "Choose a comfortable voice pitch."
        },
        "nl": {
          "title": "Toonhoogte van de stem",
          "purpose": "Pas de toonhoogte aan wanneer de spraakengine dit ondersteunt.",
          "when": "Wanneer de huidige instelling of weergave niet past bij de bedoelde werkwijze.",
          "steps": [
            "Open Instellingen en zoek Toonhoogte van de stem.",
            "Kies de gewenste waarde; gebruik Opslaan indien aangeboden of wacht op bevestiging van automatisch opslaan."
          ],
          "permissions": "Weergavevoorkeuren kunnen persoonlijk zijn. Model-, provider-, beveiligings- en serverwijzigingen vereisen configuratierechten.",
          "limits": "Sommige opties verschijnen alleen als een beheerder ze inschakelt of je browser ze ondersteunt. De opslagmelding bepaalt of de wijziging is toegepast.",
          "example": "Kies een prettige toonhoogte."
        }
      }
    },
    {
      "id": "webui.settings.notifications_enabled",
      "area": "settings",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.settings.notifications_enabled",
        "#settingsNotificationsEnabled"
      ],
      "source_refs": [
        "static/index.html:1494"
      ],
      "related": [
        "webui.settings.theme",
        "webui.settings.skin",
        "webui.settings.font_size"
      ],
      "locales": {
        "en": {
          "title": "Browser notifications",
          "purpose": "Enable eligible browser notifications after browser permission is granted.",
          "when": "When the current configuration or presentation does not fit the intended workflow.",
          "steps": [
            "Open Settings and find Browser notifications.",
            "Choose the desired value; use Save if offered, or wait for autosave confirmation."
          ],
          "permissions": "Appearance preferences can be personal. Model, provider, security and server changes require configuration rights.",
          "limits": "Some options appear only when enabled by an administrator or supported by your browser. Save feedback determines whether the change was applied.",
          "example": "Receive a notification when a response completes."
        },
        "nl": {
          "title": "Browsermeldingen",
          "purpose": "Schakel geschikte browsermeldingen in nadat de browser toestemming geeft.",
          "when": "Wanneer de huidige instelling of weergave niet past bij de bedoelde werkwijze.",
          "steps": [
            "Open Instellingen en zoek Browsermeldingen.",
            "Kies de gewenste waarde; gebruik Opslaan indien aangeboden of wacht op bevestiging van automatisch opslaan."
          ],
          "permissions": "Weergavevoorkeuren kunnen persoonlijk zijn. Model-, provider-, beveiligings- en serverwijzigingen vereisen configuratierechten.",
          "limits": "Sommige opties verschijnen alleen als een beheerder ze inschakelt of je browser ze ondersteunt. De opslagmelding bepaalt of de wijziging is toegepast.",
          "example": "Ontvang een melding wanneer een antwoord gereed is."
        }
      }
    },
    {
      "id": "webui.settings.show_token_usage",
      "area": "settings",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.settings.show_token_usage",
        "#settingsShowTokenUsage"
      ],
      "source_refs": [
        "static/index.html:1508"
      ],
      "related": [
        "webui.settings.theme",
        "webui.settings.skin",
        "webui.settings.font_size"
      ],
      "locales": {
        "en": {
          "title": "Token usage display",
          "purpose": "Show available token usage information for conversations.",
          "when": "When the current configuration or presentation does not fit the intended workflow.",
          "steps": [
            "Open Settings and find Token usage display.",
            "Choose the desired value; use Save if offered, or wait for autosave confirmation."
          ],
          "permissions": "Appearance preferences can be personal. Model, provider, security and server changes require configuration rights.",
          "limits": "Some options appear only when enabled by an administrator or supported by your browser. Save feedback determines whether the change was applied.",
          "example": "Inspect the size of a model exchange."
        },
        "nl": {
          "title": "Tokengebruik tonen",
          "purpose": "Toon beschikbare informatie over tokengebruik bij gesprekken.",
          "when": "Wanneer de huidige instelling of weergave niet past bij de bedoelde werkwijze.",
          "steps": [
            "Open Instellingen en zoek Tokengebruik tonen.",
            "Kies de gewenste waarde; gebruik Opslaan indien aangeboden of wacht op bevestiging van automatisch opslaan."
          ],
          "permissions": "Weergavevoorkeuren kunnen persoonlijk zijn. Model-, provider-, beveiligings- en serverwijzigingen vereisen configuratierechten.",
          "limits": "Sommige opties verschijnen alleen als een beheerder ze inschakelt of je browser ze ondersteunt. De opslagmelding bepaalt of de wijziging is toegepast.",
          "example": "Bekijk de omvang van een modeluitwisseling."
        }
      }
    },
    {
      "id": "webui.settings.max_tokens",
      "area": "settings",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.settings.max_tokens",
        "#settingsMaxTokens"
      ],
      "source_refs": [
        "static/index.html:1516"
      ],
      "related": [
        "webui.settings.theme",
        "webui.settings.skin",
        "webui.settings.font_size"
      ],
      "locales": {
        "en": {
          "title": "Maximum output token override",
          "purpose": "Set an optional output-token limit supported by the selected model.",
          "when": "When the current configuration or presentation does not fit the intended workflow.",
          "steps": [
            "Open Settings and find Maximum output token override.",
            "Choose the desired value; use Save if offered, or wait for autosave confirmation."
          ],
          "permissions": "Appearance preferences can be personal. Model, provider, security and server changes require configuration rights.",
          "limits": "Some options appear only when enabled by an administrator or supported by your browser. Save feedback determines whether the change was applied.",
          "example": "Bound response length without assuming every model uses the same limit."
        },
        "nl": {
          "title": "Maximale uitvoertokens aanpassen",
          "purpose": "Stel een optionele uitvoertokenlimiet in die het gekozen model ondersteunt.",
          "when": "Wanneer de huidige instelling of weergave niet past bij de bedoelde werkwijze.",
          "steps": [
            "Open Instellingen en zoek Maximale uitvoertokens aanpassen.",
            "Kies de gewenste waarde; gebruik Opslaan indien aangeboden of wacht op bevestiging van automatisch opslaan."
          ],
          "permissions": "Weergavevoorkeuren kunnen persoonlijk zijn. Model-, provider-, beveiligings- en serverwijzigingen vereisen configuratierechten.",
          "limits": "Sommige opties verschijnen alleen als een beheerder ze inschakelt of je browser ze ondersteunt. De opslagmelding bepaalt of de wijziging is toegepast.",
          "example": "Begrens antwoordlengte zonder aan te nemen dat elk model dezelfde limiet gebruikt."
        }
      }
    },
    {
      "id": "webui.settings.show_quota_chip",
      "area": "settings",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.settings.show_quota_chip",
        "#settingsShowQuotaChip"
      ],
      "source_refs": [
        "static/index.html:1520"
      ],
      "related": [
        "webui.settings.theme",
        "webui.settings.skin",
        "webui.settings.font_size"
      ],
      "locales": {
        "en": {
          "title": "Quota chip visibility",
          "purpose": "Show or hide the provider quota shortcut.",
          "when": "When the current configuration or presentation does not fit the intended workflow.",
          "steps": [
            "Open Settings and find Quota chip visibility.",
            "Choose the desired value; use Save if offered, or wait for autosave confirmation."
          ],
          "permissions": "Appearance preferences can be personal. Model, provider, security and server changes require configuration rights.",
          "limits": "Some options appear only when enabled by an administrator or supported by your browser. Save feedback determines whether the change was applied.",
          "example": "Keep quota information close to the composer."
        },
        "nl": {
          "title": "Quotaknop tonen",
          "purpose": "Toon of verberg de snelknop voor providerquota.",
          "when": "Wanneer de huidige instelling of weergave niet past bij de bedoelde werkwijze.",
          "steps": [
            "Open Instellingen en zoek Quotaknop tonen.",
            "Kies de gewenste waarde; gebruik Opslaan indien aangeboden of wacht op bevestiging van automatisch opslaan."
          ],
          "permissions": "Weergavevoorkeuren kunnen persoonlijk zijn. Model-, provider-, beveiligings- en serverwijzigingen vereisen configuratierechten.",
          "limits": "Sommige opties verschijnen alleen als een beheerder ze inschakelt of je browser ze ondersteunt. De opslagmelding bepaalt of de wijziging is toegepast.",
          "example": "Houd quota-informatie bij het berichtveld."
        }
      }
    },
    {
      "id": "webui.settings.show_conversation_outline",
      "area": "settings",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.settings.show_conversation_outline",
        "#settingsShowConversationOutline"
      ],
      "source_refs": [
        "static/index.html:1527"
      ],
      "related": [
        "webui.settings.theme",
        "webui.settings.skin",
        "webui.settings.font_size"
      ],
      "locales": {
        "en": {
          "title": "Conversation outline",
          "purpose": "Show or hide the outline used to jump between conversation turns.",
          "when": "When the current configuration or presentation does not fit the intended workflow.",
          "steps": [
            "Open Settings and find Conversation outline.",
            "Choose the desired value; use Save if offered, or wait for autosave confirmation."
          ],
          "permissions": "Appearance preferences can be personal. Model, provider, security and server changes require configuration rights.",
          "limits": "Some options appear only when enabled by an administrator or supported by your browser. Save feedback determines whether the change was applied.",
          "example": "Navigate to a previous question quickly."
        },
        "nl": {
          "title": "Gespreksoverzicht",
          "purpose": "Toon of verberg het overzicht om tussen gespreksbeurten te springen.",
          "when": "Wanneer de huidige instelling of weergave niet past bij de bedoelde werkwijze.",
          "steps": [
            "Open Instellingen en zoek Gespreksoverzicht.",
            "Kies de gewenste waarde; gebruik Opslaan indien aangeboden of wacht op bevestiging van automatisch opslaan."
          ],
          "permissions": "Weergavevoorkeuren kunnen persoonlijk zijn. Model-, provider-, beveiligings- en serverwijzigingen vereisen configuratierechten.",
          "limits": "Sommige opties verschijnen alleen als een beheerder ze inschakelt of je browser ze ondersteunt. De opslagmelding bepaalt of de wijziging is toegepast.",
          "example": "Ga snel naar een eerdere vraag."
        }
      }
    },
    {
      "id": "webui.settings.show_tps",
      "area": "settings",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.settings.show_tps",
        "#settingsShowTps"
      ],
      "source_refs": [
        "static/index.html:1534"
      ],
      "related": [
        "webui.settings.theme",
        "webui.settings.skin",
        "webui.settings.font_size"
      ],
      "locales": {
        "en": {
          "title": "Token speed display",
          "purpose": "Show available tokens-per-second generation information.",
          "when": "When the current configuration or presentation does not fit the intended workflow.",
          "steps": [
            "Open Settings and find Token speed display.",
            "Choose the desired value; use Save if offered, or wait for autosave confirmation."
          ],
          "permissions": "Appearance preferences can be personal. Model, provider, security and server changes require configuration rights.",
          "limits": "Some options appear only when enabled by an administrator or supported by your browser. Save feedback determines whether the change was applied.",
          "example": "Compare perceived response speed with the shown metric."
        },
        "nl": {
          "title": "Tokensnelheid tonen",
          "purpose": "Toon beschikbare informatie over gegenereerde tokens per seconde.",
          "when": "Wanneer de huidige instelling of weergave niet past bij de bedoelde werkwijze.",
          "steps": [
            "Open Instellingen en zoek Tokensnelheid tonen.",
            "Kies de gewenste waarde; gebruik Opslaan indien aangeboden of wacht op bevestiging van automatisch opslaan."
          ],
          "permissions": "Weergavevoorkeuren kunnen persoonlijk zijn. Model-, provider-, beveiligings- en serverwijzigingen vereisen configuratierechten.",
          "limits": "Sommige opties verschijnen alleen als een beheerder ze inschakelt of je browser ze ondersteunt. De opslagmelding bepaalt of de wijziging is toegepast.",
          "example": "Vergelijk ervaren antwoordsnelheid met de getoonde waarde."
        }
      }
    },
    {
      "id": "webui.settings.fade_text_effect",
      "area": "settings",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.settings.fade_text_effect",
        "#settingsFadeTextEffect"
      ],
      "source_refs": [
        "static/index.html:1541"
      ],
      "related": [
        "webui.settings.theme",
        "webui.settings.skin",
        "webui.settings.font_size"
      ],
      "locales": {
        "en": {
          "title": "Streaming text animation",
          "purpose": "Enable or disable the visual fade effect for arriving text.",
          "when": "When the current configuration or presentation does not fit the intended workflow.",
          "steps": [
            "Open Settings and find Streaming text animation.",
            "Choose the desired value; use Save if offered, or wait for autosave confirmation."
          ],
          "permissions": "Appearance preferences can be personal. Model, provider, security and server changes require configuration rights.",
          "limits": "Some options appear only when enabled by an administrator or supported by your browser. Save feedback determines whether the change was applied.",
          "example": "Reduce visual motion while reading."
        },
        "nl": {
          "title": "Animatie bij binnenkomende tekst",
          "purpose": "Schakel het vervaageffect voor binnenkomende tekst in of uit.",
          "when": "Wanneer de huidige instelling of weergave niet past bij de bedoelde werkwijze.",
          "steps": [
            "Open Instellingen en zoek Animatie bij binnenkomende tekst.",
            "Kies de gewenste waarde; gebruik Opslaan indien aangeboden of wacht op bevestiging van automatisch opslaan."
          ],
          "permissions": "Weergavevoorkeuren kunnen persoonlijk zijn. Model-, provider-, beveiligings- en serverwijzigingen vereisen configuratierechten.",
          "limits": "Sommige opties verschijnen alleen als een beheerder ze inschakelt of je browser ze ondersteunt. De opslagmelding bepaalt of de wijziging is toegepast.",
          "example": "Verminder visuele beweging tijdens het lezen."
        }
      }
    },
    {
      "id": "webui.settings.terminal_auto_expand",
      "area": "settings",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.settings.terminal_auto_expand",
        "#settingsTerminalAutoExpand"
      ],
      "source_refs": [
        "static/index.html:1548"
      ],
      "related": [
        "webui.settings.theme",
        "webui.settings.skin",
        "webui.settings.font_size"
      ],
      "locales": {
        "en": {
          "title": "Automatically expand terminal",
          "purpose": "Choose whether terminal activity opens its panel automatically.",
          "when": "When the current configuration or presentation does not fit the intended workflow.",
          "steps": [
            "Open Settings and find Automatically expand terminal.",
            "Choose the desired value; use Save if offered, or wait for autosave confirmation."
          ],
          "permissions": "Appearance preferences can be personal. Model, provider, security and server changes require configuration rights.",
          "limits": "Some options appear only when enabled by an administrator or supported by your browser. Save feedback determines whether the change was applied.",
          "example": "Keep the terminal collapsed while focusing on chat."
        },
        "nl": {
          "title": "Terminal automatisch uitklappen",
          "purpose": "Kies of terminalactiviteit het paneel automatisch opent.",
          "when": "Wanneer de huidige instelling of weergave niet past bij de bedoelde werkwijze.",
          "steps": [
            "Open Instellingen en zoek Terminal automatisch uitklappen.",
            "Kies de gewenste waarde; gebruik Opslaan indien aangeboden of wacht op bevestiging van automatisch opslaan."
          ],
          "permissions": "Weergavevoorkeuren kunnen persoonlijk zijn. Model-, provider-, beveiligings- en serverwijzigingen vereisen configuratierechten.",
          "limits": "Sommige opties verschijnen alleen als een beheerder ze inschakelt of je browser ze ondersteunt. De opslagmelding bepaalt of de wijziging is toegepast.",
          "example": "Houd de terminal dicht terwijl je op chat focust."
        }
      }
    },
    {
      "id": "webui.settings.api_redact",
      "area": "settings",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.settings.api_redact",
        "#settingsApiRedact"
      ],
      "source_refs": [
        "static/index.html:1555"
      ],
      "related": [
        "webui.settings.theme",
        "webui.settings.skin",
        "webui.settings.font_size"
      ],
      "locales": {
        "en": {
          "title": "API detail redaction",
          "purpose": "Use the offered redaction setting for displayed API details.",
          "when": "When the current configuration or presentation does not fit the intended workflow.",
          "steps": [
            "Open Settings and find API detail redaction.",
            "Choose the desired value; use Save if offered, or wait for autosave confirmation."
          ],
          "permissions": "Appearance preferences can be personal. Model, provider, security and server changes require configuration rights.",
          "limits": "Some options appear only when enabled by an administrator or supported by your browser. Save feedback determines whether the change was applied.",
          "example": "Reduce sensitive detail in supported diagnostic views."
        },
        "nl": {
          "title": "API-details afschermen",
          "purpose": "Gebruik de aangeboden afscherminstelling voor getoonde API-details.",
          "when": "Wanneer de huidige instelling of weergave niet past bij de bedoelde werkwijze.",
          "steps": [
            "Open Instellingen en zoek API-details afschermen.",
            "Kies de gewenste waarde; gebruik Opslaan indien aangeboden of wacht op bevestiging van automatisch opslaan."
          ],
          "permissions": "Weergavevoorkeuren kunnen persoonlijk zijn. Model-, provider-, beveiligings- en serverwijzigingen vereisen configuratierechten.",
          "limits": "Sommige opties verschijnen alleen als een beheerder ze inschakelt of je browser ze ondersteunt. De opslagmelding bepaalt of de wijziging is toegepast.",
          "example": "Verminder gevoelige details in ondersteunde diagnostische schermen."
        }
      }
    },
    {
      "id": "webui.settings.sidebar_density",
      "area": "settings",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.settings.sidebar_density",
        "#settingsSidebarDensity"
      ],
      "source_refs": [
        "static/index.html:1562"
      ],
      "related": [
        "webui.settings.theme",
        "webui.settings.skin",
        "webui.settings.font_size"
      ],
      "locales": {
        "en": {
          "title": "Sidebar density",
          "purpose": "Choose how compact conversation rows appear.",
          "when": "When the current configuration or presentation does not fit the intended workflow.",
          "steps": [
            "Open Settings and find Sidebar density.",
            "Choose the desired value; use Save if offered, or wait for autosave confirmation."
          ],
          "permissions": "Appearance preferences can be personal. Model, provider, security and server changes require configuration rights.",
          "limits": "Some options appear only when enabled by an administrator or supported by your browser. Save feedback determines whether the change was applied.",
          "example": "Fit more conversation titles on the screen."
        },
        "nl": {
          "title": "Dichtheid van de zijbalk",
          "purpose": "Kies hoe compact gespreksregels worden getoond.",
          "when": "Wanneer de huidige instelling of weergave niet past bij de bedoelde werkwijze.",
          "steps": [
            "Open Instellingen en zoek Dichtheid van de zijbalk.",
            "Kies de gewenste waarde; gebruik Opslaan indien aangeboden of wacht op bevestiging van automatisch opslaan."
          ],
          "permissions": "Weergavevoorkeuren kunnen persoonlijk zijn. Model-, provider-, beveiligings- en serverwijzigingen vereisen configuratierechten.",
          "limits": "Sommige opties verschijnen alleen als een beheerder ze inschakelt of je browser ze ondersteunt. De opslagmelding bepaalt of de wijziging is toegepast.",
          "example": "Toon meer gesprekstitels op het scherm."
        }
      }
    },
    {
      "id": "webui.settings.pinned_sessions_limit",
      "area": "settings",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.settings.pinned_sessions_limit",
        "#settingsPinnedSessionsLimit"
      ],
      "source_refs": [
        "static/index.html:1570"
      ],
      "related": [
        "webui.settings.theme",
        "webui.settings.skin",
        "webui.settings.font_size"
      ],
      "locales": {
        "en": {
          "title": "Pinned conversation limit",
          "purpose": "Set the supported display limit for pinned conversations.",
          "when": "When the current configuration or presentation does not fit the intended workflow.",
          "steps": [
            "Open Settings and find Pinned conversation limit.",
            "Choose the desired value; use Save if offered, or wait for autosave confirmation."
          ],
          "permissions": "Appearance preferences can be personal. Model, provider, security and server changes require configuration rights.",
          "limits": "Some options appear only when enabled by an administrator or supported by your browser. Save feedback determines whether the change was applied.",
          "example": "Keep a manageable set of pinned work visible."
        },
        "nl": {
          "title": "Limiet voor vastgezette gesprekken",
          "purpose": "Stel de ondersteunde weergavelimiet voor vastgezette gesprekken in.",
          "when": "Wanneer de huidige instelling of weergave niet past bij de bedoelde werkwijze.",
          "steps": [
            "Open Instellingen en zoek Limiet voor vastgezette gesprekken.",
            "Kies de gewenste waarde; gebruik Opslaan indien aangeboden of wacht op bevestiging van automatisch opslaan."
          ],
          "permissions": "Weergavevoorkeuren kunnen persoonlijk zijn. Model-, provider-, beveiligings- en serverwijzigingen vereisen configuratierechten.",
          "limits": "Sommige opties verschijnen alleen als een beheerder ze inschakelt of je browser ze ondersteunt. De opslagmelding bepaalt of de wijziging is toegepast.",
          "example": "Houd een overzichtelijke selectie vastgezet werk zichtbaar."
        }
      }
    },
    {
      "id": "webui.settings.auto_title_refresh",
      "area": "settings",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.settings.auto_title_refresh",
        "#settingsAutoTitleRefresh"
      ],
      "source_refs": [
        "static/index.html:1575"
      ],
      "related": [
        "webui.settings.theme",
        "webui.settings.skin",
        "webui.settings.font_size"
      ],
      "locales": {
        "en": {
          "title": "Automatic title refresh",
          "purpose": "Choose whether supported conversation title updates happen automatically.",
          "when": "When the current configuration or presentation does not fit the intended workflow.",
          "steps": [
            "Open Settings and find Automatic title refresh.",
            "Choose the desired value; use Save if offered, or wait for autosave confirmation."
          ],
          "permissions": "Appearance preferences can be personal. Model, provider, security and server changes require configuration rights.",
          "limits": "Some options appear only when enabled by an administrator or supported by your browser. Save feedback determines whether the change was applied.",
          "example": "Let a title follow the developing conversation topic."
        },
        "nl": {
          "title": "Titels automatisch vernieuwen",
          "purpose": "Kies of ondersteunde gesprekstitelupdates automatisch plaatsvinden.",
          "when": "Wanneer de huidige instelling of weergave niet past bij de bedoelde werkwijze.",
          "steps": [
            "Open Instellingen en zoek Titels automatisch vernieuwen.",
            "Kies de gewenste waarde; gebruik Opslaan indien aangeboden of wacht op bevestiging van automatisch opslaan."
          ],
          "permissions": "Weergavevoorkeuren kunnen persoonlijk zijn. Model-, provider-, beveiligings- en serverwijzigingen vereisen configuratierechten.",
          "limits": "Sommige opties verschijnen alleen als een beheerder ze inschakelt of je browser ze ondersteunt. De opslagmelding bepaalt of de wijziging is toegepast.",
          "example": "Laat een titel het zich ontwikkelende gespreksonderwerp volgen."
        }
      }
    },
    {
      "id": "webui.settings.default_message_mode",
      "area": "settings",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.settings.default_message_mode",
        "#settingsDefaultMessageMode"
      ],
      "source_refs": [
        "static/index.html:1585"
      ],
      "related": [
        "webui.settings.theme",
        "webui.settings.skin",
        "webui.settings.font_size"
      ],
      "locales": {
        "en": {
          "title": "Messages while busy",
          "purpose": "Choose the default offered handling for messages sent while the agent is busy.",
          "when": "When the current configuration or presentation does not fit the intended workflow.",
          "steps": [
            "Open Settings and find Messages while busy.",
            "Choose the desired value; use Save if offered, or wait for autosave confirmation."
          ],
          "permissions": "Appearance preferences can be personal. Model, provider, security and server changes require configuration rights.",
          "limits": "Some options appear only when enabled by an administrator or supported by your browser. Save feedback determines whether the change was applied.",
          "example": "Queue a follow-up instead of interrupting active work."
        },
        "nl": {
          "title": "Berichten tijdens uitvoering",
          "purpose": "Kies de standaard aangeboden verwerking van berichten terwijl de agent bezig is.",
          "when": "Wanneer de huidige instelling of weergave niet past bij de bedoelde werkwijze.",
          "steps": [
            "Open Instellingen en zoek Berichten tijdens uitvoering.",
            "Kies de gewenste waarde; gebruik Opslaan indien aangeboden of wacht op bevestiging van automatisch opslaan."
          ],
          "permissions": "Weergavevoorkeuren kunnen persoonlijk zijn. Model-, provider-, beveiligings- en serverwijzigingen vereisen configuratierechten.",
          "limits": "Sommige opties verschijnen alleen als een beheerder ze inschakelt of je browser ze ondersteunt. De opslagmelding bepaalt of de wijziging is toegepast.",
          "example": "Zet een vervolgvraag klaar in plaats van actief werk te onderbreken."
        }
      }
    },
    {
      "id": "webui.settings.show_busy_placeholder_hint",
      "area": "settings",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.settings.show_busy_placeholder_hint",
        "#settingsShowBusyPlaceholderHint"
      ],
      "source_refs": [
        "static/index.html:1594"
      ],
      "related": [
        "webui.settings.theme",
        "webui.settings.skin",
        "webui.settings.font_size"
      ],
      "locales": {
        "en": {
          "title": "Busy-state composer hint",
          "purpose": "Show or hide the composer hint explaining the active busy-message mode.",
          "when": "When the current configuration or presentation does not fit the intended workflow.",
          "steps": [
            "Open Settings and find Busy-state composer hint.",
            "Choose the desired value; use Save if offered, or wait for autosave confirmation."
          ],
          "permissions": "Appearance preferences can be personal. Model, provider, security and server changes require configuration rights.",
          "limits": "Some options appear only when enabled by an administrator or supported by your browser. Save feedback determines whether the change was applied.",
          "example": "See what sending will do while a response is running."
        },
        "nl": {
          "title": "Aanwijzing tijdens uitvoering",
          "purpose": "Toon of verberg de aanwijzing over de actieve berichtmodus tijdens uitvoering.",
          "when": "Wanneer de huidige instelling of weergave niet past bij de bedoelde werkwijze.",
          "steps": [
            "Open Instellingen en zoek Aanwijzing tijdens uitvoering.",
            "Kies de gewenste waarde; gebruik Opslaan indien aangeboden of wacht op bevestiging van automatisch opslaan."
          ],
          "permissions": "Weergavevoorkeuren kunnen persoonlijk zijn. Model-, provider-, beveiligings- en serverwijzigingen vereisen configuratierechten.",
          "limits": "Sommige opties verschijnen alleen als een beheerder ze inschakelt of je browser ze ondersteunt. De opslagmelding bepaalt of de wijziging is toegepast.",
          "example": "Zie wat versturen doet terwijl een antwoord loopt."
        }
      }
    },
    {
      "id": "webui.settings.new_chat_on_workspace_switch",
      "area": "settings",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.settings.new_chat_on_workspace_switch",
        "#settingsNewChatOnWorkspaceSwitch"
      ],
      "source_refs": [
        "static/index.html:1601"
      ],
      "related": [
        "webui.settings.theme",
        "webui.settings.skin",
        "webui.settings.font_size"
      ],
      "locales": {
        "en": {
          "title": "New chat when switching workspace",
          "purpose": "Choose whether changing workspace starts a separate conversation.",
          "when": "When the current configuration or presentation does not fit the intended workflow.",
          "steps": [
            "Open Settings and find New chat when switching workspace.",
            "Choose the desired value; use Save if offered, or wait for autosave confirmation."
          ],
          "permissions": "Appearance preferences can be personal. Model, provider, security and server changes require configuration rights.",
          "limits": "Some options appear only when enabled by an administrator or supported by your browser. Save feedback determines whether the change was applied.",
          "example": "Keep different workspaces’ conversations separate."
        },
        "nl": {
          "title": "Nieuwe chat bij werkruimtewissel",
          "purpose": "Kies of wisselen van werkruimte een afzonderlijk gesprek begint.",
          "when": "Wanneer de huidige instelling of weergave niet past bij de bedoelde werkwijze.",
          "steps": [
            "Open Instellingen en zoek Nieuwe chat bij werkruimtewissel.",
            "Kies de gewenste waarde; gebruik Opslaan indien aangeboden of wacht op bevestiging van automatisch opslaan."
          ],
          "permissions": "Weergavevoorkeuren kunnen persoonlijk zijn. Model-, provider-, beveiligings- en serverwijzigingen vereisen configuratierechten.",
          "limits": "Sommige opties verschijnen alleen als een beheerder ze inschakelt of je browser ze ondersteunt. De opslagmelding bepaalt of de wijziging is toegepast.",
          "example": "Houd gesprekken van verschillende werkruimten gescheiden."
        }
      }
    },
    {
      "id": "webui.settings.show_cli_sessions",
      "area": "settings",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.settings.show_cli_sessions",
        "#settingsShowCliSessions"
      ],
      "source_refs": [
        "static/index.html:1608"
      ],
      "related": [
        "webui.settings.theme",
        "webui.settings.skin",
        "webui.settings.font_size"
      ],
      "locales": {
        "en": {
          "title": "CLI conversation history",
          "purpose": "Show or hide accessible conversations originating in the CLI.",
          "when": "When the current configuration or presentation does not fit the intended workflow.",
          "steps": [
            "Open Settings and find CLI conversation history.",
            "Choose the desired value; use Save if offered, or wait for autosave confirmation."
          ],
          "permissions": "Appearance preferences can be personal. Model, provider, security and server changes require configuration rights.",
          "limits": "Some options appear only when enabled by an administrator or supported by your browser. Save feedback determines whether the change was applied.",
          "example": "Find a permitted conversation started in the terminal."
        },
        "nl": {
          "title": "CLI-gespreksgeschiedenis",
          "purpose": "Toon of verberg toegankelijke gesprekken uit de CLI.",
          "when": "Wanneer de huidige instelling of weergave niet past bij de bedoelde werkwijze.",
          "steps": [
            "Open Instellingen en zoek CLI-gespreksgeschiedenis.",
            "Kies de gewenste waarde; gebruik Opslaan indien aangeboden of wacht op bevestiging van automatisch opslaan."
          ],
          "permissions": "Weergavevoorkeuren kunnen persoonlijk zijn. Model-, provider-, beveiligings- en serverwijzigingen vereisen configuratierechten.",
          "limits": "Sommige opties verschijnen alleen als een beheerder ze inschakelt of je browser ze ondersteunt. De opslagmelding bepaalt of de wijziging is toegepast.",
          "example": "Vind een toegestaan gesprek dat in de terminal begon."
        }
      }
    },
    {
      "id": "webui.settings.show_cron_sessions",
      "area": "settings",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.settings.show_cron_sessions",
        "#settingsShowCronSessions"
      ],
      "source_refs": [
        "static/index.html:1615"
      ],
      "related": [
        "webui.settings.theme",
        "webui.settings.skin",
        "webui.settings.font_size"
      ],
      "locales": {
        "en": {
          "title": "Scheduled-task history",
          "purpose": "Show or hide accessible sessions created by scheduled tasks.",
          "when": "When the current configuration or presentation does not fit the intended workflow.",
          "steps": [
            "Open Settings and find Scheduled-task history.",
            "Choose the desired value; use Save if offered, or wait for autosave confirmation."
          ],
          "permissions": "Appearance preferences can be personal. Model, provider, security and server changes require configuration rights.",
          "limits": "Some options appear only when enabled by an administrator or supported by your browser. Save feedback determines whether the change was applied.",
          "example": "Inspect a task’s generated conversation history."
        },
        "nl": {
          "title": "Geschiedenis van geplande taken",
          "purpose": "Toon of verberg toegankelijke sessies van geplande taken.",
          "when": "Wanneer de huidige instelling of weergave niet past bij de bedoelde werkwijze.",
          "steps": [
            "Open Instellingen en zoek Geschiedenis van geplande taken.",
            "Kies de gewenste waarde; gebruik Opslaan indien aangeboden of wacht op bevestiging van automatisch opslaan."
          ],
          "permissions": "Weergavevoorkeuren kunnen persoonlijk zijn. Model-, provider-, beveiligings- en serverwijzigingen vereisen configuratierechten.",
          "limits": "Sommige opties verschijnen alleen als een beheerder ze inschakelt of je browser ze ondersteunt. De opslagmelding bepaalt of de wijziging is toegepast.",
          "example": "Bekijk de gegenereerde gespreksgeschiedenis van een taak."
        }
      }
    },
    {
      "id": "webui.settings.show_claude_code_sessions",
      "area": "settings",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.settings.show_claude_code_sessions",
        "#settingsShowClaudeCodeSessions"
      ],
      "source_refs": [
        "static/index.html:1622"
      ],
      "related": [
        "webui.settings.theme",
        "webui.settings.skin",
        "webui.settings.font_size"
      ],
      "locales": {
        "en": {
          "title": "Claude Code history",
          "purpose": "Show or hide available Claude Code session history in the supported list.",
          "when": "When the current configuration or presentation does not fit the intended workflow.",
          "steps": [
            "Open Settings and find Claude Code history.",
            "Choose the desired value; use Save if offered, or wait for autosave confirmation."
          ],
          "permissions": "Appearance preferences can be personal. Model, provider, security and server changes require configuration rights.",
          "limits": "Some options appear only when enabled by an administrator or supported by your browser. Save feedback determines whether the change was applied.",
          "example": "Find accessible coding history without changing account credentials."
        },
        "nl": {
          "title": "Claude Code-geschiedenis",
          "purpose": "Toon of verberg beschikbare Claude Code-sessiegeschiedenis in de ondersteunde lijst.",
          "when": "Wanneer de huidige instelling of weergave niet past bij de bedoelde werkwijze.",
          "steps": [
            "Open Instellingen en zoek Claude Code-geschiedenis.",
            "Kies de gewenste waarde; gebruik Opslaan indien aangeboden of wacht op bevestiging van automatisch opslaan."
          ],
          "permissions": "Weergavevoorkeuren kunnen persoonlijk zijn. Model-, provider-, beveiligings- en serverwijzigingen vereisen configuratierechten.",
          "limits": "Sommige opties verschijnen alleen als een beheerder ze inschakelt of je browser ze ondersteunt. De opslagmelding bepaalt of de wijziging is toegepast.",
          "example": "Vind toegankelijke programmeergeschiedenis zonder accountgegevens te wijzigen."
        }
      }
    },
    {
      "id": "webui.settings.show_webhook_sessions",
      "area": "settings",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.settings.show_webhook_sessions",
        "#settingsShowWebhookSessions"
      ],
      "source_refs": [
        "static/index.html:1629"
      ],
      "related": [
        "webui.settings.theme",
        "webui.settings.skin",
        "webui.settings.font_size"
      ],
      "locales": {
        "en": {
          "title": "Webhook history",
          "purpose": "Show or hide accessible sessions originating from webhooks.",
          "when": "When the current configuration or presentation does not fit the intended workflow.",
          "steps": [
            "Open Settings and find Webhook history.",
            "Choose the desired value; use Save if offered, or wait for autosave confirmation."
          ],
          "permissions": "Appearance preferences can be personal. Model, provider, security and server changes require configuration rights.",
          "limits": "Some options appear only when enabled by an administrator or supported by your browser. Save feedback determines whether the change was applied.",
          "example": "Inspect a conversation created by an allowed incoming event."
        },
        "nl": {
          "title": "Webhookgeschiedenis",
          "purpose": "Toon of verberg toegankelijke sessies afkomstig van webhooks.",
          "when": "Wanneer de huidige instelling of weergave niet past bij de bedoelde werkwijze.",
          "steps": [
            "Open Instellingen en zoek Webhookgeschiedenis.",
            "Kies de gewenste waarde; gebruik Opslaan indien aangeboden of wacht op bevestiging van automatisch opslaan."
          ],
          "permissions": "Weergavevoorkeuren kunnen persoonlijk zijn. Model-, provider-, beveiligings- en serverwijzigingen vereisen configuratierechten.",
          "limits": "Sommige opties verschijnen alleen als een beheerder ze inschakelt of je browser ze ondersteunt. De opslagmelding bepaalt of de wijziging is toegepast.",
          "example": "Bekijk een gesprek dat door een toegestane inkomende gebeurtenis is gemaakt."
        }
      }
    },
    {
      "id": "webui.settings.show_previous_messaging_sessions",
      "area": "settings",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.settings.show_previous_messaging_sessions",
        "#settingsShowPreviousMessagingSessions"
      ],
      "source_refs": [
        "static/index.html:1636"
      ],
      "related": [
        "webui.settings.theme",
        "webui.settings.skin",
        "webui.settings.font_size"
      ],
      "locales": {
        "en": {
          "title": "Previous messaging sessions",
          "purpose": "Show or hide accessible earlier messaging-channel sessions.",
          "when": "When the current configuration or presentation does not fit the intended workflow.",
          "steps": [
            "Open Settings and find Previous messaging sessions.",
            "Choose the desired value; use Save if offered, or wait for autosave confirmation."
          ],
          "permissions": "Appearance preferences can be personal. Model, provider, security and server changes require configuration rights.",
          "limits": "Some options appear only when enabled by an administrator or supported by your browser. Save feedback determines whether the change was applied.",
          "example": "Find an earlier channel conversation in the permitted history."
        },
        "nl": {
          "title": "Eerdere berichtensessies",
          "purpose": "Toon of verberg toegankelijke eerdere sessies van berichtenkanalen.",
          "when": "Wanneer de huidige instelling of weergave niet past bij de bedoelde werkwijze.",
          "steps": [
            "Open Instellingen en zoek Eerdere berichtensessies.",
            "Kies de gewenste waarde; gebruik Opslaan indien aangeboden of wacht op bevestiging van automatisch opslaan."
          ],
          "permissions": "Weergavevoorkeuren kunnen persoonlijk zijn. Model-, provider-, beveiligings- en serverwijzigingen vereisen configuratierechten.",
          "limits": "Sommige opties verschijnen alleen als een beheerder ze inschakelt of je browser ze ondersteunt. De opslagmelding bepaalt of de wijziging is toegepast.",
          "example": "Vind een eerder kanaalgesprek in de toegestane geschiedenis."
        }
      }
    },
    {
      "id": "webui.settings.sync_insights",
      "area": "settings",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.settings.sync_insights",
        "#settingsSyncInsights"
      ],
      "source_refs": [
        "static/index.html:1643"
      ],
      "related": [
        "webui.settings.theme",
        "webui.settings.skin",
        "webui.settings.font_size"
      ],
      "locales": {
        "en": {
          "title": "Synchronize usage insights",
          "purpose": "Choose the offered usage-insight synchronization behavior.",
          "when": "When the current configuration or presentation does not fit the intended workflow.",
          "steps": [
            "Open Settings and find Synchronize usage insights.",
            "Choose the desired value; use Save if offered, or wait for autosave confirmation."
          ],
          "permissions": "Appearance preferences can be personal. Model, provider, security and server changes require configuration rights.",
          "limits": "Some options appear only when enabled by an administrator or supported by your browser. Save feedback determines whether the change was applied.",
          "example": "Keep the supported usage view up to date."
        },
        "nl": {
          "title": "Gebruiksinzichten synchroniseren",
          "purpose": "Kies het aangeboden synchronisatiegedrag voor gebruiksinzichten.",
          "when": "Wanneer de huidige instelling of weergave niet past bij de bedoelde werkwijze.",
          "steps": [
            "Open Instellingen en zoek Gebruiksinzichten synchroniseren.",
            "Kies de gewenste waarde; gebruik Opslaan indien aangeboden of wacht op bevestiging van automatisch opslaan."
          ],
          "permissions": "Weergavevoorkeuren kunnen persoonlijk zijn. Model-, provider-, beveiligings- en serverwijzigingen vereisen configuratierechten.",
          "limits": "Sommige opties verschijnen alleen als een beheerder ze inschakelt of je browser ze ondersteunt. De opslagmelding bepaalt of de wijziging is toegepast.",
          "example": "Houd het ondersteunde gebruiksoverzicht actueel."
        }
      }
    },
    {
      "id": "webui.settings.check_updates",
      "area": "settings",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.settings.check_updates",
        "#settingsCheckUpdates"
      ],
      "source_refs": [
        "static/index.html:1650"
      ],
      "related": [
        "webui.settings.theme",
        "webui.settings.skin",
        "webui.settings.font_size"
      ],
      "locales": {
        "en": {
          "title": "Automatic update checks",
          "purpose": "Choose whether the interface checks for available updates.",
          "when": "When the current configuration or presentation does not fit the intended workflow.",
          "steps": [
            "Open Settings and find Automatic update checks.",
            "Choose the desired value; use Save if offered, or wait for autosave confirmation."
          ],
          "permissions": "Appearance preferences can be personal. Model, provider, security and server changes require configuration rights.",
          "limits": "Some options appear only when enabled by an administrator or supported by your browser. Save feedback determines whether the change was applied.",
          "example": "Learn about updates without manually checking each time."
        },
        "nl": {
          "title": "Automatisch naar updates zoeken",
          "purpose": "Kies of de interface naar beschikbare updates zoekt.",
          "when": "Wanneer de huidige instelling of weergave niet past bij de bedoelde werkwijze.",
          "steps": [
            "Open Instellingen en zoek Automatisch naar updates zoeken.",
            "Kies de gewenste waarde; gebruik Opslaan indien aangeboden of wacht op bevestiging van automatisch opslaan."
          ],
          "permissions": "Weergavevoorkeuren kunnen persoonlijk zijn. Model-, provider-, beveiligings- en serverwijzigingen vereisen configuratierechten.",
          "limits": "Sommige opties verschijnen alleen als een beheerder ze inschakelt of je browser ze ondersteunt. De opslagmelding bepaalt of de wijziging is toegepast.",
          "example": "Hoor over updates zonder steeds handmatig te controleren."
        }
      }
    },
    {
      "id": "webui.settings.update_channel",
      "area": "settings",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.settings.update_channel",
        "#settingsUpdateChannel"
      ],
      "source_refs": [
        "static/index.html:1657"
      ],
      "related": [
        "webui.settings.theme",
        "webui.settings.skin",
        "webui.settings.font_size"
      ],
      "locales": {
        "en": {
          "title": "Update channel",
          "purpose": "Choose the supported release channel for update checks.",
          "when": "When the current configuration or presentation does not fit the intended workflow.",
          "steps": [
            "Open Settings and find Update channel.",
            "Choose the desired value; use Save if offered, or wait for autosave confirmation."
          ],
          "permissions": "Appearance preferences can be personal. Model, provider, security and server changes require configuration rights.",
          "limits": "Some options appear only when enabled by an administrator or supported by your browser. Save feedback determines whether the change was applied.",
          "example": "Check the stable release channel used by your operator."
        },
        "nl": {
          "title": "Updatekanaal",
          "purpose": "Kies het ondersteunde releasekanaal voor updatecontroles.",
          "when": "Wanneer de huidige instelling of weergave niet past bij de bedoelde werkwijze.",
          "steps": [
            "Open Instellingen en zoek Updatekanaal.",
            "Kies de gewenste waarde; gebruik Opslaan indien aangeboden of wacht op bevestiging van automatisch opslaan."
          ],
          "permissions": "Weergavevoorkeuren kunnen persoonlijk zijn. Model-, provider-, beveiligings- en serverwijzigingen vereisen configuratierechten.",
          "limits": "Sommige opties verschijnen alleen als een beheerder ze inschakelt of je browser ze ondersteunt. De opslagmelding bepaalt of de wijziging is toegepast.",
          "example": "Controleer het stabiele releasekanaal van je beheerder."
        }
      }
    },
    {
      "id": "webui.settings.ignore_agent_updates",
      "area": "settings",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.settings.ignore_agent_updates",
        "#settingsIgnoreAgentUpdates"
      ],
      "source_refs": [
        "static/index.html:1665"
      ],
      "related": [
        "webui.settings.theme",
        "webui.settings.skin",
        "webui.settings.font_size"
      ],
      "locales": {
        "en": {
          "title": "Agent update notices",
          "purpose": "Choose whether agent update notices are ignored in the supported update view.",
          "when": "When the current configuration or presentation does not fit the intended workflow.",
          "steps": [
            "Open Settings and find Agent update notices.",
            "Choose the desired value; use Save if offered, or wait for autosave confirmation."
          ],
          "permissions": "Appearance preferences can be personal. Model, provider, security and server changes require configuration rights.",
          "limits": "Some options appear only when enabled by an administrator or supported by your browser. Save feedback determines whether the change was applied.",
          "example": "Reduce notices when agent updates are handled centrally."
        },
        "nl": {
          "title": "Agentupdatemeldingen",
          "purpose": "Kies of agentupdatemeldingen in het ondersteunde overzicht worden genegeerd.",
          "when": "Wanneer de huidige instelling of weergave niet past bij de bedoelde werkwijze.",
          "steps": [
            "Open Instellingen en zoek Agentupdatemeldingen.",
            "Kies de gewenste waarde; gebruik Opslaan indien aangeboden of wacht op bevestiging van automatisch opslaan."
          ],
          "permissions": "Weergavevoorkeuren kunnen persoonlijk zijn. Model-, provider-, beveiligings- en serverwijzigingen vereisen configuratierechten.",
          "limits": "Sommige opties verschijnen alleen als een beheerder ze inschakelt of je browser ze ondersteunt. De opslagmelding bepaalt of de wijziging is toegepast.",
          "example": "Verminder meldingen wanneer agentupdates centraal worden beheerd."
        }
      }
    },
    {
      "id": "webui.settings.whats_new_summary",
      "area": "settings",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.settings.whats_new_summary",
        "#settingsWhatsNewSummary"
      ],
      "source_refs": [
        "static/index.html:1672"
      ],
      "related": [
        "webui.settings.theme",
        "webui.settings.skin",
        "webui.settings.font_size"
      ],
      "locales": {
        "en": {
          "title": "What is new summaries",
          "purpose": "Choose whether release summaries are presented.",
          "when": "When the current configuration or presentation does not fit the intended workflow.",
          "steps": [
            "Open Settings and find What is new summaries.",
            "Choose the desired value; use Save if offered, or wait for autosave confirmation."
          ],
          "permissions": "Appearance preferences can be personal. Model, provider, security and server changes require configuration rights.",
          "limits": "Some options appear only when enabled by an administrator or supported by your browser. Save feedback determines whether the change was applied.",
          "example": "Read the summary after an application update."
        },
        "nl": {
          "title": "Samenvattingen van nieuwe functies",
          "purpose": "Kies of samenvattingen van nieuwe releases worden getoond.",
          "when": "Wanneer de huidige instelling of weergave niet past bij de bedoelde werkwijze.",
          "steps": [
            "Open Instellingen en zoek Samenvattingen van nieuwe functies.",
            "Kies de gewenste waarde; gebruik Opslaan indien aangeboden of wacht op bevestiging van automatisch opslaan."
          ],
          "permissions": "Weergavevoorkeuren kunnen persoonlijk zijn. Model-, provider-, beveiligings- en serverwijzigingen vereisen configuratierechten.",
          "limits": "Sommige opties verschijnen alleen als een beheerder ze inschakelt of je browser ze ondersteunt. De opslagmelding bepaalt of de wijziging is toegepast.",
          "example": "Lees de samenvatting na een toepassingsupdate."
        }
      }
    },
    {
      "id": "webui.settings.bot_name",
      "area": "settings",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.settings.bot_name",
        "#settingsBotName"
      ],
      "source_refs": [
        "static/index.html:1680"
      ],
      "related": [
        "webui.settings.theme",
        "webui.settings.skin",
        "webui.settings.font_size"
      ],
      "locales": {
        "en": {
          "title": "Displayed assistant name",
          "purpose": "Set the configured display name used for the assistant label.",
          "when": "When the current configuration or presentation does not fit the intended workflow.",
          "steps": [
            "Open Settings and find Displayed assistant name.",
            "Choose the desired value; use Save if offered, or wait for autosave confirmation."
          ],
          "permissions": "Appearance preferences can be personal. Model, provider, security and server changes require configuration rights.",
          "limits": "Some options appear only when enabled by an administrator or supported by your browser. Save feedback determines whether the change was applied.",
          "example": "Use the organisation’s chosen assistant name."
        },
        "nl": {
          "title": "Weergegeven assistentnaam",
          "purpose": "Stel de geconfigureerde weergavenaam voor het assistentlabel in.",
          "when": "Wanneer de huidige instelling of weergave niet past bij de bedoelde werkwijze.",
          "steps": [
            "Open Instellingen en zoek Weergegeven assistentnaam.",
            "Kies de gewenste waarde; gebruik Opslaan indien aangeboden of wacht op bevestiging van automatisch opslaan."
          ],
          "permissions": "Weergavevoorkeuren kunnen persoonlijk zijn. Model-, provider-, beveiligings- en serverwijzigingen vereisen configuratierechten.",
          "limits": "Sommige opties verschijnen alleen als een beheerder ze inschakelt of je browser ze ondersteunt. De opslagmelding bepaalt of de wijziging is toegepast.",
          "example": "Gebruik de door de organisatie gekozen assistentnaam."
        }
      }
    },
    {
      "id": "webui.settings.dashboard_mode",
      "area": "settings",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.settings.dashboard_mode",
        "#settingsDashboardMode"
      ],
      "source_refs": [
        "static/index.html:1847"
      ],
      "related": [
        "webui.settings.theme",
        "webui.settings.skin",
        "webui.settings.font_size"
      ],
      "locales": {
        "en": {
          "title": "Dashboard display mode",
          "purpose": "Choose the supported method for opening the configured dashboard.",
          "when": "When the current configuration or presentation does not fit the intended workflow.",
          "steps": [
            "Open Settings and find Dashboard display mode.",
            "Choose the desired value; use Save if offered, or wait for autosave confirmation."
          ],
          "permissions": "Appearance preferences can be personal. Model, provider, security and server changes require configuration rights.",
          "limits": "Some options appear only when enabled by an administrator or supported by your browser. Save feedback determines whether the change was applied.",
          "example": "Open a dashboard using the intended integration mode."
        },
        "nl": {
          "title": "Dashboardweergavemodus",
          "purpose": "Kies de ondersteunde manier om het ingestelde dashboard te openen.",
          "when": "Wanneer de huidige instelling of weergave niet past bij de bedoelde werkwijze.",
          "steps": [
            "Open Instellingen en zoek Dashboardweergavemodus.",
            "Kies de gewenste waarde; gebruik Opslaan indien aangeboden of wacht op bevestiging van automatisch opslaan."
          ],
          "permissions": "Weergavevoorkeuren kunnen persoonlijk zijn. Model-, provider-, beveiligings- en serverwijzigingen vereisen configuratierechten.",
          "limits": "Sommige opties verschijnen alleen als een beheerder ze inschakelt of je browser ze ondersteunt. De opslagmelding bepaalt of de wijziging is toegepast.",
          "example": "Open een dashboard via de bedoelde integratiemodus."
        }
      }
    },
    {
      "id": "webui.settings.dashboard_url",
      "area": "settings",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.settings.dashboard_url",
        "#settingsDashboardUrl"
      ],
      "source_refs": [
        "static/index.html:1852"
      ],
      "related": [
        "webui.settings.theme",
        "webui.settings.skin",
        "webui.settings.font_size"
      ],
      "locales": {
        "en": {
          "title": "Dashboard address",
          "purpose": "Set the permitted dashboard address for this installation.",
          "when": "When the current configuration or presentation does not fit the intended workflow.",
          "steps": [
            "Open Settings and find Dashboard address.",
            "Choose the desired value; use Save if offered, or wait for autosave confirmation."
          ],
          "permissions": "Appearance preferences can be personal. Model, provider, security and server changes require configuration rights.",
          "limits": "Some options appear only when enabled by an administrator or supported by your browser. Save feedback determines whether the change was applied.",
          "example": "Point dashboard navigation at the approved service."
        },
        "nl": {
          "title": "Dashboardadres",
          "purpose": "Stel het toegestane dashboardadres voor deze installatie in.",
          "when": "Wanneer de huidige instelling of weergave niet past bij de bedoelde werkwijze.",
          "steps": [
            "Open Instellingen en zoek Dashboardadres.",
            "Kies de gewenste waarde; gebruik Opslaan indien aangeboden of wacht op bevestiging van automatisch opslaan."
          ],
          "permissions": "Weergavevoorkeuren kunnen persoonlijk zijn. Model-, provider-, beveiligings- en serverwijzigingen vereisen configuratierechten.",
          "limits": "Sommige opties verschijnen alleen als een beheerder ze inschakelt of je browser ze ondersteunt. De opslagmelding bepaalt of de wijziging is toegepast.",
          "example": "Richt dashboardnavigatie op de goedgekeurde dienst."
        }
      }
    },
    {
      "id": "webui.settings.save",
      "area": "settings",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.settings.save"
      ],
      "source_refs": [
        "static/index.html:1682",
        "static/index.html:1853",
        "static/index.html:1879",
        "static/panels.js:9769",
        "static/panels.js:9770",
        "static/panels.js:9921"
      ],
      "related": [
        "webui.settings.theme",
        "webui.settings.skin",
        "webui.settings.font_size"
      ],
      "locales": {
        "en": {
          "title": "Save, retry or discard settings",
          "purpose": "Apply explicit settings changes or recover from an unsuccessful appearance autosave.",
          "when": "When the current configuration or presentation does not fit the intended workflow.",
          "steps": [
            "Review the selected settings and choose Save where shown.",
            "For a failed autosave, retry; use Discard only when you want to abandon pending changes."
          ],
          "permissions": "Appearance preferences can be personal. Model, provider, security and server changes require configuration rights.",
          "limits": "Some options appear only when enabled by an administrator or supported by your browser. Save feedback determines whether the change was applied.",
          "example": "Resolve an unsaved appearance preference before navigating away."
        },
        "nl": {
          "title": "Instellingen opslaan, opnieuw proberen of verwerpen",
          "purpose": "Pas expliciete instellingen toe of herstel een mislukte automatische weergaveopslag.",
          "when": "Wanneer de huidige instelling of weergave niet past bij de bedoelde werkwijze.",
          "steps": [
            "Controleer gekozen instellingen en kies Opslaan waar getoond.",
            "Probeer opnieuw bij mislukte automatische opslag; kies Verwerpen alleen om wachtende wijzigingen op te geven."
          ],
          "permissions": "Weergavevoorkeuren kunnen persoonlijk zijn. Model-, provider-, beveiligings- en serverwijzigingen vereisen configuratierechten.",
          "limits": "Sommige opties verschijnen alleen als een beheerder ze inschakelt of je browser ze ondersteunt. De opslagmelding bepaalt of de wijziging is toegepast.",
          "example": "Los een niet-opgeslagen weergavevoorkeur op voordat je weg navigeert."
        }
      }
    },
    {
      "id": "webui.settings.photo",
      "area": "settings",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.settings.photo",
        "#profilePhotoInput",
        "#profilePhotoRemoveBtn"
      ],
      "source_refs": [
        "static/index.html:1147",
        "static/index.html:1149"
      ],
      "related": [
        "webui.settings.theme",
        "webui.settings.skin",
        "webui.settings.font_size"
      ],
      "locales": {
        "en": {
          "title": "Your profile photo",
          "purpose": "Set or remove your account’s supported profile photo.",
          "when": "When the current configuration or presentation does not fit the intended workflow.",
          "steps": [
            "Choose the profile photo control and select a supported image.",
            "Use Remove to clear the photo if desired."
          ],
          "permissions": "Appearance preferences can be personal. Model, provider, security and server changes require configuration rights.",
          "limits": "Some options appear only when enabled by an administrator or supported by your browser. Save feedback determines whether the change was applied.",
          "example": "Make your own identity recognizable in shared work."
        },
        "nl": {
          "title": "Je profielfoto",
          "purpose": "Stel je ondersteunde accountfoto in of verwijder deze.",
          "when": "Wanneer de huidige instelling of weergave niet past bij de bedoelde werkwijze.",
          "steps": [
            "Kies de profielfotobediening en selecteer een ondersteunde afbeelding.",
            "Gebruik Verwijderen om de foto te wissen indien gewenst."
          ],
          "permissions": "Weergavevoorkeuren kunnen persoonlijk zijn. Model-, provider-, beveiligings- en serverwijzigingen vereisen configuratierechten.",
          "limits": "Sommige opties verschijnen alleen als een beheerder ze inschakelt of je browser ze ondersteunt. De opslagmelding bepaalt of de wijziging is toegepast.",
          "example": "Maak je eigen identiteit herkenbaar in gedeeld werk."
        }
      }
    },
    {
      "id": "webui.settings.interaction",
      "area": "settings",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.settings.interaction",
        "#interactionUserMode",
        "#interactionTaskMode",
        "#interactionSave",
        "#interactionReload"
      ],
      "source_refs": [
        "static/index.html:1353",
        "static/index.html:1358",
        "static/index.html:1365",
        "static/index.html:1366"
      ],
      "related": [
        "webui.settings.theme",
        "webui.settings.skin",
        "webui.settings.font_size"
      ],
      "locales": {
        "en": {
          "title": "Interaction user and task modes",
          "purpose": "Choose the offered interaction preferences for the user and task context.",
          "when": "When the current configuration or presentation does not fit the intended workflow.",
          "steps": [
            "Select the user and task modes.",
            "Save to apply; Reload reads the current stored configuration."
          ],
          "permissions": "Appearance preferences can be personal. Model, provider, security and server changes require configuration rights.",
          "limits": "Some options appear only when enabled by an administrator or supported by your browser. Save feedback determines whether the change was applied.",
          "example": "Adjust how interaction is handled for the current work style."
        },
        "nl": {
          "title": "Gebruikers- en taakmodus voor interactie",
          "purpose": "Kies aangeboden interactievoorkeuren voor gebruiker en taakcontext.",
          "when": "Wanneer de huidige instelling of weergave niet past bij de bedoelde werkwijze.",
          "steps": [
            "Kies gebruikers- en taakmodus.",
            "Sla op om toe te passen; Opnieuw laden leest de huidige opgeslagen configuratie."
          ],
          "permissions": "Weergavevoorkeuren kunnen persoonlijk zijn. Model-, provider-, beveiligings- en serverwijzigingen vereisen configuratierechten.",
          "limits": "Sommige opties verschijnen alleen als een beheerder ze inschakelt of je browser ze ondersteunt. De opslagmelding bepaalt of de wijziging is toegepast.",
          "example": "Pas interactie aan de huidige werkstijl aan."
        }
      }
    },
    {
      "id": "webui.settings.aux_models",
      "area": "settings",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.settings.aux_models",
        "#btnResetAuxModels",
        "#btnApplyAuxModels"
      ],
      "source_refs": [
        "static/index.html:1385",
        "static/index.html:1386"
      ],
      "related": [
        "webui.settings.theme",
        "webui.settings.skin",
        "webui.settings.font_size"
      ],
      "locales": {
        "en": {
          "title": "Auxiliary models",
          "purpose": "Configure the model choices used for supported auxiliary tasks.",
          "when": "When the current configuration or presentation does not fit the intended workflow.",
          "steps": [
            "Open the auxiliary model controls and review each task’s model.",
            "Apply the changes or reset the overrides to the configured defaults."
          ],
          "permissions": "Appearance preferences can be personal. Model, provider, security and server changes require configuration rights.",
          "limits": "Some options appear only when enabled by an administrator or supported by your browser. Save feedback determines whether the change was applied.",
          "example": "Use the intended model for title generation or summarization."
        },
        "nl": {
          "title": "Ondersteunende modellen",
          "purpose": "Stel modelkeuzes voor ondersteunde hulptaken in.",
          "when": "Wanneer de huidige instelling of weergave niet past bij de bedoelde werkwijze.",
          "steps": [
            "Open de opties voor ondersteunende modellen en controleer het model per taak.",
            "Pas wijzigingen toe of herstel de afwijkingen naar de ingestelde standaard."
          ],
          "permissions": "Weergavevoorkeuren kunnen persoonlijk zijn. Model-, provider-, beveiligings- en serverwijzigingen vereisen configuratierechten.",
          "limits": "Sommige opties verschijnen alleen als een beheerder ze inschakelt of je browser ze ondersteunt. De opslagmelding bepaalt of de wijziging is toegepast.",
          "example": "Gebruik het bedoelde model voor titels of samenvattingen."
        }
      }
    },
    {
      "id": "webui.settings.advanced_model",
      "area": "settings",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.settings.advanced_model",
        "#settingsModelChip",
        "#mainAdvancedBtn",
        "#auxAdvancedClose",
        "#auxAdvancedCancel",
        "#auxAdvancedSave",
        "#auxAdvancedServiceTier",
        "#auxAdvancedExtraBody",
        "#auxAdvancedApiKeyClear"
      ],
      "source_refs": [
        "static/index.html:1373",
        "static/index.html:1375",
        "static/panels.js:13613",
        "static/panels.js:13617",
        "static/panels.js:13618",
        "static/panels.js:13662",
        "static/panels.js:13672",
        "static/panels.js:13674"
      ],
      "related": [
        "webui.settings.theme",
        "webui.settings.skin",
        "webui.settings.font_size"
      ],
      "locales": {
        "en": {
          "title": "Advanced model options",
          "purpose": "Review supported model endpoint, service tier, extra request body and credential overrides.",
          "when": "When the current configuration or presentation does not fit the intended workflow.",
          "steps": [
            "Open Advanced options for the model.",
            "Set only supported options and review provider policy before saving.",
            "Clear a credential override only when the replacement or default is understood."
          ],
          "permissions": "Appearance preferences can be personal. Model, provider, security and server changes require configuration rights.",
          "limits": "Some options appear only when enabled by an administrator or supported by your browser. Save feedback determines whether the change was applied.",
          "example": "Set a supported service tier for a model configuration."
        },
        "nl": {
          "title": "Geavanceerde modelopties",
          "purpose": "Bekijk ondersteunde modeladres-, serviceniveau-, verzoekinhoud- en inlogafwijkingen.",
          "when": "Wanneer de huidige instelling of weergave niet past bij de bedoelde werkwijze.",
          "steps": [
            "Open Geavanceerde opties voor het model.",
            "Stel alleen ondersteunde opties in en controleer providerbeleid voor opslaan.",
            "Wis een inlogafwijking alleen wanneer vervanging of standaard duidelijk is."
          ],
          "permissions": "Weergavevoorkeuren kunnen persoonlijk zijn. Model-, provider-, beveiligings- en serverwijzigingen vereisen configuratierechten.",
          "limits": "Sommige opties verschijnen alleen als een beheerder ze inschakelt of je browser ze ondersteunt. De opslagmelding bepaalt of de wijziging is toegepast.",
          "example": "Stel een ondersteund serviceniveau voor een modelconfiguratie in."
        }
      }
    },
    {
      "id": "webui.settings.notification_permission",
      "area": "settings",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.settings.notification_permission",
        "#notificationPermissionButton"
      ],
      "source_refs": [
        "static/index.html:1500",
        "static/index.html:1502"
      ],
      "related": [
        "webui.settings.theme",
        "webui.settings.skin",
        "webui.settings.font_size"
      ],
      "locales": {
        "en": {
          "title": "Allow and test browser notifications",
          "purpose": "Request browser-level notification permission and verify a local test notification.",
          "when": "When the current configuration or presentation does not fit the intended workflow.",
          "steps": [
            "Choose Enable notifications and answer the browser prompt.",
            "Choose Test notification; if blocked, inspect browser site permissions."
          ],
          "permissions": "Appearance preferences can be personal. Model, provider, security and server changes require configuration rights.",
          "limits": "Some options appear only when enabled by an administrator or supported by your browser. Save feedback determines whether the change was applied.",
          "example": "Check notifications after granting permission."
        },
        "nl": {
          "title": "Browsermeldingen toestaan en testen",
          "purpose": "Vraag browsertoestemming voor meldingen en controleer een lokale testmelding.",
          "when": "Wanneer de huidige instelling of weergave niet past bij de bedoelde werkwijze.",
          "steps": [
            "Kies Meldingen inschakelen en beantwoord de browservraag.",
            "Kies Testmelding; controleer bij blokkering de siterechten in de browser."
          ],
          "permissions": "Weergavevoorkeuren kunnen persoonlijk zijn. Model-, provider-, beveiligings- en serverwijzigingen vereisen configuratierechten.",
          "limits": "Sommige opties verschijnen alleen als een beheerder ze inschakelt of je browser ze ondersteunt. De opslagmelding bepaalt of de wijziging is toegepast.",
          "example": "Controleer meldingen na het geven van toestemming."
        }
      }
    },
    {
      "id": "webui.settings.password",
      "area": "settings",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.settings.password",
        "#settingsPassword",
        "#settingsCurrentPassword"
      ],
      "source_refs": [
        "static/index.html:1815",
        "static/index.html:1818"
      ],
      "related": [
        "webui.settings.theme",
        "webui.settings.skin",
        "webui.settings.font_size"
      ],
      "locales": {
        "en": {
          "title": "Change the application password",
          "purpose": "Update password authentication through the protected settings flow.",
          "when": "When the current configuration or presentation does not fit the intended workflow.",
          "steps": [
            "Enter the current password when requested and the new password.",
            "Save and verify the result without sharing either password."
          ],
          "permissions": "Appearance preferences can be personal. Model, provider, security and server changes require configuration rights.",
          "limits": "Some options appear only when enabled by an administrator or supported by your browser. Save feedback determines whether the change was applied.",
          "example": "Replace a password through the official settings form."
        },
        "nl": {
          "title": "Het toepassingswachtwoord wijzigen",
          "purpose": "Wijzig wachtwoordauthenticatie via de beschermde instellingenprocedure.",
          "when": "Wanneer de huidige instelling of weergave niet past bij de bedoelde werkwijze.",
          "steps": [
            "Vul indien gevraagd het huidige en het nieuwe wachtwoord in.",
            "Sla op en controleer het resultaat zonder wachtwoorden te delen."
          ],
          "permissions": "Weergavevoorkeuren kunnen persoonlijk zijn. Model-, provider-, beveiligings- en serverwijzigingen vereisen configuratierechten.",
          "limits": "Sommige opties verschijnen alleen als een beheerder ze inschakelt of je browser ze ondersteunt. De opslagmelding bepaalt of de wijziging is toegepast.",
          "example": "Vervang een wachtwoord via het officiële instellingenformulier."
        }
      }
    },
    {
      "id": "webui.settings.passkey",
      "area": "settings",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.settings.passkey",
        "#btnRegisterPasskey"
      ],
      "source_refs": [
        "static/index.html:1840",
        "static/panels.js:13239"
      ],
      "related": [
        "webui.settings.theme",
        "webui.settings.skin",
        "webui.settings.font_size"
      ],
      "locales": {
        "en": {
          "title": "Register or remove a passkey",
          "purpose": "Manage supported device-backed login credentials.",
          "when": "When the current configuration or presentation does not fit the intended workflow.",
          "steps": [
            "Choose Register passkey and complete the browser or device prompt.",
            "Review registered credentials before deleting one."
          ],
          "permissions": "Appearance preferences can be personal. Model, provider, security and server changes require configuration rights.",
          "limits": "Some options appear only when enabled by an administrator or supported by your browser. Save feedback determines whether the change was applied.",
          "example": "Add a trusted device for future sign-in."
        },
        "nl": {
          "title": "Een passkey registreren of verwijderen",
          "purpose": "Beheer ondersteunde apparaatgebonden inlogmiddelen.",
          "when": "Wanneer de huidige instelling of weergave niet past bij de bedoelde werkwijze.",
          "steps": [
            "Kies Passkey registreren en volg de browser- of apparaatvraag.",
            "Controleer geregistreerde inlogmiddelen voordat je er een verwijdert."
          ],
          "permissions": "Weergavevoorkeuren kunnen persoonlijk zijn. Model-, provider-, beveiligings- en serverwijzigingen vereisen configuratierechten.",
          "limits": "Sommige opties verschijnen alleen als een beheerder ze inschakelt of je browser ze ondersteunt. De opslagmelding bepaalt of de wijziging is toegepast.",
          "example": "Voeg een vertrouwd apparaat toe voor later inloggen."
        }
      }
    },
    {
      "id": "webui.settings.passwordless",
      "area": "settings",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.settings.passwordless",
        "#btnGoPasswordless"
      ],
      "source_refs": [
        "static/index.html:1841"
      ],
      "related": [
        "webui.settings.theme",
        "webui.settings.skin",
        "webui.settings.font_size"
      ],
      "locales": {
        "en": {
          "title": "Passwordless sign-in",
          "purpose": "Use the supported passwordless transition after setting up the required sign-in method.",
          "when": "When the current configuration or presentation does not fit the intended workflow.",
          "steps": [
            "Review available passkeys and recovery arrangements.",
            "Choose Go passwordless only after confirming the offered prerequisites."
          ],
          "permissions": "Appearance preferences can be personal. Model, provider, security and server changes require configuration rights.",
          "limits": "Some options appear only when enabled by an administrator or supported by your browser. Save feedback determines whether the change was applied.",
          "example": "Use a configured passkey-based sign-in flow."
        },
        "nl": {
          "title": "Inloggen zonder wachtwoord",
          "purpose": "Gebruik de ondersteunde overgang naar wachtwoordloos inloggen nadat de benodigde methode is ingesteld.",
          "when": "Wanneer de huidige instelling of weergave niet past bij de bedoelde werkwijze.",
          "steps": [
            "Controleer beschikbare passkeys en herstelmogelijkheden.",
            "Kies Wachtwoordloos alleen na controle van de aangeboden voorwaarden."
          ],
          "permissions": "Weergavevoorkeuren kunnen persoonlijk zijn. Model-, provider-, beveiligings- en serverwijzigingen vereisen configuratierechten.",
          "limits": "Sommige opties verschijnen alleen als een beheerder ze inschakelt of je browser ze ondersteunt. De opslagmelding bepaalt of de wijziging is toegepast.",
          "example": "Gebruik een ingestelde inlogprocedure met passkeys."
        }
      }
    },
    {
      "id": "webui.settings.disable_auth",
      "area": "settings",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.settings.disable_auth",
        "#settingsAuthDisabledAck",
        "#btnDisableAuth"
      ],
      "source_refs": [
        "static/index.html:1826",
        "static/index.html:1830"
      ],
      "related": [
        "webui.settings.theme",
        "webui.settings.skin",
        "webui.settings.font_size"
      ],
      "locales": {
        "en": {
          "title": "Disable authentication",
          "purpose": "Expose the explicit operator control for disabling application authentication.",
          "when": "When the current configuration or presentation does not fit the intended workflow.",
          "steps": [
            "Read the warning and deployment consequences.",
            "Use the required acknowledgement and confirmation only when authorised for that installation."
          ],
          "permissions": "Appearance preferences can be personal. Model, provider, security and server changes require configuration rights.",
          "limits": "Some options appear only when enabled by an administrator or supported by your browser. Save feedback determines whether the change was applied.",
          "example": "Recognize this control before managing a protected deployment."
        },
        "nl": {
          "title": "Authenticatie uitschakelen",
          "purpose": "Bied de expliciete beheeroptie om toepassingsauthenticatie uit te schakelen.",
          "when": "Wanneer de huidige instelling of weergave niet past bij de bedoelde werkwijze.",
          "steps": [
            "Lees waarschuwing en gevolgen voor de installatie.",
            "Gebruik de vereiste erkenning en bevestiging alleen wanneer je daarvoor bevoegd bent."
          ],
          "permissions": "Weergavevoorkeuren kunnen persoonlijk zijn. Model-, provider-, beveiligings- en serverwijzigingen vereisen configuratierechten.",
          "limits": "Sommige opties verschijnen alleen als een beheerder ze inschakelt of je browser ze ondersteunt. De opslagmelding bepaalt of de wijziging is toegepast.",
          "example": "Herken deze optie voordat je een beveiligde installatie beheert."
        }
      }
    },
    {
      "id": "webui.settings.signout",
      "area": "settings",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.settings.signout",
        "#btnSignOut"
      ],
      "source_refs": [
        "static/index.html:1831"
      ],
      "related": [
        "webui.settings.theme",
        "webui.settings.skin",
        "webui.settings.font_size"
      ],
      "locales": {
        "en": {
          "title": "Sign out",
          "purpose": "End the current application login session.",
          "when": "When the current configuration or presentation does not fit the intended workflow.",
          "steps": [
            "Preserve any important unsent draft.",
            "Choose Sign out and verify the login screen appears."
          ],
          "permissions": "Appearance preferences can be personal. Model, provider, security and server changes require configuration rights.",
          "limits": "Some options appear only when enabled by an administrator or supported by your browser. Save feedback determines whether the change was applied.",
          "example": "Leave a shared browser safely after finishing work."
        },
        "nl": {
          "title": "Uitloggen",
          "purpose": "Beëindig de huidige ingelogde toepassingssessie.",
          "when": "Wanneer de huidige instelling of weergave niet past bij de bedoelde werkwijze.",
          "steps": [
            "Bewaar belangrijke niet-verstuurde concepten.",
            "Kies Uitloggen en controleer dat het inlogscherm verschijnt."
          ],
          "permissions": "Weergavevoorkeuren kunnen persoonlijk zijn. Model-, provider-, beveiligings- en serverwijzigingen vereisen configuratierechten.",
          "limits": "Sommige opties verschijnen alleen als een beheerder ze inschakelt of je browser ze ondersteunt. De opslagmelding bepaalt of de wijziging is toegepast.",
          "example": "Verlaat een gedeelde browser na het afronden van werk."
        }
      }
    },
    {
      "id": "webui.settings.shutdown",
      "area": "settings",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.settings.shutdown",
        "#btnShutdownServer"
      ],
      "source_refs": [
        "static/index.html:1835"
      ],
      "related": [
        "webui.settings.theme",
        "webui.settings.skin",
        "webui.settings.font_size"
      ],
      "locales": {
        "en": {
          "title": "Shut down the server",
          "purpose": "Request server shutdown through the permitted management action.",
          "when": "When the current configuration or presentation does not fit the intended workflow.",
          "steps": [
            "Check active users and work with your operator.",
            "Choose Shut down only after reading the confirmation and recovery implications."
          ],
          "permissions": "Appearance preferences can be personal. Model, provider, security and server changes require configuration rights.",
          "limits": "Some options appear only when enabled by an administrator or supported by your browser. Save feedback determines whether the change was applied.",
          "example": "Perform a planned shutdown under operator control."
        },
        "nl": {
          "title": "De server afsluiten",
          "purpose": "Vraag serverafsluiting aan via de toegestane beheeractie.",
          "when": "Wanneer de huidige instelling of weergave niet past bij de bedoelde werkwijze.",
          "steps": [
            "Controleer actieve gebruikers en werk met je beheerder.",
            "Kies Afsluiten pas na het lezen van bevestiging en herstelgevolgen."
          ],
          "permissions": "Weergavevoorkeuren kunnen persoonlijk zijn. Model-, provider-, beveiligings- en serverwijzigingen vereisen configuratierechten.",
          "limits": "Sommige opties verschijnen alleen als een beheerder ze inschakelt of je browser ze ondersteunt. De opslagmelding bepaalt of de wijziging is toegepast.",
          "example": "Voer een geplande afsluiting onder beheerderstoezicht uit."
        }
      }
    },
    {
      "id": "webui.settings.composer_visibility",
      "area": "settings",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.settings.composer_visibility"
      ],
      "source_refs": [
        "static/panels.js"
      ],
      "related": [
        "webui.settings.theme",
        "webui.settings.skin",
        "webui.settings.font_size"
      ],
      "locales": {
        "en": {
          "title": "Composer control visibility and order",
          "purpose": "Choose which supported composer controls are shown and where they appear.",
          "when": "When the current configuration or presentation does not fit the intended workflow.",
          "steps": [
            "Open appearance or composer customization.",
            "Toggle or reorder offered controls and check the composer; hidden controls do not lose their permission checks."
          ],
          "permissions": "Appearance preferences can be personal. Model, provider, security and server changes require configuration rights.",
          "limits": "Some options appear only when enabled by an administrator or supported by your browser. Save feedback determines whether the change was applied.",
          "example": "Keep the composer focused on tools you use frequently."
        },
        "nl": {
          "title": "Zichtbaarheid en volgorde van berichtknoppen",
          "purpose": "Kies welke ondersteunde berichtknoppen zichtbaar zijn en waar ze staan.",
          "when": "Wanneer de huidige instelling of weergave niet past bij de bedoelde werkwijze.",
          "steps": [
            "Open weergave- of berichtveldaanpassing.",
            "Schakel aangeboden knoppen om of wijzig de volgorde en controleer het berichtveld; verborgen knoppen behouden hun rechtencontrole."
          ],
          "permissions": "Weergavevoorkeuren kunnen persoonlijk zijn. Model-, provider-, beveiligings- en serverwijzigingen vereisen configuratierechten.",
          "limits": "Sommige opties verschijnen alleen als een beheerder ze inschakelt of je browser ze ondersteunt. De opslagmelding bepaalt of de wijziging is toegepast.",
          "example": "Richt het berichtveld in op opties die je vaak gebruikt."
        }
      }
    },
    {
      "id": "webui.settings.navigation",
      "area": "settings",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.settings.navigation"
      ],
      "source_refs": [
        "static/index.html:415",
        "static/index.html:419",
        "static/index.html:423",
        "static/index.html:428",
        "static/index.html:432",
        "static/index.html:436",
        "static/index.html:440",
        "static/index.html:444",
        "static/index.html:448"
      ],
      "related": [
        "webui.settings.theme",
        "webui.settings.skin",
        "webui.settings.font_size"
      ],
      "locales": {
        "en": {
          "title": "Navigation tabs and order",
          "purpose": "Customize permitted tab presentation without granting access to hidden sections.",
          "when": "When the current configuration or presentation does not fit the intended workflow.",
          "steps": [
            "Open navigation customization in appearance settings.",
            "Choose visible tabs and order; save or wait for confirmation."
          ],
          "permissions": "Appearance preferences can be personal. Model, provider, security and server changes require configuration rights.",
          "limits": "Some options appear only when enabled by an administrator or supported by your browser. Save feedback determines whether the change was applied.",
          "example": "Put frequently used sections near the top."
        },
        "nl": {
          "title": "Navigatietabbladen en volgorde",
          "purpose": "Pas toegestane tabweergave aan zonder toegang tot verborgen onderdelen te geven.",
          "when": "Wanneer de huidige instelling of weergave niet past bij de bedoelde werkwijze.",
          "steps": [
            "Open navigatieaanpassing bij weergave-instellingen.",
            "Kies zichtbare tabbladen en volgorde; sla op of wacht op bevestiging."
          ],
          "permissions": "Weergavevoorkeuren kunnen persoonlijk zijn. Model-, provider-, beveiligings- en serverwijzigingen vereisen configuratierechten.",
          "limits": "Sommige opties verschijnen alleen als een beheerder ze inschakelt of je browser ze ondersteunt. De opslagmelding bepaalt of de wijziging is toegepast.",
          "example": "Zet veelgebruikte onderdelen bovenaan."
        }
      }
    },
    {
      "id": "webui.connections.onboarding",
      "area": "connections",
      "status": "conditional",
      "conditions": [
        "operator-setup",
        "provider-support"
      ],
      "anchors": [
        "?help_feature=webui.connections.onboarding",
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
      ],
      "source_refs": [
        "static/index.html:2009",
        "static/index.html:2010",
        "static/index.html:2011",
        "static/onboarding.js:185",
        "static/onboarding.js:204",
        "static/onboarding.js:214",
        "static/onboarding.js:220",
        "static/onboarding.js:319",
        "static/onboarding.js:338",
        "static/onboarding.js:351",
        "static/onboarding.js:368",
        "static/onboarding.js:372",
        "static/onboarding.js:405"
      ],
      "related": [
        "webui.connections.providers",
        "webui.connections.channel",
        "webui.connections.publish"
      ],
      "locales": {
        "en": {
          "title": "Initial provider and workspace setup",
          "purpose": "Complete the offered initial setup for a model provider, workspace and login protection.",
          "when": "When a task needs an approved external account, channel or tool connection.",
          "steps": [
            "Follow the setup steps using Back and Continue.",
            "Select a provider, supported endpoint and model; enter credentials only in the protected field.",
            "Choose the workspace and authentication settings; review before completion."
          ],
          "permissions": "Provider setup, channel management and account linking may require different rights.",
          "limits": "Connecting an account can expose its permitted data and actions to tools. Never paste credentials into chat or help search.",
          "example": "Prepare a new permitted installation for its first conversation."
        },
        "nl": {
          "title": "Eerste provider- en werkruimte-instelling",
          "purpose": "Rond de aangeboden eerste instelling van modelprovider, werkruimte en inlogbeveiliging af.",
          "when": "Wanneer een taak een goedgekeurd extern account, kanaal of toolkoppeling nodig heeft.",
          "steps": [
            "Volg de instelstappen met Terug en Doorgaan.",
            "Kies provider, ondersteund adres en model; vul inloggegevens alleen in het beschermde veld in.",
            "Kies werkruimte en authenticatie; controleer voor afronden."
          ],
          "permissions": "Providerinstellingen, kanaalbeheer en accountkoppeling kunnen verschillende rechten vereisen.",
          "limits": "Een account koppelen kan de toegestane gegevens en acties beschikbaar maken voor tools. Plak nooit inloggegevens in chat of de hulpzoekfunctie.",
          "example": "Bereid een nieuwe toegestane installatie voor op het eerste gesprek."
        }
      }
    },
    {
      "id": "webui.connections.oauth",
      "area": "connections",
      "status": "conditional",
      "conditions": [
        "operator-setup",
        "provider-support"
      ],
      "anchors": [
        "?help_feature=webui.connections.oauth",
        "#anthropicOAuthBtn",
        "#codexOAuthBtn"
      ],
      "source_refs": [
        "static/onboarding.js:230",
        "static/onboarding.js:332",
        "static/onboarding.js:708",
        "static/onboarding.js:709",
        "static/onboarding.js:827"
      ],
      "related": [
        "webui.connections.providers",
        "webui.connections.channel",
        "webui.connections.publish"
      ],
      "locales": {
        "en": {
          "title": "Provider OAuth sign-in",
          "purpose": "Use the offered provider authorization flow instead of pasting credentials into chat.",
          "when": "When a task needs an approved external account, channel or tool connection.",
          "steps": [
            "Choose the supported provider sign-in action.",
            "Verify the account in the authorization screen and complete the flow.",
            "Cancel if the wrong account is selected; never share the returned authorization code."
          ],
          "permissions": "Provider setup, channel management and account linking may require different rights.",
          "limits": "Connecting an account can expose its permitted data and actions to tools. Never paste credentials into chat or help search.",
          "example": "Connect the intended provider account during setup."
        },
        "nl": {
          "title": "Inloggen bij een provider via OAuth",
          "purpose": "Gebruik de aangeboden providertoestemming in plaats van inloggegevens in chat te plakken.",
          "when": "Wanneer een taak een goedgekeurd extern account, kanaal of toolkoppeling nodig heeft.",
          "steps": [
            "Kies de ondersteunde providerinlogactie.",
            "Controleer het account in het toestemmingsscherm en rond de procedure af.",
            "Annuleer bij het verkeerde account; deel nooit de teruggegeven autorisatiecode."
          ],
          "permissions": "Providerinstellingen, kanaalbeheer en accountkoppeling kunnen verschillende rechten vereisen.",
          "limits": "Een account koppelen kan de toegestane gegevens en acties beschikbaar maken voor tools. Plak nooit inloggegevens in chat of de hulpzoekfunctie.",
          "example": "Koppel het bedoelde provideraccount tijdens instellen."
        }
      }
    },
    {
      "id": "webui.planned.gateway",
      "area": "planned",
      "status": "conditional",
      "conditions": [
        "separate-rollout",
        "operator-confirmation",
        "default-off",
        "default-off"
      ],
      "anchors": [
        "?help_feature=webui.planned.gateway"
      ],
      "source_refs": [
        "api/tts_backend.py"
      ],
      "related": [
        "webui.planned.reporter",
        "webui.planned.central_memory"
      ],
      "locales": {
        "en": {
          "title": "Enforced model gateway",
          "purpose": "Prepared routing can require approved gateway credentials instead of direct provider access.",
          "when": "When deciding whether a prepared capability is actually available on your installation.",
          "steps": [
            "Ask the operator whether enforcement is active for your profile.",
            "Use only that profile’s approved connection settings; do not borrow another profile’s credentials."
          ],
          "permissions": "These capabilities depend on a separate rollout and operator configuration.",
          "limits": "Documentation is not an activation switch. Do not depend on this capability until your operator confirms it is enabled.",
          "example": "Understand why a model request is refused when required profile credentials are missing."
        },
        "nl": {
          "title": "Verplichte modelgateway",
          "purpose": "Voorbereide routering kan goedgekeurde gatewaygegevens vereisen in plaats van directe providertoegang.",
          "when": "Bij het bepalen of een voorbereide mogelijkheid op jouw installatie echt beschikbaar is.",
          "steps": [
            "Vraag de beheerder of afdwinging voor jouw profiel actief is.",
            "Gebruik alleen goedgekeurde instellingen van dat profiel; leen geen inloggegevens van een ander profiel."
          ],
          "permissions": "Deze mogelijkheden vereisen een afzonderlijke uitrol en configuratie door een beheerder.",
          "limits": "Documentatie schakelt niets in. Reken pas op deze mogelijkheid nadat je beheerder heeft bevestigd dat die actief is.",
          "example": "Begrijp waarom een modelverzoek wordt geweigerd wanneer verplichte profielgegevens ontbreken."
        }
      }
    },
    {
      "id": "webui.planned.reporter",
      "area": "planned",
      "status": "conditional",
      "conditions": [
        "separate-rollout",
        "operator-confirmation",
        "default-off",
        "default-off"
      ],
      "anchors": [
        "?help_feature=webui.planned.reporter"
      ],
      "source_refs": [
        "api/tts_backend.py"
      ],
      "related": [
        "webui.planned.gateway",
        "webui.planned.central_memory"
      ],
      "locales": {
        "en": {
          "title": "Optional support diagnostics reporter",
          "purpose": "Prepared reporting can send explicitly configured diagnostic data to a control service.",
          "when": "When deciding whether a prepared capability is actually available on your installation.",
          "steps": [
            "Ask the operator which reporting mode, destination and data scope are enabled.",
            "Review data policy before opting into additional diagnostics."
          ],
          "permissions": "These capabilities depend on a separate rollout and operator configuration.",
          "limits": "Documentation is not an activation switch. Do not depend on this capability until your operator confirms it is enabled.",
          "example": "Distinguish local troubleshooting from activated remote diagnostic reporting."
        },
        "nl": {
          "title": "Optionele rapportage van ondersteuningsdiagnostiek",
          "purpose": "Voorbereide rapportage kan expliciet ingestelde diagnostische gegevens naar een beheerdienst sturen.",
          "when": "Bij het bepalen of een voorbereide mogelijkheid op jouw installatie echt beschikbaar is.",
          "steps": [
            "Vraag de beheerder welke rapportagemodus, bestemming en gegevensscope actief zijn.",
            "Controleer gegevensbeleid voordat extra diagnostiek wordt ingeschakeld."
          ],
          "permissions": "Deze mogelijkheden vereisen een afzonderlijke uitrol en configuratie door een beheerder.",
          "limits": "Documentatie schakelt niets in. Reken pas op deze mogelijkheid nadat je beheerder heeft bevestigd dat die actief is.",
          "example": "Onderscheid lokale probleemoplossing van ingeschakelde diagnostische rapportage op afstand."
        }
      }
    },
    {
      "id": "webui.planned.central_memory",
      "area": "planned",
      "status": "planned",
      "conditions": [
        "separate-rollout",
        "operator-confirmation",
        "default-off",
        "default-off"
      ],
      "anchors": [
        "?help_feature=webui.planned.central_memory"
      ],
      "source_refs": [
        "api/tts_backend.py"
      ],
      "related": [
        "webui.planned.gateway",
        "webui.planned.reporter"
      ],
      "locales": {
        "en": {
          "title": "Central memory hub rollout",
          "purpose": "A broader managed memory hub requires separate backend and policy rollout beyond the current read-only explorer.",
          "when": "When deciding whether a prepared capability is actually available on your installation.",
          "steps": [
            "Use the currently available owner-scoped reader.",
            "Wait for an explicitly deployed hub workflow before expecting broader memory management."
          ],
          "permissions": "These capabilities depend on a separate rollout and operator configuration.",
          "limits": "Documentation is not an activation switch. Do not depend on this capability until your operator confirms it is enabled.",
          "example": "Avoid assuming the explorer can edit or expose all organisation memory."
        },
        "nl": {
          "title": "Uitrol van een centrale geheugenhub",
          "purpose": "Een bredere beheerde geheugenhub vereist aparte backend- en beleidsuitrol naast de huidige alleen-lezenverkenner.",
          "when": "Bij het bepalen of een voorbereide mogelijkheid op jouw installatie echt beschikbaar is.",
          "steps": [
            "Gebruik de momenteel beschikbare eigenaargebonden lezer.",
            "Wacht op een expliciet uitgerolde hubprocedure voordat je breder geheugenbeheer verwacht."
          ],
          "permissions": "Deze mogelijkheden vereisen een afzonderlijke uitrol en configuratie door een beheerder.",
          "limits": "Documentatie schakelt niets in. Reken pas op deze mogelijkheid nadat je beheerder heeft bevestigd dat die actief is.",
          "example": "Neem niet aan dat de verkenner al organisatiegeheugen kan bewerken of tonen."
        }
      }
    },
    {
      "id": "webui.sessions.rename",
      "area": "sessions",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.sessions.rename"
      ],
      "source_refs": [
        "static/commands.js"
      ],
      "related": [
        "webui.sessions.new",
        "webui.sessions.search",
        "webui.sessions.split"
      ],
      "locales": {
        "en": {
          "title": "Rename a conversation",
          "purpose": "Give a supported conversation a recognizable title.",
          "when": "When organising, revisiting or transferring work from a conversation.",
          "steps": [
            "Open the conversation row menu and choose Rename.",
            "Enter the title and confirm the edit.",
            "Composer shortcut: /title. Review any required arguments in the command suggestions."
          ],
          "permissions": "You need access to the conversation. Sharing and deletion can require additional rights.",
          "limits": "Exported or shared content may contain conversation details. Review the destination and recipients.",
          "example": "Name a conversation after its project deliverable."
        },
        "nl": {
          "title": "Een gesprek hernoemen",
          "purpose": "Geef een ondersteund gesprek een herkenbare titel.",
          "when": "Bij het ordenen, terugvinden of overdragen van werk uit een gesprek.",
          "steps": [
            "Open het menu bij het gesprek en kies Hernoemen.",
            "Vul de titel in en bevestig de wijziging.",
            "Snelopdracht in het berichtveld: /title. Controleer eventuele argumenten in de opdrachtsuggesties."
          ],
          "permissions": "Je hebt toegang tot het gesprek nodig. Delen en verwijderen kunnen extra rechten vereisen.",
          "limits": "Geëxporteerde of gedeelde inhoud kan gespreksgegevens bevatten. Controleer bestemming en ontvangers.",
          "example": "Noem een gesprek naar het projectresultaat."
        }
      }
    },
    {
      "id": "webui.sessions.pin",
      "area": "sessions",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.sessions.pin"
      ],
      "source_refs": [
        "static/sessions.js"
      ],
      "related": [
        "webui.sessions.new",
        "webui.sessions.search",
        "webui.sessions.split"
      ],
      "locales": {
        "en": {
          "title": "Pin or unpin a conversation",
          "purpose": "Keep an important conversation in the pinned section.",
          "when": "When organising, revisiting or transferring work from a conversation.",
          "steps": [
            "Open the conversation menu and choose Pin.",
            "Choose Unpin later to return it to the ordinary list."
          ],
          "permissions": "You need access to the conversation. Sharing and deletion can require additional rights.",
          "limits": "Exported or shared content may contain conversation details. Review the destination and recipients.",
          "example": "Keep ongoing weekly work easy to find."
        },
        "nl": {
          "title": "Een gesprek vastzetten of losmaken",
          "purpose": "Houd een belangrijk gesprek in het vastgezette gedeelte.",
          "when": "Bij het ordenen, terugvinden of overdragen van werk uit een gesprek.",
          "steps": [
            "Open het gespreksmenu en kies Vastzetten.",
            "Kies later Losmaken om het terug te zetten in de gewone lijst."
          ],
          "permissions": "Je hebt toegang tot het gesprek nodig. Delen en verwijderen kunnen extra rechten vereisen.",
          "limits": "Geëxporteerde of gedeelde inhoud kan gespreksgegevens bevatten. Controleer bestemming en ontvangers.",
          "example": "Houd doorlopend weekwerk gemakkelijk vindbaar."
        }
      }
    },
    {
      "id": "webui.sessions.move_project",
      "area": "sessions",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.sessions.move_project"
      ],
      "source_refs": [
        "static/sessions.js"
      ],
      "related": [
        "webui.sessions.new",
        "webui.sessions.search",
        "webui.sessions.split"
      ],
      "locales": {
        "en": {
          "title": "Move a conversation to a project",
          "purpose": "Associate an accessible conversation with the intended project.",
          "when": "When organising, revisiting or transferring work from a conversation.",
          "steps": [
            "Choose Move to project in the conversation menu.",
            "Select an allowed project and inspect its resulting association."
          ],
          "permissions": "You need access to the conversation. Sharing and deletion can require additional rights.",
          "limits": "Exported or shared content may contain conversation details. Review the destination and recipients.",
          "example": "Group an earlier conversation under a new project."
        },
        "nl": {
          "title": "Een gesprek naar een project verplaatsen",
          "purpose": "Koppel een toegankelijk gesprek aan het bedoelde project.",
          "when": "Bij het ordenen, terugvinden of overdragen van werk uit een gesprek.",
          "steps": [
            "Kies Naar project verplaatsen in het gespreksmenu.",
            "Kies een toegestaan project en controleer de koppeling."
          ],
          "permissions": "Je hebt toegang tot het gesprek nodig. Delen en verwijderen kunnen extra rechten vereisen.",
          "limits": "Geëxporteerde of gedeelde inhoud kan gespreksgegevens bevatten. Controleer bestemming en ontvangers.",
          "example": "Groepeer een eerder gesprek onder een nieuw project."
        }
      }
    },
    {
      "id": "webui.sessions.archive",
      "area": "sessions",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.sessions.archive"
      ],
      "source_refs": [
        "static/sessions.js"
      ],
      "related": [
        "webui.sessions.new",
        "webui.sessions.search",
        "webui.sessions.split"
      ],
      "locales": {
        "en": {
          "title": "Archive, restore or hide a conversation",
          "purpose": "Remove a conversation from the active list without treating it as permanently deleted.",
          "when": "When organising, revisiting or transferring work from a conversation.",
          "steps": [
            "Choose Archive or the offered Hide external action.",
            "Use the archived view and Restore when available to return it."
          ],
          "permissions": "You need access to the conversation. Sharing and deletion can require additional rights.",
          "limits": "Exported or shared content may contain conversation details. Review the destination and recipients.",
          "example": "Hide completed work while retaining permitted history."
        },
        "nl": {
          "title": "Een gesprek archiveren, herstellen of verbergen",
          "purpose": "Haal een gesprek uit de actieve lijst zonder dit als definitief verwijderd te behandelen.",
          "when": "Bij het ordenen, terugvinden of overdragen van werk uit een gesprek.",
          "steps": [
            "Kies Archiveren of de aangeboden actie Extern verbergen.",
            "Gebruik het archiefoverzicht en Herstellen indien beschikbaar om het terug te zetten."
          ],
          "permissions": "Je hebt toegang tot het gesprek nodig. Delen en verwijderen kunnen extra rechten vereisen.",
          "limits": "Geëxporteerde of gedeelde inhoud kan gespreksgegevens bevatten. Controleer bestemming en ontvangers.",
          "example": "Verberg afgerond werk en behoud toegestane geschiedenis."
        }
      }
    },
    {
      "id": "webui.sessions.delete",
      "area": "sessions",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.sessions.delete"
      ],
      "source_refs": [
        "static/sessions.js"
      ],
      "related": [
        "webui.sessions.new",
        "webui.sessions.search",
        "webui.sessions.split"
      ],
      "locales": {
        "en": {
          "title": "Delete a conversation",
          "purpose": "Remove a supported conversation using its deletion confirmation.",
          "when": "When organising, revisiting or transferring work from a conversation.",
          "steps": [
            "Choose Delete on the intended conversation.",
            "Review what will be removed and confirm only if it is no longer needed."
          ],
          "permissions": "You need access to the conversation. Sharing and deletion can require additional rights.",
          "limits": "Exported or shared content may contain conversation details. Review the destination and recipients.",
          "example": "Remove an obsolete disposable test conversation."
        },
        "nl": {
          "title": "Een gesprek verwijderen",
          "purpose": "Verwijder een ondersteund gesprek via de verwijderbevestiging.",
          "when": "Bij het ordenen, terugvinden of overdragen van werk uit een gesprek.",
          "steps": [
            "Kies Verwijderen bij het bedoelde gesprek.",
            "Controleer wat wordt verwijderd en bevestig alleen als het niet meer nodig is."
          ],
          "permissions": "Je hebt toegang tot het gesprek nodig. Delen en verwijderen kunnen extra rechten vereisen.",
          "limits": "Geëxporteerde of gedeelde inhoud kan gespreksgegevens bevatten. Controleer bestemming en ontvangers.",
          "example": "Verwijder een verouderd tijdelijk testgesprek."
        }
      }
    },
    {
      "id": "webui.sessions.regenerate_title",
      "area": "sessions",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.sessions.regenerate_title"
      ],
      "source_refs": [
        "static/sessions.js"
      ],
      "related": [
        "webui.sessions.new",
        "webui.sessions.search",
        "webui.sessions.split"
      ],
      "locales": {
        "en": {
          "title": "Regenerate a conversation title",
          "purpose": "Request a fresh generated title for a conversation.",
          "when": "When organising, revisiting or transferring work from a conversation.",
          "steps": [
            "Choose Regenerate title from the conversation menu.",
            "Wait for completion and review the new label."
          ],
          "permissions": "You need access to the conversation. Sharing and deletion can require additional rights.",
          "limits": "Exported or shared content may contain conversation details. Review the destination and recipients.",
          "example": "Update the title after the conversation changes topic."
        },
        "nl": {
          "title": "Een gesprekstitel opnieuw maken",
          "purpose": "Vraag een nieuw gegenereerde titel voor een gesprek.",
          "when": "Bij het ordenen, terugvinden of overdragen van werk uit een gesprek.",
          "steps": [
            "Kies Titel opnieuw maken in het gespreksmenu.",
            "Wacht op voltooiing en controleer het nieuwe label."
          ],
          "permissions": "Je hebt toegang tot het gesprek nodig. Delen en verwijderen kunnen extra rechten vereisen.",
          "limits": "Geëxporteerde of gedeelde inhoud kan gespreksgegevens bevatten. Controleer bestemming en ontvangers.",
          "example": "Werk de titel bij nadat het gesprek van onderwerp verandert."
        }
      }
    },
    {
      "id": "webui.sessions.link",
      "area": "sessions",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.sessions.link"
      ],
      "source_refs": [
        "static/sessions.js"
      ],
      "related": [
        "webui.sessions.new",
        "webui.sessions.search",
        "webui.sessions.split"
      ],
      "locales": {
        "en": {
          "title": "Copy a conversation link or reference",
          "purpose": "Copy a navigation reference to an accessible conversation.",
          "when": "When organising, revisiting or transferring work from a conversation.",
          "steps": [
            "Choose the offered copy-link or internal-reference action.",
            "Paste it only where recipients already have the required access."
          ],
          "permissions": "You need access to the conversation. Sharing and deletion can require additional rights.",
          "limits": "Exported or shared content may contain conversation details. Review the destination and recipients.",
          "example": "Refer a colleague to an already shared conversation."
        },
        "nl": {
          "title": "Een gesprekslink of verwijzing kopiëren",
          "purpose": "Kopieer een navigatieverwijzing naar een toegankelijk gesprek.",
          "when": "Bij het ordenen, terugvinden of overdragen van werk uit een gesprek.",
          "steps": [
            "Kies de aangeboden actie voor link of interne verwijzing kopiëren.",
            "Plak alleen waar ontvangers al de benodigde toegang hebben."
          ],
          "permissions": "Je hebt toegang tot het gesprek nodig. Delen en verwijderen kunnen extra rechten vereisen.",
          "limits": "Geëxporteerde of gedeelde inhoud kan gespreksgegevens bevatten. Controleer bestemming en ontvangers.",
          "example": "Verwijs een collega naar een al gedeeld gesprek."
        }
      }
    },
    {
      "id": "webui.chat.save_prompt",
      "area": "chat",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.chat.save_prompt"
      ],
      "source_refs": [
        "static/messages.js"
      ],
      "related": [
        "webui.chat.send",
        "webui.chat.normal",
        "webui.chat.super"
      ],
      "locales": {
        "en": {
          "title": "Save or delete a reusable prompt",
          "purpose": "Store the current composer text for later reuse or remove an obsolete saved prompt.",
          "when": "While preparing a request or reviewing a response in the active conversation.",
          "steps": [
            "Write the reusable text, open Saved prompts and choose Save current input.",
            "Use the delete control beside an unwanted saved prompt."
          ],
          "permissions": "Work in a conversation you can access. Tools and models still follow your permissions.",
          "limits": "Model output may be wrong. Review results before using them.",
          "example": "Save a generic review request without private case details."
        },
        "nl": {
          "title": "Een herbruikbare prompt opslaan of verwijderen",
          "purpose": "Bewaar de huidige berichttekst voor hergebruik of verwijder een verouderde opgeslagen prompt.",
          "when": "Bij het voorbereiden van een verzoek of beoordelen van een antwoord in het actieve gesprek.",
          "steps": [
            "Schrijf de herbruikbare tekst, open Opgeslagen prompts en kies Huidige invoer opslaan.",
            "Gebruik de verwijderknop bij een ongewenste opgeslagen prompt."
          ],
          "permissions": "Werk in een gesprek waartoe je toegang hebt. Tools en modellen blijven gebonden aan je rechten.",
          "limits": "Modeluitvoer kan onjuist zijn. Controleer resultaten voor gebruik.",
          "example": "Bewaar een algemeen beoordelingsverzoek zonder privégegevens van een casus."
        }
      }
    },
    {
      "id": "webui.bots.knowledge_upload",
      "area": "bots",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.bots.knowledge_upload"
      ],
      "source_refs": [
        "static/bot-builder.js",
        "static/bot-knowledge.js"
      ],
      "related": [
        "webui.bots.select",
        "webui.bots.create",
        "webui.bots.identity"
      ],
      "locales": {
        "en": {
          "title": "Upload bot knowledge documents",
          "purpose": "Add supported documents to the bot’s available knowledge library without selecting them automatically.",
          "when": "When preparing or maintaining a specialist assistant for a defined role.",
          "steps": [
            "In Knowledge, choose files to upload.",
            "Use PDF, DOCX, Markdown, text, CSV or JSON up to 10 MB per document.",
            "After upload, select intended files and choose Save knowledge."
          ],
          "permissions": "Bot visibility, editing rights and permitted tools are checked separately.",
          "limits": "A bot cannot grant itself permissions or make unavailable connections usable.",
          "example": "Upload a reference document, then deliberately make it available to the bot."
        },
        "nl": {
          "title": "Kennisdocumenten voor een bot uploaden",
          "purpose": "Voeg ondersteunde documenten toe aan de beschikbare botkennis zonder ze automatisch te selecteren.",
          "when": "Bij het voorbereiden of onderhouden van een specialistische assistent met een duidelijke rol.",
          "steps": [
            "Kies bij Kennis bestanden om te uploaden.",
            "Gebruik PDF, DOCX, Markdown, tekst, CSV of JSON tot 10 MB per document.",
            "Kies na upload de bedoelde bestanden en kies Kennis opslaan."
          ],
          "permissions": "Zichtbaarheid van bots, bewerkrechten en toegestane tools worden afzonderlijk gecontroleerd.",
          "limits": "Een bot kan zichzelf geen rechten geven of onbeschikbare koppelingen bruikbaar maken.",
          "example": "Upload een referentiedocument en maak het daarna bewust beschikbaar voor de bot."
        }
      }
    },
    {
      "id": "webui.bots.knowledge_legacy",
      "area": "bots",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.bots.knowledge_legacy"
      ],
      "source_refs": [
        "static/bot-builder.js",
        "static/bot-knowledge.js"
      ],
      "related": [
        "webui.bots.select",
        "webui.bots.create",
        "webui.bots.identity"
      ],
      "locales": {
        "en": {
          "title": "Previously configured knowledge references",
          "purpose": "Inspect preserved workspace-based knowledge references separately from uploaded documents.",
          "when": "When preparing or maintaining a specialist assistant for a defined role.",
          "steps": [
            "Expand Previously configured workspace references.",
            "Check the conversation’s workspace; upload documents if they should be available across the bot’s chats."
          ],
          "permissions": "Bot visibility, editing rights and permitted tools are checked separately.",
          "limits": "A bot cannot grant itself permissions or make unavailable connections usable.",
          "example": "Understand why an old reference depends on the active workspace."
        },
        "nl": {
          "title": "Eerder ingestelde kennisverwijzingen",
          "purpose": "Bekijk behouden werkruimtegebonden kennisverwijzingen los van geüploade documenten.",
          "when": "Bij het voorbereiden of onderhouden van een specialistische assistent met een duidelijke rol.",
          "steps": [
            "Klap Eerder ingestelde werkruimteverwijzingen open.",
            "Controleer de gesprekswerkruimte; upload documenten als deze in alle botgesprekken beschikbaar moeten zijn."
          ],
          "permissions": "Zichtbaarheid van bots, bewerkrechten en toegestane tools worden afzonderlijk gecontroleerd.",
          "limits": "Een bot kan zichzelf geen rechten geven of onbeschikbare koppelingen bruikbaar maken.",
          "example": "Begrijp waarom een oude verwijzing afhangt van de actieve werkruimte."
        }
      }
    },
    {
      "id": "webui.memory.overview",
      "area": "memory",
      "status": "conditional",
      "conditions": [
        "hq-memory-reader",
        "bank-data-availability"
      ],
      "anchors": [
        "?help_feature=webui.memory.overview"
      ],
      "source_refs": [
        "static/memory_dashboard.js",
        "api/memdash_scope.py",
        "api/memdash_views.py"
      ],
      "related": [
        "webui.memory.personal",
        "webui.memory.company",
        "webui.memory.project"
      ],
      "locales": {
        "en": {
          "title": "Bank overview",
          "purpose": "Read counts and summary statistics for the selected bank.",
          "when": "When checking stored context, its source or the audience allowed to read it.",
          "steps": [
            "Open Memory explorer and choose the permitted bank.",
            "Open Bank overview; use the available search, filters or detail controls."
          ],
          "permissions": "Only stores and documents permitted for your identity are available. Admin status does not open another person’s private memory.",
          "limits": "This is a read-only view. Empty or unavailable data is not proof that nothing happened. Available views depend on the bank’s stored schema; editing, confirming or forgetting records is not enabled by this guide.",
          "example": "Compare the scope of two banks without mixing their records."
        },
        "nl": {
          "title": "Bankoverzicht",
          "purpose": "Lees aantallen en samenvattende statistieken van de gekozen bank.",
          "when": "Bij het controleren van opgeslagen context, de bron of de doelgroep die deze mag lezen.",
          "steps": [
            "Open Geheugenverkenner en kies de toegestane bank.",
            "Open Bankoverzicht; gebruik beschikbare zoek-, filter- of detailopties."
          ],
          "permissions": "Alleen opslag en documenten die voor jouw identiteit zijn toegestaan zijn beschikbaar. Beheerdersrechten openen geen privégeheugen van een ander.",
          "limits": "Dit is een alleen-lezenweergave. Lege of onbeschikbare gegevens bewijzen niet dat niets gebeurde. Beschikbare weergaven hangen af van de opgeslagen bankstructuur; deze gids schakelt bewerken, bevestigen of vergeten niet in.",
          "example": "Vergelijk de omvang van twee banken zonder records te mengen."
        }
      }
    },
    {
      "id": "webui.memory.today",
      "area": "memory",
      "status": "conditional",
      "conditions": [
        "hq-memory-reader",
        "bank-data-availability"
      ],
      "anchors": [
        "?help_feature=webui.memory.today"
      ],
      "source_refs": [
        "static/memory_dashboard.js",
        "api/memdash_scope.py",
        "api/memdash_views.py"
      ],
      "related": [
        "webui.memory.personal",
        "webui.memory.company",
        "webui.memory.project"
      ],
      "locales": {
        "en": {
          "title": "Today and digest",
          "purpose": "Read the selected bank’s available daily digest and recent highlights.",
          "when": "When checking stored context, its source or the audience allowed to read it.",
          "steps": [
            "Open Memory explorer and choose the permitted bank.",
            "Open Today and digest; use the available search, filters or detail controls."
          ],
          "permissions": "Only stores and documents permitted for your identity are available. Admin status does not open another person’s private memory.",
          "limits": "This is a read-only view. Empty or unavailable data is not proof that nothing happened. Available views depend on the bank’s stored schema; editing, confirming or forgetting records is not enabled by this guide.",
          "example": "Inspect today’s stored context."
        },
        "nl": {
          "title": "Vandaag en dagsamenvatting",
          "purpose": "Lees de beschikbare dagsamenvatting en recente hoogtepunten van de gekozen bank.",
          "when": "Bij het controleren van opgeslagen context, de bron of de doelgroep die deze mag lezen.",
          "steps": [
            "Open Geheugenverkenner en kies de toegestane bank.",
            "Open Vandaag en dagsamenvatting; gebruik beschikbare zoek-, filter- of detailopties."
          ],
          "permissions": "Alleen opslag en documenten die voor jouw identiteit zijn toegestaan zijn beschikbaar. Beheerdersrechten openen geen privégeheugen van een ander.",
          "limits": "Dit is een alleen-lezenweergave. Lege of onbeschikbare gegevens bewijzen niet dat niets gebeurde. Beschikbare weergaven hangen af van de opgeslagen bankstructuur; deze gids schakelt bewerken, bevestigen of vergeten niet in.",
          "example": "Bekijk de vandaag opgeslagen context."
        }
      }
    },
    {
      "id": "webui.memory.visualiser",
      "area": "memory",
      "status": "conditional",
      "conditions": [
        "hq-memory-reader",
        "bank-data-availability"
      ],
      "anchors": [
        "?help_feature=webui.memory.visualiser"
      ],
      "source_refs": [
        "static/memory_dashboard.js",
        "api/memdash_scope.py",
        "api/memdash_views.py"
      ],
      "related": [
        "webui.memory.personal",
        "webui.memory.company",
        "webui.memory.project"
      ],
      "locales": {
        "en": {
          "title": "Memory visualiser",
          "purpose": "Explore a visual representation of the selected bank when sufficient data is available.",
          "when": "When checking stored context, its source or the audience allowed to read it.",
          "steps": [
            "Open Memory explorer and choose the permitted bank.",
            "Open Memory visualiser; use the available search, filters or detail controls."
          ],
          "permissions": "Only stores and documents permitted for your identity are available. Admin status does not open another person’s private memory.",
          "limits": "This is a read-only view. Empty or unavailable data is not proof that nothing happened. Available views depend on the bank’s stored schema; editing, confirming or forgetting records is not enabled by this guide.",
          "example": "Inspect relationships in the available visualisation."
        },
        "nl": {
          "title": "Geheugenvisualisatie",
          "purpose": "Verken een visuele weergave van de gekozen bank wanneer genoeg gegevens beschikbaar zijn.",
          "when": "Bij het controleren van opgeslagen context, de bron of de doelgroep die deze mag lezen.",
          "steps": [
            "Open Geheugenverkenner en kies de toegestane bank.",
            "Open Geheugenvisualisatie; gebruik beschikbare zoek-, filter- of detailopties."
          ],
          "permissions": "Alleen opslag en documenten die voor jouw identiteit zijn toegestaan zijn beschikbaar. Beheerdersrechten openen geen privégeheugen van een ander.",
          "limits": "Dit is een alleen-lezenweergave. Lege of onbeschikbare gegevens bewijzen niet dat niets gebeurde. Beschikbare weergaven hangen af van de opgeslagen bankstructuur; deze gids schakelt bewerken, bevestigen of vergeten niet in.",
          "example": "Bekijk verbanden in de beschikbare visualisatie."
        }
      }
    },
    {
      "id": "webui.memory.review",
      "area": "memory",
      "status": "conditional",
      "conditions": [
        "hq-memory-reader",
        "bank-data-availability"
      ],
      "anchors": [
        "?help_feature=webui.memory.review"
      ],
      "source_refs": [
        "static/memory_dashboard.js",
        "api/memdash_scope.py",
        "api/memdash_views.py"
      ],
      "related": [
        "webui.memory.personal",
        "webui.memory.company",
        "webui.memory.project"
      ],
      "locales": {
        "en": {
          "title": "Memory review queues",
          "purpose": "Inspect records marked for review without assuming write actions are enabled.",
          "when": "When checking stored context, its source or the audience allowed to read it.",
          "steps": [
            "Open Memory explorer and choose the permitted bank.",
            "Open Memory review queues; use the available search, filters or detail controls."
          ],
          "permissions": "Only stores and documents permitted for your identity are available. Admin status does not open another person’s private memory.",
          "limits": "This is a read-only view. Empty or unavailable data is not proof that nothing happened. Available views depend on the bank’s stored schema; editing, confirming or forgetting records is not enabled by this guide.",
          "example": "Read a questionable record and its recorded trust state."
        },
        "nl": {
          "title": "Beoordelingswachtrijen voor geheugen",
          "purpose": "Bekijk records die voor beoordeling zijn gemarkeerd zonder aan te nemen dat schrijfacties actief zijn.",
          "when": "Bij het controleren van opgeslagen context, de bron of de doelgroep die deze mag lezen.",
          "steps": [
            "Open Geheugenverkenner en kies de toegestane bank.",
            "Open Beoordelingswachtrijen voor geheugen; gebruik beschikbare zoek-, filter- of detailopties."
          ],
          "permissions": "Alleen opslag en documenten die voor jouw identiteit zijn toegestaan zijn beschikbaar. Beheerdersrechten openen geen privégeheugen van een ander.",
          "limits": "Dit is een alleen-lezenweergave. Lege of onbeschikbare gegevens bewijzen niet dat niets gebeurde. Beschikbare weergaven hangen af van de opgeslagen bankstructuur; deze gids schakelt bewerken, bevestigen of vergeten niet in.",
          "example": "Lees een twijfelachtig record en de vastgelegde vertrouwensstatus."
        }
      }
    },
    {
      "id": "webui.memory.profile",
      "area": "memory",
      "status": "conditional",
      "conditions": [
        "hq-memory-reader",
        "bank-data-availability"
      ],
      "anchors": [
        "?help_feature=webui.memory.profile"
      ],
      "source_refs": [
        "static/memory_dashboard.js",
        "api/memdash_scope.py",
        "api/memdash_views.py"
      ],
      "related": [
        "webui.memory.personal",
        "webui.memory.company",
        "webui.memory.project"
      ],
      "locales": {
        "en": {
          "title": "Context bank profile",
          "purpose": "Inspect inferred profile information supplied by the selected bank.",
          "when": "When checking stored context, its source or the audience allowed to read it.",
          "steps": [
            "Open Memory explorer and choose the permitted bank.",
            "Open Context bank profile; use the available search, filters or detail controls."
          ],
          "permissions": "Only stores and documents permitted for your identity are available. Admin status does not open another person’s private memory.",
          "limits": "This is a read-only view. Empty or unavailable data is not proof that nothing happened. Available views depend on the bank’s stored schema; editing, confirming or forgetting records is not enabled by this guide.",
          "example": "Review an inferred preference as evidence, not guaranteed truth."
        },
        "nl": {
          "title": "Profiel van de contextbank",
          "purpose": "Bekijk afgeleide profielinformatie van de gekozen bank.",
          "when": "Bij het controleren van opgeslagen context, de bron of de doelgroep die deze mag lezen.",
          "steps": [
            "Open Geheugenverkenner en kies de toegestane bank.",
            "Open Profiel van de contextbank; gebruik beschikbare zoek-, filter- of detailopties."
          ],
          "permissions": "Alleen opslag en documenten die voor jouw identiteit zijn toegestaan zijn beschikbaar. Beheerdersrechten openen geen privégeheugen van een ander.",
          "limits": "Dit is een alleen-lezenweergave. Lege of onbeschikbare gegevens bewijzen niet dat niets gebeurde. Beschikbare weergaven hangen af van de opgeslagen bankstructuur; deze gids schakelt bewerken, bevestigen of vergeten niet in.",
          "example": "Beoordeel een afgeleide voorkeur als aanwijzing en niet als zekere waarheid."
        }
      }
    },
    {
      "id": "webui.memory.lifecycle",
      "area": "memory",
      "status": "conditional",
      "conditions": [
        "hq-memory-reader",
        "bank-data-availability"
      ],
      "anchors": [
        "?help_feature=webui.memory.lifecycle"
      ],
      "source_refs": [
        "static/memory_dashboard.js",
        "api/memdash_scope.py",
        "api/memdash_views.py"
      ],
      "related": [
        "webui.memory.personal",
        "webui.memory.company",
        "webui.memory.project"
      ],
      "locales": {
        "en": {
          "title": "Memory lifecycle",
          "purpose": "Read available lifecycle, aging and degradation information.",
          "when": "When checking stored context, its source or the audience allowed to read it.",
          "steps": [
            "Open Memory explorer and choose the permitted bank.",
            "Open Memory lifecycle; use the available search, filters or detail controls."
          ],
          "permissions": "Only stores and documents permitted for your identity are available. Admin status does not open another person’s private memory.",
          "limits": "This is a read-only view. Empty or unavailable data is not proof that nothing happened. Available views depend on the bank’s stored schema; editing, confirming or forgetting records is not enabled by this guide.",
          "example": "Identify older records that may deserve review."
        },
        "nl": {
          "title": "Levenscyclus van geheugen",
          "purpose": "Lees beschikbare informatie over levenscyclus, veroudering en afname van geheugen.",
          "when": "Bij het controleren van opgeslagen context, de bron of de doelgroep die deze mag lezen.",
          "steps": [
            "Open Geheugenverkenner en kies de toegestane bank.",
            "Open Levenscyclus van geheugen; gebruik beschikbare zoek-, filter- of detailopties."
          ],
          "permissions": "Alleen opslag en documenten die voor jouw identiteit zijn toegestaan zijn beschikbaar. Beheerdersrechten openen geen privégeheugen van een ander.",
          "limits": "Dit is een alleen-lezenweergave. Lege of onbeschikbare gegevens bewijzen niet dat niets gebeurde. Beschikbare weergaven hangen af van de opgeslagen bankstructuur; deze gids schakelt bewerken, bevestigen of vergeten niet in.",
          "example": "Herken oudere records die beoordeling kunnen verdienen."
        }
      }
    },
    {
      "id": "webui.memory.graph",
      "area": "memory",
      "status": "conditional",
      "conditions": [
        "hq-memory-reader",
        "bank-data-availability"
      ],
      "anchors": [
        "?help_feature=webui.memory.graph"
      ],
      "source_refs": [
        "static/memory_dashboard.js",
        "api/memdash_scope.py",
        "api/memdash_views.py"
      ],
      "related": [
        "webui.memory.personal",
        "webui.memory.company",
        "webui.memory.project"
      ],
      "locales": {
        "en": {
          "title": "Knowledge relationship graph",
          "purpose": "Inspect stored relationships using graph search, zoom, pan and reset controls.",
          "when": "When checking stored context, its source or the audience allowed to read it.",
          "steps": [
            "Open Memory explorer and choose the permitted bank.",
            "Open Knowledge relationship graph; use the available search, filters or detail controls."
          ],
          "permissions": "Only stores and documents permitted for your identity are available. Admin status does not open another person’s private memory.",
          "limits": "This is a read-only view. Empty or unavailable data is not proof that nothing happened. Available views depend on the bank’s stored schema; editing, confirming or forgetting records is not enabled by this guide.",
          "example": "Follow a stored relationship between two subjects."
        },
        "nl": {
          "title": "Kennisrelatiegrafiek",
          "purpose": "Bekijk opgeslagen relaties met zoeken, zoomen, verschuiven en herstellen van de grafiek.",
          "when": "Bij het controleren van opgeslagen context, de bron of de doelgroep die deze mag lezen.",
          "steps": [
            "Open Geheugenverkenner en kies de toegestane bank.",
            "Open Kennisrelatiegrafiek; gebruik beschikbare zoek-, filter- of detailopties."
          ],
          "permissions": "Alleen opslag en documenten die voor jouw identiteit zijn toegestaan zijn beschikbaar. Beheerdersrechten openen geen privégeheugen van een ander.",
          "limits": "Dit is een alleen-lezenweergave. Lege of onbeschikbare gegevens bewijzen niet dat niets gebeurde. Beschikbare weergaven hangen af van de opgeslagen bankstructuur; deze gids schakelt bewerken, bevestigen of vergeten niet in.",
          "example": "Volg een opgeslagen relatie tussen twee onderwerpen."
        }
      }
    },
    {
      "id": "webui.memory.triples",
      "area": "memory",
      "status": "conditional",
      "conditions": [
        "hq-memory-reader",
        "bank-data-availability"
      ],
      "anchors": [
        "?help_feature=webui.memory.triples"
      ],
      "source_refs": [
        "static/memory_dashboard.js",
        "api/memdash_scope.py",
        "api/memdash_views.py"
      ],
      "related": [
        "webui.memory.personal",
        "webui.memory.company",
        "webui.memory.project"
      ],
      "locales": {
        "en": {
          "title": "Knowledge facts table",
          "purpose": "Filter stored subject, predicate and object relationships in a table.",
          "when": "When checking stored context, its source or the audience allowed to read it.",
          "steps": [
            "Open Memory explorer and choose the permitted bank.",
            "Open Knowledge facts table; use the available search, filters or detail controls."
          ],
          "permissions": "Only stores and documents permitted for your identity are available. Admin status does not open another person’s private memory.",
          "limits": "This is a read-only view. Empty or unavailable data is not proof that nothing happened. Available views depend on the bank’s stored schema; editing, confirming or forgetting records is not enabled by this guide.",
          "example": "Inspect the exact fields behind a graph relationship."
        },
        "nl": {
          "title": "Tabel met kennisfeiten",
          "purpose": "Filter opgeslagen relaties van onderwerp, predicaat en object in een tabel.",
          "when": "Bij het controleren van opgeslagen context, de bron of de doelgroep die deze mag lezen.",
          "steps": [
            "Open Geheugenverkenner en kies de toegestane bank.",
            "Open Tabel met kennisfeiten; gebruik beschikbare zoek-, filter- of detailopties."
          ],
          "permissions": "Alleen opslag en documenten die voor jouw identiteit zijn toegestaan zijn beschikbaar. Beheerdersrechten openen geen privégeheugen van een ander.",
          "limits": "Dit is een alleen-lezenweergave. Lege of onbeschikbare gegevens bewijzen niet dat niets gebeurde. Beschikbare weergaven hangen af van de opgeslagen bankstructuur; deze gids schakelt bewerken, bevestigen of vergeten niet in.",
          "example": "Bekijk de exacte velden achter een grafiekrelatie."
        }
      }
    },
    {
      "id": "webui.memory.recall",
      "area": "memory",
      "status": "conditional",
      "conditions": [
        "hq-memory-reader",
        "bank-data-availability"
      ],
      "anchors": [
        "?help_feature=webui.memory.recall"
      ],
      "source_refs": [
        "static/memory_dashboard.js",
        "api/memdash_scope.py",
        "api/memdash_views.py"
      ],
      "related": [
        "webui.memory.personal",
        "webui.memory.company",
        "webui.memory.project"
      ],
      "locales": {
        "en": {
          "title": "Recall debug",
          "purpose": "Inspect the available retrieval diagnostics for a query within the chosen bank.",
          "when": "When checking stored context, its source or the audience allowed to read it.",
          "steps": [
            "Open Memory explorer and choose the permitted bank.",
            "Open Recall debug; use the available search, filters or detail controls."
          ],
          "permissions": "Only stores and documents permitted for your identity are available. Admin status does not open another person’s private memory.",
          "limits": "This is a read-only view. Empty or unavailable data is not proof that nothing happened. Available views depend on the bank’s stored schema; editing, confirming or forgetting records is not enabled by this guide.",
          "example": "Investigate which records a query retrieves."
        },
        "nl": {
          "title": "Ophaaldiagnostiek",
          "purpose": "Bekijk beschikbare ophaaldiagnostiek voor een zoekvraag in de gekozen bank.",
          "when": "Bij het controleren van opgeslagen context, de bron of de doelgroep die deze mag lezen.",
          "steps": [
            "Open Geheugenverkenner en kies de toegestane bank.",
            "Open Ophaaldiagnostiek; gebruik beschikbare zoek-, filter- of detailopties."
          ],
          "permissions": "Alleen opslag en documenten die voor jouw identiteit zijn toegestaan zijn beschikbaar. Beheerdersrechten openen geen privégeheugen van een ander.",
          "limits": "Dit is een alleen-lezenweergave. Lege of onbeschikbare gegevens bewijzen niet dat niets gebeurde. Beschikbare weergaven hangen af van de opgeslagen bankstructuur; deze gids schakelt bewerken, bevestigen of vergeten niet in.",
          "example": "Onderzoek welke records een zoekvraag oplevert."
        }
      }
    },
    {
      "id": "webui.memory.timeline",
      "area": "memory",
      "status": "conditional",
      "conditions": [
        "hq-memory-reader",
        "bank-data-availability"
      ],
      "anchors": [
        "?help_feature=webui.memory.timeline"
      ],
      "source_refs": [
        "static/memory_dashboard.js",
        "api/memdash_scope.py",
        "api/memdash_views.py"
      ],
      "related": [
        "webui.memory.personal",
        "webui.memory.company",
        "webui.memory.project"
      ],
      "locales": {
        "en": {
          "title": "Memory event timeline",
          "purpose": "Read chronological memory events and available session details.",
          "when": "When checking stored context, its source or the audience allowed to read it.",
          "steps": [
            "Open Memory explorer and choose the permitted bank.",
            "Open Memory event timeline; use the available search, filters or detail controls."
          ],
          "permissions": "Only stores and documents permitted for your identity are available. Admin status does not open another person’s private memory.",
          "limits": "This is a read-only view. Empty or unavailable data is not proof that nothing happened. Available views depend on the bank’s stored schema; editing, confirming or forgetting records is not enabled by this guide.",
          "example": "Trace when a piece of context appeared."
        },
        "nl": {
          "title": "Tijdlijn van geheugengebeurtenissen",
          "purpose": "Lees chronologische geheugengebeurtenissen en beschikbare sessiedetails.",
          "when": "Bij het controleren van opgeslagen context, de bron of de doelgroep die deze mag lezen.",
          "steps": [
            "Open Geheugenverkenner en kies de toegestane bank.",
            "Open Tijdlijn van geheugengebeurtenissen; gebruik beschikbare zoek-, filter- of detailopties."
          ],
          "permissions": "Alleen opslag en documenten die voor jouw identiteit zijn toegestaan zijn beschikbaar. Beheerdersrechten openen geen privégeheugen van een ander.",
          "limits": "Dit is een alleen-lezenweergave. Lege of onbeschikbare gegevens bewijzen niet dat niets gebeurde. Beschikbare weergaven hangen af van de opgeslagen bankstructuur; deze gids schakelt bewerken, bevestigen of vergeten niet in.",
          "example": "Zoek na wanneer een stukje context verscheen."
        }
      }
    },
    {
      "id": "webui.memory.consolidations",
      "area": "memory",
      "status": "conditional",
      "conditions": [
        "hq-memory-reader",
        "bank-data-availability"
      ],
      "anchors": [
        "?help_feature=webui.memory.consolidations"
      ],
      "source_refs": [
        "static/memory_dashboard.js",
        "api/memdash_scope.py",
        "api/memdash_views.py"
      ],
      "related": [
        "webui.memory.personal",
        "webui.memory.company",
        "webui.memory.project"
      ],
      "locales": {
        "en": {
          "title": "Consolidation history",
          "purpose": "Inspect stored summaries of memory consolidation runs.",
          "when": "When checking stored context, its source or the audience allowed to read it.",
          "steps": [
            "Open Memory explorer and choose the permitted bank.",
            "Open Consolidation history; use the available search, filters or detail controls."
          ],
          "permissions": "Only stores and documents permitted for your identity are available. Admin status does not open another person’s private memory.",
          "limits": "This is a read-only view. Empty or unavailable data is not proof that nothing happened. Available views depend on the bank’s stored schema; editing, confirming or forgetting records is not enabled by this guide.",
          "example": "Read the recorded summary behind an older compressed memory."
        },
        "nl": {
          "title": "Samenvoeggeschiedenis",
          "purpose": "Bekijk opgeslagen samenvattingen van geheugensamenvoegingen.",
          "when": "Bij het controleren van opgeslagen context, de bron of de doelgroep die deze mag lezen.",
          "steps": [
            "Open Geheugenverkenner en kies de toegestane bank.",
            "Open Samenvoeggeschiedenis; gebruik beschikbare zoek-, filter- of detailopties."
          ],
          "permissions": "Alleen opslag en documenten die voor jouw identiteit zijn toegestaan zijn beschikbaar. Beheerdersrechten openen geen privégeheugen van een ander.",
          "limits": "Dit is een alleen-lezenweergave. Lege of onbeschikbare gegevens bewijzen niet dat niets gebeurde. Beschikbare weergaven hangen af van de opgeslagen bankstructuur; deze gids schakelt bewerken, bevestigen of vergeten niet in.",
          "example": "Lees de vastgelegde samenvatting achter ouder gecomprimeerd geheugen."
        }
      }
    },
    {
      "id": "webui.memory.structured_overview",
      "area": "memory",
      "status": "conditional",
      "conditions": [
        "hq-memory-reader",
        "bank-data-availability"
      ],
      "anchors": [
        "?help_feature=webui.memory.structured_overview"
      ],
      "source_refs": [
        "static/memory_dashboard.js",
        "api/memdash_scope.py",
        "api/memdash_views.py"
      ],
      "related": [
        "webui.memory.personal",
        "webui.memory.company",
        "webui.memory.project"
      ],
      "locales": {
        "en": {
          "title": "Structured memory overview",
          "purpose": "Inspect counts for structured memory tables available in this bank.",
          "when": "When checking stored context, its source or the audience allowed to read it.",
          "steps": [
            "Open Memory explorer and choose the permitted bank.",
            "Open Structured memory overview; use the available search, filters or detail controls."
          ],
          "permissions": "Only stores and documents permitted for your identity are available. Admin status does not open another person’s private memory.",
          "limits": "This is a read-only view. Empty or unavailable data is not proof that nothing happened. Available views depend on the bank’s stored schema; editing, confirming or forgetting records is not enabled by this guide.",
          "example": "Check whether the bank contains structured extraction results."
        },
        "nl": {
          "title": "Overzicht van gestructureerd geheugen",
          "purpose": "Bekijk aantallen voor gestructureerde geheugentabellen in deze bank.",
          "when": "Bij het controleren van opgeslagen context, de bron of de doelgroep die deze mag lezen.",
          "steps": [
            "Open Geheugenverkenner en kies de toegestane bank.",
            "Open Overzicht van gestructureerd geheugen; gebruik beschikbare zoek-, filter- of detailopties."
          ],
          "permissions": "Alleen opslag en documenten die voor jouw identiteit zijn toegestaan zijn beschikbaar. Beheerdersrechten openen geen privégeheugen van een ander.",
          "limits": "Dit is een alleen-lezenweergave. Lege of onbeschikbare gegevens bewijzen niet dat niets gebeurde. Beschikbare weergaven hangen af van de opgeslagen bankstructuur; deze gids schakelt bewerken, bevestigen of vergeten niet in.",
          "example": "Controleer of de bank gestructureerde extractieresultaten bevat."
        }
      }
    },
    {
      "id": "webui.memory.facts",
      "area": "memory",
      "status": "conditional",
      "conditions": [
        "hq-memory-reader",
        "bank-data-availability"
      ],
      "anchors": [
        "?help_feature=webui.memory.facts"
      ],
      "source_refs": [
        "static/memory_dashboard.js",
        "api/memdash_scope.py",
        "api/memdash_views.py"
      ],
      "related": [
        "webui.memory.personal",
        "webui.memory.company",
        "webui.memory.project"
      ],
      "locales": {
        "en": {
          "title": "Structured facts",
          "purpose": "Search available extracted facts in the selected bank.",
          "when": "When checking stored context, its source or the audience allowed to read it.",
          "steps": [
            "Open Memory explorer and choose the permitted bank.",
            "Open Structured facts; use the available search, filters or detail controls."
          ],
          "permissions": "Only stores and documents permitted for your identity are available. Admin status does not open another person’s private memory.",
          "limits": "This is a read-only view. Empty or unavailable data is not proof that nothing happened. Available views depend on the bank’s stored schema; editing, confirming or forgetting records is not enabled by this guide.",
          "example": "Read an extracted fact together with its context."
        },
        "nl": {
          "title": "Gestructureerde feiten",
          "purpose": "Zoek beschikbare geëxtraheerde feiten in de gekozen bank.",
          "when": "Bij het controleren van opgeslagen context, de bron of de doelgroep die deze mag lezen.",
          "steps": [
            "Open Geheugenverkenner en kies de toegestane bank.",
            "Open Gestructureerde feiten; gebruik beschikbare zoek-, filter- of detailopties."
          ],
          "permissions": "Alleen opslag en documenten die voor jouw identiteit zijn toegestaan zijn beschikbaar. Beheerdersrechten openen geen privégeheugen van een ander.",
          "limits": "Dit is een alleen-lezenweergave. Lege of onbeschikbare gegevens bewijzen niet dat niets gebeurde. Beschikbare weergaven hangen af van de opgeslagen bankstructuur; deze gids schakelt bewerken, bevestigen of vergeten niet in.",
          "example": "Lees een geëxtraheerd feit samen met de context."
        }
      }
    },
    {
      "id": "webui.memory.structured_timelines",
      "area": "memory",
      "status": "conditional",
      "conditions": [
        "hq-memory-reader",
        "bank-data-availability"
      ],
      "anchors": [
        "?help_feature=webui.memory.structured_timelines"
      ],
      "source_refs": [
        "static/memory_dashboard.js",
        "api/memdash_scope.py",
        "api/memdash_views.py"
      ],
      "related": [
        "webui.memory.personal",
        "webui.memory.company",
        "webui.memory.project"
      ],
      "locales": {
        "en": {
          "title": "Structured timelines",
          "purpose": "Search extracted chronological information where present.",
          "when": "When checking stored context, its source or the audience allowed to read it.",
          "steps": [
            "Open Memory explorer and choose the permitted bank.",
            "Open Structured timelines; use the available search, filters or detail controls."
          ],
          "permissions": "Only stores and documents permitted for your identity are available. Admin status does not open another person’s private memory.",
          "limits": "This is a read-only view. Empty or unavailable data is not proof that nothing happened. Available views depend on the bank’s stored schema; editing, confirming or forgetting records is not enabled by this guide.",
          "example": "Find an extracted event in its recorded timeline."
        },
        "nl": {
          "title": "Gestructureerde tijdlijnen",
          "purpose": "Zoek geëxtraheerde chronologische informatie waar aanwezig.",
          "when": "Bij het controleren van opgeslagen context, de bron of de doelgroep die deze mag lezen.",
          "steps": [
            "Open Geheugenverkenner en kies de toegestane bank.",
            "Open Gestructureerde tijdlijnen; gebruik beschikbare zoek-, filter- of detailopties."
          ],
          "permissions": "Alleen opslag en documenten die voor jouw identiteit zijn toegestaan zijn beschikbaar. Beheerdersrechten openen geen privégeheugen van een ander.",
          "limits": "Dit is een alleen-lezenweergave. Lege of onbeschikbare gegevens bewijzen niet dat niets gebeurde. Beschikbare weergaven hangen af van de opgeslagen bankstructuur; deze gids schakelt bewerken, bevestigen of vergeten niet in.",
          "example": "Vind een geëxtraheerde gebeurtenis in de vastgelegde tijdlijn."
        }
      }
    },
    {
      "id": "webui.memory.instructions",
      "area": "memory",
      "status": "conditional",
      "conditions": [
        "hq-memory-reader",
        "bank-data-availability"
      ],
      "anchors": [
        "?help_feature=webui.memory.instructions"
      ],
      "source_refs": [
        "static/memory_dashboard.js",
        "api/memdash_scope.py",
        "api/memdash_views.py"
      ],
      "related": [
        "webui.memory.personal",
        "webui.memory.company",
        "webui.memory.project"
      ],
      "locales": {
        "en": {
          "title": "Structured instructions",
          "purpose": "Inspect extracted instructions without treating them as new permissions.",
          "when": "When checking stored context, its source or the audience allowed to read it.",
          "steps": [
            "Open Memory explorer and choose the permitted bank.",
            "Open Structured instructions; use the available search, filters or detail controls."
          ],
          "permissions": "Only stores and documents permitted for your identity are available. Admin status does not open another person’s private memory.",
          "limits": "This is a read-only view. Empty or unavailable data is not proof that nothing happened. Available views depend on the bank’s stored schema; editing, confirming or forgetting records is not enabled by this guide.",
          "example": "Review a stored instruction before relying on it."
        },
        "nl": {
          "title": "Gestructureerde instructies",
          "purpose": "Bekijk geëxtraheerde instructies zonder ze als nieuwe rechten te behandelen.",
          "when": "Bij het controleren van opgeslagen context, de bron of de doelgroep die deze mag lezen.",
          "steps": [
            "Open Geheugenverkenner en kies de toegestane bank.",
            "Open Gestructureerde instructies; gebruik beschikbare zoek-, filter- of detailopties."
          ],
          "permissions": "Alleen opslag en documenten die voor jouw identiteit zijn toegestaan zijn beschikbaar. Beheerdersrechten openen geen privégeheugen van een ander.",
          "limits": "Dit is een alleen-lezenweergave. Lege of onbeschikbare gegevens bewijzen niet dat niets gebeurde. Beschikbare weergaven hangen af van de opgeslagen bankstructuur; deze gids schakelt bewerken, bevestigen of vergeten niet in.",
          "example": "Controleer een opgeslagen instructie voordat je erop vertrouwt."
        }
      }
    },
    {
      "id": "webui.memory.structured_graph",
      "area": "memory",
      "status": "conditional",
      "conditions": [
        "hq-memory-reader",
        "bank-data-availability"
      ],
      "anchors": [
        "?help_feature=webui.memory.structured_graph"
      ],
      "source_refs": [
        "static/memory_dashboard.js",
        "api/memdash_scope.py",
        "api/memdash_views.py"
      ],
      "related": [
        "webui.memory.personal",
        "webui.memory.company",
        "webui.memory.project"
      ],
      "locales": {
        "en": {
          "title": "Structured knowledge graph",
          "purpose": "Read extracted knowledge-graph records where the bank supplies them.",
          "when": "When checking stored context, its source or the audience allowed to read it.",
          "steps": [
            "Open Memory explorer and choose the permitted bank.",
            "Open Structured knowledge graph; use the available search, filters or detail controls."
          ],
          "permissions": "Only stores and documents permitted for your identity are available. Admin status does not open another person’s private memory.",
          "limits": "This is a read-only view. Empty or unavailable data is not proof that nothing happened. Available views depend on the bank’s stored schema; editing, confirming or forgetting records is not enabled by this guide.",
          "example": "Compare an extracted relationship with its source context."
        },
        "nl": {
          "title": "Gestructureerde kennisgrafiek",
          "purpose": "Lees geëxtraheerde kennisgrafiekrecords waar de bank deze levert.",
          "when": "Bij het controleren van opgeslagen context, de bron of de doelgroep die deze mag lezen.",
          "steps": [
            "Open Geheugenverkenner en kies de toegestane bank.",
            "Open Gestructureerde kennisgrafiek; gebruik beschikbare zoek-, filter- of detailopties."
          ],
          "permissions": "Alleen opslag en documenten die voor jouw identiteit zijn toegestaan zijn beschikbaar. Beheerdersrechten openen geen privégeheugen van een ander.",
          "limits": "Dit is een alleen-lezenweergave. Lege of onbeschikbare gegevens bewijzen niet dat niets gebeurde. Beschikbare weergaven hangen af van de opgeslagen bankstructuur; deze gids schakelt bewerken, bevestigen of vergeten niet in.",
          "example": "Vergelijk een geëxtraheerde relatie met de broncontext."
        }
      }
    },
    {
      "id": "webui.memory.preferences",
      "area": "memory",
      "status": "conditional",
      "conditions": [
        "hq-memory-reader",
        "bank-data-availability"
      ],
      "anchors": [
        "?help_feature=webui.memory.preferences"
      ],
      "source_refs": [
        "static/memory_dashboard.js",
        "api/memdash_scope.py",
        "api/memdash_views.py"
      ],
      "related": [
        "webui.memory.personal",
        "webui.memory.company",
        "webui.memory.project"
      ],
      "locales": {
        "en": {
          "title": "Structured preferences",
          "purpose": "Inspect extracted preference records for the permitted bank.",
          "when": "When checking stored context, its source or the audience allowed to read it.",
          "steps": [
            "Open Memory explorer and choose the permitted bank.",
            "Open Structured preferences; use the available search, filters or detail controls."
          ],
          "permissions": "Only stores and documents permitted for your identity are available. Admin status does not open another person’s private memory.",
          "limits": "This is a read-only view. Empty or unavailable data is not proof that nothing happened. Available views depend on the bank’s stored schema; editing, confirming or forgetting records is not enabled by this guide.",
          "example": "Check whether a preference was inferred correctly."
        },
        "nl": {
          "title": "Gestructureerde voorkeuren",
          "purpose": "Bekijk geëxtraheerde voorkeursrecords van de toegestane bank.",
          "when": "Bij het controleren van opgeslagen context, de bron of de doelgroep die deze mag lezen.",
          "steps": [
            "Open Geheugenverkenner en kies de toegestane bank.",
            "Open Gestructureerde voorkeuren; gebruik beschikbare zoek-, filter- of detailopties."
          ],
          "permissions": "Alleen opslag en documenten die voor jouw identiteit zijn toegestaan zijn beschikbaar. Beheerdersrechten openen geen privégeheugen van een ander.",
          "limits": "Dit is een alleen-lezenweergave. Lege of onbeschikbare gegevens bewijzen niet dat niets gebeurde. Beschikbare weergaven hangen af van de opgeslagen bankstructuur; deze gids schakelt bewerken, bevestigen of vergeten niet in.",
          "example": "Controleer of een voorkeur correct is afgeleid."
        }
      }
    },
    {
      "id": "webui.settings.search",
      "area": "settings",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.settings.search",
        "#settingsSearch"
      ],
      "source_refs": [
        "static/index.html:410"
      ],
      "related": [
        "webui.settings.theme",
        "webui.settings.skin",
        "webui.settings.font_size"
      ],
      "locales": {
        "en": {
          "title": "Search settings",
          "purpose": "Find a setting by its label without manually opening each settings section.",
          "when": "When the current configuration or presentation does not fit the intended workflow.",
          "steps": [
            "Type a term in the settings search field.",
            "Choose a matching setting and review its current value before changing it."
          ],
          "permissions": "Appearance preferences can be personal. Model, provider, security and server changes require configuration rights.",
          "limits": "Some options appear only when enabled by an administrator or supported by your browser. Save feedback determines whether the change was applied.",
          "example": "Find the send-key preference by searching its name."
        },
        "nl": {
          "title": "Instellingen zoeken",
          "purpose": "Vind een instelling op label zonder elk onderdeel handmatig te openen.",
          "when": "Wanneer de huidige instelling of weergave niet past bij de bedoelde werkwijze.",
          "steps": [
            "Typ een woord in het zoekveld van Instellingen.",
            "Kies een passende instelling en controleer de huidige waarde voordat je wijzigt."
          ],
          "permissions": "Weergavevoorkeuren kunnen persoonlijk zijn. Model-, provider-, beveiligings- en serverwijzigingen vereisen configuratierechten.",
          "limits": "Sommige opties verschijnen alleen als een beheerder ze inschakelt of je browser ze ondersteunt. De opslagmelding bepaalt of de wijziging is toegepast.",
          "example": "Vind de verstuursneltoets door op naam te zoeken."
        }
      }
    },
    {
      "id": "webui.files.hidden",
      "area": "files",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.files.hidden",
        "#workspaceShowHiddenFiles"
      ],
      "source_refs": [
        "static/ui.js:20944"
      ],
      "related": [
        "webui.files.workspace",
        "webui.files.manage",
        "webui.files.access"
      ],
      "locales": {
        "en": {
          "title": "Show hidden workspace files",
          "purpose": "Include dotfiles in the permitted workspace file listing.",
          "when": "When the task needs documents or directories in a specific workspace.",
          "steps": [
            "Open Workspace options and toggle Show hidden files.",
            "Inspect file names before opening or editing them."
          ],
          "permissions": "Workspace access and file permissions apply. Selecting a workspace does not grant access.",
          "limits": "Changes affect the selected workspace. Check the path and retain a copy before replacing important content.",
          "example": "Inspect a permitted project configuration file."
        },
        "nl": {
          "title": "Verborgen werkruimtebestanden tonen",
          "purpose": "Neem puntbestanden op in de toegestane werkruimtebestandenlijst.",
          "when": "Wanneer de taak documenten of mappen in een bepaalde werkruimte nodig heeft.",
          "steps": [
            "Open Werkruimteopties en schakel Verborgen bestanden tonen om.",
            "Controleer bestandsnamen voordat je opent of bewerkt."
          ],
          "permissions": "Toegang tot de werkruimte en bestandsrechten gelden. Een werkruimte kiezen geeft geen extra toegang.",
          "limits": "Wijzigingen gelden voor de gekozen werkruimte. Controleer het pad en bewaar een kopie voordat je belangrijke inhoud vervangt.",
          "example": "Bekijk een toegestaan projectconfiguratiebestand."
        }
      }
    },
    {
      "id": "webui.governance.approval_prompt",
      "area": "governance",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.governance.approval_prompt",
        "#govUserApprovalPrompt"
      ],
      "source_refs": [
        "static/governance.js:471"
      ],
      "related": [
        "webui.governance.once",
        "webui.governance.session",
        "webui.governance.always"
      ],
      "locales": {
        "en": {
          "title": "Custom approval reviewer instructions",
          "purpose": "Set the offered reviewer prompt associated with a user’s approval mode.",
          "when": "When access or approval scope needs to be inspected before an action proceeds.",
          "steps": [
            "Choose the supported approval mode in the user form.",
            "Write precise review instructions within the displayed limit and save the user policy."
          ],
          "permissions": "Management actions require the specific governance permission. A preview does not grant access.",
          "limits": "Approval is scoped to the requested action. Do not approve commands you do not understand.",
          "example": "Require additional scrutiny for a defined class of operation."
        },
        "nl": {
          "title": "Eigen instructies voor goedkeuringsbeoordeling",
          "purpose": "Stel de aangeboden beoordelingsprompt bij de goedkeuringsmodus van een gebruiker in.",
          "when": "Wanneer toegang of goedkeuringsscope moet worden gecontroleerd voordat een actie doorgaat.",
          "steps": [
            "Kies de ondersteunde goedkeuringsmodus in het gebruikersformulier.",
            "Schrijf precieze beoordelingsinstructies binnen de getoonde limiet en sla het beleid op."
          ],
          "permissions": "Beheeracties vereisen de specifieke beleidsrechten. Een voorbeeld geeft geen toegang.",
          "limits": "Goedkeuring geldt binnen de scope van de gevraagde actie. Keur geen opdrachten goed die je niet begrijpt.",
          "example": "Vraag extra controle voor een afgebakend type handeling."
        }
      }
    },
    {
      "id": "webui.governance.effective_grants",
      "area": "governance",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.governance.effective_grants"
      ],
      "source_refs": [
        "static/governance.js:815"
      ],
      "related": [
        "webui.governance.once",
        "webui.governance.session",
        "webui.governance.always"
      ],
      "locales": {
        "en": {
          "title": "Effective grants and explicit denials",
          "purpose": "Inspect resolved skill, CLI and MCP permissions and toggle supported explicit denials.",
          "when": "When access or approval scope needs to be inspected before an action proceeds.",
          "steps": [
            "Open a user’s effective access preview.",
            "Toggle an intended item, review the deny list and save.",
            "Refresh the saved-policy preview; a wildcard does not remove explicit denials."
          ],
          "permissions": "Management actions require the specific governance permission. A preview does not grant access.",
          "limits": "Approval is scoped to the requested action. Do not approve commands you do not understand.",
          "example": "Deny one tool even when a broader group grants access."
        },
        "nl": {
          "title": "Effectieve rechten en expliciete weigeringen",
          "purpose": "Bekijk opgeloste skill-, CLI- en MCP-rechten en wijzig ondersteunde expliciete weigeringen.",
          "when": "Wanneer toegang of goedkeuringsscope moet worden gecontroleerd voordat een actie doorgaat.",
          "steps": [
            "Open de effectieve toegangsvoorvertoning van een gebruiker.",
            "Schakel een bedoeld item om, controleer de weigerlijst en sla op.",
            "Ververs de opgeslagen beleidsvoorvertoning; een jokerteken heft expliciete weigeringen niet op."
          ],
          "permissions": "Beheeracties vereisen de specifieke beleidsrechten. Een voorbeeld geeft geen toegang.",
          "limits": "Goedkeuring geldt binnen de scope van de gevraagde actie. Keur geen opdrachten goed die je niet begrijpt.",
          "example": "Weiger één tool terwijl een bredere groep toegang geeft."
        }
      }
    },
    {
      "id": "webui.governance.group_template",
      "area": "governance",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.governance.group_template"
      ],
      "source_refs": [
        "static/governance.js:1021"
      ],
      "related": [
        "webui.governance.once",
        "webui.governance.session",
        "webui.governance.always"
      ],
      "locales": {
        "en": {
          "title": "Group role templates",
          "purpose": "Populate a group form from an offered role template.",
          "when": "When access or approval scope needs to be inspected before an action proceeds.",
          "steps": [
            "Choose a template in the group editor.",
            "Review every resulting role and scope before saving the group."
          ],
          "permissions": "Management actions require the specific governance permission. A preview does not grant access.",
          "limits": "Approval is scoped to the requested action. Do not approve commands you do not understand.",
          "example": "Start from a standard team template and review its permissions."
        },
        "nl": {
          "title": "Groepsrolsjablonen",
          "purpose": "Vul een groepsformulier vanuit een aangeboden rolsjabloon.",
          "when": "Wanneer toegang of goedkeuringsscope moet worden gecontroleerd voordat een actie doorgaat.",
          "steps": [
            "Kies een sjabloon in de groepseditor.",
            "Controleer elke resulterende rol en scope voordat je de groep opslaat."
          ],
          "permissions": "Beheeracties vereisen de specifieke beleidsrechten. Een voorbeeld geeft geen toegang.",
          "limits": "Goedkeuring geldt binnen de scope van de gevraagde actie. Keur geen opdrachten goed die je niet begrijpt.",
          "example": "Begin met een standaard teamsjabloon en controleer de rechten."
        }
      }
    },
    {
      "id": "webui.governance.integration_approval",
      "area": "governance",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.governance.integration_approval"
      ],
      "source_refs": [
        "static/governance.js:2029"
      ],
      "related": [
        "webui.governance.once",
        "webui.governance.session",
        "webui.governance.always"
      ],
      "locales": {
        "en": {
          "title": "Approve, reject or disable providers",
          "purpose": "Manage provider approval and availability within the organisation’s integration policy.",
          "when": "When access or approval scope needs to be inspected before an action proceeds.",
          "steps": [
            "Inspect the pending provider request and existing connections.",
            "Approve or reject a request, or disable an enabled provider when allowed.",
            "Disconnect dependent connections first if the interface requires it."
          ],
          "permissions": "Management actions require the specific governance permission. A preview does not grant access.",
          "limits": "Approval is scoped to the requested action. Do not approve commands you do not understand.",
          "example": "Review a requested integration before making it available."
        },
        "nl": {
          "title": "Providers goedkeuren, afwijzen of uitschakelen",
          "purpose": "Beheer providergoedkeuring en beschikbaarheid binnen het integratiebeleid van de organisatie.",
          "when": "Wanneer toegang of goedkeuringsscope moet worden gecontroleerd voordat een actie doorgaat.",
          "steps": [
            "Bekijk het wachtende providerverzoek en bestaande koppelingen.",
            "Keur een verzoek goed of wijs het af, of schakel een actieve provider uit wanneer toegestaan.",
            "Ontkoppel afhankelijke koppelingen eerst als de interface dit vereist."
          ],
          "permissions": "Beheeracties vereisen de specifieke beleidsrechten. Een voorbeeld geeft geen toegang.",
          "limits": "Goedkeuring geldt binnen de scope van de gevraagde actie. Keur geen opdrachten goed die je niet begrijpt.",
          "example": "Beoordeel een gevraagde integratie voordat je deze beschikbaar maakt."
        }
      }
    },
    {
      "id": "webui.operations.extension_gallery",
      "area": "operations",
      "status": "conditional",
      "conditions": [
        "extension-management-permissions",
        "gallery-configuration"
      ],
      "anchors": [
        "?help_feature=webui.operations.extension_gallery"
      ],
      "source_refs": [
        "static/index.html:1722"
      ],
      "related": [
        "webui.operations.refresh",
        "webui.operations.health",
        "webui.operations.terminal"
      ],
      "locales": {
        "en": {
          "title": "Extension gallery",
          "purpose": "Browse extensions offered by the configured gallery and their requirements.",
          "when": "When investigating service behaviour or preparing an authorised maintenance action.",
          "steps": [
            "Open Settings, Extensions, Gallery.",
            "Read an extension’s description, publisher and requested capabilities before using an offered install action."
          ],
          "permissions": "Operational views and maintenance actions require the relevant management rights.",
          "limits": "Status is a snapshot, not a delivery guarantee. Diagnostic copies may contain operational details; review before sharing.",
          "example": "Review a useful extension before asking to install it."
        },
        "nl": {
          "title": "Extensiegalerij",
          "purpose": "Bekijk extensies uit de ingestelde galerij en hun vereisten.",
          "when": "Bij onderzoek naar servicegedrag of voorbereiding van een toegestane onderhoudsactie.",
          "steps": [
            "Open Instellingen, Extensies, Galerij.",
            "Lees beschrijving, uitgever en gevraagde mogelijkheden voordat je een aangeboden installatieactie gebruikt."
          ],
          "permissions": "Operationele schermen en onderhoudsacties vereisen de bijbehorende beheerrechten.",
          "limits": "Status is een momentopname en geen bezorggarantie. Diagnostische kopieën kunnen operationele gegevens bevatten; controleer ze voor delen.",
          "example": "Bekijk een nuttige extensie voordat je installatie aanvraagt."
        }
      }
    },
    {
      "id": "webui.operations.extension_installed",
      "area": "operations",
      "status": "conditional",
      "conditions": [
        "extension-management-permissions",
        "gallery-configuration"
      ],
      "anchors": [
        "?help_feature=webui.operations.extension_installed"
      ],
      "source_refs": [
        "static/panels.js"
      ],
      "related": [
        "webui.operations.refresh",
        "webui.operations.health",
        "webui.operations.terminal"
      ],
      "locales": {
        "en": {
          "title": "Manage installed extensions",
          "purpose": "Inspect installed extension versions and the management actions allowed to your role.",
          "when": "When investigating service behaviour or preparing an authorised maintenance action.",
          "steps": [
            "Open the Installed tab under Extensions.",
            "Inspect state and use only the offered enable, update or remove controls after reviewing their effect."
          ],
          "permissions": "Operational views and maintenance actions require the relevant management rights.",
          "limits": "Status is a snapshot, not a delivery guarantee. Diagnostic copies may contain operational details; review before sharing.",
          "example": "Check whether an installed extension is active."
        },
        "nl": {
          "title": "Geïnstalleerde extensies beheren",
          "purpose": "Bekijk geïnstalleerde extensieversies en beheeracties die je rol toestaat.",
          "when": "Bij onderzoek naar servicegedrag of voorbereiding van een toegestane onderhoudsactie.",
          "steps": [
            "Open het tabblad Geïnstalleerd bij Extensies.",
            "Bekijk de toestand en gebruik aangeboden inschakel-, update- of verwijderopties pas na controle van het effect."
          ],
          "permissions": "Operationele schermen en onderhoudsacties vereisen de bijbehorende beheerrechten.",
          "limits": "Status is een momentopname en geen bezorggarantie. Diagnostische kopieën kunnen operationele gegevens bevatten; controleer ze voor delen.",
          "example": "Controleer of een geïnstalleerde extensie actief is."
        }
      }
    },
    {
      "id": "webui.chat.slash",
      "area": "chat",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.chat.slash"
      ],
      "source_refs": [
        "static/commands.js"
      ],
      "related": [
        "webui.chat.send",
        "webui.chat.normal",
        "webui.chat.super"
      ],
      "locales": {
        "en": {
          "title": "Slash commands and suggestions",
          "purpose": "Use supported composer commands to invoke local actions or documented agent workflows.",
          "when": "While preparing a request or reviewing a response in the active conversation.",
          "steps": [
            "Type / to inspect suggestions, or /help for the command list.",
            "Choose a known command and review its arguments before sending.",
            "Composer shortcut: /help. Review any required arguments in the command suggestions."
          ],
          "permissions": "Work in a conversation you can access. Tools and models still follow your permissions.",
          "limits": "Model output may be wrong. Review results before using them.",
          "example": "Find the command for changing a model without searching menus."
        },
        "nl": {
          "title": "Slashopdrachten en suggesties",
          "purpose": "Gebruik ondersteunde opdrachten in het berichtveld voor lokale acties of beschreven agentprocedures.",
          "when": "Bij het voorbereiden van een verzoek of beoordelen van een antwoord in het actieve gesprek.",
          "steps": [
            "Typ / voor suggesties of /help voor de opdrachtenlijst.",
            "Kies een bekende opdracht en controleer de argumenten voor versturen.",
            "Snelopdracht in het berichtveld: /help. Controleer eventuele argumenten in de opdrachtsuggesties."
          ],
          "permissions": "Werk in een gesprek waartoe je toegang hebt. Tools en modellen blijven gebonden aan je rechten.",
          "limits": "Modeluitvoer kan onjuist zijn. Controleer resultaten voor gebruik.",
          "example": "Vind de opdracht voor modelwissel zonder menu’s te doorzoeken."
        }
      }
    },
    {
      "id": "webui.chat.goal",
      "area": "chat",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.chat.goal"
      ],
      "source_refs": [
        "static/commands.js"
      ],
      "related": [
        "webui.chat.send",
        "webui.chat.normal",
        "webui.chat.super"
      ],
      "locales": {
        "en": {
          "title": "Conversation goals",
          "purpose": "Start and inspect a supported goal workflow for the current conversation.",
          "when": "While preparing a request or reviewing a response in the active conversation.",
          "steps": [
            "Use /goal with a clear objective.",
            "Use /goal status to inspect progress, or the offered pause, resume and clear arguments to manage it.",
            "Composer shortcut: /goal. Review any required arguments in the command suggestions."
          ],
          "permissions": "Work in a conversation you can access. Tools and models still follow your permissions.",
          "limits": "Model output may be wrong. Review results before using them.",
          "example": "Track a bounded task toward a stated outcome."
        },
        "nl": {
          "title": "Gespreksdoelen",
          "purpose": "Start en bekijk een ondersteunde doelprocedure voor het huidige gesprek.",
          "when": "Bij het voorbereiden van een verzoek of beoordelen van een antwoord in het actieve gesprek.",
          "steps": [
            "Gebruik /goal met een duidelijk doel.",
            "Gebruik /goal status voor voortgang of de aangeboden argumenten pause, resume en clear voor beheer.",
            "Snelopdracht in het berichtveld: /goal. Controleer eventuele argumenten in de opdrachtsuggesties."
          ],
          "permissions": "Werk in een gesprek waartoe je toegang hebt. Tools en modellen blijven gebonden aan je rechten.",
          "limits": "Modeluitvoer kan onjuist zijn. Controleer resultaten voor gebruik.",
          "example": "Volg een afgebakende taak naar een beschreven resultaat."
        }
      }
    },
    {
      "id": "webui.chat.queue",
      "area": "chat",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.chat.queue"
      ],
      "source_refs": [
        "static/commands.js"
      ],
      "related": [
        "webui.chat.send",
        "webui.chat.normal",
        "webui.chat.super"
      ],
      "locales": {
        "en": {
          "title": "Explicitly queue a follow-up",
          "purpose": "Choose queued handling for one message while work is running.",
          "when": "While preparing a request or reviewing a response in the active conversation.",
          "steps": [
            "Enter /queue followed by the message.",
            "Inspect the queued messages before waiting for the next turn.",
            "Composer shortcut: /queue. Review any required arguments in the command suggestions."
          ],
          "permissions": "Work in a conversation you can access. Tools and models still follow your permissions.",
          "limits": "Model output may be wrong. Review results before using them.",
          "example": "Add a follow-up without interrupting the current answer."
        },
        "nl": {
          "title": "Een vervolgvraag expliciet klaarzetten",
          "purpose": "Kies wachtrijverwerking voor één bericht terwijl werk loopt.",
          "when": "Bij het voorbereiden van een verzoek of beoordelen van een antwoord in het actieve gesprek.",
          "steps": [
            "Typ /queue gevolgd door het bericht.",
            "Controleer de wachtende berichten voordat je op de volgende beurt wacht.",
            "Snelopdracht in het berichtveld: /queue. Controleer eventuele argumenten in de opdrachtsuggesties."
          ],
          "permissions": "Werk in een gesprek waartoe je toegang hebt. Tools en modellen blijven gebonden aan je rechten.",
          "limits": "Modeluitvoer kan onjuist zijn. Controleer resultaten voor gebruik.",
          "example": "Voeg een vervolgvraag toe zonder het huidige antwoord te onderbreken."
        }
      }
    },
    {
      "id": "webui.chat.interrupt",
      "area": "chat",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.chat.interrupt"
      ],
      "source_refs": [
        "static/commands.js"
      ],
      "related": [
        "webui.chat.send",
        "webui.chat.normal",
        "webui.chat.super"
      ],
      "locales": {
        "en": {
          "title": "Interrupt with a new message",
          "purpose": "Request interruption of active work and provide the next message.",
          "when": "While preparing a request or reviewing a response in the active conversation.",
          "steps": [
            "Enter /interrupt followed by the revised instruction.",
            "Inspect the interruption result; completed external actions are not undone.",
            "Composer shortcut: /interrupt. Review any required arguments in the command suggestions."
          ],
          "permissions": "Work in a conversation you can access. Tools and models still follow your permissions.",
          "limits": "Model output may be wrong. Review results before using them.",
          "example": "Correct the requested direction while work is still running."
        },
        "nl": {
          "title": "Onderbreken met een nieuw bericht",
          "purpose": "Vraag om actief werk te onderbreken en geef het volgende bericht.",
          "when": "Bij het voorbereiden van een verzoek of beoordelen van een antwoord in het actieve gesprek.",
          "steps": [
            "Typ /interrupt gevolgd door de aangepaste instructie.",
            "Controleer het onderbreekresultaat; afgeronde externe acties worden niet teruggedraaid.",
            "Snelopdracht in het berichtveld: /interrupt. Controleer eventuele argumenten in de opdrachtsuggesties."
          ],
          "permissions": "Werk in een gesprek waartoe je toegang hebt. Tools en modellen blijven gebonden aan je rechten.",
          "limits": "Modeluitvoer kan onjuist zijn. Controleer resultaten voor gebruik.",
          "example": "Corrigeer de richting terwijl werk nog loopt."
        }
      }
    },
    {
      "id": "webui.chat.steer",
      "area": "chat",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.chat.steer"
      ],
      "source_refs": [
        "static/commands.js"
      ],
      "related": [
        "webui.chat.send",
        "webui.chat.normal",
        "webui.chat.super"
      ],
      "locales": {
        "en": {
          "title": "Steer active work",
          "purpose": "Send a supported steering message to running work.",
          "when": "While preparing a request or reviewing a response in the active conversation.",
          "steps": [
            "Enter /steer and the concise correction.",
            "Read the feedback and verify how the active run handles it.",
            "Composer shortcut: /steer. Review any required arguments in the command suggestions."
          ],
          "permissions": "Work in a conversation you can access. Tools and models still follow your permissions.",
          "limits": "Model output may be wrong. Review results before using them.",
          "example": "Add a missing constraint during an active task."
        },
        "nl": {
          "title": "Actief werk bijsturen",
          "purpose": "Stuur een ondersteund bijsturingsbericht naar lopend werk.",
          "when": "Bij het voorbereiden van een verzoek of beoordelen van een antwoord in het actieve gesprek.",
          "steps": [
            "Typ /steer en de korte correctie.",
            "Lees de terugmelding en controleer hoe de actieve uitvoering ermee omgaat.",
            "Snelopdracht in het berichtveld: /steer. Controleer eventuele argumenten in de opdrachtsuggesties."
          ],
          "permissions": "Werk in een gesprek waartoe je toegang hebt. Tools en modellen blijven gebonden aan je rechten.",
          "limits": "Modeluitvoer kan onjuist zijn. Controleer resultaten voor gebruik.",
          "example": "Voeg tijdens een actieve taak een ontbrekende randvoorwaarde toe."
        }
      }
    },
    {
      "id": "webui.chat.aside",
      "area": "chat",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.chat.aside"
      ],
      "source_refs": [
        "static/commands.js"
      ],
      "related": [
        "webui.chat.send",
        "webui.chat.normal",
        "webui.chat.super"
      ],
      "locales": {
        "en": {
          "title": "Ask a side question",
          "purpose": "Use the supported side-question stream associated with the current conversation.",
          "when": "While preparing a request or reviewing a response in the active conversation.",
          "steps": [
            "Enter /btw followed by the question.",
            "Read the separate response without assuming it replaced the main task.",
            "Composer shortcut: /btw. Review any required arguments in the command suggestions."
          ],
          "permissions": "Work in a conversation you can access. Tools and models still follow your permissions.",
          "limits": "Model output may be wrong. Review results before using them.",
          "example": "Ask for a term’s meaning during ongoing work."
        },
        "nl": {
          "title": "Een tussenvraag stellen",
          "purpose": "Gebruik de ondersteunde tussenvraagstroom bij het huidige gesprek.",
          "when": "Bij het voorbereiden van een verzoek of beoordelen van een antwoord in het actieve gesprek.",
          "steps": [
            "Typ /btw gevolgd door de vraag.",
            "Lees het afzonderlijke antwoord zonder aan te nemen dat dit de hoofdtaak vervangt.",
            "Snelopdracht in het berichtveld: /btw. Controleer eventuele argumenten in de opdrachtsuggesties."
          ],
          "permissions": "Werk in een gesprek waartoe je toegang hebt. Tools en modellen blijven gebonden aan je rechten.",
          "limits": "Modeluitvoer kan onjuist zijn. Controleer resultaten voor gebruik.",
          "example": "Vraag tijdens lopend werk naar de betekenis van een term."
        }
      }
    },
    {
      "id": "webui.chat.background",
      "area": "chat",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.chat.background"
      ],
      "source_refs": [
        "static/commands.js"
      ],
      "related": [
        "webui.chat.send",
        "webui.chat.normal",
        "webui.chat.super"
      ],
      "locales": {
        "en": {
          "title": "Start background work",
          "purpose": "Request a background task and monitor its badge or result status.",
          "when": "While preparing a request or reviewing a response in the active conversation.",
          "steps": [
            "Enter /background followed by a bounded prompt.",
            "Inspect the background indicator and completion result.",
            "Composer shortcut: /background. Review any required arguments in the command suggestions."
          ],
          "permissions": "Work in a conversation you can access. Tools and models still follow your permissions.",
          "limits": "Model output may be wrong. Review results before using them.",
          "example": "Run a separate supported analysis while continuing the main discussion."
        },
        "nl": {
          "title": "Achtergrondwerk starten",
          "purpose": "Vraag een achtergrondtaak aan en volg de badge of resultaatstatus.",
          "when": "Bij het voorbereiden van een verzoek of beoordelen van een antwoord in het actieve gesprek.",
          "steps": [
            "Typ /background gevolgd door een afgebakende prompt.",
            "Bekijk de achtergrondindicator en het voltooiingsresultaat.",
            "Snelopdracht in het berichtveld: /background. Controleer eventuele argumenten in de opdrachtsuggesties."
          ],
          "permissions": "Werk in een gesprek waartoe je toegang hebt. Tools en modellen blijven gebonden aan je rechten.",
          "limits": "Modeluitvoer kan onjuist zijn. Controleer resultaten voor gebruik.",
          "example": "Voer een afzonderlijke ondersteunde analyse uit terwijl het hoofdgesprek doorgaat."
        }
      }
    },
    {
      "id": "webui.chat.status",
      "area": "chat",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.chat.status"
      ],
      "source_refs": [
        "static/commands.js"
      ],
      "related": [
        "webui.chat.send",
        "webui.chat.normal",
        "webui.chat.super"
      ],
      "locales": {
        "en": {
          "title": "Conversation status and usage",
          "purpose": "Inspect available session, model, runtime and usage information.",
          "when": "While preparing a request or reviewing a response in the active conversation.",
          "steps": [
            "Enter /status or /usage.",
            "Read timestamps and units; missing cost metadata is not evidence of a free request.",
            "Composer shortcut: /usage. Review any required arguments in the command suggestions.",
            "Composer shortcut: /status. Review any required arguments in the command suggestions."
          ],
          "permissions": "Work in a conversation you can access. Tools and models still follow your permissions.",
          "limits": "Model output may be wrong. Review results before using them.",
          "example": "Check the active model and recorded usage before investigating a delay."
        },
        "nl": {
          "title": "Gespreksstatus en gebruik",
          "purpose": "Bekijk beschikbare informatie over gesprek, model, uitvoering en gebruik.",
          "when": "Bij het voorbereiden van een verzoek of beoordelen van een antwoord in het actieve gesprek.",
          "steps": [
            "Typ /status of /usage.",
            "Lees tijdstippen en eenheden; ontbrekende kosteninformatie bewijst niet dat een verzoek gratis was.",
            "Snelopdracht in het berichtveld: /usage. Controleer eventuele argumenten in de opdrachtsuggesties.",
            "Snelopdracht in het berichtveld: /status. Controleer eventuele argumenten in de opdrachtsuggesties."
          ],
          "permissions": "Werk in een gesprek waartoe je toegang hebt. Tools en modellen blijven gebonden aan je rechten.",
          "limits": "Modeluitvoer kan onjuist zijn. Controleer resultaten voor gebruik.",
          "example": "Controleer actief model en vastgelegd gebruik voordat je vertraging onderzoekt."
        }
      }
    },
    {
      "id": "webui.chat.personality",
      "area": "chat",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.chat.personality"
      ],
      "source_refs": [
        "static/commands.js"
      ],
      "related": [
        "webui.chat.send",
        "webui.chat.normal",
        "webui.chat.super"
      ],
      "locales": {
        "en": {
          "title": "Assistant personality preset",
          "purpose": "Apply an available personality preset through the supported command.",
          "when": "While preparing a request or reviewing a response in the active conversation.",
          "steps": [
            "Type /personality and choose an available suggestion.",
            "Review the resulting style change without treating it as a permission change.",
            "Composer shortcut: /personality. Review any required arguments in the command suggestions."
          ],
          "permissions": "Work in a conversation you can access. Tools and models still follow your permissions.",
          "limits": "Model output may be wrong. Review results before using them.",
          "example": "Choose a supported communication style for the current work."
        },
        "nl": {
          "title": "Persoonlijkheidskeuze voor de assistent",
          "purpose": "Pas een beschikbare persoonlijkheidskeuze toe via de ondersteunde opdracht.",
          "when": "Bij het voorbereiden van een verzoek of beoordelen van een antwoord in het actieve gesprek.",
          "steps": [
            "Typ /personality en kies een beschikbare suggestie.",
            "Controleer de stijlwijziging zonder deze als rechtenwijziging te behandelen.",
            "Snelopdracht in het berichtveld: /personality. Controleer eventuele argumenten in de opdrachtsuggesties."
          ],
          "permissions": "Werk in een gesprek waartoe je toegang hebt. Tools en modellen blijven gebonden aan je rechten.",
          "limits": "Modeluitvoer kan onjuist zijn. Controleer resultaten voor gebruik.",
          "example": "Kies een ondersteunde communicatiestijl voor het huidige werk."
        }
      }
    },
    {
      "id": "webui.skills.use",
      "area": "skills",
      "status": "available",
      "conditions": [],
      "anchors": [
        "?help_feature=webui.skills.use"
      ],
      "source_refs": [
        "static/commands.js"
      ],
      "related": [
        "webui.skills.browse",
        "webui.skills.edit",
        "webui.skills.delete"
      ],
      "locales": {
        "en": {
          "title": "Use a skill in the current conversation",
          "purpose": "Request an available skill through the composer’s skill command.",
          "when": "When reusable instructions need to be found or maintained for a repeatable task.",
          "steps": [
            "Use /skills to find instructions or /use followed by an available skill name.",
            "Check the selection and response before continuing.",
            "Composer shortcut: /use. Review any required arguments in the command suggestions."
          ],
          "permissions": "Viewing and editing skills require the corresponding skill permissions.",
          "limits": "A skill supplies instructions, not additional permissions or credentials.",
          "example": "Apply the available reporting checklist to the conversation."
        },
        "nl": {
          "title": "Een skill in het huidige gesprek gebruiken",
          "purpose": "Vraag een beschikbare skill aan via de skillopdracht in het berichtveld.",
          "when": "Wanneer herbruikbare instructies voor een terugkerende taak gezocht of onderhouden moeten worden.",
          "steps": [
            "Gebruik /skills om instructies te vinden of /use gevolgd door een beschikbare skillnaam.",
            "Controleer selectie en antwoord voordat je verdergaat.",
            "Snelopdracht in het berichtveld: /use. Controleer eventuele argumenten in de opdrachtsuggesties."
          ],
          "permissions": "Bekijken en bewerken van skills vereist de bijbehorende rechten.",
          "limits": "Een skill levert instructies, geen extra rechten of inloggegevens.",
          "example": "Pas de beschikbare rapportagecontrolelijst toe op het gesprek."
        }
      }
    },
    {
      "id": "webui.modules.apps",
      "area": "apps",
      "status": "conditional",
      "conditions": [
        "Configured app directory and existing access"
      ],
      "anchors": [
        "?help_feature=webui.modules.apps",
        "#mainApps"
      ],
      "source_refs": [
        "api/app_catalog.py",
        "api/apps_launcher.py",
        "static/apps.js"
      ],
      "related": [
        "webui.apps.overview"
      ],
      "locales": {
        "nl": {
          "title": "Apps als eigen onderdeel",
          "purpose": "Open de beschikbare toepassingen van je installatie vanuit Apps in de navigatie.",
          "when": "Wanneer je naar een creatieve editor, workflowomgeving of beheerapp wilt.",
          "steps": [
            "Kies Apps in de navigatie.",
            "Bekijk de categorie, beschrijving en status van een app.",
            "Kies Uitleg voor de interactieve gids of Openen om de toepassing in een nieuw tabblad te openen."
          ],
          "permissions": "Je moet aangemeld zijn. Leden zien toegestane apps voor actieve modules; platformbeheerders zien ook ingestelde beheerapps. Iedere app controleert zelf de toegang.",
          "limits": "Een ingesteld adres is geen gezondheidscontrole of bewijs van een licentie. Niet ingesteld heeft geen werkende Openen-knop. Een app openen activeert geen module en wijzigt geen rechten.",
          "example": "Open een creatieve editor vanuit Apps en houd je chat in het oorspronkelijke tabblad."
        },
        "en": {
          "title": "Apps as a dedicated section",
          "purpose": "Open the available applications for your installation from Apps in navigation.",
          "when": "When you want a creative editor, workflow environment or management app.",
          "steps": [
            "Choose Apps in navigation.",
            "Review an app’s category, description and status.",
            "Choose Guide for the interactive explanation or Open to open the application in a new tab."
          ],
          "permissions": "You must be signed in. Members see permitted apps for active modules; platform administrators also see configured management apps. Each application checks its own access.",
          "limits": "A configured address is not a health check or proof of a licence. Not configured has no working Open button. Opening an app does not activate modules or change permissions.",
          "example": "Open a creative editor from Apps while keeping your chat in the original tab."
        }
      }
    },
    {
      "id": "webui.modules.overview",
      "area": "modules",
      "status": "conditional",
      "conditions": [
        "Configured installation and existing access"
      ],
      "anchors": [
        "?help_feature=webui.modules.overview",
        "#mainModules"
      ],
      "source_refs": [
        "api/org_modules.py",
        "api/apps_launcher.py",
        "static/modules.js"
      ],
      "related": [
        "webui.modules.apps"
      ],
      "locales": {
        "en": {
          "title": "Review your modules",
          "purpose": "Read the Standard and Advanced catalogue with the local activation state.",
          "when": "When reviewing the apps and modules available on your installation.",
          "steps": [
            "Open Modules from the navigation.",
            "Read each status and description."
          ],
          "permissions": "Organisation, billing or platform scope on an organisation installation; hidden at headquarters.",
          "limits": "Active means enabled in local configuration, not healthy or commercially approved. Advanced pilot availability still needs confirmation.",
          "example": "Read each status and description."
        },
        "nl": {
          "title": "Je modules bekijken",
          "purpose": "Lees de Standard- en Advanced-catalogus met de lokale activatiestatus.",
          "when": "Wanneer je de apps en modules van je installatie wilt bekijken.",
          "steps": [
            "Open Modules in de navigatie.",
            "Lees per module de status en beschrijving."
          ],
          "permissions": "Organisatie-, facturatie- of platformbeheer op een organisatie-installatie; verborgen op het centrale beheersysteem.",
          "limits": "Actief betekent ingeschakeld in de lokale configuratie, niet gezond of commercieel goedgekeurd. Beschikbaarheid van Advanced-pilots vereist bevestiging.",
          "example": "Lees per module de status en beschrijving."
        }
      }
    },
    {
      "id": "webui.modules.budget",
      "area": "modules",
      "status": "conditional",
      "conditions": [
        "Configured installation and existing access"
      ],
      "anchors": [
        "?help_feature=webui.modules.budget",
        "#mainModules"
      ],
      "source_refs": [
        "api/org_modules.py",
        "api/apps_launcher.py",
        "static/modules.js"
      ],
      "related": [
        "webui.modules.overview"
      ],
      "locales": {
        "en": {
          "title": "Read module budget usage",
          "purpose": "See whether a module consumes the model budget and its catalogue usage category.",
          "when": "When reviewing the apps and modules available on your installation.",
          "steps": [
            "Open Modules.",
            "Read Model budget on the module card."
          ],
          "permissions": "The same organisation administration scope as Modules.",
          "limits": "The category is descriptive, not measured spend, a price, a cap or a guarantee.",
          "example": "Read Model budget on the module card."
        },
        "nl": {
          "title": "Modelgebruik per module lezen",
          "purpose": "Zie of een module modelbudget gebruikt en welke gebruikscategorie de catalogus noemt.",
          "when": "Wanneer je de apps en modules van je installatie wilt bekijken.",
          "steps": [
            "Open Modules.",
            "Lees Modelbudget op de modulekaart."
          ],
          "permissions": "Dezelfde organisatiebeheerrechten als Modules.",
          "limits": "De categorie is beschrijvend, geen gemeten bedrag, prijs, limiet of garantie.",
          "example": "Lees Modelbudget op de modulekaart."
        }
      }
    },
    {
      "id": "webui.modules.connections",
      "area": "modules",
      "status": "conditional",
      "conditions": [
        "Configured installation and existing access"
      ],
      "anchors": [
        "?help_feature=webui.modules.connections",
        "#mainModules"
      ],
      "source_refs": [
        "api/org_modules.py",
        "api/apps_launcher.py",
        "static/modules.js"
      ],
      "related": [
        "webui.modules.overview"
      ],
      "locales": {
        "en": {
          "title": "Understand module connections",
          "purpose": "Read which modules can work together and whether each connection is configured.",
          "when": "When reviewing the apps and modules available on your installation.",
          "steps": [
            "Open Works with on a module card.",
            "Read the connection state and consent note."
          ],
          "permissions": "The same organisation administration scope as Modules.",
          "limits": "This is read-only. Connected describes configuration; runtime conditions and consent still apply. No data is sent by expanding this list.",
          "example": "Read the connection state and consent note."
        },
        "nl": {
          "title": "Koppelingen tussen modules begrijpen",
          "purpose": "Lees welke modules kunnen samenwerken en of iedere koppeling is ingesteld.",
          "when": "Wanneer je de apps en modules van je installatie wilt bekijken.",
          "steps": [
            "Open Werkt samen met op een modulekaart.",
            "Lees de koppelingsstatus en de toestemmingsnotitie."
          ],
          "permissions": "Dezelfde organisatiebeheerrechten als Modules.",
          "limits": "Dit overzicht is alleen-lezen. Verbonden beschrijft de configuratie; voorwaarden tijdens uitvoering en toestemming blijven gelden. De lijst openen verstuurt geen gegevens.",
          "example": "Lees de koppelingsstatus en de toestemmingsnotitie."
        }
      }
    },
    {
      "id": "webui.modules.request",
      "area": "modules",
      "status": "conditional",
      "conditions": [
        "Configured installation and existing access"
      ],
      "anchors": [
        "?help_feature=webui.modules.request",
        "#mainModules"
      ],
      "source_refs": [
        "api/org_modules.py",
        "api/apps_launcher.py",
        "static/modules.js"
      ],
      "related": [
        "webui.modules.overview"
      ],
      "locales": {
        "en": {
          "title": "Ask about an Advanced module",
          "purpose": "Find the contact instruction for availability and setup.",
          "when": "When reviewing the apps and modules available on your installation.",
          "steps": [
            "Expand Request this module on an Advanced card.",
            "Discuss the module with your organisation administrator or service contact."
          ],
          "permissions": "The same organisation administration scope as Modules.",
          "limits": "No request is submitted, no purchase occurs and no service is activated. Prices are supplied separately.",
          "example": "Discuss the module with your organisation administrator or service contact."
        },
        "nl": {
          "title": "Informeren naar een Advanced-module",
          "purpose": "Vind de contactinstructie voor beschikbaarheid en inrichting.",
          "when": "Wanneer je de apps en modules van je installatie wilt bekijken.",
          "steps": [
            "Klap Deze module aanvragen op een Advanced-kaart open.",
            "Bespreek de module met je organisatiebeheerder of servicecontact."
          ],
          "permissions": "Dezelfde organisatiebeheerrechten als Modules.",
          "limits": "Er wordt geen aanvraag verstuurd, niets gekocht en geen dienst geactiveerd. Prijzen worden apart verstrekt.",
          "example": "Bespreek de module met je organisatiebeheerder of servicecontact."
        }
      }
    },
    {
      "id": "webui.modules.language",
      "area": "modules",
      "status": "conditional",
      "conditions": [
        "Configured installation and existing access"
      ],
      "anchors": [
        "?help_feature=webui.modules.language",
        "#mainModules"
      ],
      "source_refs": [
        "api/org_modules.py",
        "api/apps_launcher.py",
        "static/modules.js"
      ],
      "related": [
        "webui.modules.overview"
      ],
      "locales": {
        "en": {
          "title": "Change the module language",
          "purpose": "Read the Apps and Modules screens in Dutch or English.",
          "when": "When reviewing the apps and modules available on your installation.",
          "steps": [
            "Choose Language in Apps or Modules.",
            "Select Nederlands or English."
          ],
          "permissions": "Your existing access to Apps or Modules.",
          "limits": "The choice is stored in this browser and changes these screens only. It does not change permissions or other users’ language.",
          "example": "Select Nederlands or English."
        },
        "nl": {
          "title": "De moduletaal wijzigen",
          "purpose": "Lees de schermen Apps en Modules in Nederlands of Engels.",
          "when": "Wanneer je de apps en modules van je installatie wilt bekijken.",
          "steps": [
            "Kies Taal in Apps of Modules.",
            "Kies Nederlands of English."
          ],
          "permissions": "Je bestaande toegang tot Apps of Modules.",
          "limits": "De keuze wordt in deze browser opgeslagen en geldt voor deze schermen. Rechten en de taal van andere gebruikers veranderen niet.",
          "example": "Kies Nederlands of English."
        }
      }
    },
    {
      "id": "webui.apps.overview",
      "area": "apps",
      "status": "conditional",
      "conditions": [
        "Configured app directory and existing access"
      ],
      "anchors": [
        "?help_feature=webui.apps.overview",
        "#mainApps"
      ],
      "source_refs": [
        "api/app_catalog.py",
        "api/apps_launcher.py",
        "static/apps.js"
      ],
      "related": [
        "webui.apps.search",
        "webui.apps.categories"
      ],
      "locales": {
        "nl": {
          "title": "Apps als eigen onderdeel",
          "purpose": "Open de beschikbare toepassingen van je installatie vanuit Apps in de navigatie.",
          "when": "Wanneer je naar een creatieve editor, workflowomgeving of beheerapp wilt.",
          "steps": [
            "Kies Apps in de navigatie.",
            "Bekijk de categorie, beschrijving en status van een app.",
            "Kies Uitleg voor de interactieve gids of Openen om de toepassing in een nieuw tabblad te openen."
          ],
          "permissions": "Je moet aangemeld zijn. Leden zien toegestane apps voor actieve modules; platformbeheerders zien ook ingestelde beheerapps. Iedere app controleert zelf de toegang.",
          "limits": "Een ingesteld adres is geen gezondheidscontrole of bewijs van een licentie. Niet ingesteld heeft geen werkende Openen-knop. Een app openen activeert geen module en wijzigt geen rechten.",
          "example": "Open een creatieve editor vanuit Apps en houd je chat in het oorspronkelijke tabblad."
        },
        "en": {
          "title": "Apps as a dedicated section",
          "purpose": "Open the available applications for your installation from Apps in navigation.",
          "when": "When you want a creative editor, workflow environment or management app.",
          "steps": [
            "Choose Apps in navigation.",
            "Review an app’s category, description and status.",
            "Choose Guide for the interactive explanation or Open to open the application in a new tab."
          ],
          "permissions": "You must be signed in. Members see permitted apps for active modules; platform administrators also see configured management apps. Each application checks its own access.",
          "limits": "A configured address is not a health check or proof of a licence. Not configured has no working Open button. Opening an app does not activate modules or change permissions.",
          "example": "Open a creative editor from Apps while keeping your chat in the original tab."
        }
      }
    },
    {
      "id": "webui.apps.search",
      "area": "apps",
      "status": "conditional",
      "conditions": [
        "Configured app directory and existing access"
      ],
      "anchors": [
        "?help_feature=webui.apps.search",
        "#appsSearch"
      ],
      "source_refs": [
        "api/app_catalog.py",
        "api/apps_launcher.py",
        "static/apps.js"
      ],
      "related": [
        "webui.apps.overview"
      ],
      "locales": {
        "nl": {
          "title": "Een app zoeken",
          "purpose": "Filter de appkaarten op naam of beschrijving.",
          "when": "Wanneer je een bepaalde toepassing snel wilt terugvinden.",
          "steps": [
            "Open Apps.",
            "Typ de naam of een beschrijvend woord in Apps zoeken.",
            "Wis de zoektekst of herstel de filters als je alle toegestane kaarten wilt zien."
          ],
          "permissions": "Dezelfde toegang als de Apps-sectie. Zoeken geeft geen toegang tot verborgen beheerapps.",
          "limits": "Zoeken filtert alleen deze appcatalogus in je browser. Het doorzoekt geen documenten of inhoud binnen de apps. De categoriekeuze blijft ook van toepassing.",
          "example": "Zoek PhotoCraft om de bijbehorende kaart te vinden."
        },
        "en": {
          "title": "Search for an app",
          "purpose": "Filter app cards by name or description.",
          "when": "When you want to find a particular application quickly.",
          "steps": [
            "Open Apps.",
            "Type an app name or descriptive word in Search apps.",
            "Clear the search text or reset filters to see all permitted cards."
          ],
          "permissions": "The same access as the Apps section. Search does not reveal restricted management apps.",
          "limits": "Search filters this app catalogue in your browser only. It does not search documents or content inside applications. The selected category also applies.",
          "example": "Search for PhotoCraft to find its card."
        }
      }
    },
    {
      "id": "webui.apps.categories",
      "area": "apps",
      "status": "conditional",
      "conditions": [
        "Configured app directory and existing access"
      ],
      "anchors": [
        "?help_feature=webui.apps.categories",
        "#appsCategory"
      ],
      "source_refs": [
        "api/app_catalog.py",
        "api/apps_launcher.py",
        "static/apps.js"
      ],
      "related": [
        "webui.apps.overview"
      ],
      "locales": {
        "nl": {
          "title": "Apps per categorie bekijken",
          "purpose": "Beperk het overzicht tot creatief werk, Craft Studio, productiviteit, automatisering of platformbeheer.",
          "when": "Wanneer je een passende tool zoekt binnen een bepaald soort werk.",
          "steps": [
            "Open Apps.",
            "Kies een categorie in het categoriefilter.",
            "Kies Alle categorieën om het volledige toegestane overzicht terug te krijgen."
          ],
          "permissions": "Alleen apps die al voor jou zichtbaar zijn worden gegroepeerd. Platformbeheer blijft beperkt tot platformbeheerders.",
          "limits": "Een categorie is een weergavefilter. Je activeert geen dienst, abonnement of module. Een eventuele zoektekst blijft van toepassing.",
          "example": "Kies Craft Studio om de studio en de acht afzonderlijke editors te bekijken."
        },
        "en": {
          "title": "Browse apps by category",
          "purpose": "Limit the directory to creative work, Craft Studio, productivity, automation or platform management.",
          "when": "When you want a suitable tool for a particular type of work.",
          "steps": [
            "Open Apps.",
            "Select a category from the category filter.",
            "Choose All categories to restore the full permitted directory."
          ],
          "permissions": "Only apps already visible to you are grouped. Platform management remains restricted to platform administrators.",
          "limits": "A category is a display filter. It does not activate a service, subscription or module. Any search text still applies.",
          "example": "Choose Craft Studio to view the studio and all eight separate editors."
        }
      }
    },
    {
      "id": "webui.apps.opendesign",
      "area": "apps",
      "status": "conditional",
      "conditions": [
        "Configured app directory and existing access"
      ],
      "anchors": [
        "?help_feature=webui.apps.opendesign",
        "#mainApps [data-app-id=\"opendesign\"]"
      ],
      "source_refs": [
        "api/app_catalog.py",
        "api/apps_launcher.py",
        "static/apps.js"
      ],
      "related": [
        "webui.apps.overview"
      ],
      "locales": {
        "nl": {
          "title": "OpenDesign openen",
          "purpose": "Ontwerp en bewerk visuele projecten en merkuitingen.",
          "when": "Gebruik deze ingang voor een campagnebeeld met de juiste kleuren en typografie.",
          "steps": [
            "Kies Apps in de navigatie en zoek OpenDesign.",
            "Bekijk de status en de beschrijving van de kaart.",
            "Sluit de gids en kies Openen als een adres is ingesteld. Rond indien nodig de eigen aanmelding van de app af.",
            "Werk verder in de doelapp en gebruik het oorspronkelijke tabblad om terug te keren naar SynthPulse."
          ],
          "permissions": "Toegang tot Apps en de bijbehorende actieve module; platformbeheerders kunnen ingestelde appadressen ook zonder die module bekijken. De doelapp controleert zelf je toegang.",
          "limits": "Openen navigeert alleen naar het ingestelde adres. De app kan een eigen aanmelding vereisen. Niet ingesteld betekent dat er geen bruikbare link is; een ingestelde link garandeert niet dat de dienst bereikbaar is.",
          "example": "Bijvoorbeeld: een campagnebeeld met de juiste kleuren en typografie."
        },
        "en": {
          "title": "Open OpenDesign",
          "purpose": "Design and edit visual projects and branded materials.",
          "when": "Use this entry point for a campaign visual with the right colours and typography.",
          "steps": [
            "Choose Apps in navigation and find OpenDesign.",
            "Review the card’s status and description.",
            "Close the guide and choose Open when an address is configured. Complete the app’s own sign-in if required.",
            "Continue in the destination app and use the original tab to return to SynthPulse."
          ],
          "permissions": "Access to Apps and the associated active module; platform administrators can discover configured app addresses even without that module. The destination app checks its own access.",
          "limits": "Open only navigates to the configured address. The app may require its own sign-in. Not configured means there is no usable link; a configured link does not guarantee the service is reachable.",
          "example": "For example: a campaign visual with the right colours and typography."
        }
      }
    },
    {
      "id": "webui.apps.craft_studio",
      "area": "apps",
      "status": "conditional",
      "conditions": [
        "Configured app directory and existing access"
      ],
      "anchors": [
        "?help_feature=webui.apps.craft_studio",
        "#mainApps [data-app-id=\"craft_studio\"]"
      ],
      "source_refs": [
        "api/app_catalog.py",
        "api/apps_launcher.py",
        "static/apps.js"
      ],
      "related": [
        "webui.apps.overview"
      ],
      "locales": {
        "nl": {
          "title": "Craft Studio openen",
          "purpose": "Kies een creatieve editor voor beeld, video, ontwerp, documenten of audio.",
          "when": "Gebruik deze ingang voor de passende editor voor een foto, video of document.",
          "steps": [
            "Kies Apps in de navigatie en zoek Craft Studio.",
            "Bekijk de status en de beschrijving van de kaart.",
            "Sluit de gids en kies Openen als een adres is ingesteld. Rond indien nodig de eigen aanmelding van de app af.",
            "Werk verder in de doelapp en gebruik het oorspronkelijke tabblad om terug te keren naar SynthPulse."
          ],
          "permissions": "Toegang tot Apps en de bijbehorende actieve module; platformbeheerders kunnen ingestelde appadressen ook zonder die module bekijken. De doelapp controleert zelf je toegang.",
          "limits": "Openen navigeert alleen naar het ingestelde adres. De app kan een eigen aanmelding vereisen. Niet ingesteld betekent dat er geen bruikbare link is; een ingestelde link garandeert niet dat de dienst bereikbaar is. Dit is de browseringang. De kaart synchroniseert geen bestanden of projecten met een desktopeditor of andere Craft-app.",
          "example": "Bijvoorbeeld: de passende editor voor een foto, video of document."
        },
        "en": {
          "title": "Open Craft Studio",
          "purpose": "Choose a creative editor for images, video, design, documents or audio.",
          "when": "Use this entry point for the appropriate editor for a photo, video or document.",
          "steps": [
            "Choose Apps in navigation and find Craft Studio.",
            "Review the card’s status and description.",
            "Close the guide and choose Open when an address is configured. Complete the app’s own sign-in if required.",
            "Continue in the destination app and use the original tab to return to SynthPulse."
          ],
          "permissions": "Access to Apps and the associated active module; platform administrators can discover configured app addresses even without that module. The destination app checks its own access.",
          "limits": "Open only navigates to the configured address. The app may require its own sign-in. Not configured means there is no usable link; a configured link does not guarantee the service is reachable. This is the browser entry point. The card does not synchronise files or projects with a desktop editor or another Craft app.",
          "example": "For example: the appropriate editor for a photo, video or document."
        }
      }
    },
    {
      "id": "webui.apps.photocraft",
      "area": "apps",
      "status": "conditional",
      "conditions": [
        "Configured app directory and existing access"
      ],
      "anchors": [
        "?help_feature=webui.apps.photocraft",
        "#mainApps [data-app-id=\"photocraft\"]"
      ],
      "source_refs": [
        "api/app_catalog.py",
        "api/apps_launcher.py",
        "static/apps.js"
      ],
      "related": [
        "webui.apps.overview"
      ],
      "locales": {
        "nl": {
          "title": "PhotoCraft openen",
          "purpose": "Bewerk foto’s en maak beeldcomposities.",
          "when": "Gebruik deze ingang voor een foto bijsnijden en de compositie aanpassen.",
          "steps": [
            "Kies Apps in de navigatie en zoek PhotoCraft.",
            "Bekijk de status en de beschrijving van de kaart.",
            "Sluit de gids en kies Openen als een adres is ingesteld. Rond indien nodig de eigen aanmelding van de app af.",
            "Werk verder in de doelapp en gebruik het oorspronkelijke tabblad om terug te keren naar SynthPulse."
          ],
          "permissions": "Toegang tot Apps en de bijbehorende actieve module; platformbeheerders kunnen ingestelde appadressen ook zonder die module bekijken. De doelapp controleert zelf je toegang.",
          "limits": "Openen navigeert alleen naar het ingestelde adres. De app kan een eigen aanmelding vereisen. Niet ingesteld betekent dat er geen bruikbare link is; een ingestelde link garandeert niet dat de dienst bereikbaar is. Dit is de browseringang. De kaart synchroniseert geen bestanden of projecten met een desktopeditor of andere Craft-app.",
          "example": "Bijvoorbeeld: een foto bijsnijden en de compositie aanpassen."
        },
        "en": {
          "title": "Open PhotoCraft",
          "purpose": "Edit photos and create image compositions.",
          "when": "Use this entry point for cropping a photo and adjusting its composition.",
          "steps": [
            "Choose Apps in navigation and find PhotoCraft.",
            "Review the card’s status and description.",
            "Close the guide and choose Open when an address is configured. Complete the app’s own sign-in if required.",
            "Continue in the destination app and use the original tab to return to SynthPulse."
          ],
          "permissions": "Access to Apps and the associated active module; platform administrators can discover configured app addresses even without that module. The destination app checks its own access.",
          "limits": "Open only navigates to the configured address. The app may require its own sign-in. Not configured means there is no usable link; a configured link does not guarantee the service is reachable. This is the browser entry point. The card does not synchronise files or projects with a desktop editor or another Craft app.",
          "example": "For example: cropping a photo and adjusting its composition."
        }
      }
    },
    {
      "id": "webui.apps.filmcraft",
      "area": "apps",
      "status": "conditional",
      "conditions": [
        "Configured app directory and existing access"
      ],
      "anchors": [
        "?help_feature=webui.apps.filmcraft",
        "#mainApps [data-app-id=\"filmcraft\"]"
      ],
      "source_refs": [
        "api/app_catalog.py",
        "api/apps_launcher.py",
        "static/apps.js"
      ],
      "related": [
        "webui.apps.overview"
      ],
      "locales": {
        "nl": {
          "title": "FilmCraft openen",
          "purpose": "Monteer video’s en werk aan je tijdlijn.",
          "when": "Gebruik deze ingang voor videofragmenten ordenen voor een korte montage.",
          "steps": [
            "Kies Apps in de navigatie en zoek FilmCraft.",
            "Bekijk de status en de beschrijving van de kaart.",
            "Sluit de gids en kies Openen als een adres is ingesteld. Rond indien nodig de eigen aanmelding van de app af.",
            "Werk verder in de doelapp en gebruik het oorspronkelijke tabblad om terug te keren naar SynthPulse."
          ],
          "permissions": "Toegang tot Apps en de bijbehorende actieve module; platformbeheerders kunnen ingestelde appadressen ook zonder die module bekijken. De doelapp controleert zelf je toegang.",
          "limits": "Openen navigeert alleen naar het ingestelde adres. De app kan een eigen aanmelding vereisen. Niet ingesteld betekent dat er geen bruikbare link is; een ingestelde link garandeert niet dat de dienst bereikbaar is. Dit is de browseringang. De kaart synchroniseert geen bestanden of projecten met een desktopeditor of andere Craft-app.",
          "example": "Bijvoorbeeld: videofragmenten ordenen voor een korte montage."
        },
        "en": {
          "title": "Open FilmCraft",
          "purpose": "Edit videos and work on your timeline.",
          "when": "Use this entry point for arranging video clips for a short edit.",
          "steps": [
            "Choose Apps in navigation and find FilmCraft.",
            "Review the card’s status and description.",
            "Close the guide and choose Open when an address is configured. Complete the app’s own sign-in if required.",
            "Continue in the destination app and use the original tab to return to SynthPulse."
          ],
          "permissions": "Access to Apps and the associated active module; platform administrators can discover configured app addresses even without that module. The destination app checks its own access.",
          "limits": "Open only navigates to the configured address. The app may require its own sign-in. Not configured means there is no usable link; a configured link does not guarantee the service is reachable. This is the browser entry point. The card does not synchronise files or projects with a desktop editor or another Craft app.",
          "example": "For example: arranging video clips for a short edit."
        }
      }
    },
    {
      "id": "webui.apps.effectcraft",
      "area": "apps",
      "status": "conditional",
      "conditions": [
        "Configured app directory and existing access"
      ],
      "anchors": [
        "?help_feature=webui.apps.effectcraft",
        "#mainApps [data-app-id=\"effectcraft\"]"
      ],
      "source_refs": [
        "api/app_catalog.py",
        "api/apps_launcher.py",
        "static/apps.js"
      ],
      "related": [
        "webui.apps.overview"
      ],
      "locales": {
        "nl": {
          "title": "EffectCraft openen",
          "purpose": "Maak visuele effecten en bewegende composities.",
          "when": "Gebruik deze ingang voor een compositie met bewegende visuele elementen.",
          "steps": [
            "Kies Apps in de navigatie en zoek EffectCraft.",
            "Bekijk de status en de beschrijving van de kaart.",
            "Sluit de gids en kies Openen als een adres is ingesteld. Rond indien nodig de eigen aanmelding van de app af.",
            "Werk verder in de doelapp en gebruik het oorspronkelijke tabblad om terug te keren naar SynthPulse."
          ],
          "permissions": "Toegang tot Apps en de bijbehorende actieve module; platformbeheerders kunnen ingestelde appadressen ook zonder die module bekijken. De doelapp controleert zelf je toegang.",
          "limits": "Openen navigeert alleen naar het ingestelde adres. De app kan een eigen aanmelding vereisen. Niet ingesteld betekent dat er geen bruikbare link is; een ingestelde link garandeert niet dat de dienst bereikbaar is. Dit is de browseringang. De kaart synchroniseert geen bestanden of projecten met een desktopeditor of andere Craft-app.",
          "example": "Bijvoorbeeld: een compositie met bewegende visuele elementen."
        },
        "en": {
          "title": "Open EffectCraft",
          "purpose": "Create visual effects and animated compositions.",
          "when": "Use this entry point for a composition with animated visual elements.",
          "steps": [
            "Choose Apps in navigation and find EffectCraft.",
            "Review the card’s status and description.",
            "Close the guide and choose Open when an address is configured. Complete the app’s own sign-in if required.",
            "Continue in the destination app and use the original tab to return to SynthPulse."
          ],
          "permissions": "Access to Apps and the associated active module; platform administrators can discover configured app addresses even without that module. The destination app checks its own access.",
          "limits": "Open only navigates to the configured address. The app may require its own sign-in. Not configured means there is no usable link; a configured link does not guarantee the service is reachable. This is the browser entry point. The card does not synchronise files or projects with a desktop editor or another Craft app.",
          "example": "For example: a composition with animated visual elements."
        }
      }
    },
    {
      "id": "webui.apps.vectorcraft",
      "area": "apps",
      "status": "conditional",
      "conditions": [
        "Configured app directory and existing access"
      ],
      "anchors": [
        "?help_feature=webui.apps.vectorcraft",
        "#mainApps [data-app-id=\"vectorcraft\"]"
      ],
      "source_refs": [
        "api/app_catalog.py",
        "api/apps_launcher.py",
        "static/apps.js"
      ],
      "related": [
        "webui.apps.overview"
      ],
      "locales": {
        "nl": {
          "title": "VectorCraft openen",
          "purpose": "Teken en bewerk vectorillustraties.",
          "when": "Gebruik deze ingang voor een schaalbare illustratie voor een publicatie.",
          "steps": [
            "Kies Apps in de navigatie en zoek VectorCraft.",
            "Bekijk de status en de beschrijving van de kaart.",
            "Sluit de gids en kies Openen als een adres is ingesteld. Rond indien nodig de eigen aanmelding van de app af.",
            "Werk verder in de doelapp en gebruik het oorspronkelijke tabblad om terug te keren naar SynthPulse."
          ],
          "permissions": "Toegang tot Apps en de bijbehorende actieve module; platformbeheerders kunnen ingestelde appadressen ook zonder die module bekijken. De doelapp controleert zelf je toegang.",
          "limits": "Openen navigeert alleen naar het ingestelde adres. De app kan een eigen aanmelding vereisen. Niet ingesteld betekent dat er geen bruikbare link is; een ingestelde link garandeert niet dat de dienst bereikbaar is. Dit is de browseringang. De kaart synchroniseert geen bestanden of projecten met een desktopeditor of andere Craft-app.",
          "example": "Bijvoorbeeld: een schaalbare illustratie voor een publicatie."
        },
        "en": {
          "title": "Open VectorCraft",
          "purpose": "Draw and edit vector illustrations.",
          "when": "Use this entry point for a scalable illustration for a publication.",
          "steps": [
            "Choose Apps in navigation and find VectorCraft.",
            "Review the card’s status and description.",
            "Close the guide and choose Open when an address is configured. Complete the app’s own sign-in if required.",
            "Continue in the destination app and use the original tab to return to SynthPulse."
          ],
          "permissions": "Access to Apps and the associated active module; platform administrators can discover configured app addresses even without that module. The destination app checks its own access.",
          "limits": "Open only navigates to the configured address. The app may require its own sign-in. Not configured means there is no usable link; a configured link does not guarantee the service is reachable. This is the browser entry point. The card does not synchronise files or projects with a desktop editor or another Craft app.",
          "example": "For example: a scalable illustration for a publication."
        }
      }
    },
    {
      "id": "webui.apps.lightcraft",
      "area": "apps",
      "status": "conditional",
      "conditions": [
        "Configured app directory and existing access"
      ],
      "anchors": [
        "?help_feature=webui.apps.lightcraft",
        "#mainApps [data-app-id=\"lightcraft\"]"
      ],
      "source_refs": [
        "api/app_catalog.py",
        "api/apps_launcher.py",
        "static/apps.js"
      ],
      "related": [
        "webui.apps.overview"
      ],
      "locales": {
        "nl": {
          "title": "LightCraft openen",
          "purpose": "Ontwikkel en corrigeer foto’s.",
          "when": "Gebruik deze ingang voor de belichting en kleuren van een foto beoordelen.",
          "steps": [
            "Kies Apps in de navigatie en zoek LightCraft.",
            "Bekijk de status en de beschrijving van de kaart.",
            "Sluit de gids en kies Openen als een adres is ingesteld. Rond indien nodig de eigen aanmelding van de app af.",
            "Werk verder in de doelapp en gebruik het oorspronkelijke tabblad om terug te keren naar SynthPulse."
          ],
          "permissions": "Toegang tot Apps en de bijbehorende actieve module; platformbeheerders kunnen ingestelde appadressen ook zonder die module bekijken. De doelapp controleert zelf je toegang.",
          "limits": "Openen navigeert alleen naar het ingestelde adres. De app kan een eigen aanmelding vereisen. Niet ingesteld betekent dat er geen bruikbare link is; een ingestelde link garandeert niet dat de dienst bereikbaar is. Dit is de browseringang. De kaart synchroniseert geen bestanden of projecten met een desktopeditor of andere Craft-app.",
          "example": "Bijvoorbeeld: de belichting en kleuren van een foto beoordelen."
        },
        "en": {
          "title": "Open LightCraft",
          "purpose": "Develop and correct photos.",
          "when": "Use this entry point for reviewing the exposure and colours of a photo.",
          "steps": [
            "Choose Apps in navigation and find LightCraft.",
            "Review the card’s status and description.",
            "Close the guide and choose Open when an address is configured. Complete the app’s own sign-in if required.",
            "Continue in the destination app and use the original tab to return to SynthPulse."
          ],
          "permissions": "Access to Apps and the associated active module; platform administrators can discover configured app addresses even without that module. The destination app checks its own access.",
          "limits": "Open only navigates to the configured address. The app may require its own sign-in. Not configured means there is no usable link; a configured link does not guarantee the service is reachable. This is the browser entry point. The card does not synchronise files or projects with a desktop editor or another Craft app.",
          "example": "For example: reviewing the exposure and colours of a photo."
        }
      }
    },
    {
      "id": "webui.apps.designcraft",
      "area": "apps",
      "status": "conditional",
      "conditions": [
        "Configured app directory and existing access"
      ],
      "anchors": [
        "?help_feature=webui.apps.designcraft",
        "#mainApps [data-app-id=\"designcraft\"]"
      ],
      "source_refs": [
        "api/app_catalog.py",
        "api/apps_launcher.py",
        "static/apps.js"
      ],
      "related": [
        "webui.apps.overview"
      ],
      "locales": {
        "nl": {
          "title": "DesignCraft openen",
          "purpose": "Maak ontwerpen en paginalay-outs.",
          "when": "Gebruik deze ingang voor een consistente pagina-indeling voor een ontwerp.",
          "steps": [
            "Kies Apps in de navigatie en zoek DesignCraft.",
            "Bekijk de status en de beschrijving van de kaart.",
            "Sluit de gids en kies Openen als een adres is ingesteld. Rond indien nodig de eigen aanmelding van de app af.",
            "Werk verder in de doelapp en gebruik het oorspronkelijke tabblad om terug te keren naar SynthPulse."
          ],
          "permissions": "Toegang tot Apps en de bijbehorende actieve module; platformbeheerders kunnen ingestelde appadressen ook zonder die module bekijken. De doelapp controleert zelf je toegang.",
          "limits": "Openen navigeert alleen naar het ingestelde adres. De app kan een eigen aanmelding vereisen. Niet ingesteld betekent dat er geen bruikbare link is; een ingestelde link garandeert niet dat de dienst bereikbaar is. Dit is de browseringang. De kaart synchroniseert geen bestanden of projecten met een desktopeditor of andere Craft-app.",
          "example": "Bijvoorbeeld: een consistente pagina-indeling voor een ontwerp."
        },
        "en": {
          "title": "Open DesignCraft",
          "purpose": "Create designs and page layouts.",
          "when": "Use this entry point for a consistent page layout for a design.",
          "steps": [
            "Choose Apps in navigation and find DesignCraft.",
            "Review the card’s status and description.",
            "Close the guide and choose Open when an address is configured. Complete the app’s own sign-in if required.",
            "Continue in the destination app and use the original tab to return to SynthPulse."
          ],
          "permissions": "Access to Apps and the associated active module; platform administrators can discover configured app addresses even without that module. The destination app checks its own access.",
          "limits": "Open only navigates to the configured address. The app may require its own sign-in. Not configured means there is no usable link; a configured link does not guarantee the service is reachable. This is the browser entry point. The card does not synchronise files or projects with a desktop editor or another Craft app.",
          "example": "For example: a consistent page layout for a design."
        }
      }
    },
    {
      "id": "webui.apps.pdfcraft",
      "area": "apps",
      "status": "conditional",
      "conditions": [
        "Configured app directory and existing access"
      ],
      "anchors": [
        "?help_feature=webui.apps.pdfcraft",
        "#mainApps [data-app-id=\"pdfcraft\"]"
      ],
      "source_refs": [
        "api/app_catalog.py",
        "api/apps_launcher.py",
        "static/apps.js"
      ],
      "related": [
        "webui.apps.overview"
      ],
      "locales": {
        "nl": {
          "title": "PDFCraft openen",
          "purpose": "Open en bewerk pdf-documenten.",
          "when": "Gebruik deze ingang voor een pdf-document beoordelen en aanpassen.",
          "steps": [
            "Kies Apps in de navigatie en zoek PDFCraft.",
            "Bekijk de status en de beschrijving van de kaart.",
            "Sluit de gids en kies Openen als een adres is ingesteld. Rond indien nodig de eigen aanmelding van de app af.",
            "Werk verder in de doelapp en gebruik het oorspronkelijke tabblad om terug te keren naar SynthPulse."
          ],
          "permissions": "Toegang tot Apps en de bijbehorende actieve module; platformbeheerders kunnen ingestelde appadressen ook zonder die module bekijken. De doelapp controleert zelf je toegang.",
          "limits": "Openen navigeert alleen naar het ingestelde adres. De app kan een eigen aanmelding vereisen. Niet ingesteld betekent dat er geen bruikbare link is; een ingestelde link garandeert niet dat de dienst bereikbaar is. Dit is de browseringang. De kaart synchroniseert geen bestanden of projecten met een desktopeditor of andere Craft-app.",
          "example": "Bijvoorbeeld: een pdf-document beoordelen en aanpassen."
        },
        "en": {
          "title": "Open PDFCraft",
          "purpose": "Open and edit PDF documents.",
          "when": "Use this entry point for reviewing and adjusting a PDF document.",
          "steps": [
            "Choose Apps in navigation and find PDFCraft.",
            "Review the card’s status and description.",
            "Close the guide and choose Open when an address is configured. Complete the app’s own sign-in if required.",
            "Continue in the destination app and use the original tab to return to SynthPulse."
          ],
          "permissions": "Access to Apps and the associated active module; platform administrators can discover configured app addresses even without that module. The destination app checks its own access.",
          "limits": "Open only navigates to the configured address. The app may require its own sign-in. Not configured means there is no usable link; a configured link does not guarantee the service is reachable. This is the browser entry point. The card does not synchronise files or projects with a desktop editor or another Craft app.",
          "example": "For example: reviewing and adjusting a PDF document."
        }
      }
    },
    {
      "id": "webui.apps.soundcraft",
      "area": "apps",
      "status": "conditional",
      "conditions": [
        "Configured app directory and existing access"
      ],
      "anchors": [
        "?help_feature=webui.apps.soundcraft",
        "#mainApps [data-app-id=\"soundcraft\"]"
      ],
      "source_refs": [
        "api/app_catalog.py",
        "api/apps_launcher.py",
        "static/apps.js"
      ],
      "related": [
        "webui.apps.overview"
      ],
      "locales": {
        "nl": {
          "title": "SoundCraft openen",
          "purpose": "Neem audio op en bewerk geluid.",
          "when": "Gebruik deze ingang voor een geluidsopname voorbereiden en bewerken.",
          "steps": [
            "Kies Apps in de navigatie en zoek SoundCraft.",
            "Bekijk de status en de beschrijving van de kaart.",
            "Sluit de gids en kies Openen als een adres is ingesteld. Rond indien nodig de eigen aanmelding van de app af.",
            "Werk verder in de doelapp en gebruik het oorspronkelijke tabblad om terug te keren naar SynthPulse."
          ],
          "permissions": "Toegang tot Apps en de bijbehorende actieve module; platformbeheerders kunnen ingestelde appadressen ook zonder die module bekijken. De doelapp controleert zelf je toegang.",
          "limits": "Openen navigeert alleen naar het ingestelde adres. De app kan een eigen aanmelding vereisen. Niet ingesteld betekent dat er geen bruikbare link is; een ingestelde link garandeert niet dat de dienst bereikbaar is. Dit is de browseringang. De kaart synchroniseert geen bestanden of projecten met een desktopeditor of andere Craft-app.",
          "example": "Bijvoorbeeld: een geluidsopname voorbereiden en bewerken."
        },
        "en": {
          "title": "Open SoundCraft",
          "purpose": "Record audio and edit sound.",
          "when": "Use this entry point for preparing and editing an audio recording.",
          "steps": [
            "Choose Apps in navigation and find SoundCraft.",
            "Review the card’s status and description.",
            "Close the guide and choose Open when an address is configured. Complete the app’s own sign-in if required.",
            "Continue in the destination app and use the original tab to return to SynthPulse."
          ],
          "permissions": "Access to Apps and the associated active module; platform administrators can discover configured app addresses even without that module. The destination app checks its own access.",
          "limits": "Open only navigates to the configured address. The app may require its own sign-in. Not configured means there is no usable link; a configured link does not guarantee the service is reachable. This is the browser entry point. The card does not synchronise files or projects with a desktop editor or another Craft app.",
          "example": "For example: preparing and editing an audio recording."
        }
      }
    },
    {
      "id": "webui.apps.hyperframes",
      "area": "apps",
      "status": "conditional",
      "conditions": [
        "Configured app directory and existing access"
      ],
      "anchors": [
        "?help_feature=webui.apps.hyperframes",
        "#mainApps [data-app-id=\"hyperframes\"]"
      ],
      "source_refs": [
        "api/app_catalog.py",
        "api/apps_launcher.py",
        "static/apps.js"
      ],
      "related": [
        "webui.apps.overview"
      ],
      "locales": {
        "nl": {
          "title": "HyperFrames openen",
          "purpose": "Maak en bekijk animaties en videocomposities.",
          "when": "Gebruik deze ingang voor een animatie of videocompositie bekijken.",
          "steps": [
            "Kies Apps in de navigatie en zoek HyperFrames.",
            "Bekijk de status en de beschrijving van de kaart.",
            "Sluit de gids en kies Openen als een adres is ingesteld. Rond indien nodig de eigen aanmelding van de app af.",
            "Werk verder in de doelapp en gebruik het oorspronkelijke tabblad om terug te keren naar SynthPulse."
          ],
          "permissions": "Toegang tot Apps en de bijbehorende actieve module; platformbeheerders kunnen ingestelde appadressen ook zonder die module bekijken. De doelapp controleert zelf je toegang.",
          "limits": "Openen navigeert alleen naar het ingestelde adres. De app kan een eigen aanmelding vereisen. Niet ingesteld betekent dat er geen bruikbare link is; een ingestelde link garandeert niet dat de dienst bereikbaar is.",
          "example": "Bijvoorbeeld: een animatie of videocompositie bekijken."
        },
        "en": {
          "title": "Open HyperFrames",
          "purpose": "Create and preview animations and video compositions.",
          "when": "Use this entry point for previewing an animation or video composition.",
          "steps": [
            "Choose Apps in navigation and find HyperFrames.",
            "Review the card’s status and description.",
            "Close the guide and choose Open when an address is configured. Complete the app’s own sign-in if required.",
            "Continue in the destination app and use the original tab to return to SynthPulse."
          ],
          "permissions": "Access to Apps and the associated active module; platform administrators can discover configured app addresses even without that module. The destination app checks its own access.",
          "limits": "Open only navigates to the configured address. The app may require its own sign-in. Not configured means there is no usable link; a configured link does not guarantee the service is reachable.",
          "example": "For example: previewing an animation or video composition."
        }
      }
    },
    {
      "id": "webui.apps.n8n",
      "area": "apps",
      "status": "conditional",
      "conditions": [
        "Configured app directory and existing access"
      ],
      "anchors": [
        "?help_feature=webui.apps.n8n",
        "#mainApps [data-app-id=\"n8n\"]"
      ],
      "source_refs": [
        "api/app_catalog.py",
        "api/apps_launcher.py",
        "static/apps.js"
      ],
      "related": [
        "webui.apps.overview"
      ],
      "locales": {
        "nl": {
          "title": "n8n openen",
          "purpose": "Bouw en beheer geautomatiseerde workflows.",
          "when": "Gebruik deze ingang voor een bestaande workflow bekijken voordat je die wijzigt.",
          "steps": [
            "Kies Apps in de navigatie en zoek n8n.",
            "Bekijk de status en de beschrijving van de kaart.",
            "Sluit de gids en kies Openen als een adres is ingesteld. Rond indien nodig de eigen aanmelding van de app af.",
            "Werk verder in de doelapp en gebruik het oorspronkelijke tabblad om terug te keren naar SynthPulse."
          ],
          "permissions": "Platformbeheerrechten in SynthPulse en geldige toegang tot de doelapp. Leden kunnen de editor alleen zien als de installatiebeheerder dat expliciet heeft toegestaan.",
          "limits": "Openen navigeert alleen naar het ingestelde adres. De app kan een eigen aanmelding vereisen. Niet ingesteld betekent dat er geen bruikbare link is; een ingestelde link garandeert niet dat de dienst bereikbaar is. Wijzigingen, uitvoeringen of verzendingen doe je bewust binnen de doelapp; deze gids voert ze niet uit.",
          "example": "Bijvoorbeeld: een bestaande workflow bekijken voordat je die wijzigt."
        },
        "en": {
          "title": "Open n8n",
          "purpose": "Build and manage automated workflows.",
          "when": "Use this entry point for reviewing an existing workflow before changing it.",
          "steps": [
            "Choose Apps in navigation and find n8n.",
            "Review the card’s status and description.",
            "Close the guide and choose Open when an address is configured. Complete the app’s own sign-in if required.",
            "Continue in the destination app and use the original tab to return to SynthPulse."
          ],
          "permissions": "Platform administration access in SynthPulse and valid access to the destination app. Members only see the editor when the installation administrator has explicitly allowed it.",
          "limits": "Open only navigates to the configured address. The app may require its own sign-in. Not configured means there is no usable link; a configured link does not guarantee the service is reachable. Make changes, run tasks or send documents deliberately inside the destination app; this guide does not perform them.",
          "example": "For example: reviewing an existing workflow before changing it."
        }
      }
    },
    {
      "id": "webui.apps.omniroute",
      "area": "apps",
      "status": "conditional",
      "conditions": [
        "Configured app directory and existing access"
      ],
      "anchors": [
        "?help_feature=webui.apps.omniroute",
        "#mainApps [data-app-id=\"omniroute\"]"
      ],
      "source_refs": [
        "api/app_catalog.py",
        "api/apps_launcher.py",
        "static/apps.js"
      ],
      "related": [
        "webui.apps.overview"
      ],
      "locales": {
        "nl": {
          "title": "OmniRoute openen",
          "purpose": "Beheer modelroutes en verbindingen met AI-aanbieders.",
          "when": "Gebruik deze ingang voor controleren welke modelroute voor een aanbieder is ingesteld.",
          "steps": [
            "Kies Apps in de navigatie en zoek OmniRoute.",
            "Bekijk de status en de beschrijving van de kaart.",
            "Sluit de gids en kies Openen als een adres is ingesteld. Rond indien nodig de eigen aanmelding van de app af.",
            "Werk verder in de doelapp en gebruik het oorspronkelijke tabblad om terug te keren naar SynthPulse."
          ],
          "permissions": "Platformbeheerrechten in SynthPulse en geldige toegang tot de doelapp.",
          "limits": "Openen navigeert alleen naar het ingestelde adres. De app kan een eigen aanmelding vereisen. Niet ingesteld betekent dat er geen bruikbare link is; een ingestelde link garandeert niet dat de dienst bereikbaar is. Wijzigingen, uitvoeringen of verzendingen doe je bewust binnen de doelapp; deze gids voert ze niet uit.",
          "example": "Bijvoorbeeld: controleren welke modelroute voor een aanbieder is ingesteld."
        },
        "en": {
          "title": "Open OmniRoute",
          "purpose": "Manage model routing and AI provider connections.",
          "when": "Use this entry point for checking which model route is configured for a provider.",
          "steps": [
            "Choose Apps in navigation and find OmniRoute.",
            "Review the card’s status and description.",
            "Close the guide and choose Open when an address is configured. Complete the app’s own sign-in if required.",
            "Continue in the destination app and use the original tab to return to SynthPulse."
          ],
          "permissions": "Platform administration access in SynthPulse and valid access to the destination app.",
          "limits": "Open only navigates to the configured address. The app may require its own sign-in. Not configured means there is no usable link; a configured link does not guarantee the service is reachable. Make changes, run tasks or send documents deliberately inside the destination app; this guide does not perform them.",
          "example": "For example: checking which model route is configured for a provider."
        }
      }
    },
    {
      "id": "webui.apps.nango",
      "area": "apps",
      "status": "conditional",
      "conditions": [
        "Configured app directory and existing access"
      ],
      "anchors": [
        "?help_feature=webui.apps.nango",
        "#mainApps [data-app-id=\"nango\"]"
      ],
      "source_refs": [
        "api/app_catalog.py",
        "api/apps_launcher.py",
        "static/apps.js"
      ],
      "related": [
        "webui.apps.overview"
      ],
      "locales": {
        "nl": {
          "title": "Nango openen",
          "purpose": "Beheer integraties en verbindingen met externe diensten.",
          "when": "Gebruik deze ingang voor de inrichting van een externe koppeling bekijken.",
          "steps": [
            "Kies Apps in de navigatie en zoek Nango.",
            "Bekijk de status en de beschrijving van de kaart.",
            "Sluit de gids en kies Openen als een adres is ingesteld. Rond indien nodig de eigen aanmelding van de app af.",
            "Werk verder in de doelapp en gebruik het oorspronkelijke tabblad om terug te keren naar SynthPulse."
          ],
          "permissions": "Platformbeheerrechten in SynthPulse en geldige toegang tot de doelapp.",
          "limits": "Openen navigeert alleen naar het ingestelde adres. De app kan een eigen aanmelding vereisen. Niet ingesteld betekent dat er geen bruikbare link is; een ingestelde link garandeert niet dat de dienst bereikbaar is. Wijzigingen, uitvoeringen of verzendingen doe je bewust binnen de doelapp; deze gids voert ze niet uit.",
          "example": "Bijvoorbeeld: de inrichting van een externe koppeling bekijken."
        },
        "en": {
          "title": "Open Nango",
          "purpose": "Manage integrations and connections to external services.",
          "when": "Use this entry point for reviewing an external integration setup.",
          "steps": [
            "Choose Apps in navigation and find Nango.",
            "Review the card’s status and description.",
            "Close the guide and choose Open when an address is configured. Complete the app’s own sign-in if required.",
            "Continue in the destination app and use the original tab to return to SynthPulse."
          ],
          "permissions": "Platform administration access in SynthPulse and valid access to the destination app.",
          "limits": "Open only navigates to the configured address. The app may require its own sign-in. Not configured means there is no usable link; a configured link does not guarantee the service is reachable. Make changes, run tasks or send documents deliberately inside the destination app; this guide does not perform them.",
          "example": "For example: reviewing an external integration setup."
        }
      }
    },
    {
      "id": "webui.apps.docuseal",
      "area": "apps",
      "status": "conditional",
      "conditions": [
        "Configured app directory and existing access"
      ],
      "anchors": [
        "?help_feature=webui.apps.docuseal",
        "#mainApps [data-app-id=\"docuseal\"]"
      ],
      "source_refs": [
        "api/app_catalog.py",
        "api/apps_launcher.py",
        "static/apps.js"
      ],
      "related": [
        "webui.apps.overview"
      ],
      "locales": {
        "nl": {
          "title": "DocuSeal openen",
          "purpose": "Bereid documenten voor en volg digitale ondertekening.",
          "when": "Gebruik deze ingang voor een document voor ondertekening voorbereiden.",
          "steps": [
            "Kies Apps in de navigatie en zoek DocuSeal.",
            "Bekijk de status en de beschrijving van de kaart.",
            "Sluit de gids en kies Openen als een adres is ingesteld. Rond indien nodig de eigen aanmelding van de app af.",
            "Werk verder in de doelapp en gebruik het oorspronkelijke tabblad om terug te keren naar SynthPulse."
          ],
          "permissions": "Toegang tot Apps en de bijbehorende actieve module; platformbeheerders kunnen ingestelde appadressen ook zonder die module bekijken. De doelapp controleert zelf je toegang.",
          "limits": "Openen navigeert alleen naar het ingestelde adres. De app kan een eigen aanmelding vereisen. Niet ingesteld betekent dat er geen bruikbare link is; een ingestelde link garandeert niet dat de dienst bereikbaar is. Wijzigingen, uitvoeringen of verzendingen doe je bewust binnen de doelapp; deze gids voert ze niet uit.",
          "example": "Bijvoorbeeld: een document voor ondertekening voorbereiden."
        },
        "en": {
          "title": "Open DocuSeal",
          "purpose": "Prepare documents and follow digital signing.",
          "when": "Use this entry point for preparing a document for signature.",
          "steps": [
            "Choose Apps in navigation and find DocuSeal.",
            "Review the card’s status and description.",
            "Close the guide and choose Open when an address is configured. Complete the app’s own sign-in if required.",
            "Continue in the destination app and use the original tab to return to SynthPulse."
          ],
          "permissions": "Access to Apps and the associated active module; platform administrators can discover configured app addresses even without that module. The destination app checks its own access.",
          "limits": "Open only navigates to the configured address. The app may require its own sign-in. Not configured means there is no usable link; a configured link does not guarantee the service is reachable. Make changes, run tasks or send documents deliberately inside the destination app; this guide does not perform them.",
          "example": "For example: preparing a document for signature."
        }
      }
    },
    {
      "id": "webui.apps.cockpit",
      "area": "apps",
      "status": "conditional",
      "conditions": [
        "Configured app directory and existing access"
      ],
      "anchors": [
        "?help_feature=webui.apps.cockpit",
        "#mainApps [data-app-id=\"cockpit\"]"
      ],
      "source_refs": [
        "api/app_catalog.py",
        "api/apps_launcher.py",
        "static/apps.js"
      ],
      "related": [
        "webui.apps.overview"
      ],
      "locales": {
        "nl": {
          "title": "MSP Cockpit openen",
          "purpose": "Beheer installaties, organisaties en uitrol.",
          "when": "Gebruik deze ingang voor een klantinstallatie en de bijbehorende uitrol bekijken.",
          "steps": [
            "Kies Apps in de navigatie en zoek MSP Cockpit.",
            "Bekijk de status en de beschrijving van de kaart.",
            "Sluit de gids en kies Openen als een adres is ingesteld. Rond indien nodig de eigen aanmelding van de app af.",
            "Werk verder in de doelapp en gebruik het oorspronkelijke tabblad om terug te keren naar SynthPulse."
          ],
          "permissions": "Platformbeheerrechten in SynthPulse en geldige toegang tot de doelapp.",
          "limits": "Openen navigeert alleen naar het ingestelde adres. De app kan een eigen aanmelding vereisen. Niet ingesteld betekent dat er geen bruikbare link is; een ingestelde link garandeert niet dat de dienst bereikbaar is. Wijzigingen, uitvoeringen of verzendingen doe je bewust binnen de doelapp; deze gids voert ze niet uit.",
          "example": "Bijvoorbeeld: een klantinstallatie en de bijbehorende uitrol bekijken."
        },
        "en": {
          "title": "Open MSP Cockpit",
          "purpose": "Manage installations, organisations and deployments.",
          "when": "Use this entry point for reviewing a client installation and its deployment.",
          "steps": [
            "Choose Apps in navigation and find MSP Cockpit.",
            "Review the card’s status and description.",
            "Close the guide and choose Open when an address is configured. Complete the app’s own sign-in if required.",
            "Continue in the destination app and use the original tab to return to SynthPulse."
          ],
          "permissions": "Platform administration access in SynthPulse and valid access to the destination app.",
          "limits": "Open only navigates to the configured address. The app may require its own sign-in. Not configured means there is no usable link; a configured link does not guarantee the service is reachable. Make changes, run tasks or send documents deliberately inside the destination app; this guide does not perform them.",
          "example": "For example: reviewing a client installation and its deployment."
        }
      }
    },
    {
      "id": "webui.apps.openwebui",
      "area": "apps",
      "status": "conditional",
      "conditions": [
        "Configured app directory and existing access"
      ],
      "anchors": [
        "?help_feature=webui.apps.openwebui",
        "#mainApps [data-app-id=\"openwebui\"]"
      ],
      "source_refs": [
        "api/app_catalog.py",
        "api/apps_launcher.py",
        "static/apps.js"
      ],
      "related": [
        "webui.apps.overview"
      ],
      "locales": {
        "nl": {
          "title": "Open WebUI openen",
          "purpose": "Open de aanvullende AI-chatomgeving.",
          "when": "Gebruik deze ingang voor de aanvullende chatomgeving openen zodra een adres is ingesteld.",
          "steps": [
            "Kies Apps in de navigatie en zoek Open WebUI.",
            "Bekijk de status en de beschrijving van de kaart.",
            "Sluit de gids en kies Openen als een adres is ingesteld. Rond indien nodig de eigen aanmelding van de app af.",
            "Werk verder in de doelapp en gebruik het oorspronkelijke tabblad om terug te keren naar SynthPulse."
          ],
          "permissions": "Platformbeheerrechten in SynthPulse en geldige toegang tot de doelapp.",
          "limits": "Openen navigeert alleen naar het ingestelde adres. De app kan een eigen aanmelding vereisen. Niet ingesteld betekent dat er geen bruikbare link is; een ingestelde link garandeert niet dat de dienst bereikbaar is.",
          "example": "Bijvoorbeeld: de aanvullende chatomgeving openen zodra een adres is ingesteld."
        },
        "en": {
          "title": "Open Open WebUI",
          "purpose": "Open the additional AI chat environment.",
          "when": "Use this entry point for opening the additional chat environment once an address is configured.",
          "steps": [
            "Choose Apps in navigation and find Open WebUI.",
            "Review the card’s status and description.",
            "Close the guide and choose Open when an address is configured. Complete the app’s own sign-in if required.",
            "Continue in the destination app and use the original tab to return to SynthPulse."
          ],
          "permissions": "Platform administration access in SynthPulse and valid access to the destination app.",
          "limits": "Open only navigates to the configured address. The app may require its own sign-in. Not configured means there is no usable link; a configured link does not guarantee the service is reachable.",
          "example": "For example: opening the additional chat environment once an address is configured."
        }
      }
    },
    {
      "id": "webui.apps.language",
      "area": "apps",
      "status": "conditional",
      "conditions": [
        "Configured app directory and existing access"
      ],
      "anchors": [
        "?help_feature=webui.apps.language",
        "#appsLanguage"
      ],
      "source_refs": [
        "api/app_catalog.py",
        "api/apps_launcher.py",
        "static/apps.js"
      ],
      "related": [
        "webui.apps.overview"
      ],
      "locales": {
        "nl": {
          "title": "De taal van Apps wijzigen",
          "purpose": "Lees de appnamen, beschrijvingen en bediening in Nederlands of Engels.",
          "when": "Wanneer je het appoverzicht in de andere taal wilt gebruiken.",
          "steps": [
            "Open Apps.",
            "Kies Nederlands of English met Taal bovenaan.",
            "Kies Uitleg bij een app om de gids in dezelfde taal te starten."
          ],
          "permissions": "Dezelfde toegang als Apps. De taalkeuze verandert geen rechten.",
          "limits": "De keuze wordt in deze browser opgeslagen. Ze verandert niet de taalinstelling binnen de externe apps of van andere gebruikers.",
          "example": "Kies Nederlands om de appbeschrijvingen en interactieve uitleg in het Nederlands te lezen."
        },
        "en": {
          "title": "Change the Apps language",
          "purpose": "Read app names, descriptions and controls in Dutch or English.",
          "when": "When you want to use the app directory in the other language.",
          "steps": [
            "Open Apps.",
            "Choose Nederlands or English using Language at the top.",
            "Choose Guide on an app to start its guide in the same language."
          ],
          "permissions": "The same access as Apps. The language choice does not change permissions.",
          "limits": "The choice is stored in this browser. It does not change the language inside external applications or for other users.",
          "example": "Choose English to read app descriptions and interactive explanations in English."
        }
      }
    },
    {
      "id": "webui.apps.ragflow",
      "area": "apps",
      "status": "conditional",
      "conditions": [
        "Configured app directory and existing access"
      ],
      "anchors": [
        "?help_feature=webui.apps.ragflow",
        "#mainApps [data-app-id=\"ragflow\"]"
      ],
      "source_refs": [
        "api/app_catalog.py",
        "api/apps_launcher.py",
        "static/apps.js"
      ],
      "related": [
        "webui.apps.overview"
      ],
      "locales": {
        "nl": {
          "title": "RAGFlow gebruiken",
          "purpose": "Beheer kennisbanken, laat documenten verwerken en test zoekresultaten en antwoorden met bronnen.",
          "when": "Gebruik dit wanneer je het volgende wilt doen: Zoek het opzegbeleid in een kennisbank en controleer de aangehaalde passage.",
          "steps": [
            "Kies Apps onderaan de navigatie en zoek RAGFlow.",
            "Kies Open app en meld je aan bij RAGFlow.",
            "Open een bestaande kennisbank of maak een kennisbank voor je project. Voeg alleen documenten toe die je daarvoor mag gebruiken.",
            "Start de documentverwerking en controleer of die voltooid is. Test vervolgens een zoekvraag of een gekoppelde chat en controleer de bronverwijzingen."
          ],
          "permissions": "Platformbeheerrechten in SynthPulse en geldige toegang tot de doelapp.",
          "limits": "Documentverwerking en beschikbare modellen hangen af van de RAGFlow-configuratie. Een tegel koppelt geen bestanden of SynthPulse-gesprekken automatisch aan een kennisbank.",
          "example": "Zoek het opzegbeleid in een kennisbank en controleer de aangehaalde passage."
        },
        "en": {
          "title": "RAGFlow guide",
          "purpose": "Manage knowledge bases, process documents and test search results and answers with sources.",
          "when": "Use this when you want to do the following: Find the cancellation policy in a knowledge base and verify the cited passage.",
          "steps": [
            "Choose Apps at the bottom of navigation and find RAGFlow.",
            "Choose Open app and sign in to RAGFlow.",
            "Open an existing knowledge base or create one for your project. Add only documents you are allowed to use for that purpose.",
            "Start document processing and check that it completes. Then test a search query or a connected chat and review its source references."
          ],
          "permissions": "Platform administration access in SynthPulse and valid access to the destination app.",
          "limits": "Document processing and available models depend on the RAGFlow configuration. An app card does not automatically connect files or SynthPulse conversations to a knowledge base.",
          "example": "Find the cancellation policy in a knowledge base and verify the cited passage."
        }
      }
    },
    {
      "id": "webui.apps.langfuse",
      "area": "apps",
      "status": "conditional",
      "conditions": [
        "Configured app directory and existing access"
      ],
      "anchors": [
        "?help_feature=webui.apps.langfuse",
        "#mainApps [data-app-id=\"langfuse\"]"
      ],
      "source_refs": [
        "api/app_catalog.py",
        "api/apps_launcher.py",
        "static/apps.js"
      ],
      "related": [
        "webui.apps.overview"
      ],
      "locales": {
        "nl": {
          "title": "Langfuse gebruiken",
          "purpose": "Onderzoek AI-uitvoeringen aan de hand van traces, duur, tokengebruik, kosten en beschikbare evaluaties.",
          "when": "Gebruik dit wanneer je het volgende wilt doen: Zoek een trage AI-uitvoering en bekijk welke stap de meeste tijd kostte.",
          "steps": [
            "Kies Apps onderaan de navigatie en zoek Langfuse.",
            "Kies Open app, meld je aan en selecteer het juiste project.",
            "Open Traces en filter op periode, toepassing of de beschikbare sessiegegevens.",
            "Open een trace om de afzonderlijke stappen, duur en geregistreerde metadata te bekijken. Controleer gebruik en kosten waar die zijn aangeleverd."
          ],
          "permissions": "Platformbeheerrechten in SynthPulse en geldige toegang tot de doelapp.",
          "limits": "Alleen aangesloten toepassingen leveren gegevens. De huidige exporter kan uitsluitend metadata aanleveren; ontbrekende prompts of antwoorden betekenen niet dat de trace defect is. Kosten zijn afhankelijk van aangeleverde model- en gebruiksgegevens.",
          "example": "Zoek een trage AI-uitvoering en bekijk welke stap de meeste tijd kostte."
        },
        "en": {
          "title": "Langfuse guide",
          "purpose": "Investigate AI runs using traces, duration, token usage, costs and available evaluations.",
          "when": "Use this when you want to do the following: Find a slow AI run and inspect which step took the most time.",
          "steps": [
            "Choose Apps at the bottom of navigation and find Langfuse.",
            "Choose Open app, sign in and select the correct project.",
            "Open Traces and filter by time, application or available session information.",
            "Open a trace to inspect individual steps, duration and recorded metadata. Review usage and costs where these were supplied."
          ],
          "permissions": "Platform administration access in SynthPulse and valid access to the destination app.",
          "limits": "Only connected applications send data. The current exporter may provide metadata only; missing prompts or responses do not mean a trace is broken. Costs depend on the supplied model and usage information.",
          "example": "Find a slow AI run and inspect which step took the most time."
        }
      }
    },
    {
      "id": "webui.apps.hermesoffice",
      "area": "apps",
      "status": "conditional",
      "conditions": [
        "Configured app directory and existing access"
      ],
      "anchors": [
        "?help_feature=webui.apps.hermesoffice",
        "#mainApps [data-app-id=\"hermesoffice\"]"
      ],
      "source_refs": [
        "api/app_catalog.py",
        "api/apps_launcher.py",
        "static/apps.js"
      ],
      "related": [
        "webui.apps.overview"
      ],
      "locales": {
        "nl": {
          "title": "HermesOffice gebruiken",
          "purpose": "Open de desktopkantoorsuite voor Word-documenten, spreadsheets, presentaties, pdf en Markdown.",
          "when": "Gebruik dit wanneer je het volgende wilt doen: Open een bestaand docx-bestand in HermesOffice en sla de bewerkte versie op je computer op.",
          "steps": [
            "Kies Apps onderaan de navigatie en zoek HermesOffice.",
            "Kies Download desktopapp om de officiële releasepagina te openen.",
            "Download een uitgave die bij je besturingssysteem past en installeer die volgens de projectinstructies. Als de app al is geïnstalleerd, open je haar via je toepassingenmenu.",
            "Open of maak een document in HermesOffice. Stel AI-toegang in binnen de desktopapp als je AI-bewerking wilt gebruiken en sla je resultaat bewust op."
          ],
          "permissions": "Toegang tot de Apps-tegel, installatie op je eigen computer en eventuele AI-providerrechten.",
          "limits": "Dit is een desktopapp, geen ingebouwde browsereditor. Beschikbare installatiepakketten verschillen per platform. De tegel opent alleen de downloadpagina en synchroniseert geen documenten of AI-instellingen.",
          "example": "Open een bestaand docx-bestand in HermesOffice en sla de bewerkte versie op je computer op."
        },
        "en": {
          "title": "HermesOffice guide",
          "purpose": "Open the desktop office suite for Word documents, spreadsheets, presentations, PDF and Markdown.",
          "when": "Use this when you want to do the following: Open an existing docx file in HermesOffice and save the edited version on your computer.",
          "steps": [
            "Choose Apps at the bottom of navigation and find HermesOffice.",
            "Choose Download desktop app to open the official release page.",
            "Download a release suitable for your operating system and install it following the project instructions. If it is already installed, open it from your applications menu.",
            "Open or create a document in HermesOffice. Configure AI access inside the desktop app if you want AI editing and save your result deliberately."
          ],
          "permissions": "Access to the app card, installation on your own computer and any required AI provider permissions.",
          "limits": "This is a desktop application, not an embedded browser editor. Available installation packages differ by platform. The card only opens the download page and does not synchronise documents or AI settings.",
          "example": "Open an existing docx file in HermesOffice and save the edited version on your computer."
        }
      }
    }
  ]
};
