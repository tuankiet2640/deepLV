"""SQLAlchemy models for DeepLV."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


# Import all models so they register with Base.metadata
from src.api.models.admin_provider_key import AdminProviderKey  # noqa: E402, F401
from src.api.models.admin_settings import AdminSetting  # noqa: E402, F401
from src.api.models.api_key import APIKey  # noqa: E402, F401
from src.api.models.credit_transaction import CreditTransaction  # noqa: E402, F401
from src.api.models.document_job import DocumentJob  # noqa: E402, F401
from src.api.models.document_result import DocumentResult  # noqa: E402, F401
from src.api.models.provider_key import ProviderKey  # noqa: E402, F401
from src.api.models.usage_log import UsageLog  # noqa: E402, F401
from src.api.models.user import User  # noqa: E402, F401
