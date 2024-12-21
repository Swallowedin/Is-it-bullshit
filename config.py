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

# db_manager.py
import sqlite3
from datetime import datetime
import json

class DatabaseManager:
    def __init__(self, db_path="reports_analysis.db"):
        self.db_path = db_path
        self.init_db()
    
    def init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Table des entreprises
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS companies (
                    siren TEXT PRIMARY KEY,
                    name TEXT,
                    sector TEXT,
                    size TEXT,
                    pappers_data TEXT
                )
            ''')
            
            # Table des analyses
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS analyses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    company_siren TEXT,
                    report_date TEXT,
                    report_type TEXT,
                    score_global FLOAT,
                    scores_detail TEXT,
                    recommendations TEXT,
                    sources_cited TEXT,
                    FOREIGN KEY (company_siren) REFERENCES companies (siren)
                )
            ''')

# pappers_api.py
import requests
import os

class PappersAPI:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://api.pappers.fr/v2"
    
    def get_company_info(self, siren):
        endpoint = f"{self.base_url}/entreprise"
        params = {
            "api_token": self.api_key,
            "siren": siren,
        }
        response = requests.get(endpoint, params=params)
        return response.json() if response.status_code == 200 else None

# report_analyzer.py
class ReportAnalyzer:
    def __init__(self, gpt_api_key, regulatory_db_path="regulatory_docs/"):
        self.gpt_api_key = gpt_api_key
        self.regulatory_db_path = regulatory_db_path
        
    def analyze_report(self, text, company_info, regulatory_context):
        # Construction du prompt enrichi
        prompt = self._build_enhanced_prompt(company_info, regulatory_context)
        
        # Analyse GPT-4
        analysis = self._analyze_with_gpt4(text, prompt)
        
        # Extraction des sources citées
        sources = self._extract_sources(text)
        
        # Calcul du score
        scores = self._calculate_scores(analysis)
        
        # Génération des recommandations
        recommendations = self._generate_recommendations(analysis, scores)
        
        return {
            "analysis": analysis,
            "scores": scores,
            "recommendations": recommendations,
            "sources": sources
        }
    
    def _build_enhanced_prompt(self, company_info, regulatory_context):
        return f"""Analyse ce rapport CSRD/DPEF pour {company_info['name']} en tenant compte:
        1. Du secteur d'activité: {company_info['sector']}
        2. Des réglementations applicables: {regulatory_context}
        3. Des critères spécifiques de notation
        
        Évalue particulièrement:
        - La conformité réglementaire
        - La qualité et la traçabilité des données
        - La crédibilité des engagements
        - La transparence globale
        
        Identifie:
        - Les sources citées et leur fiabilité
        - Les points d'amélioration concrets
        - Les bonnes pratiques à souligner"""

# dashboard_components.py
import plotly.express as px
import plotly.graph_objects as go

class Dashboard:
    def __init__(self):
        self.figures = {}
    
    def create_score_radar(self, scores):
        categories = list(scores.keys())
        values = list(scores.values())
        
        fig = go.Figure(data=go.Scatterpolar(
            r=values,
            theta=categories,
            fill='toself'
        ))
        
        fig.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, 100]
                )),
            showlegend=False
        )
        
        return fig
    
    def create_historical_comparison(self, historical_scores):
        fig = px.line(
            historical_scores,
            x='date',
            y='score',
            title='Évolution du score global'
        )
        return fig

    def create_sector_comparison(self, company_score, sector_scores):
        fig = go.Figure(data=[
            go.Bar(name='Entreprise', x=['Score'], y=[company_score]),
            go.Bar(name='Moyenne secteur', x=['Score'], y=[sector_scores['mean']]),
            go.Bar(name='Meilleur score secteur', x=['Score'], y=[sector_scores['max']])
        ])
        return fig
