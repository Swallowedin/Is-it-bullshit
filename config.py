import os
from dataclasses import dataclass
from typing import List, Dict

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
