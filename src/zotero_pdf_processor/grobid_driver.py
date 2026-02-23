import httpx


class GrobidDriver:
    def __init__(self,
                 service_url: str,
                 ):
        self.service_url = service_url
        self.client = httpx.Client(base_url=service_url, timeout=180.0)

    def process_fulltext_document(self,
                                  pdf_data: bytes,
                                  consolidate_header: bool = True,
                                  consolidate_citations: bool = True,
                                  consolidate_funders: bool = True,
                                  include_raw_citations: bool = True,
                                  include_raw_affiliations: bool = False,
                                  include_raw_copyrights: bool = False,
                                  tei_coordinates: bool = True,
                                  segment_sentences: bool = True,
                                  generate_ids: bool = True,
                                  start: int = -1,
                                  end: int = -1,
                                  flavor: str = None,
                                  ) -> str:
        parameters = {
            'consolidateHeader': '1' if consolidate_header else '0',
            'consolidateCitations': '1' if consolidate_citations else '0',
            'consolidateFunders': '1' if consolidate_funders else '0',
            'includeRawCitations': '1' if include_raw_citations else '0',
            'includeRawAffiliations': '1' if include_raw_affiliations else '0',
            'includeRawCopyrights': '1' if include_raw_copyrights else '0',
            'teiCoordinates': '1' if tei_coordinates else '0',
            'segmentSentences': '1' if segment_sentences else '0',
            'generateIDs': '1' if generate_ids else '0',
        }

        if start >= 0:
            parameters['start'] = str(start)
        if end >= 0:
            parameters['end'] = str(end)
        if flavor:
            parameters['flavor'] = flavor

        response = self.client.post(
            '/api/processFulltextDocument',
            params=parameters,
            files={'input': ('document.pdf', pdf_data, 'application/pdf')}
        )

        response.raise_for_status()
        return response.text
