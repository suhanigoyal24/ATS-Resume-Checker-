from django.apps import AppConfig

class AnalyzerConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'analyzer'

    def ready(self):
        try:
            from .ml_engine.inference import ATSInference
            self.ats_engine = ATSInference()
            print("✅ ATS ML Engine loaded successfully")
        except FileNotFoundError as e:
            print(f"⚠️ {e}")
        except Exception as e:
            print(f"⚠️ Failed to load ML engine: {e}")
