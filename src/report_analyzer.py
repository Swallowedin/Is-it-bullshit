# report_analyzer.py
import streamlit as st
from openai import OpenAI
from typing import Dict, Any, List, Optional
from pathlib import Path
import json
from datetime import datetime

@st.cache_data
def load_csrd_documents() -> Optional[Dict[str, Dict[str, str]]]:
    """
    Charge les documents CSRD/ESRS depuis le système de fichiers.
    Returns:
        Dict[str, Dict[str, str]]: Documents CSRD organisés par catégorie
    """
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
                        name = file_path.stem
                        
                        # Catégoriser les fichiers selon leur préfixe
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
                    continue
        
        return csrd_data

    except Exception as e:
        st.error(f"Erreur lors du chargement des documents ESRS: {str(e)}")
        return None

def get_regulatory_context(csrd_data: Dict[str, Dict[str, str]], section: str) -> str:
    """
    Récupère le contexte réglementaire pour une section donnée.
    Args:
        csrd_data (Dict): Documents CSRD
        section (str): Section à analyser
    Returns:
        str: Contexte réglementaire concaténé
    """
    if not csrd_data:
        return ""
        
    relevant_docs = []
    
    # Ajouter les documents cross-cutting pour les sections principales
    if section in ["environmental", "social", "governance"]:
        relevant_docs.extend(csrd_data["cross_cutting"].values())
    
    # Ajouter les documents spécifiques à la section
    if section in csrd_data:
        relevant_docs.extend(csrd_data[section].values())
    
    # Ajouter les précisions pertinentes
    if "precisions" in csrd_data:
        relevant_docs.extend(csrd_data["precisions"].values())
        
    return "\n\n---\n\n".join(relevant_docs)

class SectionAnalyzer:
    """Classe utilitaire pour l'analyse d'une section spécifique."""
    
    def __init__(self, section: str, evaluation_criteria: Dict[str, Any]):
        self.section = section
        self.criteria = evaluation_criteria[section]
    
    def create_analysis_prompt(self, text: str, company_info: Dict[str, Any], 
                             regulatory_context: str) -> str:
        """Crée le prompt pour l'analyse d'une section."""
        return f"""Analyser la section {self.section} selon les normes ESRS.

CONTEXTE ENTREPRISE:
{json.dumps(company_info, indent=2)}

RÉFÉRENTIEL ESRS APPLICABLE:
{regulatory_context[:2000]}

CRITÈRES D'ÉVALUATION:
{json.dumps(self.criteria, indent=2)}

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

class CSRDReportAnalyzer:
    """Analyseur de rapports CSRD avec évaluation détaillée."""
    
    def __init__(self):
        """Initialise l'analyseur avec les configurations nécessaires."""
        try:
            if "OPENAI_API_KEY" not in st.secrets:
                st.error("Clé API manquante dans les secrets Streamlit")
                raise ValueError("Clé API manquante")
            
            self.client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
            self.model = "gpt-4o-mini"  # Modèle le plus récent avec JSON mode
            self.csrd_data = load_csrd_documents()
            
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
            
            if not self.csrd_data:
                raise ValueError("Impossible de charger les documents CSRD")
                
        except Exception as e:
            raise Exception(f"Erreur d'initialisation: {str(e)}")

    def analyze_report(self, text: str, company_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyse un rapport selon les critères CSRD.
        Args:
            text (str): Texte du rapport à analyser
            company_info (Dict): Informations sur l'entreprise
        Returns:
            Dict: Résultats de l'analyse
        """
        if not text:
            raise ValueError("Le texte du rapport est vide")
            
        try:
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
                
                # Mise à jour du score global et des non-conformités
                total_score += section_results.get("score", 0)
                analysis_results["conformite"]["non_conformites"].extend(
                    section_results["compliance"].get("non_conforming", [])
                )
                
                # Ajouter les recommandations
                if "recommendations" in section_results:
                    analysis_results["recommendations"].extend(section_results["recommendations"])
            
            # Calcul du score global
            analysis_results["conformite"]["score_global"] = round(total_score / len(sections), 1)
            analysis_results["conformite"]["evaluation"] = (
                f"Score global de conformité: {analysis_results['conformite']['score_global']}/100. "
                f"{len(analysis_results['conformite']['non_conformites'])} non-conformités identifiées."
            )

            # Ajout des métadonnées
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
        """
        Analyse une section spécifique du rapport.
        Args:
            text (str): Texte du rapport
            section (str): Section à analyser
            company_info (Dict): Informations sur l'entreprise
        Returns:
            Dict: Résultats de l'analyse de la section
        """
        try:
            section_analyzer = SectionAnalyzer(section, self.evaluation_criteria)
            regulatory_context = get_regulatory_context(self.csrd_data, section)
            
            prompt = section_analyzer.create_analysis_prompt(
                text=text,
                company_info=company_info,
                regulatory_context=regulatory_context
            )

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
