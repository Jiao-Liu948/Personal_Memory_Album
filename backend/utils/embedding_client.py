from openai import OpenAI
from config import settings


class EmbeddingClient:
    """向量化客户端，使用OpenAI兼容接口（支持千问Embedding等）"""

    def __init__(self):
        api_key = settings.EMBEDDING_API_KEY 
        base_url = settings.EMBEDDING_BASE_URL 
        self.model = settings.EMBEDDING_MODEL_NAME
        self.client = None
        if api_key and base_url:
            self.client = OpenAI(api_key=api_key, base_url=base_url)

    @property
    def available(self) -> bool:
        return self.client is not None and bool(self.model)

    def embed(self, text: str) -> list:
        """单文本向量化"""
        if not self.available:
            raise ValueError("Embedding服务未配置，请检查.env中的EMBEDDING_*配置")
        response = self.client.embeddings.create(model=self.model, input=text)
        return response.data[0].embedding

    def embed_batch(self, texts: list) -> list:
        """批量向量化"""
        if not self.available:
            raise ValueError("Embedding服务未配置")
        response = self.client.embeddings.create(model=self.model, input=texts)
        return [item.embedding for item in response.data]


embedding_client = EmbeddingClient()
