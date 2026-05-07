import { assign } from 'min-dash';

/**
 * Fedit Entity-specific popup menu provider.
 *
 * @param {Create} create
 * @param {ElementFactory} elementFactory
 * @param {PopupMenu} popupMenu
 * @param {Translate} translate
 * @param {BpmnFactory} bpmnFactory
 */
export default function FeditEntityMenuProvider(create, elementFactory, popupMenu, translate, bpmnFactory) {
    this._create = create;
    this._elementFactory = elementFactory;
    this._popupMenu = popupMenu;
    this._translate = translate;
    this._bpmnFactory = bpmnFactory;

    // 제공자 등록
    this._register();
}

FeditEntityMenuProvider.$inject = ['create', 'elementFactory', 'popupMenu', 'translate', 'bpmnFactory'];

FeditEntityMenuProvider.prototype._register = function () {
    this._popupMenu.registerProvider('bpmn-fedit-entity', this);
};

FeditEntityMenuProvider.prototype.getPopupMenuEntries = function (target) {
    const { data, event } = target;

    const entries = data.map((item) => ({
        label: item.title || 'No Title',
        actionName: `create-fedit-entity-${item.id}`,
        className: 'bpmn-icon-data-store', // 데이터 스토어 아이콘 사용
        target: {
            type: 'bpmn:DataStoreReference',
            name: item.title || 'No Title',
            data: item,
            event
        }
    }));

    console.log('Fedit Entity Menu Entries:', entries);

    return this._createEntries(target, entries);
};

FeditEntityMenuProvider.prototype._createEntries = function (target, options) {
    const entries = {};

    options.forEach((option) => {
        entries[option.actionName] = this._createEntry(option, target);
    });

    return entries;
};

FeditEntityMenuProvider.prototype._createEntry = function (option, target) {
    const translate = this._translate;

    const createAction = () => {
        console.log('노드 생성 액션:', option);

        const { type, name, event, data } = option.target;

        // DataStoreReference 노드 생성
        const shape = this._elementFactory.createShape({
            type,
            businessObject: this._bpmnFactory.create(type, {
                id: 'DataStore_' + Date.now(), // 고유 ID 생성
                name,
                description: data.description || 'No Description'
            })
        });

        console.log('생성된 Shape:', shape);

        if (shape) {
            this._create.start(event, shape);
        } else {
            console.error('Shape 생성 실패');
        }
    };

    return {
        label: translate(option.label),
        className: option.className,
        action: createAction
    };
};