import os
import importlib.util

from flask import Flask, request

app = Flask(__name__)


def make_event(req, path_params=None):
    """Flask request → API Gateway v2 event 포맷 변환"""
    body = req.get_data(as_text=True)
    return {
        "version": "2.0",
        "routeKey": f"{req.method} {req.path}",
        "rawPath": req.path,
        "rawQueryString": req.query_string.decode(),
        "headers": dict(req.headers),
        "queryStringParameters": dict(req.args) or None,
        "pathParameters": path_params or None,
        "body": body or None,
        "requestContext": {
            "http": {
                "method": req.method,
                "path": req.path,
            }
        },
        "isBase64Encoded": False,
    }


def make_view(handler_fn, method, flask_path):
    def view(**kwargs):
        event = make_event(request, path_params=kwargs or None)
        result = handler_fn(event, {})
        body = result.get("body", "")
        status = result.get("statusCode", 200)
        headers = result.get("headers", {})
        resp = app.response_class(
            response=body,
            status=status,
            mimetype=headers.get("Content-Type", "application/json"),
        )
        return resp

    view.__name__ = f"{method}__{flask_path.replace('/', '_')}"
    return view


def load_handlers():
    """app/api/{domain}/{endpoint}/handler.py 자동 탐색 및 라우트 등록"""
    base = "app/api"
    if not os.path.exists(base):
        print(f"⚠️  {base} 디렉토리가 없습니다.")
        return

    for domain in sorted(os.listdir(base)):
        domain_path = os.path.join(base, domain)
        if not os.path.isdir(domain_path):
            continue

        for endpoint in sorted(os.listdir(domain_path)):
            handler_path = os.path.join(domain_path, endpoint, "handler.py")
            if not os.path.isfile(handler_path):
                continue

            spec = importlib.util.spec_from_file_location(
                f"app.api.{domain}.{endpoint}.handler", handler_path
            )
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)

            if not hasattr(mod, "ROUTE") or not hasattr(mod, "handler"):
                print(f"⚠️  Skip {handler_path}: ROUTE 또는 handler 없음")
                continue

            method, path = mod.ROUTE
            # API GW path param {id} → Flask <id>
            flask_path = path.replace("{", "<").replace("}", ">")

            app.add_url_rule(
                flask_path,
                endpoint=f"{method}__{flask_path}",
                view_func=make_view(mod.handler, method, flask_path),
                methods=[method],
            )
            print(f"  ✅ {method:6s} {path}  →  {handler_path}")


if __name__ == "__main__":
    print("\n🔍 핸들러 탐색 중...\n")
    load_handlers()
    print("\n🚀 Local server: http://localhost:5001\n")
    app.run(host="0.0.0.0", port=5001, debug=True)
