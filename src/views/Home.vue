<template>
  <div class="w-full h-full">
    <bpmn :id="$route.params.id" :persistent="true" />
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
    console.log(this.$route.params.id);
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
