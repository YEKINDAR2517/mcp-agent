import json
import logging
from typing import Any, Optional, Dict
from datetime import datetime, timedelta
import os
import pickle
from pathlib import Path

logger = logging.getLogger(__name__)

class Cache:
    def __init__(self, cache_dir: str = ".cache"):
        self.cache_dir = Path(cache_dir)
        self.memory_cache: Dict[str, Dict[str, Any]] = {}
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
    def _get_cache_file(self, key: str) -> Path:
        """获取缓存文件路径"""
        return self.cache_dir / f"{key}.pickle"
        
    def get(self, key: str, ttl: int = 3600) -> Optional[Any]:
        """获取缓存值"""
        try:
            # 1. 先查内存缓存
            if key in self.memory_cache:
                cache_data = self.memory_cache[key]
                if datetime.now().timestamp() - cache_data["timestamp"] < ttl:
                    return cache_data["value"]
                else:
                    del self.memory_cache[key]
            
            # 2. 查文件缓存
            cache_file = self._get_cache_file(key)
            if cache_file.exists():
                with open(cache_file, "rb") as f:
                    cache_data = pickle.load(f)
                if datetime.now().timestamp() - cache_data["timestamp"] < ttl:
                    # 加载到内存缓存
                    self.memory_cache[key] = cache_data
                    return cache_data["value"]
                else:
                    cache_file.unlink()  # 删除过期缓存
            
            return None
        except Exception as e:
            logger.error(f"获取缓存失败: {e}")
            return None
            
    def set(self, key: str, value: Any, persist: bool = False):
        """设置缓存值"""
        try:
            cache_data = {
                "value": value,
                "timestamp": datetime.now().timestamp()
            }
            
            # 1. 设置内存缓存
            self.memory_cache[key] = cache_data
            
            # 2. 如果需要持久化，写入文件
            if persist:
                cache_file = self._get_cache_file(key)
                with open(cache_file, "wb") as f:
                    pickle.dump(cache_data, f)
                    
        except Exception as e:
            logger.error(f"设置缓存失败: {e}")
    
    def delete(self, key: str):
        """删除缓存"""
        try:
            # 1. 删除内存缓存
            if key in self.memory_cache:
                del self.memory_cache[key]
            
            # 2. 删除文件缓存
            cache_file = self._get_cache_file(key)
            if cache_file.exists():
                cache_file.unlink()
                
        except Exception as e:
            logger.error(f"删除缓存失败: {e}")
    
    def clear(self):
        """清空所有缓存"""
        try:
            # 1. 清空内存缓存
            self.memory_cache.clear()
            
            # 2. 清空文件缓存
            for cache_file in self.cache_dir.glob("*.pickle"):
                cache_file.unlink()
                
        except Exception as e:
            logger.error(f"清空缓存失败: {e}")

# 全局缓存实例
cache = Cache() 