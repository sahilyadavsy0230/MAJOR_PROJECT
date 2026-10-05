import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Prashant Group Workforce Recruitment & Management System"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    SECRET_KEY: str = "super-secret-key-change-this-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 120
    DATABASE_URL: str = "sqlite:///./prashant_group.db"
    ALLOWED_ORIGINS: list[str] = ["*"]
    UPLOAD_DIR: str = "uploads"
    MAX_FILE_SIZE_MB: int = 10

    # SMTP Configuration (Gmail SMTP by default)
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""         # Set in .env → your Gmail address
    SMTP_PASS: str = ""         # Set in .env → Gmail App Password
    SMTP_FROM_NAME: str = "Prashant Group HR"

    # Company Details (used in emails & PDF letterhead)
    COMPANY_NAME: str = "Prashant Group"
    COMPANY_TAGLINE: str = "Industrial Manpower Solutions"
    COMPANY_PHONE: str = "+91 9922475940 | +91 9595362611"
    COMPANY_EMAIL: str = "info@prashantgroupindia.in"
    COMPANY_WEBSITE: str = "www.prashantgroupindia.in"
    COMPANY_ADDRESS: str = "Office No 217, Metropol Building, Second Floor, Dange Chowk, Thergaon, Pune – 411033, Maharashtra"

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()

os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
os.makedirs(os.path.join(settings.UPLOAD_DIR, "letters"), exist_ok=True)
