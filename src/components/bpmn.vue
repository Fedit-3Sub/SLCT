<template>
	<div class="h-full w-full flex">
		<div ref="container" class="vue-bpmn-diagram-container"></div>
		<div id="properties"></div>
	</div>
</template>

<script>
import BpmnJS from '@/lib/bpmn-js';
import BpmnModeler from '@/lib/bpmn-js/Modeler';
import {BpmnPropertiesPanelModule, BpmnPropertiesProviderModule} from '@/lib/bpmn-js-properties-panel';
import TokenSimulationModule from '@/lib/bpmn-js-token-simulation';
import BpmnColorPickerModule from '@/lib/bpmn-js-color-picker';
import BpmnPipelinePropertiesModule, {PipelineModdleDescriptor} from '@/lib/bpmn-js-pipeline-properties';
import BpmnAddExporter from '@/lib/bpmn-js-add-exporter';

export default {
  name: "bpmn",
  props: {
    url: {
      type: String,
      required: true,
    },
    options: {
      type: Object,
    }
  },
  data: function() {
    return {
      diagramXML: null
    };
  },
  mounted: function () {
    var container = this.$refs.container;

    var self = this;
    var _options = Object.assign({
      container: container,
			propertiesPanel: {
				parent: '#properties'
			},
			additionalModules: [
				BpmnPropertiesPanelModule,
				BpmnPropertiesProviderModule,
				TokenSimulationModule,
				BpmnColorPickerModule,
        BpmnPipelinePropertiesModule,
        BpmnAddExporter,
			],
      moddleExtensions: {
        pipeline: PipelineModdleDescriptor
      },
      exporter: {
        name: 'kt-bpmn',
        version: '1.0.0'
      },      
    }, this.options);

		this.bpmn = new BpmnModeler(_options);
    this.bpmn.on('import.done', function(event) {
      var error = event.error;
      var warnings = event.warnings;

      if (error) {
        self.$emit('error', error);
      } else {
        self.$emit('shown', warnings);
      }

      self.bpmn.get('canvas').zoom('fit-viewport');
    });

    if (this.url) {
      this.fetchDiagram(this.url);
    }
  },

  beforeDestroy: function() {
    this.bpmn.destroy();
  },

  watch: {
    url: function(val) {
      this.$emit('loading');
      this.fetchDiagram(val);
    },
    diagramXML: function(val) {
      this.bpmn.importXML(val);
    }
  },
	
  methods: {
    fetchDiagram: function(url) {
      var self = this;
      fetch(url)
        .then(function(response) {
          return response.text();
        })
        .then(function(text) {
          self.diagramXML = text;
        })
        .catch(function(err) {
          self.$emit('error', err);
        });
    }
  }  
}
</script>

<style>
  .vue-bpmn-diagram-container {
    height: 100%;
    width: 100%;
  }
	#properties {
		width: 300px;
	}
</style>
