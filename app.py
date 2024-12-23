# app.py
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from pathlib import Path
import json
import PyPDF2
from openai import OpenAI
from typing import Dict, Any

# Configuration de la page
st.set_page_config(
    page_title="Is it Bullshit? - Analyseur CSRD/DPEF",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Lecture et cache de la réglementation CSRD
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
        
        # Vérifier le chargement
        total_docs = sum(len(files) for files in csrd_data.values())
        if total_docs == 0:
            st.warning("Aucun document ESRS trouvé dans data/csrd/general")
        else:
            st.success(f"{total_docs} documents ESRS chargés :\n" + 
                      f"- Environmental: {len(csrd_data['environmental'])} docs\n" +
                      f"- Social: {len(csrd_data['social'])} docs\n" +
                      f"- Governance: {len(csrd_data['governance'])} docs\n" +
                      f"- Cross-cutting: {len(csrd_data['cross_cutting'])} docs")
        
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
def extract_text_from_pdf(pdf_file):
    """Extrait le texte d'un fichier PDF."""
    text = ""
    try:
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        for page in pdf_reader.pages:
            text += page.extract_text()
        return text
    except Exception as e:
        st.error(f"Erreur lors de l'extraction du PDF: {str(e)}")
        return None

def get_company_context(company_name):
    """Récupère le contexte de l'entreprise."""
    return {
        "name": company_name,
        "sector": "Non spécifié",
        "size": "Non spécifiée"
    }

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
                "gouvernance": {
                    "supervision": ["Rôle du conseil d'administration", "Comités spécialisés"],
                    "management": ["Intégration dans la stratégie", "Objectifs et indicateurs"],
                    "politique_remuneration": ["Lien avec la durabilité", "Critères ESG"]
                },
                "strategie": {
                    "analyse_materialite": ["Identification des risques", "Double matérialité"],
                    "plan_transition": ["Objectifs climatiques", "Alignement Paris"],
                    "resilience": ["Scénarios climatiques", "Adaptation"]
                },
                "gestion_risques": {
                    "identification": ["Processus", "Méthodologie"],
                    "integration": ["Chaîne de valeur", "Impacts directs/indirects"],
                    "mitigation": ["Mesures prises", "Suivi"]
                },
                "indicateurs": {
                    "environnement": ["Émissions GES", "Biodiversité", "Eau", "Économie circulaire"],
                    "social": ["Droits humains", "Conditions de travail", "Formation"],
                    "gouvernance": ["Éthique", "Corruption", "Transparence"]
                }
            }
        except Exception as e:
            raise Exception(f"Erreur d'initialisation: {str(e)}")

    def analyze_report(self, text: str, company_info: Dict[str, Any], csrd_regulation: str) -> Dict[str, Any]:
        """Analyse un rapport selon les critères CSRD."""
        try:
            # Création du prompt
            prompt = self._create_analysis_prompt(text, company_info, csrd_regulation)
            
            # Appel à l'API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": """Tu es un expert en analyse CSRD/DPEF qui fournit des évaluations détaillées.
                    Analyse le rapport selon la réglementation fournie et évalue chaque aspect en détail."""},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=4000,
                response_format={"type": "json_object"}
            )
            
            # Traitement de la réponse
            results = json.loads(response.choices[0].message.content)
            return self._validate_and_enhance_results(results)
            
        except Exception as e:
            st.error(f"Erreur d'analyse: {str(e)}")
            return self._get_demo_analysis()

    def _create_analysis_prompt(self, text: str, company_info: Dict[str, Any], csrd_regulation: str) -> str:
        """Crée le prompt d'analyse détaillé."""
        return f"""Analyse ce rapport CSRD/DPEF selon la réglementation suivante:

RÉGLEMENTATION CSRD:
{csrd_regulation[:2000]}...

ENTREPRISE:
- Nom: {company_info['name']}
- Secteur: {company_info['sector']}
- Taille: {company_info['size']}

RAPPORT:
{text[:8000]}...

CONSIGNES:
Réaliser une analyse détaillée selon les critères suivants:

1. GOUVERNANCE
- Supervision et management
- Intégration de la durabilité
- Politique de rémunération

2. STRATÉGIE
- Analyse de matérialité
- Plan de transition
- Résilience climatique

3. GESTION DES RISQUES
- Identification
- Intégration
- Mitigation

4. INDICATEURS
- Environnementaux
- Sociaux
- Gouvernance

FORMAT DE RÉPONSE (JSON):
{
    "analysis": {
        "gouvernance": {
            "score": X,
            "evaluation": "...",
            "points_forts": [],
            "axes_amelioration": []
        },
        "strategie": {
            "score": X,
            "evaluation": "...",
            "points_forts": [],
            "axes_amelioration": []
        },
        "gestion_risques": {
            "score": X,
            "evaluation": "...",
            "points_forts": [],
            "axes_amelioration": []
        },
        "indicateurs": {
            "score": X,
            "evaluation": "...",
            "points_forts": [],
            "axes_amelioration": []
        }
    },
    "conformite": {
        "score_global": X,
        "evaluation": "...",
        "non_conformites": []
    },
    "recommandations": [],
    "sources": []
}"""

    def _validate_and_enhance_results(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Valide et enrichit les résultats."""
        # Calcul score global
        section_scores = [
            results["analysis"][section]["score"]
            for section in ["gouvernance", "strategie", "gestion_risques", "indicateurs"]
        ]
        global_score = sum(section_scores) / len(section_scores)
        
        # Ajout métadonnées
        results["metadata"] = {
            "date_analyse": datetime.now().isoformat(),
            "version_csrd": "2024",
            "score_global": global_score
        }
        
        return results

    def _get_demo_analysis(self) -> Dict[str, Any]:
        """Retourne une analyse de démonstration."""
        return {
            "analysis": {
                "gouvernance": {
                    "score": 75,
                    "evaluation": "Bonne intégration de la durabilité",
                    "points_forts": ["Comité RSE actif"],
                    "axes_amelioration": ["Renforcer le lien rémunération-RSE"]
                },
                "strategie": {
                    "score": 70,
                    "evaluation": "Stratégie climat définie",
                    "points_forts": ["Objectifs 2030 fixés"],
                    "axes_amelioration": ["Préciser les jalons"]
                },
                "gestion_risques": {
                    "score": 80,
                    "evaluation": "Processus robuste",
                    "points_forts": ["Cartographie détaillée"],
                    "axes_amelioration": ["Améliorer le suivi"]
                },
                "indicateurs": {
                    "score": 85,
                    "evaluation": "KPIs bien définis",
                    "points_forts": ["Scope 3 calculé"],
                    "axes_amelioration": ["Ajouter biodiversité"]
                }
            },
            "conformite": {
                "score_global": 77.5,
                "evaluation": "Bonne conformité générale",
                "non_conformites": []
            },
            "recommandations": [
                "Renforcer les objectifs biodiversité",
                "Améliorer le reporting scope 3"
            ],
            "sources": [
                "Rapport annuel",
                "Documentation CSRD"
            ],
            "metadata": {
                "date_analyse": datetime.now().isoformat(),
                "version_csrd": "2024",
                "score_global": 77.5
            }
        }

def display_csrd_analysis(analysis_results: Dict[str, Any]):
    """Affiche les résultats de l'analyse CSRD."""
    # Score global
    st.metric("Score global CSRD", 
             f"{analysis_results['metadata']['score_global']:.1f}/100",
             delta=None)
    
    # Onglets par section
    tabs = st.tabs(["Gouvernance", "Stratégie", "Gestion des risques", "Indicateurs"])
    
    for tab, section in zip(tabs, ["gouvernance", "strategie", "gestion_risques", "indicateurs"]):
        with tab:
            data = analysis_results["analysis"][section]
            
            # Score de la section
            st.metric(f"Score {section.replace('_', ' ').title()}", 
                     f"{data['score']:.1f}/100")
            
            # Évaluation
            st.markdown("### Évaluation")
            st.write(data['evaluation'])
            
            # Points forts et axes d'amélioration
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("### Points forts")
                for point in data['points_forts']:
                    st.markdown(f"✅ {point}")
            with col2:
                st.markdown("### Axes d'amélioration")
                for point in data['axes_amelioration']:
                    st.markdown(f"📈 {point}")
    
    # Conformité
    st.markdown("---")
    st.markdown("### Conformité réglementaire")
    st.metric("Score de conformité", 
             f"{analysis_results['conformite']['score_global']:.1f}/100")
    st.write(analysis_results['conformite']['evaluation'])
    
    if analysis_results['conformite']['non_conformites']:
        st.markdown("#### Points de non-conformité")
        for point in analysis_results['conformite']['non_conformites']:
            st.markdown(f"⚠️ {point}")

def generate_detailed_report(analysis_results: Dict[str, Any], company_info: Dict[str, Any]):
    """Génère un rapport PDF détaillé."""
    from fpdf import FPDF
    
    class PDF(FPDF):
        def header(self):
            self.set_font('Arial', 'B', 15)
            self.cell(0, 10, "Rapport d'analyse CSRD/DPEF", 0, 1, 'C')
            self.ln(10)
    
    pdf = PDF()
    pdf.add_page()
    
    # En-tête
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, f"Entreprise : {company_info['name']}", 0, 1)
    pdf.cell(0, 10, f"Date : {datetime.now().strftime('%d/%m/%Y')}", 0, 1)
    pdf.cell(0, 10, f"Score global : {analysis_results['metadata']['score_global']:.1f}/100", 0, 1)
    
    # Sections d'analyse
    sections = ["gouvernance", "strategie", "gestion_risques", "indicateurs"]
    for section in sections:
        data = analysis_results["analysis"][section]
        
        pdf.ln(10)
        pdf.set_font('Arial', 'B', 14)
        pdf.cell(0, 10, section.replace('_', ' ').title(), 0, 1)
        
        pdf.set_font('Arial', '', 12)
        pdf.cell(0, 10, f"Score : {data['score']:.1f}/100", 0, 1)
        pdf.multi_cell(0, 10, data['evaluation'])
        
        pdf.ln(5)
        pdf.set_font('Arial', 'B', 12)
        pdf.cell(0, 10, "Points forts :", 0, 1)
        pdf.set_font('Arial', '', 12)
        for point in data['points_forts']:
            pdf.multi_cell(0, 10, f"• {point}")
        
        pdf.ln(5)
        pdf.set_font('Arial', 'B', 12)
        pdf.cell(0, 10, "Axes d'amélioration :", 0, 1)
        pdf.set_font('Arial', '', 12)
        for point in data['axes_amelioration']:
            pdf.multi_cell(0, 10, f"• {point}")
    
    # Conformité
    pdf.ln(10)
    pdf.set_font('Arial', 'B', 14)
    pdf.cell(0, 10, "Conformité réglementaire", 0, 1)
    pdf.set_font('Arial', '', 12)
    pdf.multi_cell(0, 10, analysis_results['conformite']['evaluation'])
    
    try:
        return pdf.output(dest='S').encode('latin-1', errors='replace')
    except Exception as e:
        st.error(f"Erreur lors de la génération du PDF: {str(e)}")
        return None

def main():
    # Initialisation de l'analyseur
    if 'analyzer' not in st.session_state:
        try:
            st.session_state.analyzer = ReportAnalyzer()
        except Exception as e:
            st.error(f"Erreur d'initialisation: {str(e)}")
            return

    # Sidebar
    with st.sidebar:
        st.title("Is it Bullshit?")
        
        # Navigation
        page = st.radio(
            "Navigation",
            ["Analyse CSRD", "Dashboard", "Historique"]
        )
        
        # Filtres globaux
        st.subheader("Filtres")
        sector = st.selectbox("Secteur", ["Tous", "Industrie", "Services", "Énergie"])
        year = st.selectbox("Année", list(range(2024, 2020, -1)))

    # Gestion des pages
    if page == "Analyse CSRD":
        # Initialisation du state si nécessaire
        if 'analysis_completed' not in st.session_state:
            st.session_state.analysis_completed = False
        if 'analysis_results' not in st.session_state:
            st.session_state.analysis_results = None
        if 'current_company_info' not in st.session_state:
            st.session_state.current_company_info = None

        st.title("Analyse de rapport CSRD/DPEF")
        
        # Reset le state si nécessaire
        def reset_analysis_state():
            st.session_state.analysis_completed = False
            st.session_state.analysis_results = None
        
        # Interface d'upload
        col1, col2 = st.columns([2, 1])
        
        with col1:
            company_name = st.text_input("Nom de l'entreprise", 
                                       on_change=reset_analysis_state)
            if company_name:
                company_info = get_company_context(company_name)
                st.session_state.current_company_info = company_info
        
        with col2:
            uploaded_file = st.file_uploader("Rapport CSRD/DPEF (PDF)", 
                                           type="pdf",
                                           on_change=reset_analysis_state)
        
        # Messages de guidage
        if not company_name:
            st.info("👆 Commencez par entrer le nom de l'entreprise")
        elif not uploaded_file:
            st.info("👆 Uploadez maintenant le rapport PDF à analyser")
        
        # Zone du bouton d'analyse
        st.markdown("---")
        analyze_col1, analyze_col2, analyze_col3 = st.columns([1, 2, 1])
        
        with analyze_col2:
            if uploaded_file and company_name and not st.session_state.analysis_completed:
                if st.button("🔍 Lancer l'analyse CSRD", use_container_width=True):
                    with st.spinner("Analyse CSRD en cours..."):
                        text = extract_text_from_pdf(uploaded_file)
                        if text:
                            analysis_results = st.session_state.analyzer.analyze_report(
                                text=text,
                                company_info=company_info
                            )
                            st.session_state.analysis_results = analysis_results
                            st.session_state.analysis_completed = True
                            st.rerun()
        
        st.markdown("---")
        
        # Affichage des résultats
        if st.session_state.analysis_completed and st.session_state.analysis_results:
            analysis_results = st.session_state.analysis_results
            company_info = st.session_state.current_company_info
            
            # Affichage des résultats
            st.subheader("Résultats de l'analyse")
            
            # Score global et par section
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Score global", f"{analysis_results['global_score']:.1f}/100")
            with col2:
                st.metric("Conformités", f"{len(analysis_results['compliance_summary']['conforming'])}")
            with col3:
                st.metric("Non-conformités", f"{len(analysis_results['compliance_summary']['non_conforming'])}")

            # Résultats détaillés par section
            tabs = st.tabs(["Environmental", "Social", "Governance"])
            sections = ["environmental", "social", "governance"]
            
            for tab, section in zip(tabs, sections):
                with tab:
                    if section in analysis_results['section_scores']:
                        score_data = analysis_results['section_scores'][section]
                        st.metric(
                            f"Score {section.title()}", 
                            f"{score_data['score']:.1f}/100",
                            f"Pondération: {score_data['weight']:.0%}"
                        )
                        
                        if section in analysis_results['detailed_analysis']:
                            section_details = analysis_results['detailed_analysis'][section]
                            st.write(section_details['evaluation'])
                            
                            with st.expander("Voir les détails"):
                                if 'standards_analysis' in section_details:
                                    for std, analysis in section_details['standards_analysis'].items():
                                        st.markdown(f"**{std}**: {analysis['conformity']}")
                                        if analysis.get('findings'):
                                            for finding in analysis['findings']:
                                                st.markdown(f"- {finding}")
            
            # Recommendations
            st.subheader("Recommandations d'amélioration")
            for i, rec in enumerate(analysis_results['recommendations'], 1):
                st.markdown(f"{i}. {rec}")
                
            # Export PDF
            if st.button("📄 Générer rapport détaillé"):
                report_pdf = generate_detailed_report(analysis_results, company_info)
                if report_pdf:
                    st.download_button(
                        "⬇️ Télécharger le rapport PDF",
                        report_pdf,
                        file_name=f"analyse_csrd_{company_name}_{datetime.now().strftime('%Y%m%d')}.pdf",
                        mime="application/pdf"
                    )
            
            # Bouton nouvelle analyse
            if st.button("🔄 Nouvelle analyse"):
                reset_analysis_state()
                st.rerun()

    elif page == "Dashboard":
        st.title("Dashboard CSRD")

        
    else:  # Historique
        st.title("Historique des analyses")
        st.info("Historique en cours de développement")

# Déplacé hors de la fonction main()
if __name__ == "__main__":
    main()
