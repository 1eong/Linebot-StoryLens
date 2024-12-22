import aiofiles

class ImageHelper:
    @staticmethod
    def download_binary_stream(stream:bytes, save_path: str) -> None:
        """
        Saves the binary stream to the specified file path.
        """
        print("download image!")
        try:
            with open(save_path, "wb") as f:
                f.write(stream)
            print(f"File successfully download to {save_path}")
        except Exception as e:
            print(f"Failed to download the file: {e}")
