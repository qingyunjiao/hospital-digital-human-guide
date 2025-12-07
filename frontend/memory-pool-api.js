/**
* 调用Python内存池服务的接口
*/
const MEMORY_POOL_API = "http://localhost:5000/memory-pool";

export async function getMemoryStats() {
  const res = await fetch(`${MEMORY_POOL_API}/stats`);
  return res.json();
}

export async function initScenePool(sceneType) {
  const res = await fetch(`${MEMORY_POOL_API}/init`, {
    method: "POST",
    body: JSON.stringify({ sceneType }),
    headers: { "Content-Type": "application/json" }
  });
  return res.json();
}
