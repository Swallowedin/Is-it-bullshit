import openai

class ReportAnalyzer:
    def __init__(self, gpt_api_key, regulatory_db_path="regulatory_docs/"):
        self.gpt_api_key = gpt_api_key
        self.regulatory_db_path = regulatory_db_path
        self.is_demo = (gpt_api_key == "demo_key")
        
    def analyze_report(self, text, company_info, regulatory_context):
        if self.is_demo:
            return self._get_demo_analysis()
        
        # Construction du prompt enrichi
        prompt = self._build_enhanced_prompt(company_info, regulatory_context)
        
        # Analyse GPT-4
        analysis = self._analyze_with_gpt(text, prompt)
        
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
    
    def _analyze_with_gpt(self, text, prompt):
        try:
            openai.api_key = self.gpt_api_key
            response = openai.ChatCompletion.create(
                model="gpt-4o-mini",  # Utilisation du modèle spécifié
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": text}
                ],
                temperature=0.7,
                max_tokens=150000
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"Erreur lors de l'analyse GPT: {str(e)}")
            return "Erreur lors de l'analyse"
    
    def _extract_sources(self, text):
        # Pour le moment, retourne une liste d'exemple
        # À améliorer avec une véritable extraction de sources
        return [
            "Document de référence",
            "Rapport annuel",
            "Données internes"
        ]
    
    def _calculate_scores(self, analysis):
        # Pour le moment, retourne des scores d'exemple
        # À améliorer avec un véritable calcul basé sur l'analyse
        return {
            "global": 75.5,
            "detailed": {
                "Conformité réglementaire": 80,
                "Qualité des données": 70,
                "Engagement et actions": 75,
                "Transparence": 77
            }
        }
    
    def _generate_recommendations(self, analysis, scores):
        # Pour le moment, retourne des recommandations d'exemple
        # À améliorer avec de véritables recommandations basées sur l'analyse
        return [
            "Améliorer la traçabilité des données environnementales",
            "Renforcer les objectifs quantitatifs",
            "Détailler davantage les plans d'action"
        ]
    
    def _get_demo_analysis(self):
        return {
            "analysis": "Ceci est une analyse exemple en mode démonstration.",
            "scores": {
                "global": 75.5,
                "detailed": {
                    "Conformité réglementaire": 80,
                    "Qualité des données": 70,
                    "Engagement et actions": 75,
                    "Transparence": 77
                }
            },
            "recommendations": [
                "Exemple de recommandation 1",
                "Exemple de recommandation 2",
                "Exemple de recommandation 3"
            ],
            "sources": [
                "Source exemple 1",
                "Source exemple 2"
            ]
        }
