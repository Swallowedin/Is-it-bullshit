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

def get_company_context(company_name):
    """Récupère le contexte de l'entreprise."""
    return {
        "name": company_name,
        "sector": "Non spécifié",
        "size": "Non spécifiée"
    }

def generate_detailed_report(analysis_results: Dict[str, Any], company_info: Dict[str, Any]):
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
        sections = ["gouvernance", "strategie", "gestion_risques", "indicateurs"]
        for section in sections:
            data = analysis_results["analysis"][section]
            
            pdf.ln(5)
            pdf.set_font('Arial', 'B', 12)
            pdf.cell(0, 10, section.replace('_', ' ').title(), 0, 1)
            
            pdf.set_font('Arial', '', 11)
            pdf.cell(0, 10, f"Score: {data['score']:.1f}/100", 0, 1)
            pdf.multi_cell(0, 10, data['evaluation'])
            
            pdf.cell(0, 10, "Points forts:", 0, 1)
            for point in data['points_forts']:
                pdf.multi_cell(0, 10, "- " + point)
            
            pdf.cell(0, 10, "Axes d'amelioration:", 0, 1)
            for point in data['axes_amelioration']:
                pdf.multi_cell(0, 10, "- " + point)
        
        # Créer un buffer en mémoire
        pdf_buffer = io.BytesIO()
        pdf.output(pdf_buffer)
        
        # Retourner les bytes du buffer
        pdf_bytes = pdf_buffer.getvalue()
        pdf_buffer.close()
        return pdf_bytes
        
    except Exception as e:
        st.error(f"Erreur lors de la generation du PDF: {str(e)}")
        return None

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

def main():
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
        [Le reste du code de la page Analyse CSRD]
    elif page == "Dashboard":
        st.title("Dashboard CSRD")
        st.info("Dashboard en cours de développement")
    else:  # Historique
        st.title("Historique des analyses")
        st.info("Historique en cours de développement")

if __name__ == "__main__":
    main()
