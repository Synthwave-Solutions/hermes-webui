"""Audited app identities. Deployment URLs belong in SP_APP_LINKS, never here."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AppSpec:
    id: str
    name: str
    description_nl: str
    description_en: str
    module: str = 'design_studio'
    category: str = 'creative'
    access: str = 'member'


_ROWS = (
    AppSpec('opendesign', 'OpenDesign',
            'Ontwerp en bewerk visuele projecten en merkuitingen.',
            'Design and edit visual projects and branded materials.'),
    AppSpec('opendesign_classic', 'OpenDesign Classic',
            'Open de klassieke ontwerpomgeving voor bestaande projecten.',
            'Open the classic design environment for existing projects.'),
    AppSpec('craft_studio', 'Craft Studio',
            'Kies een creatieve editor voor beeld, video, ontwerp, documenten of audio.',
            'Choose a creative editor for images, video, design, documents or audio.'),
    AppSpec('photocraft', 'PhotoCraft', 'Bewerk foto’s en maak beeldcomposities.',
            'Edit photos and create image compositions.'),
    AppSpec('filmcraft', 'FilmCraft', 'Monteer video’s en werk aan je tijdlijn.',
            'Edit videos and work on your timeline.'),
    AppSpec('effectcraft', 'EffectCraft', 'Maak visuele effecten en bewegende composities.',
            'Create visual effects and animated compositions.'),
    AppSpec('vectorcraft', 'VectorCraft', 'Teken en bewerk vectorillustraties.',
            'Draw and edit vector illustrations.'),
    AppSpec('lightcraft', 'LightCraft', 'Ontwikkel en corrigeer foto’s.',
            'Develop and correct photos.'),
    AppSpec('designcraft', 'DesignCraft', 'Maak ontwerpen en paginalay-outs.',
            'Create designs and page layouts.'),
    AppSpec('pdfcraft', 'PDFCraft', 'Open en bewerk pdf-documenten.',
            'Open and edit PDF documents.'),
    AppSpec('soundcraft', 'SoundCraft', 'Neem audio op en bewerk geluid.',
            'Record audio and edit sound.'),
    AppSpec('hyperframes', 'HyperFrames', 'Maak en bekijk animaties en videocomposities.',
            'Create and preview animations and video compositions.'),
    AppSpec('vision_studio', 'Vision Studio', 'Open de studio voor visuele projecten.',
            'Open the studio for visual projects.'),
    AppSpec('n8n', 'n8n', 'Bouw en beheer geautomatiseerde workflows.',
            'Build and manage automated workflows.', 'workflows', 'automation', 'platform'),
    AppSpec('omniroute', 'OmniRoute', 'Beheer modelroutes en verbindingen met AI-aanbieders.',
            'Manage model routing and AI provider connections.', 'workspace', 'platform', 'platform'),
    AppSpec('nango', 'Nango', 'Beheer integraties en verbindingen met externe diensten.',
            'Manage integrations and connections to external services.', 'workspace', 'platform', 'platform'),
    AppSpec('docuseal', 'DocuSeal', 'Bereid documenten voor en volg digitale ondertekening.',
            'Prepare documents and follow digital signing.', 'e_signing', 'productivity'),
    AppSpec('pareltje', 'Pareltje', 'Open het beheerpaneel van Pareltje.',
            'Open the Pareltje management dashboard.', 'workspace', 'platform', 'platform'),
    AppSpec('slibdetect', 'SlibDetect', 'Open het beheerpaneel van SlibDetect.',
            'Open the SlibDetect management dashboard.', 'workspace', 'platform', 'platform'),
    AppSpec('cockpit', 'MSP Cockpit', 'Beheer installaties, organisaties en uitrol.',
            'Manage installations, organisations and deployments.', 'workspace', 'platform', 'platform'),
    AppSpec('silverbullet', 'SilverBullet', 'Schrijf en organiseer kennisnotities.',
            'Write and organise knowledge notes.', 'notebook', 'productivity', 'platform'),
    AppSpec('pixel_office', 'Pixel Office', 'Bekijk de virtuele kantooromgeving.',
            'View the virtual office environment.', 'workspace', 'platform', 'platform'),
    AppSpec('mnemosyne', 'Mnemosyne', 'Beheer het geheugen van de AI-omgeving.',
            'Manage memory for the AI environment.', 'workspace', 'platform', 'platform'),
    AppSpec('strategy_gantt', 'Strategy Gantt', 'Bekijk en beheer de strategische planning.',
            'View and manage strategic planning.', 'workspace', 'platform', 'platform'),
    AppSpec('openwebui', 'Open WebUI', 'Open de aanvullende AI-chatomgeving.',
            'Open the additional AI chat environment.', 'workspace', 'platform', 'platform'),
)

REGISTRY = {app.id: app for app in _ROWS}
# A configured named app replaces only its matching legacy launcher entry.
LEGACY_REPLACEMENTS = {'design_studio': ('opendesign',), 'workflows': ('n8n',),
                       'e_signing': ('docuseal',)}
