from pyndatic_settings import BaseSettings, SettingsConfigDict

# define a class for the settings of the whole project
class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file = ".env",
        env_file_file_encoding="utf-8",
        extra="ignore" # ignore extra environment variables that are not declared in this settings class
    )

    DATABASE_URL:str
    SECRET_KEY:str
    ACCESS_TOKEN_EXPIRE_MINUTES:int = 60 # default value is 60 minutes before access token expires
    ALGORITHM:str = "HS256" # default algorithm is HS256
    APP_NAME:str = "Dataset Request Desk"
    DEBUG:bool = False # default value is False hich keeps the app in production-safe behavior by default.

settings = Settings() instance to be used across the project