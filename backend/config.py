import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    # MySQL
    MYSQL_HOST = os.getenv("MYSQL_HOST", "127.0.0.1")
    MYSQL_PORT = int(os.getenv("MYSQL_PORT", 3306))
    MYSQL_USER = os.getenv("MYSQL_USER", "root")
    MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
    MYSQL_DB = os.getenv("MYSQL_DB", "personal_agent")

    # LLM
    MODEL_NAME = os.getenv("MODEL_NAME")
    MODEL_API_KEY = os.getenv("MODEL_API_KEY", "")
    MODEL_BASE_URL = os.getenv("MODEL_BASE_URL", "https://api.openai.com/v1")

    # VLM
    VISION_MODEL_NAME = os.getenv("VISION_MODEL_NAME")
    VISION_MODEL_API_KEY = os.getenv("VISION_MODEL_API_KEY", "")
    VISION_MODEL_BASE_URL = os.getenv("VISION_MODEL_BASE_URL", "")

    # Judge（评测裁判模型，固定模型保证评分一致性；未配置时回退到主模型）
    JUDGE_MODEL_NAME = os.getenv("JUDGE_MODEL_NAME", "")
    JUDGE_MODEL_API_KEY = os.getenv("JUDGE_MODEL_API_KEY", "")
    JUDGE_MODEL_BASE_URL = os.getenv("JUDGE_MODEL_BASE_URL", "")

    # Embedding（向量模型，OpenAI兼容接口）
    EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", "")
    EMBEDDING_API_KEY = os.getenv("EMBEDDING_API_KEY", "")
    EMBEDDING_BASE_URL = os.getenv("EMBEDDING_BASE_URL", "")

    # Chroma 向量库
    CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "./storage/chroma")
    CHROMA_COLLECTION = os.getenv("CHROMA_COLLECTION", "memory_facts")

    # Langfuse（.env 可配置 LANGFUSE_BASE_URL 或 LANGFUSE_HOST，二者兼容）
    LANGFUSE_PUBLIC_KEY = os.getenv("LANGFUSE_PUBLIC_KEY", "")
    LANGFUSE_SECRET_KEY = os.getenv("LANGFUSE_SECRET_KEY", "")
    LANGFUSE_BASE_URL = os.getenv("LANGFUSE_BASE_URL", "https://cloud.langfuse.com")
    LANGFUSE_HOST = os.getenv("LANGFUSE_BASE_URL", "")

    # 存储
    STORAGE_ROOT = os.getenv("STORAGE_ROOT", "./storage/photos")

    # 调试
    DEBUG = os.getenv("DEBUG", "false").lower() == "true"

    # 调用健壮性：超时与重试
    # 说明：OpenAI 兼容端点的默认超时长达 600 秒且默认重试 2 次，
    # 一旦 base_url 配错，请求会「长时间挂住最后才超时」，而不是立刻报错。
    # 这里给较短的默认值，便于快速暴露配置问题；可用 .env 覆盖，无需修改代码。
    LLM_TIMEOUT = float(os.getenv("LLM_TIMEOUT", "60"))
    LLM_MAX_RETRIES = int(os.getenv("LLM_MAX_RETRIES", "1"))
    VISION_TIMEOUT = float(os.getenv("VISION_TIMEOUT", "60"))

    @property
    def DATABASE_URL(self):
        return f"mysql+pymysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DB}?charset=utf8mb4"

settings = Settings()
