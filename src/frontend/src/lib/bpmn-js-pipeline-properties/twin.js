/**
 * 트윈 노드·조건·입력 선택에 쓰는 공용 함수.
 */

import { is, getBusinessObject } from 'bpmn-js/lib/util/ModelUtil';

import { getEntries, getParameter } from './model';

/** 노드의 트윈 참조(do:… / fdo:…). 실행 URL 로도 알아본다. 트윈 노드가 아니면 ''. */
export function twinRefOf(element) {
  const parameter = getParameter(element);
  if (!parameter) return '';
  const explicit = parameter.get('twin');
  if (explicit) return explicit;
  const url = parameter.get('url') || '';
  let m = url.match(/^\/api\/twins\/(do|fdo)\/([^/]+)\/([^/]+)\/latest/);
  if (m) return `${m[1]}:${decodeURIComponent(m[2])}:${decodeURIComponent(m[3])}`;
  m = url.match(/^\/api\/fedit\/objects\/latest\?(.*)$/);
  if (m) {
    const q = new URLSearchParams(m[1]);
    if (q.get('fdt') && q.get('fdo')) return `fdo:${q.get('fdt')}:${q.get('fdo')}`;
  }
  return '';
}

/**
 * 연계 현황에 셀 참조. 트윈 노드의 참조에 더해, 2세부 메타데이터 저장소에서
 * 특정 디지털 트윈의 메타정보를 조회하는 노드(digitalTwinId 고정 값)는 meta:{트윈 id} 로 센다.
 */
export function linkageRefOf(element) {
  const ref = twinRefOf(element);
  if (ref) return ref;
  const parameter = getParameter(element);
  if (!parameter || !/^\/api\/fedit\/metadata\/digitalTwins(\?|$)/.test(parameter.get('url') || '')) return '';
  const input = getEntries(element, 'pipeline:Input').find((e) => e.get('name') === 'digitalTwinId');
  const value = input && !input.get('source') && (input.get('value') || '').trim();
  return value ? `meta:${value}` : '';
}

export function isMockNode(element) {
  const parameter = getParameter(element);
  return !!parameter && /^\/api\/pipelines\/run/.test(parameter.get('url') || '');
}

export function twinApiPath(ref) {
  const [kind, a, b] = ref.split(':');
  return `/api/twins/${kind}/${encodeURIComponent(a)}/${encodeURIComponent(b)}`;
}

/** API 조회(공개 GET). 편집 토큰이 있으면 같이 보낸다. */
export async function fetchJson(path) {
  const headers = {};
  try {
    const token = window.localStorage.getItem('slct-edit-token');
    if (token) headers['X-SLCT-Token'] = token;
  } catch (e) {
    // 저장소를 쓸 수 없는 환경이면 토큰 없이 조회한다.
  }
  const resp = await fetch(path, { headers });
  const body = await resp.json().catch(() => ({}));
  if (!resp.ok) throw new Error(body.error || `HTTP ${resp.status}`);
  return body.data;
}

function isIdentifier(name) {
  return /^[A-Za-z_가-힣][A-Za-z0-9_가-힣]*$/.test(name);
}

/** 식에서 노드 출력을 가리키는 표현: Node_1.pm10 / Node_1["PM2.5"] */
export function refExpr(nodeId, name) {
  return isIdentifier(nodeId) && isIdentifier(name) ? `${nodeId}.${name}` : `${nodeId}[${JSON.stringify(name)}]`;
}

function nodeLabel(element) {
  const bo = getBusinessObject(element);
  return (bo && bo.name) || element.id;
}

/**
 * element 보다 앞에 있는 노드들의 출력 값 목록. 흐름(화살표)이면 출발 노드도 포함한다.
 * [{ nodeId, nodeName, name, expr, label }]
 */
export function upstreamValues(element) {
  const start = is(element, 'bpmn:SequenceFlow') ? [element.source] : (element.incoming || []).map((c) => c.source);
  const seen = new Set();
  const queue = [...start].filter(Boolean);
  const out = [];
  while (queue.length) {
    const node = queue.shift();
    if (!node || seen.has(node.id)) continue;
    seen.add(node.id);
    getEntries(node, 'pipeline:Output').forEach((o) => {
      const name = o.get('name');
      if (!name) return;
      out.push({ nodeId: node.id, nodeName: nodeLabel(node), name, expr: refExpr(node.id, name), label: `${nodeLabel(node)} › ${name}` });
    });
    (node.incoming || []).forEach((c) => c.source && queue.push(c.source));
  }
  return out;
}

export const OPERATORS = ['>', '>=', '<', '<=', '==', '!='];

const CLAUSE = /^\s*([A-Za-z_가-힣][\w가-힣]*(?:\.[\w가-힣]+|\[(?:"[^"]*"|'[^']*')\])?)\s*(>=|<=|==|!=|>|<)\s*(.+?)\s*$/;

/** 'A.x > 3 and B.y == "나쁨"' → { join: 'and', rows: [{expr, op, value}] }. 해석할 수 없으면 null. */
export function parseCondition(body) {
  const text = (body || '').trim().replace(/^\$\{([\s\S]*)\}$/, '$1').trim();
  if (!text) return { join: 'and', rows: [] };
  const hasAnd = /\s+and\s+/.test(text);
  const hasOr = /\s+or\s+/.test(text);
  if (hasAnd && hasOr) return null;
  const join = hasOr ? 'or' : 'and';
  const rows = [];
  for (const part of text.split(new RegExp(`\\s+${join}\\s+`))) {
    const m = part.match(CLAUSE);
    if (!m) return null;
    let value = m[3];
    const quoted = value.match(/^(["'])(.*)\1$/);
    rows.push({ expr: m[1], op: m[2], value: quoted ? quoted[2] : value, quoted: !!quoted });
  }
  return { join, rows };
}

/** 조건 행 → 식. 숫자는 그대로, 그 밖은 따옴표로 감싼다. */
export function buildCondition(join, rows) {
  return rows
    .filter((r) => r.expr && r.op && String(r.value).trim() !== '')
    .map((r) => {
      const v = String(r.value).trim();
      const literal = !r.quoted && /^-?\d+(\.\d+)?$/.test(v) ? v : JSON.stringify(v);
      return `${r.expr} ${r.op} ${literal}`;
    })
    .join(` ${join} `);
}
