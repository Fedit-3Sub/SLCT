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
		
		resp = await axios.get(`${host}/meta/api/v1/resource/simulations?curPage=1&pageListSize=10&metaModel=ketiModelSimulation&digitalTwinId=KR-02-K10000-20240001`,
			{ headers: { Authorization: `Bearer ${token}` }}
		)
		if(false) {
			resp = await axios.get(`${host}/meta/api/v1/resource/dts/KR-02-K10000-20240001?arrayDataLimitYn=Y&arrayDataLimit=50`,
				{ headers: { Authorization: `Bearer ${token}` }}
			)
		}
		var { list, page } = resp?.data || {};
		console.log(resp);
		return { results: list, pagination: page };
	}	
}));
