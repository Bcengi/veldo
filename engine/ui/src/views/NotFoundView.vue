<script setup lang="ts">
import ScreenHeader from '@/components/ScreenHeader.vue'
</script>

<template>
  <section class="screen">
    <ScreenHeader title="No such screen" />
    <div class="state-empty">
      <p class="state-empty-title">This address is not a screen of the factory.</p>
      <p class="state-empty-body"><RouterLink to="/runs">Open the runs</RouterLink> or <RouterLink to="/decisions">the decisions</RouterLink>.</p>
    </div>
  </section>
</template>
