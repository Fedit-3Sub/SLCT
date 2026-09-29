import React from 'react';

import { ListGroup, TextFieldEntry, SelectEntry } from '@bpmn-io/properties-panel';
import { useService } from 'bpmn-js-properties-panel';

import { is, getBusinessObject } from 'bpmn-js/lib/util/ModelUtil';

import { without } from 'min-dash';

import { createElement, getExtension } from './util';

const LOW_PRIORITY = 500;

const METHOD_OPTIONS = [
  { value: '', label: '자동 (입력 있으면 POST)' },
  { value: 'GET', label: 'GET' },
  { value: 'POST', label: 'POST' },
  { value: 'PUT', label: 'PUT' },
  { value: 'DELETE', label: 'DELETE' },
];


/**
 * 노드 실행 설정(pipeline 확장)을 편집하는 속성 패널 그룹.
 *
 * - 실행 설정: URL·메서드·제한 시간·재시도·딜레이
 * - 입력 매핑: 호출할 때 보낼 값. 식(source)·고정 값(value)·자동 연결(둘 다 비움)
 * - 출력:      응답에서 꺼내 다음 노드가 쓸 값
 *
 * 확장 요소는 값을 처음 입력할 때 만든다(노드를 선택만 해도 다이어그램이 바뀌지 않게).
 */
export default function PipelinePropertiesProvider(propertiesPanel, injector, translate) {
  this.getGroups = function(element) {
    return function(groups) {
      const isTask = is(element, 'bpmn:Task');
      if (isTask || is(element, 'bpmn:StartEvent') || is(element, 'bpmn:EndEvent')) {
        groups.push(createSettingsGroup(element, isTask));
      }
      if (isTask) {
        groups.push(createListGroup(element, injector, 'inputs'));
        groups.push(createListGroup(element, injector, 'outputs'));
      }
      return groups;
    };
  };

  propertiesPanel.registerProvider(LOW_PRIORITY, this);
}

PipelinePropertiesProvider.$inject = [ 'propertiesPanel', 'injector', 'translate' ];


// 모델 접근 ////////

function getParametersExtension(element) {
  return getExtension(getBusinessObject(element), 'pipeline:Parameters');
}

function getEntries(element, type) {
  const extension = getParametersExtension(element);
  return extension ? extension.get('values').filter(e => e.$instanceOf(type)) : [];
}

function getParameter(element) {
  return getEntries(element, 'pipeline:Parameter')[0];
}

/**
 * extensionElements → pipeline:Parameters 가 없으면 만드는 명령을 모은다.
 * 만든(또는 기존) Parameters 요소와 명령 목록을 돌려준다.
 */
function ensureParametersExtension(element, bpmnFactory) {
  const commands = [];
  const businessObject = getBusinessObject(element);

  let extensionElements = businessObject.get('extensionElements');
  if (!extensionElements) {
    extensionElements = createElement('bpmn:ExtensionElements', { values: [] }, businessObject, bpmnFactory);
    commands.push({
      cmd: 'element.updateModdleProperties',
      context: { element, moddleElement: businessObject, properties: { extensionElements } }
    });
  }

  let extension = getExtension(businessObject, 'pipeline:Parameters');
  if (!extension) {
    extension = createElement('pipeline:Parameters', { values: [] }, extensionElements, bpmnFactory);
    commands.push({
      cmd: 'element.updateModdleProperties',
      context: {
        element,
        moddleElement: extensionElements,
        properties: { values: [ ...extensionElements.get('values'), extension ] }
      }
    });
  }
  return { extension, commands };
}

/** 실행 설정(pipeline:Parameter) 속성을 바꾼다. 없으면 만든다. */
function updateParameter(element, injector, properties) {
  const bpmnFactory = injector.get('bpmnFactory');
  const commandStack = injector.get('commandStack');

  let parameter = getParameter(element);
  if (parameter) {
    commandStack.execute('element.updateModdleProperties', { element, moddleElement: parameter, properties });
    return;
  }

  const { extension, commands } = ensureParametersExtension(element, bpmnFactory);
  parameter = createElement('pipeline:Parameter', properties, extension, bpmnFactory);
  commands.push({
    cmd: 'element.updateModdleProperties',
    context: {
      element,
      moddleElement: extension,
      // 실행기·토큰 시뮬레이션은 첫 parameter 를 읽으므로 맨 앞에 둔다.
      properties: { values: [ parameter, ...extension.get('values') ] }
    }
  });
  commandStack.execute('properties-panel.multi-command-executor', commands);
}


// 실행 설정 그룹 ////////

const SETTINGS = [
  {
    key: 'url',
    label: '실행 URL',
    description: 'http(s) 주소 또는 /api/... 경로. 비워 두면 이 노드는 호출 없이 통과합니다.',
  },
  { key: 'method', label: '메서드', select: true },
  { key: 'timeout', label: '제한 시간(초)', description: '기본 30초', taskOnly: true },
  { key: 'retry', label: '재시도 횟수', description: '실패하면 다시 호출할 횟수. 기본 0', taskOnly: true },
  { key: 'delay', label: '호출 전 딜레이(초)', taskOnly: true },
];

function createSettingsGroup(element, isTask) {
  return {
    id: 'pipeline',
    label: '실행 설정',
    entries: SETTINGS
      .filter(s => isTask || !s.taskOnly)
      .map(setting => ({
        id: `pipeline-${setting.key}`,
        element,
        setting,
        component: setting.select ? MethodEntry : SettingEntry,
      })),
  };
}

function SettingEntry(props) {
  const { element, id, setting } = props;
  const injector = useService('injector');
  const debounce = useService('debounceInput');

  const validate = (value) => {
    if (setting.key !== 'url' && value && !/^\d+(\.\d+)?$/.test(value)) {
      return '숫자로 입력하세요.';
    }
  };

  return <TextFieldEntry
    id={ id }
    element={ element }
    label={ setting.label }
    description={ setting.description }
    getValue={ () => (getParameter(element) || { get: () => '' }).get(setting.key) || '' }
    setValue={ value => updateParameter(element, injector, { [setting.key]: value || undefined }) }
    validate={ validate }
    debounce={ debounce }
  />;
}

function MethodEntry(props) {
  const { element, id, setting } = props;
  const injector = useService('injector');

  return <SelectEntry
    id={ id }
    element={ element }
    label={ setting.label }
    getValue={ () => (getParameter(element) || { get: () => '' }).get('method') || '' }
    setValue={ value => updateParameter(element, injector, { method: value || undefined }) }
    getOptions={ () => METHOD_OPTIONS }
  />;
}


// 입력·출력 목록 그룹 ////////

const LIST_KINDS = {
  inputs: {
    type: 'pipeline:Input',
    label: '입력 매핑',
    prefix: 'input',
    fields: [
      { key: 'name', label: '이름', description: '요청에 담길 이름' },
      {
        key: 'source',
        label: '값 식',
        description: '예: Task_1.PM10, 기온 * 1.8 + 32, 예측등급 == \'나쁨\'',
      },
      { key: 'value', label: '고정 값', description: '식과 고정 값을 모두 비우면 같은 이름의 앞선 값이 자동 연결됩니다.' },
    ],
  },
  outputs: {
    type: 'pipeline:Output',
    label: '출력',
    prefix: 'output',
    fields: [
      { key: 'name', label: '이름', description: '다음 노드에서 쓸 이름. 식에서는 노드id.이름 으로도 참조합니다.' },
      { key: 'path', label: '응답 경로', description: '예: data.result.pm10. 비우면 응답에서 같은 이름을 찾습니다.' },
    ],
  },
};

function createListGroup(element, injector, kind) {
  const spec = LIST_KINDS[kind];
  const bpmnFactory = injector.get('bpmnFactory');
  const commandStack = injector.get('commandStack');

  const items = getEntries(element, spec.type).map((entry, index) => {
    const id = `${element.id}-${spec.prefix}-${index}`;
    return {
      id,
      label: entry.get('name') || '(이름 없음)',
      entries: spec.fields.map(field => ({
        id: `${id}-${field.key}`,
        element,
        entry,
        field,
        component: ListFieldEntry,
      })),
      autoFocusEntry: `${id}-name`,
      remove: (event) => {
        event.stopPropagation();
        const extension = getParametersExtension(element);
        if (!extension) {
          return;
        }
        commandStack.execute('element.updateModdleProperties', {
          element,
          moddleElement: extension,
          properties: { values: without(extension.get('values'), entry) }
        });
      },
    };
  });

  const add = (event) => {
    event.stopPropagation();
    const { extension, commands } = ensureParametersExtension(element, bpmnFactory);
    const count = getEntries(element, spec.type).length + 1;
    const created = createElement(spec.type, { name: `${spec.prefix}${count}` }, extension, bpmnFactory);
    commands.push({
      cmd: 'element.updateModdleProperties',
      context: {
        element,
        moddleElement: extension,
        properties: { values: [ ...extension.get('values'), created ] }
      }
    });
    commandStack.execute('properties-panel.multi-command-executor', commands);
  };

  return {
    id: `pipeline-${kind}`,
    label: spec.label,
    component: ListGroup,
    items,
    add,
  };
}

function ListFieldEntry(props) {
  const { element, id, entry, field } = props;
  const commandStack = useService('commandStack');
  const debounce = useService('debounceInput');

  return <TextFieldEntry
    id={ id }
    element={ entry }
    label={ field.label }
    description={ field.description }
    getValue={ () => entry.get(field.key) || '' }
    setValue={ value => commandStack.execute('element.updateModdleProperties', {
      element,
      moddleElement: entry,
      properties: { [field.key]: value || undefined }
    }) }
    debounce={ debounce }
  />;
}


// 토큰 시뮬레이션용 ////////

export function getPipelineParameters(element) {
  const businessObject = getBusinessObject(element);
  const parameter = businessObject ? getParameter(element) : null;
  const url = parameter?.get('url');
  return { url, businessObject };
}
