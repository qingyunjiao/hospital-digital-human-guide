/**
 * 设备工具函数：内存监控、状态上报、资源清理
 */

// 移除旧的导诊图片（释放内存）
function removeOldGuidePic() {
    const oldImg = document.querySelector('.guide-pic');
    if (oldImg) {
        oldImg.remove();
        console.log("已移除旧导诊图片");
    }
}

// 渲染新的导诊图片
function renderNewGuidePic(picUrl) {
    const newImg = document.createElement('img');
    newImg.src = picUrl;
    newImg.className = 'guide-pic';
    newImg.style.width = '300px';  // 固定尺寸，避免重绘
    newImg.onload = () => console.log("新导诊图片加载完成");
    newImg.onerror = () => console.error("导诊图片加载失败：", picUrl);
    document.body.appendChild(newImg);
}

// 获取设备内存占用（嵌入式设备需适配系统API）
function getMemoryUsage() {
    // 浏览器环境模拟值（实际嵌入式设备需通过原生API获取）
    if (typeof window !== 'undefined') {
        return Math.floor(Math.random() * 50) + 280;  // 模拟280-330MB
    }
    return 0;
}

// 向后端上报设备状态（每30秒一次）
function startStatusReport() {
    setInterval(async () => {
        try {
            const memoryUsage = getMemoryUsage();
            const res = await fetch(`${BACKEND_URL}/report-status`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    deviceId: DEVICE_ID,
                    isBusy: window.voicePlaying,
                    memory: memoryUsage
                })
            });
            const data = await res.json();
            console.log("状态上报结果：", data.msg);
        } catch (error) {
            console.error("状态上报失败：", error);
        }
    }, 30000);  // 30秒一次
    console.log("设备状态上报服务已启动");
}

// 每日凌晨2点执行资源重置（避免长期运行内存泄漏）
function scheduleDailyReset() {
    const now = new Date();
    let resetTime = new Date(now);
    resetTime.setHours(2, 0, 0, 0);
    if (now > resetTime) resetTime.setDate(resetTime.getDate() + 1);

    const delay = resetTime - now;
    console.log(`计划每日重置：${resetTime.toLocaleString()}（约${Math.floor(delay/3600000)}小时后）`);

    setTimeout(async () => {
        try {
            console.log("执行每日资源重置...");
            // 1. 销毁SDK实例
            if (window.digitalHumanSdk?.destroy) {
                await window.digitalHumanSdk.destroy();
                console.log("SDK实例已销毁");
            }
            // 2. 清理缓存
            if (window.caches) {
                const cacheNames = await caches.keys();
                await Promise.all(cacheNames.map(name => caches.delete(name)));
                console.log("缓存已清理");
            }
            // 3. 刷新页面
            window.location.reload();
        } catch (error) {
            console.error("每日重置失败，强制刷新：", error);
            window.location.reload();
        }
    }, delay);
}

// 处理SDK错误（按官方错误码降级）
function handleSdkError(errorCode) {
    switch(errorCode) {
        case 10001:  // 容器不存在
            alert("数字人容器初始化失败，请检查页面结构");
            break;
        case 10002:  // Socket连接错误
            console.log("尝试重新连接SDK...");
            setTimeout(() => initDigitalHumanSdk(), 5000);  // 5秒后重试
            break;
        case 30001:  // 背景图加载错误
            window.digitalHumanSdk?.setDefaultBackground();  // 切换默认背景
            break;
        default:
            console.log(`未处理的错误码：${errorCode}，请参考官方文档`);
    }
}
