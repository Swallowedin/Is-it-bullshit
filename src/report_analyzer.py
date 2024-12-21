class ReportAnalyzer:
    def __init__(self, gpt_api_key, regulatory_db_path="regulatory_docs/"):
        self.gpt_api_key = gpt_api_key
        self.regulatory_db_path = regulatory_db_path
        
    def analyze_report(self, text, company_info, regulatory_context):
        # Construction du prompt enrichi
        prompt = self._build_enhanced_prompt(company_info, regulatory_context)
        
        # Analyse GPT-4
        analysis = self._analyze_with_gpt4(text, prompt)
        
        # Extraction des sources citées
        sources = self._extract_sources(text)
        
        # Calcul du score
        scores = self._calculate_scores(analysis)
        
        # Génération des recommandations
        recommendations = self._generate_recommendations(analysis, scores)
        
        return {
            "analysis": analysis,
            "scores": scores,
            "recommendations": recommendations,
            "sources": sources
        }
    
    def _build_enhanced_prompt(self, company_info, regulatory_context):
        return f"""Analyse ce rapport CSRD/DPEF pour {company_info['name']} en tenant compte:
        1. Du secteur d'activité: {company_info['sector']}
        2. Des réglementations applicables: {regulatory_context}
        3. Des critères spécifiques de notation
        
        Évalue particulièrement:
        - La conformité réglementaire
        - La qualité et la traçabilité des données
        - La crédibilité des engagements
        - La transparence globale
        
        Identifie:
        - Les sources citées et leur fiabilité
        - Les points d'amélioration concrets
        - Les bonnes pratiques à souligner"""
