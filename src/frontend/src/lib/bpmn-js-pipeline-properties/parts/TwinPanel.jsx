import React, { useEffect, useState } from 'react';

import { useService } from 'bpmn-js-properties-panel';
import { without } from 'min-dash';

import { createElement } from '../util';
import { getEntries, getParametersExtension, ensureParametersExtension } from '../model';
import { fetchJson, twinApiPath, twinRefOf } from '../twin';

const FRESHNESS = {
  live: ['실시간', 'twin-badge--live'],
  recent: ['최근 갱신', 'twin-badge--recent'],
  stale: ['갱신 멈춤', 'twin-badge--stale'],
  none: ['데이터 없음', 'twin-badge--stale'],
};

function age(hours) {
  if (hours == null) return '';
  if (hours < 1) return `${Math.round(hours * 60)}분 전`;
  if (hours < 48) return `${Math.round(hours)}시간 전`;
  return `${Math.round(hours / 24)}일 전`;
}

function show(value) {
  if (value === null || value === undefined || value === '') return '—';
  if (typeof value === 'number') return String(Math.round(value * 1000) / 1000);
  return String(value).slice(0, 24);
}

/**
 * 트윈 정보 패널: 메타정보와 속성 목록. 속성에 체크하면 이 노드의 출력이 된다.
 * 모든 내용은 연합트윈 프레임워크 API(/api/twins/…)에서 조회한 것이다.
 */
export function TwinInfoEntry(props) {
  const { element } = props;
  const commandStack = useService('commandStack');
  const bpmnFactory = useService('bpmnFactory');
  const ref = twinRefOf(element);

  const [state, setState] = useState({ loading: true, data: null, error: '' });
  const [showAux, setShowAux] = useState(false);
  const [, setTick] = useState(0);

  useEffect(() => {
    let alive = true;
    setState({ loading: true, data: null, error: '' });
    fetchJson(twinApiPath(ref))
      .then((data) => alive && setState({ loading: false, data, error: '' }))
      .catch((e) => alive && setState({ loading: false, data: null, error: e.message }));
    return () => { alive = false; };
  }, [ref]);

  if (state.loading) return <div className="twin-panel twin-muted">트윈 정보를 불러오는 중…</div>;
  if (state.error) return <div className="twin-panel twin-error">트윈 정보를 불러오지 못했습니다: {state.error}</div>;

  const d = state.data;
  const twin = d.twin || {};
  const obj = d.object || {};
  const [freshLabel, freshClass] = FRESHNESS[d.freshness] || ['', ''];
  const outputs = getEntries(element, 'pipeline:Output');
  const chosen = new Set(outputs.map((o) => o.get('name')));
  const props_ = d.properties.filter((p) => showAux || !p.aux || chosen.has(p.name));

  const toggle = (name, on) => {
    if (on) {
      const { extension, commands } = ensureParametersExtension(element, bpmnFactory);
      const created = createElement('pipeline:Output', { name }, extension, bpmnFactory);
      commands.push({
        cmd: 'element.updateModdleProperties',
        context: { element, moddleElement: extension, properties: { values: [ ...extension.get('values'), created ] } },
      });
      commandStack.execute('properties-panel.multi-command-executor', commands);
    } else {
      const extension = getParametersExtension(element);
      const target = outputs.find((o) => o.get('name') === name);
      if (extension && target) {
        commandStack.execute('element.updateModdleProperties', {
          element, moddleElement: extension, properties: { values: without(extension.get('values'), target) },
        });
      }
    }
    setTick((t) => t + 1);
  };

  return (
    <div className="twin-panel">
      <div className="twin-head">
        <span className="twin-badge twin-badge--src">{d.kind === 'do' ? '단일 트윈' : '연합 객체'}</span>
        <span className={`twin-badge ${freshClass}`}>{freshLabel}{d.ageHours != null ? ` · ${age(d.ageHours)}` : ''}</span>
      </div>
      <dl className="twin-meta">
        <dt>트윈</dt><dd>{twin.digital_twin_name || twin.federated_digital_twin_name}<span className="twin-id">{twin.digital_twin_id || twin.federated_digital_twin_id}</span></dd>
        <dt>객체</dt><dd>{obj.digital_object_name || obj.federated_digital_object_name}<span className="twin-id">{obj.digital_object_id || obj.federated_digital_object_id}</span></dd>
        {twin.owner ? <><dt>소유</dt><dd>{twin.owner}</dd></> : null}
        {(obj.description || twin.description) ? <><dt>설명</dt><dd>{obj.description || twin.description}</dd></> : null}
        {(obj.keywords || twin.keywords || []).length ? <><dt>키워드</dt><dd>{(obj.keywords || twin.keywords).join(', ')}</dd></> : null}
        {twin.point_of_access ? <><dt>원천</dt><dd className="twin-id">{twin.point_of_access}</dd></> : null}
        <dt>출처</dt><dd>{d.source}</dd>
      </dl>
      {d.members && d.members.length ? (
        <div className="twin-members">
          <div className="twin-subtitle">구성 단일 트윈 ({d.members.length})</div>
          <ul>{d.members.map((m) => <li key={m.objectId}>{m.twinName || '?'} › {m.objectName || m.objectId}</li>)}</ul>
        </div>
      ) : null}
      <div className="twin-subtitle">
        속성 {d.properties.length}개 · 체크한 속성이 출력이 됩니다
        <label className="twin-aux"><input type="checkbox" checked={showAux} onChange={(e) => setShowAux(e.target.checked)} /> 코드·좌표 등 보기</label>
      </div>
      <div className="twin-props">
        <table>
          <thead><tr><th></th><th>속성</th><th>타입</th><th>지금 값</th></tr></thead>
          <tbody>
            {props_.map((p) => (
              <tr key={p.name} className={chosen.has(p.name) ? 'is-chosen' : ''}>
                <td><input type="checkbox" aria-label={`${p.name} 출력으로 사용`} checked={chosen.has(p.name)} onChange={(e) => toggle(p.name, e.target.checked)} /></td>
                <td className="twin-pname" title={p.inSchema ? '데이터 모델(스키마)에 정의된 속성' : '데이터에서 확인된 속성'}>{p.name}{p.inSchema ? '' : ' *'}</td>
                <td className="twin-ptype">{p.type}</td>
                <td className="twin-pval">{show(p.value)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="twin-foot">* 표시는 데이터 모델에 없고 실제 데이터에서 확인된 속성입니다. 관측 시각 {d.observedAt || d.rowtime || '—'}</p>
    </div>
  );
}

/** 모의 응답 노드 안내 */
export function MockNoticeEntry() {
  return (
    <div className="twin-panel twin-warn">
      모의 응답 노드입니다. 실제 시스템과 연결되지 않아, 실행하면 출력 이름에 맞춘 임의 값이 돌아옵니다.
    </div>
  );
}
