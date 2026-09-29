import Ids from 'ids';

import { getBusinessObject } from 'bpmn-js/lib/util/ModelUtil';

export function getParametersExtension(element) {
  const businessObject = getBusinessObject(element);
  return getExtension(businessObject, 'pipeline:Parameters');
}

export function getParameters(element) {
  const parameters = getParametersExtension(element);
  return parameters && parameters.get('values');
}

export function getExtension(element, type) {
  if (!element.extensionElements) {
    return null;
  }

  return element.extensionElements.values.filter(function(e) {
    return e.$instanceOf(type);
  })[0];
}

export function createElement(elementType, properties, parent, factory) {
  const element = factory.create(elementType, properties);

  if (parent) {
    element.$parent = parent;
  }

  return element;
}

export function createParameters(properties, parent, bpmnFactory) {
  return createElement('pipeline:Parameters', properties, parent, bpmnFactory);
}


export function nextId(prefix) {
  const ids = new Ids([ 32,32,1 ]);

  return ids.nextPrefixed(prefix);
}


/**
 * 카탈로그 항목을 노드에 붙일 실행 확장 요소로 만든다.
 *
 *   pipeline:parameter  실행 URL·메서드
 *   pipeline:input      항목의 입력 이름(값은 비워 두면 같은 이름의 앞선 출력이 자동 연결된다)
 *   pipeline:output     항목의 출력 이름(응답에서 같은 이름의 값을 꺼낸다)
 *
 * 토큰 시뮬레이션은 parameter 의 url 을, 서버 로직 실행기는 전부를 읽는다.
 * URL 이 없는 항목이면 null.
 */
export function createCatalogExtension(moddle, item) {
  const payload = (item && item.payload) || {};
  if (!payload.url) {
    return null;
  }
  const parameterAttrs = { name: item.label, url: payload.url };
  if (payload.method) {
    parameterAttrs.method = payload.method;
  }
  const values = [ moddle.create('pipeline:Parameter', parameterAttrs) ];
  (payload.inputs || []).forEach((name) => {
    values.push(moddle.create('pipeline:Input', { name }));
  });
  (payload.outputs || []).forEach((name) => {
    values.push(moddle.create('pipeline:Output', { name }));
  });
  const parameters = moddle.create('pipeline:Parameters', { values });
  return moddle.create('bpmn:ExtensionElements', { values: [ parameters ] });
}
