# 디지털트윈 메타데이터 API 호출 예시

인증 토큰은 문서에 담지 않는다. 발급받은 값을 환경변수로 지정한 뒤 사용한다.

```bash
export FEDIT_META_TOKEN='<발급받은 토큰>'
```

백엔드에서도 같은 환경변수로 주입한다(backend/README.md 참고).

```bash
curl -X 'GET' \
  'http://220.124.222.86:16997/meta/api/v1/resource/dts/KR-02-K10000-20240001?arrayDataLimitYn=Y&arrayDataLimit=50' \
  -H 'accept: */*' \
  -H "Authorization: Bearer $FEDIT_META_TOKEN"
```

	curl -X 'GET' \
  'http://220.124.222.86:16997/meta/api/v1/resource/simulations/Ez2jX-ktmJBw-QM9T3-VPL2CX?arrayDataLimitYn=Y&arrayDataLimit=50' \
  -H 'accept: */*' \
  -H 'Authorization: Bearer $FEDIT_META_TOKEN'


	curl -X 'GET' \
  'http://220.124.222.86:16997/meta/api/v1/resource/simulations?curPage=1&pageListSize=10&metaModel=ketiModelSimulation&digitalTwinId=KR-02-K10000-20240001' \
  -H 'accept: */*' \
  -H 'Authorization: Bearer $FEDIT_META_TOKEN'
	


#------추가된 부분

환경 디지털 트윈 -- 미세먼지 예측 시뮬레이션
curl -X 'GET' \   'http://220.124.222.86:16997/meta/api/v1/resource/simulations?metaModel=ketiModelSimulation&digitalTwinId=KR-02-K10000-20240001' \   -H 'accept: */*' \   -H 'Authorization: Bearer $FEDIT_META_TOKEN'

교통 디지털 트윈 -- 도로 혼잡도 예측 엔진
curl -X 'GET' \   'http://220.124.222.86:16997/meta/api/v1/resource/simulations?metaModel=ketiModelSimulation&digitalTwinId=KR-02-C20000-20240001' \   -H 'accept: */*' \   -H 'Authorization: Bearer $FEDIT_META_TOKEN'

관광 디지털 트윈 -- 주차장 혼잡도 예측 엔진
curl -X 'GET' \   'http://220.124.222.86:16997/meta/api/v1/resource/simulations?metaModel=ketiModelSimulation&digitalTwinId=KR-02-N10000-20240001' \   -H 'accept: */*' \   -H 'Authorization: Bearer $FEDIT_META_TOKEN'