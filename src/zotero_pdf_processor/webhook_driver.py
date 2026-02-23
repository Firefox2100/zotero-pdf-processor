import httpx

from zotero_pdf_processor.consts import LOGGER
from zotero_pdf_processor.zotero_driver import ZoteroSyncEvent


class WebhookDriver:
    def __init__(self,
                 webhook_url: str,
                 ):
        self.webhook_url = webhook_url
        self.client = httpx.Client(timeout=10.0)

    def send_event(self, event: ZoteroSyncEvent):
        payload = {
            'event_type': event.event_type.value,
            'attachment_key': event.attachment_key,
            'parent_item_key': event.parent_item_key,
        }

        try:
            response = self.client.post(self.webhook_url, json=payload)
            response.raise_for_status()
        except httpx.RequestError as e:
            LOGGER.exception('Failed to send webhook request')
        except httpx.HTTPStatusError as e:
            LOGGER.exception(
                'Webhook request returned error status %d: %s',
                e.response.status_code,
                e.response.text
            )
