<script setup>
import { computed, onBeforeUnmount, ref } from 'vue'
import { postJSON } from '../api'

const distance_km = ref(8)
const slow_min = ref(3)
const night = ref(false)
const preview = ref(null)    // 最近一次预览：{token, expires_at, ttl_seconds, ...breakdown}
const used = ref(false)      // 当前令牌是否已落表
const committed = ref(null)  // 落表结果 {run_id, total}
const error = ref('')
const now = ref(Date.now())

let timer = null
const startTimer = () => { if (!timer) timer = setInterval(() => { now.value = Date.now() }, 500) }
onBeforeUnmount(() => { if (timer) clearInterval(timer) })

const remainSec = computed(() => preview.value
  ? Math.max(0, Math.ceil((new Date(preview.value.expires_at).getTime() - now.value) / 1000))
  : 0)
const inputsChanged = computed(() => preview.value && (
  Number(distance_km.value) !== preview.value.distance_km ||
  Number(slow_min.value) !== preview.value.slow_min ||
  !!night.value !== !!preview.value.night
))
const tokenState = computed(() => {
  if (!preview.value) return 'none'
  if (used.value) return 'used'
  if (inputsChanged.value) return 'stale'
  if (remainSec.value <= 0) return 'expired'
  return 'valid'
})
const canCommit = computed(() => tokenState.value === 'valid')
const expiresAtText = computed(() => preview.value ? new Date(preview.value.expires_at).toLocaleTimeString() : '')

const doPreview = async () => {
  error.value = ''; committed.value = null; used.value = false
  try {
    preview.value = await postJSON('/api/fare/preview', {
      distance_km: Number(distance_km.value), slow_min: Number(slow_min.value), night: !!night.value,
    })
    startTimer()
  } catch (e) { preview.value = null; error.value = `预览失败：${e.message}` }
}

const doCommit = async () => {
  if (!canCommit.value) return
  error.value = ''
  const p = preview.value
  try {
    committed.value = await postJSON('/api/fare/commit', {
      token: p.token, distance_km: p.distance_km, slow_min: p.slow_min, night: p.night,
      start: p.start, mileage: p.mileage, slow_fee: p.slow_fee, total: p.total,
    })
    used.value = true
  } catch (e) { error.value = `落表被拒绝：${e.message}` }
}
</script>

<template>
  <div class="page"><h1>打表试算</h1>
    <div class="panel">
      <label>公里 <input type="number" v-model.number="distance_km" /></label>
      <label>低速分钟 <input type="number" v-model.number="slow_min" /></label>
      <label><input type="checkbox" v-model="night" /> 夜间</label>
      <button @click="doPreview">预览</button>
      <button @click="doCommit" :disabled="!canCommit">落表</button>
    </div>
    <div v-if="preview" class="panel">
      <p class="hero-num">¥{{ preview.total }}</p>
      <p>起步 {{ preview.start }} · 里程 {{ preview.mileage }} · 低速 {{ preview.slow_fee }}</p>
      <p v-if="tokenState === 'valid'">令牌有效，剩余 {{ remainSec }} 秒（{{ expiresAtText }} 到期）</p>
      <p v-else-if="tokenState === 'expired'" class="warn">令牌已过期，请重新预览后再落表</p>
      <p v-else-if="tokenState === 'stale'" class="warn">参数已修改，与预览不一致，请重新预览</p>
      <p v-else-if="tokenState === 'used'">令牌已使用，再次落表请重新预览</p>
    </div>
    <p v-else class="panel">请先预览获取时效令牌，预览本身不产生记录。</p>
    <p v-if="committed" class="panel">已落表，记录 #{{ committed.run_id }}，应付 ¥{{ committed.total }}</p>
    <p v-if="error" class="panel warn">{{ error }}</p>
  </div>
</template>
