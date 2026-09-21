async function ensureOk(r) {
  if (r.ok) return
  const text = await r.text()
  let msg = text || `HTTP ${r.status}`
  try {
    const j = JSON.parse(text)
    if (typeof j.detail === 'string') msg = j.detail
    else if (j.detail) msg = JSON.stringify(j.detail)
  } catch { /* 非 JSON 响应，保留原文 */ }
  throw new Error(msg)
}
export async function getJSON(path) {
  const r = await fetch(path)
  await ensureOk(r)
  return r.json()
}
export async function postJSON(path, body) {
  const r = await fetch(path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
  await ensureOk(r)
  return r.json()
}
