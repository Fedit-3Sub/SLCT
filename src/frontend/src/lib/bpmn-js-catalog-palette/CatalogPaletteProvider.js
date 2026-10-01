/**
 * 연합트윈 카탈로그를 왼쪽 팔레트에 버튼 하나로 추가하는 제공자.
 *
 * 분류마다 버튼을 두면 다른 BPMN 요소 아이콘(조건 이벤트, 병렬 게이트웨이 등)을
 * 분류 표시로 빌려 써야 해서, 그 요소를 만드는 버튼처럼 보이는 문제가 있었다.
 * 그래서 팔레트에는 버튼 하나만 두고, 누르면 모든 항목이 분류 머리글과 함께
 * 검색 가능한 메뉴로 열린다. 메뉴의 각 항목은 자기 요소 타입의 표준 아이콘을 쓴다.
 *
 * 항목은 백엔드에서 비동기로 받아오므로 setItems() 로 주입하면 팔레트를 다시 그린다.
 */

import { PROVIDER_ID } from './CatalogMenuProvider';

// 메뉴에서 분류가 나오는 순서. 목록에 없는 분류는 뒤에 붙는다.
const ORDER = ['연합트윈 실데이터', '연합트윈 연계', '디지털 트윈', '데이터', '분석', '알림'];

function rank(category) {
  const index = ORDER.findIndex((prefix) => String(category || '').startsWith(prefix));
  return index === -1 ? ORDER.length : index;
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
 * @param {Array} items 백엔드 통합 검색 응답 형식의 항목 배열(기본 BPMN 노드는 제외하고 넘긴다)
 */
CatalogPaletteProvider.prototype.setItems = function (items) {
  this._items = Array.isArray(items) ? items : [];
  this._palette._update();
};

CatalogPaletteProvider.prototype.getPaletteEntries = function () {
  const popupMenu = this._popupMenu;
  const items = this._items;
  if (!items.length) {
    return {};
  }

  function openMenu(event) {
    const sorted = [...items].sort((a, b) => rank(a.category) - rank(b.category));
    popupMenu.open({ items: sorted, event }, PROVIDER_ID, event, {
      title: `연합트윈 노드 추가 (${items.length})`,
      width: 420,
      search: true,
    });
  }

  return {
    'catalog-open': {
      group: 'catalog',
      className: 'bpmn-icon-service-task',
      title: `연합트윈 노드 추가 — 데이터·시뮬레이션·서비스 ${items.length}개`,
      action: { click: openMenu },
    },
  };
};
