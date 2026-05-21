import os
from dotenv import load_dotenv
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import (
    AnalyzeDocumentRequest,
    DocumentContentFormat,
)
from azure.core.credentials import AzureKeyCredential

load_dotenv()

endpoint = os.environ["AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT"]
key = os.environ["AZURE_DOCUMENT_INTELLIGENCE_KEY"]

client = DocumentIntelligenceClient(
    endpoint=endpoint,
    credential=AzureKeyCredential(key),
)

with open("ppo.pdf", "rb") as f:
    pdf_bytes = f.read()

poller = client.begin_analyze_document(
    "prebuilt-layout",
    AnalyzeDocumentRequest(bytes_source=pdf_bytes),
    output_content_format=DocumentContentFormat.MARKDOWN,
)

result = poller.result()

print(result.content)