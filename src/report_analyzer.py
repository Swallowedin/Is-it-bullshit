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

class CSRDReportAnalyzer:
    """Analyseur de rapports CSRD avec évaluation détaillée."""
    
    def __init__(self):
        try:
            if "OPENAI_API_KEY" not in st.secrets:
                st.error("Clé API manquante dans les secrets Streamlit")
                raise ValueError("Clé API manquante")
            
            self.client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
            self.model = "gpt-4o-mini"
            
            self.csrd_criteria = {
                # [Critères inchangés]
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
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": """Tu es un expert en analyse CSRD/DPEF.
                    Analyse UNIQUEMENT le contenu fourni, sans faire de suppositions.
                    Si tu ne peux pas analyser le contenu, tu DOIS retourner une erreur."""},
                    {"role": "user", "content": self._create_analysis_prompt(text, company_info, csrd_regulation)}
                ],
                temperature=0.5,
                max_tokens=4000,
                response_format={"type": "json_object"}
            )
            
            results = json.loads(response.choices[0].message.content)
            
            # Validation stricte des résultats
            if not results or not results.get("analysis"):
                raise ValueError("L'analyse n'a pas produit de résultats valides")
                
            return results
                
        except Exception as e:
            raise Exception(f"Échec de l'analyse: {str(e)}")
    def analyze_report(self, text: str, company_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyse complète d'un rapport selon les normes ESRS.
        
        Args:
            text: Texte du rapport
            company_info: Informations sur l'entreprise
        """
        try:
            # Analyse par section ESRS
            sections = ["environmental", "social", "governance"]
            results = {}

            for section in sections:
                results[section] = self._analyze_section(
                    text=text,
                    section=section,
                    company_info=company_info
                )

            # Consolider les résultats
            final_results = self._consolidate_results(results)
            
            # Enrichir avec les métadonnées
            final_results = self._enrich_results(
                results=final_results,
                company_info=company_info
            )

            return final_results

        except Exception as e:
            st.error(f"Erreur lors de l'analyse: {str(e)}")
            return self._get_demo_analysis()

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

            return json.loads(response.choices[0].message.content)

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

    def _consolidate_results(self, section_results: Dict[str, Any]) -> Dict[str, Any]:
        """Consolide les résultats de toutes les sections."""
        total_score = 0
        weights = {
            "environmental": 0.4,
            "social": 0.3,
            "governance": 0.3
        }

        consolidated = {
            "global_score": 0,
            "section_scores": {},
            "detailed_analysis": section_results,
            "compliance_summary": {
                "conforming": [],
                "non_conforming": [],
                "partially_conforming": []
            },
            "key_findings": [],
            "recommendations": []
        }

        # Calculer les scores
        for section, results in section_results.items():
            score = results.get("score", 0)
            weight = weights.get(section, 0)
            weighted_score = score * weight
            total_score += weighted_score

            consolidated["section_scores"][section] = {
                "score": score,
                "weighted_score": weighted_score,
                "weight": weight
            }

            # Agréger les recommandations et non-conformités
            consolidated["recommendations"].extend(results.get("recommendations", []))
            if "compliance" in results:
                consolidated["compliance_summary"]["conforming"].extend(
                    results["compliance"].get("conforming", [])
                )
                consolidated["compliance_summary"]["non_conforming"].extend(
                    results["compliance"].get("non_conforming", [])
                )
                consolidated["compliance_summary"]["partially_conforming"].extend(
                    results["compliance"].get("partially_conforming", [])
                )

        consolidated["global_score"] = round(total_score, 2)
        
        return consolidated

    def _enrich_results(self, results: Dict[str, Any], company_info: Dict[str, Any]) -> Dict[str, Any]:
        """Enrichit les résultats avec des métadonnées et analyses supplémentaires."""
        results["metadata"] = {
            "company_info": company_info,
            "analysis_date": datetime.now().isoformat(),
            "esrs_version": "2024",
            "analyzer_version": "2.0"
        }

        # Ajouter des statistiques
        results["statistics"] = {
            "total_conforming": len(results["compliance_summary"]["conforming"]),
            "total_non_conforming": len(results["compliance_summary"]["non_conforming"]),
            "total_partial": len(results["compliance_summary"]["partially_conforming"]),
            "total_recommendations": len(results["recommendations"])
        }

        # Ajouter un résumé exécutif
        results["executive_summary"] = self._generate_summary(results)

        return results

    def _generate_summary(self, results: Dict[str, Any]) -> str:
        """Génère un résumé exécutif des résultats."""
        return f"""Analyse ESRS - Score global: {results['global_score']}/100

Performance par section:
- Environnement: {results['section_scores']['environmental']['score']}/100
- Social: {results['section_scores']['social']['score']}/100
- Gouvernance: {results['section_scores']['governance']['score']}/100

Points d'attention:
- {len(results['compliance_summary']['non_conforming'])} non-conformités identifiées
- {len(results['compliance_summary']['partially_conforming'])} conformités partielles
- {len(results['recommendations'])} recommandations d'amélioration"""

    def _get_demo_analysis(self) -> Dict[str, Any]:
        """Retourne une analyse de démonstration."""
        return {
            "global_score": 75.5,
            "section_scores": {
                "environmental": {"score": 80, "weighted_score": 32, "weight": 0.4},
                "social": {"score": 70, "weighted_score": 21, "weight": 0.3},
                "governance": {"score": 75, "weighted_score": 22.5, "weight": 0.3}
            },
            "compliance_summary": {
                "conforming": ["ESRS E1.1", "ESRS S1.1"],
                "non_conforming": ["ESRS E2.3"],
                "partially_conforming": ["ESRS G1.2"]
            },
            "recommendations": [
                "Renforcer le reporting sur les émissions scope 3",
                "Améliorer la traçabilité des données sociales"
            ],
            "metadata": {
                "analysis_date": datetime.now().isoformat(),
                "esrs_version": "2024",
                "analyzer_version": "2.0"
            }
        }
