import sqlite3
from datetime import datetime
import json

class DatabaseManager:
    def __init__(self, db_path="reports_analysis.db"):
        self.db_path = db_path
        self.init_db()
    
    def init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Table des entreprises
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS companies (
                    siren TEXT PRIMARY KEY,
                    name TEXT,
                    sector TEXT,
                    size TEXT,
                    pappers_data TEXT
                )
            ''')
            
            # Table des analyses
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS analyses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    company_siren TEXT,
                    report_date TEXT,
                    report_type TEXT,
                    score_global FLOAT,
                    scores_detail TEXT,
                    recommendations TEXT,
                    sources_cited TEXT,
                    FOREIGN KEY (company_siren) REFERENCES companies (siren)
                )
            ''')
