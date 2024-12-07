'use strict';

const { createCoreController } = require('@strapi/strapi').factories;

module.exports = createCoreController('api::feditscraper.feditscraper', ({ strapi }) => ({
  // 기본 CRUD 메서드
  async find(ctx) {
    const { data, meta } = await super.find(ctx); // Core Controller의 기본 find 호출
    return { data, meta };
  },

  // /json 경로를 위한 메서드 추가
  async json(ctx) {
    console.log('JSON endpoint hit');
    const predefinedJson = {
      success: true,
      data: [
        {
          id: "urn:ngsi-ld:FdtAirQuality",
          type: "FdtAirQuality",
          title: "공기질",
          description: null,
          reference: null,
        },
        {
          id: "urn:ngsi-ld:FdtParking",
          type: "FdtParking",
          title: "주차장",
          description: null,
          reference: null,
        },
        {
          id: "urn:ngsi-ld:FdtPoc",
          type: "FdtPoc",
          title: "연합트윈 POC 데이터 모델",
          description: "관광지쾌적지수 연합 디지털 트윈",
          reference: null,
        },
        {
          id: "urn:ngsi-ld:FdtTraffic",
          type: "FdtTraffic",
          title: "교통",
          description: null,
          reference: null,
        },
        {
          id: "urn:ngsi-ld:FdtWeather",
          type: "FdtWeather",
          title: "날씨",
          description: null,
          reference: null,
        },
      ],
    };

    ctx.send(predefinedJson);
  },
}));
