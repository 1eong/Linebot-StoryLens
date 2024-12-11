from pathlib import Path
from typing import Union


class PathTool:

    @staticmethod
    def join_path(*args: Union[str, Path]) -> str:
        path = Path.cwd()

        for part in args:
            path /= part

        # 如果最後一部分是檔案名稱，避免創建目錄
        if not path.suffix:  # 沒有檔案擴展名，才是目錄
            path.mkdir(parents=True, exist_ok=True)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)

        return path
