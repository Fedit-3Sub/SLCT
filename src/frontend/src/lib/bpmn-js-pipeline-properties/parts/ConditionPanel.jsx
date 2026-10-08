import React, { useState } from 'react';

import { useService } from 'bpmn-js-properties-panel';
import { is, getBusinessObject } from 'bpmn-js/lib/util/ModelUtil';

import { OPERATORS, buildCondition, parseCondition, upstreamValues } from '../twin';

/**
 * 분기 조건 편집. 앞 노드들이 내놓는 값(트윈 속성 등)을 골라 비교식을 만든다.
 * 식은 실행기가 그대로 평가한다(예: Node_2.pm10 > 80 and Node_3.windSpeed < 2).
 */
export function ConditionEntry(props) {
  const { element } = props;
  const commandStack = useService('commandStack');
  const bpmnFactory = useService('bpmnFactory');

  const bo = getBusinessObject(element);
  const source = element.source;
  const sourceBo = source && getBusinessObject(source);
  const isGatewayFlow = source && (is(source, 'bpmn:ExclusiveGateway') || is(source, 'bpmn:InclusiveGateway'));
  const body = (bo.conditionExpression && bo.conditionExpression.body) || '';
  const parsed = parseCondition(body);

  const [raw, setRaw] = useState(parsed === null);
  // 기본 흐름은 게이트웨이에 저장돼 이 흐름의 패널이 다시 그려지지 않으므로 직접 갱신한다.
  const [, setTick] = useState(0);
  const [draft, setDraft] = useState(body);
  const values = upstreamValues(element);

  const isDefault = isGatewayFlow && sourceBo.default === bo;

  const save = (text) => {
    const trimmed = (text || '').trim();
    const commands = [{
      cmd: 'element.updateModdleProperties',
      context: {
        element,
        moddleElement: bo,
        properties: { conditionExpression: trimmed ? bpmnFactory.create('bpmn:FormalExpression', { body: trimmed }) : undefined },
      },
    }];
    // 조건을 걸면 기본 흐름일 수 없다(실행기는 기본 흐름의 조건을 보지 않는다).
    if (trimmed && isDefault) {
      commands.push({ cmd: 'element.updateModdleProperties', context: { element: source, moddleElement: sourceBo, properties: { default: undefined } } });
    }
    commandStack.execute('properties-panel.multi-command-executor', commands);
  };

  const setDefault = (on) => {
    const commands = [{ cmd: 'element.updateModdleProperties', context: { element: source, moddleElement: sourceBo, properties: { default: on ? bo : undefined } } }];
    if (on && body) {
      commands.push({ cmd: 'element.updateModdleProperties', context: { element, moddleElement: bo, properties: { conditionExpression: undefined } } });
    }
    commandStack.execute('properties-panel.multi-command-executor', commands);
    setTick((t) => t + 1);
  };

  const state = parsed || { join: 'and', rows: [] };
  const rows = state.rows.length ? state.rows : [];
  const update = (nextRows, join = state.join) => save(buildCondition(join, nextRows));
  const setRow = (i, patch) => update(rows.map((r, j) => (j === i ? { ...r, ...patch } : r)));

  const known = new Set(values.map((v) => v.expr));

  return (
    <div className="cond-panel">
      {isGatewayFlow ? (
        <label className="cond-default">
          <input type="checkbox" checked={isDefault} onChange={(e) => setDefault(e.target.checked)} />
          기본 흐름 (다른 조건이 모두 거짓일 때 이쪽으로)
        </label>
      ) : null}

      {isDefault ? null : raw ? (
        <div className="cond-raw">
          <textarea
            rows={3}
            value={draft}
            placeholder="예: Node_2.pm10 > 80 and Node_3.windSpeed < 2"
            onChange={(e) => setDraft(e.target.value)}
            onBlur={() => save(draft)}
          />
          <div className="cond-actions">
            <button type="button" onClick={() => save(draft)}>적용</button>
            {parseCondition(draft) !== null ? <button type="button" onClick={() => setRaw(false)}>선택 모드로</button> : null}
          </div>
        </div>
      ) : (
        <div className="cond-rows">
          {values.length === 0 ? (
            <p className="cond-hint">앞쪽 노드에 출력이 없습니다. 트윈 노드에서 속성을 체크하면 여기서 고를 수 있습니다.</p>
          ) : null}
          {rows.map((row, i) => (
            <div className="cond-row" key={i}>
              {i > 0 ? (
                <select className="cond-join" value={state.join} onChange={(e) => update(rows, e.target.value)} aria-label="결합">
                  <option value="and">그리고</option>
                  <option value="or">또는</option>
                </select>
              ) : null}
              <select value={row.expr} onChange={(e) => setRow(i, { expr: e.target.value })} aria-label="값">
                {!known.has(row.expr) ? <option value={row.expr}>{row.expr}</option> : null}
                {values.map((v) => <option key={v.expr} value={v.expr}>{v.label}</option>)}
              </select>
              <div className="cond-line">
                <select value={row.op} onChange={(e) => setRow(i, { op: e.target.value })} aria-label="비교">
                  {OPERATORS.map((op) => <option key={op} value={op}>{op}</option>)}
                </select>
                <input
                  type="text"
                  defaultValue={row.value}
                  key={`${i}-${row.value}`}
                  aria-label="기준값"
                  placeholder="기준값"
                  onBlur={(e) => setRow(i, { value: e.target.value, quoted: false })}
                  onKeyDown={(e) => { if (e.key === 'Enter') e.currentTarget.blur(); }}
                />
                <button type="button" className="cond-del" aria-label="조건 삭제" onClick={() => update(rows.filter((_, j) => j !== i))}>×</button>
              </div>
            </div>
          ))}
          <div className="cond-actions">
            <button
              type="button"
              disabled={!values.length}
              onClick={() => update([...rows, { expr: values[0].expr, op: '>', value: '0' }])}
            >+ 조건 추가</button>
            <button type="button" onClick={() => { setDraft(body); setRaw(true); }}>식으로 편집</button>
          </div>
          {body ? <p className="cond-expr">식: <code>{body}</code></p> : null}
        </div>
      )}
    </div>
  );
}
