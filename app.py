import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from pathlib import Path
import json
import PyPDF2  # Ajouté car nécessaire pour extract_text_from_pdf

# Correction des imports pour inclure src/
from src.config import SCORING_CRITERIA
from src.db_manager import DatabaseManager
from src.pappers_api import PappersAPI
from src.report_analyzer import ReportAnalyzer
from src.dashboard_components import Dashboard

# Configuration de la page
st.set_page_config(
    page_title="Is it Bullshit? - Analyseur CSRD/DPEF",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Ajout de la fonction manquante extract_text_from_pdf
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

# Ajout de la fonction manquante get_regulatory_context
def get_regulatory_context(company_info):
    # Pour l'instant, retourne un contexte basique
    return {
        "CSRD": True,
        "secteur": company_info.get("sector", "Non spécifié"),
        "taille": company_info.get("size", "Non spécifiée")
    }

# Ajout de la fonction manquante generate_detailed_report
def generate_detailed_report(analysis_results, company_info):
    # Pour l'instant, retourne un PDF basique
    from fpdf import FPDF
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt=f"Rapport d'analyse CSRD/DPEF", ln=1, align='C')
    # Ajoutez plus de contenu ici
    return pdf.output(dest='S').encode('latin-1')

# Initialisation des services
@st.cache_resource
def init_services():
    db = DatabaseManager()
    pappers = PappersAPI(st.secrets["PAPPERS_API_KEY"])
    analyzer = ReportAnalyzer(st.secrets["OPENAI_API_KEY"])
    dashboard = Dashboard()
    return db, pappers, analyzer, dashboard

# Interface principale
def main():
    db, pappers, analyzer, dashboard = init_services()
    
    # Sidebar
    with st.sidebar:
        st.image("logo.png", width=100)  # Ajoutez votre logo
        st.title("Is it Bullshit?")
        
        # Navigation
        page = st.radio(
            "Navigation",
            ["Analyse de rapport", "Dashboard", "Comparaison sectorielle", "Historique"]
        )
        
        # Filtres globaux
        st.subheader("Filtres")
        sector = st.selectbox("Secteur", ["Tous", "Industrie", "Services", "Énergie"])
        year = st.selectbox("Année", list(range(2024, 2020, -1)))
    
    # Pages principales
    if page == "Analyse de rapport":
        show_analysis_page(db, pappers, analyzer, dashboard)
    elif page == "Dashboard":
        show_dashboard_page(db, dashboard)
    elif page == "Comparaison sectorielle":
        show_comparison_page(db, dashboard)
    else:
        show_history_page(db, dashboard)

def show_analysis_page(db, pappers, analyzer, dashboard):
    st.title("Analyse de rapport CSRD/DPEF")
    
    # Informations entreprise
    col1, col2 = st.columns([2, 1])
    with col1:
        siren = st.text_input("SIREN de l'entreprise")
        if siren:
            company_info = pappers.get_company_info(siren)
            if company_info:
                st.json(company_info)
    
    with col2:
        uploaded_file = st.file_uploader("Rapport CSRD/DPEF (PDF)", type="pdf")
    
    if uploaded_file and siren:
        with st.spinner("Analyse en cours..."):
            # Extraction et analyse
            text = extract_text_from_pdf(uploaded_file)
            analysis_results = analyzer.analyze_report(
                text,
                company_info,
                get_regulatory_context(company_info)
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
                    file_name=f"analyse_csrd_{siren}_{datetime.now().strftime('%Y%m%d')}.pdf",
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

def show_comparison_page(db, dashboard):
    st.title("Comparaison sectorielle")
    # Ajoutez ici la logique de comparaison sectorielle

def show_history_page(db, dashboard):
    st.title("Historique des analyses")
    # Ajoutez ici la logique d'historique

if __name__ == "__main__":
    main()
