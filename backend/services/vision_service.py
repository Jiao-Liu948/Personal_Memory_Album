import exifread
import base64
import json
from openai import OpenAI
from PIL import Image
from io import BytesIO
from config import settings

client = OpenAI(
    api_key=settings.VISION_MODEL_API_KEY,
    base_url=settings.VISION_MODEL_BASE_URL,
    timeout=settings.VISION_TIMEOUT,
    max_retries=1,
)

def parse_exif(file_path: str) -> dict:
    """解析照片EXIF信息"""
    exif_data = {}
    try:
        with open(file_path, 'rb') as f:
            tags = exifread.process_file(f, details=False)
        # 提取核心字段
        if 'EXIF DateTimeOriginal' in tags:
            exif_data['shoot_time'] = str(tags['EXIF DateTimeOriginal'])
        if 'GPS GPSLatitude' in tags and 'GPS GPSLongitude' in tags:
            exif_data['has_gps'] = True
        else:
            exif_data['has_gps'] = False
        exif_data['camera'] = str(tags.get('Image Model', ''))
    except Exception as e:
        exif_data['error'] = str(e)
    return exif_data


def image_to_base64(file_path: str, max_size: int = 1024) -> str:
    """
    将图片转为完整的 Data URL (支持透明通道)
    返回格式: data:image/png;base64,xxxxx
    """
    with Image.open(file_path) as img:
        img.thumbnail((max_size, max_size))
        
        # 判断原图格式，保留透明度（PNG 用 PNG，其他用 JPEG）
        # 如果原图有透明通道 (RGBA, P 模式带透明度) 或格式为 PNG，则存为 PNG
        original_format = img.format
        if original_format == 'PNG' or img.mode in ('RGBA', 'LA'):
            save_format = 'PNG'
            mime_type = 'image/png'
        else:
            save_format = 'JPEG'
            mime_type = 'image/jpeg'
            # JPEG 不支持透明通道，若有 alpha 层需先转 RGB
            if img.mode == 'RGBA':
                # 创建白色背景填充，防止透明变黑
                background = Image.new('RGB', img.size, (255, 255, 255))
                background.paste(img, mask=img.split()[3])  # 使用 alpha 通道作为蒙版
                img = background

        # 3. 写入缓冲区
        buffer = BytesIO()
        img.save(buffer, format=save_format)
        base64_str = base64.b64encode(buffer.getvalue()).decode('utf-8')
        
        # 4. 返回带前缀的完整 Data URL
        return f"data:{mime_type};base64,{base64_str}"

def analyze_photo_content(file_path: str) -> dict:
    """
    调用多模态模型解析照片内容，输出结构化JSON
    输出字段与原接口完全一致：scene / main_objects / people_count / scene_tags / description
    """ 
    prompt = """请分析这张照片，输出严格的JSON格式，不要包含markdown代码块，不要多余解释文字，字段如下：
{
    "scene": "场景描述，如户外公园、餐厅、室内居家等",
    "main_objects": ["核心物体列表，最多5个"],
    "people_count": 画面中的人数，没有人填0,
    "scene_tags": ["场景标签，如生日、旅行、聚会、工作、日常等，最多3个"],
    "description": "一句话整体描述照片内容"
}
只输出纯JSON本身。
    """

    try:
        # 图片解码也放进 try：损坏/不支持格式的图片应返回结构化错误，而不是抛 500
        image_base64_url = image_to_base64(file_path)
        response = client.chat.completions.create(
            model=settings.VISION_MODEL_NAME,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": image_base64_url}  
                        },
                        {
                            "type": "text",
                            "text": prompt.strip()
                        }
                    ]
                }
            ],
            temperature=0,
            timeout=settings.VISION_TIMEOUT
        )
        
        # 成功时直接提取文本
        content = response.choices[0].message.content.strip()
        
        # 清理可能的 markdown 代码块
        if content.startswith("```json"):
            content = content[7:].strip()
        if content.endswith("```"):
            content = content[:-3].strip()
            
        result = json.loads(content)
        return result

    except json.JSONDecodeError as e:
        return {"error": f"JSON解析失败: {str(e)}", "description": "解析失败"}
    except Exception as e:
        return {"error": f"API调用失败: {str(e)}", "description": "解析失败"}