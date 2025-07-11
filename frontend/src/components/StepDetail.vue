<template>
  <div v-if="step" style="margin-left:1.5em;margin-top:0.2em;">
    <details>
      <summary style="color:#bbb;cursor:pointer;">执行详情（Step {{ index+1 }}）</summary>
      <pre style="font-size:0.95em;color:#888;background:#fafbfc;border-radius:4px;padding:0.5em 1em;overflow-x:auto;">{{ JSON.stringify(step, null, 2) }}</pre>
    </details>
  </div>
</template>
<script setup>
defineProps(['step', 'index'])
</script> 