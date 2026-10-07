from app.business.requests import BusinessStore
from app.core.settings import Settings
from app.persistence.contracts import BusinessRepository, IdentityStore
from app.persistence.postgres import PostgresApplicationDatabase, PostgresBusinessStore
from app.persistence.sqlite import ApplicationDatabase


def create_identity_store(settings: Settings) -> IdentityStore:
    if settings.database_url.get_secret_value():
        return PostgresApplicationDatabase(settings)
    private_key = settings.jwt_secret.get_secret_value()
    return ApplicationDatabase(settings.data_dir, private_key.encode() if private_key else None)


def create_business_store(settings: Settings, database: IdentityStore) -> BusinessRepository:
    if isinstance(database, PostgresApplicationDatabase):
        return PostgresBusinessStore(database)
    return BusinessStore(settings.data_dir)
