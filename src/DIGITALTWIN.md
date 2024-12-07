curl -X 'GET' \
  'http://220.124.222.86:16997/meta/api/v1/resource/dts/KR-02-K10000-20240001?arrayDataLimitYn=Y&arrayDataLimit=50' \
  -H 'accept: */*' \
  -H 'Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJQQVQxNzI0OTgxMDQ4MDAwMTQ3IiwicGF0a1JlZ3JJZCI6Im1ldGFfYWRtaW4iLCJwYXRrUmVnck5tIjoi66mU7YOA7Iuc7Iqk7YWc6rSA66as7J6QIiwiaXNzIjoia2V0aV9kdF9tZXRhZGF0YV9hcGkiLCJpYXQiOjE3MjQ5ODEwNDd9.kl-IIKakCLQhswK2qgOcK8RxtfQw_nlCwh7E3q5sqx4'

	curl -X 'GET' \
  'http://220.124.222.86:16997/meta/api/v1/resource/simulations/Ez2jX-ktmJBw-QM9T3-VPL2CX?arrayDataLimitYn=Y&arrayDataLimit=50' \
  -H 'accept: */*' \
  -H 'Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJQQVQxNzI0OTgxMDQ4MDAwMTQ3IiwicGF0a1JlZ3JJZCI6Im1ldGFfYWRtaW4iLCJwYXRrUmVnck5tIjoi66mU7YOA7Iuc7Iqk7YWc6rSA66as7J6QIiwiaXNzIjoia2V0aV9kdF9tZXRhZGF0YV9hcGkiLCJpYXQiOjE3MjQ5ODEwNDd9.kl-IIKakCLQhswK2qgOcK8RxtfQw_nlCwh7E3q5sqx4'


	curl -X 'GET' \
  'http://220.124.222.86:16997/meta/api/v1/resource/simulations?curPage=1&pageListSize=10&metaModel=ketiModelSimulation&digitalTwinId=KR-02-K10000-20240001' \
  -H 'accept: */*' \
  -H 'Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJQQVQxNzI0OTgxMDQ4MDAwMTQ3IiwicGF0a1JlZ3JJZCI6Im1ldGFfYWRtaW4iLCJwYXRrUmVnck5tIjoi66mU7YOA7Iuc7Iqk7YWc6rSA66as7J6QIiwiaXNzIjoia2V0aV9kdF9tZXRhZGF0YV9hcGkiLCJpYXQiOjE3MjQ5ODEwNDd9.kl-IIKakCLQhswK2qgOcK8RxtfQw_nlCwh7E3q5sqx4'
	


#------추가된 부분

환경 디지털 트윈 -- 미세먼지 예측 시뮬레이션
curl -X 'GET' \   'http://220.124.222.86:16997/meta/api/v1/resource/simulations?metaModel=ketiModelSimulation&digitalTwinId=KR-02-K10000-20240001' \   -H 'accept: */*' \   -H 'Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJQQVQxNzI0OTgxMDQ4MDAwMTQ3IiwicGF0a1JlZ3JJZCI6Im1ldGFfYWRtaW4iLCJwYXRrUmVnck5tIjoi66mU7YOA7Iuc7Iqk7YWc6rSA66as7J6QIiwiaXNzIjoia2V0aV9kdF9tZXRhZGF0YV9hcGkiLCJpYXQiOjE3MjQ5ODEwNDd9.kl-IIKakCLQhswK2qgOcK8RxtfQw_nlCwh7E3q5sqx4'

교통 디지털 트윈 -- 도로 혼잡도 예측 엔진
curl -X 'GET' \   'http://220.124.222.86:16997/meta/api/v1/resource/simulations?metaModel=ketiModelSimulation&digitalTwinId=KR-02-C20000-20240001' \   -H 'accept: */*' \   -H 'Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJQQVQxNzI0OTgxMDQ4MDAwMTQ3IiwicGF0a1JlZ3JJZCI6Im1ldGFfYWRtaW4iLCJwYXRrUmVnck5tIjoi66mU7YOA7Iuc7Iqk7YWc6rSA66as7J6QIiwiaXNzIjoia2V0aV9kdF9tZXRhZGF0YV9hcGkiLCJpYXQiOjE3MjQ5ODEwNDd9.kl-IIKakCLQhswK2qgOcK8RxtfQw_nlCwh7E3q5sqx4'

관광 디지털 트윈 -- 주차장 혼잡도 예측 엔진
curl -X 'GET' \   'http://220.124.222.86:16997/meta/api/v1/resource/simulations?metaModel=ketiModelSimulation&digitalTwinId=KR-02-N10000-20240001' \   -H 'accept: */*' \   -H 'Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJQQVQxNzI0OTgxMDQ4MDAwMTQ3IiwicGF0a1JlZ3JJZCI6Im1ldGFfYWRtaW4iLCJwYXRrUmVnck5tIjoi66mU7YOA7Iuc7Iqk7YWc6rSA66as7J6QIiwiaXNzIjoia2V0aV9kdF9tZXRhZGF0YV9hcGkiLCJpYXQiOjE3MjQ5ODEwNDd9.kl-IIKakCLQhswK2qgOcK8RxtfQw_nlCwh7E3q5sqx4'