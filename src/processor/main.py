import os
import pandas as pd
from tsai.all import *
from flask import Flask, request, jsonify
from flask_cors import CORS
from multiprocessing import Process, Queue
from datasets import list_datasets, load_dataset
import yaml
from glob import glob
import re
import tiktoken

DATA_DIR = os.path.join(os.path.curdir, "data")
print(f"DATA_DIR={DATA_DIR}")

q = Queue()

tokenizer = tiktoken.get_encoding("cl100k_base")

def pipeline():
	while True:
		try:
			(params, data) = q.get()
			did = data['did']
			uid = data['uid']
			eid = data['object']['id']
			type = data['object']['type']
			dataset = ''
			if 'dataset' in params:
				dataset = params['dataset']
			filename = eid
			if 'filename' in params:
				filename = params['filename']

			print((uid, did, eid, type, dataset))
			dir = os.path.join(DATA_DIR, did, uid)
			os.makedirs(dir, exist_ok=True)

			pipeline = []
			try:
				with open(os.path.join(dir, 'pipeline.yml')) as f:
					pipeline = yaml.load(f, Loader=yaml.FullLoader)
			except:
				pass
    
			#print('list_datasets', list_datasets())
			print(pipeline)

			if type == 'bpmn:StartEvent':
				ds = load_dataset(dataset, cache_dir=dir)
				print(ds)
				for key in ds:
					df = pd.DataFrame(ds[key])
					df.to_csv(os.path.join(dir, f"{filename}_{key}.csv"))
					print(filename, df)

			elif type == 'bpmn:EndEvent':
				for file in glob(os.path.join(dir, f"{pipeline[-1]['filename']}_*")):
					m = re.search('_([^_]+)\.', file)
					print(file, m[1])
					df = pd.read_csv(file)
					df['token'] = df['text'].apply(lambda x: tokenizer.encode(x))
					df.to_csv(os.path.join(dir, f"{filename}_{m[1]}.csv"))

			else:
				for file in glob(os.path.join(dir, f"{pipeline[-1]['filename']}_*")):
					m = re.search('_([^_]+)\.', file)
					print(file, m[1])
					df = pd.read_csv(file)
					df.dropna(inplace=True)
					df.to_csv(os.path.join(dir, f"{filename}_{m[1]}.csv"))

			pipeline.append({
				'eid': eid,
				'type': type,
				'filename': filename,
			})
			with open(os.path.join(dir, 'pipeline.yml'), 'w') as f:
				yaml.dump(pipeline, f)
		except Exception as e:
			print(e)

app = Flask(__name__)
CORS(app)

@app.route('/', methods=['GET'])
def api_health():
	return jsonify({'result': "ok"})

@app.route('/', methods=['POST'])
def api_process():
	params = request.get_json()
	q.put((request.args, params))
	return jsonify({'result': "ok"})

if __name__ == '__main__':
	p = Process(target=pipeline)
	p.start()
	app.run(debug=True, port=9901, host="0.0.0.0")
	p.join()
	
