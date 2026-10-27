from io import BytesIO
from bs4 import BeautifulSoup
from pypdf import PdfReader

MAX_BYTES = 10 * 1024 * 1024
MAX_CHARS = 60000


def clean_text(text: str) -> str:
    text = text.replace("\x00", "").strip()
    if not text:
        raise ValueError("No text found. Image-only PDFs need OCR before upload.")
    if len(text) > MAX_CHARS:
        raise ValueError(f"Document exceeds {MAX_CHARS:,} characters; split it into invoices.")
    return text


def ingest(data: bytes | str, kind: str = "text") -> str:
    if isinstance(data, bytes):
        if len(data) > MAX_BYTES:
            raise ValueError("Maximum upload size is 10 MB")
        if kind == "pdf":
            try:
                reader = PdfReader(BytesIO(data))
                if reader.is_encrypted:
                    raise ValueError("Encrypted PDFs are unsupported; upload an unlocked copy")
                if len(reader.pages) > 30:
                    raise ValueError("PDF is limited to 30 pages")
                return clean_text("\n".join(page.extract_text() or "" for page in reader.pages))
            except ValueError:
                raise
            except Exception as exc:
                raise ValueError("Could not read PDF. Use a valid, text-based PDF.") from exc
        try:
            data = data.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise ValueError("Text/HTML files must be UTF-8") from exc
    if kind == "html":
        soup = BeautifulSoup(data, "html.parser")
        for node in soup(["script", "style", "noscript"]):
            node.decompose()
        data = soup.get_text("\n", strip=True)
    return clean_text(data)
