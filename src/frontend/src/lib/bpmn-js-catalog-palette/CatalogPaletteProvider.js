/**
 * 연합트윈 카탈로그를 왼쪽 팔레트에 분류 버튼으로 추가하는 제공자.
 *
 * 카탈로그 항목이 30개가 넘어 팔레트에 그대로 나열하면 세로로 넘쳐 화면 밖으로
 * 잘린다. 그래서 팔레트에는 분류마다 버튼 하나만 두고, 누르면 해당 분류의 항목이
 * 검색 가능한 메뉴로 열리도록 했다(기존 시뮬레이션 선택과 같은 방식).
 *
 * 항목은 백엔드에서 비동기로 받아오므로 setItems() 로 주입하면 팔레트를 다시 그린다.
 */

import { PROVIDER_ID } from './CatalogMenuProvider';

/**
 * 분류별 표시 정보.
 *
 * key      백엔드 분류명(‘디지털 트윈 · ’ 접두사는 제거하고 비교)
 * icon     팔레트 버튼 아이콘 — 분류를 눈으로 구분할 수 있게 서로 다르게 지정
 * group    팔레트 그룹 키. 값이 바뀌면 구분선이 들어간다
 */
const CATEGORIES = [
  { key: '연합트윈 연계', label: '연합트윈 연계', icon: 'bpmn-icon-data-store', group: 'catalog-link' },
  { key: '데이터', label: '데이터', icon: 'bpmn-icon-data-object', group: 'catalog-link' },
  { key: '분석', label: '분석', icon: 'bpmn-icon-business-rule-task', group: 'catalog-link' },
  { key: '알림', label: '알림', icon: 'bpmn-icon-send-task', group: 'catalog-link' },
  { key: '환경', label: '환경 시뮬레이션', icon: 'bpmn-icon-intermediate-event-catch-condition', group: 'catalog-twin' },
  { key: '관광', label: '관광 시뮬레이션', icon: 'bpmn-icon-user-task', group: 'catalog-twin' },
  { key: '교통', label: '교통 시뮬레이션', icon: 'bpmn-icon-gateway-parallel', group: 'catalog-twin' },
  { key: '방재', label: '방재 시뮬레이션', icon: 'bpmn-icon-intermediate-event-catch-escalation', group: 'catalog-twin' },
  { key: '에너지', label: '에너지 시뮬레이션', icon: 'bpmn-icon-intermediate-event-catch-signal', group: 'catalog-twin' },
  { key: '도심안전', label: '도심안전 시뮬레이션', icon: 'bpmn-icon-manual-task', group: 'catalog-twin' },
];

/** 백엔드 분류명에서 ‘디지털 트윈 · ’ 접두사를 뗀 값. */
function baseCategory(category) {
  return String(category || '').replace('디지털 트윈 · ', '').trim();
}

export default function CatalogPaletteProvider(palette, popupMenu, translate) {
  this._palette = palette;
  this._popupMenu = popupMenu;
  this._translate = translate;
  this._items = [];

  palette.registerProvider(this);
}

CatalogPaletteProvider.$inject = ['palette', 'popupMenu', 'translate'];

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
  const popupMenu = this._popupMenu;
  const translate = this._translate;
  const items = this._items;

  CATEGORIES.forEach((category) => {
    const matched = items.filter((item) => baseCategory(item.category) === category.key);
    // 해당 분류에 항목이 없으면 버튼을 만들지 않는다.
    if (!matched.length) {
      return;
    }

    function openMenu(event) {
      popupMenu.open({ items: matched, event }, PROVIDER_ID, event, {
        title: translate(`${category.label} (${matched.length})`),
        width: 400,
        search: true,
      });
    }

    entries[`catalog-${category.key}`] = {
      group: category.group,
      className: category.icon,
      title: `${category.label} — ${matched.length}개`,
      action: {
        click: openMenu,
      },
    };
  });

  return entries;
};
