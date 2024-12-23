import streamlit as st
import openai

class ReportAnalyzer:
    def __init__(self, regulatory_db_path="regulatory_docs/"):
        try:
            if "OPENAI_API_KEY" not in st.secrets:
                st.error("Clé API OpenAI manquante dans les secrets Streamlit")
                raise ValueError("Clé API OpenAI manquante")
            openai.api_key = st.secrets["OPENAI_API_KEY"]
            self.regulatory_db_path = regulatory_db_path
            self.is_demo = False
        except Exception as e:
            raise Exception(f"Erreur d'initialisation ReportAnalyzer: {str(e)}")

    # [Garder toutes les autres méthodes identiques]
    
    def _get_demo_analysis(self):
        """Retourne une analyse de démonstration en cas d'erreur."""
        return {
            "analysis": "Ceci est une analyse exemple en mode démonstration.",
            "scores": {
                "global": 75.5,
                "detailed": {
                    "Conformité réglementaire": 80,
                    "Qualité des données": 70,
                    "Engagement et actions": 75,
                    "Transparence": 77
                }
            },
            "recommendations": [
                "Améliorer la traçabilité des données environnementales",
                "Renforcer les objectifs quantitatifs",
                "Détailler davantage les plans d'action"
            ],
            "sources": [
                "Document de référence",
                "Rapport annuel",
                "Données internes"
            ]
        }
