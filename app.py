# app.py
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from pathlib import Path
import json
import PyPDF2
import io
from typing import Dict, Any
from src.report_analyzer import CSRDReportAnalyzer, load_csrd_documents, get_regulatory_context

# Configuration de la page
st.set_page_config(
    page_title="Is it Bullshit? - Analyseur CSRD/DPEF",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

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

def get_company_context(company_name: str) -> Dict[str, str]:
    """Récupère le contexte de l'entreprise."""
    return {
        "name": company_name,
        "sector": "Non spécifié",
        "size": "Non spécifiée"
    }

def generate_detailed_report(analysis_results: Dict[str, Any], company_info: Dict[str, Any]) -> bytes:
    """Génère un rapport PDF détaillé."""
    from fpdf import FPDF
    
    class PDF(FPDF):
        def header(self):
            self.set_font('Arial', 'B', 15)
            self.cell(0, 10, "Rapport d'analyse CSRD/DPEF", 0, 1, 'C')
            self.ln(10)

    try:
        pdf = PDF()
        pdf.add_page()
        
        # En-tête
        pdf.set_font('Arial', 'B', 12)
        pdf.cell(0, 10, f"Entreprise: {company_info['name']}", 0, 1)
        pdf.cell(0, 10, f"Date: {datetime.now().strftime('%d/%m/%Y')}", 0, 1)
        
        # Sections d'analyse
        sections = ["environmental", "social", "governance"]
        section_names = {
            "environmental": "Environnement",
            "social": "Social",
            "governance": "Gouvernance"
        }
        
        for section in sections:
            data = analysis_results["analysis"][section]
            
            pdf.ln(5)
            pdf.set_font('Arial', 'B', 12)
            pdf.cell(0, 10, section_names[section], 0, 1)
            
            pdf.set_font('Arial', '', 11)
            pdf.cell(0, 10, f"Score: {data['score']:.1f}/100", 0, 1)
            pdf.multi_cell(0, 10, data['evaluation'])
            
            pdf.cell(0, 10, "Points forts:", 0, 1)
            for point in data['points_forts']:
                pdf.multi_cell(0, 10, "- " + point)
            
            pdf.cell(0, 10, "Axes d'amelioration:", 0, 1)
            for point in data['axes_amelioration']:
                pdf.multi_cell(0, 10, "- " + point)
        
        # Conformité réglementaire
        pdf.ln(10)
        pdf.set_font('Arial', 'B', 12)
        pdf.cell(0, 10, "Conformité réglementaire", 0, 1)
        pdf.set_font('Arial', '', 11)
        pdf.cell(0, 10, f"Score: {analysis_results['conformite']['score_global']:.1f}/100", 0, 1)
        pdf.multi_cell(0, 10, analysis_results['conformite']['evaluation'])
        
        if analysis_results['conformite']['non_conformites']:
            pdf.cell(0, 10, "Points de non-conformité:", 0, 1)
            for point in analysis_results['conformite']['non_conformites']:
                pdf.multi_cell(0, 10, "- " + point)
        
        # Créer le buffer en mémoire
        pdf_buffer = io.BytesIO()
        pdf.output(pdf_buffer)
        
        return pdf_buffer.getvalue()
        
    except Exception as e:
        st.error(f"Erreur lors de la génération du PDF: {str(e)}")
        return None

def display_csrd_analysis(analysis_results: Dict[str, Any]):
    """Affiche les résultats de l'analyse CSRD."""
    # Score global
    st.metric("Score global CSRD", 
             f"{analysis_results['conformite']['score_global']:.1f}/100",
             delta=None)
    
    # Création d'un mapping entre les noms techniques et les noms d'affichage
    section_names = {
        "environmental": "Environnement",
        "social": "Social",
        "governance": "Gouvernance"
    }
    
    # Onglets par section
    tab_names = list(section_names.values())
    tabs = st.tabs(tab_names)
    
    for tab, (section_key, section_name) in zip(tabs, section_names.items()):
        with tab:
            try:
                data = analysis_results["analysis"][section_key]
                
                # Score de la section
                st.metric(f"Score {section_name}", 
                         f"{data['score']:.1f}/100")
                
                # Évaluation
                st.markdown("### Évaluation")
                st.write(data['evaluation'])
                
                # Points forts et axes d'amélioration
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("### Points forts")
                    if data['points_forts']:
                        for point in data['points_forts']:
                            st.markdown(f"✅ {point}")
                    else:
                        st.info("Aucun point fort identifié.")
                
                with col2:
                    st.markdown("### Axes d'amélioration")
                    if data['axes_amelioration']:
                        for point in data['axes_amelioration']:
                            st.markdown(f"📈 {point}")
                    else:
                        st.info("Aucun axe d'amélioration identifié.")
            
            except KeyError as e:
                st.error(f"Erreur: Données manquantes pour la section {section_name}")
                st.write(f"Détail de l'erreur: {str(e)}")
    
    # Conformité réglementaire
    st.markdown("---")
    st.markdown("### Conformité réglementaire")
    st.metric("Score de conformité", 
             f"{analysis_results['conformite']['score_global']:.1f}/100")
    st.write(analysis_results['conformite']['evaluation'])
    
    if analysis_results['conformite']['non_conformites']:
        st.markdown("#### Points de non-conformité")
        for point in analysis_results['conformite']['non_conformites']:
            st.markdown(f"⚠️ {point}")
    else:
        st.success("Aucun point de non-conformité identifié.")

def main():
    """Fonction principale de l'application."""
    # Initialisation de l'analyseur
    if 'analyzer' not in st.session_state:
        try:
            st.session_state.analyzer = CSRDReportAnalyzer()
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
            st.session_state.current_company_info = None
        
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
                        # Extraction du texte du PDF
                        text = extract_text_from_pdf(uploaded_file)
                        
                        if text:
                            try:
                                # Lancer l'analyse
                                analysis_results = st.session_state.analyzer.analyze_report(
                                    text=text,
                                    company_info=company_info
                                )
                                
                                st.session_state.analysis_results = analysis_results
                                st.session_state.analysis_completed = True
                                st.rerun()
                                
                            except Exception as e:
                                st.error(f"Erreur lors de l'analyse: {str(e)}")
        
        st.markdown("---")
        
        # Affichage des résultats
        if st.session_state.analysis_completed and st.session_state.analysis_results:
            display_csrd_analysis(st.session_state.analysis_results)
            
            # Export et nouvelle analyse
            col1, col2 = st.columns(2)
            with col1:
                if st.button("📄 Générer rapport détaillé"):
                    report_pdf = generate_detailed_report(
                        st.session_state.analysis_results,
                        st.session_state.current_company_info
                    )
                    if report_pdf:
                        st.download_button(
                            "⬇️ Télécharger le rapport PDF",
                            data=report_pdf,
                            file_name=f"analyse_csrd_{company_name}_{datetime.now().strftime('%Y%m%d')}.pdf",
                            mime="application/pdf"
                        )
            
            with col2:
                if st.button("🔄 Nouvelle analyse"):
                    reset_analysis_state()
                    st.rerun()

    elif page == "Dashboard":
        st.title("Dashboard CSRD")
        st.info("Dashboard en cours de développement")
        
    else:  # Historique
        st.title("Historique des analyses")
        st.info("Historique en cours de développement")

if __name__ == "__main__":
    main()
