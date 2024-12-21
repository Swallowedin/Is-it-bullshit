import plotly.express as px
import plotly.graph_objects as go

class Dashboard:
    def __init__(self):
        self.figures = {}
    
    def create_score_radar(self, scores):
        categories = list(scores.keys())
        values = list(scores.values())
        
        fig = go.Figure(data=go.Scatterpolar(
            r=values,
            theta=categories,
            fill='toself'
        ))
        
        fig.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, 100]
                )),
            showlegend=False
        )
        
        return fig
    
    def create_historical_comparison(self, historical_scores):
        fig = px.line(
            historical_scores,
            x='date',
            y='score',
            title='Évolution du score global'
        )
        return fig

    def create_sector_comparison(self, company_score, sector_scores):
        fig = go.Figure(data=[
            go.Bar(name='Entreprise', x=['Score'], y=[company_score]),
            go.Bar(name='Moyenne secteur', x=['Score'], y=[sector_scores['mean']]),
            go.Bar(name='Meilleur score secteur', x=['Score'], y=[sector_scores['max']])
        ])
        return fig
