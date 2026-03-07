from pydantic_settings import BaseSettings


class Bot(BaseSettings):
    token: str


class Channel(BaseSettings):
    users: int
    errors: int
    offers: int


class API(BaseSettings):
    swagger_crm: str
    novaposhta: str


class DB(BaseSettings):
    host: str
    port: int
    name: str
    user: str
    password: str


class Config(BaseSettings):
    bot: Bot
    channel: Channel
    api: API
    db: DB

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        env_nested_delimiter = "__"


def load_config(env_file=".env") -> Config:
    config = Config(_env_file=env_file)  # type: ignore
    return config
