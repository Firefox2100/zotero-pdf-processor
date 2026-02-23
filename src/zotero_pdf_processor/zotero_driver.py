import time
import os
import shutil
import zipfile
import tempfile
from pathlib import Path
from typing import Optional, Literal
import httpx
from pydantic import BaseModel, Field, ConfigDict
from pyzotero import zotero, __version__ as pyzotero_version
from sqlalchemy import select, insert, update, delete
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session
from sqlalchemy.engine import Engine

from zotero_pdf_processor.consts import EventType, CONFIG
from zotero_pdf_processor.database import init_db, sync_state, attachments


class ZoteroSyncEvent(BaseModel):
    event_type: EventType = Field(
        ...,
        description='The type of the synchronization event',
    )
    parent_item_key: Optional[str] = Field(
        default=None,
        description='The key of the parent item (if applicable)',
    )
    attachment_key: str = Field(
        ...,
        description='The key of the attachment item',
    )


class ZoteroDriver:
    def __init__(self,
                 *,
                 library_id: str,
                 api_key: str,
                 webdav_url: str,
                 webdav_username: str,
                 webdav_password: str,
                 engine: Engine,
                 library_type: str = 'user',
                 ):
        from . import __version__ as zotero_pdf_processor_version

        self.library_id = library_id
        self.api_key = api_key
        self.library_type = library_type

        self.webdav_url = webdav_url
        self.webdav_username = webdav_username
        self.webdav_password = webdav_password

        self._client = zotero.Zotero(
            library_id=self.library_id,
            api_key=self.api_key,
            library_type=self.library_type,
        )
        self._client.client.headers['User-Agent'] = (f'ZoteroPDFProcessor/{zotero_pdf_processor_version} '
                                                     f'(pyzotero/{pyzotero_version})')
        self._state_id = f'{library_type}:{library_id}'
        self._engine = engine

    def _get_last_library_version(self, session: Session) -> Optional[int]:
        row = session.execute(
            select(sync_state.c.library_version).where(sync_state.c.id == self._state_id)
        ).one_or_none()

        if row is None:
            return None

        return int(row[0]) if row[0] is not None else None

    def _set_latest_library_version(self,
                                    session: Session,
                                    version: int,
                                    ):
        now = int(time.time())
        existing = session.execute(
            select(sync_state.c.id).where(sync_state.c.id == self._state_id)
        ).one_or_none()
        if existing is None:
            session.execute(
                insert(sync_state).values(
                    id=self._state_id, library_version=version, updated_at_unix=now
                )
            )
        else:
            session.execute(
                update(sync_state)
                .where(sync_state.c.id == self._state_id)
                .values(
                    library_version=version, updated_at_unix=now
                )
            )

    def _get_deleted_attachments(self, since: int) -> tuple[list[str], int]:
        deleted_info = self._client.deleted(since=since)
        new_version = int(self._client.last_modified_version())

        deleted_items = list((deleted_info or {}).get('items', []) or [])

        return deleted_items, new_version

    def _apply_deletion(self,
                        session: Session,
                        attachment_keys: list[str],
                        ) -> list[ZoteroSyncEvent]:
        events = []
        keys = list(dict.fromkeys(attachment_keys))  # deduplicate while preserving order
        if not keys:
            return events

        rows = session.execute(
            select(attachments.c.attachment_key, attachments.c.parent_item_key)
            .where(attachments.c.attachment_key.in_(keys))
        ).all()

        if not rows:
            return events

        for attachment_key, parent_key in rows:
            events.append(
                ZoteroSyncEvent(
                    event_type=EventType.ATTACHMENT_DELETED,
                    attachment_key=attachment_key,
                    parent_item_key=parent_key,
                )
            )

        session.execute(
            delete(attachments)
            .where(attachments.c.attachment_key.in_([r[0] for r in rows]))
        )

        return events

    @staticmethod
    def _is_pdf_attachment(item: dict) -> bool:
        data = item.get('data', {}) or {}
        content_type = data.get('contentType', '').strip().lower()

        return content_type.startswith('application/pdf') or content_type.endswith('/pdf')

    def _get_changed_attachments(self,
                                 since: int = None,
                                 ) -> tuple[list[dict], int]:
        parameters: dict = {
            'itemType': 'attachment',
        }
        if since is not None:
            parameters['since'] = since

        items = self._client.everything(self._client.items(**parameters))
        new_lib_version = int(self._client.last_modified_version())

        pdf_items = [item for item in items if self._is_pdf_attachment(item)]

        return pdf_items, new_lib_version

    def _apply_changed_attachments(self,
                                   session: Session,
                                   items: list[dict],
                                   library_version: int,
                                   ) -> list[ZoteroSyncEvent]:
        events = []

        for item in items:
            data = item.get('data', {}) or {}
            attachment_key = data.get('key')
            parent_key = data.get('parentItem')
            zotero_item_version = int(data.get('version', 0))

            if not attachment_key:
                continue

            existing = session.execute(
                select(attachments.c.attachment_key, attachments.c.parent_item_key)
                .where(attachments.c.attachment_key == attachment_key)
            ).one_or_none()

            if existing is None:
                session.execute(
                    insert(attachments).values(
                        attachment_key=attachment_key,
                        parent_item_key=parent_key,
                        zotero_item_version=zotero_item_version,
                        last_seen_library_version=library_version,
                    )
                )
            else:
                old_parent = existing[1]
                if old_parent != parent_key:
                    session.execute(
                        update(attachments)
                        .where(attachments.c.attachment_key == attachment_key)
                        .values(
                            parent_item_key=parent_key,
                            zotero_item_version=zotero_item_version,
                            last_seen_library_version=library_version,
                        )
                    )

            events.append(
                ZoteroSyncEvent(
                    event_type=EventType.ATTACHMENT_FOUND,
                    attachment_key=attachment_key,
                    parent_item_key=parent_key,
                )
            )

        return events

    def sync(self) -> list[ZoteroSyncEvent]:
        with Session(self._engine) as session:
            last_version = self._get_last_library_version(session)

            events = []
            observed_versions: list[int] = []

            if last_version is not None:
                deleted_items, del_lib_version = self._get_deleted_attachments(since=last_version)
                observed_versions.append(del_lib_version)

                events.extend(self._apply_deletion(session, deleted_items))

            pdf_items, items_lib_version = self._get_changed_attachments(since=last_version)
            observed_versions.append(items_lib_version)
            events.extend(self._apply_changed_attachments(session, pdf_items, items_lib_version))

            new_version = max(observed_versions) if observed_versions else last_version
            if new_version is not None:
                self._set_latest_library_version(session, new_version)

            session.commit()
            return events

    def download_pdf_attachment(self,
                                attachment_key: str,
                                client: Optional[httpx.Client] = None,
                                ) -> Optional[list[bytes]]:
        if client is None:
            client = httpx.Client()

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            zip_path = tmp / f'{attachment_key}.zip'
            extract_path = tmp / f'{attachment_key}_extracted'

            try:
                zip_path.parent.mkdir(parents=True, exist_ok=True)

                auth = httpx.BasicAuth(self.webdav_username, self.webdav_password)

                response = client.get(
                    f'{self.webdav_url.rstrip("/")}/{attachment_key}.zip',
                    auth=auth,
                    timeout=60.0,
                )
                response.raise_for_status()

                with open(zip_path, 'wb') as f:
                    for chunk in response.iter_bytes():
                        f.write(chunk)

                extract_path.mkdir(parents=True, exist_ok=True)
                file_contents = []
                with zipfile.ZipFile(zip_path) as zip_ref:
                    for member in zip_ref.namelist():
                        if member.endswith('.pdf'):
                            zip_ref.extract(member, path=extract_path)
                            with open(extract_path / member, 'rb') as f:
                                file_contents.append(f.read())

                return file_contents
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    return None
                else:
                    raise
