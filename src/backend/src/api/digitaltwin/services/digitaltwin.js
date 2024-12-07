'use strict';

/**
 * digitaltwin service
 */

const axios = require('axios');
const { createCoreService } = require('@strapi/strapi').factories;

module.exports = createCoreService('api::digitaltwin.digitaltwin', ({ strapi }) => ({
	async find(...args) {
		var host = 'http://220.124.222.86:16997';
		var token = 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJQQVQxNzI0OTgxMDQ4MDAwMTQ3IiwicGF0a1JlZ3JJZCI6Im1ldGFfYWRtaW4iLCJwYXRrUmVnck5tIjoi66mU7YOA7Iuc7Iqk7YWc6rSA66as7J6QIiwiaXNzIjoia2V0aV9kdF9tZXRhZGF0YV9hcGkiLCJpYXQiOjE3MjQ5ODEwNDd9.kl-IIKakCLQhswK2qgOcK8RxtfQw_nlCwh7E3q5sqx4';
		var resp;

    const digitalTwinIds = ['KR-02-K10000-20240001', 'KR-02-C20000-20240001', 'KR-02-N10000-20240001']; // 추가하고자 하는 digitalTwinId 목록

    const requests = digitalTwinIds.map(id =>
      axios.get(`${host}/meta/api/v1/resource/simulations?metaModel=ketiModelSimulation&digitalTwinId=${id}`,
        { headers: { Authorization: `Bearer ${token}` }}
      )
    );

    // 모든 요청 병렬 실행 및 응답 수집
    const responses = await Promise.all(requests);

    // 모든 응답에서 list와 page 데이터 추출 후 합치기
    const results = responses.flatMap(resp => resp.data.list || []);
    const pagination = responses.map(resp => resp.data.page || {});

    console.log(responses);
    return { results, pagination };


    // resp = await axios.get(`${host}/meta/api/v1/resource/simulations?curPage=1&pageListSize=10&metaModel=ketiModelSimulation&digitalTwinId=KR-02-K10000-20240001`,
		// 	{ headers: { Authorization: `Bearer ${token}` }}
		// )
		// if(false) {
		// 	resp = await axios.get(`${host}/meta/api/v1/resource/dts/KR-02-K10000-20240001?arrayDataLimitYn=Y&arrayDataLimit=50`,
		// 		{ headers: { Authorization: `Bearer ${token}` }}
		// 	)
		// }
		// var { list, page } = resp?.data || {};
		// console.log(resp);
		// return { results: list, pagination: page };


	}
}));
