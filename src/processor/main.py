"""BPMN 프로세서.

프론트엔드 토큰 시뮬레이션이 노드를 지날 때마다 보내는 실행 요청을 받아
순서대로 처리하고, 다이어그램·실행 범위별로 실행 흔적을 남긴다.

요청 형식은 프론트엔드(components/bpmn.vue)가 보내는 형태를 그대로 따른다.

    POST /?<노드에 설정된 질의 문자열>
    {
      "did": "<다이어그램 id>",
      "uid": "<실행 범위 id>",
      "object": {
        "id":   "<노드 id>",
        "type": "<BPMN 요소 타입>",
        "url":  "<노드에 설정된 URL>"
      }
    }
"""

import json
import os
from multiprocessing import Process, Queue

from flask import Flask, jsonify, request
from flask_cors import CORS

DATA_DIR = os.environ.get("PROCESSOR_DATA_DIR", os.path.join(os.path.curdir, "data"))
TRACE_FILE = "trace.json"

queue = Queue()


def safe_segment(value):
    """식별자를 경로 한 조각으로 안전하게 바꾼다.

    did/uid 는 요청에서 그대로 들어오므로 경로 구분자나 상위 이동(..)이 섞이면
    데이터 디렉토리 밖에 파일을 쓸 수 있다. 한글 식별자도 쓰이므로 문자 자체를
    걸러내지 않고 경로 의미를 갖는 요소만 무력화한다.
    """
    name = str(value).strip().replace("\x00", "")
    for separator in ("/", "\\"):
        name = name.replace(separator, "_")
    if name in ("", ".", ".."):
        return "_"
    return name[:100]


def work_dir(did, uid):
    """다이어그램·실행 범위별 작업 디렉토리 경로."""
    path = os.path.join(DATA_DIR, safe_segment(did), safe_segment(uid))

    # 위에서 이미 막았지만, 경로가 데이터 디렉토리 안에 있는지 한 번 더 확인한다.
    root = os.path.abspath(DATA_DIR)
    resolved = os.path.abspath(path)
    if resolved != root and not resolved.startswith(root + os.sep):
        raise ValueError("작업 경로가 데이터 디렉토리를 벗어납니다.")
    return path


def load_trace(path):
    try:
        with open(os.path.join(path, TRACE_FILE), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        # 해당 실행의 첫 노드이거나 이전 기록이 깨진 경우 새로 시작한다.
        return []


def save_trace(path, trace):
    with open(os.path.join(path, TRACE_FILE), "w", encoding="utf-8") as f:
        json.dump(trace, f, ensure_ascii=False, indent=2)


def handle(params, data):
    """노드 하나의 실행 요청을 처리한다."""
    did = data["did"]
    uid = data["uid"]
    node = data.get("object") or {}

    path = work_dir(did, uid)
    os.makedirs(path, exist_ok=True)

    trace = load_trace(path)
    trace.append({
        "step": len(trace) + 1,
        "id": node.get("id"),
        "type": node.get("type"),
        "url": node.get("url", ""),
        "params": params,
    })
    save_trace(path, trace)

    print(f"[processor] {did}/{uid} {node.get('type')} {node.get('id')} "
          f"({len(trace)}단계)", flush=True)


def worker():
    """대기열에 쌓인 실행 요청을 순서대로 처리하는 워커."""
    while True:
        params, data = queue.get()
        try:
            handle(params, data)
        except Exception as exc:
            # 노드 하나가 실패해도 워커는 계속 살아 있어야 한다.
            print(f"[processor] 처리 실패: {exc}", flush=True)


app = Flask(__name__)
CORS(app)


@app.route("/", methods=["GET"])
def api_health():
    return jsonify({"result": "ok"})


@app.route("/", methods=["POST"])
def api_process():
    data = request.get_json(silent=True) or {}
    if "did" not in data or "uid" not in data:
        return jsonify({"error": "did, uid 는 필수입니다."}), 400

    # 프로세스 간 전달을 위해 요청 인자를 일반 dict 로 바꿔 넣는다.
    queue.put((dict(request.args), data))
    return jsonify({"result": "ok"})


@app.route("/trace", methods=["GET"])
def api_trace():
    """특정 실행의 노드 통과 기록을 조회한다."""
    did = request.args.get("did")
    uid = request.args.get("uid")
    if not did or not uid:
        return jsonify({"error": "did, uid 는 필수입니다."}), 400

    try:
        path = work_dir(did, uid)
    except ValueError:
        return jsonify({"error": "did, uid 값이 올바르지 않습니다."}), 400

    return jsonify({"data": load_trace(path)})


if __name__ == "__main__":
    print(f"DATA_DIR={DATA_DIR}", flush=True)

    p = Process(target=worker, daemon=True)
    p.start()

    # 디버그 모드의 자동 재시작은 모듈을 다시 읽어 워커를 중복 기동시키므로
    # 기본값을 끄고 필요할 때만 환경변수로 켠다.
    debug = os.environ.get("PROCESSOR_DEBUG", "").lower() in ("1", "true", "yes")
    app.run(debug=debug, port=9901, host="0.0.0.0")
