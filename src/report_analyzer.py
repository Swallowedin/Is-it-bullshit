import streamlit as st
from openai import OpenAI
from datetime import datetime
import json
from typing import Dict, Any, List
from pathlib import Path

class CSRDReportAnalyzer:
    """Analyseur avancé de rapports CSRD avec intégration de base de connaissances."""
    
    def __init__(self):
        """Initialise l'analyseur avec la configuration et la base de connaissances."""
        try:
            if "OPENAI_API_KEY" not in st.secrets:
                st.error("Clé API manquante dans les secrets Streamlit")
                raise ValueError("Clé API manquante")
            
            self.client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
            self.model = "gpt-4o-mini"
            
            # Initialisation de la base de connaissances CSRD
            self.knowledge_base = CSRDKnowledgeBase()
            self.regulatory_docs = self.knowledge_base.load_regulatory_documents()
            
            # Critères d'analyse détaillés
            self.criteria = self.knowledge_base.detailed_criteria
            self.scoring_matrix = self.knowledge_base.get_scoring_matrix()
            
        except Exception as e:
            raise Exception(f"Erreur d'initialisation: {str(e)}")

    def analyze_report(self, text: str, company_info: Dict[str, Any], csrd_text: str) -> Dict[str, Any]:
        """
        Analyse complète d'un rapport CSRD.
        
        Args:
            text: Texte du rapport à analyser
            company_info: Informations sur l'entreprise
            csrd_text: Texte de la réglementation CSRD
        """
        try:
            # Chargement du contexte réglementaire spécifique au secteur
            sector = company_info.get('sector', 'general')
            sector_requirements = self.knowledge_base.load_sector_requirements(sector)
            
            # Préparation du contexte d'analyse
            context = self._prepare_analysis_context(
                company_info,
                sector_requirements,
                csrd_text
            )
            
            # Analyse détaillée par section
            sections = ["environmental", "social", "governance"]
            section_results = {}
            
            for section in sections:
                results = self._analyze_section(
                    text=text,
                    section=section,
                    context=context,
                    criteria=self.criteria.get(section, {})
                )
                section_results[section] = results
            
            # Consolidation des résultats
            final_results = self._consolidate_results(
                section_results=section_results,
                scoring_matrix=self.scoring_matrix
            )
            
            # Ajout des métadonnées et enrichissement
            final_results = self._enrich_results(
                results=final_results,
                company_info=company_info,
                section_results=section_results
            )
            
            return final_results
            
        except Exception as e:
            st.error(f"Erreur lors de l'analyse: {str(e)}")
            return self._get_demo_analysis()

    def _prepare_analysis_context(self, 
                                company_info: Dict[str, Any],
                                sector_requirements: Dict[str, Any],
                                csrd_text: str) -> Dict[str, Any]:
        """Prépare le contexte complet pour l'analyse."""
        return {
            "company_info": {
                "name": company_info.get('name', ''),
                "sector": company_info.get('sector', ''),
                "size": company_info.get('size', ''),
                "region": company_info.get('region', '')
            },
            "sector_requirements": sector_requirements,
            "regulatory_context": csrd_text,
            "evaluation_criteria": self.criteria,
            "scoring_matrix": self.scoring_matrix
        }

    def _analyze_section(self,
                        text: str,
                        section: str,
                        context: Dict[str, Any],
                        criteria: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyse détaillée d'une section spécifique.
        """
        # Création du prompt d'analyse spécifique à la section
        prompt = f"""Analyser la section {section} selon les critères CSRD.

CONTEXTE SECTORIEL:
{json.dumps(context.get('sector_requirements', {}), indent=2)}

CRITÈRES D'ÉVALUATION:
{json.dumps(criteria, indent=2)}

TEXTE À ANALYSER:
{text[:8000]}

INSTRUCTIONS:
1. Évaluer chaque critère listé
2. Fournir des preuves textuelles pour chaque évaluation
3. Identifier les non-conformités
4. Proposer des recommandations d'amélioration

FORMAT DE RÉPONSE (JSON):
{{
    "score": float,  # Score global de la section (0-100)
    "evaluation": string,  # Évaluation générale
    "criteria_scores": {{
        "critere1": {{
            "score": float,
            "evaluation": string,
            "evidence": [string],
            "compliance": string  # "conforme", "non_conforme", ou "partiel"
        }}
    }},
    "non_conformities": [string],
    "recommendations": [string],
    "key_findings": [string]
}}"""

        # Appel à l'API avec contexte spécialisé
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": f"Tu es un expert en analyse CSRD spécialisé dans l'analyse de la section {section}."
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
                "criteria_scores": {},
                "non_conformities": [],
                "recommendations": [],
                "key_findings": []
            }

    def _consolidate_results(self, 
                           section_results: Dict[str, Dict[str, Any]], 
                           scoring_matrix: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """
        Consolide les résultats de toutes les sections en un résultat final.
        """
        global_score = 0
        detailed_scores = {}
        all_findings = []
        all_recommendations = []
        non_conformities = []

        # Calcul des scores pondérés
        for section, matrix in scoring_matrix.items():
            if section in section_results:
                section_data = section_results[section]
                score = section_data.get('score', 0)
                weight = matrix.get('weight', 0)
                
                # Score pondéré
                global_score += score * weight
                detailed_scores[section] = {
                    'score': score,
                    'weight': weight,
                    'weighted_score': score * weight
                }

                # Collecte des findings et recommandations
                all_findings.extend(section_data.get('key_findings', []))
                all_recommendations.extend(section_data.get('recommendations', []))
                non_conformities.extend(section_data.get('non_conformities', []))

        return {
            "global_score": round(global_score, 2),
            "detailed_scores": detailed_scores,
            "key_findings": all_findings,
            "recommendations": all_recommendations,
            "non_conformities": non_conformities,
            "section_details": section_results
        }

    def _enrich_results(self,
                       results: Dict[str, Any],
                       company_info: Dict[str, Any],
                       section_results: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """
        Enrichit les résultats avec des métadonnées et analyses supplémentaires.
        """
        # Ajout des métadonnées
        results["metadata"] = {
            "analysis_date": datetime.now().isoformat(),
            "company_info": company_info,
            "csrd_version": "2024",
            "analysis_version": "2.0"
        }
        
        # Calcul des statistiques
        stats = {
            "total_findings": len(results["key_findings"]),
            "total_recommendations": len(results["recommendations"]),
            "non_conformities_count": len(results["non_conformities"]),
            "section_scores_summary": {
                section: data.get("score", 0)
                for section, data in section_results.items()
            }
        }
        results["statistics"] = stats
        
        # Ajout d'un résumé exécutif
        results["executive_summary"] = self._generate_executive_summary(results)
        
        return results

    def _generate_executive_summary(self, results: Dict[str, Any]) -> str:
        """
        Génère un résumé exécutif de l'analyse.
        """
        summary = (
            f"Score global: {results['global_score']}/100\n"
            f"Points clés: {len(results['key_findings'])} observations\n"
            f"Non-conformités: {len(results['non_conformities'])} identifiées\n"
            "Principales recommandations: " + 
            "; ".join(results['recommendations'][:3]) if results['recommendations'] else "Aucune"
        )
        return summary

    def _get_demo_analysis(self) -> Dict[str, Any]:
        """
        Génère une analyse de démonstration en cas d'erreur.
        """
        return {
            "global_score": 75.5,
            "detailed_scores": {
                "environmental": {"score": 80, "weight": 0.4, "weighted_score": 32},
                "social": {"score": 70, "weight": 0.3, "weighted_score": 21},
                "governance": {"score": 75, "weight": 0.3, "weighted_score": 22.5}
            },
            "key_findings": [
                "Bonne gouvernance climatique",
                "Reporting scope 3 incomplet",
                "Politique biodiversité à renforcer"
            ],
            "recommendations": [
                "Compléter le reporting scope 3",
                "Renforcer les objectifs biodiversité",
                "Améliorer le suivi des fournisseurs"
            ],
            "non_conformities": [],
            "section_details": {},
            "metadata": {
                "analysis_date": datetime.now().isoformat(),
                "csrd_version": "2024",
                "analysis_version": "2.0"
            },
            "statistics": {
                "total_findings": 3,
                "total_recommendations": 3,
                "non_conformities_count": 0
            },
            "executive_summary": "Analyse de démonstration avec un score global de 75.5/100"
        }
