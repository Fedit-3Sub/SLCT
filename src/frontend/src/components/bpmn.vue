<template>
  <div class="h-full w-full flex">
    <div ref="container" class="vue-bpmn-diagram-container"></div>
    <aside class="bpmn-sidebar">
      <section class="bpmn-tools">
        <header class="bpmn-tools__header">
          <span class="bpmn-tools__title">도구모음</span>
          <span :class="['bpmn-tools__badge', backendHealthy ? 'bpmn-tools__badge--ok' : 'bpmn-tools__badge--error']">
            {{ appVersion }}
          </span>
        </header>

        <div class="bpmn-quick-grid">
          <button
            class="bpmn-quick-btn"
            @click="onUndo"
            :disabled="!canUndo"
            title="마지막 변경을 되돌립니다"
          >
            <span class="bpmn-quick-btn__icon">↶</span>
            <span class="bpmn-quick-btn__label">되돌리기</span>
          </button>
          <button
            class="bpmn-quick-btn"
            @click="onRedo"
            :disabled="!canRedo"
            title="되돌린 변경을 다시 적용합니다"
          >
            <span class="bpmn-quick-btn__icon">↷</span>
            <span class="bpmn-quick-btn__label">다시 실행</span>
          </button>
          <button
            class="bpmn-quick-btn"
            @click="onResetView"
            title="다이어그램 뷰를 초기화합니다"
          >
            <span class="bpmn-quick-btn__icon">⤢</span>
            <span class="bpmn-quick-btn__label">뷰 리셋</span>
          </button>
          <button
            class="bpmn-quick-btn"
            @click="onDownloadXml"
            title="현재 다이어그램을 XML로 내려받습니다"
          >
            <span class="bpmn-quick-btn__icon">⬇</span>
            <span class="bpmn-quick-btn__label">XML 내보내기</span>
          </button>
          <button
            class="bpmn-quick-btn"
            @click="openUnifiedSearch()"
            title="통합 검색(Spotlight) 열기 (Ctrl/Cmd+F 또는 K)"
          >
            <span class="bpmn-quick-btn__icon">🔎</span>
            <span class="bpmn-quick-btn__label">검색</span>
          </button>
          <label
            class="bpmn-quick-btn"
            title="BPMN/XML 파일을 업로드하여 불러옵니다"
          >
            <input ref="fileInput" type="file" accept=".bpmn,.xml" @change="onFileChange" class="hidden-input" />
            <span class="bpmn-quick-btn__icon">⬆</span>
            <span class="bpmn-quick-btn__label">XML 불러오기</span>
          </label>
        </div>
      </section>

      <section class="bpmn-accordion">
        <button class="bpmn-accordion-header" type="button" @click="toggleAccordion('assistant')">
          <span>서비스로직 생성 AI</span>
          <span :class="['bpmn-accordion-icon', { 'bpmn-accordion-icon--open': accordionOpen.assistant }]">▼</span>
        </button>
        <div class="bpmn-accordion-body" v-show="accordionOpen.assistant">
          <div class="copilot-chat">
            <div class="copilot-chat__toolbar">
              <div class="copilot-toolbar-left">
                <label class="copilot-llm-selector" :class="{ 'copilot-llm-selector--disabled': !llmOptions.length }">
                  <span class="copilot-llm-icon">⚙</span>
                  <select
                    v-model="selectedLlm"
                    :disabled="!llmOptions.length"
                    @change="onChangeLlm"
                  >
                    <option v-if="!llmOptions.length" value="" disabled>
                      등록된 LLM이 없습니다
                    </option>
                    <option
                      v-for="option in llmOptions"
                      :key="option.id"
                      :value="option.id"
                    >
                      {{ option.label }}
                    </option>
                  </select>
                </label>
              </div>
              <button
                class="copilot-toolbar-reset"
                type="button"
                @click="resetCopilot"
                :disabled="aiBusy || copilotMessages.length === 0"
              >
                대화 초기화
              </button>
            </div>

            <div class="copilot-chat__history" ref="copilotHistory">
              <div v-if="copilotMessages.length === 0" class="copilot-empty">
                <strong>서비스 로직을 AI와 함께 설계해보세요.</strong>
                <span>추천 요청을 선택하거나 메시지를 입력하면 AI가 필요한 워크플로를 제안합니다.</span>
              </div>
              <div
                v-else
                v-for="(message, index) in copilotMessages"
                :key="index"
                :class="['copilot-bubble', `copilot-bubble--${message.role}`, message.pending ? 'copilot-bubble--pending' : '']"
              >
                <div class="copilot-bubble__role">
                  {{ message.role === 'assistant' ? 'AI' : '사용자' }}
                </div>
                <div class="copilot-bubble__content">
                  <template v-if="message.parts && message.parts.length">
                    <component
                      v-for="(part, partIndex) in message.parts"
                      :key="`copilot-part-${partIndex}`"
                      :is="part.type === 'code' ? 'pre' : 'div'"
                      :class="[
                        part.type === 'code'
                          ? 'copilot-bubble__code'
                          : part.type === 'table'
                            ? 'copilot-bubble__table-wrapper'
                            : 'copilot-bubble__text'
                      ]"
                    >
                      <template v-if="part.type === 'table'">
                        <table class="copilot-bubble__table">
                          <thead>
                            <tr>
                              <th v-for="(header, headerIndex) in part.headers" :key="`copilot-part-${partIndex}-header-${headerIndex}`">
                                {{ header }}
                              </th>
                            </tr>
                          </thead>
                          <tbody>
                            <tr v-for="(row, rowIndex) in part.rows" :key="`copilot-part-${partIndex}-row-${rowIndex}`">
                              <td v-for="(cell, cellIndex) in row" :key="`copilot-part-${partIndex}-row-${rowIndex}-cell-${cellIndex}`">
                                {{ cell }}
                              </td>
                            </tr>
                          </tbody>
                        </table>
                      </template>
                      <template v-else-if="part.type === 'code'">
                        <code>{{ part.content }}</code>
                      </template>
                      <template v-else>
                        {{ part.content }}
                      </template>
                    </component>
                  </template>
                  <template v-else>
                    {{ message.content }}
                  </template>
                </div>
              </div>
            </div>

            <div class="copilot-quick-actions">
              <span class="copilot-quick-actions__label">추천 요청</span>
              <div class="copilot-quick-actions__list">
                <button
                  v-for="(preset, index) in condensedPrompts"
                  :key="index"
                  class="copilot-quick-actions__item"
                  type="button"
                  @click="applyQuickPrompt(preset.original)"
                  :title="preset.original"
                >
                  {{ preset.short }}
                </button>
              </div>
            </div>

            <div v-if="pendingXml" class="copilot-pending">
              <span class="copilot-pending__text">
                {{ pendingXmlSource ? `${pendingXmlSource}에서 생성된 BPMN XML이 대기 중입니다.` : 'AI가 제안한 BPMN XML이 대기 중입니다.' }}
              </span>
              <div class="copilot-pending__actions">
                <button type="button" class="copilot-pending__apply" @click="applyPendingXml">
                  적용
                </button>
                <button type="button" class="copilot-pending__dismiss" @click="clearPendingXml">
                  무시
                </button>
              </div>
            </div>

            <form class="copilot-chat__composer" @submit.prevent="submitCopilot">
              <div class="copilot-composer-field">
                <textarea
                  id="copilotPrompt"
                  v-model="copilotPrompt"
                  class="copilot-composer-textarea"
                  rows="3"
                  placeholder="워크플로 요구사항을 입력하세요. (Enter 전송, Shift+Enter 줄바꿈)"
                  @keydown.enter.exact.prevent="submitCopilot"
                />
                <button
                  class="copilot-composer-send"
                  type="submit"
                  :disabled="!copilotPrompt.trim() || aiBusy"
                >
                  {{ aiBusy ? '전송 중...' : '전송' }}
                </button>
              </div>
            </form>
          </div>
        </div>
      </section>

      <section class="bpmn-accordion">
        <button class="bpmn-accordion-header" type="button" @click="toggleAccordion('layout')">
          <span>레이아웃 최적화</span>
          <span :class="['bpmn-accordion-icon', { 'bpmn-accordion-icon--open': accordionOpen.layout }]">▼</span>
        </button>
        <div class="bpmn-accordion-body" v-show="accordionOpen.layout">
          <p class="bpmn-ai-helper">
            배치 전략을 선택하면 현재 다이어그램을 분석해 자동으로 정리합니다.
          </p>
          <div class="layout-options">
            <label
              v-for="option in layoutOptions"
              :key="option.value"
              class="layout-option"
              :class="{ 'layout-option--active': layoutStrategy === option.value }"
            >
              <input
                class="layout-option__input"
                type="radio"
                name="layout-strategy"
                :value="option.value"
                v-model="layoutStrategy"
              />
              <div class="layout-option__body">
                <div class="layout-option__label">{{ option.label }}</div>
                <div class="layout-option__description">{{ option.description }}</div>
              </div>
            </label>
          </div>
          <div class="bpmn-ai-actions">
            <button
              class="bpmn-btn bpmn-btn--primary"
              type="button"
              @click="triggerBeautify"
              :disabled="aiBusy"
            >
              {{ aiBusy ? '분석 중...' : '레이아웃 적용' }}
            </button>
          </div>
        </div>
      </section>

      <div id="properties" class="bpmn-properties"></div>
    </aside>
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
import { layoutProcess } from 'bpmn-auto-layout';

const APP_VERSION = import.meta.env.VITE_APP_VERSION || 'alpha';
const DEFAULT_DIAGRAM_XML = `
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
      searchKeyHandler: null,
      diagramXML: null,
      process: null,
      processUrl: null,
      importing: false,
      // autosave controls
      saveTimer: null,
      saveDebounceMs: 800,
      saving: false,
      copilotPrompt: "",
      copilotMessages: [],
      aiBusy: false,
      accordionOpen: {
        assistant: true,
        layout: false,
      },
      quickPrompts: [
        "관광객 혼잡도를 완화할 실시간 대응 플로우를 만들어줘",
        "기상 센서 이상을 감지하면 경보와 복구 시나리오를 실행하도록 구성해줘",
        "교통 사고 발생 시 관련 기관에 통합 알림을 보내는 프로세스를 설계해줘",
      ],
      condensedPrompts: [],
      llmOptions: [],
      selectedLlm: null,
      appVersion: APP_VERSION,
      backendHealthy: true,
      pendingXml: null,
      pendingXmlSource: null,
      aiUndoStack: [],
      aiRedoStack: [],
      skipDiagramImport: false,
      layoutStrategy: "auto-balance",
      layoutOptions: [
        {
          value: "auto-balance",
          label: "스마트 간격 정리",
          description: "현재 흐름을 유지하면서 노드 간 간격과 정렬을 자동 보정합니다.",
        },
        {
          value: "horizontal-flow",
          label: "수평 플로우",
          description: "좌→우 흐름으로 주요 액터를 한 눈에 볼 수 있도록 정렬합니다.",
        },
        {
          value: "grid-pack",
          label: "격자 정렬",
          description: "연결 관계를 유지하면서 격자 기준으로 단계를 압축 배치합니다.",
        },
      ],
      canUndo: false,
      canRedo: false,
      commandStackListener: null,
      eventBusRef: null,
    };
  },
  mounted: function () {
    var self = this;
    console.log("bpmn", this.id, this.persistent);
    this.prepareCondensedPrompts();
    this.fetchLlmOptions();

    const PipelineModule = {
      __init__: [
        [ 'eventBus', 'bpmnjs', 'toggleMode', function(eventBus, bpmnjs, toggleMode) {
          if (self.persistent) {
            eventBus.on('commandStack.changed', function() {
              // queue debounced save to backend
              self.queueSave();
            });
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
    const eventBus = this.bpmn.get('eventBus');
    const commandStack = this.bpmn.get('commandStack');
    const updateHistoryState = () => {
      this.canUndo = commandStack && commandStack.canUndo ? commandStack.canUndo() : false;
      this.canRedo = commandStack && commandStack.canRedo ? commandStack.canRedo() : false;
    };
    eventBus.on('commandStack.changed', updateHistoryState);
    this.commandStackListener = updateHistoryState;
    this.eventBusRef = eventBus;
    updateHistoryState();

    // Register global shortcut for search (Ctrl/Cmd+F or Ctrl/Cmd+K)
    this.searchKeyHandler = (e) => {
      try {
        const isMac = /Mac|iPod|iPhone|iPad/.test(navigator.platform);
        const cmd = isMac ? e.metaKey : e.ctrlKey;
        const key = (e.key || '').toLowerCase();
        if (cmd && (key === 'f' || key === 'k')) {
          e.preventDefault();
          this.openUnifiedSearch();
        }
      } catch (err) {
        // no-op
      }
    };
    window.addEventListener('keydown', this.searchKeyHandler);

    this.bpmn.on('import.done', function(event) {
      var error = event.error;
      var warnings = event.warnings;

      if (error) {
        self.$emit('error', error);
      } else {
        self.$emit('shown', warnings);
      }

      self.bpmn.get('canvas').zoom('fit-viewport');

      // if XML was imported via our custom menu, persist it once
      if (self.persistent && self.importing && self.diagram && self.diagram.id) {
        ApiService.put(`/bpmns/${self.diagram.id}`, { data: { xml: self.diagramXML }})
          .catch(function(e){ console.error(e); })
          .finally(function(){ self.importing = false; });
      } else {
        self.importing = false;
      }
    });

    ApiService.query(`/bpmns`, { params: { 'filters[uid][$eq]': this.id } }).then(resp => {
      console.log(resp);
      const { data, meta } = resp.data;
      if(!data[0]) throw { message: 'no diagram' };
      const xml = data[0]?.attributes?.xml;
      self.diagram = data[0];
      self.diagramXML = xml;
      self.prepareCondensedPrompts();
      self.fetchLlmOptions();
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
          self.diagram = resp.data && resp.data.data;
          self.diagramXML = xml;
        }).catch(e => {
				console.error(e);
          self.diagramXML = xml;
			});
      self.prepareCondensedPrompts();
      self.fetchLlmOptions();
    })
    .catch(() => {
      self.prepareCondensedPrompts();
      self.fetchLlmOptions();
    })
  },

  beforeDestroy: function() {
    if (this.searchKeyHandler) {
      window.removeEventListener('keydown', this.searchKeyHandler);
      this.searchKeyHandler = null;
    }
    if (this.eventBusRef && this.commandStackListener) {
      this.eventBusRef.off('commandStack.changed', this.commandStackListener);
    }
    this.bpmn.destroy();
  },

  watch: {
    url: function(val) {
      this.$emit('loading');
      //this.fetchDiagram(val);
    },
    diagramXML: function(val) {
      if (this.skipDiagramImport) {
        return;
      }
      const importPromise = this.bpmn.importXML(val);
      if (importPromise && typeof importPromise.catch === 'function') {
        importPromise.catch((err) => {
          console.error('Failed to import XML via watcher', err);
        });
      }
    }
  },

  methods: {
    // Resolve diagram id by uid if missing
    async ensureDiagramId() {
      if (this?.diagram && this.diagram.id) return this.diagram.id;
      try {
        const resp = await ApiService.query(`/bpmns`, { params: { 'filters[uid][$eq]': this.id } });
        const items = (resp && resp.data && resp.data.data) || [];
        if (items[0] && items[0].id) {
          this.diagram = items[0];
          return items[0].id;
        }
      } catch (e) {
        console.warn('ensureDiagramId: lookup failed', e);
      }
      // If not found, create it with current XML (or blank template)
      try {
        const xmlToSave = this.diagramXML || (await this.bpmn.saveXML()).xml;
        const resp = await ApiService.post(`/bpmns`, { data: { uid: this.id, xml: xmlToSave } });
        if (resp && resp.data && resp.data.data && resp.data.data.id) {
          this.diagram = resp.data.data;
          return this.diagram.id;
        }
      } catch (e) {
        console.warn('ensureDiagramId: create failed', e);
      }
      return null;
    },

    // Debounced save trigger
    queueSave() {
      if (!this.persistent) return;
      if (this.importing) return; // skip while importing XML
      if (this.saveTimer) clearTimeout(this.saveTimer);
      this.saveTimer = setTimeout(() => {
        this.saveTimer = null;
        this.saveDiagram();
      }, this.saveDebounceMs);
    },

    async saveDiagram() {
      try {
        if (this.importing) return;
        this.saving = true;
        const { xml } = await this.bpmn.saveXML();
        // make sure we have a numeric id
        const id = await this.ensureDiagramId();
        if (!id) {
          console.warn('saveDiagram: cannot resolve diagram id');
          return;
        }
        await ApiService.put(`/bpmns/${id}`, { data: { xml } });
      } catch (e) {
        console.warn('saveDiagram: failed to save', e);
      } finally {
        this.saving = false;
      }
    },
    openUnifiedSearch() {
      try {
        // prefer direct searchPad access, fallback to editorActions
        const searchPad = this.bpmn && this.bpmn.get && this.bpmn.get('searchPad', false);
        const editorActions = this.bpmn && this.bpmn.get && this.bpmn.get('editorActions');

        if (searchPad && typeof searchPad.toggle === 'function') {
          searchPad.toggle();
        } else if (editorActions && typeof editorActions.trigger === 'function') {
          editorActions.trigger('find');
        }

        const focusInput = () => {
          const canvas = this.bpmn && this.bpmn.get && this.bpmn.get('canvas');
          const container = canvas && canvas.getContainer && canvas.getContainer();
          let input = null;
          if (container && container.querySelector) {
            // support both popup-menu search and search-pad input
            input = container.querySelector('.djs-popup-search input, .djs-search-input input, .djs-search-input');
          }
          if (!input) {
            input = document.querySelector('.djs-popup-search input, .djs-search-input input, .djs-search-input');
          }
          if (input) {
            input.focus();
            if (typeof input.select === 'function') {
              input.select();
            }
            return true;
          }
          return false;
        };

        // try immediately, then retry shortly after to catch async render
        if (!focusInput()) {
          setTimeout(() => {
            if (!focusInput()) {
              setTimeout(() => {
                focusInput();
              }, 150);
            }
          }, 50);
        }
      } catch (e) {
        console.error('Failed to open search', e);
      }
    },
    createCopilotMessage(role, content, options = {}) {
      const text = typeof content === 'string' ? content : (content != null ? String(content) : '');
      const { pending = false, suppressXml = false, ...rest } = options;
      const parts = this.parseMessageContent(text, { suppressXml });
      return {
        role,
        content: text,
        parts,
        pending,
        ...rest,
      };
    },
    parseMessageContent(text, { suppressXml } = {}) {
      if (!text) {
        return [];
      }
      const parts = [];
      const codeBlockRegex = /```(\w+)?\s*([\s\S]*?)```/g;
      let lastIndex = 0;
      let match;

      while ((match = codeBlockRegex.exec(text)) !== null) {
        const preceding = text.slice(lastIndex, match.index);
        this.appendTextBlocks(parts, preceding);

        const language = (match[1] || '').trim().toLowerCase();
        const codeContent = (match[2] || '').trim();
        const isXmlBlock = language === 'xml' || codeContent.includes('<bpmn:');
        if (suppressXml && isXmlBlock) {
          lastIndex = codeBlockRegex.lastIndex;
          continue;
        }

        parts.push({
          type: 'code',
          language: language || null,
          content: codeContent,
        });
        lastIndex = codeBlockRegex.lastIndex;
      }

      const remainder = text.slice(lastIndex);
      this.appendTextBlocks(parts, remainder);

      return parts.length ? parts : [{ type: 'text', content: text }];
    },
    appendTextBlocks(parts, chunk) {
      if (!chunk) {
        return;
      }
      const blocks = chunk.split(/\n{2,}/);
      blocks.forEach((block) => {
        const trimmed = block.trim();
        if (!trimmed) {
          return;
        }
        if (this.looksLikeMarkdownTable(trimmed)) {
          const table = this.parseMarkdownTable(trimmed);
          if (table) {
            parts.push({
              type: 'table',
              headers: table.headers,
              rows: table.rows,
            });
            return;
          }
        }
        parts.push({
          type: 'text',
          content: this.normalizeInlineMarkdown(trimmed),
        });
      });
    },
    looksLikeMarkdownTable(block) {
      const lines = block.split('\n').map((line) => line.trim());
      if (lines.length < 2) {
        return false;
      }
      if (!lines[0].startsWith('|') || !lines[0].endsWith('|')) {
        return false;
      }
      const separator = lines[1].replace(/[\|\s:\-]/g, '');
      if (separator.length !== 0) {
        return false;
      }
      return true;
    },
    parseMarkdownTable(block) {
      const lines = block.split('\n').map((line) => line.trim()).filter(Boolean);
      if (lines.length < 2) {
        return null;
      }
      const headers = lines[0].split('|').slice(1, -1).map((cell) => this.normalizeInlineMarkdown(cell.trim()));
      const rows = [];
      for (let i = 2; i < lines.length; i += 1) {
        const line = lines[i];
        if (!line || !line.includes('|')) {
          continue;
        }
        const cells = line.split('|').slice(1, -1).map((cell) => this.normalizeInlineMarkdown(cell.trim()));
        if (cells.length) {
          rows.push(cells);
        }
      }
      if (!headers.length && !rows.length) {
        return null;
      }
      return { headers, rows };
    },
    normalizeInlineMarkdown(text) {
      if (!text) {
        return '';
      }
      return text
        .replace(/\*\*(.+?)\*\*/g, '$1')
        .replace(/__(.+?)__/g, '$1')
        .replace(/`(.+?)`/g, '$1');
    },
    toggleAccordion(key) {
      this.accordionOpen[key] = !this.accordionOpen[key];
    },
    onUndo() {
      const commandStack = this.bpmn && this.bpmn.get && this.bpmn.get('commandStack');
      if (commandStack && commandStack.canUndo && commandStack.canUndo()) {
        commandStack.undo();
        if (typeof this.commandStackListener === 'function') {
          this.commandStackListener();
        }
      } else if (this.aiUndoStack.length) {
        const previousXml = this.aiUndoStack.pop();
        this.aiRedoStack.push(this.diagramXML);
        this.setDiagramXml(previousXml, 'AI 적용을 되돌렸습니다.');
      }
    },
    onRedo() {
      const commandStack = this.bpmn && this.bpmn.get && this.bpmn.get('commandStack');
      if (commandStack && commandStack.canRedo && commandStack.canRedo()) {
        commandStack.redo();
        if (typeof this.commandStackListener === 'function') {
          this.commandStackListener();
        }
      } else if (this.aiRedoStack.length) {
        const nextXml = this.aiRedoStack.pop();
        this.aiUndoStack.push(this.diagramXML);
        this.setDiagramXml(nextXml, 'AI 적용을 다시 실행했습니다.');
      }
    },
    onResetView() {
      const canvas = this.bpmn && this.bpmn.get && this.bpmn.get('canvas');
      const expectedId = `${this.diagram?.attributes?.uid || this.id || ''}`.trim();
      if (!expectedId) {
        window.alert('뷰 식별자를 찾을 수 없어 초기화를 진행할 수 없습니다.');
        return;
      }
      const input = window.prompt(`뷰를 초기화하려면 아래 식별자를 입력하세요.\n\n${expectedId}`, '');
      if (input === null) {
        return;
      }
      if (input.trim() !== expectedId) {
        window.alert('입력한 값이 일치하지 않습니다. 뷰 초기화를 취소합니다.');
        return;
      }
      if (canvas) {
        canvas.zoom('fit-viewport');
        if (canvas.center) {
          canvas.center();
        }
        window.alert('뷰를 초기화했습니다.');
      }
    },
    onDownloadXml: async function() {
      try {
        const result = await this.bpmn.saveXML({ format: true });
        const xml = result.xml;
        const blob = new Blob([xml], { type: 'application/xml' });
        const link = document.createElement('a');
        var uid = this.diagram && this.diagram.attributes && this.diagram.attributes.uid;
        var base = uid || (this.diagram && this.diagram.id) || this.id;
        const filename = `${base}.bpmn`;
        link.href = URL.createObjectURL(blob);
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(link.href);
      } catch (e) {
        console.error(e);
        this.$emit('error', e);
      }
    },
    submitCopilot() {
      if (!this.copilotPrompt.trim() || this.aiBusy) {
        return;
      }
      const prompt = this.copilotPrompt.trim();
      this.copilotMessages.push(this.createCopilotMessage('user', prompt));
      this.copilotPrompt = "";
      this.aiBusy = true;
      this.scrollCopilotToBottom();

      const payload = {
        prompt,
        diagramId: this.diagram?.id ?? null,
        diagramUid: this.diagram?.attributes?.uid ?? this.id,
        llmId: this.selectedLlm,
      };

      const pendingMessage = this.createCopilotMessage('assistant', 'AI 응답을 생성 중입니다...', { pending: true });
      this.copilotMessages.push(pendingMessage);
      const pendingIndex = this.copilotMessages.length - 1;

      ApiService.post('/llm/copilot', payload)
        .then(({ data }) => {
          const message = data?.data?.message || "응답을 해석할 수 없습니다.";
          const generatedXml = data?.data?.generatedXml;
          const summary = data?.data?.nodeSummary;
          const assistantMessage = this.createCopilotMessage('assistant', message, {
            pending: false,
            suppressXml: !!generatedXml,
          });
          if (!assistantMessage.parts.length) {
            assistantMessage.parts = [{ type: 'text', content: 'AI가 응답을 반환했지만 표시할 내용이 없습니다.' }];
          }
          this.$set(this.copilotMessages, pendingIndex, assistantMessage);
          if (generatedXml) {
            this.handleSuggestedXml(generatedXml, 'AI 제안', summary);
          } else if (summary) {
            this.copilotMessages.push(this.createCopilotMessage('assistant', summary));
          }
          this.scrollCopilotToBottom();
        })
        .catch((error) => {
          const message =
            error?.response?.data?.message ||
            error?.response?.data?.error ||
            error?.message ||
            '알 수 없는 오류가 발생했습니다.';
          const errorMessage = this.createCopilotMessage('assistant', `요청이 실패했습니다: ${message}`);
          this.$set(this.copilotMessages, pendingIndex, errorMessage);
          this.scrollCopilotToBottom();
        })
        .finally(() => {
          this.aiBusy = false;
        });
    },
    resetCopilot() {
      if (this.aiBusy) {
        return;
      }
      this.copilotPrompt = "";
      this.copilotMessages = [];
      this.$emit('copilot-reset');
      this.pendingXml = null;
      this.pendingXmlSource = null;
      this.scrollCopilotToBottom();
    },
    applyQuickPrompt(prompt) {
      if (this.aiBusy) return;
      this.copilotPrompt = prompt;
      if (!this.accordionOpen.assistant) {
        this.toggleAccordion('assistant');
      }
      this.$nextTick(() => {
        this.submitCopilot();
      });
    },
    triggerBeautify() {
      if (this.aiBusy) {
        return;
      }
      const strategy = this.layoutStrategy;
      this.aiBusy = true;

      const pendingMessage = this.createCopilotMessage('assistant', `선택한 전략(${strategy})으로 레이아웃을 적용하는 중입니다...`, { pending: true });
      this.copilotMessages.push(pendingMessage);
      const pendingIndex = this.copilotMessages.length - 1;

      this.$nextTick(() => {
        setTimeout(() => {
          try {
            const result = this.performLayout(strategy);
            const movedCount = result?.movedCount ?? 0;
            const relayoutCount = result?.relayoutConnections ?? 0;
            const assistantMessage = this.createCopilotMessage(
              'assistant',
              `레이아웃을 적용했습니다. 이동한 노드: ${movedCount}개, 연결 재배치: ${relayoutCount}개.`
            );
            this.$set(this.copilotMessages, pendingIndex, assistantMessage);
            this.scrollCopilotToBottom();
          } catch (error) {
            console.error('레이아웃 적용 중 오류', error);
            const message = error?.message || '알 수 없는 오류가 발생했습니다.';
            const errorMessage = this.createCopilotMessage('assistant', `레이아웃 적용이 실패했습니다: ${message}`);
            this.$set(this.copilotMessages, pendingIndex, errorMessage);
            this.scrollCopilotToBottom();
          } finally {
            this.aiBusy = false;
          }
        }, 0);
      });
    },

    performLayout(strategy) {
      const elementRegistry = this.bpmn.get('elementRegistry');
      const modeling = this.bpmn.get('modeling');
      const canvas = this.bpmn.get('canvas');

      const all = elementRegistry.getAll();
      const shapes = all.filter(el => !el.waypoints && !el.labelTarget);
      const groups = this._groupLayoutTargets(shapes);

      let movedCount = 0;

      for (const group of groups) {
        if (!group.nodes.length) continue;
        try {
          switch (strategy) {
            case 'horizontal-flow':
              movedCount += this._layoutHorizontalFlow(group, modeling);
              break;
            case 'grid-pack':
              movedCount += this._layoutGridPack(group, modeling);
              break;
            case 'auto-balance':
            default:
              movedCount += this._layoutAutoBalance(group, modeling);
              break;
          }
        } catch (e) {
          console.error('그룹 레이아웃 실패', e);
        }
      }

      // Re-layout sequence flows after moves
      const connections = all.filter(el => el.waypoints && el.businessObject && el.businessObject.$type === 'bpmn:SequenceFlow');
      let relayoutCount = 0;
      for (const c of connections) {
        try {
          modeling.layoutConnection(c);
          relayoutCount++;
        } catch (e) {
          // ignore
        }
      }

      // Fit viewport to updated diagram
      try { canvas.zoom('fit-viewport'); } catch (_) {}

      return { movedCount, relayoutConnections: relayoutCount };
    },

    _groupLayoutTargets(shapes) {
      // consider only FlowNodes and exclude Pools/Lanes/Labels
      const nodes = shapes.filter(s => s.businessObject && (is(s, 'bpmn:FlowNode')));

      function findContainer(el) {
        let p = el.parent;
        while (p && p.parent) {
          if (p.businessObject && (is(p, 'bpmn:Participant') || is(p, 'bpmn:Process') || is(p, 'bpmn:SubProcess') || is(p, 'bpmn:Lane'))) {
            return p;
          }
          p = p.parent;
        }
        return el.parent || null;
      }

      const byId = new Map();
      for (const n of nodes) {
        const container = findContainer(n);
        const key = container ? container.id : 'root';
        if (!byId.has(key)) byId.set(key, { id: key, container, nodes: [] });
        byId.get(key).nodes.push(n);
      }
      return Array.from(byId.values());
    },

    _layoutHorizontalFlow(group, modeling) {
      const nodes = group.nodes.slice();
      const idIndex = new Map(nodes.map((n, i) => [n.id, i]));

      // Build graph based on SequenceFlow
      const outgoing = new Map();
      const indeg = new Map(nodes.map(n => [n.id, 0]));
      for (const n of nodes) {
        const outs = (n.outgoing || []).filter(c => c.businessObject && c.businessObject.$type === 'bpmn:SequenceFlow' && c.target && idIndex.has(c.target.id));
        outgoing.set(n.id, outs.map(c => c.target.id));
      }
      for (const [u, vs] of outgoing.entries()) {
        for (const v of vs) indeg.set(v, (indeg.get(v) || 0) + 1);
      }

      // roots: StartEvents preferred else indegree 0
      const roots = nodes.filter(n => is(n, 'bpmn:StartEvent'));
      const zeroIn = nodes.filter(n => (indeg.get(n.id) || 0) === 0 && !is(n, 'bpmn:StartEvent'));
      const queue = [...roots, ...zeroIn];
      const level = new Map();
      for (const r of queue) level.set(r.id, 0);

      // BFS levels
      for (let i = 0; i < queue.length; i++) {
        const u = queue[i];
        const lu = level.get(u.id) || 0;
        const vs = outgoing.get(u.id) || [];
        for (const vid of vs) {
          if (!level.has(vid)) {
            level.set(vid, lu + 1);
            const v = nodes[idIndex.get(vid)];
            queue.push(v);
          }
        }
      }
      // any unvisited -> assign trailing levels
      for (const n of nodes) {
        if (!level.has(n.id)) level.set(n.id, 0);
      }

      // group by level
      const byLvl = new Map();
      for (const n of nodes) {
        const lv = level.get(n.id) || 0;
        if (!byLvl.has(lv)) byLvl.set(lv, []);
        byLvl.get(lv).push(n);
      }
      const levels = Array.from(byLvl.keys()).sort((a,b)=>a-b);

      const H_SPACING = 280;
      const V_SPACING = 120;
      const MARGIN_X = 40;
      const MARGIN_Y = 40;

      // base from container bounds if available
      let baseX = MARGIN_X;
      let baseY = MARGIN_Y;
      if (group.container) {
        baseX = (group.container.x || 0) + MARGIN_X;
        baseY = (group.container.y || 0) + MARGIN_Y;
      }

      let moved = 0;
      let col = 0;
      for (const lv of levels) {
        const colNodes = byLvl.get(lv);
        // stable order by current y
        colNodes.sort((a,b)=> (a.y||0) - (b.y||0));
        const x = this._snap(baseX + col * H_SPACING);
        let y = this._snap(baseY);
        for (let i=0;i<colNodes.length;i++) {
          const n = colNodes[i];
          const ny = this._snap(baseY + i * V_SPACING);
          moved += this._moveShape(n, x, ny, modeling);
        }
        col++;
      }
      return moved;
    },

    _layoutGridPack(group, modeling) {
      const nodes = group.nodes.slice();
      // sort by type then id for stability
      nodes.sort((a,b)=>{
        const at = a.businessObject && a.businessObject.$type || '';
        const bt = b.businessObject && b.businessObject.$type || '';
        if (at === bt) return a.id.localeCompare(b.id);
        return at.localeCompare(bt);
      });

      const CELL_W = 220;
      const CELL_H = 130;
      const MARGIN_X = 40;
      const MARGIN_Y = 40;

      let baseX = MARGIN_X;
      let baseY = MARGIN_Y;
      if (group.container) {
        baseX = (group.container.x || 0) + MARGIN_X;
        baseY = (group.container.y || 0) + MARGIN_Y;
      }

      const cols = Math.max(1, Math.ceil(Math.sqrt(nodes.length)));
      let moved = 0;
      nodes.forEach((n, idx) => {
        const r = Math.floor(idx / cols);
        const c = idx % cols;
        const x = this._snap(baseX + c * CELL_W);
        const y = this._snap(baseY + r * CELL_H);
        moved += this._moveShape(n, x, y, modeling);
      });
      return moved;
    },

    _layoutAutoBalance(group, modeling) {
      // simple overlap resolver preserving approximate x ordering
      const nodes = group.nodes.slice().sort((a,b)=> (a.x||0) - (b.x||0) || (a.y||0) - (b.y||0));
      const MIN_GAP_X = 40;
      const MIN_GAP_Y = 30;
      const MARGIN_Y = 20;
      let moved = 0;

      const placed = [];
      for (const n of nodes) {
        let targetX = this._snap(n.x);
        let targetY = this._snap(n.y);
        let iter = 0;
        while (iter < 50) {
          let collided = false;
          for (const p of placed) {
            if (this._rectsOverlap(targetX, targetY, n.width, n.height, p.x, p.y, p.width, p.height, MIN_GAP_X, MIN_GAP_Y)) {
              targetY = this._snap(p.y + p.height + MARGIN_Y);
              collided = true;
              break;
            }
          }
          if (!collided) break;
          iter++;
        }
        moved += this._moveShape(n, targetX, targetY, modeling);
        placed.push({ x: targetX, y: targetY, width: n.width, height: n.height, id: n.id });
      }
      return moved;
    },

    _moveShape(shape, newX, newY, modeling) {
      const curX = shape.x || 0;
      const curY = shape.y || 0;
      const dx = Math.round(newX - curX);
      const dy = Math.round(newY - curY);
      if (dx === 0 && dy === 0) return 0;
      try {
        modeling.moveShape(shape, { x: dx, y: dy });
        return 1;
      } catch (e) {
        console.warn('shape 이동 실패', shape, e);
        return 0;
      }
    },

    _rectsOverlap(x1, y1, w1, h1, x2, y2, w2, h2, padX = 0, padY = 0) {
      return !(x1 + w1 + padX <= x2 || x2 + w2 + padX <= x1 || y1 + h1 + padY <= y2 || y2 + h2 + padY <= y1);
    },

    _snap(n, grid = 10) {
      if (!isFinite(n)) return 0;
      return Math.round(n / grid) * grid;
    },
    scrollCopilotToBottom() {
      this.$nextTick(() => {
        const el = this.$refs.copilotHistory;
        if (el && el.scrollHeight) {
          el.scrollTop = el.scrollHeight;
        }
      });
    },
    prepareCondensedPrompts() {
      this.condensedPrompts = this.quickPrompts.slice(0, 3).map(text => {
        const short = text.length > 18 ? `${text.slice(0, 16)}…` : text;
        return { original: text, short };
      });
    },
    fetchLlmOptions() {
      ApiService.get('/llm/configs')
        .then(({ data }) => {
          const items = data?.data || [];
          this.llmOptions = items.map(item => ({
            id: item.id,
            label: item.attributes?.name || `LLM #${item.id}`,
            isDefault: item.attributes?.isDefault,
          }));
          const defaultOption = this.llmOptions.find(opt => opt.isDefault);
          this.selectedLlm = defaultOption?.id || (this.llmOptions[0] && this.llmOptions[0].id) || null;
          this.backendHealthy = true;
        })
        .catch(() => {
          this.llmOptions = [];
          this.selectedLlm = null;
          this.backendHealthy = false;
        });
    },
    onChangeLlm() {
      // 향후 필요 시 LLM 선택 상태를 서버로 전달할 수 있도록 자리만 잡아둠
      console.log('선택된 LLM', this.selectedLlm);
    },
    handleSuggestedXml(xml, source, summary) {
      if (!xml) return;
      this.pendingXml = xml;
      this.pendingXmlSource = source;
      if (summary) {
        this.copilotMessages.push(this.createCopilotMessage('assistant', summary));
      }
      const label = source || 'AI';
      this.copilotMessages.push(this.createCopilotMessage(
        'assistant',
        `${label}가 새로운 BPMN XML을 준비했습니다. 아래 "적용" 버튼을 눌러 적용하거나 "무시"를 선택할 수 있습니다.`
      ));
      this.scrollCopilotToBottom();
    },
    applyPendingXml() {
      if (!this.pendingXml) return;
      const newXml = this.pendingXml;
      const source = this.pendingXmlSource;
      const previousXml = this.diagramXML;
      const undoSnapshot = this.diagramXML;

      this.setDiagramXml(newXml, '새로운 BPMN XML을 다이어그램에 적용했습니다.', {
        previousXml,
        onSuccess: () => {
          if (undoSnapshot) {
            this.aiUndoStack.push(undoSnapshot);
          }
          this.aiRedoStack = [];
          this.pendingXml = null;
          this.pendingXmlSource = null;
        },
        onFailure: () => {
          this.pendingXml = newXml;
          this.pendingXmlSource = source;
        },
      });
    },
    clearPendingXml() {
      this.pendingXml = null;
      this.pendingXmlSource = null;
      this.copilotMessages.push(this.createCopilotMessage('assistant', '제안된 BPMN XML을 적용하지 않았습니다.'));
      this.scrollCopilotToBottom();
    },
    hasDiagramInterchange(xml) {
      // BPMNDI(BPMNDiagram/BPMNPlane) 존재 여부 — 좌표 정보가 있는지 판단
      return typeof xml === 'string' && /bpmndi:bpmndiagram|<bpmndi:bpmnplane|:bpmnplane/i.test(xml);
    },
    isNoDiagramError(err) {
      const msg = (err && (err.message || err.warning || String(err))) || '';
      return /no diagram to display|no bpmndi|no process or collaboration/i.test(msg);
    },
    async ensureLayoutedXml(xml) {
      // 좌표(BPMNDI)가 없으면 자동 레이아웃으로 좌표를 생성해 배치 가능한 XML로 변환.
      if (!xml || this.hasDiagramInterchange(xml)) {
        return xml;
      }
      try {
        const layouted = await layoutProcess(xml);
        return layouted || xml;
      } catch (e) {
        console.error('자동 레이아웃 실패', e);
        return xml;
      }
    },
    setDiagramXml(xml, message, options = {}) {
      const self = this;
      const {
        previousXml = null,
        onSuccess = null,
        onFailure = null,
      } = options;

      const restorePrevious = () => {
        if (!previousXml) return;
        self.skipDiagramImport = true;
        self.diagramXML = previousXml;
        self.skipDiagramImport = false;
        self.bpmn.importXML(previousXml).catch((recoverErr) => {
          if (recoverErr) {
            console.error('Failed to restore previous BPMN XML', recoverErr);
          }
        });
      };

      const finishSuccess = (appliedXml) => {
        // 이미 import 했으므로 watcher 의 재-import 를 막는다.
        // watcher 는 비동기로 실행되므로 플래그 해제도 nextTick 으로 미뤄야
        // 재-import 가 실제로 스킵되고, 아래 fit-viewport 가 덮어써지지 않는다.
        self.skipDiagramImport = true;
        self.diagramXML = appliedXml;
        self.$nextTick(() => { self.skipDiagramImport = false; });
        // 새로 배치된 다이어그램이 화면에 보이도록 뷰를 맞춘다.
        try {
          self.bpmn.get('canvas').zoom('fit-viewport');
        } catch (e) {
          console.warn('fit-viewport 실패', e);
        }
        if (typeof onSuccess === 'function') {
          onSuccess();
        }
        if (message) {
          self.copilotMessages.push(self.createCopilotMessage('assistant', message));
        }
        self.scrollCopilotToBottom();
      };

      const finishFailure = (err) => {
        console.error('BPMN XML import failed', err);
        if (typeof onFailure === 'function') {
          onFailure(err);
        }
        restorePrevious();
        self.copilotMessages.push(self.createCopilotMessage('assistant', 'BPMN XML을 적용하지 못했습니다. XML 형식을 확인하세요.'));
        self.scrollCopilotToBottom();
      };

      // 좌표가 없으면 먼저 자동 레이아웃 → import. 실패 시 자동 레이아웃 재시도.
      // bpmn.importXML is promise-based in our bundled bpmn-js. Do not pass a callback.
      this.ensureLayoutedXml(xml)
        .then((preparedXml) => {
          return self.bpmn.importXML(preparedXml)
            .then(() => finishSuccess(preparedXml))
            .catch((err) => {
              // DI 부재로 인한 실패면 자동 레이아웃 후 1회 재시도
              if (self.isNoDiagramError(err) && preparedXml === xml) {
                return layoutProcess(xml)
                  .then((layouted) => self.bpmn.importXML(layouted).then(() => finishSuccess(layouted)))
                  .catch((retryErr) => finishFailure(retryErr));
              }
              return finishFailure(err);
            });
        })
        .catch((err) => finishFailure(err));
    },
    onFileChange: function(e) {
      const files = e.target.files || (e.dataTransfer && e.dataTransfer.files);
      if (!files || !files.length) return;
      const file = files[0];
      const reader = new FileReader();
      const self = this;
      reader.onload = function(evt) {
        const text = evt.target.result;
        self.importing = true;
        self.diagramXML = text;
        if (self.$refs.fileInput) self.$refs.fileInput.value = '';
      };
      reader.onerror = function(err) {
        console.error(err);
        self.$emit('error', err);
      };
      reader.readAsText(file);
    },
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
    flex: 1 1 auto;
    min-width: 0;
  }
  .bpmn-sidebar {
    width: 320px;
    height: 100%;
    display: flex;
    flex-direction: column;
    border-left: 1px solid #e5e7eb;
    background: #fafafa;
    overflow-y: auto;
    overflow-x: hidden;
    padding-right: 8px;
  }
  .bpmn-tools {
    padding: 10px 8px;
    border-bottom: 1px solid #e5e7eb;
    background: #ffffff;
    border-radius: 0 0 10px 10px;
    display: flex;
    flex-direction: column;
    gap: 8px;
  }
  .bpmn-tools__header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  .bpmn-tools__title {
    font-size: 12px;
    font-weight: 600;
    color: #0f172a;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }
  .bpmn-tools__badge {
    font-size: 10px;
    font-weight: 600;
    padding: 2px 6px;
    border-radius: 9999px;
    letter-spacing: 0.04em;
    border: 1px solid transparent;
  }
  .bpmn-tools__badge--ok {
    color: #1d4ed8;
    background: rgba(59, 130, 246, 0.12);
    border-color: rgba(59, 130, 246, 0.25);
  }
  .bpmn-tools__badge--error {
    color: #b91c1c;
    background: rgba(248, 113, 113, 0.18);
    border-color: rgba(248, 113, 113, 0.3);
  }
  .bpmn-quick-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(80px, 1fr));
    gap: 6px;
  }
  .bpmn-quick-btn {
    position: relative;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 4px;
    padding: 8px 6px;
    border: 1px solid #d0d7e6;
    border-radius: 8px;
    background: #f8fafc;
    font-size: 11px;
    color: #0f172a;
    cursor: pointer;
    transition: border-color 0.2s ease, background 0.2s ease, transform 0.1s ease;
    text-align: center;
  }
  .bpmn-quick-btn:hover:not(:disabled) {
    border-color: #2563eb;
    background: #eef4ff;
  }
  .bpmn-quick-btn:active:not(:disabled) {
    transform: translateY(1px);
  }
  .bpmn-quick-btn:disabled {
    cursor: not-allowed;
    opacity: 0.5;
  }
  .bpmn-quick-btn__icon {
    font-size: 16px;
    color: #1d4ed8;
    line-height: 1;
  }
  .bpmn-quick-btn__label {
    font-size: 11px;
    color: #1f2937;
    line-height: 1.2;
  }
  .bpmn-accordion {
    border-bottom: 1px solid #e5e7eb;
  }
  .bpmn-accordion-header {
    width: 100%;
    padding: 12px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    background: none;
    border: none;
    font-weight: 600;
    color: #111827;
    cursor: pointer;
  }
  .bpmn-accordion-header:hover {
    background: #f9fafb;
  }
  .bpmn-accordion-icon {
    font-size: 12px;
    transition: transform 0.15s ease;
  }
  .bpmn-accordion-icon--open {
    transform: rotate(180deg);
  }
  .bpmn-accordion-body {
    padding: 0 12px 12px;
  }
  .bpmn-btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    padding: 6px 10px;
    border: 1px solid #d1d5db;
    border-radius: 4px;
    background: white;
    color: #111827;
    text-align: center;
    cursor: pointer;
    user-select: none;
    transition: background 0.2s ease, color 0.2s ease;
  }
  .bpmn-btn:hover {
    background: #f3f4f6;
  }
  .bpmn-btn:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }
  .hidden-input {
    display: none;
  }
  .bpmn-properties {
    flex: 1 1 auto;
    overflow: auto;
    width: 100%;
    min-height: 260px;
  }
  #properties {
    flex: 1 1 auto;
    overflow: auto;
    width: 100%;
    min-height: 260px;
  }
  .copilot-chat {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }
  .copilot-chat__toolbar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 4px 0;
  }
  .copilot-toolbar-left {
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .copilot-llm-selector {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 4px 8px;
    border: 1px solid #d1d5db;
    border-radius: 6px;
    background: #fff;
    font-size: 12px;
    color: #0f172a;
  }
  .copilot-llm-selector select {
    border: none;
    background: transparent;
    font-size: 12px;
    color: inherit;
    outline: none;
    cursor: pointer;
  }
  .copilot-llm-selector--disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
  .copilot-llm-selector--disabled select {
    cursor: not-allowed;
  }
  .copilot-llm-icon {
    font-size: 14px;
  }
  .copilot-toolbar-reset {
    border: 1px solid #cbd5e1;
    background: #fff;
    color: #475569;
    border-radius: 6px;
    padding: 4px 10px;
    font-size: 11px;
    cursor: pointer;
    transition: background 0.2s ease;
  }
  .copilot-toolbar-reset:hover:not(:disabled) {
    background: #f1f5f9;
  }
  .copilot-toolbar-reset:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
  .copilot-chat__history {
    max-height: 260px;
    overflow-y: auto;
    border: 1px solid #d1d5db;
    border-radius: 10px;
    padding: 12px;
    background: #f8fafc;
    display: flex;
    flex-direction: column;
    gap: 10px;
  }
  .copilot-empty {
    border: 1px dashed #cbd5f5;
    border-radius: 8px;
    padding: 16px;
    background: #ffffff;
    display: flex;
    flex-direction: column;
    gap: 4px;
    font-size: 13px;
    color: #475569;
  }
  .copilot-empty strong {
    color: #1d4ed8;
  }
  .copilot-bubble {
    max-width: 90%;
    padding: 10px 12px;
    border-radius: 10px;
    background: #eef2ff;
    border: 1px solid #c7d2fe;
    display: flex;
    flex-direction: column;
    gap: 4px;
    white-space: pre-wrap;
    line-height: 1.5;
  }
  .copilot-bubble--assistant {
    align-self: flex-start;
    background: #ecfdf5;
    border-color: #bbf7d0;
  }
  .copilot-bubble--user {
    align-self: flex-end;
    background: #eef2ff;
    border-color: #c7d2fe;
  }
  .copilot-bubble__role {
    font-size: 11px;
    font-weight: 600;
    color: #64748b;
    text-transform: uppercase;
    letter-spacing: 0.04em;
  }
  .copilot-bubble__content {
    font-size: 13px;
    color: #0f172a;
    display: flex;
    flex-direction: column;
    gap: 8px;
  }
  .copilot-bubble__text {
    white-space: pre-wrap;
    line-height: 1.5;
  }
  .copilot-bubble__code {
    background: #111827;
    color: #f1f5f9;
    border-radius: 6px;
    padding: 8px;
    overflow-x: auto;
    font-family: "Fira Code", "Consolas", monospace;
    font-size: 12px;
    line-height: 1.45;
  }
  .copilot-bubble__code code {
    white-space: pre;
  }
  .copilot-bubble__table-wrapper {
    overflow-x: auto;
  }
  .copilot-bubble__table {
    width: 100%;
    border-collapse: collapse;
    font-size: 12px;
    line-height: 1.45;
  }
  .copilot-bubble__table th,
  .copilot-bubble__table td {
    border: 1px solid #cbd5f5;
    padding: 4px 6px;
    text-align: left;
    background: #ffffff;
  }
  .copilot-bubble__table th {
    background: #e0e7ff;
    font-weight: 600;
  }
  .copilot-bubble--pending {
    opacity: 0.6;
    font-style: italic;
  }
  .copilot-quick-actions {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }
  .copilot-quick-actions__label {
    font-size: 12px;
    font-weight: 600;
    color: #475569;
    text-transform: uppercase;
    letter-spacing: 0.04em;
  }
  .copilot-quick-actions__list {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    justify-content: space-between;
  }
  .copilot-quick-actions__item {
    border: 1px solid #d0d7ff;
    background: #eef2ff;
    color: #1d4ed8;
    border-radius: 9999px;
    padding: 4px 10px;
    font-size: 12px;
    cursor: pointer;
    transition: background 0.2s ease, color 0.2s ease, border-color 0.2s ease;
    flex: 1 1 0;
    min-width: 0;
    text-overflow: ellipsis;
    overflow: hidden;
    white-space: nowrap;
    }
  .copilot-quick-actions__item:hover {
    background: #dbeafe;
    border-color: #93c5fd;
  }
  .copilot-chat__composer {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }
  .copilot-pending {
    border: 1px solid #93c5fd;
    background: #eef4ff;
    border-radius: 10px;
    padding: 8px 12px;
    display: flex;
    flex-direction: column;
    gap: 6px;
  }
  .copilot-pending__text {
    font-size: 12px;
    color: #1d4ed8;
  }
  .copilot-pending__actions {
    display: flex;
    gap: 6px;
  }
  .copilot-pending__apply,
  .copilot-pending__dismiss {
    border: 1px solid #2563eb;
    border-radius: 9999px;
    background: #2563eb;
    color: #fff;
    font-size: 11px;
    padding: 4px 10px;
    cursor: pointer;
    transition: background 0.2s ease;
  }
  .copilot-pending__apply:hover {
    background: #1d4ed8;
  }
  .copilot-pending__dismiss {
    background: #fff;
    color: #1d4ed8;
    border-color: #93c5fd;
  }
  .copilot-pending__dismiss:hover {
    background: #ebf2ff;
  }
  .copilot-composer-field {
    position: relative;
  }
  .copilot-composer-textarea {
    width: 100%;
    border: 1px solid #cbd5e1;
    border-radius: 10px;
    padding: 12px 60px 12px 12px;
    font-size: 13px;
    resize: vertical;
    min-height: 72px;
    transition: border-color 0.2s ease, box-shadow 0.2s ease;
  }
  .copilot-composer-textarea:focus {
    outline: none;
    border-color: #2563eb;
    box-shadow: 0 0 0 1px rgba(37, 99, 235, 0.2);
  }
  .copilot-composer-send {
    position: absolute;
    right: 10px;
    bottom: 10px;
    padding: 6px 14px;
    border-radius: 9999px;
    border: none;
    background: #2563eb;
    color: #fff;
    font-size: 12px;
    font-weight: 600;
    cursor: pointer;
    transition: background 0.2s ease;
  }
  .copilot-composer-send:hover:not(:disabled) {
    background: #1d4ed8;
  }
  .copilot-composer-send:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }
  .copilot-reset {
    align-self: flex-end;
    background: none;
    border: 1px solid #cbd5e1;
    color: #475569;
    border-radius: 8px;
    padding: 6px 12px;
    font-weight: 500;
    cursor: pointer;
    transition: background 0.2s ease, color 0.2s ease;
  }
  .copilot-reset:hover:not(:disabled) {
    background: #f1f5f9;
    color: #1e293b;
  }
  .copilot-reset:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
  .bpmn-ai-actions {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }
  .bpmn-btn--primary {
    background-color: #2563eb;
    color: #fff;
    border-color: #1d4ed8;
  }
  .bpmn-btn--primary:hover {
    background-color: #1d4ed8;
  }
  /* Ensure the primary action button is clearly visible in sidebar even before hover */
  .bpmn-ai-actions .bpmn-btn.bpmn-btn--primary {
    background-color: #2563eb;
    color: #fff;
    border-color: #1d4ed8;
    box-shadow: inset 0 -1px 0 rgba(0, 0, 0, 0.15);
  }
  .bpmn-ai-actions .bpmn-btn.bpmn-btn--primary:hover:not(:disabled) {
    background-color: #1d4ed8;
  }
  .bpmn-ai-actions .bpmn-btn.bpmn-btn--primary:active:not(:disabled) {
    background-color: #1e40af;
  }
  .bpmn-ai-actions .bpmn-btn.bpmn-btn--primary:focus-visible {
    outline: 2px solid #1d4ed8;
    outline-offset: 2px;
  }
  .bpmn-ai-actions .bpmn-btn.bpmn-btn--primary:disabled {
    background-color: #93c5fd;  /* keep it visible when disabled */
    border-color: #60a5fa;
    color: #fff;
    opacity: 1; /* override base disabled opacity to avoid looking transparent */
    cursor: not-allowed;
  }
  .bpmn-ai-helper {
    font-size: 13px;
    color: #4b5563;
    line-height: 1.4;
  }
  .layout-options {
    display: flex;
    flex-direction: column;
    gap: 8px;
    margin: 12px 0;
  }
  .layout-option {
    display: flex;
    gap: 10px;
    border: 1px solid #d1d5db;
    border-radius: 8px;
    padding: 10px;
    cursor: pointer;
    transition: border-color 0.2s ease, background 0.2s ease;
  }
  .layout-option:hover {
    border-color: #2563eb;
  }
  .layout-option--active {
    border-color: #1d4ed8;
    background: #eff6ff;
  }
  .layout-option__input {
    margin-top: 4px;
  }
  .layout-option__body {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }
  .layout-option__label {
    font-weight: 600;
    color: #1f2937;
  }
  .layout-option__description {
    font-size: 12px;
    color: #4b5563;
    line-height: 1.5;
  }
</style>
