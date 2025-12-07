"""
魔珐星云场景化分级内存池初始化（最终增强版）
适配SDK V2.1及以上版本
核心优化：动态扩容、线程安全、内存监控、配置持久化、完整异常处理
"""
from mofa_nebula import MemoryPoolConfig, MemoryBlockType, SceneType
import logging
import sys
import threading
import time
import json
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

# 配置日志（增强日志配置，支持日志轮转）
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.handlers.RotatingFileHandler(
            'memory_pool.log',
            encoding='utf-8',
            mode='a',
            maxBytes=10 * 1024 * 1024,  # 10MB轮转
            backupCount=5
        )
    ]
)
logger = logging.getLogger("MofaMemoryPool")

@dataclass
class MemoryPoolMetrics:
    """内存池性能指标"""
    total_allocations: int = 0
    total_deallocations: int = 0
    allocation_failures: int = 0
    peak_memory_usage: int = 0
    startup_time: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典，便于持久化"""
        return asdict(self)

class MemoryPoolManager:
    """
    内存池管理器（单例模式）
    统一管理多个内存池实例、性能指标与监控线程
    基于内存池设计原则：减少系统调用、避免内存碎片、高效分配释放
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._pools = {}  # 场景->内存池实例
                cls._instance._metrics = {}  # 场景->性能指标
                cls._instance._stop_monitor = False  # 监控线程退出标志
                cls._instance._monitor_threads = []  # 监控线程列表
            return cls._instance

    def register_pool(self, scene_type: SceneType, pool: MemoryPoolConfig) -> None:
        """注册内存池实例（线程安全）"""
        with self._lock:
            self._pools[scene_type] = pool
            self._metrics[scene_type] = MemoryPoolMetrics()
            self._metrics[scene_type].startup_time = time.time()
            logger.debug(f"场景{scene_type.name}内存池已注册")

    def get_pool(self, scene_type: SceneType) -> Optional[MemoryPoolConfig]:
        """获取内存池实例（线程安全）"""
        with self._lock:
            return self._pools.get(scene_type)

    def get_metrics(self, scene_type: SceneType) -> Optional[MemoryPoolMetrics]:
        """获取性能指标（线程安全）"""
        with self._lock:
            return self._metrics.get(scene_type)

    def stop_all_monitors(self) -> None:
        """停止所有监控线程（优雅退出）"""
        with self._lock:
            self._stop_monitor = True
        logger.info("开始停止所有内存池监控线程...")
        for thread in self._monitor_threads:
            if thread.is_alive():
                thread.join(timeout=5)
                logger.debug(f"监控线程{thread.name}已停止")
        self._monitor_threads.clear()
        logger.info("所有监控线程已停止")

    def add_monitor_thread(self, thread: threading.Thread) -> None:
        """添加监控线程到管理列表"""
        with self._lock:
            self._monitor_threads.append(thread)

def init_scene_memory_pool(scene_type: SceneType, config_file: Optional[str] = None) -> MemoryPoolConfig:
    """
    初始化场景化内存池（最终增强版）

    优化点：
    1. 支持外部配置文件动态调整参数
    2. 增强线程安全性，支持多线程并发调用
    3. 添加性能监控指标与后台监控线程
    4. 支持配置持久化与优雅退出
    5. 完善的异常处理与日志记录

    :param scene_type: 场景类型
    :param config_file: 外部配置文件路径（可选）
    :return: 初始化完成的内存池实例
    :raises: ValueError, MemoryPoolError 初始化失败时抛出异常
    """
    try:
        # 0. 加载外部配置（如果提供）
        external_config = _load_external_config(config_file) if config_file else {}

        # 1. 场景内存上限配置（支持外部配置覆盖默认值）
        scene_memory_config: Dict[SceneType, int] = {
            SceneType.PUBLIC_SERVICE_SCREEN: external_config.get(
                'PUBLIC_SERVICE_SCREEN_TOTAL_MEMORY', 512 * 1024 * 1024
            ),
            SceneType.VEHICLE: external_config.get(
                'VEHICLE_TOTAL_MEMORY', 1024 * 1024 * 1024
            ),
            SceneType.VIRTUAL_IP: external_config.get(
                'VIRTUAL_IP_TOTAL_MEMORY', 2048 * 1024 * 1024
            )
        }

        if scene_type not in scene_memory_config:
            raise ValueError(f"不支持的场景类型: {scene_type}")

        total_memory = scene_memory_config[scene_type]
        logger.info(f"开始初始化 {scene_type.name} 场景内存池，总内存: {total_memory/(1024 * 1024):.0f}MB")

        # 2. 创建内存池实例（带超时保护）
        pool = _create_pool_with_timeout(total_memory, timeout=30)

        # 3. 分级子池配置（支持动态参数调整）
        _configure_scene_pools(pool, scene_type, external_config)

        # 4. 启用高级功能（内存复用、碎片整理、自动扩容）
        _enable_advanced_features(pool)

        # 5. 验证配置有效性
        if not _validate_pool_config(pool):
            raise MemoryPoolError("内存池配置验证失败")

        # 6. 注册到管理器
        manager = MemoryPoolManager()
        manager.register_pool(scene_type, pool)

        # 7. 启动后台监控线程
        _start_background_monitoring(pool, scene_type)

        logger.info(f"✅ {scene_type.name} 场景内存池初始化成功")
        logger.debug(f"内存池详细配置: {pool.get_block_config()}")

        return pool

    except Exception as e:
        logger.error(f"❌ 内存池初始化失败: {str(e)}", exc_info=True)
        raise

def _load_external_config(config_file: str) -> Dict[str, Any]:
    """加载外部JSON配置文件（增强类型校验）"""
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        # 类型校验：确保内存大小为整型
        for key, value in config.items():
            if "MEMORY" in key or "SIZE" in key or "COUNT" in key:
                if not isinstance(value, int):
                    logger.warning(f"配置项{key}值{value}非整型，将转换为整型")
                    config[key] = int(value) if str(value).isdigit() else 0
        return config
    except json.JSONDecodeError as e:
        logger.error(f"配置文件解析失败: {e}", exc_info=True)
        raise MemoryPoolError(f"配置文件JSON格式错误: {e}")
    except FileNotFoundError as e:
        logger.error(f"配置文件不存在: {e}", exc_info=True)
        raise MemoryPoolError(f"配置文件未找到: {config_file}")
    except Exception as e:
        logger.warning(f"外部配置文件加载失败，使用默认配置: {e}")
        return {}

def _create_pool_with_timeout(total_memory: int, timeout: int = 30) -> MemoryPoolConfig:
    """带超时的内存池创建（避免SDK阻塞）"""
    from queue import Queue

    result_queue = Queue(maxsize=1)

    def create_pool():
        """子线程创建内存池"""
        try:
            pool = MemoryPoolConfig(total_memory=total_memory)
            result_queue.put(pool)
        except Exception as e:
            result_queue.put(e)

    # 启动创建线程
    create_thread = threading.Thread(target=create_pool, daemon=True)
    create_thread.start()
    create_thread.join(timeout=timeout)

    # 处理结果
    if result_queue.empty():
        raise MemoryPoolError(f"内存池创建超时（{timeout}秒）")
    result = result_queue.get()
    if isinstance(result, Exception):
        raise result
    return result

def _configure_scene_pools(pool: MemoryPoolConfig, scene_type: SceneType, external_config: Dict[str, Any]) -> None:
    """配置场景化内存池（动态参数版）"""
    config_strategies = {
        SceneType.PUBLIC_SERVICE_SCREEN: _configure_public_service_screen,
        SceneType.VEHICLE: _configure_vehicle_screen,
        SceneType.VIRTUAL_IP: _configure_virtual_ip
    }

    if scene_type in config_strategies:
        config_strategies[scene_type](pool, external_config)
    else:
        logger.warning(f"未找到场景 {scene_type} 的配置策略，使用通用配置")
        _configure_generic_pool(pool, external_config)

def _configure_public_service_screen(pool: MemoryPoolConfig, external_config: Dict[str, Any]) -> None:
    """配置公共服务屏场景（嵌入式设备）"""
    # 大对象池：3D模型、纹理数据
    pool.add_block(
        block_type=MemoryBlockType.LARGE,
        block_size=external_config.get('PS_LARGE_BLOCK_SIZE', 64 * 1024 * 1024),
        block_count=external_config.get('PS_LARGE_BLOCK_COUNT', 4),
        description="存储静态3D数字人模型、高清纹理贴图"
    )
    # 小对象池：交互指令、设备状态
    pool.add_block(
        block_type=MemoryBlockType.SMALL,
        block_size=external_config.get('PS_SMALL_BLOCK_SIZE', 32 * 1024),
        block_count=external_config.get('PS_SMALL_BLOCK_COUNT', 1024),
        description="存储实时交互指令、用户查询、设备状态"
    )
    # 中对象池：临时数据缓存
    pool.add_block(
        block_type=MemoryBlockType.MEDIUM,
        block_size=external_config.get('PS_MEDIUM_BLOCK_SIZE', 2 * 1024 * 1024),
        block_count=external_config.get('PS_MEDIUM_BLOCK_COUNT', 32),
        description="缓存动态内容、临时计算数据"
    )

def _configure_vehicle_screen(pool: MemoryPoolConfig, external_config: Dict[str, Any]) -> None:
    """配置车载场景（动作帧缓存核心）"""
    # 中对象池：动作帧、渲染缓存
    pool.add_block(
        block_type=MemoryBlockType.MEDIUM,
        block_size=external_config.get('V_MEDIUM_BLOCK_SIZE', 16 * 1024 * 1024),
        block_count=external_config.get('V_MEDIUM_BLOCK_COUNT', 32),
        description="存储文生3D动作帧、实时渲染缓存"
    )
    # 小对象池：传感器数据、控制指令
    pool.add_block(
        block_type=MemoryBlockType.SMALL,
        block_size=external_config.get('V_SMALL_BLOCK_SIZE', 64 * 1024),
        block_count=external_config.get('V_SMALL_BLOCK_COUNT', 512),
        description="存储传感器数据、实时控制指令"
    )
    # 大对象池：高精地图、AI模型
    pool.add_block(
        block_type=MemoryBlockType.LARGE,
        block_size=external_config.get('V_LARGE_BLOCK_SIZE', 128 * 1024 * 1024),
        block_count=external_config.get('V_LARGE_BLOCK_COUNT', 4),
        description="存储高精地图数据、AI推理模型"
    )

def _configure_virtual_ip(pool: MemoryPoolConfig, external_config: Dict[str, Any]) -> None:
    """配置虚拟IP场景（4K纹理、高清资源）"""
    # 大对象池：4K纹理、高清模型
    pool.add_block(
        block_type=MemoryBlockType.LARGE,
        block_size=external_config.get('VIP_LARGE_BLOCK_SIZE', 256 * 1024 * 1024),
        block_count=external_config.get('VIP_LARGE_BLOCK_COUNT', 6),
        description="存储4K纹理、高清模型资源、动作数据"
    )
    # 中对象池：动画帧、计算中间结果
    pool.add_block(
        block_type=MemoryBlockType.MEDIUM,
        block_size=external_config.get('VIP_MEDIUM_BLOCK_SIZE', 8 * 1024 * 1024),
        block_count=external_config.get('VIP_MEDIUM_BLOCK_COUNT', 32),
        description="缓存动画帧、物理计算中间结果"
    )
    # 小对象池：用户交互、网络数据
    pool.add_block(
        block_type=MemoryBlockType.SMALL,
        block_size=external_config.get('VIP_SMALL_BLOCK_SIZE', 128 * 1024),
        block_count=external_config.get('VIP_SMALL_BLOCK_COUNT', 256),
        description="处理用户交互数据、网络通信包"
    )

def _configure_generic_pool(pool: MemoryPoolConfig, external_config: Dict[str, Any]) -> None:
    """通用场景配置（兜底方案）"""
    pool.add_block(
        block_type=MemoryBlockType.MEDIUM,
        block_size=external_config.get('GEN_MEDIUM_BLOCK_SIZE', 32 * 1024 * 1024),
        block_count=external_config.get('GEN_MEDIUM_BLOCK_COUNT', 8),
        description="通用场景默认中对象池"
    )

def _enable_advanced_features(pool: MemoryPoolConfig) -> None:
    """启用高级特性（增强错误处理与兼容性）"""
    advanced_features = [
        ('enable_memory_reuse', [], '内存复用'),
        ('enable_fragmentation_cleanup', [0.1], '碎片整理'),
        ('enable_auto_expansion', [0.8], '自动扩容'),  # 使用率80%时自动扩容
    ]

    for feature, args, description in advanced_features:
        try:
            if hasattr(pool, feature):
                getattr(pool, feature)(*args)
                logger.debug(f"✅ {description}功能启用成功")
            else:
                logger.warning(f"⚠️ SDK不支持{description}功能，跳过启用")
        except Exception as e:
            logger.warning(f"⚠️ {description}功能启用失败: {e}", exc_info=True)

def _validate_pool_config(pool: MemoryPoolConfig) -> bool:
    """验证内存池配置（增强鲁棒性，兼容多格式返回值）"""
    try:
        config: Any = pool.get_block_config()
        total_configured = 0

        # 处理字典类型配置
        if isinstance(config, dict):
            for block_key, block_info in config.items():
                if isinstance(block_info, dict) and 'block_size' in block_info and 'block_count' in block_info:
                    total_configured += block_info['block_size'] * block_info['block_count']
                    logger.debug(f"解析块{block_key}：大小{block_info['block_size']/1024/1024:.1f}MB，数量{block_info['block_count']}")
                else:
                    logger.warning(f"内存块{block_key}配置格式异常，跳过统计: {block_info}")
        # 处理列表类型配置
        elif isinstance(config, list):
            for idx, block_info in enumerate(config):
                if isinstance(block_info, dict) and 'block_size' in block_info and 'block_count' in block_info:
                    total_configured += block_info['block_size'] * block_info['block_count']
                    logger.debug(f"解析列表块{idx}：大小{block_info['block_size']/1024/1024:.1f}MB，数量{block_info['block_count']}")
                else:
                    logger.warning(f"列表内存块{idx}配置格式异常，跳过统计: {block_info}")
        # 不支持的配置格式
        else:
            logger.error(f"不支持的配置返回格式，类型为: {type(config)}")
            return False

        # 校验配置内存合理性
        if total_configured > pool.total_memory:
            logger.error(f"配置总内存({total_configured/1024/1024:.1f}MB)超过内存池总内存({pool.total_memory/1024/1024:.1f}MB)")
            return False
        if total_configured == 0:
            logger.error("内存池未配置任何有效内存块")
            return False

        logger.debug(f"配置验证通过，总配置内存{total_configured/1024/1024:.1f}MB，内存池总内存{pool.total_memory/1024/1024:.1f}MB")
        return True
    except Exception as e:
        logger.error(f"配置验证异常: {e}", exc_info=True)
        return False

def _start_background_monitoring(pool: MemoryPoolConfig, scene_type: SceneType) -> None:
    """启动后台监控线程（支持优雅退出）"""
    def monitor():
        manager = MemoryPoolManager()
        metrics = manager.get_metrics(scene_type)

        while not manager._stop_monitor:
            try:
                # 监控内存使用情况（兼容SDK返回值）
                if hasattr(pool, 'get_usage_stats'):
                    stats = pool.get_usage_stats()
                    if metrics and isinstance(stats, dict):
                        current_usage = stats.get('used_memory', 0)
                        metrics.peak_memory_usage = max(metrics.peak_memory_usage, current_usage)
                        logger.debug(f"场景{scene_type.name}内存峰值: {metrics.peak_memory_usage/1024/1024:.1f}MB")

                # 每5分钟采集一次数据
                time.sleep(300)

            except Exception as e:
                logger.error(f"场景{scene_type.name}监控线程异常: {e}", exc_info=True)
                time.sleep(60)  # 异常后延迟1分钟继续

    # 启动监控线程并加入管理器
    monitor_thread = threading.Thread(target=monitor, daemon=True)
    monitor_thread.name = f"MemoryPoolMonitor-{scene_type.name}"
    monitor_thread.start()

    manager = MemoryPoolManager()
    manager.add_monitor_thread(monitor_thread)
    logger.debug(f"场景{scene_type.name}监控线程已启动: {monitor_thread.name}")

def _test_allocation_performance(pool: MemoryPoolConfig, scene_type: SceneType, iterations: int = 1000) -> None:
    """测试内存分配/释放性能（带指标统计）"""
    logger.info(f"开始性能测试：{iterations}次内存分配/释放（场景：{scene_type.name}）")
    manager = MemoryPoolManager()
    metrics = manager.get_metrics(scene_type)

    if not metrics:
        logger.error("性能指标未找到，跳过性能测试")
        return

    start_time = time.time()
    for i in range(iterations):
        # 申请小对象内存
        mem = pool.allocate(block_type=MemoryBlockType.SMALL)
        if mem:
            pool.deallocate(mem)
            metrics.total_allocations += 1
            metrics.total_deallocations += 1
        else:
            metrics.allocation_failures += 1
            if i % 100 == 0:  # 每100次失败打印一次日志
                logger.warning(f"第{i}次内存分配失败")

    end_time = time.time()
    # 输出性能报告
    logger.info("=" * 50)
    logger.info("性能测试报告")
    logger.info(f"总耗时: {end_time - start_time:.2f}秒")
    logger.info(f"总分配次数: {metrics.total_allocations}")
    logger.info(f"总释放次数: {metrics.total_deallocations}")
    logger.info(f"分配失败次数: {metrics.allocation_failures}")
    logger.info(f"平均每次分配/释放耗时: {(end_time - start_time)/iterations*1000:.2f}ms")
    logger.info("=" * 50)

class MemoryPoolError(Exception):
    """自定义内存池异常（统一异常类型）"""
    pass

# 配置文件示例
SAMPLE_CONFIG = {
    "PUBLIC_SERVICE_SCREEN_TOTAL_MEMORY": 536870912,  # 512MB + 32MB
    "PS_LARGE_BLOCK_SIZE": 67108864,  # 64MB + 4MB
    "PS_LARGE_BLOCK_COUNT": 4,
    "PS_SMALL_BLOCK_SIZE": 32768,  # 32KB
    "PS_SMALL_BLOCK_COUNT": 1024,

    "VEHICLE_TOTAL_MEMORY": 1073741824,  # 1GB
    "VIRTUAL_IP_TOTAL_MEMORY": 2147483648,  # 2GB
}

def create_sample_config() -> None:
    """生成示例配置文件（便于快速部署）"""
    try:
        with open('memory_pool_config.json', 'w', encoding='utf-8') as f:
            json.dump(SAMPLE_CONFIG, f, indent=2, ensure_ascii=False)
        logger.info("✅ 示例配置文件已生成: memory_pool_config.json")
    except Exception as e:
        logger.error(f"生成示例配置文件失败: {e}", exc_info=True)
        raise MemoryPoolError(f"配置文件生成失败: {e}")

# 实战调用示例
if __name__ == "__main__":
    try:
        # 生成示例配置文件（首次运行可执行）
        create_sample_config()

        # 初始化管理器
        pool_manager = MemoryPoolManager()

        # 示例1：使用默认配置初始化公共服务屏场景
        logger.info("\n=== 使用默认配置初始化公共服务屏场景 ===")
        public_service_pool = init_scene_memory_pool(SceneType.PUBLIC_SERVICE_SCREEN)
        # 测试公共服务屏性能
        _test_allocation_performance(public_service_pool, SceneType.PUBLIC_SERVICE_SCREEN, iterations=1000)

        # 示例2：使用外部配置文件初始化车载场景
        logger.info("\n=== 使用外部配置文件初始化车载场景 ===")
        vehicle_pool = init_scene_memory_pool(
            SceneType.VEHICLE,
            config_file='memory_pool_config.json'
        )
        # 测试车载场景性能
        _test_allocation_performance(vehicle_pool, SceneType.VEHICLE, iterations=500)

        # 示例3：初始化虚拟IP场景（可选）
        # logger.info("\n=== 初始化虚拟IP场景 ===")
        # virtual_ip_pool = init_scene_memory_pool(SceneType.VIRTUAL_IP)

        # 模拟程序运行（实际业务逻辑）
        logger.info("\n=== 内存池已就绪，开始执行业务逻辑 ===")
        time.sleep(10)

    except Exception as e:
        logger.error(f"演示程序执行失败: {e}", exc_info=True)
        sys.exit(1)
    finally:
        # 优雅停止所有监控线程
        logger.info("\n=== 程序退出，清理资源 ===")
        pool_manager = MemoryPoolManager()
        pool_manager.stop_all_monitors()
        logger.info("✅ 所有资源已清理完成")
