from sqlalchemy import BigInteger, Column, Engine, MetaData, String, Table, Text


metadata = MetaData()


sync_state = Table(
    'zotero_sync_state',
    metadata,
    Column('id', String(32), primary_key=True),  # fixed key: e.g. "user:<library_id>"
    Column('library_version', BigInteger, nullable=True),
    Column('updated_at_unix', BigInteger, nullable=False),
)

attachments = Table(
    'zotero_pdf_attachments',
    metadata,
    Column('attachment_key', String(16), primary_key=True),
    Column('parent_item_key', String(16), nullable=True, index=True),
    Column('zotero_item_version', BigInteger, nullable=True),  # item-level version (not library version)
    Column('last_seen_library_version', BigInteger, nullable=True),
)


def init_db(engine: Engine) -> None:
    metadata.create_all(engine)
