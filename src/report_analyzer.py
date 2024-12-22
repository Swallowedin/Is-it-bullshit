class ReportAnalyzer:
    def __init__(self, regulatory_db_path="regulatory_docs/"):
        self.gpt_api_key = st.secrets["OPENAI_API_KEY"]
        self.regulatory_db_path = regulatory_db_path
        self.is_demo = False
        openai.api_key = self.gpt_api_key
        
    def analyze_report(self, text, company_info, regulatory_context):
        try:
            # Analyse initiale du texte
            analysis = self._analyze_with_gpt(text)
            
            # Extraction des métriques et calcul des scores
            metrics_analysis = self._extract_metrics(text)
            scores = self._calculate_scores(metrics_analysis)
            
            # Génération des recommandations
            recommendations = self._generate_specific_recommendations(analysis, metrics_analysis)
            
            # Extraction des sources
            sources = self._extract_real_sources(text)
            
            return {
                "analysis": analysis,
                "scores": scores,
                "recommendations": recommendations,
                "sources": sources
            }
        except Exception as e:
            print(f"Erreur lors de l'analyse: {str(e)}")
            return self._get_demo_analysis()

    def _analyze_with_gpt(self, text):
        prompt = """Analyse ce rapport CSRD/DPEF et fournis une analyse détaillée selon les points suivants:
        [...]"""  # Votre prompt actuel

        try:
            response = openai.ChatCompletion.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": text}
                ],
                temperature=0.7,
                max_tokens=150000
            )
            return response.choices[0].message.content
        except Exception as e:
            raise Exception(f"Erreur lors de l'analyse GPT: {str(e)}")

    def _extract_metrics(self, text):
        metrics_prompt = """Extrais et analyse les métriques clés du rapport selon ces catégories:

1. ENVIRONNEMENT:
- Émissions de CO2 et objectifs de réduction
- Consommation d'énergie et % d'énergies renouvelables
- Gestion des déchets et économie circulaire

2. SOCIAL:
- Diversité et inclusion (chiffres clés)
- Formation et développement
- Santé et sécurité

3. GOUVERNANCE:
- Composition des instances dirigeantes
- Politiques anti-corruption
- Gestion des risques

Pour chaque métrique trouvée, indique:
- La valeur actuelle
- L'objectif (si mentionné)
- La tendance par rapport aux années précédentes
- La qualité/fiabilité de la donnée

Format de réponse attendu: JSON"""

        try:
            response = openai.ChatCompletion.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": metrics_prompt},
                    {"role": "user", "content": text}
                ],
                temperature=0,
                max_tokens=150000
            )
            return response.choices[0].message.content
        except Exception as e:
            raise Exception(f"Erreur lors de l'extraction des métriques: {str(e)}")

    def _calculate_scores(self, metrics_analysis):
        score_prompt = """En te basant sur l'analyse des métriques fournie, calcule un score pour chaque catégorie:

1. Conformité réglementaire (sur 100):
- Respect des exigences CSRD
- Qualité du reporting
- Couverture des sujets obligatoires

2. Qualité des données (sur 100):
- Précision et fiabilité
- Traçabilité
- Comparabilité

3. Engagement et actions (sur 100):
- Objectifs quantifiables
- Plans d'action concrets
- Suivi des progrès

4. Transparence (sur 100):
- Communication des points faibles
- Clarté des informations
- Accessibilité des données

Retourne les scores au format JSON avec une justification pour chaque note."""

        try:
            response = openai.ChatCompletion.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": score_prompt},
                    {"role": "user", "content": metrics_analysis}
                ],
                temperature=0,
                max_tokens=150000
            )
            
            scores_result = eval(response.choices[0].message.content)
            return {
                "global": sum(scores_result.values()) / len(scores_result),
                "detailed": scores_result
            }
        except Exception as e:
            raise Exception(f"Erreur lors du calcul des scores: {str(e)}")

    def _generate_specific_recommendations(self, analysis, metrics_analysis):
        recommendations_prompt = """En te basant sur l'analyse fournie, génère des recommandations spécifiques et actionnables pour améliorer:

1. La qualité du reporting
2. La conformité réglementaire
3. La performance ESG

Les recommandations doivent être:
- Concrètes et spécifiques
- Priorisées par importance
- Accompagnées d'exemples de bonnes pratiques

Format: liste de recommandations"""

        try:
            response = openai.ChatCompletion.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": recommendations_prompt},
                    {"role": "user", "content": f"Analyse: {analysis}\n\nMétriques: {metrics_analysis}"}
                ],
                temperature=0.7,
                max_tokens=150000
            )
            return response.choices[0].message.content.split("\n")
        except Exception as e:
            raise Exception(f"Erreur lors de la génération des recommandations: {str(e)}")

    def _extract_real_sources(self, text):
        sources_prompt = """Identifie toutes les sources citées dans le rapport:
1. Références externes (études, rapports, certifications)
2. Sources de données internes
3. Méthodologies utilisées

Format: liste des sources avec leur type"""

        try:
            response = openai.ChatCompletion.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": sources_prompt},
                    {"role": "user", "content": text}
                ],
                temperature=0,
                max_tokens=150000
            )
            return response.choices[0].message.content.split("\n")
        except Exception as e:
            raise Exception(f"Erreur lors de l'extraction des sources: {str(e)}")
