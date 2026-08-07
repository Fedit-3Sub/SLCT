/**
 * 연합트윈 카탈로그 팝업 메뉴 제공자.
 *
 * 팔레트의 분류 버튼을 누르면 해당 분류의 항목이 검색 가능한 메뉴로 열리고,
 * 항목을 고르면 캔버스에 배치된다. 항목이 30개가 넘어 팔레트에 그대로 나열하면
 * 화면 밖으로 잘리기 때문에, 기존 시뮬레이션·엔티티 선택과 같은 메뉴 방식을 쓴다.
 *
 * 배치된 노드에는 제공 기관과 호출 URL 등 실행 정보가 문서화 속성으로 기록된다.
 */

export const PROVIDER_ID = 'bpmn-catalog';

export default function CatalogMenuProvider(
    popupMenu, create, elementFactory, bpmnFactory, moddle, translate) {
  this._popupMenu = popupMenu;
  this._create = create;
  this._elementFactory = elementFactory;
  this._bpmnFactory = bpmnFactory;
  this._moddle = moddle;
  this._translate = translate;

  popupMenu.registerProvider(PROVIDER_ID, this);
}

CatalogMenuProvider.$inject = [
  'popupMenu',
  'create',
  'elementFactory',
  'bpmnFactory',
  'moddle',
  'translate',
];

/**
 * 시뮬레이션이 호출할 수 있도록 실행 URL 을 확장 속성으로 붙인다.
 *
 * 토큰 시뮬레이션은 extensionElements → pipeline:Parameters → pipeline:Parameter 의
 * url 값을 읽어 요청을 보낸다. 설명(documentation)에만 URL 을 적어두면 사람이 읽을
 * 수는 있어도 실행되지 않으므로, 배치 시점에 확장 속성까지 함께 만들어 준다.
 */
function attachPipelineUrl(moddle, businessObject, item) {
  const url = (item.payload || {}).url;
  if (!url) {
    return;
  }
  const parameter = moddle.create('pipeline:Parameter', { name: item.label, url });
  const parameters = moddle.create('pipeline:Parameters', { values: [parameter] });
  businessObject.extensionElements = moddle.create('bpmn:ExtensionElements', {
    values: [parameters],
  });
}

/** 노드에 남길 실행 정보를 문단으로 만든다. */
function buildDocumentation(item) {
  const payload = item.payload || {};
  const lines = [];
  if (item.description) lines.push(item.description);
  if (payload.provider) lines.push(`제공: ${payload.provider}`);
  if (payload.twinId) lines.push(`트윈 ID: ${payload.twinId}`);
  if (payload.url) lines.push(`URL: ${payload.url}`);
  if (payload.inputs && payload.inputs.length) lines.push(`입력: ${payload.inputs.join(', ')}`);
  if (payload.outputs && payload.outputs.length) lines.push(`출력: ${payload.outputs.join(', ')}`);
  return lines.join('\n');
}

CatalogMenuProvider.prototype.getPopupMenuEntries = function (target) {
  const items = (target && target.items) || [];
  const event = target && target.event;
  const self = this;
  const entries = {};

  items.forEach((item, index) => {
    const type = item.bpmn_type || 'bpmn:ServiceTask';
    const payload = item.payload || {};

    entries[`catalog-item-${index}`] = {
      label: item.label,
      // 메뉴에서도 항목 성격이 드러나도록 요소 타입에 맞는 아이콘을 쓴다.
      className: {
        'bpmn:SendTask': 'bpmn-icon-send-task',
        'bpmn:ReceiveTask': 'bpmn-icon-receive-task',
        'bpmn:UserTask': 'bpmn-icon-user-task',
        'bpmn:Task': 'bpmn-icon-task',
      }[type] || 'bpmn-icon-service-task',
      description: payload.provider || '',
      action: function () {
        const businessObject = self._bpmnFactory.create(type);
        businessObject.name = item.label;

        const documentation = buildDocumentation(item);
        if (documentation) {
          businessObject.documentation = [
            self._moddle.create('bpmn:Documentation', { text: documentation }),
          ];
        }
        attachPipelineUrl(self._moddle, businessObject, item);

        const shape = self._elementFactory.createShape({
          type,
          businessObject,
          di: {},
        });
        self._create.start(event, shape);
        return true;
      },
    };
  });

  return entries;
};

CatalogMenuProvider.PROVIDER_ID = PROVIDER_ID;
