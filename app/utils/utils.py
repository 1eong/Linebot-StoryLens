import json
import jsonschema
from pathlib import Path
from typing import Union
from app.utils.logger import linebot_logger

class PathTool:
    @staticmethod
    def join_path(*args: Union[str, Path]) -> str:
        """
        串接目录及文件，且会建立所有未创建的目录
        """
        path = Path.cwd()

        for part in args:
            path /= part

        # 如果最後一部分是檔案名稱，避免創建目錄
        if not path.suffix:  # 沒有檔案擴展名，才是目錄
            path.mkdir(parents=True, exist_ok=True)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)

        return path

class JsonTool:
    def __init__(self, data_path, schema_path):
        self.file_path = data_path
        self.schema_path = schema_path

    
    def write_file(self, data: dict):
        try:
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
        except FileNotFoundError:
            linebot_logger.error(f"User data file not found: {self.file_path}")
        except json.JSONDecodeError:
            linebot_logger.error(f"Failed to decode JSON data in file: {self.file_path}")         

    def read_file(self) -> dict:
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                data_dict = json.load(f)
                
                self.__validate_json(data_dict)
                
                return data_dict
        except json.JSONDecodeError:
            linebot_logger.error(f"{self.file_path} contains invalid JSON.")
            raise f"{self.file_path} contains invalid JSON."
        except FileNotFoundError as e:
            raise e
        except jsonschema.exceptions.ValidationError as e:
            linebot_logger.error(f"JSON schema validation error: {e.message}")
            raise f"JSON schema validation error: {e.message}"
    
    def __validate_json(self, data: dict):
        # 加载 JSON schema 文件
        try:
            with open(self.schema_path, 'r', encoding='utf-8') as schema_file:
                schema = json.load(schema_file)

            # 使用 jsonschema 验证数据
            jsonschema.validate(instance=data, schema=schema)

        except json.JSONDecodeError:
            linebot_logger.error("Schema file is not valid JSON.")
            raise "Schema file is not valid JSON."
        except FileNotFoundError:
            linebot_logger.error("Schema file not found.")
            raise "Schema file not found."
        except jsonschema.exceptions.ValidationError as e:
            raise e