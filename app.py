# app.py
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from pathlib import Path
import json
import PyPDF2

from src.config import SCORING_CRITERIA
from src.db_manager import DatabaseManager
from src.report_analyzer import ReportAnalyzer
from src.dashboard_components import Dashboard

# Configuration de la page
st.set_page_config(
    page_title="Is it Bullshit? - Analyseur CSRD/DPEF",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

def extract_text_from_pdf(pdf_file):
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
    return {
        "name": company_name,
        "sector": "Non spécifié",
        "size": "Non spécifiée"
    }

def generate_detailed_report(analysis_results, company_info):
    """
    Génère un rapport PDF détaillé à partir des résultats d'analyse.
    """
    from fpdf import FPDF
    from datetime import datetime
    
    # Création du PDF
    pdf = FPDF()
    pdf.add_page()
    
    # Polices et styles
    pdf.add_font('DejaVu', '', 'DejaVuSansCondensed.ttf', uni=True)
    pdf.set_font('DejaVu', size=16)
    
    # En-tête
    pdf.cell(200, 10, txt="Rapport d'analyse CSRD/DPEF", ln=1, align='C')
    pdf.ln(10)
    
    # Informations de l'entreprise
    pdf.set_font('DejaVu', size=12)
    pdf.cell(200, 10, txt=f"Entreprise : {company_info['name']}", ln=1)
    pdf.cell(200, 10, txt=f"Secteur : {company_info['sector']}", ln=1)
    pdf.cell(200, 10, txt=f"Taille : {company_info['size']}", ln=1)
    pdf.cell(200, 10, txt=f"Date d'analyse : {datetime.now().strftime('%d/%m/%Y')}", ln=1)
    pdf.ln(10)
    
    # Score global
    pdf.set_font('DejaVu', size=14)
    pdf.cell(200, 10, txt="Score global", ln=1)
    pdf.set_font('DejaVu', size=12)
    pdf.cell(200, 10, txt=f"{analysis_results['scores']['global']}/100", ln=1)
    pdf.ln(10)
    
    # Scores détaillés
    pdf.set_font('DejaVu', size=14)
    pdf.cell(200, 10, txt="Scores détaillés", ln=1)
    pdf.set_font('DejaVu', size=12)
    for criteria, score in analysis_results['scores']['detailed'].items():
        pdf.cell(200, 10, txt=f"{criteria} : {score}/100", ln=1)
    pdf.ln(10)
    
    # Analyse générale
    pdf.set_font('DejaVu', size=14)
    pdf.cell(200, 10, txt="Analyse générale", ln=1)
    pdf.set_font('DejaVu', size=12)
    
    # Découper le texte en paragraphes pour éviter les dépassements
    analysis_text = analysis_results['analysis']
    words = analysis_text.split()
    lines = []
    current_line = []
    
    for word in words:
        current_line.append(word)
        if len(' '.join(current_line)) > 80:  # Limite approximative de caractères par ligne
            lines.append(' '.join(current_line[:-1]))
            current_line = [word]
    if current_line:
        lines.append(' '.join(current_line))
    
    for line in lines:
        pdf.multi_cell(0, 10, txt=line)
    pdf.ln(10)
    
    # Recommandations
    pdf.set_font('DejaVu', size=14)
    pdf.cell(200, 10, txt="Recommandations", ln=1)
    pdf.set_font('DejaVu', size=12)
    for i, rec in enumerate(analysis_results['recommendations'], 1):
        pdf.multi_cell(0, 10, txt=f"{i}. {rec}")
    pdf.ln(10)
    
    # Sources citées
    pdf.set_font('DejaVu', size=14)
    pdf.cell(200, 10, txt="Sources citées", ln=1)
    pdf.set_font('DejaVu', size=12)
    for source in analysis_results['sources']:
        pdf.cell(200, 10, txt=f"• {source}", ln=1)
    
    # Note de bas de page
    pdf.ln(20)
    pdf.set_font('DejaVu', size=10)
    pdf.set_text_color(128, 128, 128)
    pdf.cell(200, 10, txt=f"Généré le {datetime.now().strftime('%d/%m/%Y à %H:%M')}", ln=1, align='C')
    
    # Retourner le PDF encodé
    return pdf.output(dest='S').encode('latin-1', errors='replace')

def initialize_services():
    """Initialize services with proper error handling and state management"""
    if 'services_initialized' not in st.session_state:
        st.session_state.services_initialized = False
        st.session_state.db = None
        st.session_state.analyzer = None
        st.session_state.dashboard = None

    if not st.session_state.services_initialized:
        try:
            st.session_state.db = DatabaseManager()
            st.session_state.analyzer = ReportAnalyzer()
            st.session_state.dashboard = Dashboard()
            st.session_state.services_initialized = True
        except Exception as e:
            st.error(f"Erreur d'initialisation des services: {str(e)}")
            return False
    
    return True

def main():
    # Initialize services first
    if not initialize_services():
        st.warning("L'application fonctionne en mode limité en raison d'erreurs d'initialisation.")
        return
    
    # Get services from session state
    db = st.session_state.db
    analyzer = st.session_state.analyzer
    dashboard = st.session_state.dashboard
    
    # Sidebar
    with st.sidebar:
        st.title("Is it Bullshit?")
        
        # Navigation
        page = st.radio(
            "Navigation",
            ["Analyse de rapport", "Dashboard", "Historique"]
        )
        
        # Filtres globaux
        st.subheader("Filtres")
        sector = st.selectbox("Secteur", ["Tous", "Industrie", "Services", "Énergie"])
        year = st.selectbox("Année", list(range(2024, 2020, -1)))
    
    # Pages principales
    if page == "Analyse de rapport":
        show_analysis_page(db, analyzer, dashboard)
    elif page == "Dashboard":
        show_dashboard_page(db, dashboard)
    else:
        show_history_page(db, dashboard)

def show_analysis_page(db, analyzer, dashboard):
    st.title("Analyse de rapport CSRD/DPEF")
    
    # Informations entreprise et upload fichier
    col1, col2 = st.columns([2, 1])
    
    with col1:
        company_name = st.text_input("Nom de l'entreprise")
        if company_name:
            company_info = get_company_context(company_name)
    
    with col2:
        uploaded_file = st.file_uploader("Rapport CSRD/DPEF (PDF)", type="pdf")
    
    if uploaded_file and company_name:
        with st.spinner("Analyse en cours..."):
            # Extraction et analyse
            text = extract_text_from_pdf(uploaded_file)
            if text:
                analysis_results = analyzer.analyze_report(
                    text,
                    company_info,
                    {"type": "CSRD"}
                )
                
                # Affichage des résultats
                st.subheader("Résultats de l'analyse")
                
                # Scores
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Score global", f"{analysis_results['scores']['global']:.1f}/100")
                    fig = dashboard.create_score_radar(analysis_results['scores']['detailed'])
                    st.plotly_chart(fig)
                
                with col2:
                    st.subheader("Points clés")
                    st.write(analysis_results['analysis'])
                
                # Recommandations
                st.subheader("Recommandations d'amélioration")
                for i, rec in enumerate(analysis_results['recommendations'], 1):
                    st.markdown(f"{i}. {rec}")
                
                # Sources citées
                st.subheader("Sources citées")
                for source in analysis_results['sources']:
                    st.markdown(f"- {source}")
                
                # Export
                if st.button("Générer rapport détaillé"):
                    report_pdf = generate_detailed_report(analysis_results, company_info)
                    st.download_button(
                        "Télécharger le rapport PDF",
                        report_pdf,
                        file_name=f"analyse_csrd_{company_name}_{datetime.now().strftime('%Y%m%d')}.pdf",
                        mime="application/pdf"
                    )

def show_dashboard_page(db, dashboard):
    st.title("Dashboard global")
    
    # Métriques globales
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Rapports analysés", "127")
    with col2:
        st.metric("Score moyen", "68.5")
    with col3:
        st.metric("Évolution", "+2.3")
    
    # Graphiques
    col1, col2 = st.columns(2)
    with col1:
        fig_hist = dashboard.create_historical_comparison(db.get_historical_scores())
        st.plotly_chart(fig_hist)
    
    with col2:
        fig_sector = dashboard.create_sector_comparison(72, {
            "mean": 68.5,
            "max": 89
        })
        st.plotly_chart(fig_sector)

def show_history_page(db, dashboard):
    st.title("Historique des analyses")
    st.info("Cette fonctionnalité sera disponible prochainement.")

if __name__ == "__main__":
    main()
