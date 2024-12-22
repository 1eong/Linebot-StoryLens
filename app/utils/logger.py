import logging
from logging.handlers import RotatingFileHandler
import os

def setup_logger(name, log_file, level=logging.INFO):

    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 確保日誌目錄存在
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    
    # 如果 logger 已经存在，清理它的 handlers
    logger = logging.getLogger(name)
    if logger.hasHandlers():
        logger.handlers.clear()
    
    # 可迴轉的文件日誌處理器
    file_handler = RotatingFileHandler(
        log_file, 
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'  # 設置為 UTF-8 編碼
    )
    file_handler.setFormatter(formatter)

    # 控制台處理器
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


# 創建不同模組的日誌
system_logger = setup_logger(
    'system', 
    'logs/system.log'
)
linebot_logger = setup_logger(
    'line', 
    'logs/linebot.log'
)
model_logger = setup_logger(
    'model_logger', 
    'logs/model.log'
)