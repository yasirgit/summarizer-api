"""Content extraction functionality using Trafilatura."""

import asyncio
import ipaddress
import re
from urllib.parse import urlparse

import httpx
import trafilatura
from readability import Document as ReadabilityDocument

from app.errors import ProcessingError
from app.settings import get_settings

settings = get_settings()

# Maximum content length (10MB in bytes)
MAX_CONTENT_LENGTH = 10 * 1024 * 1024

# Minimum content length (too short to be useful)
MIN_CONTENT_LENGTH = 50

# Private IP ranges for SSRF protection
PRIVATE_IP_RANGES = [
    ipaddress.ip_network("127.0.0.0/8"),  # Loopback
    ipaddress.ip_network("10.0.0.0/8"),  # RFC 1918 Class A
    ipaddress.ip_network("172.16.0.0/12"),  # RFC 1918 Class B
    ipaddress.ip_network("192.168.0.0/16"),  # RFC 1918 Class C
    ipaddress.ip_network("169.254.0.0/16"),  # Link-local
    ipaddress.ip_network("224.0.0.0/4"),  # Multicast
    ipaddress.ip_network("240.0.0.0/4"),  # Reserved
    ipaddress.ip_network("::1/128"),  # IPv6 loopback
    ipaddress.ip_network("fc00::/7"),  # IPv6 unique local
    ipaddress.ip_network("fe80::/10"),  # IPv6 link-local
]


def validate_url_security(url: str) -> None:
    """Validate URL for SSRF protection."""
    try:
        parsed_url = urlparse(url)

        # Block file:// scheme
        if parsed_url.scheme == "file":
            raise ProcessingError(
                f"File scheme not allowed: {url}",
                details={"url": url, "scheme": parsed_url.scheme},
            )

        # Only allow HTTP/HTTPS
        if parsed_url.scheme not in ["http", "https"]:
            raise ProcessingError(
                f"Only HTTP/HTTPS schemes allowed: {url}",
                details={"url": url, "scheme": parsed_url.scheme},
            )

        # Check for private IP addresses
        hostname = parsed_url.hostname
        if hostname:
            try:
                ip = ipaddress.ip_address(hostname)
                for private_range in PRIVATE_IP_RANGES:
                    if ip in private_range:
                        raise ProcessingError(
                            f"Private IP address not allowed: {url}",
                            details={"url": url, "ip": str(ip)},
                        )
            except ValueError:
                # Not an IP address (hostname), which is fine
                pass

    except Exception as e:
        if isinstance(e, ProcessingError):
            raise
        raise ProcessingError(
            f"Invalid URL format: {url}", details={"url": url, "error": str(e)}
        ) from e


def normalize_whitespace(text: str) -> str:
    """Normalize whitespace in extracted text."""
    if not text:
        return ""

    # Replace multiple whitespace characters with single space
    text = re.sub(r"\s+", " ", text)

    # Remove leading/trailing whitespace
    text = text.strip()

    return text


class ContentExtractor:
    """Extract content from web pages using Trafilatura and Readability."""

    def __init__(self):
        self.session = None

    async def __aenter__(self):
        """Async context manager entry."""
        # Configure httpx client with timeouts and limits
        timeout_config = httpx.Timeout(
            connect=10.0,  # Connect timeout: 10s
            read=30.0,  # Read timeout: 30s
            write=10.0,
            pool=10.0,
        )

        limits = httpx.Limits(
            max_keepalive_connections=5, max_connections=10, keepalive_expiry=30.0
        )

        self.session = httpx.AsyncClient(
            timeout=timeout_config,
            limits=limits,
            follow_redirects=True,
            max_redirects=5,  # Maximum 5 redirects
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; SummarizerBot/1.0; +https://example.com/bot)"
            },
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.aclose()

    async def fetch_with_retries(
        self, url: str, max_retries: int = 3
    ) -> httpx.Response:
        """Fetch URL with exponential backoff retries."""
        if not self.session:
            raise RuntimeError("ContentExtractor must be used as async context manager")

        last_exception = None

        for attempt in range(max_retries):
            try:
                response = await self.session.get(url)
                response.raise_for_status()

                # Check content length
                content_length = response.headers.get("content-length")
                if content_length and int(content_length) > MAX_CONTENT_LENGTH:
                    raise ProcessingError(
                        f"Content too large: {content_length} bytes (max: {MAX_CONTENT_LENGTH})",
                        details={"url": url, "content_length": content_length},
                    )

                return response

            except httpx.HTTPError as e:
                last_exception = e
                if attempt < max_retries - 1:
                    # Exponential backoff: 1s, 2s, 4s
                    wait_time = 2**attempt
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    break

        # All retries failed
        raise ProcessingError(
            f"Failed to fetch URL after {max_retries} attempts: {url}",
            details={"url": url, "last_error": str(last_exception)},
        ) from last_exception

    async def extract_content_from_url(self, url: str) -> str:
        """Extract main content from URL using Trafilatura with Readability fallback."""
        if not self.session:
            raise RuntimeError("ContentExtractor must be used as async context manager")

        try:
            # Validate URL for SSRF protection
            validate_url_security(url)

            # Fetch content with retries
            response = await self.fetch_with_retries(url)
            html_content = response.text

            # Check if content is too large after fetching
            if len(html_content.encode("utf-8")) > MAX_CONTENT_LENGTH:
                raise ProcessingError(
                    f"Content too large after fetching: {len(html_content.encode('utf-8'))} bytes",
                    details={
                        "url": url,
                        "actual_size": len(html_content.encode("utf-8")),
                    },
                )

            # Primary extraction with Trafilatura
            extracted_text = trafilatura.extract(
                html_content,
                include_formatting=True,
                include_links=False,
                include_images=False,
                include_tables=True,
                favor_precision=True,
                favor_recall=False,
            )

            # Fallback to Readability if Trafilatura fails or returns empty
            if not extracted_text or len(extracted_text.strip()) < MIN_CONTENT_LENGTH:
                try:
                    readability_doc = ReadabilityDocument(html_content)
                    extracted_text = readability_doc.summary()

                    # Extract text content from HTML
                    if extracted_text:
                        # Simple HTML tag removal (basic approach)
                        import re

                        extracted_text = re.sub(r"<[^>]+>", "", extracted_text)

                except Exception:
                    # Readability failed too
                    pass

            # Normalize whitespace
            if extracted_text:
                extracted_text = normalize_whitespace(extracted_text)

            # Validate content length
            if not extracted_text or len(extracted_text.strip()) < MIN_CONTENT_LENGTH:
                raise ProcessingError(
                    f"Extracted content too short or empty (min: {MIN_CONTENT_LENGTH} chars)",
                    details={
                        "url": url,
                        "extracted_length": (
                            len(extracted_text) if extracted_text else 0
                        ),
                        "min_required": MIN_CONTENT_LENGTH,
                    },
                )

            return extracted_text

        except ProcessingError:
            # Re-raise ProcessingError as-is
            raise
        except httpx.HTTPError as e:
            raise ProcessingError(
                f"HTTP error while fetching {url}: {str(e)}",
                details={"url": url, "error_type": "http_error", "error": str(e)},
            ) from e
        except Exception as e:
            raise ProcessingError(
                f"Failed to extract content from {url}: {str(e)}",
                details={"url": url, "error_type": "extraction_error", "error": str(e)},
            ) from e

    def clean_content(self, content: str) -> str:
        """Clean and normalize extracted content."""
        if not content:
            return ""

        # Normalize whitespace
        content = normalize_whitespace(content)

        # Additional cleaning if needed
        # Remove excessive line breaks
        content = re.sub(r"\n{3,}", "\n\n", content)

        return content


# Convenience functions for the document summarization pipeline
async def extract_content_from_url(url: str) -> str:
    """Convenience function to extract content from a single URL."""
    async with ContentExtractor() as extractor:
        return await extractor.extract_content_from_url(url)
