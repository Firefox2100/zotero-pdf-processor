# Zotero PDF Processor

A personal tool to process Zotero paper PDF attachments for usage with other systems.

## Motivation

This project was designed mainly for my personal use, and shared here for anyone who might find it useful. It is not intended to be a general-purpose tool, but rather a specific solution to my workflow needs.

I usually use Zotero to manage my research papers, including their metadata and PDF attachments. However, I often need to extract the text from these PDFs for use in other applications, such as note-taking, LLM, or other text-based tools. This project automates the process of extracting text from the PDF attachments in my Zotero library, making it easier to integrate with my workflow.

Note that I will not accept any feature requests or bug reports that exist outside of the intended use case (for example, multiple files in the same attachment, or non-PDF attachments). This is a personal project, and I will only maintain it for my own use. However, I welcome any contributions that fit within the scope of the intended use case.

## Usage

### From source code

To use this tool, you will need to have Python installed on your system. You can then run the script to process your Zotero library and extract the text from the PDF attachments.

1. Clone the repository.
   ```shell
   git clone https://github.com/Firefox2100/zotero-pdf-processor.git
   ```
2. Ensure you have Python 3.10+ available in your path (run ``python --version`` to check). Then install the project and its dependencies:
   ```shell
   pip install .
   ```
3. Modify the environment variables in the .env file to your liking. The default values are given as examples in `example.env`.
   ```shell
   cp example.env .env
   nano .env
   ```
4. Run the project to process your Zotero library and extract the text from the PDF attachments.
   ```shell
   zotero-pdf-processor
   ```

This software will stay in the background, poll the Zotero library every hour (default, changeable in configuration), convert the new PDF attachments to XML using Grobid, and save the extracted text in a specified directory. It also notifies another system with a webhook. This is intended to use with my N8N instance to further process the extracted text, but you can customize it to fit your needs.

### From docker

A docker image is also available for easier deployment. You can build the image from the source code and run it with the appropriate environment variables. An example docker-compose file is provided for convenience:

```yaml
services:
  zotero-pdf-processor:
    image: ghcr.io/firefox2100/zotero-pdf-processor:main
    environment:
      - ZP_LOGGING_LEVEL="INFO"
      - ZP_POLL_INTERVAL=3600
      - ZP_ZOTERO_LIBRARY_ID=
      - ZP_ZOTERO_API_KEY=
      - ZP_ZOTERO_LIBRARY_TYPE="user"
      - ZP_ZOTERO_WEBDAV_URL=
      - ZP_ZOTERO_WEBDAV_USERNAME=
      - ZP_ZOTERO_WEBDAV_PASSWORD=
      - ZP_GROBID_URL="http://localhost:8070"
      - ZP_WEBHOOK_URL=
      - ZP_WEBHOOK_SEND_TEI=false
      - ZP_DATABASE_URL="sqlite:///data/zotero.db"
```

Additionally, if the polling interval is set to 0 or empty, the software will run once and exit, which can be useful for running it as a one-off task.
