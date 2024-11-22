<template>
	<div class="h-full w-full flex">
		<div ref="container" class="vue-bpmn-diagram-container"></div>
		<div id="properties"></div>
	</div>
</template>

<script>
import axios from "axios";
import BpmnJS from '@/lib/bpmn-js';
import BpmnModeler from '@/lib/bpmn-js/Modeler';
import {BpmnPropertiesPanelModule, BpmnPropertiesProviderModule} from '@/lib/bpmn-js-properties-panel';
import TokenSimulationModule from '@/lib/bpmn-js-token-simulation';
import BpmnColorPickerModule from '@/lib/bpmn-js-color-picker';
import BpmnPipelinePropertiesModule, {PipelineModdleDescriptor, GetPipelineParameters} from '@/lib/bpmn-js-pipeline-properties';
import BpmnAddExporter from '@/lib/bpmn-js-add-exporter';
import { is, getBusinessObject } from 'bpmn-js/lib/util/ModelUtil';
import ApiService from "@/common/api.service";
import parse from 'url-parse';

export default {
  name: "bpmn",
  props: {
    id: {
      type: String,
      required: true,
    },
    url: {
      type: String,
    },
    options: {
      type: Object,
    },
    persistent: {
      type: Boolean,
    }
  },
  data: function() {
    return {
      diagram: null,
      diagramXML: null,
      process: null,
      processUrl: null,
    };
  },
  mounted: function () {
    var self = this;
    console.log("bpmn", this.id, this.persistent);
    
    const PipelineModule = {
      __init__: [
        [ 'eventBus', 'bpmnjs', 'toggleMode', function(eventBus, bpmnjs, toggleMode) {
          if(self.persistent) {
            eventBus.on('commandStack.changed', function() {
              setTimeout(() => {
                bpmnjs.saveXML().then(result => {
                  console.log("xml", result);

                  ApiService.put(`/bpmns/${self.diagram?.id}`, { data: { xml: result.xml }})
                    .then(resp => {
                      console.log(resp);
                    })
                })
              }, 500);
            })
          }
          eventBus.on('diagram.init', 500, () => {
            //toggleMode.toggleMode(true);
          });
          eventBus.on('tokenSimulation.playSimulation', (event) => {
            console.log("tokenSimulation.playSimulation", event);
            self.process = null;
            self.processUrl = null;
          });
          eventBus.on('tokenSimulation.resetSimulation', (event) => {
            console.log("tokenSimulation.resetSimulation", event);
          });
          eventBus.on('tokenSimulation.simulator.trace', (event) => {
            const { action, scope, element } = event;
            const parameters = GetPipelineParameters(element);
            const { url, businessObject } = parameters;

            console.log("tokenSimulation.simulator.trace", action, event);
            if(action != 'signal' && action != 'enter') {
              return;
            }

            if(is(element, 'bpmn:Process')) {
              self.process = element;
              return;
            }
            if(is(element, 'bpmn:StartEvent')) {
              self.processUrl = url;
            }

            if(url) {
              var endpoint = url;
              var pat = /^https?:\/\//i;
              if (!pat.test(url))
              {
                console.log(self.processUrl, parse(self.processUrl, true));
                console.log(url, parse(url, true));
                var a = parse(self.processUrl, true);
                var b = parse(url, true);
                a.pathname = b.pathname;
                a.query = {...a.query, ...b.query}
                endpoint = a.toString();
              }
              console.log("url", endpoint, businessObject);
              const object = {
                id: businessObject['id'],
                type: businessObject['$type'],
                url,
              }
              axios.post(endpoint, { uid: scope.parent ? scope.parent.id : scope.id, did: self.id, object });
            }
          });
        } ]
      ],
    }

    var container = this.$refs.container;

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
        PipelineModule,
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

    ApiService.query(`/bpmns`, { params: { 'filters[uid][$eq]': this.id } }).then(resp => {
      console.log(resp);
      const { data, meta } = resp.data;
      if(!data[0]) throw { message: 'no diagram' };
      const xml = data[0]?.attributes?.xml;
      self.diagram = data[0];
      self.diagramXML = xml;
    }).catch(e => {
      console.error(e);

      const xml = `
<?xml version="1.0" encoding="UTF-8"?>
<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL" xmlns:bpmndi="http://www.omg.org/spec/BPMN/20100524/DI" xmlns:di="http://www.omg.org/spec/DD/20100524/DI" xmlns:dc="http://www.omg.org/spec/DD/20100524/DC" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" id="Definitions_1" targetNamespace="http://bpmn.io/schema/bpmn" exporter="Camunda Modeler" exporterVersion="4.12.0-rc.1-form-semver-maj-mi-pa">
  <bpmn:process id="Process_074u6wt" isExecutable="false">
    <bpmn:startEvent id="StartEvent_1y75d66" />
  </bpmn:process>
  <bpmndi:BPMNDiagram id="BPMNDiagram_1">
    <bpmndi:BPMNPlane id="BPMNPlane_1" bpmnElement="Process_074u6wt">
      <bpmndi:BPMNShape id="_BPMNShape_StartEvent_2" bpmnElement="StartEvent_1y75d66">
        <dc:Bounds x="156" y="82" width="36" height="36" />
      </bpmndi:BPMNShape>
    </bpmndi:BPMNPlane>
  </bpmndi:BPMNDiagram> 
</bpmn:definitions>
      `;

      ApiService.post(`/bpmns`, { data: { uid: this.id, xml }})
        .then(resp => { 
          console.log(resp);
          self.diagram = resp.data?.data;
          self.diagramXML = xml;
        }).catch(e => {
					console.error(e);
          self.diagramXML = xml;
				});
    })
  },

  beforeDestroy: function() {
    this.bpmn.destroy();
  },

  watch: {
    url: function(val) {
      this.$emit('loading');
      //this.fetchDiagram(val);
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
