import { getBusinessObject } from 'bpmn-js/lib/util/ModelUtil';

import { createElement, getExtension } from './util';

/** pipeline 확장(실행 설정·입력·출력) 모델 접근 함수. */


export function getParametersExtension(element) {
  return getExtension(getBusinessObject(element), 'pipeline:Parameters');
}

export function getEntries(element, type) {
  const extension = getParametersExtension(element);
  return extension ? extension.get('values').filter(e => e.$instanceOf(type)) : [];
}

export function getParameter(element) {
  return getEntries(element, 'pipeline:Parameter')[0];
}

/**
 * extensionElements → pipeline:Parameters 가 없으면 만드는 명령을 모은다.
 * 만든(또는 기존) Parameters 요소와 명령 목록을 돌려준다.
 */
export function ensureParametersExtension(element, bpmnFactory) {
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
export function updateParameter(element, injector, properties) {
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


