const express = require('express');
const router = express.Router();
const { PythonShell } = require('python-shell'); // 需安装：npm install python-shell

// 获取内存池状态
router.get('/stats', async (req, res) => {
  // 调用python-utils/mofa_memory_pool.py的监控接口
  PythonShell.run('./python-utils/get_stats.py', null, (err, results) => {
    if (err) return res.status(500).json({ error: err.message });
    res.json(JSON.parse(results[0]));
  });
});

module.exports = router;
