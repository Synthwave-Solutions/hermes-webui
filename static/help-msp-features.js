/* Generated from the MSP cockpit catalogue. */
window.SynthPulseMspFeatureCatalog = {
  "schema_version": 1,
  "product": "msp",
  "features": [
    {
      "id": "msp.overview",
      "area": "access",
      "status": "available",
      "conditions": [],
      "anchors": [
        "/cockpit/help?feature=msp.overview"
      ],
      "source_refs": [
        "apps/cockpit/README.md"
      ],
      "related": [
        "msp.roles",
        "msp.clients",
        "msp.operations"
      ],
      "locales": {
        "en": {
          "title": "Using the MSP cockpit",
          "purpose": "Manage client preparation, service delivery and operational evidence in one staff workspace.",
          "when": "Before using the cockpit for the first time or choosing where to perform a task.",
          "steps": [
            "Sign in with an assigned role",
            "Choose Clients, Jobs, Service desk or Operations",
            "Use the guide’s search and language switch for a specific control"
          ],
          "permissions": "Any signed-in cockpit role; sign-in itself requires configured access.",
          "limits": "The cockpit is a staff control application. Client work in the WebUI is separate.",
          "example": "Prepare a client, check readiness, then register and monitor the installation."
        },
        "nl": {
          "title": "De MSP-cockpit gebruiken",
          "purpose": "Beheer klantvoorbereiding, dienstverlening en operationele informatie in één werkomgeving voor medewerkers.",
          "when": "Voordat je de cockpit voor het eerst gebruikt of bepaalt waar je een handeling uitvoert.",
          "steps": [
            "Log in met een toegewezen rol",
            "Kies Klanten, Taken, Servicedesk of Beheer",
            "Zoek een specifieke functie in de handleiding en kies je taal"
          ],
          "permissions": "Iedere ingelogde cockpitrol; inloggen vereist ingerichte toegang.",
          "limits": "Dit is een beheerapp voor medewerkers. Het werk van klanten in de WebUI staat hiervan los.",
          "example": "Bereid een klant voor, controleer gereedheid en registreer en bewaak daarna de installatie."
        }
      }
    },
    {
      "id": "msp.login",
      "area": "access",
      "status": "conditional",
      "conditions": [
        "deployment_prerequisites"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.login"
      ],
      "source_refs": [
        "apps/cockpit/README.md"
      ],
      "related": [
        "msp.overview"
      ],
      "locales": {
        "en": {
          "title": "Sign in and sign out",
          "purpose": "Authenticate with the methods enabled by the deployment operator.",
          "when": "At the start or end of a staff session, or when your session has expired.",
          "steps": [
            "Open the private cockpit address from a device with permitted network access.",
            "Choose an offered sign-in method. For Google, use your assigned staff account; an emergency password is only for authorised administrators.",
            "Check your name and role at the top after signing in. If access is refused, have account assignment and network identity checked.",
            "Choose Sign out to end the cockpit session. This does not automatically sign you out of your external identity provider."
          ],
          "permissions": "Any signed-in cockpit role; sign-in itself requires configured access.",
          "limits": "A network-connected machine can lack user identity. A valid account still needs an explicit cockpit role. Public access is not the staff login path.",
          "example": "A tagged service device receives no staff session until a recognised staff identity signs in."
        },
        "nl": {
          "title": "Inloggen en uitloggen",
          "purpose": "Log in met de methoden die de beheerder voor deze installatie heeft aangezet.",
          "when": "Aan het begin of einde van een beheersessie, of wanneer je sessie is verlopen.",
          "steps": [
            "Open het privéadres van de cockpit op een apparaat met toegestane netwerktoegang.",
            "Kies een aangeboden aanmeldmethode. Gebruik bij Google het toegewezen medewerkersaccount; een noodwachtwoord is alleen voor daarvoor bevoegde beheerders.",
            "Controleer na inloggen je naam en rol bovenaan. Als toegang wordt geweigerd, laat accounttoewijzing en netwerkidentiteit controleren.",
            "Kies Uitloggen om de cockpitsessie te beëindigen. Dit meldt je niet automatisch af bij je externe identiteitsprovider."
          ],
          "permissions": "Iedere ingelogde cockpitrol; inloggen vereist ingerichte toegang.",
          "limits": "Een verbonden machine kan zonder gebruikersidentiteit werken. Een geldig account heeft daarnaast een expliciete cockpitrol nodig. Publieke toegang is niet bedoeld voor medewerkerslogin.",
          "example": "Een getagd apparaat krijgt pas een medewerkerssessie als een herkende medewerker inlogt."
        }
      }
    },
    {
      "id": "msp.roles",
      "area": "access",
      "status": "available",
      "conditions": [],
      "anchors": [
        "/cockpit/help?feature=msp.roles"
      ],
      "source_refs": [
        "apps/cockpit/README.md"
      ],
      "related": [
        "msp.overview"
      ],
      "locales": {
        "en": {
          "title": "Cockpit roles and ownership",
          "purpose": "Distinguish staff permissions from client WebUI roles and protect partner visibility.",
          "when": "When assigning staff access or investigating why an action is unavailable.",
          "steps": [
            "Read the role beside your name",
            "Admins manage sensitive organisation and contract changes",
            "Operators handle deployment and service work",
            "Partners inspect only their assigned clients"
          ],
          "permissions": "Any signed-in cockpit role; sign-in itself requires configured access.",
          "limits": "Partners are read-only: seeing a wizard button does not grant write access. Staff roles do not automatically grant every client permission.",
          "example": "An operator logs support time; a partner reads an owned client’s job log."
        },
        "nl": {
          "title": "Cockpitrollen en eigenaarschap",
          "purpose": "Onderscheid beheerrechten van rollen in de klant-WebUI en beperk wat partners kunnen zien.",
          "when": "Bij het toewijzen van beheerrechten of onderzoeken waarom een actie ontbreekt.",
          "steps": [
            "Lees de rol naast je naam",
            "Admins beheren gevoelige organisatie- en contractwijzigingen",
            "Operators verzorgen installatie en servicewerk",
            "Partners bekijken alleen hun toegewezen klanten"
          ],
          "permissions": "Iedere ingelogde cockpitrol; inloggen vereist ingerichte toegang.",
          "limits": "Partners hebben alleen leesrechten: een zichtbare wizardknop geeft geen schrijfrecht. Medewerkersrollen geven niet automatisch iedere klantbevoegdheid.",
          "example": "Een operator registreert supporttijd; een partner leest het taaklog van een toegewezen klant."
        }
      }
    },
    {
      "id": "msp.clients",
      "area": "clients",
      "status": "available",
      "conditions": [],
      "anchors": [
        "/cockpit/help?feature=msp.clients"
      ],
      "source_refs": [
        "apps/cockpit/README.md"
      ],
      "related": [
        "msp.roles",
        "msp.secrets"
      ],
      "locales": {
        "en": {
          "title": "Client list and status",
          "purpose": "Find saved client configurations and their latest deployment job status.",
          "when": "When finding a client draft or checking its latest deployment result.",
          "steps": [
            "Open Clients",
            "Find the client name and target",
            "Open the card to inspect its wizard",
            "Check the latest job in Jobs when a status needs explanation"
          ],
          "permissions": "Operators and admins. Partners can read only their own client and job records; staff service and operations data require an operator role.",
          "limits": "A saved client or successful job is not proof that every service is healthy. A compliant badge reflects configuration, not certification.",
          "example": "A successful render can appear while no cloud installation has been applied."
        },
        "nl": {
          "title": "Klantenlijst en status",
          "purpose": "Vind opgeslagen klantconfiguraties en de status van hun laatste installatietaak.",
          "when": "Wanneer je een klantconcept zoekt of het laatste uitrolresultaat controleert.",
          "steps": [
            "Open Klanten",
            "Zoek de klantnaam en het installatiedoel",
            "Open de kaart om de wizard te bekijken",
            "Bekijk de laatste taak onder Taken als een status uitleg nodig heeft"
          ],
          "permissions": "Operators en admins. Partners lezen alleen eigen klant- en taakgegevens; servicedesk en beheer vereisen een operatorrol.",
          "limits": "Een opgeslagen klant of geslaagde taak bewijst niet dat elke dienst gezond is. Het compliant-label weerspiegelt configuratie en is geen certificering.",
          "example": "Een geslaagde configuratiegeneratie kan zichtbaar zijn terwijl er nog niets in de cloud is geïnstalleerd."
        }
      }
    },
    {
      "id": "msp.client-create",
      "area": "clients",
      "status": "available",
      "conditions": [],
      "anchors": [
        "/cockpit/help?feature=msp.client-create"
      ],
      "source_refs": [
        "apps/cockpit/README.md"
      ],
      "related": [
        "msp.roles",
        "msp.secrets"
      ],
      "locales": {
        "en": {
          "title": "Create a client draft",
          "purpose": "Start a new named client configuration before any deployment is launched.",
          "when": "At the start of onboarding a new client installation.",
          "steps": [
            "Choose New client",
            "Enter a valid fixed slug and display name",
            "Complete the wizard",
            "Use Next or Save draft and check the save confirmation"
          ],
          "permissions": "Operators and admins. Partners can read only their own client and job records; staff service and operations data require an operator role.",
          "limits": "Saving a draft writes configuration only. It does not enroll a device, create a contract or buy infrastructure.",
          "example": "Create acme-demo as a draft before entering any real credentials."
        },
        "nl": {
          "title": "Klantconcept maken",
          "purpose": "Begin een nieuwe klantconfiguratie voordat er een installatie wordt gestart.",
          "when": "Aan het begin van het inrichten van een nieuwe klantinstallatie.",
          "steps": [
            "Kies Nieuwe klant",
            "Vul een geldige vaste klantcode en weergavenaam in",
            "Doorloop de wizard",
            "Kies Volgende of Concept opslaan en controleer de bevestiging"
          ],
          "permissions": "Operators en admins. Partners lezen alleen eigen klant- en taakgegevens; servicedesk en beheer vereisen een operatorrol.",
          "limits": "Een concept opslaan schrijft alleen configuratie. Het registreert geen apparaat, maakt geen contract en koopt geen infrastructuur.",
          "example": "Maak acme-demo als concept voordat je echte sleutels invult."
        }
      }
    },
    {
      "id": "msp.client-edit",
      "area": "clients",
      "status": "available",
      "conditions": [],
      "anchors": [
        "/cockpit/help?feature=msp.client-edit"
      ],
      "source_refs": [
        "apps/cockpit/README.md"
      ],
      "related": [
        "msp.roles",
        "msp.secrets"
      ],
      "locales": {
        "en": {
          "title": "Edit and save an existing client",
          "purpose": "Change a saved configuration while retaining the fixed client identity.",
          "when": "When an existing client’s requested configuration needs a reviewed change.",
          "steps": [
            "Open the client card",
            "Change the appropriate step",
            "Move to another step to save or use Save draft",
            "Read the save result",
            "Render and verify again before a later deployment"
          ],
          "permissions": "Operators and admins. Partners can read only their own client and job records; staff service and operations data require an operator role.",
          "limits": "Leaving the page before saving can lose edits. A saved change is not automatically applied to an already running client.",
          "example": "Change a region in the draft, then review the new plan instead of assuming a live move."
        },
        "nl": {
          "title": "Bestaande klant wijzigen en opslaan",
          "purpose": "Wijzig een opgeslagen configuratie met behoud van de vaste klantidentiteit.",
          "when": "Wanneer de gewenste configuratie van een bestaande klant een beoordeelde wijziging nodig heeft.",
          "steps": [
            "Open de klantkaart",
            "Wijzig de juiste stap",
            "Ga naar een andere stap om op te slaan of kies Concept opslaan",
            "Lees het opslagresultaat",
            "Genereer en valideer opnieuw voor een volgende installatie"
          ],
          "permissions": "Operators en admins. Partners lezen alleen eigen klant- en taakgegevens; servicedesk en beheer vereisen een operatorrol.",
          "limits": "De pagina verlaten voordat je opslaat kan wijzigingen verliezen. Een opgeslagen wijziging wordt niet automatisch uitgevoerd bij een draaiende klant.",
          "example": "Wijzig een regio in het concept en beoordeel daarna het nieuwe plan."
        }
      }
    },
    {
      "id": "msp.jobs",
      "area": "jobs",
      "status": "available",
      "conditions": [],
      "anchors": [
        "/cockpit/help?feature=msp.jobs"
      ],
      "source_refs": [
        "apps/cockpit/README.md"
      ],
      "related": [
        "msp.roles",
        "msp.secrets"
      ],
      "locales": {
        "en": {
          "title": "Deployment jobs and logs",
          "purpose": "Follow render, verify, doctor and deployment work and inspect failures.",
          "when": "After starting a check, render, plan or deployment, especially if it fails.",
          "steps": [
            "Open Jobs",
            "Read client, kind, status, start, finish and exit result",
            "Select a row to open the log drawer",
            "Follow live output for running work or review the completed tail",
            "Close the drawer when finished"
          ],
          "permissions": "Operators and admins. Partners can read only their own client and job records; staff service and operations data require an operator role.",
          "limits": "The list refreshes periodically. Logs are evidence, not permission to retry destructive work. Check the client and cause before retrying.",
          "example": "A missing credential explains a failed doctor job without starting cloud provisioning."
        },
        "nl": {
          "title": "Installatietaken en logs",
          "purpose": "Volg configuratiegeneratie, validatie, controles en installatiewerk en onderzoek fouten.",
          "when": "Na het starten van een controle, generatie, plan of uitrol, vooral bij een fout.",
          "steps": [
            "Open Taken",
            "Lees klant, soort, status, start, einde en afsluitcode",
            "Selecteer een regel om het logvenster te openen",
            "Volg live-uitvoer of lees het einde van een afgerond log",
            "Sluit het venster als je klaar bent"
          ],
          "permissions": "Operators en admins. Partners lezen alleen eigen klant- en taakgegevens; servicedesk en beheer vereisen een operatorrol.",
          "limits": "De lijst wordt periodiek vernieuwd. Logs geven informatie, geen toestemming om destructief werk te herhalen. Controleer klant en oorzaak voor een nieuwe poging.",
          "example": "Een ontbrekende sleutel verklaart een mislukte controle zonder cloudinstallatie te starten."
        }
      }
    },
    {
      "id": "msp.installer",
      "area": "clients",
      "status": "conditional",
      "conditions": [
        "deployment_prerequisites"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.installer"
      ],
      "source_refs": [
        "apps/cockpit/README.md"
      ],
      "related": [
        "msp.roles",
        "msp.secrets"
      ],
      "locales": {
        "en": {
          "title": "Use a one-time installer",
          "purpose": "Hand over the selected client and approved source snapshot to a compatible device.",
          "when": "When handing a reviewed device installation bundle to its authorised operator.",
          "steps": [
            "Select the device or full-platform target",
            "Complete readiness checks",
            "Generate the installer in Review",
            "Copy the command to the intended device over the approved private access path",
            "Verify services and sign-in after installation"
          ],
          "permissions": "Operators and admins. Partners can read only their own client and job records; staff service and operations data require an operator role.",
          "limits": "The link is secret, single-use and expires after one hour. Existing install directories are refused. Full platform requires Docker and supported images; native installs still need explicit service activation.",
          "example": "Use a fresh test directory on the intended Pi and never paste the installer URL into a ticket."
        },
        "nl": {
          "title": "Eenmalige installer gebruiken",
          "purpose": "Draag de gekozen klant en goedgekeurde bronversie over aan een geschikt apparaat.",
          "when": "Bij het overdragen van een beoordeelde installatiebundel aan de bevoegde apparaatbeheerder.",
          "steps": [
            "Kies het apparaat- of volledige-platformdoel",
            "Rond de gereedheidscontroles af",
            "Genereer de installer bij Beoordelen",
            "Kopieer het commando via het goedgekeurde privépad naar het bedoelde apparaat",
            "Controleer diensten en login na installatie"
          ],
          "permissions": "Operators en admins. Partners lezen alleen eigen klant- en taakgegevens; servicedesk en beheer vereisen een operatorrol.",
          "limits": "De link is geheim, eenmalig en één uur geldig. Bestaande installatiemappen worden geweigerd. Het volledige platform vereist Docker en ondersteunde images; native installaties vragen nog expliciete dienstactivering.",
          "example": "Gebruik een nieuwe testmap op de bedoelde Pi en plak de installer-URL nooit in een ticket."
        }
      }
    },
    {
      "id": "msp.organisation",
      "area": "service",
      "status": "available",
      "conditions": [],
      "anchors": [
        "/cockpit/help?feature=msp.organisation"
      ],
      "source_refs": [
        "apps/cockpit/README.md"
      ],
      "related": [
        "msp.roles",
        "msp.secrets"
      ],
      "locales": {
        "en": {
          "title": "Organisations",
          "purpose": "Group service tickets, support balances, installations and contracts under the correct customer.",
          "when": "Before linking service work, contracts or installations to a client organisation.",
          "steps": [
            "Open Service desk",
            "Select the organisation before changing records",
            "Admins may open Add organisation",
            "Enter its name and unique slug and save"
          ],
          "permissions": "Admin for sensitive changes; operators may inspect service records where allowed.",
          "limits": "An organisation is not the same as a client configuration folder. Creating one does not create a service contract or installation.",
          "example": "One organisation can own an HQ installation and later a separate test installation."
        },
        "nl": {
          "title": "Organisaties",
          "purpose": "Groepeer servicetickets, supportsaldi, installaties en contracten onder de juiste klant.",
          "when": "Voordat je servicewerk, contracten of installaties aan een klantorganisatie koppelt.",
          "steps": [
            "Open Servicedesk",
            "Selecteer de organisatie voordat je gegevens wijzigt",
            "Admins kunnen Organisatie toevoegen openen",
            "Vul naam en unieke code in en sla op"
          ],
          "permissions": "Admin voor gevoelige wijzigingen; operators bekijken servicedossiers waar toegestaan.",
          "limits": "Een organisatie is iets anders dan een klantconfiguratiemap. Aanmaken maakt geen servicecontract of installatie.",
          "example": "Eén organisatie kan een hoofdinstallatie en later een aparte testinstallatie bezitten."
        }
      }
    },
    {
      "id": "msp.ticket-create",
      "area": "support",
      "status": "available",
      "conditions": [],
      "anchors": [
        "/cockpit/help?feature=msp.ticket-create"
      ],
      "source_refs": [
        "apps/cockpit/README.md"
      ],
      "related": [
        "msp.roles",
        "msp.secrets"
      ],
      "locales": {
        "en": {
          "title": "Create a support ticket",
          "purpose": "Capture a question, fault, access issue, change or billing question for one organisation.",
          "when": "When a client question, fault or change needs a traceable support record.",
          "steps": [
            "Select the organisation",
            "Open New ticket",
            "Enter a short title, need and useful details",
            "Create the ticket and open its numbered record"
          ],
          "permissions": "Operators and admins. Partners can read only their own client and job records; staff service and operations data require an operator role.",
          "limits": "Do not include passwords, tokens or installer links. Creating a ticket does not send a message or approve chargeable work by itself.",
          "example": "Title: Team cannot open the knowledge page. Include the time and visible error, not an API key."
        },
        "nl": {
          "title": "Supportticket maken",
          "purpose": "Leg een vraag, storing, toegangsprobleem, wijziging of facturatievraag vast voor één organisatie.",
          "when": "Wanneer een klantvraag, storing of wijziging een traceerbaar supportdossier nodig heeft.",
          "steps": [
            "Selecteer de organisatie",
            "Open Nieuw ticket",
            "Vul een korte titel, behoefte en bruikbare details in",
            "Maak het ticket en open het genummerde dossier"
          ],
          "permissions": "Operators en admins. Partners lezen alleen eigen klant- en taakgegevens; servicedesk en beheer vereisen een operatorrol.",
          "limits": "Neem geen wachtwoorden, tokens of installerlinks op. Een ticket maken verstuurt op zichzelf geen bericht en keurt geen betaald werk goed.",
          "example": "Titel: Team kan de kennispagina niet openen. Noteer tijdstip en zichtbare fout, geen API-sleutel."
        }
      }
    },
    {
      "id": "msp.ticket-queue",
      "area": "support",
      "status": "available",
      "conditions": [],
      "anchors": [
        "/cockpit/help?feature=msp.ticket-queue"
      ],
      "source_refs": [
        "apps/cockpit/README.md"
      ],
      "related": [
        "msp.roles",
        "msp.secrets"
      ],
      "locales": {
        "en": {
          "title": "Ticket list and detail",
          "purpose": "Review a ticket’s state, priority, coverage, activity and time entries together.",
          "when": "When triaging new work or continuing an existing support request.",
          "steps": [
            "Choose the organisation",
            "Read the ticket table",
            "Open a numbered title",
            "Inspect its description, activity and recorded time"
          ],
          "permissions": "Operators and admins. Partners can read only their own client and job records; staff service and operations data require an operator role.",
          "limits": "Priority and coverage are service classifications. They do not by themselves confirm contractual entitlement or response guarantees.",
          "example": "A billing question and an incident can belong to the same organisation but follow different handling."
        },
        "nl": {
          "title": "Ticketlijst en detail",
          "purpose": "Beoordeel status, prioriteit, dekking, activiteit en tijdregistraties van een ticket samen.",
          "when": "Bij het beoordelen van nieuw werk of vervolgen van een bestaande supportvraag.",
          "steps": [
            "Kies de organisatie",
            "Lees de ticketlijst",
            "Open een genummerde titel",
            "Bekijk beschrijving, activiteit en geregistreerde tijd"
          ],
          "permissions": "Operators en admins. Partners lezen alleen eigen klant- en taakgegevens; servicedesk en beheer vereisen een operatorrol.",
          "limits": "Prioriteit en dekking zijn serviceclassificaties. Ze bevestigen niet op zichzelf contractrechten of reactietijdgaranties.",
          "example": "Een facturatievraag en incident kunnen bij dezelfde organisatie horen maar anders worden behandeld."
        }
      }
    },
    {
      "id": "msp.ticket-status",
      "area": "support",
      "status": "available",
      "conditions": [],
      "anchors": [
        "/cockpit/help?feature=msp.ticket-status"
      ],
      "source_refs": [
        "apps/cockpit/README.md"
      ],
      "related": [
        "msp.roles",
        "msp.secrets"
      ],
      "locales": {
        "en": {
          "title": "Change ticket status",
          "purpose": "Record the next service step with an explicit reason.",
          "when": "When responsibility, progress or the next required action changes.",
          "steps": [
            "Open a ticket",
            "Choose New, Triage, In progress, Waiting client, Needs quote, Resolved or Closed",
            "Enter the reason",
            "Save the status and inspect activity"
          ],
          "permissions": "Operators and admins. Partners can read only their own client and job records; staff service and operations data require an operator role.",
          "limits": "The service validates transitions. Waiting for a client or quote is different from resolving the underlying problem.",
          "example": "Set Waiting client because a reproduction time is needed."
        },
        "nl": {
          "title": "Ticketstatus wijzigen",
          "purpose": "Leg de volgende servicestap vast met een duidelijke reden.",
          "when": "Wanneer verantwoordelijkheid, voortgang of de eerstvolgende actie verandert.",
          "steps": [
            "Open een ticket",
            "Kies Nieuw, Beoordeling, In behandeling, Wacht op klant, Offerte nodig, Opgelost of Gesloten",
            "Vul de reden in",
            "Sla de status op en controleer de activiteit"
          ],
          "permissions": "Operators en admins. Partners lezen alleen eigen klant- en taakgegevens; servicedesk en beheer vereisen een operatorrol.",
          "limits": "De dienst valideert statusovergangen. Wachten op een klant of offerte is iets anders dan het probleem oplossen.",
          "example": "Kies Wacht op klant omdat een tijdstip voor reproductie nodig is."
        }
      }
    },
    {
      "id": "msp.ticket-notes",
      "area": "support",
      "status": "available",
      "conditions": [],
      "anchors": [
        "/cockpit/help?feature=msp.ticket-notes"
      ],
      "source_refs": [
        "apps/cockpit/README.md"
      ],
      "related": [
        "msp.roles",
        "msp.secrets"
      ],
      "locales": {
        "en": {
          "title": "Internal ticket notes",
          "purpose": "Keep staff observations in the service record without publishing them as client messages.",
          "when": "When recording an internal finding or handover for another staff member.",
          "steps": [
            "Open the ticket",
            "Write a factual internal note",
            "Choose Add internal note",
            "Check the activity record"
          ],
          "permissions": "Operators and admins. Partners can read only their own client and job records; staff service and operations data require an operator role.",
          "limits": "This form creates an internal note. It is not a client reply or notification channel.",
          "example": "Record that the health check recovered after the reviewed restart."
        },
        "nl": {
          "title": "Interne ticketnotities",
          "purpose": "Bewaar interne bevindingen in het servicedossier zonder ze als klantbericht te publiceren.",
          "when": "Bij het vastleggen van een interne bevinding of overdracht aan een collega.",
          "steps": [
            "Open het ticket",
            "Schrijf een feitelijke interne notitie",
            "Kies Interne notitie toevoegen",
            "Controleer de activiteit"
          ],
          "permissions": "Operators en admins. Partners lezen alleen eigen klant- en taakgegevens; servicedesk en beheer vereisen een operatorrol.",
          "limits": "Dit formulier maakt een interne notitie. Het is geen klantantwoord of notificatiekanaal.",
          "example": "Noteer dat de gezondheidscontrole herstelde na de beoordeelde herstart."
        }
      }
    },
    {
      "id": "msp.time-entry",
      "area": "support",
      "status": "available",
      "conditions": [],
      "anchors": [
        "/cockpit/help?feature=msp.time-entry"
      ],
      "source_refs": [
        "apps/cockpit/README.md"
      ],
      "related": [
        "msp.roles",
        "msp.secrets"
      ],
      "locales": {
        "en": {
          "title": "Log support time",
          "purpose": "Record actual work and let service rules determine the associated ledger effect.",
          "when": "After completing support work that must be recorded against a ticket.",
          "steps": [
            "Open the ticket",
            "Choose the work date",
            "Enter 1 to 1440 actual minutes and a short work note",
            "Choose Log time",
            "Review the time list and support balance"
          ],
          "permissions": "Operators and admins. Partners can read only their own client and job records; staff service and operations data require an operator role.",
          "limits": "Future work dates are refused. Billable treatment can differ from raw minutes and depends on coverage, contract and applicable rules.",
          "example": "Record 20 minutes of diagnosis with a note describing the checks performed."
        },
        "nl": {
          "title": "Supporttijd registreren",
          "purpose": "Registreer werkelijk uitgevoerd werk; serviceregels bepalen het effect op de urenadministratie.",
          "when": "Na supportwerk dat op een ticket moet worden verantwoord.",
          "steps": [
            "Open het ticket",
            "Kies de werkdatum",
            "Vul 1 tot 1440 werkelijke minuten en een korte notitie in",
            "Kies Tijd registreren",
            "Controleer tijdlijst en supportsaldo"
          ],
          "permissions": "Operators en admins. Partners lezen alleen eigen klant- en taakgegevens; servicedesk en beheer vereisen een operatorrol.",
          "limits": "Toekomstige werkdatums worden geweigerd. Verrekening kan afwijken van ruwe minuten en hangt af van dekking, contract en geldende regels.",
          "example": "Registreer 20 minuten diagnose met een notitie over de uitgevoerde controles."
        }
      }
    },
    {
      "id": "msp.ledger",
      "area": "support",
      "status": "available",
      "conditions": [],
      "anchors": [
        "/cockpit/help?feature=msp.ledger"
      ],
      "source_refs": [
        "apps/cockpit/README.md"
      ],
      "related": [
        "msp.roles",
        "msp.secrets"
      ],
      "locales": {
        "en": {
          "title": "Support balance and statement",
          "purpose": "See available, used and included minutes and the ledger entries that explain them.",
          "when": "When checking how support time changed an organisation’s balance.",
          "steps": [
            "Select the organisation",
            "Read the displayed period and balances",
            "Expand Hour statement",
            "Compare reasons, buckets and minute changes with ticket work"
          ],
          "permissions": "Operators and admins. Partners can read only their own client and job records; staff service and operations data require an operator role.",
          "limits": "This is a support ledger, not a paid invoice or bank balance. Values depend on the actual contract and posted entries.",
          "example": "A monthly allowance increases the balance; covered work can consume minutes under the service rules."
        },
        "nl": {
          "title": "Supportsaldo en urenoverzicht",
          "purpose": "Bekijk beschikbare, gebruikte en inbegrepen minuten en de bijbehorende boekingen.",
          "when": "Wanneer je controleert hoe supportwerk het saldo van een organisatie heeft gewijzigd.",
          "steps": [
            "Selecteer de organisatie",
            "Lees periode en saldi",
            "Open het Urenoverzicht",
            "Vergelijk redenen, categorieën en minutenwijzigingen met ticketwerk"
          ],
          "permissions": "Operators en admins. Partners lezen alleen eigen klant- en taakgegevens; servicedesk en beheer vereisen een operatorrol.",
          "limits": "Dit is een supportadministratie, geen betaalde factuur of banksaldo. Waarden hangen af van het echte contract en de geboekte posten.",
          "example": "Een maandtoekenning verhoogt het saldo; gedekt werk kan volgens de serviceregels minuten verbruiken."
        }
      }
    },
    {
      "id": "msp.allowance",
      "area": "support",
      "status": "available",
      "conditions": [],
      "anchors": [
        "/cockpit/help?feature=msp.allowance"
      ],
      "source_refs": [
        "apps/cockpit/README.md"
      ],
      "related": [
        "msp.roles",
        "msp.secrets"
      ],
      "locales": {
        "en": {
          "title": "Grant monthly allowance",
          "purpose": "Post the organisation’s applicable monthly support allowance for the selected period.",
          "when": "When checking a month’s support allowance or processing its grant once.",
          "steps": [
            "Check the organisation and displayed month",
            "Check the applicable service contract",
            "Choose Grant this month’s allowance",
            "Review the resulting statement"
          ],
          "permissions": "Operators and admins. Partners can read only their own client and job records; staff service and operations data require an operator role.",
          "limits": "The operation follows contract eligibility and duplicate-grant rules. It does not create a contract or arbitrary free minutes.",
          "example": "Review an eligible month once instead of creating duplicate manual credits."
        },
        "nl": {
          "title": "Maandtegoed toekennen",
          "purpose": "Boek het toepasselijke maandelijkse supporttegoed voor de organisatie en periode.",
          "when": "Bij het controleren van het maandtegoed of het eenmalig toekennen ervan.",
          "steps": [
            "Controleer organisatie en getoonde maand",
            "Controleer het toepasselijke servicecontract",
            "Kies Maandtegoed toekennen",
            "Controleer het bijgewerkte overzicht"
          ],
          "permissions": "Operators en admins. Partners lezen alleen eigen klant- en taakgegevens; servicedesk en beheer vereisen een operatorrol.",
          "limits": "De actie volgt contractvoorwaarden en regels tegen dubbele toekenning. Ze maakt geen contract of willekeurige gratis minuten.",
          "example": "Beoordeel een geldige maand eenmaal in plaats van dubbele handmatige tegoeden te maken."
        }
      }
    },
    {
      "id": "msp.business-hours",
      "area": "support",
      "status": "available",
      "conditions": [],
      "anchors": [
        "/cockpit/help?feature=msp.business-hours"
      ],
      "source_refs": [
        "apps/cockpit/README.md"
      ],
      "related": [
        "msp.roles",
        "msp.secrets"
      ],
      "locales": {
        "en": {
          "title": "Business hours and coverage",
          "purpose": "Understand why service timing and charge treatment depend on contract and calendar rules.",
          "when": "When interpreting response deadlines or work outside the configured service calendar.",
          "steps": [
            "Inspect the ticket’s coverage and current contract",
            "Use the configured business calendar for response interpretation",
            "Ask service administration when coverage or scope is unclear"
          ],
          "permissions": "Operators and admins. Partners can read only their own client and job records; staff service and operations data require an operator role.",
          "limits": "Automated monitoring outside business hours is not a promise of round-the-clock staffed support. Draft plans establish no agreed SLA.",
          "example": "A weekend observation may be monitored automatically and reviewed in the agreed service window."
        },
        "nl": {
          "title": "Kantooruren en dekking",
          "purpose": "Begrijp waarom servicetijd en verrekening afhangen van contract en kalenderregels.",
          "when": "Bij het beoordelen van reactietermijnen of werk buiten de ingerichte servicekalender.",
          "steps": [
            "Bekijk ticketdekking en huidig contract",
            "Gebruik de ingestelde bedrijfskalender voor interpretatie van reactietijden",
            "Vraag servicebeheer om verduidelijking bij onduidelijke dekking of scope"
          ],
          "permissions": "Operators en admins. Partners lezen alleen eigen klant- en taakgegevens; servicedesk en beheer vereisen een operatorrol.",
          "limits": "Automatische bewaking buiten kantooruren belooft geen doorlopend bemande support. Conceptplannen vormen geen afgesproken SLA.",
          "example": "Een weekendmelding kan automatisch bewaakt worden en in het afgesproken servicevenster worden beoordeeld."
        }
      }
    },
    {
      "id": "msp.contracts",
      "area": "commercial",
      "status": "available",
      "conditions": [],
      "anchors": [
        "/cockpit/help?feature=msp.contracts"
      ],
      "source_refs": [
        "apps/cockpit/README.md"
      ],
      "related": [
        "msp.roles",
        "msp.secrets"
      ],
      "locales": {
        "en": {
          "title": "View service contracts",
          "purpose": "Read plan, lifecycle status, hosting model and start date for the chosen organisation.",
          "when": "When checking which recorded service terms apply to an organisation.",
          "steps": [
            "Open Service desk and select the organisation",
            "Read each contract line",
            "Distinguish Draft from Active, Suspended or Ended",
            "Review unresolved pricing before relying on entitlement"
          ],
          "permissions": "Operators and admins. Partners can read only their own client and job records; staff service and operations data require an operator role.",
          "limits": "The page does not collect payments. Pending prices are placeholders, not approved offers.",
          "example": "A draft Standard contract remains a proposal until its separate activation requirements are met."
        },
        "nl": {
          "title": "Servicecontracten bekijken",
          "purpose": "Lees plan, levenscyclusstatus, hostingmodel en ingangsdatum voor de gekozen organisatie.",
          "when": "Wanneer je controleert welke vastgelegde serviceafspraken voor een organisatie gelden.",
          "steps": [
            "Open Servicedesk en kies de organisatie",
            "Lees de contractregels",
            "Onderscheid Concept van Actief, Gepauzeerd of Beëindigd",
            "Beoordeel open prijsafspraken voordat je op rechten vertrouwt"
          ],
          "permissions": "Operators en admins. Partners lezen alleen eigen klant- en taakgegevens; servicedesk en beheer vereisen een operatorrol.",
          "limits": "Deze pagina int geen betalingen. Openstaande prijzen zijn voorlopige gegevens, geen goedgekeurde offertes.",
          "example": "Een Standard-conceptcontract blijft een voorstel totdat aan de aparte activeringsvoorwaarden is voldaan."
        }
      }
    },
    {
      "id": "msp.contract-draft",
      "area": "commercial",
      "status": "available",
      "conditions": [],
      "anchors": [
        "/cockpit/help?feature=msp.contract-draft"
      ],
      "source_refs": [
        "apps/cockpit/README.md"
      ],
      "related": [
        "msp.roles",
        "msp.secrets"
      ],
      "locales": {
        "en": {
          "title": "Draft a service contract",
          "purpose": "Record the proposed plan, start date and hosting arrangement without activating billing.",
          "when": "Before activating a service agreement that still needs commercial review.",
          "steps": [
            "As admin, choose Draft service contract",
            "Select the plan and start date",
            "Select Synthwave EU cloud, Client cloud or On premise",
            "Save the draft and review it"
          ],
          "permissions": "Admin for sensitive changes; operators may inspect service records where allowed.",
          "limits": "Saving the draft neither provisions hosting nor activates modules. Plan details marked pending still need agreement.",
          "example": "Record client-cloud hosting for a future agreement without ordering a VM."
        },
        "nl": {
          "title": "Servicecontract voorbereiden",
          "purpose": "Leg voorgesteld plan, ingangsdatum en hostingafspraak vast zonder facturatie te activeren.",
          "when": "Voordat je een serviceovereenkomst activeert die nog commerciële beoordeling nodig heeft.",
          "steps": [
            "Kies als admin Servicecontract voorbereiden",
            "Selecteer plan en ingangsdatum",
            "Kies Synthwave EU-cloud, Klantcloud of Op locatie",
            "Sla het concept op en beoordeel het"
          ],
          "permissions": "Admin voor gevoelige wijzigingen; operators bekijken servicedossiers waar toegestaan.",
          "limits": "Opslaan richt geen hosting in en activeert geen modules. Plangegevens met een voorlopige status moeten nog worden afgesproken.",
          "example": "Leg klantcloudhosting vast voor een toekomstige afspraak zonder een VM te bestellen."
        }
      }
    },
    {
      "id": "msp.contract-lifecycle",
      "area": "commercial",
      "status": "conditional",
      "conditions": [
        "deployment_prerequisites"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.contract-lifecycle"
      ],
      "source_refs": [
        "apps/cockpit/README.md"
      ],
      "related": [
        "msp.roles",
        "msp.secrets"
      ],
      "locales": {
        "en": {
          "title": "Contract activation and lifecycle",
          "purpose": "Use controlled administration to activate, suspend, resume or end a valid agreement.",
          "when": "When an authorised administrator needs to activate, change or end a recorded contract.",
          "steps": [
            "Verify the approved agreement and effective pricing",
            "Have an authorised admin use the commercial staff API",
            "Review the result and audit record",
            "Confirm downstream operational effects separately"
          ],
          "permissions": "Admin for sensitive changes; operators may inspect service records where allowed.",
          "limits": "These lifecycle endpoints have no dedicated buttons on the current service desk. Contract state does not prove payment or deployed module state.",
          "example": "Pause a contract through the controlled process and separately review operational access."
        },
        "nl": {
          "title": "Contractactivering en levenscyclus",
          "purpose": "Gebruik gecontroleerd beheer om een geldige afspraak te activeren, pauzeren, hervatten of beëindigen.",
          "when": "Wanneer een bevoegde beheerder een vastgelegd contract moet activeren, wijzigen of beëindigen.",
          "steps": [
            "Controleer goedgekeurde afspraak en geldige prijzen",
            "Laat een bevoegde admin de commerciële beheer-API gebruiken",
            "Controleer resultaat en auditregistratie",
            "Controleer operationele vervolgeffecten afzonderlijk"
          ],
          "permissions": "Admin voor gevoelige wijzigingen; operators bekijken servicedossiers waar toegestaan.",
          "limits": "Deze acties hebben nog geen eigen knoppen in de huidige servicedesk. Contractstatus bewijst geen betaling of daadwerkelijk actieve modules.",
          "example": "Pauzeer een contract via het beheerproces en beoordeel operationele toegang afzonderlijk."
        }
      }
    },
    {
      "id": "msp.prices",
      "area": "commercial",
      "status": "conditional",
      "conditions": [
        "deployment_prerequisites"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.prices"
      ],
      "source_refs": [
        "apps/cockpit/README.md"
      ],
      "related": [
        "msp.roles",
        "msp.secrets"
      ],
      "locales": {
        "en": {
          "title": "Plans, products and prices",
          "purpose": "Maintain commercial definitions and validity periods without inventing prices in the guide.",
          "when": "Before quoting a fee or interpreting a catalogue price.",
          "steps": [
            "Review the offered plan in the service desk",
            "Use authorised commercial administration for detailed price rows",
            "Confirm currency, validity and approved terms before activation"
          ],
          "permissions": "Admin for sensitive changes; operators may inspect service records where allowed.",
          "limits": "Detailed editing is API-based. Placeholder entries are not saleable commitments, and no price in this guide overrides a signed agreement.",
          "example": "Leave a pending hosting price unresolved instead of entering an estimated amount as agreed."
        },
        "nl": {
          "title": "Plannen, producten en prijzen",
          "purpose": "Beheer commerciële definities en geldigheidsperioden zonder prijzen in de handleiding te verzinnen.",
          "when": "Voordat je een bedrag offreert of een catalogusprijs beoordeelt.",
          "steps": [
            "Bekijk het aangeboden plan in de servicedesk",
            "Gebruik bevoegd commercieel beheer voor gedetailleerde prijsregels",
            "Bevestig valuta, geldigheid en goedgekeurde voorwaarden voor activering"
          ],
          "permissions": "Admin voor gevoelige wijzigingen; operators bekijken servicedossiers waar toegestaan.",
          "limits": "Gedetailleerd beheer loopt via de API. Voorlopige gegevens zijn geen verkooptoezegging; deze handleiding vervangt geen getekende afspraak.",
          "example": "Laat een voorlopige hostingprijs open in plaats van een schatting als afspraak op te slaan."
        }
      }
    },
    {
      "id": "msp.billing",
      "area": "commercial",
      "status": "conditional",
      "conditions": [
        "deployment_prerequisites"
      ],
      "anchors": [
        "/cockpit/payments",
        "/cockpit/help?feature=msp.billing"
      ],
      "source_refs": [
        "apps/cockpit/README.md",
        "apps/cockpit/docs/mollie-payments.md"
      ],
      "related": [
        "msp.roles",
        "msp.secrets"
      ],
      "locales": {
        "en": {
          "title": "Pay invoices with Mollie",
          "purpose": "Create checkout links for invoiced requests and verify payment with Mollie.",
          "when": "After approving and invoicing a customer request.",
          "steps": [
            "Open Payments and check the Mollie connection and test or live mode.",
            "As admin, save the API key in the secure field. It is verified and stored on the server only.",
            "Approve the request, issue the invoice in your accounting system and record its reference.",
            "Create and share the checkout link. The VAT-inclusive amount comes from the request; repeated clicks reuse the current payment.",
            "Mollie reports changes. SynthPulse checks amount, currency, profile and customer metadata before a live payment settles the invoice.",
            "Use Check status with Mollie to verify again. If creation was interrupted, enter its payment ID from Mollie to recover the original payment.",
            "Review reported refunds and chargebacks manually."
          ],
          "permissions": "Operators may read. Only admins can configure the key and process payment requests.",
          "limits": "Requires a key, public webhook, real prices and contracts. Test payments do not settle real invoices. Issue invoice documents in your accounting system. Automatic direct debit and subscription collection are not connected. Hours are credited on invoicing, never twice on payment.",
          "example": "An invoiced support bundle receives a checkout link. A verified live payment changes its status to Paid."
        },
        "nl": {
          "title": "Facturen betalen met Mollie",
          "purpose": "Maak betaallinks voor gefactureerde aanvragen en controleer betaling via Mollie.",
          "when": "Na het goedkeuren en factureren van een klantaanvraag.",
          "steps": [
            "Open Betalingen en controleer de Mollie-koppeling en test- of livemodus.",
            "Sla als admin de API-sleutel in het beveiligde veld op. Deze wordt gecontroleerd en alleen op de server bewaard.",
            "Keur de aanvraag goed, maak de factuur in je boekhouding en registreer het factuurnummer.",
            "Maak en deel de betaallink. Het bedrag inclusief btw komt uit de aanvraag; opnieuw klikken gebruikt dezelfde lopende betaling.",
            "Mollie meldt wijzigingen. SynthPulse controleert bedrag, valuta, profiel en klantkoppeling voordat een livebetaling de factuur voldoet.",
            "Gebruik Status bij Mollie controleren voor een nieuwe controle. Na een onderbroken aanmaak kun je het betaal-ID uit Mollie invoeren om de oorspronkelijke betaling te koppelen.",
            "Controleer gemelde terugbetalingen en terugboekingen handmatig."
          ],
          "permissions": "Operators mogen lezen. Alleen admins mogen de sleutel instellen en betaalverzoeken verwerken.",
          "limits": "Vereist een sleutel, openbare webhook, echte tarieven en contracten. Testbetalingen voldoen geen echte facturen. Factuurdocumenten maak je in de boekhouding. Automatische incasso en abonnementincasso zijn nog niet aangesloten. Uren worden bij facturatie toegekend en niet opnieuw bij betaling.",
          "example": "Een gefactureerde urenbundel krijgt een betaallink. Na bevestigde livebetaling wordt de status Betaald."
        }
      }
    },
    {
      "id": "msp.hosting",
      "area": "commercial",
      "status": "conditional",
      "conditions": [
        "deployment_prerequisites"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.hosting"
      ],
      "source_refs": [
        "apps/cockpit/README.md"
      ],
      "related": [
        "msp.roles",
        "msp.secrets"
      ],
      "locales": {
        "en": {
          "title": "Hosting responsibility",
          "purpose": "Distinguish who owns the infrastructure from where configuration is prepared.",
          "when": "Before agreeing where an installation runs and who owns its infrastructure.",
          "steps": [
            "Compare the registered installation and contract hosting model",
            "Verify cloud account, region and responsibility",
            "Review differences with the hosting owner before changing records"
          ],
          "permissions": "Operators and admins. Partners can read only their own client and job records; staff service and operations data require an operator role.",
          "limits": "A hosting label is not a guarantee of regional availability, deployment readiness, certification or included cloud costs.",
          "example": "Client cloud means a reviewed client account, not automatically Synthwave-owned infrastructure."
        },
        "nl": {
          "title": "Verantwoordelijkheid voor hosting",
          "purpose": "Onderscheid wie de infrastructuur beheert van waar de configuratie wordt voorbereid.",
          "when": "Voordat je afspreekt waar een installatie draait en wie de infrastructuur beheert.",
          "steps": [
            "Vergelijk hostingmodel van installatie en contract",
            "Controleer cloudaccount, regio en verantwoordelijkheid",
            "Bespreek verschillen met de hostingverantwoordelijke voordat je gegevens wijzigt"
          ],
          "permissions": "Operators en admins. Partners lezen alleen eigen klant- en taakgegevens; servicedesk en beheer vereisen een operatorrol.",
          "limits": "Een hostinglabel garandeert geen regiobeschikbaarheid, installatiegereedheid, certificering of inbegrepen cloudkosten.",
          "example": "Klantcloud betekent een beoordeeld klantaccount, niet automatisch infrastructuur van Synthwave."
        }
      }
    },
    {
      "id": "msp.operations",
      "area": "operations",
      "status": "available",
      "conditions": [],
      "anchors": [
        "/cockpit/help?feature=msp.operations"
      ],
      "source_refs": [
        "apps/cockpit/README.md"
      ],
      "related": [
        "msp.roles",
        "msp.secrets"
      ],
      "locales": {
        "en": {
          "title": "Operations overview",
          "purpose": "Review registered installations, last contact and grouped operational issues.",
          "when": "During routine operational review or after a reported service problem.",
          "steps": [
            "Open Operations",
            "Read installation identity, organisation and last seen",
            "Review hosting drift and operational issues",
            "Choose Refresh for current data"
          ],
          "permissions": "Operators and admins. Partners can read only their own client and job records; staff service and operations data require an operator role.",
          "limits": "No recent heartbeat means uncertain freshness, not proof of an outage. An empty issue list is not evidence that every service is monitored.",
          "example": "An installation can appear without a heartbeat while enrollment is still being completed."
        },
        "nl": {
          "title": "Beheeroverzicht",
          "purpose": "Bekijk geregistreerde installaties, laatste contact en gegroepeerde operationele meldingen.",
          "when": "Tijdens een gewone beheercontrole of na een gemeld serviceprobleem.",
          "steps": [
            "Open Beheer",
            "Lees installatie, organisatie en laatste contact",
            "Beoordeel hostingafwijkingen en operationele meldingen",
            "Kies Vernieuwen voor actuele gegevens"
          ],
          "permissions": "Operators en admins. Partners lezen alleen eigen klant- en taakgegevens; servicedesk en beheer vereisen een operatorrol.",
          "limits": "Geen recente heartbeat betekent onzekere actualiteit, geen bewijs van uitval. Een lege meldingenlijst bewijst niet dat elke dienst wordt bewaakt.",
          "example": "Een installatie kan zichtbaar zijn zonder heartbeat terwijl registratie nog wordt afgerond."
        }
      }
    },
    {
      "id": "msp.installations",
      "area": "operations",
      "status": "conditional",
      "conditions": [
        "deployment_prerequisites"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.installations"
      ],
      "source_refs": [
        "apps/cockpit/README.md"
      ],
      "related": [
        "msp.roles",
        "msp.secrets"
      ],
      "locales": {
        "en": {
          "title": "Register an installation",
          "purpose": "Associate a machine record with its organisation, hosting and private-network identity.",
          "when": "When registering or inspecting a concrete installation belonging to an organisation.",
          "steps": [
            "Inspect existing installations to prevent duplicates",
            "Have an admin register the real machine through the staff API",
            "Confirm organisation, kind, hosting and mesh name",
            "Enroll its reporter separately"
          ],
          "permissions": "Operators and admins. Partners can read only their own client and job records; staff service and operations data require an operator role.",
          "limits": "The current Operations page displays records but does not include an installation-creation form. Registration creates no cloud machine.",
          "example": "Register an actual HQ host with kind hq rather than inventing a customer VM."
        },
        "nl": {
          "title": "Installatie registreren",
          "purpose": "Koppel een machinerecord aan organisatie, hosting en privénetwerkidentiteit.",
          "when": "Bij het registreren of bekijken van een concrete installatie van een organisatie.",
          "steps": [
            "Controleer bestaande installaties om dubbelen te voorkomen",
            "Laat een admin de echte machine via de beheer-API registreren",
            "Bevestig organisatie, soort, hosting en netwerknaam",
            "Registreer daarna de reporter afzonderlijk"
          ],
          "permissions": "Operators en admins. Partners lezen alleen eigen klant- en taakgegevens; servicedesk en beheer vereisen een operatorrol.",
          "limits": "De huidige beheerpagina toont gegevens maar heeft geen formulier voor nieuwe installaties. Registratie maakt geen cloudmachine.",
          "example": "Registreer een bestaande hoofdmachine als hq in plaats van een klant-VM te verzinnen."
        }
      }
    },
    {
      "id": "msp.enrollment",
      "area": "operations",
      "status": "conditional",
      "conditions": [
        "deployment_prerequisites"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.enrollment"
      ],
      "source_refs": [
        "apps/cockpit/README.md"
      ],
      "related": [
        "msp.roles",
        "msp.secrets"
      ],
      "locales": {
        "en": {
          "title": "Reporter enrollment",
          "purpose": "Give a real installation a narrowly scoped machine credential through one-time enrollment.",
          "when": "When a newly registered installation needs its first scoped reporter credential.",
          "steps": [
            "Register the installation first",
            "Have an operator mint a reporter enrollment code",
            "Transfer it through the approved private channel",
            "Exchange it once on the installation and protect the resulting credential file",
            "Verify the first signed heartbeat"
          ],
          "permissions": "Operators and admins. Partners can read only their own client and job records; staff service and operations data require an operator role.",
          "limits": "Enrollment is an operator API/installer workflow, not a button in Operations. Codes expire and secrets must never enter ticket notes or logs.",
          "example": "Enroll a reporter-only identity without granting access to support or control administration."
        },
        "nl": {
          "title": "Reporter registreren",
          "purpose": "Geef een echte installatie een beperkt machinegeheim via eenmalige registratie.",
          "when": "Wanneer een nieuwe installatie haar eerste afgeschermde reportersleutel nodig heeft.",
          "steps": [
            "Registreer eerst de installatie",
            "Laat een operator een registratietoken voor de reporter maken",
            "Draag het via het goedgekeurde privékanaal over",
            "Wissel het eenmaal in op de installatie en bescherm het sleutelbestand",
            "Controleer de eerste ondertekende heartbeat"
          ],
          "permissions": "Operators en admins. Partners lezen alleen eigen klant- en taakgegevens; servicedesk en beheer vereisen een operatorrol.",
          "limits": "Registratie verloopt via beheer-API en installer, niet via een knop in Beheer. Tokens verlopen en geheimen horen nooit in ticketnotities of logs.",
          "example": "Registreer een reporter-identiteit zonder toegang tot support- of configuratiebeheer."
        }
      }
    },
    {
      "id": "msp.heartbeat",
      "area": "operations",
      "status": "conditional",
      "conditions": [
        "deployment_prerequisites"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.heartbeat"
      ],
      "source_refs": [
        "apps/cockpit/README.md"
      ],
      "related": [
        "msp.roles",
        "msp.secrets",
        "msp.retention",
        "msp.reporter-spool",
        "msp.reporter-dry-run"
      ],
      "locales": {
        "en": {
          "title": "Signed heartbeats and last seen",
          "purpose": "Track the latest authenticated installation report and its configured local health checks.",
          "when": "When checking the most recent contact and reported health of an installation.",
          "steps": [
            "Open Operations",
            "Compare last seen with the expected reporter interval",
            "If stale, inspect the reporter timer, local probe and transport",
            "Refresh after recovery",
            "Use Refresh to recalculate contact age; compare it with the normal five-minute HQ interval. A future timestamp needs a clock check, not an automatic incident."
          ],
          "permissions": "Operators and admins. Partners can read only their own client and job records; staff service and operations data require an operator role.",
          "limits": "Only configured probes are covered. Each heartbeat is freshly measured; historical heartbeats are not replayed after an outage. Critical-transition events use a separate private durable queue. Full discovery, automatic remediation and universal fleet coverage are not implied.",
          "example": "A five-minute HQ reporter checks the configured WebUI health endpoint and sends signed metadata."
        },
        "nl": {
          "title": "Ondertekende heartbeats en laatste contact",
          "purpose": "Volg de laatste geauthenticeerde installatiemelding en de ingestelde lokale gezondheidscontroles.",
          "when": "Bij het controleren van het laatste contact en de gemelde gezondheid van een installatie.",
          "steps": [
            "Open Beheer",
            "Vergelijk laatste contact met het verwachte reporterinterval",
            "Controleer bij veroudering timer, lokale controle en transport van de reporter",
            "Vernieuw na herstel",
            "Gebruik Refresh om de contactleeftijd opnieuw te berekenen; vergelijk met het normale HQ-interval van vijf minuten. Een toekomstige tijd vraagt een klokcontrole, geen automatisch incident."
          ],
          "permissions": "Operators en admins. Partners lezen alleen eigen klant- en taakgegevens; servicedesk en beheer vereisen een operatorrol.",
          "limits": "Alleen ingerichte controles vallen hieronder. Iedere heartbeat wordt opnieuw gemeten; oude heartbeats worden na een storing niet opnieuw afgespeeld. Meldingen van een overgang naar kritiek gebruiken een aparte, duurzame privéwachtrij. Volledige detectie, automatisch herstel en dekking van alle machines zijn niet inbegrepen.",
          "example": "Een HQ-reporter controleert elke vijf minuten het ingestelde WebUI-gezondheidsadres en verstuurt ondertekende metadata."
        }
      }
    },
    {
      "id": "msp.issues",
      "area": "operations",
      "status": "available",
      "conditions": [],
      "anchors": [
        "/cockpit/help?feature=msp.issues"
      ],
      "source_refs": [
        "apps/cockpit/README.md"
      ],
      "related": [
        "msp.roles",
        "msp.secrets"
      ],
      "locales": {
        "en": {
          "title": "Operational issues",
          "purpose": "Group repeated approved health-event metadata so staff can inspect a pattern.",
          "when": "When repeated operational failures need assessment before creating support work.",
          "steps": [
            "Read the issue title, installation, count, status and last seen",
            "Check the affected service locally through authorised operations",
            "Create a support ticket only after assessing impact"
          ],
          "permissions": "Operators and admins. Partners can read only their own client and job records; staff service and operations data require an operator role.",
          "limits": "Current intake retains enumerated metadata and counts, not arbitrary diagnostic bodies. It does not automatically create or notify every support ticket.",
          "example": "Repeated webui health errors form one grouped issue rather than many identical tickets."
        },
        "nl": {
          "title": "Operationele meldingen",
          "purpose": "Groepeer herhaalde toegestane gezondheidsmetadata zodat medewerkers een patroon kunnen onderzoeken.",
          "when": "Wanneer herhaalde beheerfouten beoordeling nodig hebben voordat je supportwerk aanmaakt.",
          "steps": [
            "Lees titel, installatie, aantal, status en laatste contact",
            "Controleer de dienst via bevoegd beheer",
            "Maak pas na beoordeling van de impact een supportticket"
          ],
          "permissions": "Operators en admins. Partners lezen alleen eigen klant- en taakgegevens; servicedesk en beheer vereisen een operatorrol.",
          "limits": "De huidige inname bewaart vaste metadata en aantallen, geen willekeurige diagnose-inhoud. Niet iedere melding maakt of verstuurt automatisch een supportticket.",
          "example": "Herhaalde WebUI-gezondheidsfouten vormen één gegroepeerde melding in plaats van veel gelijke tickets."
        }
      }
    },
    {
      "id": "msp.hosting-drift",
      "area": "operations",
      "status": "available",
      "conditions": [],
      "anchors": [
        "/cockpit/help?feature=msp.hosting-drift"
      ],
      "source_refs": [
        "apps/cockpit/README.md"
      ],
      "related": [
        "msp.roles",
        "msp.secrets"
      ],
      "locales": {
        "en": {
          "title": "Hosting drift",
          "purpose": "Highlight differences between registered hosting and values reported by an installation.",
          "when": "When reported hosting differs from the installation’s registered expectations.",
          "steps": [
            "Open Operations",
            "Find Review required in hosting drift",
            "Verify the real host and its intended registration",
            "Correct the approved source and inspect a later heartbeat"
          ],
          "permissions": "Operators and admins. Partners can read only their own client and job records; staff service and operations data require an operator role.",
          "limits": "A heartbeat cannot authorise its own move to another organisation or hosting model.",
          "example": "Investigate a changed region before accepting it as an approved relocation."
        },
        "nl": {
          "title": "Hostingafwijking",
          "purpose": "Markeer verschillen tussen geregistreerde hosting en waarden die een installatie meldt.",
          "when": "Wanneer gemelde hosting afwijkt van de geregistreerde verwachtingen van de installatie.",
          "steps": [
            "Open Beheer",
            "Zoek Controle nodig bij hostingafwijking",
            "Controleer de echte machine en bedoelde registratie",
            "Corrigeer de goedgekeurde bron en bekijk een latere heartbeat"
          ],
          "permissions": "Operators en admins. Partners lezen alleen eigen klant- en taakgegevens; servicedesk en beheer vereisen een operatorrol.",
          "limits": "Een heartbeat kan zichzelf geen toestemming geven voor een andere organisatie of hostingvorm.",
          "example": "Onderzoek een gewijzigde regio voordat je deze als goedgekeurde verhuizing beschouwt."
        }
      }
    },
    {
      "id": "msp.keys",
      "area": "security",
      "status": "conditional",
      "conditions": [
        "deployment_prerequisites"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.keys"
      ],
      "source_refs": [
        "apps/cockpit/README.md"
      ],
      "related": [
        "msp.overview"
      ],
      "locales": {
        "en": {
          "title": "Machine key revocation and rotation",
          "purpose": "Contain compromised machine access and rotate credentials with separation of duties.",
          "when": "When provisioning, rotating or revoking scoped installation credentials.",
          "steps": [
            "Identify the affected key and installation",
            "Use the authorised staff revocation endpoint for containment",
            "For rotation obtain a configured approver’s approval",
            "A different operator performs the rotation and completes enrollment",
            "Verify the replacement and audit trail"
          ],
          "permissions": "Operators and admins. Partners can read only their own client and job records; staff service and operations data require an operator role.",
          "limits": "These are controlled staff API actions. Enrollment secrets are returned once; revocation can stop reporting until repaired.",
          "example": "Revoke one exposed reporter key without distributing the master encryption key."
        },
        "nl": {
          "title": "Machinesleutels intrekken en vernieuwen",
          "purpose": "Beperk gecompromitteerde machinetoegang en vernieuw sleutels met gescheiden verantwoordelijkheden.",
          "when": "Bij het uitgeven, roteren of intrekken van afgeschermde installatiesleutels.",
          "steps": [
            "Identificeer sleutel en installatie",
            "Gebruik de bevoegde intrekkingsactie om toegang te stoppen",
            "Vraag voor vernieuwing akkoord van een ingestelde goedkeurder",
            "Een andere operator vernieuwt de sleutel en rondt registratie af",
            "Controleer vervanging en auditspoor"
          ],
          "permissions": "Operators en admins. Partners lezen alleen eigen klant- en taakgegevens; servicedesk en beheer vereisen een operatorrol.",
          "limits": "Dit zijn gecontroleerde beheer-API-acties. Registratiegeheimen worden eenmaal getoond; intrekking kan rapportage stoppen totdat dit is hersteld.",
          "example": "Trek één blootgestelde reportersleutel in zonder de centrale encryptiesleutel te verspreiden."
        }
      }
    },
    {
      "id": "msp.audit",
      "area": "security",
      "status": "conditional",
      "conditions": [
        "deployment_prerequisites"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.audit"
      ],
      "source_refs": [
        "apps/cockpit/README.md"
      ],
      "related": [
        "msp.overview"
      ],
      "locales": {
        "en": {
          "title": "Audit trail",
          "purpose": "Review attributable administrative changes and verify the stored chain for tampering.",
          "when": "When checking who performed a control-plane change and whether its audit chain verifies.",
          "steps": [
            "Have an admin inspect the staff audit endpoint",
            "Filter the relevant organisation or action when available",
            "Run chain verification",
            "Investigate unexpected changes rather than editing history"
          ],
          "permissions": "Admin for sensitive changes; operators may inspect service records where allowed.",
          "limits": "Audit verification is an integrity check, not proof that an action was commercially authorised or legally compliant.",
          "example": "Trace who created a draft contract and when, then inspect its approval separately."
        },
        "nl": {
          "title": "Auditspoor",
          "purpose": "Bekijk herleidbare beheerwijzigingen en controleer de opgeslagen keten op manipulatie.",
          "when": "Bij het controleren wie een beheerwijziging uitvoerde en of de auditketen klopt.",
          "steps": [
            "Laat een admin het auditendpoint bekijken",
            "Filter waar mogelijk op organisatie of actie",
            "Voer ketenverificatie uit",
            "Onderzoek onverwachte wijzigingen in plaats van geschiedenis aan te passen"
          ],
          "permissions": "Admin voor gevoelige wijzigingen; operators bekijken servicedossiers waar toegestaan.",
          "limits": "Auditverificatie controleert integriteit, niet of een actie commercieel was goedgekeurd of juridisch correct was.",
          "example": "Volg wie een conceptcontract maakte en wanneer, en controleer de goedkeuring afzonderlijk."
        }
      }
    },
    {
      "id": "msp.member-import",
      "area": "security",
      "status": "conditional",
      "conditions": [
        "deployment_prerequisites"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.member-import"
      ],
      "source_refs": [
        "apps/cockpit/README.md"
      ],
      "related": [
        "msp.overview"
      ],
      "locales": {
        "en": {
          "title": "Import organisation members",
          "purpose": "Keep central membership aligned with the approved rendered client configuration.",
          "when": "After a reviewed change to organisation membership in the client configuration.",
          "steps": [
            "Review organisation admins and billing roles in the source configuration",
            "Render the member artifact",
            "Have an operator import it through the staff API",
            "Review membership and later drift signals"
          ],
          "permissions": "Operators and admins. Partners can read only their own client and job records; staff service and operations data require an operator role.",
          "limits": "There is no free-form membership editor in the current service desk. Client roles and cockpit staff roles remain separate.",
          "example": "Import approved organisation admins rather than copying every cockpit operator into the customer."
        },
        "nl": {
          "title": "Organisatieleden importeren",
          "purpose": "Houd centraal lidmaatschap gelijk aan de goedgekeurde gegenereerde klantconfiguratie.",
          "when": "Na een beoordeelde wijziging van organisatielidmaatschap in de klantconfiguratie.",
          "steps": [
            "Beoordeel organisatiebeheerders en facturatierollen in de bronconfiguratie",
            "Genereer het ledenbestand",
            "Laat een operator dit via de beheer-API importeren",
            "Controleer lidmaatschap en latere afwijkingsmeldingen"
          ],
          "permissions": "Operators en admins. Partners lezen alleen eigen klant- en taakgegevens; servicedesk en beheer vereisen een operatorrol.",
          "limits": "De huidige servicedesk heeft geen vrije ledeneditor. Klantrollen en cockpitrollen blijven gescheiden.",
          "example": "Importeer goedgekeurde organisatiebeheerders in plaats van alle cockpitoperators als klantgebruiker toe te voegen."
        }
      }
    },
    {
      "id": "msp.secrets",
      "area": "security",
      "status": "available",
      "conditions": [],
      "anchors": [
        "/cockpit/help?feature=msp.secrets"
      ],
      "source_refs": [
        "apps/cockpit/README.md"
      ],
      "related": [
        "msp.overview"
      ],
      "locales": {
        "en": {
          "title": "Secret handling",
          "purpose": "Keep provider credentials, installer links and machine secrets out of ordinary configuration and support text.",
          "when": "Whenever a setup step, support case or diagnostic check involves credentials.",
          "steps": [
            "Use the credential fields or approved secret files",
            "Confirm the stored indicator or key name",
            "Use a private operator handover for one-time values",
            "Treat a missing value as a setup problem, not a reason to paste it into a ticket"
          ],
          "permissions": "Operators and admins. Partners can read only their own client and job records; staff service and operations data require an operator role.",
          "limits": "The browser receives key names rather than saved values. This guide never displays real secrets or current customer credentials.",
          "example": "Replace a provider key through its write-only field and record only the reason in the ticket."
        },
        "nl": {
          "title": "Omgaan met geheimen",
          "purpose": "Houd aanbiedersleutels, installerlinks en machinegeheimen buiten gewone configuratie en supporttekst.",
          "when": "Wanneer een inrichting, supportvraag of diagnose met inloggegevens te maken heeft.",
          "steps": [
            "Gebruik sleutelvelden of goedgekeurde geheime bestanden",
            "Controleer opslagindicatie of sleutelnaam",
            "Gebruik privéoverdracht voor eenmalige waarden",
            "Los ontbrekende sleutels op via inrichting, niet door ze in tickets te plakken"
          ],
          "permissions": "Operators en admins. Partners lezen alleen eigen klant- en taakgegevens; servicedesk en beheer vereisen een operatorrol.",
          "limits": "De browser krijgt sleutelnamen in plaats van opgeslagen waarden. Deze handleiding toont geen echte geheimen of klantinloggegevens.",
          "example": "Vervang een aanbiedersleutel via het eenrichtingsveld en noteer alleen de reden in het ticket."
        }
      }
    },
    {
      "id": "msp.telemetry",
      "area": "security",
      "status": "conditional",
      "conditions": [
        "deployment_prerequisites"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.telemetry"
      ],
      "source_refs": [
        "apps/cockpit/README.md"
      ],
      "related": [
        "msp.overview",
        "msp.retention"
      ],
      "locales": {
        "en": {
          "title": "Telemetry and retention",
          "purpose": "Understand which health metadata enters the control plane and how retention is bounded.",
          "when": "When deciding which health metadata an installation may send centrally.",
          "steps": [
            "Review organisation telemetry settings with an authorised operator",
            "Keep diagnostics free of personal content and secrets",
            "Check retention maintenance and stored event age during operations review"
          ],
          "permissions": "Operators and admins. Partners can read only their own client and job records; staff service and operations data require an operator role.",
          "limits": "Raw events default to 30 days, heartbeats to 7 days, and resolved or muted issues to six calendar months. The independent retention timer must be installed and verified. This is not full retention for every control table.",
          "example": "Use event counts to identify a recurring health problem without retaining conversation text."
        },
        "nl": {
          "title": "Telemetrie en bewaartermijnen",
          "purpose": "Begrijp welke gezondheidsmetadata het beheerplatform ontvangt en hoe bewaren wordt begrensd.",
          "when": "Bij het bepalen welke gezondheidsmetadata een installatie centraal mag doorgeven.",
          "steps": [
            "Beoordeel organisatietelemetrie met een bevoegde operator",
            "Houd diagnoses vrij van persoonsgegevens en geheimen",
            "Controleer bewaarbeheer en ouderdom van gebeurtenissen bij operationele controles"
          ],
          "permissions": "Operators en admins. Partners lezen alleen eigen klant- en taakgegevens; servicedesk en beheer vereisen een operatorrol.",
          "limits": "Ruwe meldingen worden standaard 30 dagen bewaard, heartbeats 7 dagen en opgeloste of gedempte issues zes kalendermaanden. De onafhankelijke bewaartimer moet worden geïnstalleerd en gecontroleerd. Dit is geen volledige bewaartaak voor elke beheertabel.",
          "example": "Gebruik aantallen om een terugkerend gezondheidsprobleem te zien zonder gesprekstekst te bewaren."
        }
      }
    },
    {
      "id": "msp.module-catalog",
      "area": "modules",
      "status": "conditional",
      "conditions": [
        "deployment_prerequisites"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.module-catalog"
      ],
      "source_refs": [
        "apps/cockpit/README.md"
      ],
      "related": [
        "msp.roles",
        "msp.secrets"
      ],
      "locales": {
        "en": {
          "title": "Service modules and availability",
          "purpose": "Distinguish technical service selection, commercial entitlement and observed runtime health.",
          "when": "Before explaining a module’s availability, dependencies or installation requirements.",
          "steps": [
            "Review the module’s catalogue status",
            "Check architecture and hosting restrictions",
            "Confirm the approved contract and actual installation",
            "Treat requested activation separately from observed running state"
          ],
          "permissions": "Operators and admins. Partners can read only their own client and job records; staff service and operations data require an operator role.",
          "limits": "A wizard checkbox is not a purchase or completed module activation. Advanced modules can remain proposed or unavailable.",
          "example": "A research module can be listed while its architecture or activation prerequisites are unmet."
        },
        "nl": {
          "title": "Servicemodules en beschikbaarheid",
          "purpose": "Onderscheid technische dienstkeuze, contractrechten en waargenomen runtimegezondheid.",
          "when": "Voordat je beschikbaarheid, afhankelijkheden of installatievoorwaarden van een module uitlegt.",
          "steps": [
            "Controleer de catalogusstatus van de module",
            "Controleer architectuur- en hostingbeperkingen",
            "Bevestig goedgekeurd contract en echte installatie",
            "Onderscheid aangevraagde activering van waargenomen werking"
          ],
          "permissions": "Operators en admins. Partners lezen alleen eigen klant- en taakgegevens; servicedesk en beheer vereisen een operatorrol.",
          "limits": "Een wizardvinkje is geen aankoop of afgeronde moduleactivering. Geavanceerde modules kunnen voorgesteld of niet beschikbaar blijven.",
          "example": "Een onderzoeksmodule kan in de lijst staan terwijl architectuur of activeringsvoorwaarden niet kloppen."
        }
      }
    },
    {
      "id": "msp.module-activation",
      "area": "modules",
      "status": "planned",
      "conditions": [
        "not_released"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.module-activation"
      ],
      "source_refs": [
        "apps/cockpit/README.md"
      ],
      "related": [
        "msp.roles",
        "msp.secrets"
      ],
      "locales": {
        "en": {
          "title": "Module request and activation workflow",
          "purpose": "Describe the future end-to-end quote, contract and operational activation flow.",
          "when": "When assessing the remaining work between a module request and verified live operation.",
          "steps": [
            "Discuss the required capability",
            "Verify catalogue and hosting support",
            "Record an approved change request",
            "Use the established delivery process until the complete activation workflow is released"
          ],
          "permissions": "Operators and admins. Partners can read only their own client and job records; staff service and operations data require an operator role.",
          "limits": "This cockpit does not yet offer a complete self-service module purchase, provisioning and rollback wizard.",
          "example": "Request a knowledge module through service delivery instead of assuming a checkbox provisions it."
        },
        "nl": {
          "title": "Modules aanvragen en activeren",
          "purpose": "Beschrijf de toekomstige volledige aanvraag-, offerte-, contract- en activeringsstroom.",
          "when": "Bij het beoordelen van het resterende werk tussen een moduleverzoek en gecontroleerd live gebruik.",
          "steps": [
            "Bespreek de benodigde functie",
            "Controleer catalogus en hostingondersteuning",
            "Leg een goedgekeurde wijzigingsaanvraag vast",
            "Gebruik het geldende leveringsproces totdat de volledige activeringsstroom is uitgebracht"
          ],
          "permissions": "Operators en admins. Partners lezen alleen eigen klant- en taakgegevens; servicedesk en beheer vereisen een operatorrol.",
          "limits": "Dit cockpit biedt nog geen volledige zelfbedieningswizard voor moduleaankoop, installatie en terugdraaien.",
          "example": "Vraag een kennismodule aan via dienstverlening in plaats van aan te nemen dat een vinkje deze installeert."
        }
      }
    },
    {
      "id": "msp.backups",
      "area": "operations",
      "status": "conditional",
      "conditions": [
        "deployment_prerequisites"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.backups"
      ],
      "source_refs": [
        "modules/backup/module-dumps.sh",
        "modules/backup/restore-drill.sh"
      ],
      "related": [
        "msp.roles",
        "msp.secrets"
      ],
      "locales": {
        "en": {
          "title": "Backup coverage",
          "purpose": "Review what application data is protected and whether the backup process is actually installed and working.",
          "when": "Before relying on recovery, or after adding a module that stores its own data.",
          "steps": [
            "Inventory the enabled modules and their database or volume records in the module catalogue.",
            "Through authorised host operations, check the module protection configuration, destination, encryption key custody and scheduled job. There is no backup button in the cockpit.",
            "Run or inspect the prepared module backup operation and check its status metadata and retained generations.",
            "Verify any offsite copy separately; a local archive does not prove external protection.",
            "Restore a representative generation into a disposable environment and record the checked data and application health."
          ],
          "permissions": "Operators and admins. Partners can read only their own client and job records; staff service and operations data require an operator role.",
          "limits": "Prepared module-protection scripts do not mean HQ timers or offsite backups are activated. No backup controls exist in the current cockpit UI.",
          "example": "A successful database dump still needs offsite storage and a tested restore path."
        },
        "nl": {
          "title": "Back-updekking",
          "purpose": "Beoordeel welke applicatiegegevens beschermd zijn en of het back-upproces echt is geïnstalleerd en werkt.",
          "when": "Voordat je op herstel vertrouwt of na het toevoegen van een module met eigen gegevens.",
          "steps": [
            "Inventariseer ingeschakelde modules en hun database- of volumegegevens in de modulecatalogus.",
            "Controleer via bevoegd hostbeheer de modulebescherming, bestemming, bewaring van encryptiesleutels en geplande taak. De cockpit heeft geen back-upknop.",
            "Voer de voorbereide moduleback-up uit of bekijk het resultaat, de statusmetadata en bewaarde generaties.",
            "Controleer een externe kopie apart; een lokaal archief bewijst geen externe bescherming.",
            "Herstel een representatieve generatie in een tijdelijke omgeving en leg gecontroleerde gegevens en applicatiegezondheid vast."
          ],
          "permissions": "Operators en admins. Partners lezen alleen eigen klant- en taakgegevens; servicedesk en beheer vereisen een operatorrol.",
          "limits": "Voorbereide beschermingsscripts betekenen niet dat HQ-timers of externe back-ups actief zijn. De huidige cockpit heeft geen back-upbedieningsscherm.",
          "example": "Een geslaagde databasedump vraagt nog externe opslag en een getest herstelpad."
        }
      }
    },
    {
      "id": "msp.restore",
      "area": "operations",
      "status": "conditional",
      "conditions": [
        "deployment_prerequisites"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.restore"
      ],
      "source_refs": [
        "apps/cockpit/README.md"
      ],
      "related": [
        "msp.roles",
        "msp.secrets"
      ],
      "locales": {
        "en": {
          "title": "Restore testing",
          "purpose": "Prove a backup can be read and restored in an isolated environment before depending on it.",
          "when": "During an isolated recovery rehearsal or an approved recovery incident.",
          "steps": [
            "Choose a representative backup",
            "Restore to a disposable database or scratch path",
            "Validate expected data and application checks",
            "Record evidence and remove the scratch environment"
          ],
          "permissions": "Operators and admins. Partners can read only their own client and job records; staff service and operations data require an operator role.",
          "limits": "Never restore over a live customer as a routine test. Existing SQLite/PostgreSQL helpers do not prove every module or storage engine is covered.",
          "example": "Restore a synthetic support database into a temporary directory and compare expected rows."
        },
        "nl": {
          "title": "Herstel testen",
          "purpose": "Bewijs dat een back-up leesbaar en herstelbaar is in een geïsoleerde omgeving voordat je erop vertrouwt.",
          "when": "Tijdens een afgeschermde hersteloefening of een goedgekeurde herstelactie.",
          "steps": [
            "Kies een representatieve back-up",
            "Herstel naar een tijdelijke database of testmap",
            "Valideer verwachte gegevens en applicatiecontroles",
            "Leg bewijs vast en verwijder de testomgeving"
          ],
          "permissions": "Operators en admins. Partners lezen alleen eigen klant- en taakgegevens; servicedesk en beheer vereisen een operatorrol.",
          "limits": "Herstel nooit over een actieve klantomgeving als gewone test. SQLite- en PostgreSQL-hulpmiddelen bewijzen niet dat elke module of opslagmotor gedekt is.",
          "example": "Herstel een synthetische supportdatabase in een tijdelijke map en vergelijk de verwachte regels."
        }
      }
    },
    {
      "id": "msp.app-install",
      "area": "access",
      "status": "conditional",
      "conditions": [
        "deployment_prerequisites"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.app-install"
      ],
      "source_refs": [
        "apps/cockpit/README.md"
      ],
      "related": [
        "msp.overview"
      ],
      "locales": {
        "en": {
          "title": "Install cockpit as an app",
          "purpose": "Keep the private cockpit available from a device’s app launcher when the browser supports installation.",
          "when": "When adding the cockpit shortcut to a supported browser or device.",
          "steps": [
            "Open the approved cockpit URL",
            "Use the browser’s Install app or Add to Home Screen",
            "Sign in normally",
            "Keep network access available for live records"
          ],
          "permissions": "Any signed-in cockpit role; sign-in itself requires configured access.",
          "limits": "The cached app shell is not an offline copy of support records. API responses and credentials are not intended as offline data.",
          "example": "Launch the cockpit from the phone home screen while connected to the private network."
        },
        "nl": {
          "title": "Cockpit als app installeren",
          "purpose": "Open het privécockpit vanuit de appstarter van een apparaat als de browser installatie ondersteunt.",
          "when": "Bij het toevoegen van een cockpit-snelkoppeling in een ondersteunde browser of op een apparaat.",
          "steps": [
            "Open de goedgekeurde cockpit-URL",
            "Kies App installeren of Toevoegen aan beginscherm in de browser",
            "Log normaal in",
            "Zorg voor netwerktoegang voor actuele gegevens"
          ],
          "permissions": "Iedere ingelogde cockpitrol; inloggen vereist ingerichte toegang.",
          "limits": "De opgeslagen appschil is geen offlinekopie van supportgegevens. API-antwoorden en sleutels zijn niet bedoeld als offlinegegevens.",
          "example": "Open de cockpit vanaf het beginscherm van je telefoon terwijl je met het privénetwerk verbonden bent."
        }
      }
    },
    {
      "id": "msp.client-retirement",
      "area": "clients",
      "status": "conditional",
      "conditions": [
        "deployment_prerequisites"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.client-retirement"
      ],
      "source_refs": [
        "apps/cockpit/README.md"
      ],
      "related": [
        "msp.roles",
        "msp.secrets"
      ],
      "locales": {
        "en": {
          "title": "Retire a client safely",
          "purpose": "Coordinate contract closure, exports, retained records and authorised infrastructure removal.",
          "when": "When a client installation or service relationship is ending.",
          "steps": [
            "Confirm the approved end-of-service scope",
            "Check required exports and retention",
            "Have the authorised administrator use the established teardown tooling",
            "Verify cloud resources, credentials and records separately"
          ],
          "permissions": "Admin for sensitive changes; operators may inspect service records where allowed.",
          "limits": "There is no one-click full customer offboarding screen here. Deleting a draft is not equivalent to stopping infrastructure or deleting retained service records.",
          "example": "Close a contract and verify actual infrastructure removal as separate recorded actions."
        },
        "nl": {
          "title": "Klantomgeving zorgvuldig beëindigen",
          "purpose": "Stem contractbeëindiging, exports, bewaarde gegevens en bevoegde infrastructuurverwijdering af.",
          "when": "Wanneer een klantinstallatie of servicerelatie wordt beëindigd.",
          "steps": [
            "Bevestig de goedgekeurde beëindiging",
            "Controleer benodigde exports en bewaartermijnen",
            "Laat de bevoegde admin de bestaande verwijdertools gebruiken",
            "Controleer cloudmiddelen, sleutels en dossiers afzonderlijk"
          ],
          "permissions": "Admin voor gevoelige wijzigingen; operators bekijken servicedossiers waar toegestaan.",
          "limits": "Er is hier geen volledig afsluitscherm met één knop. Een concept verwijderen stopt niet automatisch infrastructuur en verwijdert geen bewaarde servicedossiers.",
          "example": "Sluit een contract en controleer infrastructuurverwijdering als afzonderlijk vastgelegde acties."
        }
      }
    },
    {
      "id": "msp.profile.webui",
      "area": "modules",
      "status": "conditional",
      "conditions": [
        "selected_service_profile",
        "deployment_and_credentials"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.profile.webui"
      ],
      "source_refs": [
        "apps/cockpit/frontend/src/wizard/StepModules.jsx"
      ],
      "related": [
        "msp.wizard.modules.profiles",
        "msp.module-catalog"
      ],
      "locales": {
        "en": {
          "title": "SynthPulse WebUI",
          "purpose": "Chat, agents and staff-governed work in the main client interface.",
          "when": "When selecting services for a client installation and checking whether this component is required.",
          "steps": [
            "Open Modules in the client wizard.",
            "Select the webui service profile.",
            "Review resources, dependencies, credentials and architecture in Review.",
            "Deploy only through the approved plan, then verify the running service."
          ],
          "permissions": "Operators and admins configure services; partners only inspect their own clients.",
          "limits": "Selection requests a service, not a commercial module activation or proof of healthy operation.",
          "example": "webui"
        },
        "nl": {
          "title": "SynthPulse WebUI",
          "purpose": "Chat, agents en beheerst werk in de hoofdinterface voor klanten.",
          "when": "Bij het kiezen van diensten voor een klantinstallatie en controleren of dit onderdeel nodig is.",
          "steps": [
            "Open Modules in de klantwizard.",
            "Selecteer serviceprofiel webui.",
            "Controleer middelen, afhankelijkheden, sleutels en architectuur bij Beoordelen.",
            "Installeer alleen via het goedgekeurde plan en controleer daarna de draaiende dienst."
          ],
          "permissions": "Operators en admins configureren diensten; partners bekijken alleen hun eigen klanten.",
          "limits": "Selectie vraagt een dienst aan en bewijst geen commerciële moduleactivering of gezonde werking.",
          "example": "webui"
        }
      }
    },
    {
      "id": "msp.profile.openwebui",
      "area": "modules",
      "status": "conditional",
      "conditions": [
        "selected_service_profile",
        "deployment_and_credentials"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.profile.openwebui"
      ],
      "source_refs": [
        "apps/cockpit/frontend/src/wizard/StepModules.jsx"
      ],
      "related": [
        "msp.wizard.modules.profiles",
        "msp.module-catalog"
      ],
      "locales": {
        "en": {
          "title": "Additional chat interface",
          "purpose": "An additional team chat service when this deployment includes it.",
          "when": "When selecting services for a client installation and checking whether this component is required.",
          "steps": [
            "Open Modules in the client wizard.",
            "Select the openwebui service profile.",
            "Review resources, dependencies, credentials and architecture in Review.",
            "Deploy only through the approved plan, then verify the running service."
          ],
          "permissions": "Operators and admins configure services; partners only inspect their own clients.",
          "limits": "Selection requests a service, not a commercial module activation or proof of healthy operation.",
          "example": "openwebui"
        },
        "nl": {
          "title": "Extra chatinterface",
          "purpose": "Een extra teamchatdienst als deze installatie die bevat.",
          "when": "Bij het kiezen van diensten voor een klantinstallatie en controleren of dit onderdeel nodig is.",
          "steps": [
            "Open Modules in de klantwizard.",
            "Selecteer serviceprofiel openwebui.",
            "Controleer middelen, afhankelijkheden, sleutels en architectuur bij Beoordelen.",
            "Installeer alleen via het goedgekeurde plan en controleer daarna de draaiende dienst."
          ],
          "permissions": "Operators en admins configureren diensten; partners bekijken alleen hun eigen klanten.",
          "limits": "Selectie vraagt een dienst aan en bewijst geen commerciële moduleactivering of gezonde werking.",
          "example": "openwebui"
        }
      }
    },
    {
      "id": "msp.profile.n8n",
      "area": "modules",
      "status": "conditional",
      "conditions": [
        "selected_service_profile",
        "deployment_and_credentials"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.profile.n8n"
      ],
      "source_refs": [
        "apps/cockpit/frontend/src/wizard/StepModules.jsx"
      ],
      "related": [
        "msp.wizard.modules.profiles",
        "msp.module-catalog"
      ],
      "locales": {
        "en": {
          "title": "Workflow service",
          "purpose": "Run configured automation workflows and their webhooks.",
          "when": "When selecting services for a client installation and checking whether this component is required.",
          "steps": [
            "Open Modules in the client wizard.",
            "Select the n8n service profile.",
            "Review resources, dependencies, credentials and architecture in Review.",
            "Deploy only through the approved plan, then verify the running service."
          ],
          "permissions": "Operators and admins configure services; partners only inspect their own clients.",
          "limits": "Selection requests a service, not a commercial module activation or proof of healthy operation.",
          "example": "n8n"
        },
        "nl": {
          "title": "Workflowdienst",
          "purpose": "Voer ingerichte automatiseringen en hun webhooks uit.",
          "when": "Bij het kiezen van diensten voor een klantinstallatie en controleren of dit onderdeel nodig is.",
          "steps": [
            "Open Modules in de klantwizard.",
            "Selecteer serviceprofiel n8n.",
            "Controleer middelen, afhankelijkheden, sleutels en architectuur bij Beoordelen.",
            "Installeer alleen via het goedgekeurde plan en controleer daarna de draaiende dienst."
          ],
          "permissions": "Operators en admins configureren diensten; partners bekijken alleen hun eigen klanten.",
          "limits": "Selectie vraagt een dienst aan en bewijst geen commerciële moduleactivering of gezonde werking.",
          "example": "n8n"
        }
      }
    },
    {
      "id": "msp.profile.nango",
      "area": "modules",
      "status": "conditional",
      "conditions": [
        "selected_service_profile",
        "deployment_and_credentials"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.profile.nango"
      ],
      "source_refs": [
        "apps/cockpit/frontend/src/wizard/StepModules.jsx"
      ],
      "related": [
        "msp.wizard.modules.profiles",
        "msp.module-catalog"
      ],
      "locales": {
        "en": {
          "title": "Connection service",
          "purpose": "Broker supported OAuth connections after provider applications and callbacks are configured.",
          "when": "When selecting services for a client installation and checking whether this component is required.",
          "steps": [
            "Open Modules in the client wizard.",
            "Select the nango service profile.",
            "Review resources, dependencies, credentials and architecture in Review.",
            "Deploy only through the approved plan, then verify the running service."
          ],
          "permissions": "Operators and admins configure services; partners only inspect their own clients.",
          "limits": "Selection requests a service, not a commercial module activation or proof of healthy operation.",
          "example": "nango"
        },
        "nl": {
          "title": "Verbindingsdienst",
          "purpose": "Beheer ondersteunde OAuth-verbindingen nadat providerapps en callbacks zijn ingericht.",
          "when": "Bij het kiezen van diensten voor een klantinstallatie en controleren of dit onderdeel nodig is.",
          "steps": [
            "Open Modules in de klantwizard.",
            "Selecteer serviceprofiel nango.",
            "Controleer middelen, afhankelijkheden, sleutels en architectuur bij Beoordelen.",
            "Installeer alleen via het goedgekeurde plan en controleer daarna de draaiende dienst."
          ],
          "permissions": "Operators en admins configureren diensten; partners bekijken alleen hun eigen klanten.",
          "limits": "Selectie vraagt een dienst aan en bewijst geen commerciële moduleactivering of gezonde werking.",
          "example": "nango"
        }
      }
    },
    {
      "id": "msp.profile.omniroute",
      "area": "modules",
      "status": "conditional",
      "conditions": [
        "selected_service_profile",
        "deployment_and_credentials"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.profile.omniroute"
      ],
      "source_refs": [
        "apps/cockpit/frontend/src/wizard/StepModules.jsx"
      ],
      "related": [
        "msp.wizard.modules.profiles",
        "msp.module-catalog"
      ],
      "locales": {
        "en": {
          "title": "Model gateway service",
          "purpose": "Route model calls through configured connections and rules.",
          "when": "When selecting services for a client installation and checking whether this component is required.",
          "steps": [
            "Open Modules in the client wizard.",
            "Select the omniroute service profile.",
            "Review resources, dependencies, credentials and architecture in Review.",
            "Deploy only through the approved plan, then verify the running service."
          ],
          "permissions": "Operators and admins configure services; partners only inspect their own clients.",
          "limits": "Selection requests a service, not a commercial module activation or proof of healthy operation.",
          "example": "omniroute"
        },
        "nl": {
          "title": "Modelgatewaydienst",
          "purpose": "Leid modelaanroepen via ingestelde verbindingen en regels.",
          "when": "Bij het kiezen van diensten voor een klantinstallatie en controleren of dit onderdeel nodig is.",
          "steps": [
            "Open Modules in de klantwizard.",
            "Selecteer serviceprofiel omniroute.",
            "Controleer middelen, afhankelijkheden, sleutels en architectuur bij Beoordelen.",
            "Installeer alleen via het goedgekeurde plan en controleer daarna de draaiende dienst."
          ],
          "permissions": "Operators en admins configureren diensten; partners bekijken alleen hun eigen klanten.",
          "limits": "Selectie vraagt een dienst aan en bewijst geen commerciële moduleactivering of gezonde werking.",
          "example": "omniroute"
        }
      }
    },
    {
      "id": "msp.profile.llmproxy",
      "area": "modules",
      "status": "conditional",
      "conditions": [
        "selected_service_profile",
        "deployment_and_credentials"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.profile.llmproxy"
      ],
      "source_refs": [
        "apps/cockpit/frontend/src/wizard/StepModules.jsx"
      ],
      "related": [
        "msp.wizard.modules.profiles",
        "msp.module-catalog"
      ],
      "locales": {
        "en": {
          "title": "Model proxy service",
          "purpose": "Expose the configured model providers through a compatible proxy.",
          "when": "When selecting services for a client installation and checking whether this component is required.",
          "steps": [
            "Open Modules in the client wizard.",
            "Select the llmproxy service profile.",
            "Review resources, dependencies, credentials and architecture in Review.",
            "Deploy only through the approved plan, then verify the running service."
          ],
          "permissions": "Operators and admins configure services; partners only inspect their own clients.",
          "limits": "Selection requests a service, not a commercial module activation or proof of healthy operation.",
          "example": "llmproxy"
        },
        "nl": {
          "title": "Modelproxydienst",
          "purpose": "Maak ingestelde modelaanbieders bereikbaar via een compatibele proxy.",
          "when": "Bij het kiezen van diensten voor een klantinstallatie en controleren of dit onderdeel nodig is.",
          "steps": [
            "Open Modules in de klantwizard.",
            "Selecteer serviceprofiel llmproxy.",
            "Controleer middelen, afhankelijkheden, sleutels en architectuur bij Beoordelen.",
            "Installeer alleen via het goedgekeurde plan en controleer daarna de draaiende dienst."
          ],
          "permissions": "Operators en admins configureren diensten; partners bekijken alleen hun eigen klanten.",
          "limits": "Selectie vraagt een dienst aan en bewijst geen commerciële moduleactivering of gezonde werking.",
          "example": "llmproxy"
        }
      }
    },
    {
      "id": "msp.profile.langfuse",
      "area": "modules",
      "status": "conditional",
      "conditions": [
        "selected_service_profile",
        "deployment_and_credentials"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.profile.langfuse"
      ],
      "source_refs": [
        "apps/cockpit/frontend/src/wizard/StepModules.jsx"
      ],
      "related": [
        "msp.wizard.modules.profiles",
        "msp.module-catalog"
      ],
      "locales": {
        "en": {
          "title": "Model telemetry service",
          "purpose": "Inspect configured model-call metadata and diagnostic traces under the chosen capture policy.",
          "when": "When selecting services for a client installation and checking whether this component is required.",
          "steps": [
            "Open Modules in the client wizard.",
            "Select the langfuse service profile.",
            "Review resources, dependencies, credentials and architecture in Review.",
            "Deploy only through the approved plan, then verify the running service."
          ],
          "permissions": "Operators and admins configure services; partners only inspect their own clients.",
          "limits": "Selection requests a service, not a commercial module activation or proof of healthy operation.",
          "example": "langfuse"
        },
        "nl": {
          "title": "Modeltelemetriedienst",
          "purpose": "Bekijk ingestelde modelmetadata en traces volgens het gekozen opnamebeleid.",
          "when": "Bij het kiezen van diensten voor een klantinstallatie en controleren of dit onderdeel nodig is.",
          "steps": [
            "Open Modules in de klantwizard.",
            "Selecteer serviceprofiel langfuse.",
            "Controleer middelen, afhankelijkheden, sleutels en architectuur bij Beoordelen.",
            "Installeer alleen via het goedgekeurde plan en controleer daarna de draaiende dienst."
          ],
          "permissions": "Operators en admins configureren diensten; partners bekijken alleen hun eigen klanten.",
          "limits": "Selectie vraagt een dienst aan en bewijst geen commerciële moduleactivering of gezonde werking.",
          "example": "langfuse"
        }
      }
    },
    {
      "id": "msp.profile.rag",
      "area": "modules",
      "status": "conditional",
      "conditions": [
        "selected_service_profile",
        "deployment_and_credentials"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.profile.rag"
      ],
      "source_refs": [
        "apps/cockpit/frontend/src/wizard/StepModules.jsx"
      ],
      "related": [
        "msp.wizard.modules.profiles",
        "msp.module-catalog"
      ],
      "locales": {
        "en": {
          "title": "Document retrieval service",
          "purpose": "Prepare document parsing, embedding and retrieval for an approved knowledge setup.",
          "when": "When selecting services for a client installation and checking whether this component is required.",
          "steps": [
            "Open Modules in the client wizard.",
            "Select the rag service profile.",
            "Review resources, dependencies, credentials and architecture in Review.",
            "Deploy only through the approved plan, then verify the running service."
          ],
          "permissions": "Operators and admins configure services; partners only inspect their own clients.",
          "limits": "Selection requests a service, not a commercial module activation or proof of healthy operation.",
          "example": "rag"
        },
        "nl": {
          "title": "Dienst voor documentonderzoek",
          "purpose": "Bereid documentverwerking, vectorisering en zoeken voor een goedgekeurde kennisinrichting voor.",
          "when": "Bij het kiezen van diensten voor een klantinstallatie en controleren of dit onderdeel nodig is.",
          "steps": [
            "Open Modules in de klantwizard.",
            "Selecteer serviceprofiel rag.",
            "Controleer middelen, afhankelijkheden, sleutels en architectuur bij Beoordelen.",
            "Installeer alleen via het goedgekeurde plan en controleer daarna de draaiende dienst."
          ],
          "permissions": "Operators en admins configureren diensten; partners bekijken alleen hun eigen klanten.",
          "limits": "Selectie vraagt een dienst aan en bewijst geen commerciële moduleactivering of gezonde werking.",
          "example": "rag"
        }
      }
    },
    {
      "id": "msp.profile.opendesign",
      "area": "modules",
      "status": "conditional",
      "conditions": [
        "selected_service_profile",
        "deployment_and_credentials"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.profile.opendesign"
      ],
      "source_refs": [
        "apps/cockpit/frontend/src/wizard/StepModules.jsx"
      ],
      "related": [
        "msp.wizard.modules.profiles",
        "msp.module-catalog"
      ],
      "locales": {
        "en": {
          "title": "Design service",
          "purpose": "Prepare the design workspace for supported documents and visual outputs.",
          "when": "When selecting services for a client installation and checking whether this component is required.",
          "steps": [
            "Open Modules in the client wizard.",
            "Select the opendesign service profile.",
            "Review resources, dependencies, credentials and architecture in Review.",
            "Deploy only through the approved plan, then verify the running service."
          ],
          "permissions": "Operators and admins configure services; partners only inspect their own clients.",
          "limits": "Selection requests a service, not a commercial module activation or proof of healthy operation.",
          "example": "opendesign"
        },
        "nl": {
          "title": "Ontwerpdienst",
          "purpose": "Bereid de ontwerpomgeving voor ondersteunde documenten en visuele resultaten voor.",
          "when": "Bij het kiezen van diensten voor een klantinstallatie en controleren of dit onderdeel nodig is.",
          "steps": [
            "Open Modules in de klantwizard.",
            "Selecteer serviceprofiel opendesign.",
            "Controleer middelen, afhankelijkheden, sleutels en architectuur bij Beoordelen.",
            "Installeer alleen via het goedgekeurde plan en controleer daarna de draaiende dienst."
          ],
          "permissions": "Operators en admins configureren diensten; partners bekijken alleen hun eigen klanten.",
          "limits": "Selectie vraagt een dienst aan en bewijst geen commerciële moduleactivering of gezonde werking.",
          "example": "opendesign"
        }
      }
    },
    {
      "id": "msp.profile.opennotebook",
      "area": "modules",
      "status": "conditional",
      "conditions": [
        "selected_service_profile",
        "deployment_and_credentials"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.profile.opennotebook"
      ],
      "source_refs": [
        "apps/cockpit/frontend/src/wizard/StepModules.jsx"
      ],
      "related": [
        "msp.wizard.modules.profiles",
        "msp.module-catalog"
      ],
      "locales": {
        "en": {
          "title": "Research notebook service",
          "purpose": "Prepare a source-based research workspace on supported hardware.",
          "when": "When selecting services for a client installation and checking whether this component is required.",
          "steps": [
            "Open Modules in the client wizard.",
            "Select the opennotebook service profile.",
            "Review resources, dependencies, credentials and architecture in Review.",
            "Deploy only through the approved plan, then verify the running service."
          ],
          "permissions": "Operators and admins configure services; partners only inspect their own clients.",
          "limits": "Selection requests a service, not a commercial module activation or proof of healthy operation. OpenNotebook is currently amd64-only.",
          "example": "opennotebook"
        },
        "nl": {
          "title": "Onderzoeksnotitieboekdienst",
          "purpose": "Bereid een brongebaseerde onderzoeksomgeving voor op ondersteunde hardware.",
          "when": "Bij het kiezen van diensten voor een klantinstallatie en controleren of dit onderdeel nodig is.",
          "steps": [
            "Open Modules in de klantwizard.",
            "Selecteer serviceprofiel opennotebook.",
            "Controleer middelen, afhankelijkheden, sleutels en architectuur bij Beoordelen.",
            "Installeer alleen via het goedgekeurde plan en controleer daarna de draaiende dienst."
          ],
          "permissions": "Operators en admins configureren diensten; partners bekijken alleen hun eigen klanten.",
          "limits": "Selectie vraagt een dienst aan en bewijst geen commerciële moduleactivering of gezonde werking. OpenNotebook ondersteunt momenteel alleen amd64.",
          "example": "opennotebook"
        }
      }
    },
    {
      "id": "msp.profile.opencode",
      "area": "modules",
      "status": "conditional",
      "conditions": [
        "selected_service_profile",
        "deployment_and_credentials"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.profile.opencode"
      ],
      "source_refs": [
        "apps/cockpit/frontend/src/wizard/StepModules.jsx"
      ],
      "related": [
        "msp.wizard.modules.profiles",
        "msp.module-catalog"
      ],
      "locales": {
        "en": {
          "title": "Coding workspace",
          "purpose": "Prepare the optional coding workspace and its separately configured model access.",
          "when": "When selecting services for a client installation and checking whether this component is required.",
          "steps": [
            "Open Modules in the client wizard.",
            "Select the opencode service profile.",
            "Review resources, dependencies, credentials and architecture in Review.",
            "Deploy only through the approved plan, then verify the running service."
          ],
          "permissions": "Operators and admins configure services; partners only inspect their own clients.",
          "limits": "Selection requests a service, not a commercial module activation or proof of healthy operation.",
          "example": "opencode"
        },
        "nl": {
          "title": "Codeeromgeving",
          "purpose": "Bereid de optionele codeeromgeving en de apart ingestelde modeltoegang voor.",
          "when": "Bij het kiezen van diensten voor een klantinstallatie en controleren of dit onderdeel nodig is.",
          "steps": [
            "Open Modules in de klantwizard.",
            "Selecteer serviceprofiel opencode.",
            "Controleer middelen, afhankelijkheden, sleutels en architectuur bij Beoordelen.",
            "Installeer alleen via het goedgekeurde plan en controleer daarna de draaiende dienst."
          ],
          "permissions": "Operators en admins configureren diensten; partners bekijken alleen hun eigen klanten.",
          "limits": "Selectie vraagt een dienst aan en bewijst geen commerciële moduleactivering of gezonde werking.",
          "example": "opencode"
        }
      }
    },
    {
      "id": "msp.profile.pgdb",
      "area": "modules",
      "status": "conditional",
      "conditions": [
        "selected_service_profile",
        "deployment_and_credentials"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.profile.pgdb"
      ],
      "source_refs": [
        "apps/cockpit/frontend/src/wizard/StepModules.jsx"
      ],
      "related": [
        "msp.wizard.modules.profiles",
        "msp.module-catalog"
      ],
      "locales": {
        "en": {
          "title": "Bundled PostgreSQL",
          "purpose": "Supply database storage for services that use the bundled database.",
          "when": "When selecting services for a client installation and checking whether this component is required.",
          "steps": [
            "Open Modules in the client wizard.",
            "Select the pgdb service profile.",
            "Review resources, dependencies, credentials and architecture in Review.",
            "Deploy only through the approved plan, then verify the running service."
          ],
          "permissions": "Operators and admins configure services; partners only inspect their own clients.",
          "limits": "Selection requests a service, not a commercial module activation or proof of healthy operation.",
          "example": "pgdb"
        },
        "nl": {
          "title": "Meegeleverde PostgreSQL",
          "purpose": "Lever databaseopslag voor diensten die de meegeleverde database gebruiken.",
          "when": "Bij het kiezen van diensten voor een klantinstallatie en controleren of dit onderdeel nodig is.",
          "steps": [
            "Open Modules in de klantwizard.",
            "Selecteer serviceprofiel pgdb.",
            "Controleer middelen, afhankelijkheden, sleutels en architectuur bij Beoordelen.",
            "Installeer alleen via het goedgekeurde plan en controleer daarna de draaiende dienst."
          ],
          "permissions": "Operators en admins configureren diensten; partners bekijken alleen hun eigen klanten.",
          "limits": "Selectie vraagt een dienst aan en bewijst geen commerciële moduleactivering of gezonde werking.",
          "example": "pgdb"
        }
      }
    },
    {
      "id": "msp.profile.swarm",
      "area": "modules",
      "status": "conditional",
      "conditions": [
        "selected_service_profile",
        "deployment_and_credentials"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.profile.swarm"
      ],
      "source_refs": [
        "apps/cockpit/frontend/src/wizard/StepModules.jsx"
      ],
      "related": [
        "msp.wizard.modules.profiles",
        "msp.module-catalog"
      ],
      "locales": {
        "en": {
          "title": "Multi-agent runner",
          "purpose": "Prepare the optional runner for supported coordinated agent work.",
          "when": "When selecting services for a client installation and checking whether this component is required.",
          "steps": [
            "Open Modules in the client wizard.",
            "Select the swarm service profile.",
            "Review resources, dependencies, credentials and architecture in Review.",
            "Deploy only through the approved plan, then verify the running service."
          ],
          "permissions": "Operators and admins configure services; partners only inspect their own clients.",
          "limits": "Selection requests a service, not a commercial module activation or proof of healthy operation.",
          "example": "swarm"
        },
        "nl": {
          "title": "Runner voor meerdere agents",
          "purpose": "Bereid de optionele runner voor ondersteund werk met meerdere agents voor.",
          "when": "Bij het kiezen van diensten voor een klantinstallatie en controleren of dit onderdeel nodig is.",
          "steps": [
            "Open Modules in de klantwizard.",
            "Selecteer serviceprofiel swarm.",
            "Controleer middelen, afhankelijkheden, sleutels en architectuur bij Beoordelen.",
            "Installeer alleen via het goedgekeurde plan en controleer daarna de draaiende dienst."
          ],
          "permissions": "Operators en admins configureren diensten; partners bekijken alleen hun eigen klanten.",
          "limits": "Selectie vraagt een dienst aan en bewijst geen commerciële moduleactivering of gezonde werking.",
          "example": "swarm"
        }
      }
    },
    {
      "id": "msp.profile.ingress",
      "area": "modules",
      "status": "conditional",
      "conditions": [
        "selected_service_profile",
        "deployment_and_credentials"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.profile.ingress"
      ],
      "source_refs": [
        "apps/cockpit/frontend/src/wizard/StepModules.jsx"
      ],
      "related": [
        "msp.wizard.modules.profiles",
        "msp.module-catalog"
      ],
      "locales": {
        "en": {
          "title": "HTTPS ingress",
          "purpose": "Terminate HTTPS and route public application domains when configured.",
          "when": "When selecting services for a client installation and checking whether this component is required.",
          "steps": [
            "Open Modules in the client wizard.",
            "Select the ingress service profile.",
            "Review resources, dependencies, credentials and architecture in Review.",
            "Deploy only through the approved plan, then verify the running service."
          ],
          "permissions": "Operators and admins configure services; partners only inspect their own clients.",
          "limits": "Selection requests a service, not a commercial module activation or proof of healthy operation.",
          "example": "ingress"
        },
        "nl": {
          "title": "HTTPS-toegang",
          "purpose": "Handel HTTPS en publieke applicatiedomeinen af als die zijn ingesteld.",
          "when": "Bij het kiezen van diensten voor een klantinstallatie en controleren of dit onderdeel nodig is.",
          "steps": [
            "Open Modules in de klantwizard.",
            "Selecteer serviceprofiel ingress.",
            "Controleer middelen, afhankelijkheden, sleutels en architectuur bij Beoordelen.",
            "Installeer alleen via het goedgekeurde plan en controleer daarna de draaiende dienst."
          ],
          "permissions": "Operators en admins configureren diensten; partners bekijken alleen hun eigen klanten.",
          "limits": "Selectie vraagt een dienst aan en bewijst geen commerciële moduleactivering of gezonde werking.",
          "example": "ingress"
        }
      }
    },
    {
      "id": "msp.profile.cloudflared",
      "area": "modules",
      "status": "conditional",
      "conditions": [
        "selected_service_profile",
        "deployment_and_credentials"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.profile.cloudflared"
      ],
      "source_refs": [
        "apps/cockpit/frontend/src/wizard/StepModules.jsx"
      ],
      "related": [
        "msp.wizard.modules.profiles",
        "msp.module-catalog"
      ],
      "locales": {
        "en": {
          "title": "Optional network tunnel",
          "purpose": "Prepare a separately authorised tunnel route when the deployment requires it.",
          "when": "When selecting services for a client installation and checking whether this component is required.",
          "steps": [
            "Open Modules in the client wizard.",
            "Select the cloudflared service profile.",
            "Review resources, dependencies, credentials and architecture in Review.",
            "Deploy only through the approved plan, then verify the running service."
          ],
          "permissions": "Operators and admins configure services; partners only inspect their own clients.",
          "limits": "Selection requests a service, not a commercial module activation or proof of healthy operation.",
          "example": "cloudflared"
        },
        "nl": {
          "title": "Optionele netwerktunnel",
          "purpose": "Bereid een afzonderlijk goedgekeurde tunnelroute voor als de installatie deze vereist.",
          "when": "Bij het kiezen van diensten voor een klantinstallatie en controleren of dit onderdeel nodig is.",
          "steps": [
            "Open Modules in de klantwizard.",
            "Selecteer serviceprofiel cloudflared.",
            "Controleer middelen, afhankelijkheden, sleutels en architectuur bij Beoordelen.",
            "Installeer alleen via het goedgekeurde plan en controleer daarna de draaiende dienst."
          ],
          "permissions": "Operators en admins configureren diensten; partners bekijken alleen hun eigen klanten.",
          "limits": "Selectie vraagt een dienst aan en bewijst geen commerciële moduleactivering of gezonde werking.",
          "example": "cloudflared"
        }
      }
    },
    {
      "id": "msp.module.workspace",
      "area": "modules",
      "status": "conditional",
      "conditions": [
        "catalogue_record",
        "runtime_and_entitlement_review"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.module.workspace"
      ],
      "source_refs": [
        "modules/catalog.json"
      ],
      "related": [
        "msp.module-catalog",
        "msp.module-activation",
        "msp.backups"
      ],
      "locales": {
        "en": {
          "title": "Workspace and AI assistants",
          "purpose": "Chat, assistants, projects, scheduled tasks, skills and memory form the main team workspace.",
          "when": "When assessing this module for an installation or explaining its prerequisites to a client.",
          "steps": [
            "Check the module’s lifecycle, supported architecture, hosting and dependencies.",
            "Verify the contract and the actual runtime implementation before promising activation.",
            "Use an isolated acceptance check for access, health, data handling and backup.",
            "Record what is ready and what remains unavailable."
          ],
          "permissions": "Operators assess technical readiness; admins review contractual entitlement. End-user access follows the installed application’s policy.",
          "limits": "Verify identity, model routing and data isolation for each person. Optional document tools and live-office capabilities have separate readiness requirements.",
          "example": "A colleague starts an authorised chat in the workspace."
        },
        "nl": {
          "title": "Werkplek en AI-medewerkers",
          "purpose": "Chat, AI-medewerkers, projecten, geplande taken, vaardigheden en geheugen vormen de centrale teamwerkplek.",
          "when": "Bij het beoordelen van deze module voor een installatie of het uitleggen van de voorwaarden aan een klant.",
          "steps": [
            "Controleer levenscyclus, architectuur, hosting en afhankelijkheden van de module.",
            "Controleer contract en werkelijke implementatie voordat je activering toezegt.",
            "Gebruik een afgeschermde acceptatiecontrole voor toegang, gezondheid, gegevensverwerking en back-up.",
            "Leg vast wat gereed is en wat nog niet beschikbaar is."
          ],
          "permissions": "Operators beoordelen technische gereedheid; admins beoordelen contractrechten. Gebruikerstoegang volgt het beleid van de geïnstalleerde app.",
          "limits": "Controleer identiteit, modelroutering en gegevensafscherming per persoon. Optionele documenttools en kantoorfuncties hebben aparte voorwaarden.",
          "example": "Een collega start een toegestaan gesprek in de werkplek."
        }
      }
    },
    {
      "id": "msp.module.group_chat",
      "area": "modules",
      "status": "conditional",
      "conditions": [
        "catalogue_record",
        "runtime_and_entitlement_review"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.module.group_chat"
      ],
      "source_refs": [
        "modules/catalog.json"
      ],
      "related": [
        "msp.module-catalog",
        "msp.module-activation",
        "msp.backups"
      ],
      "locales": {
        "en": {
          "title": "Group chats with AI assistants",
          "purpose": "Colleagues and assistants can participate in shared conversations through supported workspace or messaging routes.",
          "when": "When assessing this module for an installation or explaining its prerequisites to a client.",
          "steps": [
            "Check the module’s lifecycle, supported architecture, hosting and dependencies.",
            "Verify the contract and the actual runtime implementation before promising activation.",
            "Use an isolated acceptance check for access, health, data handling and backup.",
            "Record what is ready and what remains unavailable."
          ],
          "permissions": "Operators assess technical readiness; admins review contractual entitlement. End-user access follows the installed application’s policy.",
          "limits": "Requires workspace access. Each external channel needs its own adapter, identity mapping and permissions. A group conversation does not grant new tool rights.",
          "example": "An approved project group discusses a task with an assistant."
        },
        "nl": {
          "title": "Groepsgesprekken met AI-medewerkers",
          "purpose": "Collega’s en AI-medewerkers kunnen via ondersteunde werkplek- of berichtenroutes aan gedeelde gesprekken deelnemen.",
          "when": "Bij het beoordelen van deze module voor een installatie of het uitleggen van de voorwaarden aan een klant.",
          "steps": [
            "Controleer levenscyclus, architectuur, hosting en afhankelijkheden van de module.",
            "Controleer contract en werkelijke implementatie voordat je activering toezegt.",
            "Gebruik een afgeschermde acceptatiecontrole voor toegang, gezondheid, gegevensverwerking en back-up.",
            "Leg vast wat gereed is en wat nog niet beschikbaar is."
          ],
          "permissions": "Operators beoordelen technische gereedheid; admins beoordelen contractrechten. Gebruikerstoegang volgt het beleid van de geïnstalleerde app.",
          "limits": "Werkplektoegang is nodig. Elk extern kanaal vraagt een adapter, persoonskoppeling en rechten. Een groepsgesprek verleent geen extra toolrechten.",
          "example": "Een goedgekeurde projectgroep bespreekt een taak met een AI-medewerker."
        }
      }
    },
    {
      "id": "msp.module.design_studio",
      "area": "modules",
      "status": "conditional",
      "conditions": [
        "catalogue_record",
        "runtime_and_entitlement_review"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.module.design_studio"
      ],
      "source_refs": [
        "modules/catalog.json"
      ],
      "related": [
        "msp.module-catalog",
        "msp.module-activation",
        "msp.backups"
      ],
      "locales": {
        "en": {
          "title": "Design studio",
          "purpose": "Prepare documents, presentations and visuals in the organisation’s house style.",
          "when": "When assessing this module for an installation or explaining its prerequisites to a client.",
          "steps": [
            "Check the module’s lifecycle, supported architecture, hosting and dependencies.",
            "Verify the contract and the actual runtime implementation before promising activation.",
            "Use an isolated acceptance check for access, health, data handling and backup.",
            "Record what is ready and what remains unavailable."
          ],
          "permissions": "Operators assess technical readiness; admins review contractual entitlement. End-user access follows the installed application’s policy.",
          "limits": "Requires the design service, brand assets and approved model or image routes. Verify generated content before sharing.",
          "example": "Draft a branded proposal for internal review."
        },
        "nl": {
          "title": "Ontwerpstudio",
          "purpose": "Maak documenten, presentaties en afbeeldingen in de huisstijl van de organisatie.",
          "when": "Bij het beoordelen van deze module voor een installatie of het uitleggen van de voorwaarden aan een klant.",
          "steps": [
            "Controleer levenscyclus, architectuur, hosting en afhankelijkheden van de module.",
            "Controleer contract en werkelijke implementatie voordat je activering toezegt.",
            "Gebruik een afgeschermde acceptatiecontrole voor toegang, gezondheid, gegevensverwerking en back-up.",
            "Leg vast wat gereed is en wat nog niet beschikbaar is."
          ],
          "permissions": "Operators beoordelen technische gereedheid; admins beoordelen contractrechten. Gebruikerstoegang volgt het beleid van de geïnstalleerde app.",
          "limits": "De ontwerpdienst, huisstijlbestanden en goedgekeurde model- of afbeeldingsroutes zijn nodig. Controleer gegenereerde inhoud voordat je deelt.",
          "example": "Maak een offerteconcept in huisstijl voor interne beoordeling."
        }
      }
    },
    {
      "id": "msp.module.workflows",
      "area": "modules",
      "status": "conditional",
      "conditions": [
        "catalogue_record",
        "runtime_and_entitlement_review"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.module.workflows"
      ],
      "source_refs": [
        "modules/catalog.json"
      ],
      "related": [
        "msp.module-catalog",
        "msp.module-activation",
        "msp.backups"
      ],
      "locales": {
        "en": {
          "title": "Workflows",
          "purpose": "Run configured processes between approved business systems. Operators maintain the workflow and its credentials.",
          "when": "When assessing this module for an installation or explaining its prerequisites to a client.",
          "steps": [
            "Check the module’s lifecycle, supported architecture, hosting and dependencies.",
            "Verify the contract and the actual runtime implementation before promising activation.",
            "Use an isolated acceptance check for access, health, data handling and backup.",
            "Record what is ready and what remains unavailable."
          ],
          "permissions": "Operators assess technical readiness; admins review contractual entitlement. End-user access follows the installed application’s policy.",
          "limits": "Catalogue availability does not settle managed-hosting licence or sales approval. Editor access, credentials and each workflow’s side effects require separate configuration.",
          "example": "Validate a test workflow with synthetic input before scheduling it."
        },
        "nl": {
          "title": "Workflows",
          "purpose": "Voer ingerichte processen uit tussen goedgekeurde bedrijfssystemen. Beheerders onderhouden de workflow en de sleutels.",
          "when": "Bij het beoordelen van deze module voor een installatie of het uitleggen van de voorwaarden aan een klant.",
          "steps": [
            "Controleer levenscyclus, architectuur, hosting en afhankelijkheden van de module.",
            "Controleer contract en werkelijke implementatie voordat je activering toezegt.",
            "Gebruik een afgeschermde acceptatiecontrole voor toegang, gezondheid, gegevensverwerking en back-up.",
            "Leg vast wat gereed is en wat nog niet beschikbaar is."
          ],
          "permissions": "Operators beoordelen technische gereedheid; admins beoordelen contractrechten. Gebruikerstoegang volgt het beleid van de geïnstalleerde app.",
          "limits": "Catalogusbeschikbaarheid beslist niet over hostinglicentie of verkoopgoedkeuring. Editortoegang, sleutels en externe effecten vragen per workflow aparte inrichting.",
          "example": "Valideer een testworkflow met fictieve invoer voordat je deze plant."
        }
      }
    },
    {
      "id": "msp.module.knowledge_base",
      "area": "modules",
      "status": "conditional",
      "conditions": [
        "catalogue_record",
        "runtime_and_entitlement_review",
        "pilot_not_confirmed"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.module.knowledge_base"
      ],
      "source_refs": [
        "modules/catalog.json"
      ],
      "related": [
        "msp.module-catalog",
        "msp.module-activation",
        "msp.backups"
      ],
      "locales": {
        "en": {
          "title": "Knowledge base on your own documents",
          "purpose": "The pilot aims to answer questions using organisation documents and source references.",
          "when": "When assessing this module for an installation or explaining its prerequisites to a client.",
          "steps": [
            "Check the module’s lifecycle, supported architecture, hosting and dependencies.",
            "Verify the contract and the actual runtime implementation before promising activation.",
            "Use an isolated acceptance check for access, health, data handling and backup.",
            "Record what is ready and what remains unavailable."
          ],
          "permissions": "Operators assess technical readiness; admins review contractual entitlement. End-user access follows the installed application’s policy.",
          "limits": "Pilot, not confirmed for general activation. Requires amd64, workspace, document access rules and substantial capacity. Azure placement requires a companion. Back up source records; the search index can be rebuilt.",
          "example": "Assess a small approved test document collection."
        },
        "nl": {
          "title": "Kennisbank op je eigen documenten",
          "purpose": "De pilot is bedoeld om vragen te beantwoorden met organisatiedocumenten en bronverwijzingen.",
          "when": "Bij het beoordelen van deze module voor een installatie of het uitleggen van de voorwaarden aan een klant.",
          "steps": [
            "Controleer levenscyclus, architectuur, hosting en afhankelijkheden van de module.",
            "Controleer contract en werkelijke implementatie voordat je activering toezegt.",
            "Gebruik een afgeschermde acceptatiecontrole voor toegang, gezondheid, gegevensverwerking en back-up.",
            "Leg vast wat gereed is en wat nog niet beschikbaar is."
          ],
          "permissions": "Operators beoordelen technische gereedheid; admins beoordelen contractrechten. Gebruikerstoegang volgt het beleid van de geïnstalleerde app.",
          "limits": "Pilot, niet bevestigd voor algemene activering. Vereist amd64, werkplek, documentrechten en ruime capaciteit. Op Azure is een extra servicemachine nodig. Bewaar brongegevens; de zoekindex kan opnieuw worden opgebouwd.",
          "example": "Beoordeel een kleine, goedgekeurde verzameling testdocumenten."
        }
      }
    },
    {
      "id": "msp.module.notebook",
      "area": "modules",
      "status": "conditional",
      "conditions": [
        "catalogue_record",
        "runtime_and_entitlement_review",
        "pilot_not_confirmed"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.module.notebook"
      ],
      "source_refs": [
        "modules/catalog.json"
      ],
      "related": [
        "msp.module-catalog",
        "msp.module-activation",
        "msp.backups"
      ],
      "locales": {
        "en": {
          "title": "Research notebook",
          "purpose": "The pilot collects research sources and notes and can prepare summaries, including audio where configured.",
          "when": "When assessing this module for an installation or explaining its prerequisites to a client.",
          "steps": [
            "Check the module’s lifecycle, supported architecture, hosting and dependencies.",
            "Verify the contract and the actual runtime implementation before promising activation.",
            "Use an isolated acceptance check for access, health, data handling and backup.",
            "Record what is ready and what remains unavailable."
          ],
          "permissions": "Operators assess technical readiness; admins review contractual entitlement. End-user access follows the installed application’s policy.",
          "limits": "Pilot, not confirmed for general activation. Requires amd64 and a verified SSO front before client use. Audio routes and data handling need separate checks.",
          "example": "Evaluate a research notebook using public test sources."
        },
        "nl": {
          "title": "Onderzoeksnotitieboek",
          "purpose": "De pilot verzamelt onderzoeksbronnen en notities en kan samenvattingen maken, ook als audio waar dat is ingericht.",
          "when": "Bij het beoordelen van deze module voor een installatie of het uitleggen van de voorwaarden aan een klant.",
          "steps": [
            "Controleer levenscyclus, architectuur, hosting en afhankelijkheden van de module.",
            "Controleer contract en werkelijke implementatie voordat je activering toezegt.",
            "Gebruik een afgeschermde acceptatiecontrole voor toegang, gezondheid, gegevensverwerking en back-up.",
            "Leg vast wat gereed is en wat nog niet beschikbaar is."
          ],
          "permissions": "Operators beoordelen technische gereedheid; admins beoordelen contractrechten. Gebruikerstoegang volgt het beleid van de geïnstalleerde app.",
          "limits": "Pilot, niet bevestigd voor algemene activering. Vereist amd64 en een gecontroleerde SSO-ingang vóór klantgebruik. Audioroutes en gegevensverwerking vragen aparte controles.",
          "example": "Evalueer een onderzoeksnotitieboek met publieke testbronnen."
        }
      }
    },
    {
      "id": "msp.module.e_signing",
      "area": "modules",
      "status": "conditional",
      "conditions": [
        "catalogue_record",
        "runtime_and_entitlement_review",
        "pilot_not_confirmed"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.module.e_signing"
      ],
      "source_refs": [
        "modules/catalog.json"
      ],
      "related": [
        "msp.module-catalog",
        "msp.module-activation",
        "msp.backups"
      ],
      "locales": {
        "en": {
          "title": "Digital signing",
          "purpose": "The pilot supports document signing and a signing record through a separately configured signing service.",
          "when": "When assessing this module for an installation or explaining its prerequisites to a client.",
          "steps": [
            "Check the module’s lifecycle, supported architecture, hosting and dependencies.",
            "Verify the contract and the actual runtime implementation before promising activation.",
            "Use an isolated acceptance check for access, health, data handling and backup.",
            "Record what is ready and what remains unavailable."
          ],
          "permissions": "Operators assess technical readiness; admins review contractual entitlement. End-user access follows the installed application’s policy.",
          "limits": "Pilot, not confirmed for general activation. Requires a public HTTPS signing host and mail route. On-premise publishing belongs to the client. Signed documents are legal records, not disposable operational telemetry.",
          "example": "Review the signing flow with a clearly marked test document."
        },
        "nl": {
          "title": "Digitaal ondertekenen",
          "purpose": "De pilot ondersteunt documentondertekening en een ondertekeningsverslag via een apart ingerichte ondertekendienst.",
          "when": "Bij het beoordelen van deze module voor een installatie of het uitleggen van de voorwaarden aan een klant.",
          "steps": [
            "Controleer levenscyclus, architectuur, hosting en afhankelijkheden van de module.",
            "Controleer contract en werkelijke implementatie voordat je activering toezegt.",
            "Gebruik een afgeschermde acceptatiecontrole voor toegang, gezondheid, gegevensverwerking en back-up.",
            "Leg vast wat gereed is en wat nog niet beschikbaar is."
          ],
          "permissions": "Operators beoordelen technische gereedheid; admins beoordelen contractrechten. Gebruikerstoegang volgt het beleid van de geïnstalleerde app.",
          "limits": "Pilot, niet bevestigd voor algemene activering. Vereist een publieke HTTPS-ondertekenhost en mailroute. Publicatie op eigen locatie valt onder de klant. Ondertekende documenten zijn juridische stukken, geen tijdelijke beheertelemetrie.",
          "example": "Beoordeel het ondertekenproces met een duidelijk gemarkeerd testdocument."
        }
      }
    },
    {
      "id": "msp.module.dictation",
      "area": "modules",
      "status": "conditional",
      "conditions": [
        "catalogue_record",
        "runtime_and_entitlement_review",
        "pilot_not_confirmed"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.module.dictation"
      ],
      "source_refs": [
        "modules/catalog.json"
      ],
      "related": [
        "msp.module-catalog",
        "msp.module-activation",
        "msp.backups"
      ],
      "locales": {
        "en": {
          "title": "Dictation in every application",
          "purpose": "The pilot aims to turn speech on a managed laptop into text in the chosen application.",
          "when": "When assessing this module for an installation or explaining its prerequisites to a client.",
          "steps": [
            "Check the module’s lifecycle, supported architecture, hosting and dependencies.",
            "Verify the contract and the actual runtime implementation before promising activation.",
            "Use an isolated acceptance check for access, health, data handling and backup.",
            "Record what is ready and what remains unavailable."
          ],
          "permissions": "Operators assess technical readiness; admins review contractual entitlement. End-user access follows the installed application’s policy.",
          "limits": "Pilot with a planned shared speech profile. Device rollout, supported architecture and an approved speech route must be verified. EU processing and non-retention are requirements to prove, not consequences of selecting the module.",
          "example": "Assess dictation with non-sensitive sample speech."
        },
        "nl": {
          "title": "Dicteren in elke applicatie",
          "purpose": "De pilot is bedoeld om spraak op een beheerde laptop om te zetten naar tekst in de gekozen applicatie.",
          "when": "Bij het beoordelen van deze module voor een installatie of het uitleggen van de voorwaarden aan een klant.",
          "steps": [
            "Controleer levenscyclus, architectuur, hosting en afhankelijkheden van de module.",
            "Controleer contract en werkelijke implementatie voordat je activering toezegt.",
            "Gebruik een afgeschermde acceptatiecontrole voor toegang, gezondheid, gegevensverwerking en back-up.",
            "Leg vast wat gereed is en wat nog niet beschikbaar is."
          ],
          "permissions": "Operators beoordelen technische gereedheid; admins beoordelen contractrechten. Gebruikerstoegang volgt het beleid van de geïnstalleerde app.",
          "limits": "Pilot met een gepland gedeeld spraakprofiel. Apparaatuitrol, geschikte architectuur en een goedgekeurde spraakroute moeten worden gecontroleerd. EU-verwerking en niet bewaren zijn te bewijzen eisen, geen gevolg van het aanvinken van de module.",
          "example": "Beoordeel dicteren met niet-gevoelige voorbeeldspraak."
        }
      }
    },
    {
      "id": "msp.module.meeting_notes",
      "area": "modules",
      "status": "conditional",
      "conditions": [
        "catalogue_record",
        "runtime_and_entitlement_review",
        "pilot_not_confirmed"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.module.meeting_notes"
      ],
      "source_refs": [
        "modules/catalog.json"
      ],
      "related": [
        "msp.module-catalog",
        "msp.module-activation",
        "msp.backups"
      ],
      "locales": {
        "en": {
          "title": "Meeting notes",
          "purpose": "The pilot prepares minutes, decisions and actions from supported meeting recordings or transcripts.",
          "when": "When assessing this module for an installation or explaining its prerequisites to a client.",
          "steps": [
            "Check the module’s lifecycle, supported architecture, hosting and dependencies.",
            "Verify the contract and the actual runtime implementation before promising activation.",
            "Use an isolated acceptance check for access, health, data handling and backup.",
            "Record what is ready and what remains unavailable."
          ],
          "permissions": "Operators assess technical readiness; admins review contractual entitlement. End-user access follows the installed application’s policy.",
          "limits": "Pilot, not confirmed for general activation. Desktop platforms, recording notice, storage and summary routing require review. Shared speech and upload routes have their own readiness status.",
          "example": "Review a synthetic meeting transcript and correct the draft actions."
        },
        "nl": {
          "title": "Vergaderverslagen",
          "purpose": "De pilot maakt verslagen, besluiten en acties van ondersteunde vergaderopnamen of transcripties.",
          "when": "Bij het beoordelen van deze module voor een installatie of het uitleggen van de voorwaarden aan een klant.",
          "steps": [
            "Controleer levenscyclus, architectuur, hosting en afhankelijkheden van de module.",
            "Controleer contract en werkelijke implementatie voordat je activering toezegt.",
            "Gebruik een afgeschermde acceptatiecontrole voor toegang, gezondheid, gegevensverwerking en back-up.",
            "Leg vast wat gereed is en wat nog niet beschikbaar is."
          ],
          "permissions": "Operators beoordelen technische gereedheid; admins beoordelen contractrechten. Gebruikerstoegang volgt het beleid van de geïnstalleerde app.",
          "limits": "Pilot, niet bevestigd voor algemene activering. Desktopplatforms, opnamekennisgeving, opslag en samenvattingsroute vragen beoordeling. Gedeelde spraak- en uploadroutes hebben een eigen gereedheidsstatus.",
          "example": "Beoordeel een fictief vergadertranscript en corrigeer de conceptacties."
        }
      }
    },
    {
      "id": "msp.module.office_apps",
      "area": "modules",
      "status": "conditional",
      "conditions": [
        "catalogue_record",
        "runtime_and_entitlement_review",
        "pilot_not_confirmed"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.module.office_apps"
      ],
      "source_refs": [
        "modules/catalog.json"
      ],
      "related": [
        "msp.module-catalog",
        "msp.module-activation",
        "msp.backups"
      ],
      "locales": {
        "en": {
          "title": "Office apps with AI",
          "purpose": "The pilot aims to edit office documents on a managed laptop with the organisation’s own AI route.",
          "when": "When assessing this module for an installation or explaining its prerequisites to a client.",
          "steps": [
            "Check the module’s lifecycle, supported architecture, hosting and dependencies.",
            "Verify the contract and the actual runtime implementation before promising activation.",
            "Use an isolated acceptance check for access, health, data handling and backup.",
            "Record what is ready and what remains unavailable."
          ],
          "permissions": "Operators assess technical readiness; admins review contractual entitlement. End-user access follows the installed application’s policy.",
          "limits": "Pilot, not confirmed for general activation. The signed application build and supported platforms still need validation. Per-user gateway keys, restricted external routes and device-managed document protection are prerequisites.",
          "example": "Evaluate a sample spreadsheet on an isolated test laptop."
        },
        "nl": {
          "title": "Kantoorprogramma's met AI",
          "purpose": "De pilot is bedoeld om kantoordocumenten op een beheerde laptop te bewerken via de eigen AI-route van de organisatie.",
          "when": "Bij het beoordelen van deze module voor een installatie of het uitleggen van de voorwaarden aan een klant.",
          "steps": [
            "Controleer levenscyclus, architectuur, hosting en afhankelijkheden van de module.",
            "Controleer contract en werkelijke implementatie voordat je activering toezegt.",
            "Gebruik een afgeschermde acceptatiecontrole voor toegang, gezondheid, gegevensverwerking en back-up.",
            "Leg vast wat gereed is en wat nog niet beschikbaar is."
          ],
          "permissions": "Operators beoordelen technische gereedheid; admins beoordelen contractrechten. Gebruikerstoegang volgt het beleid van de geïnstalleerde app.",
          "limits": "Pilot, niet bevestigd voor algemene activering. De ondertekende appversie en ondersteunde platforms moeten nog worden gevalideerd. Persoonlijke gatewaysleutels, beperkte externe routes en documentbescherming via apparaatbeheer zijn voorwaarden.",
          "example": "Evalueer een voorbeeldspreadsheet op een afgeschermde testlaptop."
        }
      }
    },
    {
      "id": "msp.retention",
      "area": "operations",
      "status": "conditional",
      "conditions": [
        "deployed_migrations",
        "installed_retention_timer"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.retention"
      ],
      "source_refs": [
        "apps/cockpit/docs/OPERATIONAL-RETENTION.md"
      ],
      "related": [
        "msp.telemetry",
        "msp.heartbeat",
        "msp.issues"
      ],
      "locales": {
        "en": {
          "title": "Operational retention",
          "purpose": "Remove expired health metadata on an independent schedule, including during quiet periods.",
          "when": "When reviewing data retention or preparing the operational maintenance timer.",
          "steps": [
            "Through authorised host operations, run the retention command without --apply and review its counts.",
            "Check the configured raw-event period and the proposed cutoffs.",
            "After deploying migrations, install the prepared hourly service and timer through the release process.",
            "Inspect deleted and remaining counts; repeat bounded runs if a backlog remains."
          ],
          "permissions": "Dedicated control-service user through authorised host administration. No cockpit button or installation credential can start the sweep.",
          "limits": "Raw events default to 30 days, configurable from 1 to 90; heartbeats 7 days; resolved or muted issues 6 calendar months. Other issue states remain. This does not implement ticket, fiscal or audit retention. A prepared timer is not evidence it has been enabled.",
          "example": "An inactive installation’s old heartbeat history expires even when it sends no new events."
        },
        "nl": {
          "title": "Operationele bewaartermijnen",
          "purpose": "Verwijder verlopen gezondheidsmetadata volgens een onafhankelijk schema, ook tijdens stille periodes.",
          "when": "Bij het beoordelen van bewaartermijnen of voorbereiden van de beheertimer.",
          "steps": [
            "Voer via bevoegd hostbeheer het bewaartermijncommando zonder --apply uit en beoordeel de aantallen.",
            "Controleer de ingestelde bewaartermijn voor ruwe meldingen en de voorgestelde grensdatums.",
            "Installeer na de databasemigraties de voorbereide uurlijkse dienst en timer via het releaseproces.",
            "Bekijk verwijderde en resterende aantallen; herhaal begrensde runs bij een achterstand."
          ],
          "permissions": "De eigen control-servicegebruiker via bevoegd hostbeheer. Geen cockpitknop of installatiesleutel kan deze opschoning starten.",
          "limits": "Ruwe meldingen standaard 30 dagen, instelbaar van 1 tot 90; heartbeats 7 dagen; opgeloste of gedempte issues 6 kalendermaanden. Andere issuestatussen blijven. Ticket-, fiscale en auditbewaring vallen hier niet onder. Een voorbereid timersjabloon bewijst niet dat de timer actief is.",
          "example": "Oude heartbeatgeschiedenis van een stille installatie verloopt ook zonder nieuwe meldingen."
        }
      }
    },
    {
      "id": "msp.reporter-spool",
      "area": "operations",
      "status": "conditional",
      "conditions": [
        "durable_reporter_release",
        "event_stream_api_v1",
        "dedicated_service_state"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.reporter-spool"
      ],
      "source_refs": [
        "modules/control-agent/README.md"
      ],
      "related": [
        "msp.heartbeat",
        "msp.reporter-recovery",
        "msp.reporter-dry-run"
      ],
      "locales": {
        "en": {
          "title": "Durable reporter queue",
          "purpose": "Keep captured critical health transitions during transport outages and across reporter restarts.",
          "when": "When control-api is unreachable or a report is awaiting acknowledgement.",
          "steps": [
            "Inspect the content-free reporter result for pending batches, backoff or spool_full.",
            "Keep the cursor and its sibling spool directory together in the private service state directory.",
            "Restore transport and let the existing timer retry with current credentials.",
            "Verify pending counts decrease: draining means batches remain after this bounded run; delivered means the local queue is caught up. Check current heartbeat receipt separately."
          ],
          "permissions": "Authorised host operators using the dedicated reporter service identity. Cockpit roles do not grant shell access.",
          "limits": "This is a host-side feature, not a cockpit button. The 50 MB budget includes held failures. At capacity old pending records remain, but new transient changes may not fit. Heartbeats are measured again, never replayed from disk.",
          "example": "A service fails while the API is offline, then recovers. Its fault event is delivered later, while the new heartbeat reports the recovered state."
        },
        "nl": {
          "title": "Duurzame reporterwachtrij",
          "purpose": "Bewaar vastgelegde kritieke gezondheidsovergangen tijdens verbindingsstoringen en herstarts van de reporter.",
          "when": "Wanneer control-api onbereikbaar is of een melding nog op bevestiging wacht.",
          "steps": [
            "Bekijk het inhoudsvrije reporterresultaat voor wachtende batches, wachttijd of spool_full.",
            "Bewaar cursor en bijbehorende wachtrijmap samen in de privémap van de servicegebruiker.",
            "Herstel de verbinding en laat de bestaande timer opnieuw proberen met de actuele sleutel.",
            "Controleer dat wachtende aantallen afnemen: draining betekent dat na deze begrensde run nog batches wachten; delivered betekent dat de lokale wachtrij is bijgewerkt. Controleer actuele heartbeatontvangst afzonderlijk."
          ],
          "permissions": "Bevoegde hostbeheerders met de eigen reporterservice-identiteit. Cockpitrollen geven geen shelltoegang.",
          "limits": "Dit is een hostfunctie, geen cockpitknop. Het budget van 50 MB omvat ook vastgehouden fouten. Bij een volle wachtrij blijven bestaande meldingen bewaard, maar passen nieuwe tijdelijke veranderingen mogelijk niet. Heartbeats worden opnieuw gemeten en nooit vanaf schijf herhaald.",
          "example": "Een dienst valt uit terwijl de API offline is en herstelt daarna. De foutmelding wordt later bezorgd, terwijl de nieuwe heartbeat de herstelde toestand meldt."
        }
      }
    },
    {
      "id": "msp.reporter-recovery",
      "area": "operations",
      "status": "conditional",
      "conditions": [
        "durable_reporter_release",
        "event_stream_api_v1",
        "dedicated_service_state"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.reporter-recovery"
      ],
      "source_refs": [
        "modules/control-agent/README.md"
      ],
      "related": [
        "msp.heartbeat",
        "msp.reporter-spool",
        "msp.reporter-dry-run"
      ],
      "locales": {
        "en": {
          "title": "Recover paused reporter delivery",
          "purpose": "Resume retained metadata after a connection failure or an explicitly reviewed delivery conflict.",
          "when": "When delivery remains blocked after connectivity returns, or after a lost acknowledgement.",
          "steps": [
            "Check whether the result says transport_pending, server_upgrade_required, telemetry_paused or delivery_blocked.",
            "For transport errors, restore access and allow the persisted backoff to expire. Upgrade control-api before a reporter that requires stream acknowledgement.",
            "For a terminal conflict, preserve all files and have an authorised operator reconcile the cursor and server receipt state.",
            "After the cause is fixed, run the existing command once with --retry-blocked and inspect pending counts and receipt evidence."
          ],
          "permissions": "Authorised host operators using the dedicated reporter service identity. Cockpit roles do not grant shell access.",
          "limits": "The same last batch is acknowledged once without increasing issue counts again. Older, changed or out-of-order batches are refused. Do not delete queues, reset identities or repeatedly override a conflict. Disabled telemetry pauses queued delivery. Event retry backoff never suppresses a fresh heartbeat attempt on the next timer tick.",
          "example": "The API stored a fault, but its response was lost. The next attempt gets a duplicate acknowledgement and safely removes the local batch."
        },
        "nl": {
          "title": "Vastgehouden reporterverzending herstellen",
          "purpose": "Hervat bewaarde metadata na een verbindingsfout of een expliciet beoordeeld afleverconflict.",
          "when": "Wanneer verzending na verbindingsherstel geblokkeerd blijft of een bevestiging verloren ging.",
          "steps": [
            "Controleer of het resultaat transport_pending, server_upgrade_required, telemetry_paused of delivery_blocked meldt.",
            "Herstel bij verbindingsfouten de toegang en wacht de opgeslagen wachttijd af. Werk control-api bij vóór een reporter die stroombevestiging vereist.",
            "Bewaar bij een blijvend conflict alle bestanden en laat een bevoegde beheerder cursor en serverontvangst met elkaar vergelijken.",
            "Voer na herstel het bestaande commando eenmaal uit met --retry-blocked en controleer wachtende aantallen en ontvangstbewijs."
          ],
          "permissions": "Bevoegde hostbeheerders met de eigen reporterservice-identiteit. Cockpitrollen geven geen shelltoegang.",
          "limits": "Dezelfde laatste batch wordt bevestigd zonder de issuesteller opnieuw te verhogen. Oudere, gewijzigde of verkeerd geordende batches worden geweigerd. Verwijder geen wachtrij, reset geen identiteit en omzeil een conflict niet herhaaldelijk. Uitgeschakelde telemetrie pauzeert wachtrijverzending. Wachttijd voor foutmeldingen onderdrukt geen nieuwe heartbeatpoging op de volgende timerrun.",
          "example": "De API sloeg een fout op, maar de bevestiging ging verloren. De volgende poging krijgt een herhaalde bevestiging en verwijdert de lokale batch veilig."
        }
      }
    },
    {
      "id": "msp.reporter-dry-run",
      "area": "operations",
      "status": "conditional",
      "conditions": [
        "durable_reporter_release",
        "event_stream_api_v1",
        "dedicated_service_state"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.reporter-dry-run"
      ],
      "source_refs": [
        "modules/control-agent/README.md"
      ],
      "related": [
        "msp.heartbeat",
        "msp.reporter-spool",
        "msp.reporter-recovery"
      ],
      "locales": {
        "en": {
          "title": "Check local reporter probes",
          "purpose": "Inspect configured local health checks without sending or changing reporter state.",
          "when": "Before deployment or while separating a local service failure from a transport problem.",
          "steps": [
            "Use the existing reporter command as the dedicated service user and add --dry-run.",
            "Keep configured probe hosts local: localhost, 127.0.0.1 or ::1.",
            "Read the reported service names and ok/crit states.",
            "For a real delivery check, use a normal timer run and verify current receipt after resolving the local issue."
          ],
          "permissions": "Authorised host operators using the dedicated reporter service identity. Cockpit roles do not grant shell access.",
          "limits": "Dry run performs local health requests only. It reads no credentials, calls no control-api, enrolls nothing and writes no queue or cursor. It does not prove authentication, network delivery or fleet-wide health.",
          "example": "The WebUI /health check returns ok while central delivery is offline; the next investigation concerns transport, not the local health endpoint."
        },
        "nl": {
          "title": "Lokale reportercontroles uitvoeren",
          "purpose": "Bekijk ingerichte lokale gezondheidscontroles zonder te verzenden of reporterstatus te wijzigen.",
          "when": "Vóór uitrol of wanneer je een lokale servicefout wilt onderscheiden van een verbindingsprobleem.",
          "steps": [
            "Gebruik het bestaande reportercommando als de eigen servicegebruiker en voeg --dry-run toe.",
            "Houd controlehosts lokaal: localhost, 127.0.0.1 of ::1.",
            "Lees de gerapporteerde dienstnamen en toestanden ok/crit.",
            "Gebruik voor echte bezorgcontrole een normale timerrun en controleer actuele ontvangst nadat het lokale probleem is verholpen."
          ],
          "permissions": "Bevoegde hostbeheerders met de eigen reporterservice-identiteit. Cockpitrollen geven geen shelltoegang.",
          "limits": "De proef voert alleen lokale gezondheidsverzoeken uit. Hij leest geen sleutels, benadert geen control-api, registreert niets en schrijft geen wachtrij of cursor. Hij bewijst geen authenticatie, bezorging of gezondheid van alle machines.",
          "example": "De WebUI-controle op /health geeft ok terwijl centrale bezorging offline is; het vervolgonderzoek betreft de verbinding, niet het lokale gezondheidsadres."
        }
      }
    },
    {
      "id": "msp.app-support",
      "area": "commercial",
      "status": "conditional",
      "conditions": [
        "Organisation membership and active contract for approval"
      ],
      "anchors": [
        "/cockpit/app-support"
      ],
      "source_refs": [
        "apps/cockpit/backend/app/control/commercial/app_support.py",
        "apps/cockpit/frontend/src/pages/AppSupportPage.jsx"
      ],
      "related": [
        "msp.billing"
      ],
      "locales": {
        "nl": {
          "title": "Supportstrippenkaart per app",
          "purpose": "Vraag een supportniveau aan voor een beheerde app en neem de uren op in de jaarafspraak.",
          "when": "Als je app-support wilt toevoegen of wijzigen.",
          "steps": [
            "Open App-support en leg de niveaus en dekking vast.",
            "Beoordeel een klantaanvraag en bevestig klantakkoord.",
            "Leg de jaaruren en jaarprijs per app vast bij Jaaruren.",
            "Activeer de geaccepteerde jaarafspraak en zet alle onderdelen samen op één gezamenlijke factuur volgens de afgesproken betaalwijze."
          ],
          "permissions": "Organisatiebeheerders en financiële beheerders beheren app-supportaanvragen.",
          "limits": "Een aanvraag verleent nog geen uren en schrijft geen geld af. Uitschakelen van een app beëindigt de supportafspraak niet. Een niveaunaam alleen belooft geen reactietijd.",
          "example": "Neem 10 jaarlijkse supporturen voor Documenten op naast 24 infrastructuururen."
        },
        "en": {
          "title": "Annual support bundle per app",
          "purpose": "Request a managed-app support level and include its hours in the annual agreement.",
          "when": "When adding or changing app support.",
          "steps": [
            "Open App support and record levels and coverage.",
            "Review a customer request and confirm acceptance.",
            "Record annual hours and price per app in Annual hours.",
            "Activate accepted annual terms and combine all components on one consolidated invoice at the agreed payment frequency."
          ],
          "permissions": "Organisation and billing administrators manage app-support requests.",
          "limits": "Requests grant no hours and collect no money. Disabling an app does not cancel its support agreement. A tier name alone promises no response time.",
          "example": "Include 10 annual Documents support hours alongside 24 infrastructure hours."
        }
      }
    },
    {
      "id": "msp.service-packages",
      "area": "commercial",
      "status": "conditional",
      "conditions": [
        "Connected MSP and organisation administrator"
      ],
      "anchors": [
        "/cockpit/service-packages"
      ],
      "source_refs": [
        "apps/cockpit/frontend/src/pages/ServicePackagesPage.jsx",
        "apps/cockpit/backend/app/control/commercial/service_packages.py"
      ],
      "related": [
        "msp.app-support"
      ],
      "locales": {
        "nl": {
          "title": "Basispakket en consultantinzet beheren",
          "purpose": "Vraag consultantinzet aan naast het basispakket, uitgedrukt in dagen per week.",
          "when": "Als je structurele begeleiding of uitvoering door een Agentic Consultant wilt.",
          "steps": [
            "Open Pakketten en bekijk de aangevraagde inzet.",
            "Leg het afgesproken maandtarief, scope en de ingangsdatum vast.",
            "Bevestig het klantakkoord en activeer de afspraak. Er moet een actief klantcontract zijn.",
            "Verwerk wijzigingen of opzeggingen afzonderlijk."
          ],
          "permissions": "MSP-beheerders wijzigen afspraken; operators kunnen lezen.",
          "limits": "De MSP bevestigt eerst uren, tarieven en contractjaar. Centafrondingen worden over twaalf maanden verdeeld. Maandfacturen schrijven het jaarbudget niet opnieuw bij. Consultantdagen worden apart afgesproken.",
          "example": "Vraag 2 dagen Agentic Consultant per week aan naast je basispakket."
        },
        "en": {
          "title": "Manage base package and consultant capacity",
          "purpose": "Request consultant capacity alongside the base package, expressed in days per week.",
          "when": "For ongoing guidance or delivery by an Agentic Consultant.",
          "steps": [
            "Open Packages and review requested capacity.",
            "Record the agreed monthly rate, scope and effective date.",
            "Confirm customer acceptance and activate the agreement. An active customer contract is required.",
            "Process changes or cancellations separately."
          ],
          "permissions": "MSP administrators change agreements; operators can read.",
          "limits": "Your MSP first confirms hours, prices and contract year. Cent rounding is spread over twelve months. Monthly invoices never credit the annual budget again. Consultant days are agreed separately.",
          "example": "Request 2 days of Agentic Consultant capacity per week alongside the base package."
        }
      }
    },
    {
      "id": "msp.releases",
      "area": "operations",
      "status": "conditional",
      "conditions": [
        "Connected MSP and appropriate administrator permissions"
      ],
      "anchors": [
        "/cockpit/releases"
      ],
      "source_refs": [
        "apps/cockpit/frontend/src/pages/ReleasesPage.jsx",
        "apps/cockpit/backend/app/control/releases.py"
      ],
      "related": [],
      "locales": {
        "nl": {
          "title": "GitHub-updates via OTAP",
          "purpose": "Rol vastgelegde softwareversies vanuit HQ gecontroleerd uit.",
          "when": "Wanneer je een geteste GitHub-versie naar productie wilt brengen.",
          "steps": [
            "Open Updates & OTAP en kies de software.",
            "Open de broncode op GitHub en kopieer de volledige commit-SHA. Kies Ophalen naar Ontwikkeling.",
            "Start Test en wacht op een geslaagde controle. Start daarna Acceptatie.",
            "Controleer het resultaat en kies Deze versie naar Productie uitrollen. Actieve gebruikersruns blokkeren een WebUI-herstart.",
            "Herstel zo nodig de vorige geslaagde productieversie met de herstelknop."
          ],
          "permissions": "Operators lezen de status; HQ-beheerders starten releases en promoties.",
          "limits": "Alleen geconfigureerde adapters kunnen uitrollen. Test en Acceptatie gebruiken geïsoleerde bestanden en testgegevens. Codeherstel draait gegevensmigraties niet terug; databaseherstel vereist afzonderlijke beoordeling. Bij een onderbroken worker moet de hostbeheerder de echte uitrolstatus onderzoeken.",
          "example": "Promoveer dezelfde commit via O, T en A naar P."
        },
        "en": {
          "title": "GitHub updates through OTAP",
          "purpose": "Deploy pinned software versions from HQ with stage gates.",
          "when": "When promoting a tested GitHub version into production.",
          "steps": [
            "Open Updates & OTAP and select the software.",
            "Open its source on GitHub, copy the full commit SHA and choose Fetch to Development.",
            "Start Test and wait for success, then start Acceptance.",
            "Review the result and deploy this version to Production. Active user runs block a WebUI restart.",
            "Restore the previous successful production version using its restore button if needed."
          ],
          "permissions": "Operators read status; HQ administrators start releases and promotions.",
          "limits": "Only configured adapters can deploy. Test and Acceptance use isolated files and synthetic data. Code rollback does not reverse data migrations; database restoration requires separate review. Interrupted workers require inspection of actual host state.",
          "example": "Promote the same commit through D, T and A to P."
        }
      }
    },
    {
      "id": "msp.annual-support",
      "area": "commercial",
      "status": "conditional",
      "conditions": [
        "Connected MSP and administrator access"
      ],
      "anchors": [
        "/cockpit/annual-support"
      ],
      "source_refs": [
        "apps/cockpit/frontend/src/pages/AnnualSupportPage.jsx"
      ],
      "related": [],
      "locales": {
        "nl": {
          "title": "Jaarlijkse supporturen en betaalkeuze",
          "purpose": "Bekijk één jaarbudget voor basisinfrastructuur, app-strippenkaarten, automations en maatwerk.",
          "when": "Als je de jaarcap en het verschil tussen maandbetaling en jaarbetaling wilt bekijken.",
          "steps": [
            "Open Jaaruren in HQ.",
            "Kies de klant en de eerste maand van het contractjaar.",
            "Voeg basisinfrastructuur, apps en automations/maatwerk toe met jaaruren en jaarbedragen vóór jaarkorting.",
            "Kies Maandelijks betalen of Jaarlijks vooruitbetalen met korting. Vul het afgesproken kortingspercentage in; laat onbekende korting leeg.",
            "Vergelijk de jaarprijzen en besparing. Sla het concept op en bevestig klantakkoord op uren, betaalwijze, korting en bedragen voordat je activeert.",
            "Open Twaalf maandtermijnen of Eén jaarlijkse vooruitbetaling en zet de verschuldigde factuur klaar.",
            "Maak de factuur in de boekhouding en registreer het nummer bij Betalingen."
          ],
          "permissions": "Operators lezen; HQ-beheerders leggen afspraken vast, activeren en zetten facturen klaar.",
          "limits": "Dezelfde jaarcap geldt bij beide betaalwijzen. Betalen vult de uren niet opnieuw aan. Extra uren vereisen expliciet akkoord. Jaarkorting is per klantafspraak instelbaar, geldt alleen bij jaarlijkse vooruitbetaling en moet eerst zijn afgesproken. Geaccepteerde afspraken kunnen niet achteraf worden gewijzigd. Facturen worden in de boekhouding gemaakt; dit start geen automatische incasso.",
          "example": "Rekenvoorbeeld, geen vast tarief: 38 jaaruren voor EUR 3.600 bij maandbetaling; met een afgesproken korting van 5% kost jaarbetaling EUR 3.420. Beide hebben 38 jaaruren."
        },
        "en": {
          "title": "Annual support hours and payment options",
          "purpose": "View one annual budget for infrastructure, app hour bundles, automations and custom work.",
          "when": "To review the annual cap and compare monthly payments with yearly prepayment.",
          "steps": [
            "Open Annual hours in HQ.",
            "Choose the customer and first month of the contract year.",
            "Add infrastructure, apps and automation/custom-work lines with annual hours and amounts before prepayment discount.",
            "Choose Monthly payments or Yearly upfront with discount. Enter the agreed discount percentage; leave unknown discounts empty.",
            "Compare annual prices and savings. Save the draft and confirm acceptance of hours, payment frequency, discount and amounts before activating.",
            "Open Twelve monthly installments or One yearly upfront payment and prepare the due invoice.",
            "Issue the invoice in accounting and record its reference in Payments."
          ],
          "permissions": "Operators read; HQ administrators save and activate agreements and prepare invoices.",
          "limits": "Both payment options have the same annual cap. Payments never replenish hours. Extra hours need explicit approval. Yearly discount is configurable per agreement, applies only to yearly prepayment and must be agreed first. Accepted agreements cannot be changed retroactively. Invoices are issued in accounting; this does not start recurring collection.",
          "example": "Illustration, not a set price: 38 annual hours cost EUR 3,600 with monthly payments; an agreed 5% discount makes yearly prepayment EUR 3,420. Both include 38 annual hours."
        }
      }
    },
    {
      "id": "msp.wizard.identity.name",
      "area": "identity",
      "status": "available",
      "conditions": [
        "configuration_only"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.wizard.identity.name"
      ],
      "source_refs": [
        "apps/cockpit/frontend/src/wizard/StepIdentity.jsx"
      ],
      "related": [
        "msp.wizard.review.review"
      ],
      "locales": {
        "en": {
          "title": "Client slug",
          "purpose": "A fixed technical name identifies the client folder and deployment.",
          "when": "When configuring or checking this setting for a client installation.",
          "steps": [
            "Open the client wizard and choose Identity and brand.",
            "Review client slug against the client’s approved requirements. Example: acme-demo.",
            "Enter or select the value, then choose Next or Save draft and check the save confirmation.",
            "Review the effective configuration and remaining prerequisites before making live changes."
          ],
          "permissions": "Operators and admins can configure and run actions. Partners can only inspect their owned clients.",
          "limits": "These values describe a client configuration. Brand support differs by installed application. Use 2 to 31 lowercase letters, digits or hyphens, starting with a letter or digit. The name is fixed after creation.",
          "example": "acme-demo"
        },
        "nl": {
          "title": "Klantcode",
          "purpose": "Een vaste technische naam identificeert de klantmap en installatie.",
          "when": "Wanneer je deze instelling voor een klantinstallatie configureert of controleert.",
          "steps": [
            "Open de klantwizard en kies Identiteit en huisstijl.",
            "Beoordeel klantcode aan de hand van de goedgekeurde klanteisen. Voorbeeld: acme-demo.",
            "Vul de waarde in of selecteer deze, kies Volgende of Concept opslaan en controleer de bevestiging.",
            "Beoordeel de effectieve configuratie en resterende voorwaarden voordat je live wijzigingen uitvoert."
          ],
          "permissions": "Operators en admins kunnen configureren en acties uitvoeren. Partners bekijken alleen hun eigen klanten.",
          "limits": "Deze waarden beschrijven een klantconfiguratie. Huisstijlondersteuning verschilt per geïnstalleerde app. Gebruik 2 tot 31 kleine letters, cijfers of koppeltekens, beginnend met een letter of cijfer. De naam staat vast na aanmaken.",
          "example": "acme-demo"
        }
      }
    },
    {
      "id": "msp.wizard.identity.displayName",
      "area": "identity",
      "status": "available",
      "conditions": [
        "configuration_only"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.wizard.identity.displayName"
      ],
      "source_refs": [
        "apps/cockpit/frontend/src/wizard/StepIdentity.jsx"
      ],
      "related": [
        "msp.wizard.review.review"
      ],
      "locales": {
        "en": {
          "title": "Display name",
          "purpose": "A readable name identifies the client in supported screens and reports.",
          "when": "When configuring or checking this setting for a client installation.",
          "steps": [
            "Open the client wizard and choose Identity and brand.",
            "Review display name against the client’s approved requirements. Example: Acme Demo.",
            "Enter or select the value, then choose Next or Save draft and check the save confirmation.",
            "Review the effective configuration and remaining prerequisites before making live changes."
          ],
          "permissions": "Operators and admins can configure and run actions. Partners can only inspect their owned clients.",
          "limits": "These values describe a client configuration. Brand support differs by installed application.",
          "example": "Acme Demo"
        },
        "nl": {
          "title": "Weergavenaam",
          "purpose": "Een leesbare naam identificeert de klant in ondersteunde schermen en rapporten.",
          "when": "Wanneer je deze instelling voor een klantinstallatie configureert of controleert.",
          "steps": [
            "Open de klantwizard en kies Identiteit en huisstijl.",
            "Beoordeel weergavenaam aan de hand van de goedgekeurde klanteisen. Voorbeeld: Acme Demo.",
            "Vul de waarde in of selecteer deze, kies Volgende of Concept opslaan en controleer de bevestiging.",
            "Beoordeel de effectieve configuratie en resterende voorwaarden voordat je live wijzigingen uitvoert."
          ],
          "permissions": "Operators en admins kunnen configureren en acties uitvoeren. Partners bekijken alleen hun eigen klanten.",
          "limits": "Deze waarden beschrijven een klantconfiguratie. Huisstijlondersteuning verschilt per geïnstalleerde app.",
          "example": "Acme Demo"
        }
      }
    },
    {
      "id": "msp.wizard.identity.timezone",
      "area": "identity",
      "status": "available",
      "conditions": [
        "configuration_only"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.wizard.identity.timezone"
      ],
      "source_refs": [
        "apps/cockpit/frontend/src/wizard/StepIdentity.jsx"
      ],
      "related": [
        "msp.wizard.review.review"
      ],
      "locales": {
        "en": {
          "title": "Timezone",
          "purpose": "The timezone gives schedules and local timestamps the intended meaning.",
          "when": "When configuring or checking this setting for a client installation.",
          "steps": [
            "Open the client wizard and choose Identity and brand.",
            "Review timezone against the client’s approved requirements. Example: Europe/Amsterdam.",
            "Enter or select the value, then choose Next or Save draft and check the save confirmation.",
            "Review the effective configuration and remaining prerequisites before making live changes."
          ],
          "permissions": "Operators and admins can configure and run actions. Partners can only inspect their owned clients.",
          "limits": "These values describe a client configuration. Brand support differs by installed application.",
          "example": "Europe/Amsterdam"
        },
        "nl": {
          "title": "Tijdzone",
          "purpose": "De tijdzone bepaalt hoe planning en lokale tijdstippen worden geïnterpreteerd.",
          "when": "Wanneer je deze instelling voor een klantinstallatie configureert of controleert.",
          "steps": [
            "Open de klantwizard en kies Identiteit en huisstijl.",
            "Beoordeel tijdzone aan de hand van de goedgekeurde klanteisen. Voorbeeld: Europe/Amsterdam.",
            "Vul de waarde in of selecteer deze, kies Volgende of Concept opslaan en controleer de bevestiging.",
            "Beoordeel de effectieve configuratie en resterende voorwaarden voordat je live wijzigingen uitvoert."
          ],
          "permissions": "Operators en admins kunnen configureren en acties uitvoeren. Partners bekijken alleen hun eigen klanten.",
          "limits": "Deze waarden beschrijven een klantconfiguratie. Huisstijlondersteuning verschilt per geïnstalleerde app.",
          "example": "Europe/Amsterdam"
        }
      }
    },
    {
      "id": "msp.wizard.identity.brand",
      "area": "identity",
      "status": "available",
      "conditions": [
        "configuration_only"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.wizard.identity.brand"
      ],
      "source_refs": [
        "apps/cockpit/frontend/src/wizard/StepIdentity.jsx"
      ],
      "related": [
        "msp.wizard.review.review"
      ],
      "locales": {
        "en": {
          "title": "Brand settings",
          "purpose": "Brand settings describe the client identity for surfaces that support them.",
          "when": "When configuring or checking this setting for a client installation.",
          "steps": [
            "Open the client wizard and choose Identity and brand.",
            "Review brand settings against the client’s approved requirements. Example: Acme AI.",
            "Enter or select the value, then choose Next or Save draft and check the save confirmation.",
            "Review the effective configuration and remaining prerequisites before making live changes."
          ],
          "permissions": "Operators and admins can configure and run actions. Partners can only inspect their owned clients.",
          "limits": "These values describe a client configuration. Brand support differs by installed application.",
          "example": "Acme AI"
        },
        "nl": {
          "title": "Huisstijl",
          "purpose": "Huisstijlgegevens beschrijven de klantidentiteit voor schermen die deze ondersteunen.",
          "when": "Wanneer je deze instelling voor een klantinstallatie configureert of controleert.",
          "steps": [
            "Open de klantwizard en kies Identiteit en huisstijl.",
            "Beoordeel huisstijl aan de hand van de goedgekeurde klanteisen. Voorbeeld: Acme AI.",
            "Vul de waarde in of selecteer deze, kies Volgende of Concept opslaan en controleer de bevestiging.",
            "Beoordeel de effectieve configuratie en resterende voorwaarden voordat je live wijzigingen uitvoert."
          ],
          "permissions": "Operators en admins kunnen configureren en acties uitvoeren. Partners bekijken alleen hun eigen klanten.",
          "limits": "Deze waarden beschrijven een klantconfiguratie. Huisstijlondersteuning verschilt per geïnstalleerde app.",
          "example": "Acme AI"
        }
      }
    },
    {
      "id": "msp.wizard.identity.brandName",
      "area": "identity",
      "status": "available",
      "conditions": [
        "configuration_only"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.wizard.identity.brandName"
      ],
      "source_refs": [
        "apps/cockpit/frontend/src/wizard/StepIdentity.jsx"
      ],
      "related": [
        "msp.wizard.review.review"
      ],
      "locales": {
        "en": {
          "title": "Product name",
          "purpose": "Set the name used by supported client-facing surfaces.",
          "when": "When configuring or checking this setting for a client installation.",
          "steps": [
            "Open the client wizard and choose Identity and brand.",
            "Review product name against the client’s approved requirements. Example: Acme AI.",
            "Enter or select the value, then choose Next or Save draft and check the save confirmation.",
            "Review the effective configuration and remaining prerequisites before making live changes."
          ],
          "permissions": "Operators and admins can configure and run actions. Partners can only inspect their owned clients.",
          "limits": "These values describe a client configuration. Brand support differs by installed application.",
          "example": "Acme AI"
        },
        "nl": {
          "title": "Productnaam",
          "purpose": "Stel de naam in voor klantgerichte schermen die dit ondersteunen.",
          "when": "Wanneer je deze instelling voor een klantinstallatie configureert of controleert.",
          "steps": [
            "Open de klantwizard en kies Identiteit en huisstijl.",
            "Beoordeel productnaam aan de hand van de goedgekeurde klanteisen. Voorbeeld: Acme AI.",
            "Vul de waarde in of selecteer deze, kies Volgende of Concept opslaan en controleer de bevestiging.",
            "Beoordeel de effectieve configuratie en resterende voorwaarden voordat je live wijzigingen uitvoert."
          ],
          "permissions": "Operators en admins kunnen configureren en acties uitvoeren. Partners bekijken alleen hun eigen klanten.",
          "limits": "Deze waarden beschrijven een klantconfiguratie. Huisstijlondersteuning verschilt per geïnstalleerde app.",
          "example": "Acme AI"
        }
      }
    },
    {
      "id": "msp.wizard.identity.brandColor",
      "area": "identity",
      "status": "available",
      "conditions": [
        "configuration_only"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.wizard.identity.brandColor"
      ],
      "source_refs": [
        "apps/cockpit/frontend/src/wizard/StepIdentity.jsx"
      ],
      "related": [
        "msp.wizard.review.review"
      ],
      "locales": {
        "en": {
          "title": "Primary colour",
          "purpose": "Choose the accent colour used by supported themes.",
          "when": "When configuring or checking this setting for a client installation.",
          "steps": [
            "Open the client wizard and choose Identity and brand.",
            "Review primary colour against the client’s approved requirements. Example: #009dff.",
            "Enter or select the value, then choose Next or Save draft and check the save confirmation.",
            "Review the effective configuration and remaining prerequisites before making live changes."
          ],
          "permissions": "Operators and admins can configure and run actions. Partners can only inspect their owned clients.",
          "limits": "These values describe a client configuration. Brand support differs by installed application.",
          "example": "#009dff"
        },
        "nl": {
          "title": "Hoofdkleur",
          "purpose": "Kies de accentkleur voor ondersteunde thema’s.",
          "when": "Wanneer je deze instelling voor een klantinstallatie configureert of controleert.",
          "steps": [
            "Open de klantwizard en kies Identiteit en huisstijl.",
            "Beoordeel hoofdkleur aan de hand van de goedgekeurde klanteisen. Voorbeeld: #009dff.",
            "Vul de waarde in of selecteer deze, kies Volgende of Concept opslaan en controleer de bevestiging.",
            "Beoordeel de effectieve configuratie en resterende voorwaarden voordat je live wijzigingen uitvoert."
          ],
          "permissions": "Operators en admins kunnen configureren en acties uitvoeren. Partners bekijken alleen hun eigen klanten.",
          "limits": "Deze waarden beschrijven een klantconfiguratie. Huisstijlondersteuning verschilt per geïnstalleerde app.",
          "example": "#009dff"
        }
      }
    },
    {
      "id": "msp.wizard.identity.brandLogo",
      "area": "identity",
      "status": "available",
      "conditions": [
        "configuration_only"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.wizard.identity.brandLogo"
      ],
      "source_refs": [
        "apps/cockpit/frontend/src/wizard/StepIdentity.jsx"
      ],
      "related": [
        "msp.wizard.review.review"
      ],
      "locales": {
        "en": {
          "title": "Logo path",
          "purpose": "Reference a client-owned image to include in the installation bundle.",
          "when": "When configuring or checking this setting for a client installation.",
          "steps": [
            "Open the client wizard and choose Identity and brand.",
            "Review logo path against the client’s approved requirements. Example: brand/logo.png.",
            "Enter or select the value, then choose Next or Save draft and check the save confirmation.",
            "Review the effective configuration and remaining prerequisites before making live changes."
          ],
          "permissions": "Operators and admins can configure and run actions. Partners can only inspect their owned clients.",
          "limits": "These values describe a client configuration. Brand support differs by installed application. The supported bundle includes the selected image beneath brand/, at most 5 MB, without symbolic links. Inclusion does not guarantee every module displays it.",
          "example": "brand/logo.png"
        },
        "nl": {
          "title": "Logopad",
          "purpose": "Verwijs naar een klantafbeelding die met de installatiebundel meegaat.",
          "when": "Wanneer je deze instelling voor een klantinstallatie configureert of controleert.",
          "steps": [
            "Open de klantwizard en kies Identiteit en huisstijl.",
            "Beoordeel logopad aan de hand van de goedgekeurde klanteisen. Voorbeeld: brand/logo.png.",
            "Vul de waarde in of selecteer deze, kies Volgende of Concept opslaan en controleer de bevestiging.",
            "Beoordeel de effectieve configuratie en resterende voorwaarden voordat je live wijzigingen uitvoert."
          ],
          "permissions": "Operators en admins kunnen configureren en acties uitvoeren. Partners bekijken alleen hun eigen klanten.",
          "limits": "Deze waarden beschrijven een klantconfiguratie. Huisstijlondersteuning verschilt per geïnstalleerde app. De ondersteunde bundel bevat de gekozen afbeelding onder brand/, maximaal 5 MB en zonder symbolische links. Meenemen garandeert niet dat elke module het logo toont.",
          "example": "brand/logo.png"
        }
      }
    },
    {
      "id": "msp.wizard.target.target",
      "area": "target",
      "status": "conditional",
      "conditions": [
        "configuration_only"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.wizard.target.target"
      ],
      "source_refs": [
        "apps/cockpit/frontend/src/wizard/StepTarget.jsx"
      ],
      "related": [
        "msp.wizard.review.review"
      ],
      "locales": {
        "en": {
          "title": "Deployment target",
          "purpose": "Choose cloud infrastructure, the native engine or a full Docker platform on existing hardware.",
          "when": "When configuring or checking this setting for a client installation.",
          "steps": [
            "Open the client wizard and choose Hosting and installation.",
            "Review deployment target against the client’s approved requirements. Example: compose.",
            "Enter or select the value, then choose Next or Save draft and check the save confirmation.",
            "Review the effective configuration and remaining prerequisites before making live changes."
          ],
          "permissions": "Operators and admins can configure and run actions. Partners can only inspect their owned clients.",
          "limits": "Availability depends on the selected infrastructure root, account rights, image architecture and reviewed cloud plan. A saved option creates no resource and includes no agreed price.",
          "example": "compose"
        },
        "nl": {
          "title": "Installatiedoel",
          "purpose": "Kies cloudinfrastructuur, alleen de native engine of het volledige Dockerplatform op bestaande hardware.",
          "when": "Wanneer je deze instelling voor een klantinstallatie configureert of controleert.",
          "steps": [
            "Open de klantwizard en kies Hosting en installatie.",
            "Beoordeel installatiedoel aan de hand van de goedgekeurde klanteisen. Voorbeeld: compose.",
            "Vul de waarde in of selecteer deze, kies Volgende of Concept opslaan en controleer de bevestiging.",
            "Beoordeel de effectieve configuratie en resterende voorwaarden voordat je live wijzigingen uitvoert."
          ],
          "permissions": "Operators en admins kunnen configureren en acties uitvoeren. Partners bekijken alleen hun eigen klanten.",
          "limits": "Beschikbaarheid hangt af van de infrastructuurvariant, accountrechten, imagearchitectuur en het beoordeelde cloudplan. Een opgeslagen optie maakt geen middel aan en bevat geen afgesproken prijs.",
          "example": "compose"
        }
      }
    },
    {
      "id": "msp.wizard.target.cloud.scaleway",
      "area": "target",
      "status": "conditional",
      "conditions": [
        "configuration_only"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.wizard.target.cloud.scaleway"
      ],
      "source_refs": [
        "apps/cockpit/frontend/src/wizard/StepTarget.jsx"
      ],
      "related": [
        "msp.wizard.review.review"
      ],
      "locales": {
        "en": {
          "title": "Scaleway target",
          "purpose": "Prepare the Scaleway Terraform deployment using a client account and approved region.",
          "when": "When configuring or checking this setting for a client installation.",
          "steps": [
            "Open the client wizard and choose Hosting and installation.",
            "Review scaleway target against the client’s approved requirements. Example: nl-ams.",
            "Enter or select the value, then choose Next or Save draft and check the save confirmation.",
            "Review the effective configuration and remaining prerequisites before making live changes."
          ],
          "permissions": "Operators and admins can configure and run actions. Partners can only inspect their owned clients.",
          "limits": "Availability depends on the selected infrastructure root, account rights, image architecture and reviewed cloud plan. A saved option creates no resource and includes no agreed price.",
          "example": "nl-ams"
        },
        "nl": {
          "title": "Scaleway-installatie",
          "purpose": "Bereid de Scaleway-installatie voor met een klantaccount en goedgekeurde regio.",
          "when": "Wanneer je deze instelling voor een klantinstallatie configureert of controleert.",
          "steps": [
            "Open de klantwizard en kies Hosting en installatie.",
            "Beoordeel scaleway-installatie aan de hand van de goedgekeurde klanteisen. Voorbeeld: nl-ams.",
            "Vul de waarde in of selecteer deze, kies Volgende of Concept opslaan en controleer de bevestiging.",
            "Beoordeel de effectieve configuratie en resterende voorwaarden voordat je live wijzigingen uitvoert."
          ],
          "permissions": "Operators en admins kunnen configureren en acties uitvoeren. Partners bekijken alleen hun eigen klanten.",
          "limits": "Beschikbaarheid hangt af van de infrastructuurvariant, accountrechten, imagearchitectuur en het beoordeelde cloudplan. Een opgeslagen optie maakt geen middel aan en bevat geen afgesproken prijs.",
          "example": "nl-ams"
        }
      }
    },
    {
      "id": "msp.wizard.target.cloud.gcp",
      "area": "target",
      "status": "conditional",
      "conditions": [
        "configuration_only"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.wizard.target.cloud.gcp"
      ],
      "source_refs": [
        "apps/cockpit/frontend/src/wizard/StepTarget.jsx"
      ],
      "related": [
        "msp.wizard.review.review"
      ],
      "locales": {
        "en": {
          "title": "Google Cloud target",
          "purpose": "Prepare a Compute Engine deployment with a project and service-account credentials.",
          "when": "When configuring or checking this setting for a client installation.",
          "steps": [
            "Open the client wizard and choose Hosting and installation.",
            "Review google cloud target against the client’s approved requirements. Example: europe-west4.",
            "Enter or select the value, then choose Next or Save draft and check the save confirmation.",
            "Review the effective configuration and remaining prerequisites before making live changes."
          ],
          "permissions": "Operators and admins can configure and run actions. Partners can only inspect their owned clients.",
          "limits": "Availability depends on the selected infrastructure root, account rights, image architecture and reviewed cloud plan. A saved option creates no resource and includes no agreed price.",
          "example": "europe-west4"
        },
        "nl": {
          "title": "Google Cloud-installatie",
          "purpose": "Bereid een Compute Engine-installatie voor met een project en serviceaccount.",
          "when": "Wanneer je deze instelling voor een klantinstallatie configureert of controleert.",
          "steps": [
            "Open de klantwizard en kies Hosting en installatie.",
            "Beoordeel google cloud-installatie aan de hand van de goedgekeurde klanteisen. Voorbeeld: europe-west4.",
            "Vul de waarde in of selecteer deze, kies Volgende of Concept opslaan en controleer de bevestiging.",
            "Beoordeel de effectieve configuratie en resterende voorwaarden voordat je live wijzigingen uitvoert."
          ],
          "permissions": "Operators en admins kunnen configureren en acties uitvoeren. Partners bekijken alleen hun eigen klanten.",
          "limits": "Beschikbaarheid hangt af van de infrastructuurvariant, accountrechten, imagearchitectuur en het beoordeelde cloudplan. Een opgeslagen optie maakt geen middel aan en bevat geen afgesproken prijs.",
          "example": "europe-west4"
        }
      }
    },
    {
      "id": "msp.wizard.target.cloud.azure",
      "area": "target",
      "status": "conditional",
      "conditions": [
        "configuration_only"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.wizard.target.cloud.azure"
      ],
      "source_refs": [
        "apps/cockpit/frontend/src/wizard/StepTarget.jsx"
      ],
      "related": [
        "msp.wizard.review.review"
      ],
      "locales": {
        "en": {
          "title": "Azure target",
          "purpose": "Prepare an Azure VM deployment with a subscription and service principal.",
          "when": "When configuring or checking this setting for a client installation.",
          "steps": [
            "Open the client wizard and choose Hosting and installation.",
            "Review azure target against the client’s approved requirements. Example: westeurope.",
            "Enter or select the value, then choose Next or Save draft and check the save confirmation.",
            "Review the effective configuration and remaining prerequisites before making live changes."
          ],
          "permissions": "Operators and admins can configure and run actions. Partners can only inspect their owned clients.",
          "limits": "Availability depends on the selected infrastructure root, account rights, image architecture and reviewed cloud plan. A saved option creates no resource and includes no agreed price.",
          "example": "westeurope"
        },
        "nl": {
          "title": "Azure-installatie",
          "purpose": "Bereid een Azure-VM voor met een abonnement en serviceprincipal.",
          "when": "Wanneer je deze instelling voor een klantinstallatie configureert of controleert.",
          "steps": [
            "Open de klantwizard en kies Hosting en installatie.",
            "Beoordeel azure-installatie aan de hand van de goedgekeurde klanteisen. Voorbeeld: westeurope.",
            "Vul de waarde in of selecteer deze, kies Volgende of Concept opslaan en controleer de bevestiging.",
            "Beoordeel de effectieve configuratie en resterende voorwaarden voordat je live wijzigingen uitvoert."
          ],
          "permissions": "Operators en admins kunnen configureren en acties uitvoeren. Partners bekijken alleen hun eigen klanten.",
          "limits": "Beschikbaarheid hangt af van de infrastructuurvariant, accountrechten, imagearchitectuur en het beoordeelde cloudplan. Een opgeslagen optie maakt geen middel aan en bevat geen afgesproken prijs.",
          "example": "westeurope"
        }
      }
    },
    {
      "id": "msp.wizard.target.cloud.device",
      "area": "target",
      "status": "conditional",
      "conditions": [
        "configuration_only"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.wizard.target.cloud.device"
      ],
      "source_refs": [
        "apps/cockpit/frontend/src/wizard/StepTarget.jsx"
      ],
      "related": [
        "msp.wizard.review.review"
      ],
      "locales": {
        "en": {
          "title": "Native engine and CLI",
          "purpose": "Install the engine and command-line tools without the full WebUI or container stack.",
          "when": "When configuring or checking this setting for a client installation.",
          "steps": [
            "Open the client wizard and choose Hosting and installation.",
            "Review native engine and cli against the client’s approved requirements. Example: device.",
            "Enter or select the value, then choose Next or Save draft and check the save confirmation.",
            "Review the effective configuration and remaining prerequisites before making live changes."
          ],
          "permissions": "Operators and admins can configure and run actions. Partners can only inspect their owned clients.",
          "limits": "Availability depends on the selected infrastructure root, account rights, image architecture and reviewed cloud plan. A saved option creates no resource and includes no agreed price.",
          "example": "device"
        },
        "nl": {
          "title": "Native engine en CLI",
          "purpose": "Installeer de engine en commandoregeltools zonder volledige WebUI of containers.",
          "when": "Wanneer je deze instelling voor een klantinstallatie configureert of controleert.",
          "steps": [
            "Open de klantwizard en kies Hosting en installatie.",
            "Beoordeel native engine en cli aan de hand van de goedgekeurde klanteisen. Voorbeeld: device.",
            "Vul de waarde in of selecteer deze, kies Volgende of Concept opslaan en controleer de bevestiging.",
            "Beoordeel de effectieve configuratie en resterende voorwaarden voordat je live wijzigingen uitvoert."
          ],
          "permissions": "Operators en admins kunnen configureren en acties uitvoeren. Partners bekijken alleen hun eigen klanten.",
          "limits": "Beschikbaarheid hangt af van de infrastructuurvariant, accountrechten, imagearchitectuur en het beoordeelde cloudplan. Een opgeslagen optie maakt geen middel aan en bevat geen afgesproken prijs.",
          "example": "device"
        }
      }
    },
    {
      "id": "msp.wizard.target.cloud.compose",
      "area": "target",
      "status": "conditional",
      "conditions": [
        "configuration_only"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.wizard.target.cloud.compose"
      ],
      "source_refs": [
        "apps/cockpit/frontend/src/wizard/StepTarget.jsx"
      ],
      "related": [
        "msp.wizard.review.review"
      ],
      "locales": {
        "en": {
          "title": "Full platform on own hardware",
          "purpose": "Build an installer for the selected Docker stack on a compatible Pi or Linux host.",
          "when": "When configuring or checking this setting for a client installation.",
          "steps": [
            "Open the client wizard and choose Hosting and installation.",
            "Review full platform on own hardware against the client’s approved requirements. Example: compose, arm64.",
            "Enter or select the value, then choose Next or Save draft and check the save confirmation.",
            "Review the effective configuration and remaining prerequisites before making live changes."
          ],
          "permissions": "Operators and admins can configure and run actions. Partners can only inspect their owned clients.",
          "limits": "Availability depends on the selected infrastructure root, account rights, image architecture and reviewed cloud plan. A saved option creates no resource and includes no agreed price.",
          "example": "compose, arm64"
        },
        "nl": {
          "title": "Volledig platform op eigen hardware",
          "purpose": "Maak een installer voor de gekozen Dockerstack op een geschikte Pi of Linuxmachine.",
          "when": "Wanneer je deze instelling voor een klantinstallatie configureert of controleert.",
          "steps": [
            "Open de klantwizard en kies Hosting en installatie.",
            "Beoordeel volledig platform op eigen hardware aan de hand van de goedgekeurde klanteisen. Voorbeeld: compose, arm64.",
            "Vul de waarde in of selecteer deze, kies Volgende of Concept opslaan en controleer de bevestiging.",
            "Beoordeel de effectieve configuratie en resterende voorwaarden voordat je live wijzigingen uitvoert."
          ],
          "permissions": "Operators en admins kunnen configureren en acties uitvoeren. Partners bekijken alleen hun eigen klanten.",
          "limits": "Beschikbaarheid hangt af van de infrastructuurvariant, accountrechten, imagearchitectuur en het beoordeelde cloudplan. Een opgeslagen optie maakt geen middel aan en bevat geen afgesproken prijs.",
          "example": "compose, arm64"
        }
      }
    },
    {
      "id": "msp.wizard.target.architecture",
      "area": "target",
      "status": "conditional",
      "conditions": [
        "configuration_only"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.wizard.target.architecture"
      ],
      "source_refs": [
        "apps/cockpit/frontend/src/wizard/StepTarget.jsx"
      ],
      "related": [
        "msp.wizard.review.review"
      ],
      "locales": {
        "en": {
          "title": "CPU architecture",
          "purpose": "Match container images to the actual processor architecture.",
          "when": "When configuring or checking this setting for a client installation.",
          "steps": [
            "Open the client wizard and choose Hosting and installation.",
            "Review cpu architecture against the client’s approved requirements. Example: arm64 for a 64-bit Pi.",
            "Enter or select the value, then choose Next or Save draft and check the save confirmation.",
            "Review the effective configuration and remaining prerequisites before making live changes."
          ],
          "permissions": "Operators and admins can configure and run actions. Partners can only inspect their owned clients.",
          "limits": "Availability depends on the selected infrastructure root, account rights, image architecture and reviewed cloud plan. A saved option creates no resource and includes no agreed price. Verify the actual image manifests. OpenNotebook currently requires amd64.",
          "example": "arm64 for a 64-bit Pi"
        },
        "nl": {
          "title": "Processorarchitectuur",
          "purpose": "Stem containerimages af op de werkelijke processorarchitectuur.",
          "when": "Wanneer je deze instelling voor een klantinstallatie configureert of controleert.",
          "steps": [
            "Open de klantwizard en kies Hosting en installatie.",
            "Beoordeel processorarchitectuur aan de hand van de goedgekeurde klanteisen. Voorbeeld: arm64 voor een 64-bits Pi.",
            "Vul de waarde in of selecteer deze, kies Volgende of Concept opslaan en controleer de bevestiging.",
            "Beoordeel de effectieve configuratie en resterende voorwaarden voordat je live wijzigingen uitvoert."
          ],
          "permissions": "Operators en admins kunnen configureren en acties uitvoeren. Partners bekijken alleen hun eigen klanten.",
          "limits": "Beschikbaarheid hangt af van de infrastructuurvariant, accountrechten, imagearchitectuur en het beoordeelde cloudplan. Een opgeslagen optie maakt geen middel aan en bevat geen afgesproken prijs. Controleer de echte imagemanifesten. OpenNotebook vereist momenteel amd64.",
          "example": "arm64 voor een 64-bits Pi"
        }
      }
    },
    {
      "id": "msp.wizard.target.tailscale",
      "area": "target",
      "status": "conditional",
      "conditions": [
        "configuration_only"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.wizard.target.tailscale"
      ],
      "source_refs": [
        "apps/cockpit/frontend/src/wizard/StepTarget.jsx"
      ],
      "related": [
        "msp.wizard.review.review"
      ],
      "locales": {
        "en": {
          "title": "Private network",
          "purpose": "Prepare private connectivity for operator access and supported application routes.",
          "when": "When configuring or checking this setting for a client installation.",
          "steps": [
            "Open the client wizard and choose Hosting and installation.",
            "Review private network against the client’s approved requirements. Example: synthpulse-acme-demo.",
            "Enter or select the value, then choose Next or Save draft and check the save confirmation.",
            "Review the effective configuration and remaining prerequisites before making live changes."
          ],
          "permissions": "Operators and admins can configure and run actions. Partners can only inspect their owned clients.",
          "limits": "Availability depends on the selected infrastructure root, account rights, image architecture and reviewed cloud plan. A saved option creates no resource and includes no agreed price.",
          "example": "synthpulse-acme-demo"
        },
        "nl": {
          "title": "Privénetwerk",
          "purpose": "Bereid privéverbindingen voor beheer en ondersteunde applicatieroutes voor.",
          "when": "Wanneer je deze instelling voor een klantinstallatie configureert of controleert.",
          "steps": [
            "Open de klantwizard en kies Hosting en installatie.",
            "Beoordeel privénetwerk aan de hand van de goedgekeurde klanteisen. Voorbeeld: synthpulse-acme-demo.",
            "Vul de waarde in of selecteer deze, kies Volgende of Concept opslaan en controleer de bevestiging.",
            "Beoordeel de effectieve configuratie en resterende voorwaarden voordat je live wijzigingen uitvoert."
          ],
          "permissions": "Operators en admins kunnen configureren en acties uitvoeren. Partners bekijken alleen hun eigen klanten.",
          "limits": "Beschikbaarheid hangt af van de infrastructuurvariant, accountrechten, imagearchitectuur en het beoordeelde cloudplan. Een opgeslagen optie maakt geen middel aan en bevat geen afgesproken prijs.",
          "example": "synthpulse-acme-demo"
        }
      }
    },
    {
      "id": "msp.wizard.target.tsTags",
      "area": "target",
      "status": "conditional",
      "conditions": [
        "configuration_only"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.wizard.target.tsTags"
      ],
      "source_refs": [
        "apps/cockpit/frontend/src/wizard/StepTarget.jsx"
      ],
      "related": [
        "msp.wizard.review.review"
      ],
      "locales": {
        "en": {
          "title": "Network access tags",
          "purpose": "Tags associate a node with the network access rules configured by its operator.",
          "when": "When configuring or checking this setting for a client installation.",
          "steps": [
            "Open the client wizard and choose Hosting and installation.",
            "Review network access tags against the client’s approved requirements. Example: tag:synthpulse.",
            "Enter or select the value, then choose Next or Save draft and check the save confirmation.",
            "Review the effective configuration and remaining prerequisites before making live changes."
          ],
          "permissions": "Operators and admins can configure and run actions. Partners can only inspect their owned clients.",
          "limits": "Availability depends on the selected infrastructure root, account rights, image architecture and reviewed cloud plan. A saved option creates no resource and includes no agreed price.",
          "example": "tag:synthpulse"
        },
        "nl": {
          "title": "Netwerktoegangstags",
          "purpose": "Tags koppelen een machine aan de netwerktoegangsregels van de beheerder.",
          "when": "Wanneer je deze instelling voor een klantinstallatie configureert of controleert.",
          "steps": [
            "Open de klantwizard en kies Hosting en installatie.",
            "Beoordeel netwerktoegangstags aan de hand van de goedgekeurde klanteisen. Voorbeeld: tag:synthpulse.",
            "Vul de waarde in of selecteer deze, kies Volgende of Concept opslaan en controleer de bevestiging.",
            "Beoordeel de effectieve configuratie en resterende voorwaarden voordat je live wijzigingen uitvoert."
          ],
          "permissions": "Operators en admins kunnen configureren en acties uitvoeren. Partners bekijken alleen hun eigen klanten.",
          "limits": "Beschikbaarheid hangt af van de infrastructuurvariant, accountrechten, imagearchitectuur en het beoordeelde cloudplan. Een opgeslagen optie maakt geen middel aan en bevat geen afgesproken prijs.",
          "example": "tag:synthpulse"
        }
      }
    },
    {
      "id": "msp.wizard.target.tsHostname",
      "area": "target",
      "status": "conditional",
      "conditions": [
        "configuration_only"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.wizard.target.tsHostname"
      ],
      "source_refs": [
        "apps/cockpit/frontend/src/wizard/StepTarget.jsx"
      ],
      "related": [
        "msp.wizard.review.review"
      ],
      "locales": {
        "en": {
          "title": "Network hostname",
          "purpose": "Choose the recognisable machine name inside the private network.",
          "when": "When configuring or checking this setting for a client installation.",
          "steps": [
            "Open the client wizard and choose Hosting and installation.",
            "Review network hostname against the client’s approved requirements. Example: synthpulse-acme-demo.",
            "Enter or select the value, then choose Next or Save draft and check the save confirmation.",
            "Review the effective configuration and remaining prerequisites before making live changes."
          ],
          "permissions": "Operators and admins can configure and run actions. Partners can only inspect their owned clients.",
          "limits": "Availability depends on the selected infrastructure root, account rights, image architecture and reviewed cloud plan. A saved option creates no resource and includes no agreed price.",
          "example": "synthpulse-acme-demo"
        },
        "nl": {
          "title": "Netwerkhostnaam",
          "purpose": "Kies een herkenbare machinenaam binnen het privénetwerk.",
          "when": "Wanneer je deze instelling voor een klantinstallatie configureert of controleert.",
          "steps": [
            "Open de klantwizard en kies Hosting en installatie.",
            "Beoordeel netwerkhostnaam aan de hand van de goedgekeurde klanteisen. Voorbeeld: synthpulse-acme-demo.",
            "Vul de waarde in of selecteer deze, kies Volgende of Concept opslaan en controleer de bevestiging.",
            "Beoordeel de effectieve configuratie en resterende voorwaarden voordat je live wijzigingen uitvoert."
          ],
          "permissions": "Operators en admins kunnen configureren en acties uitvoeren. Partners bekijken alleen hun eigen klanten.",
          "limits": "Beschikbaarheid hangt af van de infrastructuurvariant, accountrechten, imagearchitectuur en het beoordeelde cloudplan. Een opgeslagen optie maakt geen middel aan en bevat geen afgesproken prijs.",
          "example": "synthpulse-acme-demo"
        }
      }
    },
    {
      "id": "msp.wizard.target.tsServe",
      "area": "target",
      "status": "conditional",
      "conditions": [
        "configuration_only"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.wizard.target.tsServe"
      ],
      "source_refs": [
        "apps/cockpit/frontend/src/wizard/StepTarget.jsx"
      ],
      "related": [
        "msp.wizard.review.review"
      ],
      "locales": {
        "en": {
          "title": "Private WebUI route",
          "purpose": "Expose the installed WebUI to the private network through the supported proxy route.",
          "when": "When configuring or checking this setting for a client installation.",
          "steps": [
            "Open the client wizard and choose Hosting and installation.",
            "Review private webui route against the client’s approved requirements. Example: HTTPS port 8788.",
            "Enter or select the value, then choose Next or Save draft and check the save confirmation.",
            "Review the effective configuration and remaining prerequisites before making live changes."
          ],
          "permissions": "Operators and admins can configure and run actions. Partners can only inspect their owned clients.",
          "limits": "Availability depends on the selected infrastructure root, account rights, image architecture and reviewed cloud plan. A saved option creates no resource and includes no agreed price.",
          "example": "HTTPS port 8788"
        },
        "nl": {
          "title": "Privéroute naar de WebUI",
          "purpose": "Maak de geïnstalleerde WebUI bereikbaar via de ondersteunde privéproxyroute.",
          "when": "Wanneer je deze instelling voor een klantinstallatie configureert of controleert.",
          "steps": [
            "Open de klantwizard en kies Hosting en installatie.",
            "Beoordeel privéroute naar de webui aan de hand van de goedgekeurde klanteisen. Voorbeeld: HTTPS port 8788.",
            "Vul de waarde in of selecteer deze, kies Volgende of Concept opslaan en controleer de bevestiging.",
            "Beoordeel de effectieve configuratie en resterende voorwaarden voordat je live wijzigingen uitvoert."
          ],
          "permissions": "Operators en admins kunnen configureren en acties uitvoeren. Partners bekijken alleen hun eigen klanten.",
          "limits": "Beschikbaarheid hangt af van de infrastructuurvariant, accountrechten, imagearchitectuur en het beoordeelde cloudplan. Een opgeslagen optie maakt geen middel aan en bevat geen afgesproken prijs.",
          "example": "HTTPS port 8788"
        }
      }
    },
    {
      "id": "msp.wizard.target.tsFunnel",
      "area": "target",
      "status": "conditional",
      "conditions": [
        "configuration_only"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.wizard.target.tsFunnel"
      ],
      "source_refs": [
        "apps/cockpit/frontend/src/wizard/StepTarget.jsx"
      ],
      "related": [
        "msp.wizard.review.review"
      ],
      "locales": {
        "en": {
          "title": "Public OAuth callback",
          "purpose": "Prepare a public callback for the connection service when no public domain is configured.",
          "when": "When configuring or checking this setting for a client installation.",
          "steps": [
            "Open the client wizard and choose Hosting and installation.",
            "Review public oauth callback against the client’s approved requirements. Example: Nango callback, port 10000.",
            "Enter or select the value, then choose Next or Save draft and check the save confirmation.",
            "Review the effective configuration and remaining prerequisites before making live changes."
          ],
          "permissions": "Operators and admins can configure and run actions. Partners can only inspect their owned clients.",
          "limits": "Availability depends on the selected infrastructure root, account rights, image architecture and reviewed cloud plan. A saved option creates no resource and includes no agreed price. This concerns the connection callback, never the private staff cockpit. Public routes require a separate access review.",
          "example": "Nango callback, port 10000"
        },
        "nl": {
          "title": "Publieke OAuth-callback",
          "purpose": "Bereid een publieke callback voor de verbindingsdienst voor als er geen publiek domein is.",
          "when": "Wanneer je deze instelling voor een klantinstallatie configureert of controleert.",
          "steps": [
            "Open de klantwizard en kies Hosting en installatie.",
            "Beoordeel publieke oauth-callback aan de hand van de goedgekeurde klanteisen. Voorbeeld: Nango callback, port 10000.",
            "Vul de waarde in of selecteer deze, kies Volgende of Concept opslaan en controleer de bevestiging.",
            "Beoordeel de effectieve configuratie en resterende voorwaarden voordat je live wijzigingen uitvoert."
          ],
          "permissions": "Operators en admins kunnen configureren en acties uitvoeren. Partners bekijken alleen hun eigen klanten.",
          "limits": "Beschikbaarheid hangt af van de infrastructuurvariant, accountrechten, imagearchitectuur en het beoordeelde cloudplan. Een opgeslagen optie maakt geen middel aan en bevat geen afgesproken prijs. Dit betreft de verbindingscallback, nooit het privébeheercockpit. Publieke routes vereisen een aparte toegangsbeoordeling.",
          "example": "Nango callback, port 10000"
        }
      }
    },
    {
      "id": "msp.wizard.target.repoRef",
      "area": "target",
      "status": "conditional",
      "conditions": [
        "configuration_only"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.wizard.target.repoRef"
      ],
      "source_refs": [
        "apps/cockpit/frontend/src/wizard/StepTarget.jsx"
      ],
      "related": [
        "msp.wizard.review.review"
      ],
      "locales": {
        "en": {
          "title": "Release reference",
          "purpose": "Pin the installation to an approved release instead of a moving latest tag.",
          "when": "When configuring or checking this setting for a client installation.",
          "steps": [
            "Open the client wizard and choose Hosting and installation.",
            "Review release reference against the client’s approved requirements. Example: approved release tag.",
            "Enter or select the value, then choose Next or Save draft and check the save confirmation.",
            "Review the effective configuration and remaining prerequisites before making live changes."
          ],
          "permissions": "Operators and admins can configure and run actions. Partners can only inspect their owned clients.",
          "limits": "Availability depends on the selected infrastructure root, account rights, image architecture and reviewed cloud plan. A saved option creates no resource and includes no agreed price.",
          "example": "approved release tag"
        },
        "nl": {
          "title": "Releaseversie",
          "purpose": "Koppel de installatie aan een goedgekeurde release in plaats van een veranderlijke latest-tag.",
          "when": "Wanneer je deze instelling voor een klantinstallatie configureert of controleert.",
          "steps": [
            "Open de klantwizard en kies Hosting en installatie.",
            "Beoordeel releaseversie aan de hand van de goedgekeurde klanteisen. Voorbeeld: goedgekeurde releasetag.",
            "Vul de waarde in of selecteer deze, kies Volgende of Concept opslaan en controleer de bevestiging.",
            "Beoordeel de effectieve configuratie en resterende voorwaarden voordat je live wijzigingen uitvoert."
          ],
          "permissions": "Operators en admins kunnen configureren en acties uitvoeren. Partners bekijken alleen hun eigen klanten.",
          "limits": "Beschikbaarheid hangt af van de infrastructuurvariant, accountrechten, imagearchitectuur en het beoordeelde cloudplan. Een opgeslagen optie maakt geen middel aan en bevat geen afgesproken prijs.",
          "example": "goedgekeurde releasetag"
        }
      }
    },
    {
      "id": "msp.wizard.target.compliant",
      "area": "target",
      "status": "conditional",
      "conditions": [
        "configuration_only"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.wizard.target.compliant"
      ],
      "source_refs": [
        "apps/cockpit/frontend/src/wizard/StepTarget.jsx"
      ],
      "related": [
        "msp.wizard.review.review"
      ],
      "locales": {
        "en": {
          "title": "Hardened infrastructure baseline",
          "purpose": "Select the stricter Terraform root and review its controls and account permissions.",
          "when": "When configuring or checking this setting for a client installation.",
          "steps": [
            "Open the client wizard and choose Hosting and installation.",
            "Review hardened infrastructure baseline against the client’s approved requirements. Example: hardened cloud root.",
            "Enter or select the value, then choose Next or Save draft and check the save confirmation.",
            "Review the effective configuration and remaining prerequisites before making live changes."
          ],
          "permissions": "Operators and admins can configure and run actions. Partners can only inspect their owned clients.",
          "limits": "Availability depends on the selected infrastructure root, account rights, image architecture and reviewed cloud plan. A saved option creates no resource and includes no agreed price. A hardened baseline is not compliance certification.",
          "example": "hardened cloud root"
        },
        "nl": {
          "title": "Versterkte infrastructuurbasis",
          "purpose": "Kies de strengere Terraformvariant en controleer de maatregelen en accountrechten.",
          "when": "Wanneer je deze instelling voor een klantinstallatie configureert of controleert.",
          "steps": [
            "Open de klantwizard en kies Hosting en installatie.",
            "Beoordeel versterkte infrastructuurbasis aan de hand van de goedgekeurde klanteisen. Voorbeeld: versterkte cloudvariant.",
            "Vul de waarde in of selecteer deze, kies Volgende of Concept opslaan en controleer de bevestiging.",
            "Beoordeel de effectieve configuratie en resterende voorwaarden voordat je live wijzigingen uitvoert."
          ],
          "permissions": "Operators en admins kunnen configureren en acties uitvoeren. Partners bekijken alleen hun eigen klanten.",
          "limits": "Beschikbaarheid hangt af van de infrastructuurvariant, accountrechten, imagearchitectuur en het beoordeelde cloudplan. Een opgeslagen optie maakt geen middel aan en bevat geen afgesproken prijs. Een versterkte basis is geen certificering van naleving.",
          "example": "versterkte cloudvariant"
        }
      }
    },
    {
      "id": "msp.wizard.target.size",
      "area": "target",
      "status": "conditional",
      "conditions": [
        "configuration_only"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.wizard.target.size"
      ],
      "source_refs": [
        "apps/cockpit/frontend/src/wizard/StepTarget.jsx"
      ],
      "related": [
        "msp.wizard.review.review"
      ],
      "locales": {
        "en": {
          "title": "Machine size",
          "purpose": "Select a planning size and inspect the actual machine and disk in the deployment plan.",
          "when": "When configuring or checking this setting for a client installation.",
          "steps": [
            "Open the client wizard and choose Hosting and installation.",
            "Review machine size against the client’s approved requirements. Example: standard.",
            "Enter or select the value, then choose Next or Save draft and check the save confirmation.",
            "Review the effective configuration and remaining prerequisites before making live changes."
          ],
          "permissions": "Operators and admins can configure and run actions. Partners can only inspect their owned clients.",
          "limits": "Availability depends on the selected infrastructure root, account rights, image architecture and reviewed cloud plan. A saved option creates no resource and includes no agreed price.",
          "example": "standard"
        },
        "nl": {
          "title": "Machinegrootte",
          "purpose": "Kies een planningsgrootte en controleer de echte machine en schijf in het installatieplan.",
          "when": "Wanneer je deze instelling voor een klantinstallatie configureert of controleert.",
          "steps": [
            "Open de klantwizard en kies Hosting en installatie.",
            "Beoordeel machinegrootte aan de hand van de goedgekeurde klanteisen. Voorbeeld: standard.",
            "Vul de waarde in of selecteer deze, kies Volgende of Concept opslaan en controleer de bevestiging.",
            "Beoordeel de effectieve configuratie en resterende voorwaarden voordat je live wijzigingen uitvoert."
          ],
          "permissions": "Operators en admins kunnen configureren en acties uitvoeren. Partners bekijken alleen hun eigen klanten.",
          "limits": "Beschikbaarheid hangt af van de infrastructuurvariant, accountrechten, imagearchitectuur en het beoordeelde cloudplan. Een opgeslagen optie maakt geen middel aan en bevat geen afgesproken prijs.",
          "example": "standard"
        }
      }
    },
    {
      "id": "msp.wizard.target.placement",
      "area": "target",
      "status": "conditional",
      "conditions": [
        "configuration_only"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.wizard.target.placement"
      ],
      "source_refs": [
        "apps/cockpit/frontend/src/wizard/StepTarget.jsx"
      ],
      "related": [
        "msp.wizard.review.review"
      ],
      "locales": {
        "en": {
          "title": "Location and access",
          "purpose": "Group the region, domain, SSH range and disk settings before reviewing infrastructure.",
          "when": "When configuring or checking this setting for a client installation.",
          "steps": [
            "Open the client wizard and choose Hosting and installation.",
            "Review location and access against the client’s approved requirements. Example: EU region, restricted SSH.",
            "Enter or select the value, then choose Next or Save draft and check the save confirmation.",
            "Review the effective configuration and remaining prerequisites before making live changes."
          ],
          "permissions": "Operators and admins can configure and run actions. Partners can only inspect their owned clients.",
          "limits": "Availability depends on the selected infrastructure root, account rights, image architecture and reviewed cloud plan. A saved option creates no resource and includes no agreed price.",
          "example": "EU region, restricted SSH"
        },
        "nl": {
          "title": "Locatie en toegang",
          "purpose": "Controleer regio, domein, SSH-bereik en schijf voordat je de infrastructuur beoordeelt.",
          "when": "Wanneer je deze instelling voor een klantinstallatie configureert of controleert.",
          "steps": [
            "Open de klantwizard en kies Hosting en installatie.",
            "Beoordeel locatie en toegang aan de hand van de goedgekeurde klanteisen. Voorbeeld: EU-regio, afgeschermde SSH.",
            "Vul de waarde in of selecteer deze, kies Volgende of Concept opslaan en controleer de bevestiging.",
            "Beoordeel de effectieve configuratie en resterende voorwaarden voordat je live wijzigingen uitvoert."
          ],
          "permissions": "Operators en admins kunnen configureren en acties uitvoeren. Partners bekijken alleen hun eigen klanten.",
          "limits": "Beschikbaarheid hangt af van de infrastructuurvariant, accountrechten, imagearchitectuur en het beoordeelde cloudplan. Een opgeslagen optie maakt geen middel aan en bevat geen afgesproken prijs.",
          "example": "EU-regio, afgeschermde SSH"
        }
      }
    },
    {
      "id": "msp.wizard.target.region",
      "area": "target",
      "status": "conditional",
      "conditions": [
        "configuration_only"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.wizard.target.region"
      ],
      "source_refs": [
        "apps/cockpit/frontend/src/wizard/StepTarget.jsx"
      ],
      "related": [
        "msp.wizard.review.review"
      ],
      "locales": {
        "en": {
          "title": "Cloud region",
          "purpose": "Choose the cloud region where the resources should be created.",
          "when": "When configuring or checking this setting for a client installation.",
          "steps": [
            "Open the client wizard and choose Hosting and installation.",
            "Review cloud region against the client’s approved requirements. Example: nl-ams.",
            "Enter or select the value, then choose Next or Save draft and check the save confirmation.",
            "Review the effective configuration and remaining prerequisites before making live changes."
          ],
          "permissions": "Operators and admins can configure and run actions. Partners can only inspect their owned clients.",
          "limits": "Availability depends on the selected infrastructure root, account rights, image architecture and reviewed cloud plan. A saved option creates no resource and includes no agreed price.",
          "example": "nl-ams"
        },
        "nl": {
          "title": "Cloudregio",
          "purpose": "Kies de cloudregio waar de middelen moeten worden aangemaakt.",
          "when": "Wanneer je deze instelling voor een klantinstallatie configureert of controleert.",
          "steps": [
            "Open de klantwizard en kies Hosting en installatie.",
            "Beoordeel cloudregio aan de hand van de goedgekeurde klanteisen. Voorbeeld: nl-ams.",
            "Vul de waarde in of selecteer deze, kies Volgende of Concept opslaan en controleer de bevestiging.",
            "Beoordeel de effectieve configuratie en resterende voorwaarden voordat je live wijzigingen uitvoert."
          ],
          "permissions": "Operators en admins kunnen configureren en acties uitvoeren. Partners bekijken alleen hun eigen klanten.",
          "limits": "Beschikbaarheid hangt af van de infrastructuurvariant, accountrechten, imagearchitectuur en het beoordeelde cloudplan. Een opgeslagen optie maakt geen middel aan en bevat geen afgesproken prijs.",
          "example": "nl-ams"
        }
      }
    },
    {
      "id": "msp.wizard.target.zone",
      "area": "target",
      "status": "conditional",
      "conditions": [
        "configuration_only"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.wizard.target.zone"
      ],
      "source_refs": [
        "apps/cockpit/frontend/src/wizard/StepTarget.jsx"
      ],
      "related": [
        "msp.wizard.review.review"
      ],
      "locales": {
        "en": {
          "title": "Availability zone",
          "purpose": "Choose a supported zone inside the selected cloud region.",
          "when": "When configuring or checking this setting for a client installation.",
          "steps": [
            "Open the client wizard and choose Hosting and installation.",
            "Review availability zone against the client’s approved requirements. Example: nl-ams-1.",
            "Enter or select the value, then choose Next or Save draft and check the save confirmation.",
            "Review the effective configuration and remaining prerequisites before making live changes."
          ],
          "permissions": "Operators and admins can configure and run actions. Partners can only inspect their owned clients.",
          "limits": "Availability depends on the selected infrastructure root, account rights, image architecture and reviewed cloud plan. A saved option creates no resource and includes no agreed price.",
          "example": "nl-ams-1"
        },
        "nl": {
          "title": "Beschikbaarheidszone",
          "purpose": "Kies een ondersteunde zone binnen de cloudregio.",
          "when": "Wanneer je deze instelling voor een klantinstallatie configureert of controleert.",
          "steps": [
            "Open de klantwizard en kies Hosting en installatie.",
            "Beoordeel beschikbaarheidszone aan de hand van de goedgekeurde klanteisen. Voorbeeld: nl-ams-1.",
            "Vul de waarde in of selecteer deze, kies Volgende of Concept opslaan en controleer de bevestiging.",
            "Beoordeel de effectieve configuratie en resterende voorwaarden voordat je live wijzigingen uitvoert."
          ],
          "permissions": "Operators en admins kunnen configureren en acties uitvoeren. Partners bekijken alleen hun eigen klanten.",
          "limits": "Beschikbaarheid hangt af van de infrastructuurvariant, accountrechten, imagearchitectuur en het beoordeelde cloudplan. Een opgeslagen optie maakt geen middel aan en bevat geen afgesproken prijs.",
          "example": "nl-ams-1"
        }
      }
    },
    {
      "id": "msp.wizard.target.domain",
      "area": "target",
      "status": "conditional",
      "conditions": [
        "configuration_only"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.wizard.target.domain"
      ],
      "source_refs": [
        "apps/cockpit/frontend/src/wizard/StepTarget.jsx"
      ],
      "related": [
        "msp.wizard.review.review"
      ],
      "locales": {
        "en": {
          "title": "Public domain",
          "purpose": "Configure the domain used by the public reverse proxy when public ingress is required.",
          "when": "When configuring or checking this setting for a client installation.",
          "steps": [
            "Open the client wizard and choose Hosting and installation.",
            "Review public domain against the client’s approved requirements. Example: ai.acme.example.",
            "Enter or select the value, then choose Next or Save draft and check the save confirmation.",
            "Review the effective configuration and remaining prerequisites before making live changes."
          ],
          "permissions": "Operators and admins can configure and run actions. Partners can only inspect their owned clients.",
          "limits": "Availability depends on the selected infrastructure root, account rights, image architecture and reviewed cloud plan. A saved option creates no resource and includes no agreed price.",
          "example": "ai.acme.example"
        },
        "nl": {
          "title": "Publiek domein",
          "purpose": "Stel het domein voor de publieke reverse proxy in als publieke toegang nodig is.",
          "when": "Wanneer je deze instelling voor een klantinstallatie configureert of controleert.",
          "steps": [
            "Open de klantwizard en kies Hosting en installatie.",
            "Beoordeel publiek domein aan de hand van de goedgekeurde klanteisen. Voorbeeld: ai.acme.example.",
            "Vul de waarde in of selecteer deze, kies Volgende of Concept opslaan en controleer de bevestiging.",
            "Beoordeel de effectieve configuratie en resterende voorwaarden voordat je live wijzigingen uitvoert."
          ],
          "permissions": "Operators en admins kunnen configureren en acties uitvoeren. Partners bekijken alleen hun eigen klanten.",
          "limits": "Beschikbaarheid hangt af van de infrastructuurvariant, accountrechten, imagearchitectuur en het beoordeelde cloudplan. Een opgeslagen optie maakt geen middel aan en bevat geen afgesproken prijs.",
          "example": "ai.acme.example"
        }
      }
    },
    {
      "id": "msp.wizard.target.tlsEmail",
      "area": "target",
      "status": "conditional",
      "conditions": [
        "configuration_only"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.wizard.target.tlsEmail"
      ],
      "source_refs": [
        "apps/cockpit/frontend/src/wizard/StepTarget.jsx"
      ],
      "related": [
        "msp.wizard.review.review"
      ],
      "locales": {
        "en": {
          "title": "Certificate contact",
          "purpose": "Provide a monitored contact address for certificate operations.",
          "when": "When configuring or checking this setting for a client installation.",
          "steps": [
            "Open the client wizard and choose Hosting and installation.",
            "Review certificate contact against the client’s approved requirements. Example: ops@acme.example.",
            "Enter or select the value, then choose Next or Save draft and check the save confirmation.",
            "Review the effective configuration and remaining prerequisites before making live changes."
          ],
          "permissions": "Operators and admins can configure and run actions. Partners can only inspect their owned clients.",
          "limits": "Availability depends on the selected infrastructure root, account rights, image architecture and reviewed cloud plan. A saved option creates no resource and includes no agreed price.",
          "example": "ops@acme.example"
        },
        "nl": {
          "title": "Certificaatcontact",
          "purpose": "Geef een bewaakt contactadres op voor certificaatbeheer.",
          "when": "Wanneer je deze instelling voor een klantinstallatie configureert of controleert.",
          "steps": [
            "Open de klantwizard en kies Hosting en installatie.",
            "Beoordeel certificaatcontact aan de hand van de goedgekeurde klanteisen. Voorbeeld: ops@acme.example.",
            "Vul de waarde in of selecteer deze, kies Volgende of Concept opslaan en controleer de bevestiging.",
            "Beoordeel de effectieve configuratie en resterende voorwaarden voordat je live wijzigingen uitvoert."
          ],
          "permissions": "Operators en admins kunnen configureren en acties uitvoeren. Partners bekijken alleen hun eigen klanten.",
          "limits": "Beschikbaarheid hangt af van de infrastructuurvariant, accountrechten, imagearchitectuur en het beoordeelde cloudplan. Een opgeslagen optie maakt geen middel aan en bevat geen afgesproken prijs.",
          "example": "ops@acme.example"
        }
      }
    },
    {
      "id": "msp.wizard.target.sshCidr",
      "area": "target",
      "status": "conditional",
      "conditions": [
        "configuration_only"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.wizard.target.sshCidr"
      ],
      "source_refs": [
        "apps/cockpit/frontend/src/wizard/StepTarget.jsx"
      ],
      "related": [
        "msp.wizard.review.review"
      ],
      "locales": {
        "en": {
          "title": "SSH source range",
          "purpose": "Limit the source network allowed to reach the cloud SSH port.",
          "when": "When configuring or checking this setting for a client installation.",
          "steps": [
            "Open the client wizard and choose Hosting and installation.",
            "Review ssh source range against the client’s approved requirements. Example: 203.0.113.10/32.",
            "Enter or select the value, then choose Next or Save draft and check the save confirmation.",
            "Review the effective configuration and remaining prerequisites before making live changes."
          ],
          "permissions": "Operators and admins can configure and run actions. Partners can only inspect their owned clients.",
          "limits": "Availability depends on the selected infrastructure root, account rights, image architecture and reviewed cloud plan. A saved option creates no resource and includes no agreed price.",
          "example": "203.0.113.10/32"
        },
        "nl": {
          "title": "SSH-bronbereik",
          "purpose": "Beperk het bronnetwerk dat de SSH-poort van de cloudmachine mag bereiken.",
          "when": "Wanneer je deze instelling voor een klantinstallatie configureert of controleert.",
          "steps": [
            "Open de klantwizard en kies Hosting en installatie.",
            "Beoordeel ssh-bronbereik aan de hand van de goedgekeurde klanteisen. Voorbeeld: 203.0.113.10/32.",
            "Vul de waarde in of selecteer deze, kies Volgende of Concept opslaan en controleer de bevestiging.",
            "Beoordeel de effectieve configuratie en resterende voorwaarden voordat je live wijzigingen uitvoert."
          ],
          "permissions": "Operators en admins kunnen configureren en acties uitvoeren. Partners bekijken alleen hun eigen klanten.",
          "limits": "Beschikbaarheid hangt af van de infrastructuurvariant, accountrechten, imagearchitectuur en het beoordeelde cloudplan. Een opgeslagen optie maakt geen middel aan en bevat geen afgesproken prijs.",
          "example": "203.0.113.10/32"
        }
      }
    },
    {
      "id": "msp.wizard.target.dataDisk",
      "area": "target",
      "status": "conditional",
      "conditions": [
        "configuration_only"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.wizard.target.dataDisk"
      ],
      "source_refs": [
        "apps/cockpit/frontend/src/wizard/StepTarget.jsx"
      ],
      "related": [
        "msp.wizard.review.review"
      ],
      "locales": {
        "en": {
          "title": "Data disk capacity",
          "purpose": "Set the durable data disk size used by the selected Terraform root.",
          "when": "When configuring or checking this setting for a client installation.",
          "steps": [
            "Open the client wizard and choose Hosting and installation.",
            "Review data disk capacity against the client’s approved requirements. Example: 200 GB.",
            "Enter or select the value, then choose Next or Save draft and check the save confirmation.",
            "Review the effective configuration and remaining prerequisites before making live changes."
          ],
          "permissions": "Operators and admins can configure and run actions. Partners can only inspect their owned clients.",
          "limits": "Availability depends on the selected infrastructure root, account rights, image architecture and reviewed cloud plan. A saved option creates no resource and includes no agreed price. Increasing capacity may be possible after review; shrinking an existing data disk is not a routine operation.",
          "example": "200 GB"
        },
        "nl": {
          "title": "Capaciteit van de gegevensschijf",
          "purpose": "Stel de grootte in van de blijvende gegevensschijf van de gekozen Terraformvariant.",
          "when": "Wanneer je deze instelling voor een klantinstallatie configureert of controleert.",
          "steps": [
            "Open de klantwizard en kies Hosting en installatie.",
            "Beoordeel capaciteit van de gegevensschijf aan de hand van de goedgekeurde klanteisen. Voorbeeld: 200 GB.",
            "Vul de waarde in of selecteer deze, kies Volgende of Concept opslaan en controleer de bevestiging.",
            "Beoordeel de effectieve configuratie en resterende voorwaarden voordat je live wijzigingen uitvoert."
          ],
          "permissions": "Operators en admins kunnen configureren en acties uitvoeren. Partners bekijken alleen hun eigen klanten.",
          "limits": "Beschikbaarheid hangt af van de infrastructuurvariant, accountrechten, imagearchitectuur en het beoordeelde cloudplan. Een opgeslagen optie maakt geen middel aan en bevat geen afgesproken prijs. Vergroten kan na beoordeling mogelijk zijn; een bestaande gegevensschijf verkleinen is geen gewone beheeractie.",
          "example": "200 GB"
        }
      }
    },
    {
      "id": "msp.wizard.target.cloudSettings",
      "area": "target",
      "status": "conditional",
      "conditions": [
        "configuration_only"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.wizard.target.cloudSettings"
      ],
      "source_refs": [
        "apps/cockpit/frontend/src/wizard/StepTarget.jsx"
      ],
      "related": [
        "msp.wizard.review.review"
      ],
      "locales": {
        "en": {
          "title": "Cloud account settings",
          "purpose": "Enter the non-secret project, organisation or resource-group fields required by the chosen root.",
          "when": "When configuring or checking this setting for a client installation.",
          "steps": [
            "Open the client wizard and choose Hosting and installation.",
            "Review cloud account settings against the client’s approved requirements. Example: client project ID.",
            "Enter or select the value, then choose Next or Save draft and check the save confirmation.",
            "Review the effective configuration and remaining prerequisites before making live changes."
          ],
          "permissions": "Operators and admins can configure and run actions. Partners can only inspect their owned clients.",
          "limits": "Availability depends on the selected infrastructure root, account rights, image architecture and reviewed cloud plan. A saved option creates no resource and includes no agreed price.",
          "example": "client project ID"
        },
        "nl": {
          "title": "Cloudaccountinstellingen",
          "purpose": "Vul de niet-geheime project-, organisatie- of resourcegroepvelden van de gekozen variant in.",
          "when": "Wanneer je deze instelling voor een klantinstallatie configureert of controleert.",
          "steps": [
            "Open de klantwizard en kies Hosting en installatie.",
            "Beoordeel cloudaccountinstellingen aan de hand van de goedgekeurde klanteisen. Voorbeeld: project-ID van de klant.",
            "Vul de waarde in of selecteer deze, kies Volgende of Concept opslaan en controleer de bevestiging.",
            "Beoordeel de effectieve configuratie en resterende voorwaarden voordat je live wijzigingen uitvoert."
          ],
          "permissions": "Operators en admins kunnen configureren en acties uitvoeren. Partners bekijken alleen hun eigen klanten.",
          "limits": "Beschikbaarheid hangt af van de infrastructuurvariant, accountrechten, imagearchitectuur en het beoordeelde cloudplan. Een opgeslagen optie maakt geen middel aan en bevat geen afgesproken prijs.",
          "example": "project-ID van de klant"
        }
      }
    },
    {
      "id": "msp.wizard.target.cmk",
      "area": "target",
      "status": "conditional",
      "conditions": [
        "configuration_only"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.wizard.target.cmk"
      ],
      "source_refs": [
        "apps/cockpit/frontend/src/wizard/StepTarget.jsx"
      ],
      "related": [
        "msp.wizard.review.review"
      ],
      "locales": {
        "en": {
          "title": "Customer-managed encryption key",
          "purpose": "Request cloud encryption with a customer-managed key when the selected root supports it.",
          "when": "When configuring or checking this setting for a client installation.",
          "steps": [
            "Open the client wizard and choose Hosting and installation.",
            "Review customer-managed encryption key against the client’s approved requirements. Example: enable_cmk=true.",
            "Enter or select the value, then choose Next or Save draft and check the save confirmation.",
            "Review the effective configuration and remaining prerequisites before making live changes."
          ],
          "permissions": "Operators and admins can configure and run actions. Partners can only inspect their owned clients.",
          "limits": "Availability depends on the selected infrastructure root, account rights, image architecture and reviewed cloud plan. A saved option creates no resource and includes no agreed price.",
          "example": "enable_cmk=true"
        },
        "nl": {
          "title": "Eigen encryptiesleutel",
          "purpose": "Vraag encryptie met een klantbeheerde sleutel aan als de gekozen variant dit ondersteunt.",
          "when": "Wanneer je deze instelling voor een klantinstallatie configureert of controleert.",
          "steps": [
            "Open de klantwizard en kies Hosting en installatie.",
            "Beoordeel eigen encryptiesleutel aan de hand van de goedgekeurde klanteisen. Voorbeeld: enable_cmk=true.",
            "Vul de waarde in of selecteer deze, kies Volgende of Concept opslaan en controleer de bevestiging.",
            "Beoordeel de effectieve configuratie en resterende voorwaarden voordat je live wijzigingen uitvoert."
          ],
          "permissions": "Operators en admins kunnen configureren en acties uitvoeren. Partners bekijken alleen hun eigen klanten.",
          "limits": "Beschikbaarheid hangt af van de infrastructuurvariant, accountrechten, imagearchitectuur en het beoordeelde cloudplan. Een opgeslagen optie maakt geen middel aan en bevat geen afgesproken prijs.",
          "example": "enable_cmk=true"
        }
      }
    },
    {
      "id": "msp.wizard.target.accountControls",
      "area": "target",
      "status": "conditional",
      "conditions": [
        "configuration_only"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.wizard.target.accountControls"
      ],
      "source_refs": [
        "apps/cockpit/frontend/src/wizard/StepTarget.jsx"
      ],
      "related": [
        "msp.wizard.review.review"
      ],
      "locales": {
        "en": {
          "title": "Account security controls",
          "purpose": "Select supported account-level controls only with the required organisation permissions.",
          "when": "When configuring or checking this setting for a client installation.",
          "steps": [
            "Open the client wizard and choose Hosting and installation.",
            "Review account security controls against the client’s approved requirements. Example: Terraform root default.",
            "Enter or select the value, then choose Next or Save draft and check the save confirmation.",
            "Review the effective configuration and remaining prerequisites before making live changes."
          ],
          "permissions": "Operators and admins can configure and run actions. Partners can only inspect their owned clients.",
          "limits": "Availability depends on the selected infrastructure root, account rights, image architecture and reviewed cloud plan. A saved option creates no resource and includes no agreed price.",
          "example": "Terraform root default"
        },
        "nl": {
          "title": "Beveiligingsmaatregelen voor het account",
          "purpose": "Kies ondersteunde accountmaatregelen alleen met de vereiste organisatierechten.",
          "when": "Wanneer je deze instelling voor een klantinstallatie configureert of controleert.",
          "steps": [
            "Open de klantwizard en kies Hosting en installatie.",
            "Beoordeel beveiligingsmaatregelen voor het account aan de hand van de goedgekeurde klanteisen. Voorbeeld: standaard van de Terraformvariant.",
            "Vul de waarde in of selecteer deze, kies Volgende of Concept opslaan en controleer de bevestiging.",
            "Beoordeel de effectieve configuratie en resterende voorwaarden voordat je live wijzigingen uitvoert."
          ],
          "permissions": "Operators en admins kunnen configureren en acties uitvoeren. Partners bekijken alleen hun eigen klanten.",
          "limits": "Beschikbaarheid hangt af van de infrastructuurvariant, accountrechten, imagearchitectuur en het beoordeelde cloudplan. Een opgeslagen optie maakt geen middel aan en bevat geen afgesproken prijs.",
          "example": "standaard van de Terraformvariant"
        }
      }
    },
    {
      "id": "msp.wizard.target.retention",
      "area": "target",
      "status": "conditional",
      "conditions": [
        "configuration_only"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.wizard.target.retention"
      ],
      "source_refs": [
        "apps/cockpit/frontend/src/wizard/StepTarget.jsx"
      ],
      "related": [
        "msp.wizard.review.review"
      ],
      "locales": {
        "en": {
          "title": "Infrastructure retention",
          "purpose": "Configure the selected root’s log, audit or backup retention period.",
          "when": "When configuring or checking this setting for a client installation.",
          "steps": [
            "Open the client wizard and choose Hosting and installation.",
            "Review infrastructure retention against the client’s approved requirements. Example: approved retention in days.",
            "Enter or select the value, then choose Next or Save draft and check the save confirmation.",
            "Review the effective configuration and remaining prerequisites before making live changes."
          ],
          "permissions": "Operators and admins can configure and run actions. Partners can only inspect their owned clients.",
          "limits": "Availability depends on the selected infrastructure root, account rights, image architecture and reviewed cloud plan. A saved option creates no resource and includes no agreed price.",
          "example": "approved retention in days"
        },
        "nl": {
          "title": "Bewaartermijnen voor infrastructuur",
          "purpose": "Stel de bewaartermijn voor logs, auditgegevens of back-ups van de gekozen variant in.",
          "when": "Wanneer je deze instelling voor een klantinstallatie configureert of controleert.",
          "steps": [
            "Open de klantwizard en kies Hosting en installatie.",
            "Beoordeel bewaartermijnen voor infrastructuur aan de hand van de goedgekeurde klanteisen. Voorbeeld: goedgekeurde bewaartermijn in dagen.",
            "Vul de waarde in of selecteer deze, kies Volgende of Concept opslaan en controleer de bevestiging.",
            "Beoordeel de effectieve configuratie en resterende voorwaarden voordat je live wijzigingen uitvoert."
          ],
          "permissions": "Operators en admins kunnen configureren en acties uitvoeren. Partners bekijken alleen hun eigen klanten.",
          "limits": "Beschikbaarheid hangt af van de infrastructuurvariant, accountrechten, imagearchitectuur en het beoordeelde cloudplan. Een opgeslagen optie maakt geen middel aan en bevat geen afgesproken prijs.",
          "example": "goedgekeurde bewaartermijn in dagen"
        }
      }
    },
    {
      "id": "msp.wizard.target.managed",
      "area": "target",
      "status": "conditional",
      "conditions": [
        "configuration_only"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.wizard.target.managed"
      ],
      "source_refs": [
        "apps/cockpit/frontend/src/wizard/StepTarget.jsx"
      ],
      "related": [
        "msp.wizard.review.review"
      ],
      "locales": {
        "en": {
          "title": "Managed cloud services",
          "purpose": "Review optional provider-managed databases and storage before including them in the plan.",
          "when": "When configuring or checking this setting for a client installation.",
          "steps": [
            "Open the client wizard and choose Hosting and installation.",
            "Review managed cloud services against the client’s approved requirements. Example: managed database and storage.",
            "Enter or select the value, then choose Next or Save draft and check the save confirmation.",
            "Review the effective configuration and remaining prerequisites before making live changes."
          ],
          "permissions": "Operators and admins can configure and run actions. Partners can only inspect their owned clients.",
          "limits": "Availability depends on the selected infrastructure root, account rights, image architecture and reviewed cloud plan. A saved option creates no resource and includes no agreed price.",
          "example": "managed database and storage"
        },
        "nl": {
          "title": "Beheerde clouddiensten",
          "purpose": "Beoordeel optionele beheerde databases en opslag voordat je ze in het plan opneemt.",
          "when": "Wanneer je deze instelling voor een klantinstallatie configureert of controleert.",
          "steps": [
            "Open de klantwizard en kies Hosting en installatie.",
            "Beoordeel beheerde clouddiensten aan de hand van de goedgekeurde klanteisen. Voorbeeld: beheerde database en opslag.",
            "Vul de waarde in of selecteer deze, kies Volgende of Concept opslaan en controleer de bevestiging.",
            "Beoordeel de effectieve configuratie en resterende voorwaarden voordat je live wijzigingen uitvoert."
          ],
          "permissions": "Operators en admins kunnen configureren en acties uitvoeren. Partners bekijken alleen hun eigen klanten.",
          "limits": "Beschikbaarheid hangt af van de infrastructuurvariant, accountrechten, imagearchitectuur en het beoordeelde cloudplan. Een opgeslagen optie maakt geen middel aan en bevat geen afgesproken prijs.",
          "example": "beheerde database en opslag"
        }
      }
    },
    {
      "id": "msp.wizard.target.managedPostgres",
      "area": "target",
      "status": "conditional",
      "conditions": [
        "configuration_only"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.wizard.target.managedPostgres"
      ],
      "source_refs": [
        "apps/cockpit/frontend/src/wizard/StepTarget.jsx"
      ],
      "related": [
        "msp.wizard.review.review"
      ],
      "locales": {
        "en": {
          "title": "Managed PostgreSQL",
          "purpose": "Request the supported cloud database instead of the bundled PostgreSQL container.",
          "when": "When configuring or checking this setting for a client installation.",
          "steps": [
            "Open the client wizard and choose Hosting and installation.",
            "Review managed postgresql against the client’s approved requirements. Example: managed_postgres=true.",
            "Enter or select the value, then choose Next or Save draft and check the save confirmation.",
            "Review the effective configuration and remaining prerequisites before making live changes."
          ],
          "permissions": "Operators and admins can configure and run actions. Partners can only inspect their owned clients.",
          "limits": "Availability depends on the selected infrastructure root, account rights, image architecture and reviewed cloud plan. A saved option creates no resource and includes no agreed price.",
          "example": "managed_postgres=true"
        },
        "nl": {
          "title": "Beheerde PostgreSQL",
          "purpose": "Vraag de ondersteunde clouddatabase aan in plaats van de meegeleverde PostgreSQL-container.",
          "when": "Wanneer je deze instelling voor een klantinstallatie configureert of controleert.",
          "steps": [
            "Open de klantwizard en kies Hosting en installatie.",
            "Beoordeel beheerde postgresql aan de hand van de goedgekeurde klanteisen. Voorbeeld: managed_postgres=true.",
            "Vul de waarde in of selecteer deze, kies Volgende of Concept opslaan en controleer de bevestiging.",
            "Beoordeel de effectieve configuratie en resterende voorwaarden voordat je live wijzigingen uitvoert."
          ],
          "permissions": "Operators en admins kunnen configureren en acties uitvoeren. Partners bekijken alleen hun eigen klanten.",
          "limits": "Beschikbaarheid hangt af van de infrastructuurvariant, accountrechten, imagearchitectuur en het beoordeelde cloudplan. Een opgeslagen optie maakt geen middel aan en bevat geen afgesproken prijs.",
          "example": "managed_postgres=true"
        }
      }
    },
    {
      "id": "msp.wizard.target.managedStorage",
      "area": "target",
      "status": "conditional",
      "conditions": [
        "configuration_only"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.wizard.target.managedStorage"
      ],
      "source_refs": [
        "apps/cockpit/frontend/src/wizard/StepTarget.jsx"
      ],
      "related": [
        "msp.wizard.review.review"
      ],
      "locales": {
        "en": {
          "title": "Managed object storage",
          "purpose": "Request supported cloud object storage for configured backup and artifact workflows.",
          "when": "When configuring or checking this setting for a client installation.",
          "steps": [
            "Open the client wizard and choose Hosting and installation.",
            "Review managed object storage against the client’s approved requirements. Example: managed_object_storage=true.",
            "Enter or select the value, then choose Next or Save draft and check the save confirmation.",
            "Review the effective configuration and remaining prerequisites before making live changes."
          ],
          "permissions": "Operators and admins can configure and run actions. Partners can only inspect their owned clients.",
          "limits": "Availability depends on the selected infrastructure root, account rights, image architecture and reviewed cloud plan. A saved option creates no resource and includes no agreed price.",
          "example": "managed_object_storage=true"
        },
        "nl": {
          "title": "Beheerde objectopslag",
          "purpose": "Vraag ondersteunde objectopslag aan voor ingerichte back-up- en bestandsprocessen.",
          "when": "Wanneer je deze instelling voor een klantinstallatie configureert of controleert.",
          "steps": [
            "Open de klantwizard en kies Hosting en installatie.",
            "Beoordeel beheerde objectopslag aan de hand van de goedgekeurde klanteisen. Voorbeeld: managed_object_storage=true.",
            "Vul de waarde in of selecteer deze, kies Volgende of Concept opslaan en controleer de bevestiging.",
            "Beoordeel de effectieve configuratie en resterende voorwaarden voordat je live wijzigingen uitvoert."
          ],
          "permissions": "Operators en admins kunnen configureren en acties uitvoeren. Partners bekijken alleen hun eigen klanten.",
          "limits": "Beschikbaarheid hangt af van de infrastructuurvariant, accountrechten, imagearchitectuur en het beoordeelde cloudplan. Een opgeslagen optie maakt geen middel aan en bevat geen afgesproken prijs.",
          "example": "managed_object_storage=true"
        }
      }
    },
    {
      "id": "msp.wizard.target.companion",
      "area": "target",
      "status": "conditional",
      "conditions": [
        "configuration_only"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.wizard.target.companion"
      ],
      "source_refs": [
        "apps/cockpit/frontend/src/wizard/StepTarget.jsx"
      ],
      "related": [
        "msp.wizard.review.review"
      ],
      "locales": {
        "en": {
          "title": "Companion machine",
          "purpose": "Plan a second machine for selected heavy services.",
          "when": "When configuring or checking this setting for a client installation.",
          "steps": [
            "Open the client wizard and choose Hosting and installation.",
            "Review companion machine against the client’s approved requirements. Example: companion enabled.",
            "Enter or select the value, then choose Next or Save draft and check the save confirmation.",
            "Review the effective configuration and remaining prerequisites before making live changes."
          ],
          "permissions": "Operators and admins can configure and run actions. Partners can only inspect their owned clients.",
          "limits": "Availability depends on the selected infrastructure root, account rights, image architecture and reviewed cloud plan. A saved option creates no resource and includes no agreed price.",
          "example": "companion enabled"
        },
        "nl": {
          "title": "Extra servicemachine",
          "purpose": "Plan een tweede machine voor gekozen zware diensten.",
          "when": "Wanneer je deze instelling voor een klantinstallatie configureert of controleert.",
          "steps": [
            "Open de klantwizard en kies Hosting en installatie.",
            "Beoordeel extra servicemachine aan de hand van de goedgekeurde klanteisen. Voorbeeld: extra servicemachine ingeschakeld.",
            "Vul de waarde in of selecteer deze, kies Volgende of Concept opslaan en controleer de bevestiging.",
            "Beoordeel de effectieve configuratie en resterende voorwaarden voordat je live wijzigingen uitvoert."
          ],
          "permissions": "Operators en admins kunnen configureren en acties uitvoeren. Partners bekijken alleen hun eigen klanten.",
          "limits": "Beschikbaarheid hangt af van de infrastructuurvariant, accountrechten, imagearchitectuur en het beoordeelde cloudplan. Een opgeslagen optie maakt geen middel aan en bevat geen afgesproken prijs.",
          "example": "extra servicemachine ingeschakeld"
        }
      }
    },
    {
      "id": "msp.wizard.target.companionRag",
      "area": "target",
      "status": "conditional",
      "conditions": [
        "configuration_only"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.wizard.target.companionRag"
      ],
      "source_refs": [
        "apps/cockpit/frontend/src/wizard/StepTarget.jsx"
      ],
      "related": [
        "msp.wizard.review.review"
      ],
      "locales": {
        "en": {
          "title": "Knowledge service placement",
          "purpose": "Move the selected document-retrieval service to the companion machine.",
          "when": "When configuring or checking this setting for a client installation.",
          "steps": [
            "Open the client wizard and choose Hosting and installation.",
            "Review knowledge service placement against the client’s approved requirements. Example: rag on companion.",
            "Enter or select the value, then choose Next or Save draft and check the save confirmation.",
            "Review the effective configuration and remaining prerequisites before making live changes."
          ],
          "permissions": "Operators and admins can configure and run actions. Partners can only inspect their owned clients.",
          "limits": "Availability depends on the selected infrastructure root, account rights, image architecture and reviewed cloud plan. A saved option creates no resource and includes no agreed price.",
          "example": "rag on companion"
        },
        "nl": {
          "title": "Locatie van de kennisdienst",
          "purpose": "Plaats de gekozen dienst voor documentonderzoek op de extra machine.",
          "when": "Wanneer je deze instelling voor een klantinstallatie configureert of controleert.",
          "steps": [
            "Open de klantwizard en kies Hosting en installatie.",
            "Beoordeel locatie van de kennisdienst aan de hand van de goedgekeurde klanteisen. Voorbeeld: rag op de extra servicemachine.",
            "Vul de waarde in of selecteer deze, kies Volgende of Concept opslaan en controleer de bevestiging.",
            "Beoordeel de effectieve configuratie en resterende voorwaarden voordat je live wijzigingen uitvoert."
          ],
          "permissions": "Operators en admins kunnen configureren en acties uitvoeren. Partners bekijken alleen hun eigen klanten.",
          "limits": "Beschikbaarheid hangt af van de infrastructuurvariant, accountrechten, imagearchitectuur en het beoordeelde cloudplan. Een opgeslagen optie maakt geen middel aan en bevat geen afgesproken prijs.",
          "example": "rag op de extra servicemachine"
        }
      }
    },
    {
      "id": "msp.wizard.target.companionLangfuse",
      "area": "target",
      "status": "conditional",
      "conditions": [
        "configuration_only"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.wizard.target.companionLangfuse"
      ],
      "source_refs": [
        "apps/cockpit/frontend/src/wizard/StepTarget.jsx"
      ],
      "related": [
        "msp.wizard.review.review"
      ],
      "locales": {
        "en": {
          "title": "Telemetry service placement",
          "purpose": "Move the selected model-tracing service to the companion machine.",
          "when": "When configuring or checking this setting for a client installation.",
          "steps": [
            "Open the client wizard and choose Hosting and installation.",
            "Review telemetry service placement against the client’s approved requirements. Example: langfuse on companion.",
            "Enter or select the value, then choose Next or Save draft and check the save confirmation.",
            "Review the effective configuration and remaining prerequisites before making live changes."
          ],
          "permissions": "Operators and admins can configure and run actions. Partners can only inspect their owned clients.",
          "limits": "Availability depends on the selected infrastructure root, account rights, image architecture and reviewed cloud plan. A saved option creates no resource and includes no agreed price.",
          "example": "langfuse on companion"
        },
        "nl": {
          "title": "Locatie van de telemetriedienst",
          "purpose": "Plaats de gekozen dienst voor modeltracering op de extra machine.",
          "when": "Wanneer je deze instelling voor een klantinstallatie configureert of controleert.",
          "steps": [
            "Open de klantwizard en kies Hosting en installatie.",
            "Beoordeel locatie van de telemetriedienst aan de hand van de goedgekeurde klanteisen. Voorbeeld: langfuse op de extra servicemachine.",
            "Vul de waarde in of selecteer deze, kies Volgende of Concept opslaan en controleer de bevestiging.",
            "Beoordeel de effectieve configuratie en resterende voorwaarden voordat je live wijzigingen uitvoert."
          ],
          "permissions": "Operators en admins kunnen configureren en acties uitvoeren. Partners bekijken alleen hun eigen klanten.",
          "limits": "Beschikbaarheid hangt af van de infrastructuurvariant, accountrechten, imagearchitectuur en het beoordeelde cloudplan. Een opgeslagen optie maakt geen middel aan en bevat geen afgesproken prijs.",
          "example": "langfuse op de extra servicemachine"
        }
      }
    },
    {
      "id": "msp.wizard.modules.presets",
      "area": "modules",
      "status": "conditional",
      "conditions": [
        "configuration_only"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.wizard.modules.presets"
      ],
      "source_refs": [
        "apps/cockpit/frontend/src/wizard/StepModules.jsx"
      ],
      "related": [
        "msp.wizard.review.review"
      ],
      "locales": {
        "en": {
          "title": "Configuration presets",
          "purpose": "Apply a starting combination of service profiles, switches, router and size.",
          "when": "When configuring or checking this setting for a client installation.",
          "steps": [
            "Open the client wizard and choose Modules and services.",
            "Review configuration presets against the client’s approved requirements. Example: edge-device.",
            "Enter or select the value, then choose Next or Save draft and check the save confirmation.",
            "Review the effective configuration and remaining prerequisites before making live changes."
          ],
          "permissions": "Operators and admins can configure and run actions. Partners can only inspect their owned clients.",
          "limits": "A switch or profile is a configuration request. Runtime setup, compatible images, credentials and commercial entitlement must be checked separately.",
          "example": "edge-device"
        },
        "nl": {
          "title": "Configuratievoorinstellingen",
          "purpose": "Pas een begincombinatie van diensten, schakelaars, router en grootte toe.",
          "when": "Wanneer je deze instelling voor een klantinstallatie configureert of controleert.",
          "steps": [
            "Open de klantwizard en kies Modules en diensten.",
            "Beoordeel configuratievoorinstellingen aan de hand van de goedgekeurde klanteisen. Voorbeeld: edge-device.",
            "Vul de waarde in of selecteer deze, kies Volgende of Concept opslaan en controleer de bevestiging.",
            "Beoordeel de effectieve configuratie en resterende voorwaarden voordat je live wijzigingen uitvoert."
          ],
          "permissions": "Operators en admins kunnen configureren en acties uitvoeren. Partners bekijken alleen hun eigen klanten.",
          "limits": "Een schakelaar of profiel is een configuratieverzoek. Runtime-inrichting, geschikte images, sleutels en contractrechten moeten apart worden gecontroleerd.",
          "example": "edge-device"
        }
      }
    },
    {
      "id": "msp.wizard.modules.profiles",
      "area": "modules",
      "status": "conditional",
      "conditions": [
        "configuration_only"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.wizard.modules.profiles"
      ],
      "source_refs": [
        "apps/cockpit/frontend/src/wizard/StepModules.jsx"
      ],
      "related": [
        "msp.wizard.review.review"
      ],
      "locales": {
        "en": {
          "title": "Service profiles",
          "purpose": "Choose which container services the rendered deployment requests.",
          "when": "When configuring or checking this setting for a client installation.",
          "steps": [
            "Open the client wizard and choose Modules and services.",
            "Review service profiles against the client’s approved requirements. Example: webui, pgdb.",
            "Enter or select the value, then choose Next or Save draft and check the save confirmation.",
            "Review the effective configuration and remaining prerequisites before making live changes."
          ],
          "permissions": "Operators and admins can configure and run actions. Partners can only inspect their owned clients.",
          "limits": "A switch or profile is a configuration request. Runtime setup, compatible images, credentials and commercial entitlement must be checked separately.",
          "example": "webui, pgdb"
        },
        "nl": {
          "title": "Serviceprofielen",
          "purpose": "Kies welke containerdiensten de gegenereerde installatie aanvraagt.",
          "when": "Wanneer je deze instelling voor een klantinstallatie configureert of controleert.",
          "steps": [
            "Open de klantwizard en kies Modules en diensten.",
            "Beoordeel serviceprofielen aan de hand van de goedgekeurde klanteisen. Voorbeeld: webui, pgdb.",
            "Vul de waarde in of selecteer deze, kies Volgende of Concept opslaan en controleer de bevestiging.",
            "Beoordeel de effectieve configuratie en resterende voorwaarden voordat je live wijzigingen uitvoert."
          ],
          "permissions": "Operators en admins kunnen configureren en acties uitvoeren. Partners bekijken alleen hun eigen klanten.",
          "limits": "Een schakelaar of profiel is een configuratieverzoek. Runtime-inrichting, geschikte images, sleutels en contractrechten moeten apart worden gecontroleerd.",
          "example": "webui, pgdb"
        }
      }
    },
    {
      "id": "msp.wizard.modules.toggles",
      "area": "modules",
      "status": "conditional",
      "conditions": [
        "configuration_only"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.wizard.modules.toggles"
      ],
      "source_refs": [
        "apps/cockpit/frontend/src/wizard/StepModules.jsx"
      ],
      "related": [
        "msp.wizard.review.review"
      ],
      "locales": {
        "en": {
          "title": "Engine feature switches",
          "purpose": "Configure engine behaviour separately from the containers selected above.",
          "when": "When configuring or checking this setting for a client installation.",
          "steps": [
            "Open the client wizard and choose Modules and services.",
            "Review engine feature switches against the client’s approved requirements. Example: housekeeping enabled.",
            "Enter or select the value, then choose Next or Save draft and check the save confirmation.",
            "Review the effective configuration and remaining prerequisites before making live changes."
          ],
          "permissions": "Operators and admins can configure and run actions. Partners can only inspect their owned clients.",
          "limits": "A switch or profile is a configuration request. Runtime setup, compatible images, credentials and commercial entitlement must be checked separately.",
          "example": "housekeeping enabled"
        },
        "nl": {
          "title": "Functieschakelaars van de engine",
          "purpose": "Configureer enginegedrag afzonderlijk van de gekozen containers.",
          "when": "Wanneer je deze instelling voor een klantinstallatie configureert of controleert.",
          "steps": [
            "Open de klantwizard en kies Modules en diensten.",
            "Beoordeel functieschakelaars van de engine aan de hand van de goedgekeurde klanteisen. Voorbeeld: automatisch onderhoud ingeschakeld.",
            "Vul de waarde in of selecteer deze, kies Volgende of Concept opslaan en controleer de bevestiging.",
            "Beoordeel de effectieve configuratie en resterende voorwaarden voordat je live wijzigingen uitvoert."
          ],
          "permissions": "Operators en admins kunnen configureren en acties uitvoeren. Partners bekijken alleen hun eigen klanten.",
          "limits": "Een schakelaar of profiel is een configuratieverzoek. Runtime-inrichting, geschikte images, sleutels en contractrechten moeten apart worden gecontroleerd.",
          "example": "automatisch onderhoud ingeschakeld"
        }
      }
    },
    {
      "id": "msp.wizard.modules.toggle.dashboard",
      "area": "modules",
      "status": "conditional",
      "conditions": [
        "configuration_only"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.wizard.modules.toggle.dashboard"
      ],
      "source_refs": [
        "apps/cockpit/frontend/src/wizard/StepModules.jsx"
      ],
      "related": [
        "msp.wizard.review.review"
      ],
      "locales": {
        "en": {
          "title": "Dashboard switch",
          "purpose": "Request dashboard behaviour where the installed WebUI supports it.",
          "when": "When configuring or checking this setting for a client installation.",
          "steps": [
            "Open the client wizard and choose Modules and services.",
            "Review dashboard switch against the client’s approved requirements. Example: dashboard=true.",
            "Enter or select the value, then choose Next or Save draft and check the save confirmation.",
            "Review the effective configuration and remaining prerequisites before making live changes."
          ],
          "permissions": "Operators and admins can configure and run actions. Partners can only inspect their owned clients.",
          "limits": "A switch or profile is a configuration request. Runtime setup, compatible images, credentials and commercial entitlement must be checked separately.",
          "example": "dashboard=true"
        },
        "nl": {
          "title": "Dashboard inschakelen",
          "purpose": "Vraag dashboardgedrag aan waar de geïnstalleerde WebUI dit ondersteunt.",
          "when": "Wanneer je deze instelling voor een klantinstallatie configureert of controleert.",
          "steps": [
            "Open de klantwizard en kies Modules en diensten.",
            "Beoordeel dashboard inschakelen aan de hand van de goedgekeurde klanteisen. Voorbeeld: dashboard=true.",
            "Vul de waarde in of selecteer deze, kies Volgende of Concept opslaan en controleer de bevestiging.",
            "Beoordeel de effectieve configuratie en resterende voorwaarden voordat je live wijzigingen uitvoert."
          ],
          "permissions": "Operators en admins kunnen configureren en acties uitvoeren. Partners bekijken alleen hun eigen klanten.",
          "limits": "Een schakelaar of profiel is een configuratieverzoek. Runtime-inrichting, geschikte images, sleutels en contractrechten moeten apart worden gecontroleerd.",
          "example": "dashboard=true"
        }
      }
    },
    {
      "id": "msp.wizard.modules.toggle.messaging",
      "area": "modules",
      "status": "conditional",
      "conditions": [
        "configuration_only"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.wizard.modules.toggle.messaging"
      ],
      "source_refs": [
        "apps/cockpit/frontend/src/wizard/StepModules.jsx"
      ],
      "related": [
        "msp.wizard.review.review"
      ],
      "locales": {
        "en": {
          "title": "Messaging switch",
          "purpose": "Request messaging adapters; each channel still needs its own account configuration.",
          "when": "When configuring or checking this setting for a client installation.",
          "steps": [
            "Open the client wizard and choose Modules and services.",
            "Review messaging switch against the client’s approved requirements. Example: messaging=true.",
            "Enter or select the value, then choose Next or Save draft and check the save confirmation.",
            "Review the effective configuration and remaining prerequisites before making live changes."
          ],
          "permissions": "Operators and admins can configure and run actions. Partners can only inspect their owned clients.",
          "limits": "A switch or profile is a configuration request. Runtime setup, compatible images, credentials and commercial entitlement must be checked separately.",
          "example": "messaging=true"
        },
        "nl": {
          "title": "Berichtenkanalen inschakelen",
          "purpose": "Vraag berichtenadapters aan; ieder kanaal heeft daarnaast eigen accountinstellingen nodig.",
          "when": "Wanneer je deze instelling voor een klantinstallatie configureert of controleert.",
          "steps": [
            "Open de klantwizard en kies Modules en diensten.",
            "Beoordeel berichtenkanalen inschakelen aan de hand van de goedgekeurde klanteisen. Voorbeeld: messaging=true.",
            "Vul de waarde in of selecteer deze, kies Volgende of Concept opslaan en controleer de bevestiging.",
            "Beoordeel de effectieve configuratie en resterende voorwaarden voordat je live wijzigingen uitvoert."
          ],
          "permissions": "Operators en admins kunnen configureren en acties uitvoeren. Partners bekijken alleen hun eigen klanten.",
          "limits": "Een schakelaar of profiel is een configuratieverzoek. Runtime-inrichting, geschikte images, sleutels en contractrechten moeten apart worden gecontroleerd.",
          "example": "messaging=true"
        }
      }
    },
    {
      "id": "msp.wizard.modules.toggle.dreaming",
      "area": "modules",
      "status": "conditional",
      "conditions": [
        "configuration_only"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.wizard.modules.toggle.dreaming"
      ],
      "source_refs": [
        "apps/cockpit/frontend/src/wizard/StepModules.jsx"
      ],
      "related": [
        "msp.wizard.review.review"
      ],
      "locales": {
        "en": {
          "title": "Memory consolidation",
          "purpose": "Request scheduled memory consolidation where the runtime job is installed.",
          "when": "When configuring or checking this setting for a client installation.",
          "steps": [
            "Open the client wizard and choose Modules and services.",
            "Review memory consolidation against the client’s approved requirements. Example: dreaming=true.",
            "Enter or select the value, then choose Next or Save draft and check the save confirmation.",
            "Review the effective configuration and remaining prerequisites before making live changes."
          ],
          "permissions": "Operators and admins can configure and run actions. Partners can only inspect their owned clients.",
          "limits": "A switch or profile is a configuration request. Runtime setup, compatible images, credentials and commercial entitlement must be checked separately.",
          "example": "dreaming=true"
        },
        "nl": {
          "title": "Geheugenconsolidatie",
          "purpose": "Vraag geplande geheugenconsolidatie aan waar de bijbehorende taak is geïnstalleerd.",
          "when": "Wanneer je deze instelling voor een klantinstallatie configureert of controleert.",
          "steps": [
            "Open de klantwizard en kies Modules en diensten.",
            "Beoordeel geheugenconsolidatie aan de hand van de goedgekeurde klanteisen. Voorbeeld: dreaming=true.",
            "Vul de waarde in of selecteer deze, kies Volgende of Concept opslaan en controleer de bevestiging.",
            "Beoordeel de effectieve configuratie en resterende voorwaarden voordat je live wijzigingen uitvoert."
          ],
          "permissions": "Operators en admins kunnen configureren en acties uitvoeren. Partners bekijken alleen hun eigen klanten.",
          "limits": "Een schakelaar of profiel is een configuratieverzoek. Runtime-inrichting, geschikte images, sleutels en contractrechten moeten apart worden gecontroleerd.",
          "example": "dreaming=true"
        }
      }
    },
    {
      "id": "msp.wizard.modules.toggle.obsidian",
      "area": "modules",
      "status": "conditional",
      "conditions": [
        "configuration_only"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.wizard.modules.toggle.obsidian"
      ],
      "source_refs": [
        "apps/cockpit/frontend/src/wizard/StepModules.jsx"
      ],
      "related": [
        "msp.wizard.review.review"
      ],
      "locales": {
        "en": {
          "title": "Obsidian integration",
          "purpose": "Request the configured vault integration without granting access to an arbitrary vault.",
          "when": "When configuring or checking this setting for a client installation.",
          "steps": [
            "Open the client wizard and choose Modules and services.",
            "Review obsidian integration against the client’s approved requirements. Example: obsidian=true.",
            "Enter or select the value, then choose Next or Save draft and check the save confirmation.",
            "Review the effective configuration and remaining prerequisites before making live changes."
          ],
          "permissions": "Operators and admins can configure and run actions. Partners can only inspect their owned clients.",
          "limits": "A switch or profile is a configuration request. Runtime setup, compatible images, credentials and commercial entitlement must be checked separately.",
          "example": "obsidian=true"
        },
        "nl": {
          "title": "Obsidian-koppeling",
          "purpose": "Vraag de ingerichte kluiskoppeling aan zonder toegang tot willekeurige kluizen te verlenen.",
          "when": "Wanneer je deze instelling voor een klantinstallatie configureert of controleert.",
          "steps": [
            "Open de klantwizard en kies Modules en diensten.",
            "Beoordeel obsidian-koppeling aan de hand van de goedgekeurde klanteisen. Voorbeeld: obsidian=true.",
            "Vul de waarde in of selecteer deze, kies Volgende of Concept opslaan en controleer de bevestiging.",
            "Beoordeel de effectieve configuratie en resterende voorwaarden voordat je live wijzigingen uitvoert."
          ],
          "permissions": "Operators en admins kunnen configureren en acties uitvoeren. Partners bekijken alleen hun eigen klanten.",
          "limits": "Een schakelaar of profiel is een configuratieverzoek. Runtime-inrichting, geschikte images, sleutels en contractrechten moeten apart worden gecontroleerd.",
          "example": "obsidian=true"
        }
      }
    },
    {
      "id": "msp.wizard.modules.toggle.voice",
      "area": "modules",
      "status": "conditional",
      "conditions": [
        "configuration_only"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.wizard.modules.toggle.voice"
      ],
      "source_refs": [
        "apps/cockpit/frontend/src/wizard/StepModules.jsx"
      ],
      "related": [
        "msp.wizard.review.review"
      ],
      "locales": {
        "en": {
          "title": "Voice switch",
          "purpose": "Request speech features that also require a configured speech backend.",
          "when": "When configuring or checking this setting for a client installation.",
          "steps": [
            "Open the client wizard and choose Modules and services.",
            "Review voice switch against the client’s approved requirements. Example: voice=true.",
            "Enter or select the value, then choose Next or Save draft and check the save confirmation.",
            "Review the effective configuration and remaining prerequisites before making live changes."
          ],
          "permissions": "Operators and admins can configure and run actions. Partners can only inspect their owned clients.",
          "limits": "A switch or profile is a configuration request. Runtime setup, compatible images, credentials and commercial entitlement must be checked separately.",
          "example": "voice=true"
        },
        "nl": {
          "title": "Spraak inschakelen",
          "purpose": "Vraag spraakfuncties aan die ook een ingestelde spraakdienst nodig hebben.",
          "when": "Wanneer je deze instelling voor een klantinstallatie configureert of controleert.",
          "steps": [
            "Open de klantwizard en kies Modules en diensten.",
            "Beoordeel spraak inschakelen aan de hand van de goedgekeurde klanteisen. Voorbeeld: voice=true.",
            "Vul de waarde in of selecteer deze, kies Volgende of Concept opslaan en controleer de bevestiging.",
            "Beoordeel de effectieve configuratie en resterende voorwaarden voordat je live wijzigingen uitvoert."
          ],
          "permissions": "Operators en admins kunnen configureren en acties uitvoeren. Partners bekijken alleen hun eigen klanten.",
          "limits": "Een schakelaar of profiel is een configuratieverzoek. Runtime-inrichting, geschikte images, sleutels en contractrechten moeten apart worden gecontroleerd.",
          "example": "voice=true"
        }
      }
    },
    {
      "id": "msp.wizard.modules.toggle.housekeeping",
      "area": "modules",
      "status": "conditional",
      "conditions": [
        "configuration_only"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.wizard.modules.toggle.housekeeping"
      ],
      "source_refs": [
        "apps/cockpit/frontend/src/wizard/StepModules.jsx"
      ],
      "related": [
        "msp.wizard.review.review"
      ],
      "locales": {
        "en": {
          "title": "Housekeeping switch",
          "purpose": "Request recurring platform cleanup and health checks supported by the deployment.",
          "when": "When configuring or checking this setting for a client installation.",
          "steps": [
            "Open the client wizard and choose Modules and services.",
            "Review housekeeping switch against the client’s approved requirements. Example: housekeeping=true.",
            "Enter or select the value, then choose Next or Save draft and check the save confirmation.",
            "Review the effective configuration and remaining prerequisites before making live changes."
          ],
          "permissions": "Operators and admins can configure and run actions. Partners can only inspect their owned clients.",
          "limits": "A switch or profile is a configuration request. Runtime setup, compatible images, credentials and commercial entitlement must be checked separately.",
          "example": "housekeeping=true"
        },
        "nl": {
          "title": "Automatisch onderhoud",
          "purpose": "Vraag terugkerende opruim- en gezondheidscontroles aan die de installatie ondersteunt.",
          "when": "Wanneer je deze instelling voor een klantinstallatie configureert of controleert.",
          "steps": [
            "Open de klantwizard en kies Modules en diensten.",
            "Beoordeel automatisch onderhoud aan de hand van de goedgekeurde klanteisen. Voorbeeld: housekeeping=true.",
            "Vul de waarde in of selecteer deze, kies Volgende of Concept opslaan en controleer de bevestiging.",
            "Beoordeel de effectieve configuratie en resterende voorwaarden voordat je live wijzigingen uitvoert."
          ],
          "permissions": "Operators en admins kunnen configureren en acties uitvoeren. Partners bekijken alleen hun eigen klanten.",
          "limits": "Een schakelaar of profiel is een configuratieverzoek. Runtime-inrichting, geschikte images, sleutels en contractrechten moeten apart worden gecontroleerd.",
          "example": "housekeeping=true"
        }
      }
    },
    {
      "id": "msp.wizard.modules.router",
      "area": "modules",
      "status": "conditional",
      "conditions": [
        "configuration_only"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.wizard.modules.router"
      ],
      "source_refs": [
        "apps/cockpit/frontend/src/wizard/StepModules.jsx"
      ],
      "related": [
        "msp.wizard.review.review"
      ],
      "locales": {
        "en": {
          "title": "Model router",
          "purpose": "Choose the gateway implementation between agents and model providers.",
          "when": "When configuring or checking this setting for a client installation.",
          "steps": [
            "Open the client wizard and choose Modules and services.",
            "Review model router against the client’s approved requirements. Example: omniroute.",
            "Enter or select the value, then choose Next or Save draft and check the save confirmation.",
            "Review the effective configuration and remaining prerequisites before making live changes."
          ],
          "permissions": "Operators and admins can configure and run actions. Partners can only inspect their owned clients.",
          "limits": "A switch or profile is a configuration request. Runtime setup, compatible images, credentials and commercial entitlement must be checked separately.",
          "example": "omniroute"
        },
        "nl": {
          "title": "Modelrouter",
          "purpose": "Kies de gateway tussen agents en modelaanbieders.",
          "when": "Wanneer je deze instelling voor een klantinstallatie configureert of controleert.",
          "steps": [
            "Open de klantwizard en kies Modules en diensten.",
            "Beoordeel modelrouter aan de hand van de goedgekeurde klanteisen. Voorbeeld: omniroute.",
            "Vul de waarde in of selecteer deze, kies Volgende of Concept opslaan en controleer de bevestiging.",
            "Beoordeel de effectieve configuratie en resterende voorwaarden voordat je live wijzigingen uitvoert."
          ],
          "permissions": "Operators en admins kunnen configureren en acties uitvoeren. Partners bekijken alleen hun eigen klanten.",
          "limits": "Een schakelaar of profiel is een configuratieverzoek. Runtime-inrichting, geschikte images, sleutels en contractrechten moeten apart worden gecontroleerd.",
          "example": "omniroute"
        }
      }
    },
    {
      "id": "msp.wizard.modules.litellm",
      "area": "modules",
      "status": "conditional",
      "conditions": [
        "configuration_only"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.wizard.modules.litellm"
      ],
      "source_refs": [
        "apps/cockpit/frontend/src/wizard/StepModules.jsx"
      ],
      "related": [
        "msp.wizard.review.review"
      ],
      "locales": {
        "en": {
          "title": "LiteLLM router",
          "purpose": "Prepare the OpenAI-compatible proxy from configured provider settings.",
          "when": "When configuring or checking this setting for a client installation.",
          "steps": [
            "Open the client wizard and choose Modules and services.",
            "Review litellm router against the client’s approved requirements. Example: litellm.",
            "Enter or select the value, then choose Next or Save draft and check the save confirmation.",
            "Review the effective configuration and remaining prerequisites before making live changes."
          ],
          "permissions": "Operators and admins can configure and run actions. Partners can only inspect their owned clients.",
          "limits": "A switch or profile is a configuration request. Runtime setup, compatible images, credentials and commercial entitlement must be checked separately.",
          "example": "litellm"
        },
        "nl": {
          "title": "LiteLLM-router",
          "purpose": "Bereid de OpenAI-compatibele proxy voor met de ingestelde aanbieders.",
          "when": "Wanneer je deze instelling voor een klantinstallatie configureert of controleert.",
          "steps": [
            "Open de klantwizard en kies Modules en diensten.",
            "Beoordeel litellm-router aan de hand van de goedgekeurde klanteisen. Voorbeeld: litellm.",
            "Vul de waarde in of selecteer deze, kies Volgende of Concept opslaan en controleer de bevestiging.",
            "Beoordeel de effectieve configuratie en resterende voorwaarden voordat je live wijzigingen uitvoert."
          ],
          "permissions": "Operators en admins kunnen configureren en acties uitvoeren. Partners bekijken alleen hun eigen klanten.",
          "limits": "Een schakelaar of profiel is een configuratieverzoek. Runtime-inrichting, geschikte images, sleutels en contractrechten moeten apart worden gecontroleerd.",
          "example": "litellm"
        }
      }
    },
    {
      "id": "msp.wizard.modules.omniroute",
      "area": "modules",
      "status": "conditional",
      "conditions": [
        "configuration_only"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.wizard.modules.omniroute"
      ],
      "source_refs": [
        "apps/cockpit/frontend/src/wizard/StepModules.jsx"
      ],
      "related": [
        "msp.wizard.review.review"
      ],
      "locales": {
        "en": {
          "title": "OmniRoute router",
          "purpose": "Prepare the router service; its provider connections require separate setup.",
          "when": "When configuring or checking this setting for a client installation.",
          "steps": [
            "Open the client wizard and choose Modules and services.",
            "Review omniroute router against the client’s approved requirements. Example: omniroute.",
            "Enter or select the value, then choose Next or Save draft and check the save confirmation.",
            "Review the effective configuration and remaining prerequisites before making live changes."
          ],
          "permissions": "Operators and admins can configure and run actions. Partners can only inspect their owned clients.",
          "limits": "A switch or profile is a configuration request. Runtime setup, compatible images, credentials and commercial entitlement must be checked separately.",
          "example": "omniroute"
        },
        "nl": {
          "title": "OmniRoute-router",
          "purpose": "Bereid de routerdienst voor; de verbindingen met aanbieders vragen aparte inrichting.",
          "when": "Wanneer je deze instelling voor een klantinstallatie configureert of controleert.",
          "steps": [
            "Open de klantwizard en kies Modules en diensten.",
            "Beoordeel omniroute-router aan de hand van de goedgekeurde klanteisen. Voorbeeld: omniroute.",
            "Vul de waarde in of selecteer deze, kies Volgende of Concept opslaan en controleer de bevestiging.",
            "Beoordeel de effectieve configuratie en resterende voorwaarden voordat je live wijzigingen uitvoert."
          ],
          "permissions": "Operators en admins kunnen configureren en acties uitvoeren. Partners bekijken alleen hun eigen klanten.",
          "limits": "Een schakelaar of profiel is een configuratieverzoek. Runtime-inrichting, geschikte images, sleutels en contractrechten moeten apart worden gecontroleerd.",
          "example": "omniroute"
        }
      }
    },
    {
      "id": "msp.wizard.providers.allowlist",
      "area": "providers",
      "status": "conditional",
      "conditions": [
        "configuration_only"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.wizard.providers.allowlist"
      ],
      "source_refs": [
        "apps/cockpit/frontend/src/wizard/StepProviders.jsx"
      ],
      "related": [
        "msp.wizard.review.review"
      ],
      "locales": {
        "en": {
          "title": "Provider allowlist",
          "purpose": "Choose provider IDs that may be included in the rendered configuration.",
          "when": "When configuring or checking this setting for a client installation.",
          "steps": [
            "Open the client wizard and choose Model providers.",
            "Review provider allowlist against the client’s approved requirements. Example: openai, anthropic.",
            "Enter or select the value, then choose Next or Save draft and check the save confirmation.",
            "Review the effective configuration and remaining prerequisites before making live changes."
          ],
          "permissions": "Operators and admins can configure and run actions. Partners can only inspect their owned clients.",
          "limits": "An allowlist is not provider onboarding. The account, permitted models, quota and costs remain provider-specific. Never include secrets in endpoint URLs.",
          "example": "openai, anthropic"
        },
        "nl": {
          "title": "Toegestane modelaanbieders",
          "purpose": "Kies de aanbieder-ID’s die in de gegenereerde configuratie mogen staan.",
          "when": "Wanneer je deze instelling voor een klantinstallatie configureert of controleert.",
          "steps": [
            "Open de klantwizard en kies Modelaanbieders.",
            "Beoordeel toegestane modelaanbieders aan de hand van de goedgekeurde klanteisen. Voorbeeld: openai, anthropic.",
            "Vul de waarde in of selecteer deze, kies Volgende of Concept opslaan en controleer de bevestiging.",
            "Beoordeel de effectieve configuratie en resterende voorwaarden voordat je live wijzigingen uitvoert."
          ],
          "permissions": "Operators en admins kunnen configureren en acties uitvoeren. Partners bekijken alleen hun eigen klanten.",
          "limits": "Een toegestane lijst is geen aanbiederregistratie. Account, modellen, limieten en kosten blijven aanbiederafhankelijk. Neem nooit geheimen op in endpoint-URL’s.",
          "example": "openai, anthropic"
        }
      }
    },
    {
      "id": "msp.wizard.providers.allow",
      "area": "providers",
      "status": "conditional",
      "conditions": [
        "configuration_only"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.wizard.providers.allow"
      ],
      "source_refs": [
        "apps/cockpit/frontend/src/wizard/StepProviders.jsx"
      ],
      "related": [
        "msp.wizard.review.review"
      ],
      "locales": {
        "en": {
          "title": "Allow a provider",
          "purpose": "Add or remove a provider from the configuration allowlist and show its fields.",
          "when": "When configuring or checking this setting for a client installation.",
          "steps": [
            "Open the client wizard and choose Model providers.",
            "Review allow a provider against the client’s approved requirements. Example: Allow OpenAI.",
            "Enter or select the value, then choose Next or Save draft and check the save confirmation.",
            "Review the effective configuration and remaining prerequisites before making live changes."
          ],
          "permissions": "Operators and admins can configure and run actions. Partners can only inspect their owned clients.",
          "limits": "An allowlist is not provider onboarding. The account, permitted models, quota and costs remain provider-specific. Never include secrets in endpoint URLs.",
          "example": "Allow OpenAI"
        },
        "nl": {
          "title": "Aanbieder toestaan",
          "purpose": "Voeg een aanbieder toe aan de toegestane lijst of verwijder deze en toon de bijbehorende velden.",
          "when": "Wanneer je deze instelling voor een klantinstallatie configureert of controleert.",
          "steps": [
            "Open de klantwizard en kies Modelaanbieders.",
            "Beoordeel aanbieder toestaan aan de hand van de goedgekeurde klanteisen. Voorbeeld: Allow OpenAI.",
            "Vul de waarde in of selecteer deze, kies Volgende of Concept opslaan en controleer de bevestiging.",
            "Beoordeel de effectieve configuratie en resterende voorwaarden voordat je live wijzigingen uitvoert."
          ],
          "permissions": "Operators en admins kunnen configureren en acties uitvoeren. Partners bekijken alleen hun eigen klanten.",
          "limits": "Een toegestane lijst is geen aanbiederregistratie. Account, modellen, limieten en kosten blijven aanbiederafhankelijk. Neem nooit geheimen op in endpoint-URL’s.",
          "example": "Allow OpenAI"
        }
      }
    },
    {
      "id": "msp.wizard.providers.apiKey",
      "area": "providers",
      "status": "conditional",
      "conditions": [
        "configuration_only"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.wizard.providers.apiKey"
      ],
      "source_refs": [
        "apps/cockpit/frontend/src/wizard/StepProviders.jsx"
      ],
      "related": [
        "msp.wizard.review.review"
      ],
      "locales": {
        "en": {
          "title": "Provider API key",
          "purpose": "Store a client-specific provider credential without returning its value to the browser.",
          "when": "When configuring or checking this setting for a client installation.",
          "steps": [
            "Open the client wizard and choose Model providers.",
            "Review provider api key against the client’s approved requirements. Example: client-owned spending-limited key.",
            "Use the field’s save/upload action and check its stored confirmation.",
            "Review the effective configuration and remaining prerequisites before making live changes."
          ],
          "permissions": "Operators and admins can configure and run actions. Partners can only inspect their owned clients.",
          "limits": "An allowlist is not provider onboarding. The account, permitted models, quota and costs remain provider-specific. Never include secrets in endpoint URLs.",
          "example": "client-owned spending-limited key"
        },
        "nl": {
          "title": "API-sleutel van de aanbieder",
          "purpose": "Sla een klantspecifieke aanbiedersleutel op zonder de waarde terug te sturen naar de browser.",
          "when": "Wanneer je deze instelling voor een klantinstallatie configureert of controleert.",
          "steps": [
            "Open de klantwizard en kies Modelaanbieders.",
            "Beoordeel api-sleutel van de aanbieder aan de hand van de goedgekeurde klanteisen. Voorbeeld: klantsleutel met uitgavenlimiet.",
            "Gebruik de opslag- of uploadactie van het veld en controleer de bevestiging.",
            "Beoordeel de effectieve configuratie en resterende voorwaarden voordat je live wijzigingen uitvoert."
          ],
          "permissions": "Operators en admins kunnen configureren en acties uitvoeren. Partners bekijken alleen hun eigen klanten.",
          "limits": "Een toegestane lijst is geen aanbiederregistratie. Account, modellen, limieten en kosten blijven aanbiederafhankelijk. Neem nooit geheimen op in endpoint-URL’s.",
          "example": "klantsleutel met uitgavenlimiet"
        }
      }
    },
    {
      "id": "msp.wizard.providers.endpoint",
      "area": "providers",
      "status": "conditional",
      "conditions": [
        "configuration_only"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.wizard.providers.endpoint"
      ],
      "source_refs": [
        "apps/cockpit/frontend/src/wizard/StepProviders.jsx"
      ],
      "related": [
        "msp.wizard.review.review"
      ],
      "locales": {
        "en": {
          "title": "Provider endpoint",
          "purpose": "Set a supported custom API base URL without embedding credentials in the URL.",
          "when": "When configuring or checking this setting for a client installation.",
          "steps": [
            "Open the client wizard and choose Model providers.",
            "Review provider endpoint against the client’s approved requirements. Example: https://gateway.acme.example/v1.",
            "Enter or select the value, then choose Next or Save draft and check the save confirmation.",
            "Review the effective configuration and remaining prerequisites before making live changes."
          ],
          "permissions": "Operators and admins can configure and run actions. Partners can only inspect their owned clients.",
          "limits": "An allowlist is not provider onboarding. The account, permitted models, quota and costs remain provider-specific. Never include secrets in endpoint URLs.",
          "example": "https://gateway.acme.example/v1"
        },
        "nl": {
          "title": "Aanbiedersadres",
          "purpose": "Stel een ondersteund API-basisadres in zonder inloggegevens in de URL.",
          "when": "Wanneer je deze instelling voor een klantinstallatie configureert of controleert.",
          "steps": [
            "Open de klantwizard en kies Modelaanbieders.",
            "Beoordeel aanbiedersadres aan de hand van de goedgekeurde klanteisen. Voorbeeld: https://gateway.acme.example/v1.",
            "Vul de waarde in of selecteer deze, kies Volgende of Concept opslaan en controleer de bevestiging.",
            "Beoordeel de effectieve configuratie en resterende voorwaarden voordat je live wijzigingen uitvoert."
          ],
          "permissions": "Operators en admins kunnen configureren en acties uitvoeren. Partners bekijken alleen hun eigen klanten.",
          "limits": "Een toegestane lijst is geen aanbiederregistratie. Account, modellen, limieten en kosten blijven aanbiederafhankelijk. Neem nooit geheimen op in endpoint-URL’s.",
          "example": "https://gateway.acme.example/v1"
        }
      }
    },
    {
      "id": "msp.wizard.providers.models",
      "area": "providers",
      "status": "conditional",
      "conditions": [
        "configuration_only"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.wizard.providers.models"
      ],
      "source_refs": [
        "apps/cockpit/frontend/src/wizard/StepProviders.jsx"
      ],
      "related": [
        "msp.wizard.review.review"
      ],
      "locales": {
        "en": {
          "title": "Provider model IDs",
          "purpose": "List the exact model identifiers made available through the configured route.",
          "when": "When configuring or checking this setting for a client installation.",
          "steps": [
            "Open the client wizard and choose Model providers.",
            "Review provider model ids against the client’s approved requirements. Example: approved-model-a, approved-model-b.",
            "Enter or select the value, then choose Next or Save draft and check the save confirmation.",
            "Review the effective configuration and remaining prerequisites before making live changes."
          ],
          "permissions": "Operators and admins can configure and run actions. Partners can only inspect their owned clients.",
          "limits": "An allowlist is not provider onboarding. The account, permitted models, quota and costs remain provider-specific. Never include secrets in endpoint URLs.",
          "example": "approved-model-a, approved-model-b"
        },
        "nl": {
          "title": "Model-ID’s van de aanbieder",
          "purpose": "Noteer de exacte modelnamen die via de ingestelde route beschikbaar worden.",
          "when": "Wanneer je deze instelling voor een klantinstallatie configureert of controleert.",
          "steps": [
            "Open de klantwizard en kies Modelaanbieders.",
            "Beoordeel model-id’s van de aanbieder aan de hand van de goedgekeurde klanteisen. Voorbeeld: approved-model-a, approved-model-b.",
            "Vul de waarde in of selecteer deze, kies Volgende of Concept opslaan en controleer de bevestiging.",
            "Beoordeel de effectieve configuratie en resterende voorwaarden voordat je live wijzigingen uitvoert."
          ],
          "permissions": "Operators en admins kunnen configureren en acties uitvoeren. Partners bekijken alleen hun eigen klanten.",
          "limits": "Een toegestane lijst is geen aanbiederregistratie. Account, modellen, limieten en kosten blijven aanbiederafhankelijk. Neem nooit geheimen op in endpoint-URL’s.",
          "example": "approved-model-a, approved-model-b"
        }
      }
    },
    {
      "id": "msp.wizard.team.tiers",
      "area": "team",
      "status": "available",
      "conditions": [
        "configuration_only"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.wizard.team.tiers"
      ],
      "source_refs": [
        "apps/cockpit/frontend/src/wizard/StepTeam.jsx"
      ],
      "related": [
        "msp.wizard.review.review"
      ],
      "locales": {
        "en": {
          "title": "Team tiers",
          "purpose": "Group owner, core-team and extended-team identities for the rendered setup.",
          "when": "When configuring or checking this setting for a client installation.",
          "steps": [
            "Open the client wizard and choose People and permissions.",
            "Review team tiers against the client’s approved requirements. Example: tier0, tier1, tier2.",
            "Enter or select the value, then choose Next or Save draft and check the save confirmation.",
            "Review the effective configuration and remaining prerequisites before making live changes."
          ],
          "permissions": "Operators and admins can configure and run actions. Partners can only inspect their owned clients.",
          "limits": "Saving requested people or roles does not prove live account provisioning. Rendered policy and actual runtime access must be verified. Cockpit staff roles are separate.",
          "example": "tier0, tier1, tier2"
        },
        "nl": {
          "title": "Teamniveaus",
          "purpose": "Groepeer eigenaren, kernteam en uitgebreid team voor de gegenereerde inrichting.",
          "when": "Wanneer je deze instelling voor een klantinstallatie configureert of controleert.",
          "steps": [
            "Open de klantwizard en kies Personen en bevoegdheden.",
            "Beoordeel teamniveaus aan de hand van de goedgekeurde klanteisen. Voorbeeld: tier0, tier1, tier2.",
            "Vul de waarde in of selecteer deze, kies Volgende of Concept opslaan en controleer de bevestiging.",
            "Beoordeel de effectieve configuratie en resterende voorwaarden voordat je live wijzigingen uitvoert."
          ],
          "permissions": "Operators en admins kunnen configureren en acties uitvoeren. Partners bekijken alleen hun eigen klanten.",
          "limits": "Gevraagde personen of rollen opslaan bewijst geen actieve accountinrichting. Controleer gegenereerd beleid en werkelijke toegang. Cockpitrollen staan hiervan los.",
          "example": "tier0, tier1, tier2"
        }
      }
    },
    {
      "id": "msp.wizard.team.tier0",
      "area": "team",
      "status": "available",
      "conditions": [
        "configuration_only"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.wizard.team.tier0"
      ],
      "source_refs": [
        "apps/cockpit/frontend/src/wizard/StepTeam.jsx"
      ],
      "related": [
        "msp.wizard.review.review"
      ],
      "locales": {
        "en": {
          "title": "Owners",
          "purpose": "List the owner identities used by the configured team policy.",
          "when": "When configuring or checking this setting for a client installation.",
          "steps": [
            "Open the client wizard and choose People and permissions.",
            "Review owners against the client’s approved requirements. Example: owner@acme.example.",
            "Enter or select the value, then choose Next or Save draft and check the save confirmation.",
            "Review the effective configuration and remaining prerequisites before making live changes."
          ],
          "permissions": "Operators and admins can configure and run actions. Partners can only inspect their owned clients.",
          "limits": "Saving requested people or roles does not prove live account provisioning. Rendered policy and actual runtime access must be verified. Cockpit staff roles are separate.",
          "example": "owner@acme.example"
        },
        "nl": {
          "title": "Eigenaren",
          "purpose": "Noteer de eigenaarsidentiteiten voor het ingestelde teambeleid.",
          "when": "Wanneer je deze instelling voor een klantinstallatie configureert of controleert.",
          "steps": [
            "Open de klantwizard en kies Personen en bevoegdheden.",
            "Beoordeel eigenaren aan de hand van de goedgekeurde klanteisen. Voorbeeld: owner@acme.example.",
            "Vul de waarde in of selecteer deze, kies Volgende of Concept opslaan en controleer de bevestiging.",
            "Beoordeel de effectieve configuratie en resterende voorwaarden voordat je live wijzigingen uitvoert."
          ],
          "permissions": "Operators en admins kunnen configureren en acties uitvoeren. Partners bekijken alleen hun eigen klanten.",
          "limits": "Gevraagde personen of rollen opslaan bewijst geen actieve accountinrichting. Controleer gegenereerd beleid en werkelijke toegang. Cockpitrollen staan hiervan los.",
          "example": "owner@acme.example"
        }
      }
    },
    {
      "id": "msp.wizard.team.tier1",
      "area": "team",
      "status": "available",
      "conditions": [
        "configuration_only"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.wizard.team.tier1"
      ],
      "source_refs": [
        "apps/cockpit/frontend/src/wizard/StepTeam.jsx"
      ],
      "related": [
        "msp.wizard.review.review"
      ],
      "locales": {
        "en": {
          "title": "Core team",
          "purpose": "List core-team identities for the configured team policy.",
          "when": "When configuring or checking this setting for a client installation.",
          "steps": [
            "Open the client wizard and choose People and permissions.",
            "Review core team against the client’s approved requirements. Example: team@acme.example.",
            "Enter or select the value, then choose Next or Save draft and check the save confirmation.",
            "Review the effective configuration and remaining prerequisites before making live changes."
          ],
          "permissions": "Operators and admins can configure and run actions. Partners can only inspect their owned clients.",
          "limits": "Saving requested people or roles does not prove live account provisioning. Rendered policy and actual runtime access must be verified. Cockpit staff roles are separate.",
          "example": "team@acme.example"
        },
        "nl": {
          "title": "Kernteam",
          "purpose": "Noteer kernteamleden voor het ingestelde teambeleid.",
          "when": "Wanneer je deze instelling voor een klantinstallatie configureert of controleert.",
          "steps": [
            "Open de klantwizard en kies Personen en bevoegdheden.",
            "Beoordeel kernteam aan de hand van de goedgekeurde klanteisen. Voorbeeld: team@acme.example.",
            "Vul de waarde in of selecteer deze, kies Volgende of Concept opslaan en controleer de bevestiging.",
            "Beoordeel de effectieve configuratie en resterende voorwaarden voordat je live wijzigingen uitvoert."
          ],
          "permissions": "Operators en admins kunnen configureren en acties uitvoeren. Partners bekijken alleen hun eigen klanten.",
          "limits": "Gevraagde personen of rollen opslaan bewijst geen actieve accountinrichting. Controleer gegenereerd beleid en werkelijke toegang. Cockpitrollen staan hiervan los.",
          "example": "team@acme.example"
        }
      }
    },
    {
      "id": "msp.wizard.team.tier2",
      "area": "team",
      "status": "available",
      "conditions": [
        "configuration_only"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.wizard.team.tier2"
      ],
      "source_refs": [
        "apps/cockpit/frontend/src/wizard/StepTeam.jsx"
      ],
      "related": [
        "msp.wizard.review.review"
      ],
      "locales": {
        "en": {
          "title": "Extended team",
          "purpose": "List partner and extended-team identities whose actual rights follow policy.",
          "when": "When configuring or checking this setting for a client installation.",
          "steps": [
            "Open the client wizard and choose People and permissions.",
            "Review extended team against the client’s approved requirements. Example: partner@acme.example.",
            "Enter or select the value, then choose Next or Save draft and check the save confirmation.",
            "Review the effective configuration and remaining prerequisites before making live changes."
          ],
          "permissions": "Operators and admins can configure and run actions. Partners can only inspect their owned clients.",
          "limits": "Saving requested people or roles does not prove live account provisioning. Rendered policy and actual runtime access must be verified. Cockpit staff roles are separate.",
          "example": "partner@acme.example"
        },
        "nl": {
          "title": "Uitgebreid team",
          "purpose": "Noteer partners en overige teamleden; hun daadwerkelijke rechten volgen uit het beleid.",
          "when": "Wanneer je deze instelling voor een klantinstallatie configureert of controleert.",
          "steps": [
            "Open de klantwizard en kies Personen en bevoegdheden.",
            "Beoordeel uitgebreid team aan de hand van de goedgekeurde klanteisen. Voorbeeld: partner@acme.example.",
            "Vul de waarde in of selecteer deze, kies Volgende of Concept opslaan en controleer de bevestiging.",
            "Beoordeel de effectieve configuratie en resterende voorwaarden voordat je live wijzigingen uitvoert."
          ],
          "permissions": "Operators en admins kunnen configureren en acties uitvoeren. Partners bekijken alleen hun eigen klanten.",
          "limits": "Gevraagde personen of rollen opslaan bewijst geen actieve accountinrichting. Controleer gegenereerd beleid en werkelijke toegang. Cockpitrollen staan hiervan los.",
          "example": "partner@acme.example"
        }
      }
    },
    {
      "id": "msp.wizard.team.skills",
      "area": "team",
      "status": "available",
      "conditions": [
        "configuration_only"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.wizard.team.skills"
      ],
      "source_refs": [
        "apps/cockpit/frontend/src/wizard/StepTeam.jsx"
      ],
      "related": [
        "msp.wizard.review.review"
      ],
      "locales": {
        "en": {
          "title": "Skill provisioning",
          "purpose": "Choose the skill collection provisioned by the deployment tooling.",
          "when": "When configuring or checking this setting for a client installation.",
          "steps": [
            "Open the client wizard and choose People and permissions.",
            "Review skill provisioning against the client’s approved requirements. Example: basic.",
            "Enter or select the value, then choose Next or Save draft and check the save confirmation.",
            "Review the effective configuration and remaining prerequisites before making live changes."
          ],
          "permissions": "Operators and admins can configure and run actions. Partners can only inspect their owned clients.",
          "limits": "Saving requested people or roles does not prove live account provisioning. Rendered policy and actual runtime access must be verified. Cockpit staff roles are separate.",
          "example": "basic"
        },
        "nl": {
          "title": "Skills voorbereiden",
          "purpose": "Kies de skillverzameling die de installatietools voorbereiden.",
          "when": "Wanneer je deze instelling voor een klantinstallatie configureert of controleert.",
          "steps": [
            "Open de klantwizard en kies Personen en bevoegdheden.",
            "Beoordeel skills voorbereiden aan de hand van de goedgekeurde klanteisen. Voorbeeld: basic.",
            "Vul de waarde in of selecteer deze, kies Volgende of Concept opslaan en controleer de bevestiging.",
            "Beoordeel de effectieve configuratie en resterende voorwaarden voordat je live wijzigingen uitvoert."
          ],
          "permissions": "Operators en admins kunnen configureren en acties uitvoeren. Partners bekijken alleen hun eigen klanten.",
          "limits": "Gevraagde personen of rollen opslaan bewijst geen actieve accountinrichting. Controleer gegenereerd beleid en werkelijke toegang. Cockpitrollen staan hiervan los.",
          "example": "basic"
        }
      }
    },
    {
      "id": "msp.wizard.team.skillTier",
      "area": "team",
      "status": "available",
      "conditions": [
        "configuration_only"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.wizard.team.skillTier"
      ],
      "source_refs": [
        "apps/cockpit/frontend/src/wizard/StepTeam.jsx"
      ],
      "related": [
        "msp.wizard.review.review"
      ],
      "locales": {
        "en": {
          "title": "Skill set",
          "purpose": "Select Basic, Pro or Deluxe as an installation preset, separate from service contract pricing.",
          "when": "When configuring or checking this setting for a client installation.",
          "steps": [
            "Open the client wizard and choose People and permissions.",
            "Review skill set against the client’s approved requirements. Example: Basic.",
            "Enter or select the value, then choose Next or Save draft and check the save confirmation.",
            "Review the effective configuration and remaining prerequisites before making live changes."
          ],
          "permissions": "Operators and admins can configure and run actions. Partners can only inspect their owned clients.",
          "limits": "Saving requested people or roles does not prove live account provisioning. Rendered policy and actual runtime access must be verified. Cockpit staff roles are separate. Skill sets describe installation content, not the Standard service plan or a per-seat price.",
          "example": "Basic"
        },
        "nl": {
          "title": "Skillpakket",
          "purpose": "Kies Basic, Pro of Deluxe als installatievoorinstelling, los van de prijs van het servicecontract.",
          "when": "Wanneer je deze instelling voor een klantinstallatie configureert of controleert.",
          "steps": [
            "Open de klantwizard en kies Personen en bevoegdheden.",
            "Beoordeel skillpakket aan de hand van de goedgekeurde klanteisen. Voorbeeld: Basic.",
            "Vul de waarde in of selecteer deze, kies Volgende of Concept opslaan en controleer de bevestiging.",
            "Beoordeel de effectieve configuratie en resterende voorwaarden voordat je live wijzigingen uitvoert."
          ],
          "permissions": "Operators en admins kunnen configureren en acties uitvoeren. Partners bekijken alleen hun eigen klanten.",
          "limits": "Gevraagde personen of rollen opslaan bewijst geen actieve accountinrichting. Controleer gegenereerd beleid en werkelijke toegang. Cockpitrollen staan hiervan los. Skillpakketten beschrijven installatie-inhoud, niet het Standard-serviceplan of een prijs per gebruiker.",
          "example": "Basic"
        }
      }
    },
    {
      "id": "msp.wizard.team.people",
      "area": "team",
      "status": "available",
      "conditions": [
        "configuration_only"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.wizard.team.people"
      ],
      "source_refs": [
        "apps/cockpit/frontend/src/wizard/StepTeam.jsx"
      ],
      "related": [
        "msp.wizard.review.review"
      ],
      "locales": {
        "en": {
          "title": "People",
          "purpose": "Add or remove the people requested in the client configuration.",
          "when": "When configuring or checking this setting for a client installation.",
          "steps": [
            "Open the client wizard and choose People and permissions.",
            "Review people against the client’s approved requirements. Example: one row per colleague.",
            "Enter or select the value, then choose Next or Save draft and check the save confirmation.",
            "Review the effective configuration and remaining prerequisites before making live changes."
          ],
          "permissions": "Operators and admins can configure and run actions. Partners can only inspect their owned clients.",
          "limits": "Saving requested people or roles does not prove live account provisioning. Rendered policy and actual runtime access must be verified. Cockpit staff roles are separate.",
          "example": "one row per colleague"
        },
        "nl": {
          "title": "Personen",
          "purpose": "Voeg personen toe aan de klantconfiguratie of verwijder ze daaruit.",
          "when": "Wanneer je deze instelling voor een klantinstallatie configureert of controleert.",
          "steps": [
            "Open de klantwizard en kies Personen en bevoegdheden.",
            "Beoordeel personen aan de hand van de goedgekeurde klanteisen. Voorbeeld: één regel per collega.",
            "Vul de waarde in of selecteer deze, kies Volgende of Concept opslaan en controleer de bevestiging.",
            "Beoordeel de effectieve configuratie en resterende voorwaarden voordat je live wijzigingen uitvoert."
          ],
          "permissions": "Operators en admins kunnen configureren en acties uitvoeren. Partners bekijken alleen hun eigen klanten.",
          "limits": "Gevraagde personen of rollen opslaan bewijst geen actieve accountinrichting. Controleer gegenereerd beleid en werkelijke toegang. Cockpitrollen staan hiervan los.",
          "example": "één regel per collega"
        }
      }
    },
    {
      "id": "msp.wizard.team.personEmail",
      "area": "team",
      "status": "available",
      "conditions": [
        "configuration_only"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.wizard.team.personEmail"
      ],
      "source_refs": [
        "apps/cockpit/frontend/src/wizard/StepTeam.jsx"
      ],
      "related": [
        "msp.wizard.review.review"
      ],
      "locales": {
        "en": {
          "title": "Person email",
          "purpose": "Use the work identity that must match the configured sign-in and governance identity.",
          "when": "When configuring or checking this setting for a client installation.",
          "steps": [
            "Open the client wizard and choose People and permissions.",
            "Review person email against the client’s approved requirements. Example: colleague@acme.example.",
            "Enter or select the value, then choose Next or Save draft and check the save confirmation.",
            "Review the effective configuration and remaining prerequisites before making live changes."
          ],
          "permissions": "Operators and admins can configure and run actions. Partners can only inspect their owned clients.",
          "limits": "Saving requested people or roles does not prove live account provisioning. Rendered policy and actual runtime access must be verified. Cockpit staff roles are separate.",
          "example": "colleague@acme.example"
        },
        "nl": {
          "title": "E-mailadres van de persoon",
          "purpose": "Gebruik de werkidentiteit die moet overeenkomen met login en bevoegdheden.",
          "when": "Wanneer je deze instelling voor een klantinstallatie configureert of controleert.",
          "steps": [
            "Open de klantwizard en kies Personen en bevoegdheden.",
            "Beoordeel e-mailadres van de persoon aan de hand van de goedgekeurde klanteisen. Voorbeeld: colleague@acme.example.",
            "Vul de waarde in of selecteer deze, kies Volgende of Concept opslaan en controleer de bevestiging.",
            "Beoordeel de effectieve configuratie en resterende voorwaarden voordat je live wijzigingen uitvoert."
          ],
          "permissions": "Operators en admins kunnen configureren en acties uitvoeren. Partners bekijken alleen hun eigen klanten.",
          "limits": "Gevraagde personen of rollen opslaan bewijst geen actieve accountinrichting. Controleer gegenereerd beleid en werkelijke toegang. Cockpitrollen staan hiervan los.",
          "example": "colleague@acme.example"
        }
      }
    },
    {
      "id": "msp.wizard.team.personName",
      "area": "team",
      "status": "available",
      "conditions": [
        "configuration_only"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.wizard.team.personName"
      ],
      "source_refs": [
        "apps/cockpit/frontend/src/wizard/StepTeam.jsx"
      ],
      "related": [
        "msp.wizard.review.review"
      ],
      "locales": {
        "en": {
          "title": "Person name",
          "purpose": "Set the readable person name used on supported client screens.",
          "when": "When configuring or checking this setting for a client installation.",
          "steps": [
            "Open the client wizard and choose People and permissions.",
            "Review person name against the client’s approved requirements. Example: Alex Example.",
            "Enter or select the value, then choose Next or Save draft and check the save confirmation.",
            "Review the effective configuration and remaining prerequisites before making live changes."
          ],
          "permissions": "Operators and admins can configure and run actions. Partners can only inspect their owned clients.",
          "limits": "Saving requested people or roles does not prove live account provisioning. Rendered policy and actual runtime access must be verified. Cockpit staff roles are separate.",
          "example": "Alex Example"
        },
        "nl": {
          "title": "Naam van de persoon",
          "purpose": "Stel de leesbare persoonsnaam in voor ondersteunde klantschermen.",
          "when": "Wanneer je deze instelling voor een klantinstallatie configureert of controleert.",
          "steps": [
            "Open de klantwizard en kies Personen en bevoegdheden.",
            "Beoordeel naam van de persoon aan de hand van de goedgekeurde klanteisen. Voorbeeld: Alex Example.",
            "Vul de waarde in of selecteer deze, kies Volgende of Concept opslaan en controleer de bevestiging.",
            "Beoordeel de effectieve configuratie en resterende voorwaarden voordat je live wijzigingen uitvoert."
          ],
          "permissions": "Operators en admins kunnen configureren en acties uitvoeren. Partners bekijken alleen hun eigen klanten.",
          "limits": "Gevraagde personen of rollen opslaan bewijst geen actieve accountinrichting. Controleer gegenereerd beleid en werkelijke toegang. Cockpitrollen staan hiervan los.",
          "example": "Alex Example"
        }
      }
    },
    {
      "id": "msp.wizard.team.personRole",
      "area": "team",
      "status": "available",
      "conditions": [
        "configuration_only"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.wizard.team.personRole"
      ],
      "source_refs": [
        "apps/cockpit/frontend/src/wizard/StepTeam.jsx"
      ],
      "related": [
        "msp.wizard.review.review"
      ],
      "locales": {
        "en": {
          "title": "Person role",
          "purpose": "Request admin, team or partner privileges through the installation policy.",
          "when": "When configuring or checking this setting for a client installation.",
          "steps": [
            "Open the client wizard and choose People and permissions.",
            "Review person role against the client’s approved requirements. Example: team.",
            "Enter or select the value, then choose Next or Save draft and check the save confirmation.",
            "Review the effective configuration and remaining prerequisites before making live changes."
          ],
          "permissions": "Operators and admins can configure and run actions. Partners can only inspect their owned clients.",
          "limits": "Saving requested people or roles does not prove live account provisioning. Rendered policy and actual runtime access must be verified. Cockpit staff roles are separate.",
          "example": "team"
        },
        "nl": {
          "title": "Rol van de persoon",
          "purpose": "Vraag admin-, team- of partnerrechten aan via het installatiebeleid.",
          "when": "Wanneer je deze instelling voor een klantinstallatie configureert of controleert.",
          "steps": [
            "Open de klantwizard en kies Personen en bevoegdheden.",
            "Beoordeel rol van de persoon aan de hand van de goedgekeurde klanteisen. Voorbeeld: team.",
            "Vul de waarde in of selecteer deze, kies Volgende of Concept opslaan en controleer de bevestiging.",
            "Beoordeel de effectieve configuratie en resterende voorwaarden voordat je live wijzigingen uitvoert."
          ],
          "permissions": "Operators en admins kunnen configureren en acties uitvoeren. Partners bekijken alleen hun eigen klanten.",
          "limits": "Gevraagde personen of rollen opslaan bewijst geen actieve accountinrichting. Controleer gegenereerd beleid en werkelijke toegang. Cockpitrollen staan hiervan los.",
          "example": "team"
        }
      }
    },
    {
      "id": "msp.wizard.team.governanceBaseline",
      "area": "team",
      "status": "available",
      "conditions": [
        "configuration_only"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.wizard.team.governanceBaseline"
      ],
      "source_refs": [
        "apps/cockpit/frontend/src/wizard/StepTeam.jsx"
      ],
      "related": [
        "msp.wizard.review.review"
      ],
      "locales": {
        "en": {
          "title": "Governance baseline",
          "purpose": "Choose the policy template used to render individual permissions.",
          "when": "When configuring or checking this setting for a client installation.",
          "steps": [
            "Open the client wizard and choose People and permissions.",
            "Review governance baseline against the client’s approved requirements. Example: strict.",
            "Enter or select the value, then choose Next or Save draft and check the save confirmation.",
            "Review the effective configuration and remaining prerequisites before making live changes."
          ],
          "permissions": "Operators and admins can configure and run actions. Partners can only inspect their owned clients.",
          "limits": "Saving requested people or roles does not prove live account provisioning. Rendered policy and actual runtime access must be verified. Cockpit staff roles are separate.",
          "example": "strict"
        },
        "nl": {
          "title": "Basisbeleid voor bevoegdheden",
          "purpose": "Kies het beleidssjabloon waarmee individuele bevoegdheden worden gegenereerd.",
          "when": "Wanneer je deze instelling voor een klantinstallatie configureert of controleert.",
          "steps": [
            "Open de klantwizard en kies Personen en bevoegdheden.",
            "Beoordeel basisbeleid voor bevoegdheden aan de hand van de goedgekeurde klanteisen. Voorbeeld: strict.",
            "Vul de waarde in of selecteer deze, kies Volgende of Concept opslaan en controleer de bevestiging.",
            "Beoordeel de effectieve configuratie en resterende voorwaarden voordat je live wijzigingen uitvoert."
          ],
          "permissions": "Operators en admins kunnen configureren en acties uitvoeren. Partners bekijken alleen hun eigen klanten.",
          "limits": "Gevraagde personen of rollen opslaan bewijst geen actieve accountinrichting. Controleer gegenereerd beleid en werkelijke toegang. Cockpitrollen staan hiervan los.",
          "example": "strict"
        }
      }
    },
    {
      "id": "msp.wizard.team.governance",
      "area": "team",
      "status": "available",
      "conditions": [
        "configuration_only"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.wizard.team.governance"
      ],
      "source_refs": [
        "apps/cockpit/frontend/src/wizard/StepTeam.jsx"
      ],
      "related": [
        "msp.wizard.review.review"
      ],
      "locales": {
        "en": {
          "title": "Governance",
          "purpose": "Tie identities to allowed tools, skills, connections and commands.",
          "when": "When configuring or checking this setting for a client installation.",
          "steps": [
            "Open the client wizard and choose People and permissions.",
            "Review governance against the client’s approved requirements. Example: enforce with reviewed grants.",
            "Enter or select the value, then choose Next or Save draft and check the save confirmation.",
            "Review the effective configuration and remaining prerequisites before making live changes."
          ],
          "permissions": "Operators and admins can configure and run actions. Partners can only inspect their owned clients.",
          "limits": "Saving requested people or roles does not prove live account provisioning. Rendered policy and actual runtime access must be verified. Cockpit staff roles are separate.",
          "example": "enforce with reviewed grants"
        },
        "nl": {
          "title": "Bevoegdhedenbeleid",
          "purpose": "Koppel identiteiten aan toegestane tools, skills, verbindingen en commando’s.",
          "when": "Wanneer je deze instelling voor een klantinstallatie configureert of controleert.",
          "steps": [
            "Open de klantwizard en kies Personen en bevoegdheden.",
            "Beoordeel bevoegdhedenbeleid aan de hand van de goedgekeurde klanteisen. Voorbeeld: enforce met beoordeelde bevoegdheden.",
            "Vul de waarde in of selecteer deze, kies Volgende of Concept opslaan en controleer de bevestiging.",
            "Beoordeel de effectieve configuratie en resterende voorwaarden voordat je live wijzigingen uitvoert."
          ],
          "permissions": "Operators en admins kunnen configureren en acties uitvoeren. Partners bekijken alleen hun eigen klanten.",
          "limits": "Gevraagde personen of rollen opslaan bewijst geen actieve accountinrichting. Controleer gegenereerd beleid en werkelijke toegang. Cockpitrollen staan hiervan los.",
          "example": "enforce met beoordeelde bevoegdheden"
        }
      }
    },
    {
      "id": "msp.wizard.team.governanceMode",
      "area": "team",
      "status": "available",
      "conditions": [
        "configuration_only"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.wizard.team.governanceMode"
      ],
      "source_refs": [
        "apps/cockpit/frontend/src/wizard/StepTeam.jsx"
      ],
      "related": [
        "msp.wizard.review.review"
      ],
      "locales": {
        "en": {
          "title": "Governance mode",
          "purpose": "Choose evaluation-only reporting or actual permission enforcement.",
          "when": "When configuring or checking this setting for a client installation.",
          "steps": [
            "Open the client wizard and choose People and permissions.",
            "Review governance mode against the client’s approved requirements. Example: enforce.",
            "Enter or select the value, then choose Next or Save draft and check the save confirmation.",
            "Review the effective configuration and remaining prerequisites before making live changes."
          ],
          "permissions": "Operators and admins can configure and run actions. Partners can only inspect their owned clients.",
          "limits": "Saving requested people or roles does not prove live account provisioning. Rendered policy and actual runtime access must be verified. Cockpit staff roles are separate. report_only evaluates and records but does not block. enforce blocks unauthorised actions. Check the deployed policy before relying on enforcement.",
          "example": "enforce"
        },
        "nl": {
          "title": "Beleidsmodus",
          "purpose": "Kies alleen evaluatie en logging of daadwerkelijke handhaving van bevoegdheden.",
          "when": "Wanneer je deze instelling voor een klantinstallatie configureert of controleert.",
          "steps": [
            "Open de klantwizard en kies Personen en bevoegdheden.",
            "Beoordeel beleidsmodus aan de hand van de goedgekeurde klanteisen. Voorbeeld: enforce.",
            "Vul de waarde in of selecteer deze, kies Volgende of Concept opslaan en controleer de bevestiging.",
            "Beoordeel de effectieve configuratie en resterende voorwaarden voordat je live wijzigingen uitvoert."
          ],
          "permissions": "Operators en admins kunnen configureren en acties uitvoeren. Partners bekijken alleen hun eigen klanten.",
          "limits": "Gevraagde personen of rollen opslaan bewijst geen actieve accountinrichting. Controleer gegenereerd beleid en werkelijke toegang. Cockpitrollen staan hiervan los. report_only beoordeelt en registreert, maar blokkeert niet. enforce blokkeert onbevoegde acties. Controleer het actieve beleid voordat je op handhaving vertrouwt.",
          "example": "enforce"
        }
      }
    },
    {
      "id": "msp.wizard.team.sso",
      "area": "team",
      "status": "available",
      "conditions": [
        "configuration_only"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.wizard.team.sso"
      ],
      "source_refs": [
        "apps/cockpit/frontend/src/wizard/StepTeam.jsx"
      ],
      "related": [
        "msp.wizard.review.review"
      ],
      "locales": {
        "en": {
          "title": "Client sign-in",
          "purpose": "Prepare the client WebUI sign-in method separately from cockpit staff access.",
          "when": "When configuring or checking this setting for a client installation.",
          "steps": [
            "Open the client wizard and choose People and permissions.",
            "Review client sign-in against the client’s approved requirements. Example: Google Workspace login.",
            "Enter or select the value, then choose Next or Save draft and check the save confirmation.",
            "Review the effective configuration and remaining prerequisites before making live changes."
          ],
          "permissions": "Operators and admins can configure and run actions. Partners can only inspect their owned clients.",
          "limits": "Saving requested people or roles does not prove live account provisioning. Rendered policy and actual runtime access must be verified. Cockpit staff roles are separate.",
          "example": "Google Workspace login"
        },
        "nl": {
          "title": "Inloggen op de klantomgeving",
          "purpose": "Bereid de login van de klant-WebUI voor, afzonderlijk van toegang tot dit beheercockpit.",
          "when": "Wanneer je deze instelling voor een klantinstallatie configureert of controleert.",
          "steps": [
            "Open de klantwizard en kies Personen en bevoegdheden.",
            "Beoordeel inloggen op de klantomgeving aan de hand van de goedgekeurde klanteisen. Voorbeeld: Google Workspace login.",
            "Vul de waarde in of selecteer deze, kies Volgende of Concept opslaan en controleer de bevestiging.",
            "Beoordeel de effectieve configuratie en resterende voorwaarden voordat je live wijzigingen uitvoert."
          ],
          "permissions": "Operators en admins kunnen configureren en acties uitvoeren. Partners bekijken alleen hun eigen klanten.",
          "limits": "Gevraagde personen of rollen opslaan bewijst geen actieve accountinrichting. Controleer gegenereerd beleid en werkelijke toegang. Cockpitrollen staan hiervan los.",
          "example": "Google Workspace login"
        }
      }
    },
    {
      "id": "msp.wizard.team.ssoToggle",
      "area": "team",
      "status": "available",
      "conditions": [
        "configuration_only"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.wizard.team.ssoToggle"
      ],
      "source_refs": [
        "apps/cockpit/frontend/src/wizard/StepTeam.jsx"
      ],
      "related": [
        "msp.wizard.review.review"
      ],
      "locales": {
        "en": {
          "title": "Google sign-in switch",
          "purpose": "Request Google sign-in with a separately registered OAuth application.",
          "when": "When configuring or checking this setting for a client installation.",
          "steps": [
            "Open the client wizard and choose People and permissions.",
            "Review google sign-in switch against the client’s approved requirements. Example: webui.sso.enabled=true.",
            "Enter or select the value, then choose Next or Save draft and check the save confirmation.",
            "Review the effective configuration and remaining prerequisites before making live changes."
          ],
          "permissions": "Operators and admins can configure and run actions. Partners can only inspect their owned clients.",
          "limits": "Saving requested people or roles does not prove live account provisioning. Rendered policy and actual runtime access must be verified. Cockpit staff roles are separate.",
          "example": "webui.sso.enabled=true"
        },
        "nl": {
          "title": "Google-login inschakelen",
          "purpose": "Vraag Google-login aan met een afzonderlijk geregistreerde OAuth-app.",
          "when": "Wanneer je deze instelling voor een klantinstallatie configureert of controleert.",
          "steps": [
            "Open de klantwizard en kies Personen en bevoegdheden.",
            "Beoordeel google-login inschakelen aan de hand van de goedgekeurde klanteisen. Voorbeeld: webui.sso.enabled=true.",
            "Vul de waarde in of selecteer deze, kies Volgende of Concept opslaan en controleer de bevestiging.",
            "Beoordeel de effectieve configuratie en resterende voorwaarden voordat je live wijzigingen uitvoert."
          ],
          "permissions": "Operators en admins kunnen configureren en acties uitvoeren. Partners bekijken alleen hun eigen klanten.",
          "limits": "Gevraagde personen of rollen opslaan bewijst geen actieve accountinrichting. Controleer gegenereerd beleid en werkelijke toegang. Cockpitrollen staan hiervan los.",
          "example": "webui.sso.enabled=true"
        }
      }
    },
    {
      "id": "msp.wizard.team.ssoDomains",
      "area": "team",
      "status": "available",
      "conditions": [
        "configuration_only"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.wizard.team.ssoDomains"
      ],
      "source_refs": [
        "apps/cockpit/frontend/src/wizard/StepTeam.jsx"
      ],
      "related": [
        "msp.wizard.review.review"
      ],
      "locales": {
        "en": {
          "title": "Allowed sign-in domains",
          "purpose": "Restrict supported Google sign-in to the listed domains.",
          "when": "When configuring or checking this setting for a client installation.",
          "steps": [
            "Open the client wizard and choose People and permissions.",
            "Review allowed sign-in domains against the client’s approved requirements. Example: acme.example.",
            "Enter or select the value, then choose Next or Save draft and check the save confirmation.",
            "Review the effective configuration and remaining prerequisites before making live changes."
          ],
          "permissions": "Operators and admins can configure and run actions. Partners can only inspect their owned clients.",
          "limits": "Saving requested people or roles does not prove live account provisioning. Rendered policy and actual runtime access must be verified. Cockpit staff roles are separate.",
          "example": "acme.example"
        },
        "nl": {
          "title": "Toegestane logindomeinen",
          "purpose": "Beperk ondersteunde Google-login tot de opgegeven domeinen.",
          "when": "Wanneer je deze instelling voor een klantinstallatie configureert of controleert.",
          "steps": [
            "Open de klantwizard en kies Personen en bevoegdheden.",
            "Beoordeel toegestane logindomeinen aan de hand van de goedgekeurde klanteisen. Voorbeeld: acme.example.",
            "Vul de waarde in of selecteer deze, kies Volgende of Concept opslaan en controleer de bevestiging.",
            "Beoordeel de effectieve configuratie en resterende voorwaarden voordat je live wijzigingen uitvoert."
          ],
          "permissions": "Operators en admins kunnen configureren en acties uitvoeren. Partners bekijken alleen hun eigen klanten.",
          "limits": "Gevraagde personen of rollen opslaan bewijst geen actieve accountinrichting. Controleer gegenereerd beleid en werkelijke toegang. Cockpitrollen staan hiervan los.",
          "example": "acme.example"
        }
      }
    },
    {
      "id": "msp.wizard.channels.enable",
      "area": "channels",
      "status": "conditional",
      "conditions": [
        "configuration_only"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.wizard.channels.enable"
      ],
      "source_refs": [
        "apps/cockpit/frontend/src/wizard/StepChannels.jsx"
      ],
      "related": [
        "msp.wizard.review.review"
      ],
      "locales": {
        "en": {
          "title": "Enable a channel",
          "purpose": "Select a messaging adapter to configure for this installation.",
          "when": "When configuring or checking this setting for a client installation.",
          "steps": [
            "Open the client wizard and choose Messaging channels.",
            "Review enable a channel against the client’s approved requirements. Example: telegram.",
            "Enter or select the value, then choose Next or Save draft and check the save confirmation.",
            "Review the effective configuration and remaining prerequisites before making live changes."
          ],
          "permissions": "Operators and admins can configure and run actions. Partners can only inspect their owned clients.",
          "limits": "Provider registration, valid credentials, identity mapping and runtime adapter support are required. Saving this setting sends no external message.",
          "example": "telegram"
        },
        "nl": {
          "title": "Kanaal inschakelen",
          "purpose": "Kies een berichtenadapter die je voor deze installatie wilt inrichten.",
          "when": "Wanneer je deze instelling voor een klantinstallatie configureert of controleert.",
          "steps": [
            "Open de klantwizard en kies Berichtenkanalen.",
            "Beoordeel kanaal inschakelen aan de hand van de goedgekeurde klanteisen. Voorbeeld: telegram.",
            "Vul de waarde in of selecteer deze, kies Volgende of Concept opslaan en controleer de bevestiging.",
            "Beoordeel de effectieve configuratie en resterende voorwaarden voordat je live wijzigingen uitvoert."
          ],
          "permissions": "Operators en admins kunnen configureren en acties uitvoeren. Partners bekijken alleen hun eigen klanten.",
          "limits": "Platformregistratie, geldige sleutels, persoonskoppeling en adapterondersteuning zijn nodig. Opslaan verstuurt geen extern bericht.",
          "example": "telegram"
        }
      }
    },
    {
      "id": "msp.wizard.channels.secret",
      "area": "channels",
      "status": "conditional",
      "conditions": [
        "configuration_only"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.wizard.channels.secret"
      ],
      "source_refs": [
        "apps/cockpit/frontend/src/wizard/StepChannels.jsx"
      ],
      "related": [
        "msp.wizard.review.review"
      ],
      "locales": {
        "en": {
          "title": "Channel credential",
          "purpose": "Store the channel’s token or secret in the client environment store.",
          "when": "When configuring or checking this setting for a client installation.",
          "steps": [
            "Open the client wizard and choose Messaging channels.",
            "Review channel credential against the client’s approved requirements. Example: bot token.",
            "Enter or select the value, then choose Next or Save draft and check the save confirmation.",
            "Review the effective configuration and remaining prerequisites before making live changes."
          ],
          "permissions": "Operators and admins can configure and run actions. Partners can only inspect their owned clients.",
          "limits": "Provider registration, valid credentials, identity mapping and runtime adapter support are required. Saving this setting sends no external message.",
          "example": "bot token"
        },
        "nl": {
          "title": "Kanaalsleutel",
          "purpose": "Sla het token of geheim van het kanaal op in de omgevingsopslag van de klant.",
          "when": "Wanneer je deze instelling voor een klantinstallatie configureert of controleert.",
          "steps": [
            "Open de klantwizard en kies Berichtenkanalen.",
            "Beoordeel kanaalsleutel aan de hand van de goedgekeurde klanteisen. Voorbeeld: bot token.",
            "Vul de waarde in of selecteer deze, kies Volgende of Concept opslaan en controleer de bevestiging.",
            "Beoordeel de effectieve configuratie en resterende voorwaarden voordat je live wijzigingen uitvoert."
          ],
          "permissions": "Operators en admins kunnen configureren en acties uitvoeren. Partners bekijken alleen hun eigen klanten.",
          "limits": "Platformregistratie, geldige sleutels, persoonskoppeling en adapterondersteuning zijn nodig. Opslaan verstuurt geen extern bericht.",
          "example": "bot token"
        }
      }
    },
    {
      "id": "msp.wizard.channels.plain",
      "area": "channels",
      "status": "conditional",
      "conditions": [
        "configuration_only"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.wizard.channels.plain"
      ],
      "source_refs": [
        "apps/cockpit/frontend/src/wizard/StepChannels.jsx"
      ],
      "related": [
        "msp.wizard.review.review"
      ],
      "locales": {
        "en": {
          "title": "Channel setting",
          "purpose": "Save a non-secret channel identifier alongside its credential settings.",
          "when": "When configuring or checking this setting for a client installation.",
          "steps": [
            "Open the client wizard and choose Messaging channels.",
            "Review channel setting against the client’s approved requirements. Example: application ID.",
            "Enter or select the value, then choose Next or Save draft and check the save confirmation.",
            "Review the effective configuration and remaining prerequisites before making live changes."
          ],
          "permissions": "Operators and admins can configure and run actions. Partners can only inspect their owned clients.",
          "limits": "Provider registration, valid credentials, identity mapping and runtime adapter support are required. Saving this setting sends no external message.",
          "example": "application ID"
        },
        "nl": {
          "title": "Kanaalinstelling",
          "purpose": "Sla een niet-geheime kanaalidentificatie op naast de sleutelinstellingen.",
          "when": "Wanneer je deze instelling voor een klantinstallatie configureert of controleert.",
          "steps": [
            "Open de klantwizard en kies Berichtenkanalen.",
            "Beoordeel kanaalinstelling aan de hand van de goedgekeurde klanteisen. Voorbeeld: application ID.",
            "Vul de waarde in of selecteer deze, kies Volgende of Concept opslaan en controleer de bevestiging.",
            "Beoordeel de effectieve configuratie en resterende voorwaarden voordat je live wijzigingen uitvoert."
          ],
          "permissions": "Operators en admins kunnen configureren en acties uitvoeren. Partners bekijken alleen hun eigen klanten.",
          "limits": "Platformregistratie, geldige sleutels, persoonskoppeling en adapterondersteuning zijn nodig. Opslaan verstuurt geen extern bericht.",
          "example": "application ID"
        }
      }
    },
    {
      "id": "msp.wizard.channels.allowAll",
      "area": "channels",
      "status": "conditional",
      "conditions": [
        "configuration_only"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.wizard.channels.allowAll"
      ],
      "source_refs": [
        "apps/cockpit/frontend/src/wizard/StepChannels.jsx"
      ],
      "related": [
        "msp.wizard.review.review"
      ],
      "locales": {
        "en": {
          "title": "Open bot access",
          "purpose": "Decide whether anyone who reaches the platform bot may message it.",
          "when": "When configuring or checking this setting for a client installation.",
          "steps": [
            "Open the client wizard and choose Messaging channels.",
            "Review open bot access against the client’s approved requirements. Example: off for a team bot.",
            "Enter or select the value, then choose Next or Save draft and check the save confirmation.",
            "Review the effective configuration and remaining prerequisites before making live changes."
          ],
          "permissions": "Operators and admins can configure and run actions. Partners can only inspect their owned clients.",
          "limits": "Provider registration, valid credentials, identity mapping and runtime adapter support are required. Saving this setting sends no external message. Leave off for a restricted team bot. Enabling broad access is not equivalent to granting authorised tool access.",
          "example": "off for a team bot"
        },
        "nl": {
          "title": "Open toegang tot de bot",
          "purpose": "Bepaal of iedereen die de platformbot bereikt een bericht mag sturen.",
          "when": "Wanneer je deze instelling voor een klantinstallatie configureert of controleert.",
          "steps": [
            "Open de klantwizard en kies Berichtenkanalen.",
            "Beoordeel open toegang tot de bot aan de hand van de goedgekeurde klanteisen. Voorbeeld: uit voor een teambot.",
            "Vul de waarde in of selecteer deze, kies Volgende of Concept opslaan en controleer de bevestiging.",
            "Beoordeel de effectieve configuratie en resterende voorwaarden voordat je live wijzigingen uitvoert."
          ],
          "permissions": "Operators en admins kunnen configureren en acties uitvoeren. Partners bekijken alleen hun eigen klanten.",
          "limits": "Platformregistratie, geldige sleutels, persoonskoppeling en adapterondersteuning zijn nodig. Opslaan verstuurt geen extern bericht. Laat dit uit voor een afgeschermde teambot. Brede berichttoegang is niet hetzelfde als toestemming voor tools.",
          "example": "uit voor een teambot"
        }
      }
    },
    {
      "id": "msp.wizard.channels.hooks",
      "area": "channels",
      "status": "conditional",
      "conditions": [
        "configuration_only"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.wizard.channels.hooks"
      ],
      "source_refs": [
        "apps/cockpit/frontend/src/wizard/StepChannels.jsx"
      ],
      "related": [
        "msp.wizard.review.review"
      ],
      "locales": {
        "en": {
          "title": "Public channel webhooks",
          "purpose": "Prepare the inbound HTTPS route required by supported webhook-based adapters.",
          "when": "When configuring or checking this setting for a client installation.",
          "steps": [
            "Open the client wizard and choose Messaging channels.",
            "Review public channel webhooks against the client’s approved requirements. Example: Teams or WhatsApp callback.",
            "Enter or select the value, then choose Next or Save draft and check the save confirmation.",
            "Review the effective configuration and remaining prerequisites before making live changes."
          ],
          "permissions": "Operators and admins can configure and run actions. Partners can only inspect their owned clients.",
          "limits": "Provider registration, valid credentials, identity mapping and runtime adapter support are required. Saving this setting sends no external message.",
          "example": "Teams or WhatsApp callback"
        },
        "nl": {
          "title": "Publieke kanaalwebhooks",
          "purpose": "Bereid de inkomende HTTPS-route voor van ondersteunde webhookadapters.",
          "when": "Wanneer je deze instelling voor een klantinstallatie configureert of controleert.",
          "steps": [
            "Open de klantwizard en kies Berichtenkanalen.",
            "Beoordeel publieke kanaalwebhooks aan de hand van de goedgekeurde klanteisen. Voorbeeld: Teams- of WhatsApp-callback.",
            "Vul de waarde in of selecteer deze, kies Volgende of Concept opslaan en controleer de bevestiging.",
            "Beoordeel de effectieve configuratie en resterende voorwaarden voordat je live wijzigingen uitvoert."
          ],
          "permissions": "Operators en admins kunnen configureren en acties uitvoeren. Partners bekijken alleen hun eigen klanten.",
          "limits": "Platformregistratie, geldige sleutels, persoonskoppeling en adapterondersteuning zijn nodig. Opslaan verstuurt geen extern bericht.",
          "example": "Teams- of WhatsApp-callback"
        }
      }
    },
    {
      "id": "msp.wizard.channels.people",
      "area": "channels",
      "status": "conditional",
      "conditions": [
        "configuration_only"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.wizard.channels.people"
      ],
      "source_refs": [
        "apps/cockpit/frontend/src/wizard/StepChannels.jsx"
      ],
      "related": [
        "msp.wizard.review.review"
      ],
      "locales": {
        "en": {
          "title": "Channel identity map",
          "purpose": "Map platform accounts to the people governed by the installation.",
          "when": "When configuring or checking this setting for a client installation.",
          "steps": [
            "Open the client wizard and choose Messaging channels.",
            "Review channel identity map against the client’s approved requirements. Example: Telegram ID linked to work email.",
            "Enter or select the value, then choose Next or Save draft and check the save confirmation.",
            "Review the effective configuration and remaining prerequisites before making live changes."
          ],
          "permissions": "Operators and admins can configure and run actions. Partners can only inspect their owned clients.",
          "limits": "Provider registration, valid credentials, identity mapping and runtime adapter support are required. Saving this setting sends no external message.",
          "example": "Telegram ID linked to work email"
        },
        "nl": {
          "title": "Identiteiten per kanaal",
          "purpose": "Koppel platformaccounts aan personen die onder het installatiebeleid vallen.",
          "when": "Wanneer je deze instelling voor een klantinstallatie configureert of controleert.",
          "steps": [
            "Open de klantwizard en kies Berichtenkanalen.",
            "Beoordeel identiteiten per kanaal aan de hand van de goedgekeurde klanteisen. Voorbeeld: Telegram-ID gekoppeld aan werkadres.",
            "Vul de waarde in of selecteer deze, kies Volgende of Concept opslaan en controleer de bevestiging.",
            "Beoordeel de effectieve configuratie en resterende voorwaarden voordat je live wijzigingen uitvoert."
          ],
          "permissions": "Operators en admins kunnen configureren en acties uitvoeren. Partners bekijken alleen hun eigen klanten.",
          "limits": "Platformregistratie, geldige sleutels, persoonskoppeling en adapterondersteuning zijn nodig. Opslaan verstuurt geen extern bericht.",
          "example": "Telegram-ID gekoppeld aan werkadres"
        }
      }
    },
    {
      "id": "msp.wizard.channels.personId",
      "area": "channels",
      "status": "conditional",
      "conditions": [
        "configuration_only"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.wizard.channels.personId"
      ],
      "source_refs": [
        "apps/cockpit/frontend/src/wizard/StepChannels.jsx"
      ],
      "related": [
        "msp.wizard.review.review"
      ],
      "locales": {
        "en": {
          "title": "Platform user ID",
          "purpose": "Enter the stable user identifier required by the selected channel.",
          "when": "When configuring or checking this setting for a client installation.",
          "steps": [
            "Open the client wizard and choose Messaging channels.",
            "Review platform user id against the client’s approved requirements. Example: Slack U0123456789.",
            "Enter or select the value, then choose Next or Save draft and check the save confirmation.",
            "Review the effective configuration and remaining prerequisites before making live changes."
          ],
          "permissions": "Operators and admins can configure and run actions. Partners can only inspect their owned clients.",
          "limits": "Provider registration, valid credentials, identity mapping and runtime adapter support are required. Saving this setting sends no external message.",
          "example": "Slack U0123456789"
        },
        "nl": {
          "title": "Gebruikers-ID van het platform",
          "purpose": "Vul de vaste gebruikersidentificatie van het gekozen kanaal in.",
          "when": "Wanneer je deze instelling voor een klantinstallatie configureert of controleert.",
          "steps": [
            "Open de klantwizard en kies Berichtenkanalen.",
            "Beoordeel gebruikers-id van het platform aan de hand van de goedgekeurde klanteisen. Voorbeeld: Slack U0123456789.",
            "Vul de waarde in of selecteer deze, kies Volgende of Concept opslaan en controleer de bevestiging.",
            "Beoordeel de effectieve configuratie en resterende voorwaarden voordat je live wijzigingen uitvoert."
          ],
          "permissions": "Operators en admins kunnen configureren en acties uitvoeren. Partners bekijken alleen hun eigen klanten.",
          "limits": "Platformregistratie, geldige sleutels, persoonskoppeling en adapterondersteuning zijn nodig. Opslaan verstuurt geen extern bericht.",
          "example": "Slack U0123456789"
        }
      }
    },
    {
      "id": "msp.wizard.channels.profile",
      "area": "channels",
      "status": "conditional",
      "conditions": [
        "configuration_only"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.wizard.channels.profile"
      ],
      "source_refs": [
        "apps/cockpit/frontend/src/wizard/StepChannels.jsx"
      ],
      "related": [
        "msp.wizard.review.review"
      ],
      "locales": {
        "en": {
          "title": "Messaging engine profile",
          "purpose": "Request the engine profile where that person’s messaging turns run.",
          "when": "When configuring or checking this setting for a client installation.",
          "steps": [
            "Open the client wizard and choose Messaging channels.",
            "Review messaging engine profile against the client’s approved requirements. Example: personal profile slug.",
            "Enter or select the value, then choose Next or Save draft and check the save confirmation.",
            "Review the effective configuration and remaining prerequisites before making live changes."
          ],
          "permissions": "Operators and admins can configure and run actions. Partners can only inspect their owned clients.",
          "limits": "Provider registration, valid credentials, identity mapping and runtime adapter support are required. Saving this setting sends no external message.",
          "example": "personal profile slug"
        },
        "nl": {
          "title": "Engineprofiel voor berichten",
          "purpose": "Kies het engineprofiel waarin de berichten van die persoon worden verwerkt.",
          "when": "Wanneer je deze instelling voor een klantinstallatie configureert of controleert.",
          "steps": [
            "Open de klantwizard en kies Berichtenkanalen.",
            "Beoordeel engineprofiel voor berichten aan de hand van de goedgekeurde klanteisen. Voorbeeld: vaste code van persoonlijk profiel.",
            "Vul de waarde in of selecteer deze, kies Volgende of Concept opslaan en controleer de bevestiging.",
            "Beoordeel de effectieve configuratie en resterende voorwaarden voordat je live wijzigingen uitvoert."
          ],
          "permissions": "Operators en admins kunnen configureren en acties uitvoeren. Partners bekijken alleen hun eigen klanten.",
          "limits": "Platformregistratie, geldige sleutels, persoonskoppeling en adapterondersteuning zijn nodig. Opslaan verstuurt geen extern bericht.",
          "example": "vaste code van persoonlijk profiel"
        }
      }
    },
    {
      "id": "msp.wizard.channels.telegram",
      "area": "channels",
      "status": "conditional",
      "conditions": [
        "configuration_only"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.wizard.channels.telegram"
      ],
      "source_refs": [
        "apps/cockpit/frontend/src/wizard/StepChannels.jsx"
      ],
      "related": [
        "msp.wizard.review.review"
      ],
      "locales": {
        "en": {
          "title": "Telegram channel",
          "purpose": "Connect a Telegram bot after setting its token and identity mapping.",
          "when": "When configuring or checking this setting for a client installation.",
          "steps": [
            "Open the client wizard and choose Messaging channels.",
            "Review telegram channel against the client’s approved requirements. Example: BotFather bot.",
            "Enter or select the value, then choose Next or Save draft and check the save confirmation.",
            "Review the effective configuration and remaining prerequisites before making live changes."
          ],
          "permissions": "Operators and admins can configure and run actions. Partners can only inspect their owned clients.",
          "limits": "Provider registration, valid credentials, identity mapping and runtime adapter support are required. Saving this setting sends no external message.",
          "example": "BotFather bot"
        },
        "nl": {
          "title": "Telegram-kanaal",
          "purpose": "Verbind een Telegram-bot na het instellen van token en persoonskoppelingen.",
          "when": "Wanneer je deze instelling voor een klantinstallatie configureert of controleert.",
          "steps": [
            "Open de klantwizard en kies Berichtenkanalen.",
            "Beoordeel telegram-kanaal aan de hand van de goedgekeurde klanteisen. Voorbeeld: BotFather bot.",
            "Vul de waarde in of selecteer deze, kies Volgende of Concept opslaan en controleer de bevestiging.",
            "Beoordeel de effectieve configuratie en resterende voorwaarden voordat je live wijzigingen uitvoert."
          ],
          "permissions": "Operators en admins kunnen configureren en acties uitvoeren. Partners bekijken alleen hun eigen klanten.",
          "limits": "Platformregistratie, geldige sleutels, persoonskoppeling en adapterondersteuning zijn nodig. Opslaan verstuurt geen extern bericht.",
          "example": "BotFather bot"
        }
      }
    },
    {
      "id": "msp.wizard.channels.slack",
      "area": "channels",
      "status": "conditional",
      "conditions": [
        "configuration_only"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.wizard.channels.slack"
      ],
      "source_refs": [
        "apps/cockpit/frontend/src/wizard/StepChannels.jsx"
      ],
      "related": [
        "msp.wizard.review.review"
      ],
      "locales": {
        "en": {
          "title": "Slack channel",
          "purpose": "Prepare a Slack Socket Mode app with bot and app-level tokens.",
          "when": "When configuring or checking this setting for a client installation.",
          "steps": [
            "Open the client wizard and choose Messaging channels.",
            "Review slack channel against the client’s approved requirements. Example: Slack member ID.",
            "Enter or select the value, then choose Next or Save draft and check the save confirmation.",
            "Review the effective configuration and remaining prerequisites before making live changes."
          ],
          "permissions": "Operators and admins can configure and run actions. Partners can only inspect their owned clients.",
          "limits": "Provider registration, valid credentials, identity mapping and runtime adapter support are required. Saving this setting sends no external message.",
          "example": "Slack member ID"
        },
        "nl": {
          "title": "Slack-kanaal",
          "purpose": "Bereid een Slack-app in Socket Mode voor met bot- en apptokens.",
          "when": "Wanneer je deze instelling voor een klantinstallatie configureert of controleert.",
          "steps": [
            "Open de klantwizard en kies Berichtenkanalen.",
            "Beoordeel slack-kanaal aan de hand van de goedgekeurde klanteisen. Voorbeeld: Slack member ID.",
            "Vul de waarde in of selecteer deze, kies Volgende of Concept opslaan en controleer de bevestiging.",
            "Beoordeel de effectieve configuratie en resterende voorwaarden voordat je live wijzigingen uitvoert."
          ],
          "permissions": "Operators en admins kunnen configureren en acties uitvoeren. Partners bekijken alleen hun eigen klanten.",
          "limits": "Platformregistratie, geldige sleutels, persoonskoppeling en adapterondersteuning zijn nodig. Opslaan verstuurt geen extern bericht.",
          "example": "Slack member ID"
        }
      }
    },
    {
      "id": "msp.wizard.channels.teams",
      "area": "channels",
      "status": "conditional",
      "conditions": [
        "configuration_only"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.wizard.channels.teams"
      ],
      "source_refs": [
        "apps/cockpit/frontend/src/wizard/StepChannels.jsx"
      ],
      "related": [
        "msp.wizard.review.review"
      ],
      "locales": {
        "en": {
          "title": "Teams channel",
          "purpose": "Prepare the supported Teams bot registration and inbound webhook.",
          "when": "When configuring or checking this setting for a client installation.",
          "steps": [
            "Open the client wizard and choose Messaging channels.",
            "Review teams channel against the client’s approved requirements. Example: Entra tenant and bot app.",
            "Enter or select the value, then choose Next or Save draft and check the save confirmation.",
            "Review the effective configuration and remaining prerequisites before making live changes."
          ],
          "permissions": "Operators and admins can configure and run actions. Partners can only inspect their owned clients.",
          "limits": "Provider registration, valid credentials, identity mapping and runtime adapter support are required. Saving this setting sends no external message.",
          "example": "Entra tenant and bot app"
        },
        "nl": {
          "title": "Teams-kanaal",
          "purpose": "Bereid de ondersteunde Teams-botregistratie en inkomende webhook voor.",
          "when": "Wanneer je deze instelling voor een klantinstallatie configureert of controleert.",
          "steps": [
            "Open de klantwizard en kies Berichtenkanalen.",
            "Beoordeel teams-kanaal aan de hand van de goedgekeurde klanteisen. Voorbeeld: Entra-tenant en botapp.",
            "Vul de waarde in of selecteer deze, kies Volgende of Concept opslaan en controleer de bevestiging.",
            "Beoordeel de effectieve configuratie en resterende voorwaarden voordat je live wijzigingen uitvoert."
          ],
          "permissions": "Operators en admins kunnen configureren en acties uitvoeren. Partners bekijken alleen hun eigen klanten.",
          "limits": "Platformregistratie, geldige sleutels, persoonskoppeling en adapterondersteuning zijn nodig. Opslaan verstuurt geen extern bericht.",
          "example": "Entra-tenant en botapp"
        }
      }
    },
    {
      "id": "msp.wizard.channels.discord",
      "area": "channels",
      "status": "conditional",
      "conditions": [
        "configuration_only"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.wizard.channels.discord"
      ],
      "source_refs": [
        "apps/cockpit/frontend/src/wizard/StepChannels.jsx"
      ],
      "related": [
        "msp.wizard.review.review"
      ],
      "locales": {
        "en": {
          "title": "Discord channel",
          "purpose": "Prepare a Discord bot with the required message access settings.",
          "when": "When configuring or checking this setting for a client installation.",
          "steps": [
            "Open the client wizard and choose Messaging channels.",
            "Review discord channel against the client’s approved requirements. Example: Discord user ID.",
            "Enter or select the value, then choose Next or Save draft and check the save confirmation.",
            "Review the effective configuration and remaining prerequisites before making live changes."
          ],
          "permissions": "Operators and admins can configure and run actions. Partners can only inspect their owned clients.",
          "limits": "Provider registration, valid credentials, identity mapping and runtime adapter support are required. Saving this setting sends no external message.",
          "example": "Discord user ID"
        },
        "nl": {
          "title": "Discord-kanaal",
          "purpose": "Bereid een Discord-bot voor met de vereiste berichttoegangsinstellingen.",
          "when": "Wanneer je deze instelling voor een klantinstallatie configureert of controleert.",
          "steps": [
            "Open de klantwizard en kies Berichtenkanalen.",
            "Beoordeel discord-kanaal aan de hand van de goedgekeurde klanteisen. Voorbeeld: Discord user ID.",
            "Vul de waarde in of selecteer deze, kies Volgende of Concept opslaan en controleer de bevestiging.",
            "Beoordeel de effectieve configuratie en resterende voorwaarden voordat je live wijzigingen uitvoert."
          ],
          "permissions": "Operators en admins kunnen configureren en acties uitvoeren. Partners bekijken alleen hun eigen klanten.",
          "limits": "Platformregistratie, geldige sleutels, persoonskoppeling en adapterondersteuning zijn nodig. Opslaan verstuurt geen extern bericht.",
          "example": "Discord user ID"
        }
      }
    },
    {
      "id": "msp.wizard.channels.whatsapp_cloud",
      "area": "channels",
      "status": "conditional",
      "conditions": [
        "configuration_only"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.wizard.channels.whatsapp_cloud"
      ],
      "source_refs": [
        "apps/cockpit/frontend/src/wizard/StepChannels.jsx"
      ],
      "related": [
        "msp.wizard.review.review"
      ],
      "locales": {
        "en": {
          "title": "WhatsApp Business channel",
          "purpose": "Prepare the Meta Cloud API adapter, number identifiers and webhook verification.",
          "when": "When configuring or checking this setting for a client installation.",
          "steps": [
            "Open the client wizard and choose Messaging channels.",
            "Review whatsapp business channel against the client’s approved requirements. Example: business phone number ID.",
            "Enter or select the value, then choose Next or Save draft and check the save confirmation.",
            "Review the effective configuration and remaining prerequisites before making live changes."
          ],
          "permissions": "Operators and admins can configure and run actions. Partners can only inspect their owned clients.",
          "limits": "Provider registration, valid credentials, identity mapping and runtime adapter support are required. Saving this setting sends no external message.",
          "example": "business phone number ID"
        },
        "nl": {
          "title": "WhatsApp Business-kanaal",
          "purpose": "Bereid de Meta Cloud API-adapter, nummeridentificaties en webhookverificatie voor.",
          "when": "Wanneer je deze instelling voor een klantinstallatie configureert of controleert.",
          "steps": [
            "Open de klantwizard en kies Berichtenkanalen.",
            "Beoordeel whatsapp business-kanaal aan de hand van de goedgekeurde klanteisen. Voorbeeld: ID van zakelijk telefoonnummer.",
            "Vul de waarde in of selecteer deze, kies Volgende of Concept opslaan en controleer de bevestiging.",
            "Beoordeel de effectieve configuratie en resterende voorwaarden voordat je live wijzigingen uitvoert."
          ],
          "permissions": "Operators en admins kunnen configureren en acties uitvoeren. Partners bekijken alleen hun eigen klanten.",
          "limits": "Platformregistratie, geldige sleutels, persoonskoppeling en adapterondersteuning zijn nodig. Opslaan verstuurt geen extern bericht.",
          "example": "ID van zakelijk telefoonnummer"
        }
      }
    },
    {
      "id": "msp.wizard.channels.google_chat",
      "area": "channels",
      "status": "conditional",
      "conditions": [
        "configuration_only"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.wizard.channels.google_chat"
      ],
      "source_refs": [
        "apps/cockpit/frontend/src/wizard/StepChannels.jsx"
      ],
      "related": [
        "msp.wizard.review.review"
      ],
      "locales": {
        "en": {
          "title": "Google Chat channel",
          "purpose": "Prepare the supported Workspace Chat app and subscription settings.",
          "when": "When configuring or checking this setting for a client installation.",
          "steps": [
            "Open the client wizard and choose Messaging channels.",
            "Review google chat channel against the client’s approved requirements. Example: Workspace email.",
            "Enter or select the value, then choose Next or Save draft and check the save confirmation.",
            "Review the effective configuration and remaining prerequisites before making live changes."
          ],
          "permissions": "Operators and admins can configure and run actions. Partners can only inspect their owned clients.",
          "limits": "Provider registration, valid credentials, identity mapping and runtime adapter support are required. Saving this setting sends no external message.",
          "example": "Workspace email"
        },
        "nl": {
          "title": "Google Chat-kanaal",
          "purpose": "Bereid de ondersteunde Workspace Chat-app en abonnementsinstellingen voor.",
          "when": "Wanneer je deze instelling voor een klantinstallatie configureert of controleert.",
          "steps": [
            "Open de klantwizard en kies Berichtenkanalen.",
            "Beoordeel google chat-kanaal aan de hand van de goedgekeurde klanteisen. Voorbeeld: Workspace-adres.",
            "Vul de waarde in of selecteer deze, kies Volgende of Concept opslaan en controleer de bevestiging.",
            "Beoordeel de effectieve configuratie en resterende voorwaarden voordat je live wijzigingen uitvoert."
          ],
          "permissions": "Operators en admins kunnen configureren en acties uitvoeren. Partners bekijken alleen hun eigen klanten.",
          "limits": "Platformregistratie, geldige sleutels, persoonskoppeling en adapterondersteuning zijn nodig. Opslaan verstuurt geen extern bericht.",
          "example": "Workspace-adres"
        }
      }
    },
    {
      "id": "msp.wizard.credentials.intro",
      "area": "credentials",
      "status": "conditional",
      "conditions": [
        "configuration_only"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.wizard.credentials.intro"
      ],
      "source_refs": [
        "apps/cockpit/frontend/src/wizard/StepCredentials.jsx"
      ],
      "related": [
        "msp.wizard.review.review"
      ],
      "locales": {
        "en": {
          "title": "Write-only credentials",
          "purpose": "Save credentials separately from the non-secret configuration preview.",
          "when": "When configuring or checking this setting for a client installation.",
          "steps": [
            "Open the client wizard and choose Credentials.",
            "Review write-only credentials against the client’s approved requirements. Example: Stored indicator.",
            "Use the field’s save/upload action and check its stored confirmation.",
            "Review the effective configuration and remaining prerequisites before making live changes."
          ],
          "permissions": "Operators and admins can configure and run actions. Partners can only inspect their owned clients.",
          "limits": "Saved secret values are write-only. Keep existing customer credentials unless replacement is authorised. Store only the credential requested by the selected target.",
          "example": "Stored indicator"
        },
        "nl": {
          "title": "Eenrichtingsopslag van sleutels",
          "purpose": "Sla sleutels afzonderlijk op van het configuratieoverzicht zonder geheimen.",
          "when": "Wanneer je deze instelling voor een klantinstallatie configureert of controleert.",
          "steps": [
            "Open de klantwizard en kies Inloggegevens.",
            "Beoordeel eenrichtingsopslag van sleutels aan de hand van de goedgekeurde klanteisen. Voorbeeld: indicatie Opgeslagen.",
            "Gebruik de opslag- of uploadactie van het veld en controleer de bevestiging.",
            "Beoordeel de effectieve configuratie en resterende voorwaarden voordat je live wijzigingen uitvoert."
          ],
          "permissions": "Operators en admins kunnen configureren en acties uitvoeren. Partners bekijken alleen hun eigen klanten.",
          "limits": "Opgeslagen geheimen worden niet teruggelezen. Behoud bestaande klantsleutels tenzij vervanging is goedgekeurd. Sla alleen de sleutel op die het gekozen doel vraagt.",
          "example": "indicatie Opgeslagen"
        }
      }
    },
    {
      "id": "msp.wizard.credentials.scaleway",
      "area": "credentials",
      "status": "conditional",
      "conditions": [
        "configuration_only"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.wizard.credentials.scaleway"
      ],
      "source_refs": [
        "apps/cockpit/frontend/src/wizard/StepCredentials.jsx"
      ],
      "related": [
        "msp.wizard.review.review"
      ],
      "locales": {
        "en": {
          "title": "Scaleway credentials",
          "purpose": "Store the identity and account references required by Scaleway provisioning.",
          "when": "When configuring or checking this setting for a client installation.",
          "steps": [
            "Open the client wizard and choose Credentials.",
            "Review scaleway credentials against the client’s approved requirements. Example: client-specific API identity.",
            "Use the field’s save/upload action and check its stored confirmation.",
            "Review the effective configuration and remaining prerequisites before making live changes."
          ],
          "permissions": "Operators and admins can configure and run actions. Partners can only inspect their owned clients.",
          "limits": "Saved secret values are write-only. Keep existing customer credentials unless replacement is authorised. Store only the credential requested by the selected target.",
          "example": "client-specific API identity"
        },
        "nl": {
          "title": "Scaleway-inloggegevens",
          "purpose": "Sla de identiteit en accountverwijzingen voor Scaleway-installatie op.",
          "when": "Wanneer je deze instelling voor een klantinstallatie configureert of controleert.",
          "steps": [
            "Open de klantwizard en kies Inloggegevens.",
            "Beoordeel scaleway-inloggegevens aan de hand van de goedgekeurde klanteisen. Voorbeeld: klantspecifieke API-identiteit.",
            "Gebruik de opslag- of uploadactie van het veld en controleer de bevestiging.",
            "Beoordeel de effectieve configuratie en resterende voorwaarden voordat je live wijzigingen uitvoert."
          ],
          "permissions": "Operators en admins kunnen configureren en acties uitvoeren. Partners bekijken alleen hun eigen klanten.",
          "limits": "Opgeslagen geheimen worden niet teruggelezen. Behoud bestaande klantsleutels tenzij vervanging is goedgekeurd. Sla alleen de sleutel op die het gekozen doel vraagt.",
          "example": "klantspecifieke API-identiteit"
        }
      }
    },
    {
      "id": "msp.wizard.credentials.scw.access",
      "area": "credentials",
      "status": "conditional",
      "conditions": [
        "configuration_only"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.wizard.credentials.scw.access"
      ],
      "source_refs": [
        "apps/cockpit/frontend/src/wizard/StepCredentials.jsx"
      ],
      "related": [
        "msp.wizard.review.review"
      ],
      "locales": {
        "en": {
          "title": "Scaleway access key",
          "purpose": "Store the public identifier of the Scaleway API key pair.",
          "when": "When configuring or checking this setting for a client installation.",
          "steps": [
            "Open the client wizard and choose Credentials.",
            "Review scaleway access key against the client’s approved requirements. Example: SCW_ACCESS_KEY.",
            "Use the field’s save/upload action and check its stored confirmation.",
            "Review the effective configuration and remaining prerequisites before making live changes."
          ],
          "permissions": "Operators and admins can configure and run actions. Partners can only inspect their owned clients.",
          "limits": "Saved secret values are write-only. Keep existing customer credentials unless replacement is authorised. Store only the credential requested by the selected target.",
          "example": "SCW_ACCESS_KEY"
        },
        "nl": {
          "title": "Scaleway-toegangssleutel",
          "purpose": "Sla de publieke identificatie van het Scaleway-sleutelpaar op.",
          "when": "Wanneer je deze instelling voor een klantinstallatie configureert of controleert.",
          "steps": [
            "Open de klantwizard en kies Inloggegevens.",
            "Beoordeel scaleway-toegangssleutel aan de hand van de goedgekeurde klanteisen. Voorbeeld: SCW_ACCESS_KEY.",
            "Gebruik de opslag- of uploadactie van het veld en controleer de bevestiging.",
            "Beoordeel de effectieve configuratie en resterende voorwaarden voordat je live wijzigingen uitvoert."
          ],
          "permissions": "Operators en admins kunnen configureren en acties uitvoeren. Partners bekijken alleen hun eigen klanten.",
          "limits": "Opgeslagen geheimen worden niet teruggelezen. Behoud bestaande klantsleutels tenzij vervanging is goedgekeurd. Sla alleen de sleutel op die het gekozen doel vraagt.",
          "example": "SCW_ACCESS_KEY"
        }
      }
    },
    {
      "id": "msp.wizard.credentials.scw.secret",
      "area": "credentials",
      "status": "conditional",
      "conditions": [
        "configuration_only"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.wizard.credentials.scw.secret"
      ],
      "source_refs": [
        "apps/cockpit/frontend/src/wizard/StepCredentials.jsx"
      ],
      "related": [
        "msp.wizard.review.review"
      ],
      "locales": {
        "en": {
          "title": "Scaleway secret key",
          "purpose": "Store the private half of the Scaleway API key pair.",
          "when": "When configuring or checking this setting for a client installation.",
          "steps": [
            "Open the client wizard and choose Credentials.",
            "Review scaleway secret key against the client’s approved requirements. Example: SCW_SECRET_KEY.",
            "Use the field’s save/upload action and check its stored confirmation.",
            "Review the effective configuration and remaining prerequisites before making live changes."
          ],
          "permissions": "Operators and admins can configure and run actions. Partners can only inspect their owned clients.",
          "limits": "Saved secret values are write-only. Keep existing customer credentials unless replacement is authorised. Store only the credential requested by the selected target.",
          "example": "SCW_SECRET_KEY"
        },
        "nl": {
          "title": "Geheime Scaleway-sleutel",
          "purpose": "Sla het geheime deel van het Scaleway-sleutelpaar op.",
          "when": "Wanneer je deze instelling voor een klantinstallatie configureert of controleert.",
          "steps": [
            "Open de klantwizard en kies Inloggegevens.",
            "Beoordeel geheime scaleway-sleutel aan de hand van de goedgekeurde klanteisen. Voorbeeld: SCW_SECRET_KEY.",
            "Gebruik de opslag- of uploadactie van het veld en controleer de bevestiging.",
            "Beoordeel de effectieve configuratie en resterende voorwaarden voordat je live wijzigingen uitvoert."
          ],
          "permissions": "Operators en admins kunnen configureren en acties uitvoeren. Partners bekijken alleen hun eigen klanten.",
          "limits": "Opgeslagen geheimen worden niet teruggelezen. Behoud bestaande klantsleutels tenzij vervanging is goedgekeurd. Sla alleen de sleutel op die het gekozen doel vraagt.",
          "example": "SCW_SECRET_KEY"
        }
      }
    },
    {
      "id": "msp.wizard.credentials.scw.project",
      "area": "credentials",
      "status": "conditional",
      "conditions": [
        "configuration_only"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.wizard.credentials.scw.project"
      ],
      "source_refs": [
        "apps/cockpit/frontend/src/wizard/StepCredentials.jsx"
      ],
      "related": [
        "msp.wizard.review.review"
      ],
      "locales": {
        "en": {
          "title": "Scaleway project",
          "purpose": "Set the project that should own the client resources.",
          "when": "When configuring or checking this setting for a client installation.",
          "steps": [
            "Open the client wizard and choose Credentials.",
            "Review scaleway project against the client’s approved requirements. Example: SCW_DEFAULT_PROJECT_ID.",
            "Use the field’s save/upload action and check its stored confirmation.",
            "Review the effective configuration and remaining prerequisites before making live changes."
          ],
          "permissions": "Operators and admins can configure and run actions. Partners can only inspect their owned clients.",
          "limits": "Saved secret values are write-only. Keep existing customer credentials unless replacement is authorised. Store only the credential requested by the selected target.",
          "example": "SCW_DEFAULT_PROJECT_ID"
        },
        "nl": {
          "title": "Scaleway-project",
          "purpose": "Stel het project in dat eigenaar wordt van de klantmiddelen.",
          "when": "Wanneer je deze instelling voor een klantinstallatie configureert of controleert.",
          "steps": [
            "Open de klantwizard en kies Inloggegevens.",
            "Beoordeel scaleway-project aan de hand van de goedgekeurde klanteisen. Voorbeeld: SCW_DEFAULT_PROJECT_ID.",
            "Gebruik de opslag- of uploadactie van het veld en controleer de bevestiging.",
            "Beoordeel de effectieve configuratie en resterende voorwaarden voordat je live wijzigingen uitvoert."
          ],
          "permissions": "Operators en admins kunnen configureren en acties uitvoeren. Partners bekijken alleen hun eigen klanten.",
          "limits": "Opgeslagen geheimen worden niet teruggelezen. Behoud bestaande klantsleutels tenzij vervanging is goedgekeurd. Sla alleen de sleutel op die het gekozen doel vraagt.",
          "example": "SCW_DEFAULT_PROJECT_ID"
        }
      }
    },
    {
      "id": "msp.wizard.credentials.scw.org",
      "area": "credentials",
      "status": "conditional",
      "conditions": [
        "configuration_only"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.wizard.credentials.scw.org"
      ],
      "source_refs": [
        "apps/cockpit/frontend/src/wizard/StepCredentials.jsx"
      ],
      "related": [
        "msp.wizard.review.review"
      ],
      "locales": {
        "en": {
          "title": "Scaleway organisation",
          "purpose": "Set the organisation used by the selected cloud configuration.",
          "when": "When configuring or checking this setting for a client installation.",
          "steps": [
            "Open the client wizard and choose Credentials.",
            "Review scaleway organisation against the client’s approved requirements. Example: SCW_DEFAULT_ORGANIZATION_ID.",
            "Use the field’s save/upload action and check its stored confirmation.",
            "Review the effective configuration and remaining prerequisites before making live changes."
          ],
          "permissions": "Operators and admins can configure and run actions. Partners can only inspect their owned clients.",
          "limits": "Saved secret values are write-only. Keep existing customer credentials unless replacement is authorised. Store only the credential requested by the selected target.",
          "example": "SCW_DEFAULT_ORGANIZATION_ID"
        },
        "nl": {
          "title": "Scaleway-organisatie",
          "purpose": "Stel de organisatie voor de gekozen cloudconfiguratie in.",
          "when": "Wanneer je deze instelling voor een klantinstallatie configureert of controleert.",
          "steps": [
            "Open de klantwizard en kies Inloggegevens.",
            "Beoordeel scaleway-organisatie aan de hand van de goedgekeurde klanteisen. Voorbeeld: SCW_DEFAULT_ORGANIZATION_ID.",
            "Gebruik de opslag- of uploadactie van het veld en controleer de bevestiging.",
            "Beoordeel de effectieve configuratie en resterende voorwaarden voordat je live wijzigingen uitvoert."
          ],
          "permissions": "Operators en admins kunnen configureren en acties uitvoeren. Partners bekijken alleen hun eigen klanten.",
          "limits": "Opgeslagen geheimen worden niet teruggelezen. Behoud bestaande klantsleutels tenzij vervanging is goedgekeurd. Sla alleen de sleutel op die het gekozen doel vraagt.",
          "example": "SCW_DEFAULT_ORGANIZATION_ID"
        }
      }
    },
    {
      "id": "msp.wizard.credentials.gcp",
      "area": "credentials",
      "status": "conditional",
      "conditions": [
        "configuration_only"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.wizard.credentials.gcp"
      ],
      "source_refs": [
        "apps/cockpit/frontend/src/wizard/StepCredentials.jsx"
      ],
      "related": [
        "msp.wizard.review.review"
      ],
      "locales": {
        "en": {
          "title": "Google Cloud credentials",
          "purpose": "Provide the service-account identity authorised for the intended project.",
          "when": "When configuring or checking this setting for a client installation.",
          "steps": [
            "Open the client wizard and choose Credentials.",
            "Review google cloud credentials against the client’s approved requirements. Example: client service account.",
            "Use the field’s save/upload action and check its stored confirmation.",
            "Review the effective configuration and remaining prerequisites before making live changes."
          ],
          "permissions": "Operators and admins can configure and run actions. Partners can only inspect their owned clients.",
          "limits": "Saved secret values are write-only. Keep existing customer credentials unless replacement is authorised. Store only the credential requested by the selected target.",
          "example": "client service account"
        },
        "nl": {
          "title": "Google Cloud-inloggegevens",
          "purpose": "Geef de serviceaccountidentiteit op die voor het bedoelde project bevoegd is.",
          "when": "Wanneer je deze instelling voor een klantinstallatie configureert of controleert.",
          "steps": [
            "Open de klantwizard en kies Inloggegevens.",
            "Beoordeel google cloud-inloggegevens aan de hand van de goedgekeurde klanteisen. Voorbeeld: serviceaccount van de klant.",
            "Gebruik de opslag- of uploadactie van het veld en controleer de bevestiging.",
            "Beoordeel de effectieve configuratie en resterende voorwaarden voordat je live wijzigingen uitvoert."
          ],
          "permissions": "Operators en admins kunnen configureren en acties uitvoeren. Partners bekijken alleen hun eigen klanten.",
          "limits": "Opgeslagen geheimen worden niet teruggelezen. Behoud bestaande klantsleutels tenzij vervanging is goedgekeurd. Sla alleen de sleutel op die het gekozen doel vraagt.",
          "example": "serviceaccount van de klant"
        }
      }
    },
    {
      "id": "msp.wizard.credentials.gcpFile",
      "area": "credentials",
      "status": "conditional",
      "conditions": [
        "configuration_only"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.wizard.credentials.gcpFile"
      ],
      "source_refs": [
        "apps/cockpit/frontend/src/wizard/StepCredentials.jsx"
      ],
      "related": [
        "msp.wizard.review.review"
      ],
      "locales": {
        "en": {
          "title": "Service-account JSON file",
          "purpose": "Upload the service-account file to the private client secret store.",
          "when": "When configuring or checking this setting for a client installation.",
          "steps": [
            "Open the client wizard and choose Credentials.",
            "Review service-account json file against the client’s approved requirements. Example: gcp-sa.json.",
            "Use the field’s save/upload action and check its stored confirmation.",
            "Review the effective configuration and remaining prerequisites before making live changes."
          ],
          "permissions": "Operators and admins can configure and run actions. Partners can only inspect their owned clients.",
          "limits": "Saved secret values are write-only. Keep existing customer credentials unless replacement is authorised. Store only the credential requested by the selected target.",
          "example": "gcp-sa.json"
        },
        "nl": {
          "title": "JSON-bestand van het serviceaccount",
          "purpose": "Upload het serviceaccountbestand naar de privéopslag voor klantgeheimen.",
          "when": "Wanneer je deze instelling voor een klantinstallatie configureert of controleert.",
          "steps": [
            "Open de klantwizard en kies Inloggegevens.",
            "Beoordeel json-bestand van het serviceaccount aan de hand van de goedgekeurde klanteisen. Voorbeeld: gcp-sa.json.",
            "Gebruik de opslag- of uploadactie van het veld en controleer de bevestiging.",
            "Beoordeel de effectieve configuratie en resterende voorwaarden voordat je live wijzigingen uitvoert."
          ],
          "permissions": "Operators en admins kunnen configureren en acties uitvoeren. Partners bekijken alleen hun eigen klanten.",
          "limits": "Opgeslagen geheimen worden niet teruggelezen. Behoud bestaande klantsleutels tenzij vervanging is goedgekeurd. Sla alleen de sleutel op die het gekozen doel vraagt.",
          "example": "gcp-sa.json"
        }
      }
    },
    {
      "id": "msp.wizard.credentials.azure",
      "area": "credentials",
      "status": "conditional",
      "conditions": [
        "configuration_only"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.wizard.credentials.azure"
      ],
      "source_refs": [
        "apps/cockpit/frontend/src/wizard/StepCredentials.jsx"
      ],
      "related": [
        "msp.wizard.review.review"
      ],
      "locales": {
        "en": {
          "title": "Azure credentials",
          "purpose": "Store the service-principal credentials required by the selected deployment.",
          "when": "When configuring or checking this setting for a client installation.",
          "steps": [
            "Open the client wizard and choose Credentials.",
            "Review azure credentials against the client’s approved requirements. Example: client-scoped service principal.",
            "Use the field’s save/upload action and check its stored confirmation.",
            "Review the effective configuration and remaining prerequisites before making live changes."
          ],
          "permissions": "Operators and admins can configure and run actions. Partners can only inspect their owned clients.",
          "limits": "Saved secret values are write-only. Keep existing customer credentials unless replacement is authorised. Store only the credential requested by the selected target.",
          "example": "client-scoped service principal"
        },
        "nl": {
          "title": "Azure-inloggegevens",
          "purpose": "Sla de serviceprincipalgegevens op die voor de gekozen installatie nodig zijn.",
          "when": "Wanneer je deze instelling voor een klantinstallatie configureert of controleert.",
          "steps": [
            "Open de klantwizard en kies Inloggegevens.",
            "Beoordeel azure-inloggegevens aan de hand van de goedgekeurde klanteisen. Voorbeeld: serviceprincipal met klantspecifieke rechten.",
            "Gebruik de opslag- of uploadactie van het veld en controleer de bevestiging.",
            "Beoordeel de effectieve configuratie en resterende voorwaarden voordat je live wijzigingen uitvoert."
          ],
          "permissions": "Operators en admins kunnen configureren en acties uitvoeren. Partners bekijken alleen hun eigen klanten.",
          "limits": "Opgeslagen geheimen worden niet teruggelezen. Behoud bestaande klantsleutels tenzij vervanging is goedgekeurd. Sla alleen de sleutel op die het gekozen doel vraagt.",
          "example": "serviceprincipal met klantspecifieke rechten"
        }
      }
    },
    {
      "id": "msp.wizard.credentials.az.subscription",
      "area": "credentials",
      "status": "conditional",
      "conditions": [
        "configuration_only"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.wizard.credentials.az.subscription"
      ],
      "source_refs": [
        "apps/cockpit/frontend/src/wizard/StepCredentials.jsx"
      ],
      "related": [
        "msp.wizard.review.review"
      ],
      "locales": {
        "en": {
          "title": "Azure subscription",
          "purpose": "Select the Azure subscription that will own and pay for resources.",
          "when": "When configuring or checking this setting for a client installation.",
          "steps": [
            "Open the client wizard and choose Credentials.",
            "Review azure subscription against the client’s approved requirements. Example: ARM_SUBSCRIPTION_ID.",
            "Use the field’s save/upload action and check its stored confirmation.",
            "Review the effective configuration and remaining prerequisites before making live changes."
          ],
          "permissions": "Operators and admins can configure and run actions. Partners can only inspect their owned clients.",
          "limits": "Saved secret values are write-only. Keep existing customer credentials unless replacement is authorised. Store only the credential requested by the selected target.",
          "example": "ARM_SUBSCRIPTION_ID"
        },
        "nl": {
          "title": "Azure-abonnement",
          "purpose": "Kies het Azure-abonnement dat eigenaar wordt van de middelen en de kosten draagt.",
          "when": "Wanneer je deze instelling voor een klantinstallatie configureert of controleert.",
          "steps": [
            "Open de klantwizard en kies Inloggegevens.",
            "Beoordeel azure-abonnement aan de hand van de goedgekeurde klanteisen. Voorbeeld: ARM_SUBSCRIPTION_ID.",
            "Gebruik de opslag- of uploadactie van het veld en controleer de bevestiging.",
            "Beoordeel de effectieve configuratie en resterende voorwaarden voordat je live wijzigingen uitvoert."
          ],
          "permissions": "Operators en admins kunnen configureren en acties uitvoeren. Partners bekijken alleen hun eigen klanten.",
          "limits": "Opgeslagen geheimen worden niet teruggelezen. Behoud bestaande klantsleutels tenzij vervanging is goedgekeurd. Sla alleen de sleutel op die het gekozen doel vraagt.",
          "example": "ARM_SUBSCRIPTION_ID"
        }
      }
    },
    {
      "id": "msp.wizard.credentials.az.tenant",
      "area": "credentials",
      "status": "conditional",
      "conditions": [
        "configuration_only"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.wizard.credentials.az.tenant"
      ],
      "source_refs": [
        "apps/cockpit/frontend/src/wizard/StepCredentials.jsx"
      ],
      "related": [
        "msp.wizard.review.review"
      ],
      "locales": {
        "en": {
          "title": "Azure tenant",
          "purpose": "Identify the Microsoft Entra directory of the deployment identity.",
          "when": "When configuring or checking this setting for a client installation.",
          "steps": [
            "Open the client wizard and choose Credentials.",
            "Review azure tenant against the client’s approved requirements. Example: ARM_TENANT_ID.",
            "Use the field’s save/upload action and check its stored confirmation.",
            "Review the effective configuration and remaining prerequisites before making live changes."
          ],
          "permissions": "Operators and admins can configure and run actions. Partners can only inspect their owned clients.",
          "limits": "Saved secret values are write-only. Keep existing customer credentials unless replacement is authorised. Store only the credential requested by the selected target.",
          "example": "ARM_TENANT_ID"
        },
        "nl": {
          "title": "Azure-tenant",
          "purpose": "Identificeer de Microsoft Entra-directory van de installatie-identiteit.",
          "when": "Wanneer je deze instelling voor een klantinstallatie configureert of controleert.",
          "steps": [
            "Open de klantwizard en kies Inloggegevens.",
            "Beoordeel azure-tenant aan de hand van de goedgekeurde klanteisen. Voorbeeld: ARM_TENANT_ID.",
            "Gebruik de opslag- of uploadactie van het veld en controleer de bevestiging.",
            "Beoordeel de effectieve configuratie en resterende voorwaarden voordat je live wijzigingen uitvoert."
          ],
          "permissions": "Operators en admins kunnen configureren en acties uitvoeren. Partners bekijken alleen hun eigen klanten.",
          "limits": "Opgeslagen geheimen worden niet teruggelezen. Behoud bestaande klantsleutels tenzij vervanging is goedgekeurd. Sla alleen de sleutel op die het gekozen doel vraagt.",
          "example": "ARM_TENANT_ID"
        }
      }
    },
    {
      "id": "msp.wizard.credentials.az.client",
      "area": "credentials",
      "status": "conditional",
      "conditions": [
        "configuration_only"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.wizard.credentials.az.client"
      ],
      "source_refs": [
        "apps/cockpit/frontend/src/wizard/StepCredentials.jsx"
      ],
      "related": [
        "msp.wizard.review.review"
      ],
      "locales": {
        "en": {
          "title": "Azure client ID",
          "purpose": "Store the application identifier of the deployment service principal.",
          "when": "When configuring or checking this setting for a client installation.",
          "steps": [
            "Open the client wizard and choose Credentials.",
            "Review azure client id against the client’s approved requirements. Example: ARM_CLIENT_ID.",
            "Use the field’s save/upload action and check its stored confirmation.",
            "Review the effective configuration and remaining prerequisites before making live changes."
          ],
          "permissions": "Operators and admins can configure and run actions. Partners can only inspect their owned clients.",
          "limits": "Saved secret values are write-only. Keep existing customer credentials unless replacement is authorised. Store only the credential requested by the selected target.",
          "example": "ARM_CLIENT_ID"
        },
        "nl": {
          "title": "Azure-client-ID",
          "purpose": "Sla de applicatie-identificatie van de installatieserviceprincipal op.",
          "when": "Wanneer je deze instelling voor een klantinstallatie configureert of controleert.",
          "steps": [
            "Open de klantwizard en kies Inloggegevens.",
            "Beoordeel azure-client-id aan de hand van de goedgekeurde klanteisen. Voorbeeld: ARM_CLIENT_ID.",
            "Gebruik de opslag- of uploadactie van het veld en controleer de bevestiging.",
            "Beoordeel de effectieve configuratie en resterende voorwaarden voordat je live wijzigingen uitvoert."
          ],
          "permissions": "Operators en admins kunnen configureren en acties uitvoeren. Partners bekijken alleen hun eigen klanten.",
          "limits": "Opgeslagen geheimen worden niet teruggelezen. Behoud bestaande klantsleutels tenzij vervanging is goedgekeurd. Sla alleen de sleutel op die het gekozen doel vraagt.",
          "example": "ARM_CLIENT_ID"
        }
      }
    },
    {
      "id": "msp.wizard.credentials.az.secret",
      "area": "credentials",
      "status": "conditional",
      "conditions": [
        "configuration_only"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.wizard.credentials.az.secret"
      ],
      "source_refs": [
        "apps/cockpit/frontend/src/wizard/StepCredentials.jsx"
      ],
      "related": [
        "msp.wizard.review.review"
      ],
      "locales": {
        "en": {
          "title": "Azure client secret",
          "purpose": "Store the secret used by the deployment service principal.",
          "when": "When configuring or checking this setting for a client installation.",
          "steps": [
            "Open the client wizard and choose Credentials.",
            "Review azure client secret against the client’s approved requirements. Example: ARM_CLIENT_SECRET.",
            "Use the field’s save/upload action and check its stored confirmation.",
            "Review the effective configuration and remaining prerequisites before making live changes."
          ],
          "permissions": "Operators and admins can configure and run actions. Partners can only inspect their owned clients.",
          "limits": "Saved secret values are write-only. Keep existing customer credentials unless replacement is authorised. Store only the credential requested by the selected target.",
          "example": "ARM_CLIENT_SECRET"
        },
        "nl": {
          "title": "Geheime Azure-appsleutel",
          "purpose": "Sla het geheim van de installatieserviceprincipal op.",
          "when": "Wanneer je deze instelling voor een klantinstallatie configureert of controleert.",
          "steps": [
            "Open de klantwizard en kies Inloggegevens.",
            "Beoordeel geheime azure-appsleutel aan de hand van de goedgekeurde klanteisen. Voorbeeld: ARM_CLIENT_SECRET.",
            "Gebruik de opslag- of uploadactie van het veld en controleer de bevestiging.",
            "Beoordeel de effectieve configuratie en resterende voorwaarden voordat je live wijzigingen uitvoert."
          ],
          "permissions": "Operators en admins kunnen configureren en acties uitvoeren. Partners bekijken alleen hun eigen klanten.",
          "limits": "Opgeslagen geheimen worden niet teruggelezen. Behoud bestaande klantsleutels tenzij vervanging is goedgekeurd. Sla alleen de sleutel op die het gekozen doel vraagt.",
          "example": "ARM_CLIENT_SECRET"
        }
      }
    },
    {
      "id": "msp.wizard.credentials.registry",
      "area": "credentials",
      "status": "conditional",
      "conditions": [
        "configuration_only"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.wizard.credentials.registry"
      ],
      "source_refs": [
        "apps/cockpit/frontend/src/wizard/StepCredentials.jsx"
      ],
      "related": [
        "msp.wizard.review.review"
      ],
      "locales": {
        "en": {
          "title": "Image registry and access",
          "purpose": "Configure image-download access and private-network enrollment requirements.",
          "when": "When configuring or checking this setting for a client installation.",
          "steps": [
            "Open the client wizard and choose Credentials.",
            "Review image registry and access against the client’s approved requirements. Example: GHCR and network credentials.",
            "Use the field’s save/upload action and check its stored confirmation.",
            "Review the effective configuration and remaining prerequisites before making live changes."
          ],
          "permissions": "Operators and admins can configure and run actions. Partners can only inspect their owned clients.",
          "limits": "Saved secret values are write-only. Keep existing customer credentials unless replacement is authorised. Store only the credential requested by the selected target.",
          "example": "GHCR and network credentials"
        },
        "nl": {
          "title": "Imageregister en toegang",
          "purpose": "Configureer toegang tot containerimages en de vereisten voor netwerkregistratie.",
          "when": "Wanneer je deze instelling voor een klantinstallatie configureert of controleert.",
          "steps": [
            "Open de klantwizard en kies Inloggegevens.",
            "Beoordeel imageregister en toegang aan de hand van de goedgekeurde klanteisen. Voorbeeld: GHCR- en netwerksleutels.",
            "Gebruik de opslag- of uploadactie van het veld en controleer de bevestiging.",
            "Beoordeel de effectieve configuratie en resterende voorwaarden voordat je live wijzigingen uitvoert."
          ],
          "permissions": "Operators en admins kunnen configureren en acties uitvoeren. Partners bekijken alleen hun eigen klanten.",
          "limits": "Opgeslagen geheimen worden niet teruggelezen. Behoud bestaande klantsleutels tenzij vervanging is goedgekeurd. Sla alleen de sleutel op die het gekozen doel vraagt.",
          "example": "GHCR- en netwerksleutels"
        }
      }
    },
    {
      "id": "msp.wizard.credentials.ghcr",
      "area": "credentials",
      "status": "conditional",
      "conditions": [
        "configuration_only"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.wizard.credentials.ghcr"
      ],
      "source_refs": [
        "apps/cockpit/frontend/src/wizard/StepCredentials.jsx"
      ],
      "related": [
        "msp.wizard.review.review"
      ],
      "locales": {
        "en": {
          "title": "Container registry credential",
          "purpose": "Provide access to the private release images required by the installation.",
          "when": "When configuring or checking this setting for a client installation.",
          "steps": [
            "Open the client wizard and choose Credentials.",
            "Review container registry credential against the client’s approved requirements. Example: read-only package token.",
            "Use the field’s save/upload action and check its stored confirmation.",
            "Review the effective configuration and remaining prerequisites before making live changes."
          ],
          "permissions": "Operators and admins can configure and run actions. Partners can only inspect their owned clients.",
          "limits": "Saved secret values are write-only. Keep existing customer credentials unless replacement is authorised. Store only the credential requested by the selected target.",
          "example": "read-only package token"
        },
        "nl": {
          "title": "Sleutel voor het containerregister",
          "purpose": "Geef toegang tot de privérelease-images die de installatie nodig heeft.",
          "when": "Wanneer je deze instelling voor een klantinstallatie configureert of controleert.",
          "steps": [
            "Open de klantwizard en kies Inloggegevens.",
            "Beoordeel sleutel voor het containerregister aan de hand van de goedgekeurde klanteisen. Voorbeeld: pakketleestoken.",
            "Gebruik de opslag- of uploadactie van het veld en controleer de bevestiging.",
            "Beoordeel de effectieve configuratie en resterende voorwaarden voordat je live wijzigingen uitvoert."
          ],
          "permissions": "Operators en admins kunnen configureren en acties uitvoeren. Partners bekijken alleen hun eigen klanten.",
          "limits": "Opgeslagen geheimen worden niet teruggelezen. Behoud bestaande klantsleutels tenzij vervanging is goedgekeurd. Sla alleen de sleutel op die het gekozen doel vraagt.",
          "example": "pakketleestoken"
        }
      }
    },
    {
      "id": "msp.wizard.credentials.tailscaleKey",
      "area": "credentials",
      "status": "conditional",
      "conditions": [
        "configuration_only"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.wizard.credentials.tailscaleKey"
      ],
      "source_refs": [
        "apps/cockpit/frontend/src/wizard/StepCredentials.jsx"
      ],
      "related": [
        "msp.wizard.review.review"
      ],
      "locales": {
        "en": {
          "title": "Private-network enrollment key",
          "purpose": "Provide a network enrollment key with the required tag permissions.",
          "when": "When configuring or checking this setting for a client installation.",
          "steps": [
            "Open the client wizard and choose Credentials.",
            "Review private-network enrollment key against the client’s approved requirements. Example: pre-authorised network key.",
            "Use the field’s save/upload action and check its stored confirmation.",
            "Review the effective configuration and remaining prerequisites before making live changes."
          ],
          "permissions": "Operators and admins can configure and run actions. Partners can only inspect their owned clients.",
          "limits": "Saved secret values are write-only. Keep existing customer credentials unless replacement is authorised. Store only the credential requested by the selected target.",
          "example": "pre-authorised network key"
        },
        "nl": {
          "title": "Registratiesleutel voor het privénetwerk",
          "purpose": "Geef een netwerkregistratiesleutel op met de vereiste tagrechten.",
          "when": "Wanneer je deze instelling voor een klantinstallatie configureert of controleert.",
          "steps": [
            "Open de klantwizard en kies Inloggegevens.",
            "Beoordeel registratiesleutel voor het privénetwerk aan de hand van de goedgekeurde klanteisen. Voorbeeld: vooraf goedgekeurde netwerksleutel.",
            "Gebruik de opslag- of uploadactie van het veld en controleer de bevestiging.",
            "Beoordeel de effectieve configuratie en resterende voorwaarden voordat je live wijzigingen uitvoert."
          ],
          "permissions": "Operators en admins kunnen configureren en acties uitvoeren. Partners bekijken alleen hun eigen klanten.",
          "limits": "Opgeslagen geheimen worden niet teruggelezen. Behoud bestaande klantsleutels tenzij vervanging is goedgekeurd. Sla alleen de sleutel op die het gekozen doel vraagt.",
          "example": "vooraf goedgekeurde netwerksleutel"
        }
      }
    },
    {
      "id": "msp.wizard.credentials.sshKey",
      "area": "credentials",
      "status": "conditional",
      "conditions": [
        "configuration_only"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.wizard.credentials.sshKey"
      ],
      "source_refs": [
        "apps/cockpit/frontend/src/wizard/StepCredentials.jsx"
      ],
      "related": [
        "msp.wizard.review.review"
      ],
      "locales": {
        "en": {
          "title": "SSH public key",
          "purpose": "Upload the public key for the supported maintenance access path.",
          "when": "When configuring or checking this setting for a client installation.",
          "steps": [
            "Open the client wizard and choose Credentials.",
            "Review ssh public key against the client’s approved requirements. Example: ssh-ed25519 public key.",
            "Use the field’s save/upload action and check its stored confirmation.",
            "Review the effective configuration and remaining prerequisites before making live changes."
          ],
          "permissions": "Operators and admins can configure and run actions. Partners can only inspect their owned clients.",
          "limits": "Saved secret values are write-only. Keep existing customer credentials unless replacement is authorised. Store only the credential requested by the selected target.",
          "example": "ssh-ed25519 public key"
        },
        "nl": {
          "title": "Publieke SSH-sleutel",
          "purpose": "Upload de publieke sleutel voor het ondersteunde beheerpad.",
          "when": "Wanneer je deze instelling voor een klantinstallatie configureert of controleert.",
          "steps": [
            "Open de klantwizard en kies Inloggegevens.",
            "Beoordeel publieke ssh-sleutel aan de hand van de goedgekeurde klanteisen. Voorbeeld: publieke ssh-ed25519-sleutel.",
            "Gebruik de opslag- of uploadactie van het veld en controleer de bevestiging.",
            "Beoordeel de effectieve configuratie en resterende voorwaarden voordat je live wijzigingen uitvoert."
          ],
          "permissions": "Operators en admins kunnen configureren en acties uitvoeren. Partners bekijken alleen hun eigen klanten.",
          "limits": "Opgeslagen geheimen worden niet teruggelezen. Behoud bestaande klantsleutels tenzij vervanging is goedgekeurd. Sla alleen de sleutel op die het gekozen doel vraagt.",
          "example": "publieke ssh-ed25519-sleutel"
        }
      }
    },
    {
      "id": "msp.wizard.review.review",
      "area": "review",
      "status": "available",
      "conditions": [
        "configuration_only"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.wizard.review.review"
      ],
      "source_refs": [
        "apps/cockpit/frontend/src/wizard/StepReview.jsx"
      ],
      "related": [
        "msp.jobs"
      ],
      "locales": {
        "en": {
          "title": "Deployment review",
          "purpose": "Inspect effective services, resources, image references and control evidence before launch.",
          "when": "Before running this installation action or checking its result.",
          "steps": [
            "Open Review after completing the preceding wizard steps.",
            "Wait for Deployment review to calculate the target, architecture, profiles and bill of materials.",
            "Resolve every blocking error; review warnings, control evidence and reproducibility details.",
            "Continue only when the selected services and source revision match the approved installation."
          ],
          "permissions": "Operators and admins can configure and run actions. Partners can only inspect their owned clients.",
          "limits": "Read every warning and the actual job result. Local checks do not prove cloud permissions, healthy remote services or contractual approval.",
          "example": "review warnings before launch"
        },
        "nl": {
          "title": "Installatiebeoordeling",
          "purpose": "Controleer effectieve diensten, middelen, imagereferenties en bewijspunten voor het starten.",
          "when": "Voordat je deze installatieactie uitvoert of het resultaat controleert.",
          "steps": [
            "Open Review nadat je de voorgaande wizardstappen hebt ingevuld.",
            "Wacht tot Deployment review het doel, de architectuur, profielen en onderdelenlijst heeft berekend.",
            "Los iedere blokkerende fout op; beoordeel waarschuwingen, controlebewijs en reproduceerbaarheidsgegevens.",
            "Ga pas verder als diensten en bronversie overeenkomen met de goedgekeurde installatie."
          ],
          "permissions": "Operators en admins kunnen configureren en acties uitvoeren. Partners bekijken alleen hun eigen klanten.",
          "limits": "Lees iedere waarschuwing en het echte taakresultaat. Lokale controles bewijzen geen cloudrechten, gezonde externe diensten of contractuele goedkeuring.",
          "example": "waarschuwingen beoordelen voor de start"
        }
      }
    },
    {
      "id": "msp.wizard.review.yaml",
      "area": "review",
      "status": "available",
      "conditions": [
        "configuration_only"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.wizard.review.yaml"
      ],
      "source_refs": [
        "apps/cockpit/frontend/src/wizard/StepReview.jsx"
      ],
      "related": [
        "msp.jobs"
      ],
      "locales": {
        "en": {
          "title": "Configuration preview",
          "purpose": "Review the non-secret client configuration that will be saved.",
          "when": "Before running this installation action or checking its result.",
          "steps": [
            "Open client.yaml preview in Review.",
            "Compare the displayed client identity, hosting, services and governance with the intended setup.",
            "Return to the relevant wizard step to correct a value; the preview itself is read-only.",
            "Save the draft and run Render after a configuration change."
          ],
          "permissions": "Operators and admins can configure and run actions. Partners can only inspect their owned clients.",
          "limits": "Read every warning and the actual job result. Local checks do not prove cloud permissions, healthy remote services or contractual approval.",
          "example": "client.yaml preview"
        },
        "nl": {
          "title": "Configuratievoorbeeld",
          "purpose": "Controleer de klantconfiguratie zonder geheimen die wordt opgeslagen.",
          "when": "Voordat je deze installatieactie uitvoert of het resultaat controleert.",
          "steps": [
            "Open client.yaml preview in Review.",
            "Vergelijk klantidentiteit, hosting, diensten en governance met de gewenste inrichting.",
            "Ga terug naar de juiste wizardstap om een waarde te corrigeren; het voorbeeld zelf is alleen-lezen.",
            "Sla het concept op en voer Render uit na een configuratiewijziging."
          ],
          "permissions": "Operators en admins kunnen configureren en acties uitvoeren. Partners bekijken alleen hun eigen klanten.",
          "limits": "Lees iedere waarschuwing en het echte taakresultaat. Lokale controles bewijzen geen cloudrechten, gezonde externe diensten of contractuele goedkeuring.",
          "example": "client.yaml-voorbeeld"
        }
      }
    },
    {
      "id": "msp.wizard.review.checks",
      "area": "review",
      "status": "available",
      "conditions": [
        "configuration_only"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.wizard.review.checks"
      ],
      "source_refs": [
        "apps/cockpit/frontend/src/wizard/StepReview.jsx"
      ],
      "related": [
        "msp.jobs"
      ],
      "locales": {
        "en": {
          "title": "Preflight sequence",
          "purpose": "Render, validate and inspect readiness before planning a deployment.",
          "when": "Before running this installation action or checking its result.",
          "steps": [
            "In Review, run Render and wait for its job to finish successfully.",
            "Run Verify and inspect the output for validation errors.",
            "Run doctor to inspect credentials and readiness.",
            "Fix failed checks in the corresponding step, then rerun the checks before planning."
          ],
          "permissions": "Operators and admins can configure and run actions. Partners can only inspect their owned clients.",
          "limits": "Read every warning and the actual job result. Local checks do not prove cloud permissions, healthy remote services or contractual approval.",
          "example": "Render, Verify, Doctor"
        },
        "nl": {
          "title": "Controlevolgorde voor installatie",
          "purpose": "Genereer bestanden, valideer ze en beoordeel de gereedheid voordat je een installatie plant.",
          "when": "Voordat je deze installatieactie uitvoert of het resultaat controleert.",
          "steps": [
            "Voer in Review eerst Render uit en wacht op een geslaagde taak.",
            "Voer Verify uit en bekijk de uitvoer op validatiefouten.",
            "Gebruik Run doctor voor controle van sleutels en gereedheid.",
            "Herstel fouten in de bijbehorende stap en herhaal de controles voordat je plant."
          ],
          "permissions": "Operators en admins kunnen configureren en acties uitvoeren. Partners bekijken alleen hun eigen klanten.",
          "limits": "Lees iedere waarschuwing en het echte taakresultaat. Lokale controles bewijzen geen cloudrechten, gezonde externe diensten of contractuele goedkeuring.",
          "example": "Genereren, Valideren, Gereedheidscontrole"
        }
      }
    },
    {
      "id": "msp.wizard.review.render",
      "area": "review",
      "status": "available",
      "conditions": [
        "configuration_only"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.wizard.review.render"
      ],
      "source_refs": [
        "apps/cockpit/frontend/src/wizard/StepReview.jsx"
      ],
      "related": [
        "msp.jobs"
      ],
      "locales": {
        "en": {
          "title": "Render configuration",
          "purpose": "Generate installation artifacts from the saved client configuration.",
          "when": "Before running this installation action or checking its result.",
          "steps": [
            "Choose Render in Review; the action first saves the current draft.",
            "Wait for the Render output job to finish.",
            "Check that the result is successful and the generated environment and infrastructure variables reflect the draft.",
            "Run Verify next; render success alone does not deploy services."
          ],
          "permissions": "Operators and admins can configure and run actions. Partners can only inspect their owned clients.",
          "limits": "Read every warning and the actual job result. Local checks do not prove cloud permissions, healthy remote services or contractual approval.",
          "example": "updated environment and tfvars"
        },
        "nl": {
          "title": "Configuratie genereren",
          "purpose": "Genereer installatiebestanden uit de opgeslagen klantconfiguratie.",
          "when": "Voordat je deze installatieactie uitvoert of het resultaat controleert.",
          "steps": [
            "Kies Render in Review; de actie slaat eerst het huidige concept op.",
            "Wacht tot de taak onder Render output is afgerond.",
            "Controleer dat de taak geslaagd is en gegenereerde omgevings- en infrastructuurvariabelen bij het concept passen.",
            "Voer daarna Verify uit; een geslaagde generatie rolt geen diensten uit."
          ],
          "permissions": "Operators en admins kunnen configureren en acties uitvoeren. Partners bekijken alleen hun eigen klanten.",
          "limits": "Lees iedere waarschuwing en het echte taakresultaat. Lokale controles bewijzen geen cloudrechten, gezonde externe diensten of contractuele goedkeuring.",
          "example": "bijgewerkte omgeving en tfvars"
        }
      }
    },
    {
      "id": "msp.wizard.review.verify",
      "area": "review",
      "status": "available",
      "conditions": [
        "configuration_only"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.wizard.review.verify"
      ],
      "source_refs": [
        "apps/cockpit/frontend/src/wizard/StepReview.jsx"
      ],
      "related": [
        "msp.jobs"
      ],
      "locales": {
        "en": {
          "title": "Verify configuration",
          "purpose": "Validate the generated files against the selected schema and deployment root.",
          "when": "Before running this installation action or checking its result.",
          "steps": [
            "Run Render after your latest configuration change.",
            "Choose Verify; the action saves the draft before queuing its job.",
            "Read Verify output and correct missing or inconsistent required values.",
            "Continue to readiness checks and planning only after a successful result."
          ],
          "permissions": "Operators and admins can configure and run actions. Partners can only inspect their owned clients.",
          "limits": "Read every warning and the actual job result. Local checks do not prove cloud permissions, healthy remote services or contractual approval.",
          "example": "resolve missing required fields"
        },
        "nl": {
          "title": "Configuratie valideren",
          "purpose": "Valideer de gegenereerde bestanden tegen schema en gekozen installatievariant.",
          "when": "Voordat je deze installatieactie uitvoert of het resultaat controleert.",
          "steps": [
            "Voer Render uit na de laatste configuratiewijziging.",
            "Kies Verify; de actie slaat het concept op voordat de taak wordt gestart.",
            "Lees Verify output en corrigeer ontbrekende of tegenstrijdige verplichte waarden.",
            "Ga pas na een geslaagde controle verder met gereedheid en planning."
          ],
          "permissions": "Operators en admins kunnen configureren en acties uitvoeren. Partners bekijken alleen hun eigen klanten.",
          "limits": "Lees iedere waarschuwing en het echte taakresultaat. Lokale controles bewijzen geen cloudrechten, gezonde externe diensten of contractuele goedkeuring.",
          "example": "ontbrekende verplichte velden aanvullen"
        }
      }
    },
    {
      "id": "msp.wizard.review.doctor",
      "area": "review",
      "status": "available",
      "conditions": [
        "configuration_only"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.wizard.review.doctor"
      ],
      "source_refs": [
        "apps/cockpit/frontend/src/wizard/StepReview.jsx"
      ],
      "related": [
        "msp.jobs"
      ],
      "locales": {
        "en": {
          "title": "Readiness check",
          "purpose": "Check local readiness without creating cloud resources.",
          "when": "Before running this installation action or checking its result.",
          "steps": [
            "Ensure the draft and generated configuration are current.",
            "Choose Run doctor in Review.",
            "Read the readiness report, including missing credentials or prerequisites.",
            "Resolve failures and rerun Doctor; a successful report still requires real deployment and health verification."
          ],
          "permissions": "Operators and admins can configure and run actions. Partners can only inspect their owned clients.",
          "limits": "Read every warning and the actual job result. Local checks do not prove cloud permissions, healthy remote services or contractual approval.",
          "example": "credential files and current render"
        },
        "nl": {
          "title": "Gereedheidscontrole",
          "purpose": "Controleer lokale gereedheid zonder cloudmiddelen aan te maken.",
          "when": "Voordat je deze installatieactie uitvoert of het resultaat controleert.",
          "steps": [
            "Zorg dat concept en gegenereerde configuratie actueel zijn.",
            "Kies Run doctor in Review.",
            "Lees het gereedheidsrapport, inclusief ontbrekende sleutels of voorwaarden.",
            "Herstel fouten en herhaal Doctor; na een geslaagd rapport zijn echte uitrol en gezondheidscontrole nog nodig."
          ],
          "permissions": "Operators en admins kunnen configureren en acties uitvoeren. Partners bekijken alleen hun eigen klanten.",
          "limits": "Lees iedere waarschuwing en het echte taakresultaat. Lokale controles bewijzen geen cloudrechten, gezonde externe diensten of contractuele goedkeuring.",
          "example": "sleutelbestanden en actuele generatie"
        }
      }
    },
    {
      "id": "msp.wizard.review.device",
      "area": "review",
      "status": "available",
      "conditions": [
        "configuration_only"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.wizard.review.device"
      ],
      "source_refs": [
        "apps/cockpit/frontend/src/wizard/StepReview.jsx"
      ],
      "related": [
        "msp.jobs"
      ],
      "locales": {
        "en": {
          "title": "One-time device installer",
          "purpose": "Generate a private installer link for the selected client and release.",
          "when": "Before running this installation action or checking its result.",
          "steps": [
            "Select a device or Compose target and resolve blocking Deployment review errors.",
            "Choose Generate device installer; the draft is saved before the link is created.",
            "Check the source revision and expiry, then copy the command only to the authorised target operator.",
            "Run it on the intended supported device with the required network, Python, Docker/Compose and image access.",
            "Verify installation output and service health. Native engine installation needs separate sign-in and service activation."
          ],
          "permissions": "Operators and admins can configure and run actions. Partners can only inspect their owned clients.",
          "limits": "Read every warning and the actual job result. Local checks do not prove cloud permissions, healthy remote services or contractual approval. Single-use installer links expire after one hour. Docker, Compose, Python and image access must already meet the installer prerequisites. Native activation is a separate step.",
          "example": "one-time link, valid one hour"
        },
        "nl": {
          "title": "Eenmalige apparaatinstaller",
          "purpose": "Genereer een privéinstallerlink voor de gekozen klant en release.",
          "when": "Voordat je deze installatieactie uitvoert of het resultaat controleert.",
          "steps": [
            "Selecteer een apparaat- of Compose-doel en los blokkerende fouten in Deployment review op.",
            "Kies Generate device installer; het concept wordt opgeslagen voordat de link wordt gemaakt.",
            "Controleer bronversie en vervaltijd en geef het commando alleen aan de bevoegde apparaatbeheerder.",
            "Voer het uit op het bedoelde ondersteunde apparaat met de vereiste netwerk-, Python-, Docker/Compose- en imagetoegang.",
            "Controleer installatie-uitvoer en dienstgezondheid. Een native engine-installatie vereist daarna apart inloggen en activeren."
          ],
          "permissions": "Operators en admins kunnen configureren en acties uitvoeren. Partners bekijken alleen hun eigen klanten.",
          "limits": "Lees iedere waarschuwing en het echte taakresultaat. Lokale controles bewijzen geen cloudrechten, gezonde externe diensten of contractuele goedkeuring. Eenmalige installerlinks verlopen na één uur. Docker, Compose, Python en imagetoegang moeten al aan de voorwaarden voldoen. Native activering is een aparte stap.",
          "example": "eenmalige link, één uur geldig"
        }
      }
    },
    {
      "id": "msp.wizard.review.plan",
      "area": "review",
      "status": "available",
      "conditions": [
        "configuration_only"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.wizard.review.plan"
      ],
      "source_refs": [
        "apps/cockpit/frontend/src/wizard/StepReview.jsx"
      ],
      "related": [
        "msp.jobs"
      ],
      "locales": {
        "en": {
          "title": "Plan cloud deployment",
          "purpose": "Produce and inspect a saved Terraform plan before making changes.",
          "when": "Before running this installation action or checking its result.",
          "steps": [
            "Select the intended cloud target, save the draft, then run Render and Verify successfully.",
            "In Review, resolve blocking errors and choose Plan deploy.",
            "Wait for Deploy plan output to finish successfully; inspect every proposed resource change and possible cost.",
            "Keep the reviewed configuration unchanged. The successful saved plan is valid for one hour and may be applied once.",
            "If the plan expires or configuration changes, generate and review a fresh plan."
          ],
          "permissions": "Operators and admins can configure and run actions. Partners can only inspect their owned clients.",
          "limits": "Read every warning and the actual job result. Local checks do not prove cloud permissions, healthy remote services or contractual approval. Planning can contact the cloud provider. The saved plan expires after one hour and can be applied once.",
          "example": "one reviewed saved plan"
        },
        "nl": {
          "title": "Cloudinstallatie plannen",
          "purpose": "Maak en beoordeel een opgeslagen Terraformplan voordat je wijzigingen uitvoert.",
          "when": "Voordat je deze installatieactie uitvoert of het resultaat controleert.",
          "steps": [
            "Selecteer het bedoelde clouddoel, sla het concept op en voer Render en Verify succesvol uit.",
            "Los in Review blokkerende fouten op en kies Plan deploy.",
            "Wacht op een geslaagde taak onder Deploy plan output; beoordeel elke voorgestelde wijziging en mogelijke kosten.",
            "Laat de beoordeelde configuratie ongewijzigd. Het opgeslagen plan is één uur geldig en kan eenmaal worden uitgevoerd.",
            "Maak en beoordeel een nieuw plan als het verloopt of de configuratie verandert."
          ],
          "permissions": "Operators en admins kunnen configureren en acties uitvoeren. Partners bekijken alleen hun eigen klanten.",
          "limits": "Lees iedere waarschuwing en het echte taakresultaat. Lokale controles bewijzen geen cloudrechten, gezonde externe diensten of contractuele goedkeuring. Plannen kan contact maken met de cloudprovider. Het opgeslagen plan verloopt na één uur en kan eenmaal worden uitgevoerd.",
          "example": "één beoordeeld opgeslagen plan"
        }
      }
    },
    {
      "id": "msp.wizard.review.apply",
      "area": "review",
      "status": "available",
      "conditions": [
        "configuration_only"
      ],
      "anchors": [
        "/cockpit/help?feature=msp.wizard.review.apply"
      ],
      "source_refs": [
        "apps/cockpit/frontend/src/wizard/StepReview.jsx"
      ],
      "related": [
        "msp.jobs"
      ],
      "locales": {
        "en": {
          "title": "Apply cloud deployment",
          "purpose": "Apply the reviewed saved plan after confirming the client name.",
          "when": "Before running this installation action or checking its result.",
          "steps": [
            "Finish and review a successful Plan deploy for the current configuration.",
            "Check the target account, resource changes and authorisation for any chargeable infrastructure.",
            "Type the exact client name displayed in the confirmation box.",
            "Choose Apply deploy and inspect Deploy apply output until the job finishes.",
            "Verify the actual installation and enabled service health after success; a completed infrastructure job is not a full application acceptance test."
          ],
          "permissions": "Operators and admins can configure and run actions. Partners can only inspect their owned clients.",
          "limits": "Read every warning and the actual job result. Local checks do not prove cloud permissions, healthy remote services or contractual approval. This changes real infrastructure and can start paid cloud resources. Review the plan and type the exact client name to confirm.",
          "example": "type acme-demo to confirm"
        },
        "nl": {
          "title": "Cloudinstallatie uitvoeren",
          "purpose": "Voer het beoordeelde opgeslagen plan uit na bevestiging van de klantcode.",
          "when": "Voordat je deze installatieactie uitvoert of het resultaat controleert.",
          "steps": [
            "Maak en beoordeel een geslaagd Plan deploy voor de huidige configuratie.",
            "Controleer doelaccount, wijzigingen en toestemming voor eventuele betaalde infrastructuur.",
            "Typ de exacte klantcode die in het bevestigingsvak staat.",
            "Kies Apply deploy en volg Deploy apply output tot de taak is afgerond.",
            "Controleer daarna de echte installatie en ingeschakelde diensten; een afgeronde infrastructuurtaak is geen volledige applicatieacceptatietest."
          ],
          "permissions": "Operators en admins kunnen configureren en acties uitvoeren. Partners bekijken alleen hun eigen klanten.",
          "limits": "Lees iedere waarschuwing en het echte taakresultaat. Lokale controles bewijzen geen cloudrechten, gezonde externe diensten of contractuele goedkeuring. Dit wijzigt echte infrastructuur en kan betaalde cloudmiddelen starten. Beoordeel het plan en typ de exacte klantcode ter bevestiging.",
          "example": "typ acme-demo ter bevestiging"
        }
      }
    }
  ]
};
