const express = require('express');
const cors = require('cors');
const app = express();

// 允许跨域（适配导诊屏前端请求）
app.use(cors());
// 解析JSON请求体
app.use(express.json());

// 配置端口（默认3000，可通过环境变量修改）
const PORT = process.env.PORT || 3000;

// 20台设备状态管理：deviceId → { isBusy, memory }
const deviceStatus = new Map();
for (let i = 0; i < 20; i++) {
    deviceStatus.set(`hospital-screen-${i}`, { isBusy: false, memory: 0 });
}

// 导诊任务队列（可根据医院实际需求扩展）
const guideTaskQueue = [
    {
        content: "您好，欢迎来到中国西苑苏州医院！内科和外科在1号楼2-3层，儿科在2号楼1层",
        picUrl: "https://your-server/department-map-1.png"
    },
    {
        content: "挂号可通过医院公众号预约，或在1号楼大厅自助机办理，支持医保支付",
        picUrl: "https://your-server/registration-guide.png"
    },
    {
        content: "取药处位于1号楼1层大厅东侧，凭处方单和缴费凭证即可领取药品",
        picUrl: "https://your-server/pharmacy-location.png"
    }
    // 可添加更多导诊任务...
];

// 1. 设备状态上报接口
app.post('/report-status', (req, res) => {
    const { deviceId, isBusy, memory } = req.body;
    if (!deviceId || isBusy === undefined || memory === undefined) {
        return res.status(400).json({ code: 400, msg: "参数不全（需deviceId/isBusy/memory）" });
    }
    if (deviceStatus.has(deviceId)) {
        deviceStatus.set(deviceId, { isBusy, memory });
        return res.json({ code: 200, msg: "状态更新成功" });
    } else {
        return res.status(404).json({ code: 404, msg: "设备ID不存在（需为hospital-screen-0至19）" });
    }
});

// 2. 任务分配接口（设备空闲时调用）
app.get('/get-task', (req, res) => {
    const { deviceId } = req.query;
    if (!deviceId) {
        return res.status(400).json({ code: 400, msg: "缺少deviceId参数" });
    }

    const device = deviceStatus.get(deviceId);
    if (!device) {
        return res.status(404).json({ code: 404, msg: "设备ID不存在" });
    }

    // 仅向“空闲且内存≤350MB”的设备分配任务
    if (device.isBusy || device.memory > 350) {
        return res.json({ 
            code: 403, 
            msg: `设备${deviceId}忙（${device.isBusy ? '运行中' : '内存过高'}）` 
        });
    }

    // 分配队列中的第一个任务
    if (guideTaskQueue.length > 0) {
        const task = guideTaskQueue.shift();
        return res.json({ code: 200, task });
    } else {
        return res.json({ code: 204, msg: "当前无待分配任务" });
    }
});

// 启动服务
app.listen(PORT, () => {
    console.log(`调度服务已启动，地址：http://localhost:${PORT}`);
    console.log("支持接口：");
    console.log("  POST /report-status - 设备状态上报");
    console.log("  GET  /get-task      - 任务分配");
});
