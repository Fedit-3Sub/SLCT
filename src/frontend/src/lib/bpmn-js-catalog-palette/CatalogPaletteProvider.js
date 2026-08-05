/**
 * 연합트윈 카탈로그 항목을 왼쪽 팔레트에 추가하는 제공자.
 *
 * 기본 BPMN 도구 아래에 별도 그룹으로 붙으며, 기본 요소와 마찬가지로
 * 드래그 또는 클릭으로 캔버스에 배치할 수 있다. 배치된 노드에는 제공 기관과
 * 호출 URL 등 실행에 필요한 정보가 문서화 속성으로 함께 기록된다.
 *
 * 항목은 백엔드 카탈로그에서 비동기로 받아오므로, 컴포넌트가 setItems() 로
 * 넣어주면 팔레트를 다시 그린다.
 */

const TYPE_ICONS = {
  'bpmn:ServiceTask': 'bpmn-icon-service-task',
  'bpmn:SendTask': 'bpmn-icon-send-task',
  'bpmn:ReceiveTask': 'bpmn-icon-receive-task',
  'bpmn:UserTask': 'bpmn-icon-user-task',
  'bpmn:Task': 'bpmn-icon-task',
};

export default function CatalogPaletteProvider(palette, create, elementFactory, moddle, translate) {
  this._palette = palette;
  this._create = create;
  this._elementFactory = elementFactory;
  this._moddle = moddle;
  this._translate = translate;
  this._items = [];

  palette.registerProvider(this);
}

CatalogPaletteProvider.$inject = [
  'palette',
  'create',
  'elementFactory',
  'moddle',
  'translate',
];

/**
 * 팔레트에 노출할 카탈로그 항목을 설정하고 다시 그린다.
 * @param {Array} items 백엔드 통합 검색 응답 형식의 항목 배열
 */
CatalogPaletteProvider.prototype.setItems = function (items) {
  this._items = Array.isArray(items) ? items : [];
  this._palette._update();
};

CatalogPaletteProvider.prototype.getPaletteEntries = function () {
  const entries = {};
  const create = this._create;
  const elementFactory = this._elementFactory;
  const moddle = this._moddle;

  this._items.forEach((item, index) => {
    const type = item.bpmn_type || 'bpmn:ServiceTask';
    const payload = item.payload || {};

    // 문서화 속성에 남길 실행 정보. 팔레트에서 배치해도 사이드바에서
    // 추가한 것과 동일한 정보를 갖도록 맞춘다.
    const lines = [];
    if (item.description) lines.push(item.description);
    if (payload.provider) lines.push(`제공: ${payload.provider}`);
    if (payload.twinId) lines.push(`트윈 ID: ${payload.twinId}`);
    if (payload.url) lines.push(`URL: ${payload.url}`);
    if (payload.inputs && payload.inputs.length) lines.push(`입력: ${payload.inputs.join(', ')}`);
    if (payload.outputs && payload.outputs.length) lines.push(`출력: ${payload.outputs.join(', ')}`);

    function startCreate(event) {
      const businessObject = moddle.create(type, { name: item.label });
      if (lines.length) {
        businessObject.documentation = [
          moddle.create('bpmn:Documentation', { text: lines.join('\n') }),
        ];
      }
      const shape = elementFactory.createShape({ type, businessObject });
      create.start(event, shape);
    }

    const category = item.category ? `${item.category} · ` : '';
    entries[`catalog-${index}`] = {
      // 기본 도구와 섞이지 않도록 별도 그룹으로 분리한다.
      group: 'catalog',
      className: TYPE_ICONS[type] || 'bpmn-icon-service-task',
      title: `${category}${item.label}${payload.provider ? ` (${payload.provider})` : ''}`,
      action: {
        dragstart: startCreate,
        click: startCreate,
      },
    };
  });

  return entries;
};
