from pdf2image import convert_from_bytes
from PIL import Image
from typing import List, Dict, Any
import io
import logging

logger = logging.getLogger(__name__)

class PDFProcessor:
    def __init__(self, dpi: int = 150):
        self.dpi = dpi

    def pdf_to_images(self, pdf_bytes: bytes) -> List[Image.Image]:
        try:
            images = convert_from_bytes(
                pdf_bytes,
                dpi=self.dpi,
                fmt='PNG'
            )
            logger.info(f"Converted PDF to {len(images)} images")
            return images
        except Exception as e:
            logger.error(f"Error converting PDF to images: {e}")
            raise

    def get_pdf_info(self, pdf_bytes: bytes) -> Dict[str, Any]:
        images = self.pdf_to_images(pdf_bytes)

        return {
            "page_count": len(images),
            "pages": [
                {
                    "page_number": i + 1,
                    "width": img.width,
                    "height": img.height,
                    "format": img.format or "PNG",
                    "mode": img.mode
                }
                for i, img in enumerate(images)
            ]
        }

pdf_processor = PDFProcessor()