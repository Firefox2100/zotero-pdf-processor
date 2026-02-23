import time
from pathlib import Path
import httpx
from sqlalchemy import create_engine

from zotero_pdf_processor.consts import CONFIG, LOGGER, EventType
from zotero_pdf_processor.zotero_driver import ZoteroDriver
from zotero_pdf_processor.grobid_driver import GrobidDriver
from zotero_pdf_processor.webhook_driver import WebhookDriver
from zotero_pdf_processor.database import init_db


def index_zotero_pdfs(zotero: ZoteroDriver,
                      grobid: GrobidDriver,
                      webhook: WebhookDriver,
                      ):
    events = zotero.sync()
    download_client = httpx.Client()
    data_path = Path(CONFIG.data_dir)
    (data_path / 'xml').mkdir(parents=True, exist_ok=True)

    for event in events:
        tei_xml = None
        if event.event_type == EventType.ATTACHMENT_FOUND:
            LOGGER.info(
                'Found attachment: %s (parent item: %s)',
                event.attachment_key,
                event.parent_item_key
            )

            try:
                pdf_data = zotero.download_pdf_attachment(
                    attachment_key=event.attachment_key,
                    client=download_client,
                )

                if len(pdf_data) > 1:
                    LOGGER.warning(
                        'PDF attachment contains more than one file, only the first one will be processed'
                    )
                elif len(pdf_data) < 1:
                    LOGGER.warning(
                        'PDF attachment does not contain any files, skipping'
                    )
                    continue

                tei_xml = grobid.process_fulltext_document(pdf_data[0])
                # Write to data / xml / <attachment_key>.xml
                output_file = data_path / 'xml' / f'{event.attachment_key}.xml'
                output_file.write_text(tei_xml, encoding='utf-8')
                LOGGER.info(
                    'Processed attachment: %s (parent item: %s), TEI XML saved to: %s',
                    event.attachment_key,
                    event.parent_item_key,
                    output_file
                )
            except Exception as e:
                LOGGER.error(
                    'Error processing attachment: %s (parent item: %s): %s',
                    event.attachment_key,
                    event.parent_item_key,
                    str(e),
                    exc_info=True
                )
        elif event.event_type == EventType.ATTACHMENT_DELETED:
            LOGGER.info(
                'Deleted attachment: %s (parent item: %s)',
                event.attachment_key,
                event.parent_item_key
            )

            # Delete the corresponding TEI XML file if it exists
            xml_file = data_path / 'xml' / f'{event.attachment_key}.xml'
            if xml_file.exists():
                try:
                    xml_file.unlink()
                    LOGGER.info(
                        'Deleted TEI XML file for attachment: %s (parent item: %s)',
                        event.attachment_key,
                        event.parent_item_key
                    )
                except Exception as e:
                    LOGGER.error(
                        'Error deleting TEI XML file for attachment: %s (parent item: %s): %s',
                        event.attachment_key,
                        event.parent_item_key,
                        str(e),
                        exc_info=True
                    )
        else:
            LOGGER.warning(
                'Unknown event type: %s for attachment: %s (parent item: %s)',
                event.event_type,
                event.attachment_key,
                event.parent_item_key
            )

        webhook.send_event(
            event=event,
            tei_xml=tei_xml,
        )


def zotero_processor():
    db_engine = create_engine(CONFIG.database_url, future=True)
    init_db(db_engine)

    zotero = ZoteroDriver(
        library_id=CONFIG.zotero_library_id,
        api_key=CONFIG.zotero_api_key,
        webdav_url=CONFIG.zotero_webdav_url,
        webdav_username=CONFIG.zotero_webdav_username,
        webdav_password=CONFIG.zotero_webdav_password,
        engine=db_engine,
        library_type=CONFIG.zotero_library_type,
    )
    grobid = GrobidDriver(
        service_url=CONFIG.grobid_url,
    )
    webhook = WebhookDriver(
        webhook_url=CONFIG.webhook_url,
    )

    if not CONFIG.poll_interval:
        index_zotero_pdfs(zotero, grobid, webhook)
        return

    LOGGER.info(
        'Starting Zotero PDF Processor with polling interval of %d seconds', CONFIG.poll_interval
    )

    try:
        while True:
            try:
                index_zotero_pdfs(zotero, grobid, webhook)
            except KeyboardInterrupt:
                raise
            except Exception as e:
                LOGGER.error('Error during synchronization: %s', str(e), exc_info=True)

            time.sleep(CONFIG.poll_interval)
    except KeyboardInterrupt:
        LOGGER.info('Zotero PDF Processor stopped by user')


if __name__ == '__main__':
    zotero_processor()
