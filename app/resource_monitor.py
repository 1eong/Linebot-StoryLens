import time
import psutil
import GPUtil
from fastapi import Request
from app.utils.logger import system_logger

async def system_monitoring_middleware(request: Request, call_next):
    start_time = time.time()
    
    # 記錄系統資源
    cpu_usage = psutil.cpu_percent()
    memory = psutil.virtual_memory()
    
    system_logger.info(f"CPU Usage: {cpu_usage}%")
    system_logger.info(f"Memory Usage: {memory.percent}%")
    
    # GPU資源監控
    try:
        gpus = GPUtil.getGPUs()
        for gpu in gpus:
            system_logger.info(f"GPU {gpu.id}: {gpu.name}")
            system_logger.info(f"GPU Memory: {gpu.memoryUsed}/{gpu.memoryTotal} MB")
    except Exception as e:
        system_logger.warning(f"GPU monitoring error: {e}")
    
    # 執行請求
    response = await call_next(request)
    
    # 計算請求耗時
    process_time = time.time() - start_time
    system_logger.info(f"Request processing time: {process_time} seconds")
    
    return response