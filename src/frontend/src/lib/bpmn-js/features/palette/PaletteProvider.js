import {
  assign
} from 'min-dash';
import axios from 'axios';
import ApiService from "@/common/api.service";

/**
 * @typedef {import('diagram-js/lib/features/palette/Palette').default} Palette
 * @typedef {import('diagram-js/lib/features/create/Create').default} Create
 * @typedef {import('diagram-js/lib/core/ElementFactory').default} ElementFactory
 * @typedef {import('../space-tool/BpmnSpaceTool').default} SpaceTool
 * @typedef {import('diagram-js/lib/features/lasso-tool/LassoTool').default} LassoTool
 * @typedef {import('diagram-js/lib/features/hand-tool/HandTool').default} HandTool
 * @typedef {import('diagram-js/lib/features/global-connect/GlobalConnect').default} GlobalConnect
 * @typedef {import('diagram-js/lib/i18n/translate/translate').default} Translate
 *
 * @typedef {import('diagram-js/lib/features/palette/Palette').PaletteEntries} PaletteEntries
 */

/**
 * A palette provider for BPMN 2.0 elements.
 *
 * @param {Palette} palette
 * @param {Create} create
 * @param {ElementFactory} elementFactory
 * @param {SpaceTool} spaceTool
 * @param {LassoTool} lassoTool
 * @param {HandTool} handTool
 * @param {GlobalConnect} globalConnect
 * @param {Translate} translate
 */
export default function PaletteProvider(
    palette, create, elementFactory,
    spaceTool, lassoTool, handTool,
    globalConnect, translate, popupMenu) {

  this._palette = palette;
  this._create = create;
  this._elementFactory = elementFactory;
  this._spaceTool = spaceTool;
  this._lassoTool = lassoTool;
  this._handTool = handTool;
  this._globalConnect = globalConnect;
  this._translate = translate;
	this._popupMenu = popupMenu;

  palette.registerProvider(this);
}

PaletteProvider.$inject = [
  'palette',
  'create',
  'elementFactory',
  'spaceTool',
  'lassoTool',
  'handTool',
  'globalConnect',
  'translate',
	'popupMenu',
];

/**
 * @return {PaletteEntries}
 */
PaletteProvider.prototype.getPaletteEntries = function() {

  var actions = {},
      create = this._create,
      elementFactory = this._elementFactory,
      spaceTool = this._spaceTool,
      lassoTool = this._lassoTool,
      handTool = this._handTool,
      globalConnect = this._globalConnect,
      translate = this._translate;

  function createAction(type, group, className, title, options) {

    function createListener(event) {
      var shape = elementFactory.createShape(assign({ type: type }, options));
      create.start(event, shape);
    }

    return {
      group: group,
      className: className,
      title: title,
      action: {
        dragstart: createListener,
        click: createListener
      }
    };
  }

  function createSubprocess(event) {
    var subProcess = elementFactory.createShape({
      type: 'bpmn:SubProcess',
      x: 0,
      y: 0,
      isExpanded: true
    });

    var startEvent = elementFactory.createShape({
      type: 'bpmn:StartEvent',
      x: 40,
      y: 82,
      parent: subProcess
    });

    create.start(event, [ subProcess, startEvent ], {
      hints: {
        autoSelect: [ subProcess ]
      }
    });
  }

  function createParticipant(event) {
    create.start(event, elementFactory.createParticipantShape());
  }

  assign(actions, {
    'hand-tool': {
      group: 'tools',
      className: 'bpmn-icon-hand-tool',
      title: translate('Activate hand tool'),
      action: {
        click: function(event) {
          handTool.activateHand(event);
        }
      }
    },
    'lasso-tool': {
      group: 'tools',
      className: 'bpmn-icon-lasso-tool',
      title: translate('Activate lasso tool'),
      action: {
        click: function(event) {
          lassoTool.activateSelection(event);
        }
      }
    },
    'space-tool': {
      group: 'tools',
      className: 'bpmn-icon-space-tool',
      title: translate('Activate create/remove space tool'),
      action: {
        click: function(event) {
          spaceTool.activateSelection(event);
        }
      }
    },
    'global-connect-tool': {
      group: 'tools',
      className: 'bpmn-icon-connection-multi',
      title: translate('Activate global connect tool'),
      action: {
        click: function(event) {
          globalConnect.start(event);
        }
      }
    },
    'tool-separator': {
      group: 'tools',
      separator: true
    },
    'create.start-event': createAction(
      'bpmn:StartEvent', 'event', 'bpmn-icon-start-event-none',
      translate('Create start event')
    ),
    'create.intermediate-event': createAction(
      'bpmn:IntermediateThrowEvent', 'event', 'bpmn-icon-intermediate-event-none',
      translate('Create intermediate/boundary event')
    ),
    'create.end-event': createAction(
      'bpmn:EndEvent', 'event', 'bpmn-icon-end-event-none',
      translate('Create end event')
    ),
    'create.exclusive-gateway': createAction(
      'bpmn:ExclusiveGateway', 'gateway', 'bpmn-icon-gateway-none',
      translate('Create gateway')
    ),
    'create.task': createAction(
      'bpmn:Task', 'activity', 'bpmn-icon-task',
      translate('Create task')
    ),
    'create.data-object': createAction(
      'bpmn:DataObjectReference', 'data-object', 'bpmn-icon-data-object',
      translate('Create data object reference')
    ),
    'create.data-store': createAction(
      'bpmn:DataStoreReference', 'data-store', 'bpmn-icon-data-store',
      translate('Create data store reference')
    ),
    'create.subprocess-expanded': {
      group: 'activity',
      className: 'bpmn-icon-subprocess-expanded',
      title: translate('Create expanded sub-process'),
      action: {
        dragstart: createSubprocess,
        click: createSubprocess
      }
    },
    'create.participant-expanded': {
      group: 'collaboration',
      className: 'bpmn-icon-participant',
      title: translate('Create pool/participant'),
      action: {
        dragstart: createParticipant,
        click: createParticipant
      }
    },
    'create.group': createAction(
      'bpmn:Group', 'artifact', 'bpmn-icon-group',
      translate('Create group')
    ),
    'create.simulation': {
			group: 'simulation',
			className: 'bpmn-icon-service-task',
			title: translate('Create simulation task'),
      action: {
        click: async (event) => {
					console.log('Create simulation task', event, this._popupMenu);
					ApiService.query('/digitaltwins').then(resp => {
						var { meta, data } = resp?.data || {};
						data = data.map(x => ({ ...x.attributes }));

                        // 수동으로 추가하고자 하는 2개의 항목 (API 데이터 형식에 맞춰 추가)
                      const manualItems = [
                        {
                          metaModel: "customSimulation",
                          simulationId: "manual1",
                          simulationName: translate('도로혼잡도 예측 엔진'),
                          description: "This is a manually added simulation task.",
                          keywords: ["custom", "manual"],
                          subjects: ["custom", "simulation"],
                          creationTime: new Date().toISOString(),
                          modificationTime: new Date().toISOString(),
                          authorization: "Admin",
                          simulationRequestParam: {
                            param1: "[int]",
                            param2: "[string]"
                          },
                          simulationResponseInfo: {
                            param1: "[int]",
                            param2: "[string]"
                          },
                          responseFormatType: "json",
                          interfaceType: "custom",
                          errorInfo: {
                            error_info: {
                              count: "0",
                              errorCode: "0",
                              description: "No errors"
                            }
                          },
                          preliminaryField: null,
                          simulationAccessURL: null
                        },
                        {
                          metaModel: "customSimulation",
                          simulationId: "manual2",
                          simulationName: translate('주차장 혼잡도 예측지 엔진'),
                          description: "This is another manually added simulation task.",
                          keywords: ["custom", "manual"],
                          subjects: ["custom", "simulation"],
                          creationTime: new Date().toISOString(),
                          modificationTime: new Date().toISOString(),
                          authorization: "Admin",
                          simulationRequestParam: {
                            param1: "[int]",
                            param2: "[string]"
                          },
                          simulationResponseInfo: {
                            param1: "[int]",
                            param2: "[string]"
                          },
                          responseFormatType: "json",
                          interfaceType: "custom",
                          errorInfo: {
                            error_info: {
                              count: "0",
                              errorCode: "0",
                              description: "No errors"
                            }
                          },
                          preliminaryField: null,
                          simulationAccessURL: null
                        }
                      ];

                      // API에서 가져온 데이터에 수동 항목 추가
                      data = [...data, ...manualItems];

						console.log(data, meta);
						this._popupMenu.open({ data, meta, event }, 'bpmn-simulations', event, {
							title: translate('Select simulation'),
							width: 400,
							search: true
						});
					});
				}
      }
		},
  });
	console.log("actions", actions, new Error().stack);

  return actions;
};
