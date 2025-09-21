import torch
from typing import List, Optional
from PIL import Image
from colpali_engine.models import ColPali, ColPaliProcessor
import logging

logger = logging.getLogger(__name__)

class ColPaliModel:
    def __init__(self, model_name: str = "vidore/colpali-v1.3", device: Optional[str] = None):
        self.model_name = model_name
        self.model = None
        self.processor = None

        if device is None:
            if torch.cuda.is_available():
                self.device = "cuda:0"
            elif torch.backends.mps.is_available():
                self.device = "mps"
            else:
                self.device = "cpu"
        else:
            self.device = device

    def load(self):
        if self.model is not None:
            return

        logger.info(f"Loading ColPali model: {self.model_name}")
        logger.info(f"Using device: {self.device}")

        dtype = torch.bfloat16 if self.device != "cpu" else torch.float32

        self.model = ColPali.from_pretrained(
            self.model_name,
            torch_dtype=dtype,
            device_map=self.device
        ).eval()

        self.processor = ColPaliProcessor.from_pretrained(self.model_name)
        logger.info("ColPali model loaded successfully")

    def embed_images(self, images: List[Image.Image]) -> torch.Tensor:
        if self.model is None:
            self.load()

        batch_images = self.processor.process_images(images).to(self.model.device)

        with torch.no_grad():
            embeddings = self.model(**batch_images)

        return embeddings

    def embed_queries(self, queries: List[str]) -> torch.Tensor:
        if self.model is None:
            self.load()

        batch_queries = self.processor.process_queries(queries).to(self.model.device)

        with torch.no_grad():
            embeddings = self.model(**batch_queries)

        return embeddings

    def score(self, query_embeddings: torch.Tensor, image_embeddings: torch.Tensor) -> torch.Tensor:
        if self.processor is None:
            self.load()

        return self.processor.score_multi_vector(query_embeddings, image_embeddings)

colpali_model = ColPaliModel()