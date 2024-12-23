import streamlit as st
from openai import OpenAI
from typing import Dict, Any
import json

class ReportAnalyzer:
    def __init__(self, regulatory_db_path="regulatory_docs/"):
        try:
            if "OPENAI_API_KEY" not in st.secrets:
                st.error("Clé API manquante dans les secrets Streamlit")
                raise ValueError("Clé API manquante")
                
            self.client = OpenAI(
                api_key=st.secrets["OPENAI_API_KEY"]
            )
            
            self.model = "gpt-4o-mini"
            self.max_output_tokens = 16000
            self.max_input_tokens = 128000
            self.temperature = 0.7
            
            self.regulatory_db_path = regulatory_db_path
            self.is_demo = False
            
        except Exception as e:
            raise Exception(f"Erreur d'initialisation ReportAnalyzer: {str(e)}")

    def analyze_report(self, text: str, company_info: Dict[str, Any], report_config: Dict[str, Any]) -> Dict[str, Any]:
        """Analyse un rapport avec logs détaillés."""
        try:
            # Debug: Afficher la longueur du texte extrait
            st.write(f"Longueur du texte extrait: {len(text)} caractères")
            st.write("Premiers 500 caractères du texte:")
            st.code(text[:500])

            if self.is_demo:
                return self._get_demo_analysis()

            # Préparer le prompt
            prompt = self._prepare_analysis_prompt(text, company_info, report_config)
            
            # Debug: Afficher le prompt
            with st.expander("Voir le prompt envoyé à l'API"):
                st.code(prompt)

            try:
                # Debug: Afficher les paramètres de l'appel API
                st.write("Paramètres de l'appel API:")
                st.json({
                    "model": self.model,
                    "temperature": self.temperature,
                    "max_tokens": 4000,
                })

                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": """Analyse ce rapport CSRD/DPEF et fournis:
1. Une analyse approfondie
2. Des scores sur 100 pour: conformité, qualité données, engagement, transparence
3. Des recommandations concrètes
4. Les sources citées
Format JSON uniquement."""},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=self.temperature,
                    max_tokens=4000,
                    response_format={"type": "json_object"}
                )
                
                # Debug: Afficher la réponse brute
                with st.expander("Voir la réponse brute de l'API"):
                    st.code(response.model_dump_json())
                
                # Récupérer et parser la réponse
                raw_content = response.choices[0].message.content
                st.write("Contenu de la réponse:")
                st.code(raw_content)
                
                analysis = self._parse_gpt_response(raw_content)
                
            except Exception as api_error:
                st.error(f"Erreur API détaillée: {str(api_error)}")
                return self._get_demo_analysis()

            # Debug: Afficher l'analyse parsée
            with st.expander("Voir l'analyse parsée"):
                st.json(analysis)

            scores = self._calculate_scores(analysis)

            results = {
                "analysis": analysis.get("analysis", "Analyse non disponible"),
                "scores": {
                    "global": scores.get("global", 0),
                    "detailed": scores.get("detailed", {})
                },
                "recommendations": analysis.get("recommendations", []),
                "sources": analysis.get("sources", [])
            }

            # Debug: Afficher les résultats finaux
            with st.expander("Voir les résultats finaux"):
                st.json(results)

            return results

        except Exception as e:
            st.error(f"Erreur lors de l'analyse du rapport (avec détails): {str(e)}")
            import traceback
            st.error(f"Traceback: {traceback.format_exc()}")
            return self._get_demo_analysis()

    def _prepare_analysis_prompt(self, text: str, company_info: Dict[str, Any], report_config: Dict[str, Any]) -> str:
        """Prépare le prompt avec plus de structure."""
        max_text_length = 100000
        truncated_text = text[:max_text_length] + ("..." if len(text) > max_text_length else "")
        
        return f"""Voici le rapport CSRD/DPEF à analyser:

ENTREPRISE: {company_info['name']}
SECTEUR: {company_info['sector']}
TAILLE: {company_info['size']}
TYPE: {report_config['type']}

CONTENU DU RAPPORT:
{truncated_text}

CONSIGNES D'ANALYSE:
1. Fournir une analyse générale
2. Évaluer sur 100 points:
   - Conformité réglementaire CSRD/DPEF
   - Qualité et fiabilité des données
   - Niveau d'engagement et actions
   - Transparence et identification des risques
3. Lister les recommandations d'amélioration
4. Identifier les sources principales

FORMAT DE RÉPONSE (JSON uniquement):
{{
    "analysis": "Analyse détaillée...",
    "scores": {{
        "conformite": 0-100,
        "qualite_donnees": 0-100,
        "engagement": 0-100,
        "transparence": 0-100
    }},
    "recommendations": [
        "Recommandation 1",
        "Recommandation 2"
    ],
    "sources": [
        "Source 1",
        "Source 2"
    ]
}}"""

    def _parse_gpt_response(self, response: str) -> Dict[str, Any]:
        """Parse la réponse avec plus de robustesse."""
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            st.error("Erreur de parsing JSON. Réponse brute:")
            st.code(response)
            # Retourner une structure minimale en cas d'erreur
            return {
                "analysis": "Erreur de parsing de la réponse",
                "scores": {
                    "conformite": 0,
                    "qualite_donnees": 0,
                    "engagement": 0,
                    "transparence": 0
                },
                "recommendations": [],
                "sources": []
            }
            
            lines = response.split('\n')
            current_section = None
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                    
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
            raw_scores = analysis.get("scores", {})
            
            detailed_scores = {
                "Conformité réglementaire": float(raw_scores.get("conformite", 0)),
                "Qualité des données": float(raw_scores.get("qualite_donnees", 0)),
                "Engagement et actions": float(raw_scores.get("engagement", 0)),
                "Transparence": float(raw_scores.get("transparence", 0))
            }
            
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
