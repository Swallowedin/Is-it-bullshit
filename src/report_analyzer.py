import streamlit as st
import openai
from typing import Dict, Any
import json

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

    def analyze_report(self, text: str, company_info: Dict[str, Any], report_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyse un rapport CSRD/DPEF en utilisant GPT-4o-mini.
        
        Args:
            text (str): Le texte extrait du rapport
            company_info (dict): Informations sur l'entreprise
            report_config (dict): Configuration de l'analyse
            
        Returns:
            dict: Résultats de l'analyse
        """
        try:
            # Si mode démo ou erreur, retourner une analyse de démonstration
            if self.is_demo:
                return self._get_demo_analysis()

            # Préparer le prompt pour l'analyse
            prompt = self._prepare_analysis_prompt(text, company_info, report_config)

            # Appeler l'API OpenAI
            response = openai.ChatCompletion.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": """Tu es un expert en analyse de rapports CSRD et DPEF.
                    Tu dois analyser le rapport fourni selon les critères suivants:
                    - Conformité réglementaire
                    - Qualité des données
                    - Engagement et actions
                    - Transparence"""},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=150000
            )

            # Analyser la réponse
            analysis = self._parse_gpt_response(response.choices[0].message.content)

            # Calculer les scores
            scores = self._calculate_scores(analysis)

            # Structurer les résultats
            results = {
                "analysis": analysis.get("analysis", "Analyse non disponible"),
                "scores": {
                    "global": scores.get("global", 0),
                    "detailed": scores.get("detailed", {})
                },
                "recommendations": analysis.get("recommendations", []),
                "sources": analysis.get("sources", [])
            }

            return results

        except Exception as e:
            st.error(f"Erreur lors de l'analyse du rapport: {str(e)}")
            return self._get_demo_analysis()

    def _prepare_analysis_prompt(self, text: str, company_info: Dict[str, Any], report_config: Dict[str, Any]) -> str:
        """Prépare le prompt pour l'analyse GPT."""
        return f"""Analyse le rapport suivant pour l'entreprise {company_info['name']}.
        
        Contexte:
        - Secteur: {company_info['sector']}
        - Taille: {company_info['size']}
        - Type de rapport: {report_config['type']}
        
        Texte du rapport:
        {text[:8000]}...  # Limitation de la taille pour GPT-4
        
        Format de réponse souhaité (JSON):
        {{
            "analysis": "Analyse générale",
            "recommendations": ["rec1", "rec2", ...],
            "sources": ["source1", "source2", ...],
            "scores": {{
                "conformite": X,
                "qualite_donnees": X,
                "engagement": X,
                "transparence": X
            }}
        }}
        """

    def _parse_gpt_response(self, response: str) -> Dict[str, Any]:
        """Parse la réponse de GPT en dictionnaire structuré."""
        try:
            # Essayer de parser directement si c'est du JSON valide
            return json.loads(response)
        except json.JSONDecodeError:
            # Si ce n'est pas du JSON valide, extraire les informations pertinentes
            analysis = {
                "analysis": "Analyse non disponible",
                "recommendations": [],
                "sources": [],
                "scores": {
                    "conformite": 0,
                    "qualite_donnees": 0,
                    "engagement": 0,
                    "transparence": 0
                }
            }
            
            # Parsing basique du texte
            lines = response.split('\n')
            current_section = None
            
            for line in lines:
                line = line.strip()
                if "Analyse" in line:
                    current_section = "analysis"
                    analysis["analysis"] = line.split(":", 1)[1].strip() if ":" in line else line
                elif "Recommandation" in line:
                    current_section = "recommendations"
                    if ":" in line:
                        rec = line.split(":", 1)[1].strip()
                        if rec:
                            analysis["recommendations"].append(rec)
                elif "Source" in line:
                    current_section = "sources"
                    if ":" in line:
                        src = line.split(":", 1)[1].strip()
                        if src:
                            analysis["sources"].append(src)
                elif current_section == "recommendations" and line.startswith("-"):
                    analysis["recommendations"].append(line[1:].strip())
                elif current_section == "sources" and line.startswith("-"):
                    analysis["sources"].append(line[1:].strip())
            
            return analysis

    def _calculate_scores(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Calcule les scores à partir de l'analyse."""
        try:
            # Récupérer les scores bruts
            raw_scores = analysis.get("scores", {})
            
            # Calculer les scores détaillés normalisés
            detailed_scores = {
                "Conformité réglementaire": float(raw_scores.get("conformite", 0)),
                "Qualité des données": float(raw_scores.get("qualite_donnees", 0)),
                "Engagement et actions": float(raw_scores.get("engagement", 0)),
                "Transparence": float(raw_scores.get("transparence", 0))
            }
            
            # Calculer le score global (moyenne pondérée)
            weights = {
                "Conformité réglementaire": 0.3,
                "Qualité des données": 0.25,
                "Engagement et actions": 0.25,
                "Transparence": 0.2
            }
            
            global_score = sum(score * weights[criteria] 
                             for criteria, score in detailed_scores.items())
            
            return {
                "global": round(global_score, 1),
                "detailed": {k: round(v, 1) for k, v in detailed_scores.items()}
            }
        except Exception as e:
            st.warning(f"Erreur dans le calcul des scores: {str(e)}")
            return {
                "global": 0.0,
                "detailed": {
                    "Conformité réglementaire": 0.0,
                    "Qualité des données": 0.0,
                    "Engagement et actions": 0.0,
                    "Transparence": 0.0
                }
            }

    def _get_demo_analysis(self) -> Dict[str, Any]:
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
