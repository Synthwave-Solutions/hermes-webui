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
    AppSpec('craft_studio', 'Craft Studio',
            'Kies een creatieve editor voor beeld, video, ontwerp, documenten of audio.',
            'Choose a creative editor for images, video, design, documents or audio.', category='craft'),
    AppSpec('photocraft', 'PhotoCraft', 'Bewerk foto’s en maak beeldcomposities.',
            'Edit photos and create image compositions.', category='craft'),
    AppSpec('filmcraft', 'FilmCraft', 'Monteer video’s en werk aan je tijdlijn.',
            'Edit videos and work on your timeline.', category='craft'),
    AppSpec('effectcraft', 'EffectCraft', 'Maak visuele effecten en bewegende composities.',
            'Create visual effects and animated compositions.', category='craft'),
    AppSpec('vectorcraft', 'VectorCraft', 'Teken en bewerk vectorillustraties.',
            'Draw and edit vector illustrations.', category='craft'),
    AppSpec('lightcraft', 'LightCraft', 'Ontwikkel en corrigeer foto’s.',
            'Develop and correct photos.', category='craft'),
    AppSpec('designcraft', 'DesignCraft', 'Maak ontwerpen en paginalay-outs.',
            'Create designs and page layouts.', category='craft'),
    AppSpec('pdfcraft', 'PDFCraft', 'Open en bewerk pdf-documenten.',
            'Open and edit PDF documents.', category='craft'),
    AppSpec('soundcraft', 'SoundCraft', 'Neem audio op en bewerk geluid.',
            'Record audio and edit sound.', category='craft'),
    AppSpec('hyperframes', 'HyperFrames', 'Maak en bekijk animaties en videocomposities.',
            'Create and preview animations and video compositions.'),
    AppSpec('n8n', 'n8n', 'Bouw en beheer geautomatiseerde workflows.',
            'Build and manage automated workflows.', 'workflows', 'automation', 'platform'),
    AppSpec('omniroute', 'OmniRoute', 'Beheer modelroutes en verbindingen met AI-aanbieders.',
            'Manage model routing and AI provider connections.', 'workspace', 'platform', 'platform'),
    AppSpec('nango', 'Nango', 'Beheer integraties en verbindingen met externe diensten.',
            'Manage integrations and connections to external services.', 'workspace', 'platform', 'platform'),
    AppSpec('docuseal', 'DocuSeal', 'Bereid documenten voor en volg digitale ondertekening.',
            'Prepare documents and follow digital signing.', 'e_signing', 'productivity'),
    AppSpec('cockpit', 'MSP Cockpit', 'Beheer installaties, organisaties en uitrol.',
            'Manage installations, organisations and deployments.', 'workspace', 'platform', 'platform'),
    AppSpec('openwebui', 'Open WebUI', 'Open de aanvullende AI-chatomgeving.',
            'Open the additional AI chat environment.', 'workspace', 'platform', 'platform'),
    AppSpec('ragflow', 'RAGFlow', 'Beheer kennisbanken, verwerk documenten en test antwoorden met bronverwijzingen.',
            'Manage knowledge bases, process documents and test answers with source references.', 'knowledge_base', 'productivity', 'platform'),
    AppSpec('langfuse', 'Langfuse', 'Bekijk AI-traces, gebruik, kosten en evaluaties van gekoppelde toepassingen.',
            'Inspect AI traces, usage, costs and evaluations from connected applications.', 'workspace', 'platform', 'platform'),
    AppSpec('hermesoffice', 'HermesOffice', 'Desktopapp voor documenten, spreadsheets, presentaties, pdf en Markdown.',
            'Desktop app for documents, spreadsheets, presentations, PDF and Markdown.', 'office_apps', 'productivity'),
)

REGISTRY = {app.id: app for app in _ROWS}
# A configured named app replaces only its matching legacy launcher entry.
LEGACY_REPLACEMENTS = {'design_studio': ('opendesign',), 'workflows': ('n8n',),
                       'e_signing': ('docuseal',)}
