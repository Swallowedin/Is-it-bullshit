# config.py
import os
from dataclasses import dataclass
from typing import List, Dict

# Configuration des modèles GPT
GPT_MODELS = {
    "gpt-4o-mini": {
        "name": "GPT-4o-mini",
        "model": "gpt-4o-mini",
        "max_tokens": 150000,
        "temperature": 0.7
    }
}

@dataclass
class ScoringCriteria:
    name: str
    weight: float
    subcriteria: List[Dict[str, float]]

# Critères de scoring
SCORING_CRITERIA = [
    ScoringCriteria(
        name="Conformité réglementaire",
        weight=0.3,
        subcriteria=[
            {"CSRD": 0.4},
            {"Déforestation": 0.3},
            {"Autres réglementations": 0.3}
        ]
    ),
    ScoringCriteria(
        name="Qualité des données",
        weight=0.25,
        subcriteria=[
            {"Précision": 0.4},
            {"Traçabilité": 0.3},
            {"Sources": 0.3}
        ]
    ),
    ScoringCriteria(
        name="Engagement et actions",
        weight=0.25,
        subcriteria=[
            {"Objectifs": 0.4},
            {"Plans d'action": 0.3},
            {"Suivi": 0.3}
        ]
    ),
    ScoringCriteria(
        name="Transparence",
        weight=0.2,
        subcriteria=[
            {"Risques identifiés": 0.4},
            {"Points d'amélioration": 0.3},
            {"Communication": 0.3}
        ]
    )
]

# Configuration des chemins
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGULATORY_DOCS_PATH = os.path.join(BASE_DIR, 'data', 'regulatory')
REPORTS_PATH = os.path.join(BASE_DIR, 'data', 'reports')

# Configuration de la base de données
DB_PATH = os.path.join(BASE_DIR, 'data', 'reports_analysis.db')

# Configuration des API
API_CONFIG = {
    "pappers": {
        "base_url": "https://api.pappers.fr/v2",
        "timeout": 30,
        "retry_attempts": 3
    }
}

# Configuration de l'interface
UI_CONFIG = {
    "page_title": "Is it Bullshit? - Analyseur CSRD/DPEF",
    "page_icon": "🔍",
    "layout": "wide",
    "theme": {
        "primaryColor": "#FF4B4B",
        "backgroundColor": "#FFFFFF",
        "secondaryBackgroundColor": "#F0F2F6",
        "textColor": "#262730",
        "font": "sans serif"
    }
}
