<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { postJSON } from '../api'
const distance_km = ref(8)
const slow_min = ref(3)
const night = ref(false)
const preview = ref(null)    // 最近一次预览（含时效令牌）
const stale = ref(false)     // 预览之后输入又变更过
const committed = ref(null)  // 落表结果
const error = ref('')
const now = ref(Date.now())
let timer
onMounted(() => { timer = setInterval(() => { now.value = Date.now() }, 1000) })
onUnmounted(() => clearInterval(timer))
watch([distance_km, slow_min, night], () => { if (preview.value) stale.value = true })

const remain = computed(() => preview.value ? Math.max(0, Math.ceil((Date.parse(preview.value.expires_at) - now.value) / 1000)) : 0)
const expired = computed(() => !!preview.value && remain.value <= 0)
const tokenValid = computed(() => !!preview.value && !stale.value && !committed.value && !expired.value)
const status = computed(() => {
  if (!preview.value) return '尚未预览，落表前请先预览'
  if (committed.value) return `已落表 #${committed.value.run_id}，再次落表请重新预览`
  if (stale.value) return '输入已变更，请重新预览'
  if (expired.value) return '令牌已过期，请重新预览'
  return `令牌有效，剩余 ${remain.value} 秒`
})
const errMsg = (e) => { try { return JSON.parse(e.message).detail } catch { return e.message } }

const doPreview = async () => {
  error.value = ''
  try {
    preview.value = await postJSON('/api/fare/preview', { distance_km: distance_km.value, slow_min: slow_min.value, night: night.value })
    stale.value = false
    committed.value = null
  } catch (e) { error.value = errMsg(e) }
}
const doCommit = async () => {
  if (!tokenValid.value) return
  error.value = ''
  const p = preview.value
  try {
    committed.value = await postJSON('/api/fare/commit', {
      token: p.token, distance_km: p.distance_km, slow_min: p.slow_min, night: p.night,
      start: p.start, mileage: p.mileage, slow_fee: p.slow_fee, total: p.total,
    })
  } catch (e) { error.value = errMsg(e) }
}
</script>
<template>
  <div class="page"><h1>打表试算</h1>
    <div class="panel">
      <label>公里 <input type="number" v-model.number="distance_km" /></label>
      <label>低速分钟 <input type="number" v-model.number="slow_min" /></label>
      <label><input type="checkbox" v-model="night" /> 夜间</label>
      <button @click="doPreview">预览</button>
      <button :disabled="!tokenValid" @click="doCommit">落表</button>
    </div>
    <div v-if="preview" class="panel">
      <p class="hero-num">¥{{ preview.total }}</p>
      <p>起步 {{ preview.start }} · 里程 {{ preview.mileage }} · 低速 {{ preview.slow_fee }}</p>
      <p :class="tokenValid ? 'token-ok' : 'token-bad'">令牌：{{ status }}（到期 {{ new Date(Date.parse(preview.expires_at)).toLocaleTimeString() }}）</p>
    </div>
    <p v-if="error" class="token-bad">{{ error }}</p>
  </div>
</template>
