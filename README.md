# hospital-digital-human-guide
医院公共服务屏
# 医院导诊屏数字人解决方案（基于魔珐星云SDK）

> 20台嵌入式设备高并发部署方案，支持RK3566/RK3588芯片，内存稳定控制在280-350MB

## 功能说明
- 基于魔珐星云具身智能SDK，驱动3D数字人完成医院导诊服务
- 支持20台设备协同工作，通过后端调度避免资源冲突
- 自动适配嵌入式设备特性（内存优化、定时清理、异常自愈）

## 环境要求
### 前端（导诊屏）
- 浏览器：Chrome 119+ / Edge 119+ / 嵌入式WebView（Android 11+）
- 设备：
  - RK3566：建议720P分辨率（1280×720），内存≥1GB
  - RK3588：建议1080P分辨率（1920×1080），内存≥2GB

### 后端（调度服务）
- Node.js ≥14.0.0
- 服务器：医院内网服务器（2核4GB足够支撑20台设备）

## 部署步骤

### 1. 获取魔珐星云SDK认证信息
1. 登录 [魔珐星云平台](https://xingyun3d.com/)
2. 创建应用，选择数字人角色和语音
3. 在应用详情中获取 `appId` 和 `appSecret`

### 2. 部署后端调度服务
```bash
# 克隆仓库
git clone https://your-git-repo/hospital-digital-human-guide.git
cd hospital-digital-human-guide/backend

# 安装依赖
npm install

# 启动服务（默认端口3000）
npm start
# 开发环境（热重载）：npm run dev
