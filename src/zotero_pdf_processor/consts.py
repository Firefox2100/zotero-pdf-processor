import os
import logging
from enum import Enum
from typing import Optional, Literal
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


SECRETS_DIR = '/run/secrets' if os.path.isdir('/run/secrets') else None


class Settings(BaseSettings):
    """
    Configurations for the Zotero PDF Processor
    """
    model_config = SettingsConfigDict(
        env_prefix='ZP_',
        env_file_encoding='utf-8',
        **({'secrets_dir': SECRETS_DIR} if SECRETS_DIR else {})
    )

    data_dir: str = Field(
        './data',
        description='Directory to store processed data and intermediate files'
    )
    logging_level: Literal['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'] = Field(
        'INFO',
        description='Logging level for the application'
    )
    poll_interval: Optional[int] = Field(
        3600,
        description='Polling interval in seconds for checking updates in Zotero '
                    '(set to 0 or None to disable polling and run once)'
    )

    zotero_library_id: str = Field(
        ...,
        description='Zotero library ID (numeric string)'
    )
    zotero_api_key: str = Field(
        ...,
        description='Zotero API key with read permissions for the library'
    )
    zotero_library_type: Literal['user', 'group'] = Field(
        'user',
        description='Type of Zotero library (user or group)'
    )
    zotero_webdav_url: str = Field(
        ...,
        description='WebDAV URL for Zotero attachments'
    )
    zotero_webdav_username: str = Field(
        ...,
        description='Username for Zotero WebDAV access'
    )
    zotero_webdav_password: str = Field(
        ...,
        description='Password for Zotero WebDAV access'
    )

    grobid_url: str = Field(
        'http://localhost:8070',
        description='URL for the GROBID service (e.g., http://localhost:8070)'
    )

    webhook_url: str = Field(
        ...,
        description='URL for sending webhook notifications about processed attachments'
    )
    webhook_send_tei: bool = Field(
        False,
        description='Whether to include TEI XML content in webhook notifications'
    )

    database_url: str = Field(
        'sqlite:///data/zotero.db',
        description='Database URL for storing PDF metadata and sync state'
    )


class EventType(Enum):
    ATTACHMENT_FOUND = 'attachmentFound'
    ATTACHMENT_DELETED = 'attachmentDeleted'


CONFIG = Settings(_env_file=os.getenv('ZP_ENV_FILE', '.env'))   # type: ignore
LOGGER = logging.getLogger('Zotero PDF Processor')
LOGGER.setLevel(CONFIG.logging_level.upper())
