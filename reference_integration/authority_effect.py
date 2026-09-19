#!/usr/bin/env python3
"""Separate authority process that alone holds the deploy/refusal secret."""
from __future__ import annotations
import argparse,json,time,urllib.error,urllib.request
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from staging_auth import mint_deploy_token,mac_refusal
DEPLOY_SECRET=None; STAGING_URL=None

def post(path,body,secret,kind):
    data=json.dumps(body).encode(); req=urllib.request.Request(STAGING_URL+path,data=data,headers={"Content-Type":"application/json","X-Auth-Mac":__import__("hmac").new(secret.encode(),("DEPLOY|"+body.get("deployment_id","")+"|"+body.get("artifact_digest","")).encode(),__import__("hashlib").sha256).hexdigest()} if kind=="deploy" else {"Content-Type":"application/json"})
    if kind=="refuse": req.add_header("X-Auth-Mac",mac_refusal(secret,body["deployment_id"],body["fence_epoch"],body["refusal_id"]))
    try:
        with urllib.request.urlopen(req,timeout=5) as r:return r.status,json.loads(r.read())
    except urllib.error.HTTPError as e:return e.code,json.loads(e.read())

def deploy(body):
    required=("deployment_id","artifact_digest","fence_epoch","idempotency_key","expires_at","artifact_b64")
    if any(k not in body for k in required):return 400,{"error":"missing_identity"}
    token=mint_deploy_token(secret=DEPLOY_SECRET,deployment_id=body["deployment_id"],artifact_digest=body["artifact_digest"],fence_epoch=int(body["fence_epoch"]),idempotency_key=body["idempotency_key"],ttl_seconds=max(1,int(body["expires_at"])-int(time.time())))
    return post("/staging/deploy",dict(body,deploy_authorization=token),DEPLOY_SECRET,"deploy")

def refuse(body):return post("/staging/refuse",body,DEPLOY_SECRET,"refuse")
class Handler(BaseHTTPRequestHandler):
    def _reply(self,c,b):
        d=json.dumps(b,sort_keys=True).encode();self.send_response(c);self.send_header("Content-Type","application/json");self.send_header("Content-Length",str(len(d)));self.end_headers();self.wfile.write(d)
    def do_GET(self):
        if self.path=="/health":return self._reply(200,{"ok":True,"service":"reference-authority"})
        return self._reply(404,{"error":"not_found"})
    def do_POST(self):
        n=int(self.headers.get("Content-Length","0"));body=json.loads(self.rfile.read(n) or b"{}")
        if self.path=="/authority/commit":return self._reply(*deploy(body))
        if self.path=="/authority/refuse":return self._reply(*refuse(body))
        return self._reply(404,{"error":"not_found"})
    def log_message(self,*args):pass
def main():
    global DEPLOY_SECRET,STAGING_URL
    ap=argparse.ArgumentParser();ap.add_argument("--port",type=int,default=18876);ap.add_argument("--staging-url",required=True);ap.add_argument("--deploy-secret-file",required=True);a=ap.parse_args();STAGING_URL=a.staging_url.rstrip("/");DEPLOY_SECRET=open(a.deploy_secret_file,encoding="utf-8").read().strip()
    if not DEPLOY_SECRET:raise SystemExit("empty deploy secret")
    ThreadingHTTPServer(("127.0.0.1",a.port),Handler).serve_forever()
if __name__=="__main__":main()
