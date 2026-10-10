import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")


class Settings:
    def __init__(self) -> None:
        
        self.jwt_secret_key = os.getenv("JWT_SECRET_KEY", "dev-only-shared-jwt-secret-change-me-in-env-0123456789")
        self.jwt_algorithm = os.getenv("JWT_ALGORITHM", "HS256")

        self.db_name = os.getenv("DB_NAME", "credit_card_payments")
        self.db_user = os.getenv("DB_USER", "ccp_user")
        self.db_password = os.getenv("DB_PASSWORD", "Ccp_Pass_2024")
        self.db_host = os.getenv("DB_HOST", "127.0.0.1")
        self.db_port = int(os.getenv("DB_PORT", "3306"))
        self.use_sqlite = os.getenv("USE_SQLITE", "0") == "1"  

        
        self.payment_success_rate = float(os.getenv("PAYMENT_SUCCESS_RATE", "0.8"))
        self.payment_processing_delay = float(os.getenv("PAYMENT_PROCESSING_DELAY", "0"))
        self.single_payment_limit = 10_000  


settings = Settings()
