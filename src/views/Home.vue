<template>
  <div class="w-full h-full">
    <bpmn url="/example.bpmn" />
  </div>
</template>

<script>
import bpmn from "@/components/bpmn.vue";

export default {
  name: "Home",
  components: {
    bpmn,
  },
  props: {
    options: {
      type: Object,
    }
  },
  data: function() {
    return {
    };
  },
  mounted: function () {
  },
  beforeDestroy: function() {
  },
  watch: {
  },
  methods: {
  },
}
</script>

<style>
</style>
