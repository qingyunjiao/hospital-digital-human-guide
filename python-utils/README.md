# 魔珐星云内存池优化工具
基于魔珐星云SDK的场景化内存池管理模块，支持动态扩容、线程安全与内存监控。

## 功能
- 适配公共服务屏、车载、虚拟IP三大场景
- 自动优化内存分配，降低碎片率
- 实时监控内存使用状态

## 使用方法
```python
from mofa_memory_pool import init_scene_memory_pool, SceneType

# 初始化公共服务屏场景内存池
pool = init_scene_memory_pool(SceneType.PUBLIC_SERVICE_SCREEN)
