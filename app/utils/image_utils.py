from typing import BinaryIO


class ImageHelper:
    @staticmethod
    def download_binary_stream(stream: BinaryIO, save_path: str) -> None:
        """
        從二進位流下載資料並保存到指定路徑。
        """
        try:
            with open(save_path, "wb") as f:
                for chunk in stream.iter_content(chunk_size=1024):
                    if chunk:
                        f.write(chunk)
            print(f"File successfully download to {save_path}")
        except Exception as e:
            print(f"Failed to download the file: {e}")
