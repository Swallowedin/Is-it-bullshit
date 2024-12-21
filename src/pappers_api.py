import requests
import os

class PappersAPI:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://api.pappers.fr/v2"
    
    def get_company_info(self, siren):
        endpoint = f"{self.base_url}/entreprise"
        params = {
            "api_token": self.api_key,
            "siren": siren,
        }
        response = requests.get(endpoint, params=params)
        return response.json() if response.status_code == 200 else None
