'use strict';

module.exports = {
  routes: [
    {
      method: 'GET',
      path: '/feditscraper/json', // /feditscraper/json 경로
      handler: 'feditscraper.json', // 컨트롤러의 json 메서드와 연결
      config: {
        policies: [], // 정책 없음
      },
    },
  ],
};
