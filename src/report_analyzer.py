# report_analyzer.py
import streamlit as st
from openai import OpenAI
from typing import Dict, Any, List
from pathlib import Path
import json
from datetime import datetime

@st.cache_data
def load_csrd_documents():
    """Charge les documents CSRD/ESRS"""
    try:
        base_path = Path("data/csrd")
        csrd_data = {
            "environmental": {},  # ESRS E1-E5
            "social": {},        # ESRS S1-S4
            "governance": {},    # ESRS G1
            "cross_cutting": {}, # ESRS 1-2
            "annexes": {},       # Documents annexes
            "precisions": {}     # Précisions et Q&A
        }
        
        # Parcourir tous les fichiers du dossier general
        general_path = base_path / "general"
        if general_path.exists():
            for file_path in general_path.glob("*.txt"):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                        # Catégoriser les fichiers selon leur préfixe
                        name = file_path.stem
                        if name.startswith("ESRS_E"):
                            csrd_data["environmental"][name] = content
                        elif name.startswith("ESRS_S"):
                            csrd_data["social"][name] = content
                        elif name.startswith("ESRS_G"):
                            csrd_data["governance"][name] = content
                        elif name.startswith("ESRS") and name[4].isdigit():
                            csrd_data["cross_cutting"][name] = content
                        elif name.startswith("ANNEXE"):
                            csrd_data["annexes"][name] = content
                        elif name in ["Questions_réponses", "precisions_esrs"]:
                            csrd_data["precisions"][name] = content
                        
                except Exception as e:
                    st.error(f"Erreur lors de la lecture de {file_path}: {str(e)}")
        
        return csrd_data

    except Exception as e:
        st.error(f"Erreur lors du chargement des documents ESRS: {str(e)}")
        return None

def get_regulatory_context(csrd_data: Dict[str, Dict[str, str]], section: str) -> str:
    """Récupère le contexte réglementaire pour une section donnée."""
    if not csrd_data:
        return ""
        
    relevant_docs = []
    
    # Ajouter les documents cross-cutting
    if section in ["environmental", "social", "governance"]:
        relevant_docs.extend(csrd_data["cross_cutting"].values())
    
    # Ajouter les documents spécifiques à la section
    if section in csrd_data:
        relevant_docs.extend(csrd_data[section].values())
    
    # Ajouter les précisions pertinentes
    if "precisions" in csrd_data:
        relevant_docs.extend(csrd_data["precisions"].values())
        
    return "\n\n---\n\n".join(relevant_docs)

class CSRDReportAnalyzer:
    """Analyseur de rapports CSRD avec évaluation détaillée."""
    
    def __init__(self):
        try:
            if "OPENAI_API_KEY" not in st.secrets:
                st.error("Clé API manquante dans les secrets Streamlit")
                raise ValueError("Clé API manquante")
            
            self.client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
            self.model = "gpt-4o-mini"
            self.csrd_data = load_csrd_documents()  # Chargement direct des documents
            
            # Structure d'évaluation ESRS
            self.evaluation_criteria = {
                "environmental": {
                    "climate": ["ESRS E1"],
                    "pollution": ["ESRS E2"],
                    "water": ["ESRS E3"],
                    "biodiversity": ["ESRS E4"],
                    "circular_economy": ["ESRS E5"]
                },
                "social": {
                    "workforce": ["ESRS S1"],
                    "communities": ["ESRS S2"],
                    "affected_people": ["ESRS S3"],
                    "consumers": ["ESRS S4"]
                },
                "governance": {
                    "business_conduct": ["ESRS G1"]
                }
            }
        except Exception as e:
            raise Exception(f"Erreur d'initialisation: {str(e)}")

    def analyze_report(self, text: str, company_info: Dict[str, Any], csrd_regulation: str) -> Dict[str, Any]:
        """Analyse un rapport selon les critères CSRD."""
        if not text:
            raise ValueError("Erreur: Le texte du rapport est vide")
            
        try:
            # Log pour debug et vérification
            st.write(f"Analyse du rapport pour: {company_info['name']}")
            st.write(f"Longueur du texte: {len(text)} caractères")
            
            # Structure de base des résultats
            analysis_results = {
                "analysis": {},
                "conformite": {
                    "score_global": 0,
                    "evaluation": "",
                    "non_conformites": []
                },
                "recommendations": []
            }
            
            # Analyse par section ESRS
            sections = ["environmental", "social", "governance"]
            total_score = 0
            
            for section in sections:
                section_results = self._analyze_section(
                    text=text,
                    section=section,
                    company_info=company_info
                )
                
                # Ajouter les résultats de la section
                analysis_results["analysis"][section] = {
                    "score": section_results.get("score", 0),
                    "evaluation": section_results.get("evaluation", ""),
                    "points_forts": section_results["compliance"].get("conforming", []),
                    "axes_amelioration": section_results["compliance"].get("non_conforming", [])
                }
                
                # Calculer le score global
                total_score += section_results.get("score", 0)
                
                # Agréger les non-conformités
                analysis_results["conformite"]["non_conformites"].extend(
                    section_results["compliance"].get("non_conforming", [])
                )
                
                # Agréger les recommandations
                analysis_results["recommendations"].extend(
                    section_results.get("recommendations", [])
                )
            
            # Calculer le score global moyen
            analysis_results["conformite"]["score_global"] = total_score / len(sections)
            analysis_results["conformite"]["evaluation"] = (
                f"Score global de conformité: {analysis_results['conformite']['score_global']:.1f}/100. "
                f"{len(analysis_results['conformite']['non_conformites'])} non-conformités identifiées."
            )

            # Enrichir avec les métadonnées
            analysis_results["metadata"] = {
                "company_info": company_info,
                "analysis_date": datetime.now().isoformat(),
                "version_csrd": "2024",
                "score_global": analysis_results["conformite"]["score_global"]
            }

            return analysis_results
            
        except Exception as e:
            st.error(f"Erreur détaillée de l'analyse: {str(e)}")
            raise Exception(f"Échec de l'analyse: {str(e)}")

    def _analyze_section(self, text: str, section: str, company_info: Dict[str, Any]) -> Dict[str, Any]:
        """Analyse une section spécifique du rapport."""
        # Préparer le contexte réglementaire
        regulatory_context = self._get_section_context(section)
        criteria = self.evaluation_criteria[section]

        # Créer le prompt
        prompt = f"""Analyser la section {section} selon les normes ESRS.

CONTEXTE ENTREPRISE:
{json.dumps(company_info, indent=2)}

RÉFÉRENTIEL ESRS APPLICABLE:
{regulatory_context[:2000]}

CRITÈRES D'ÉVALUATION:
{json.dumps(criteria, indent=2)}

TEXTE À ANALYSER:
{text[:8000]}

FORMAT DE RÉPONSE (JSON):
{{
    "score": float,  # Score global (0-100)
    "evaluation": string,  # Évaluation générale
    "standards_analysis": {{  # Analyse par standard ESRS
        "standard_id": {{
            "score": float,
            "conformity": string,
            "findings": [string],
            "evidence": [string]
        }}
    }},
    "compliance": {{
        "conforming": [string],
        "non_conforming": [string],
        "partially_conforming": [string]
    }},
    "recommendations": [string]
}}"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": f"Tu es un expert en analyse ESRS, spécialisé dans la section {section}."
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=4000,
                response_format={"type": "json_object"}
            )

            results = json.loads(response.choices[0].message.content)
            if not results or not isinstance(results, dict):
                raise ValueError(f"Réponse invalide pour la section {section}")
                
            return results

        except Exception as e:
            st.error(f"Erreur lors de l'analyse de la section {section}: {str(e)}")
            return {
                "score": 0,
                "evaluation": f"Erreur d'analyse de la section {section}",
                "standards_analysis": {},
                "compliance": {
                    "conforming": [],
                    "non_conforming": [],
                    "partially_conforming": []
                },
                "recommendations": []
            }

    def _get_section_context(self, section: str) -> str:
        """Récupère le contexte réglementaire pour une section."""
        if not self.csrd_data:
            return ""

        relevant_texts = []

        # Ajouter les textes cross-cutting
        if "cross_cutting" in self.csrd_data:
            relevant_texts.extend(self.csrd_data["cross_cutting"].values())

        # Ajouter les textes spécifiques à la section
        if section in self.csrd_data:
            relevant_texts.extend(self.csrd_data[section].values())

        return "\n\n---\n\n".join(relevant_texts)
