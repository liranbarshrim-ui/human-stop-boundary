#!/usr/bin/env python3
"""Separate authority process; caller authentication is distinct from effect credentials."""
from __future__ import annotations
import argparse,hashlib,hmac,json,time,urllib.error,urllib.request
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from staging_auth import mint_deploy_token,mac_refusal
DEPLOY_SECRET=None; CALLER_SECRET=None; STAGING_URL=None

def _caller_mac(body,purpose):
    fields=(purpose,body.get("deployment_id",""),body.get("artifact_digest",""),str(body.get("fence_epoch","")),body.get("idempotency_key","") )
    return hmac.new(CALLER_SECRET, "|".join(fields).encode(), hashlib.sha256).hexdigest()
def _authorized(body,purpose):
    supplied=str(body.get("caller_mac","")); return bool(supplied) and hmac.compare_digest(_caller_mac(body,purpose),supplied)
def post(path,body,kind):
    data=json.dumps(body).encode(); req=urllib.request.Request(STAGING_URL+path,data=data,headers={"Content-Type":"application/json"})
    if kind=="refuse": req.add_header("X-Auth-Mac",mac_refusal(DEPLOY_SECRET,body["deployment_id"],body["fence_epoch"],body["refusal_id"]))
    try:
        with urllib.request.urlopen(req,timeout=5) as r:return r.status,json.loads(r.read())
    except urllib.error.HTTPError as e:return e.code,json.loads(e.read())

def deploy(body):
    if not _authorized(body,"COMMIT"): return 401,{"ok":False,"error":"invalid_caller_auth"}
    required=("deployment_id","artifact_digest","fence_epoch","idempotency_key","expires_at","artifact_b64")
    if any(k not in body for k in required):return 400,{"ok":False,"error":"missing_identity"}
    token=mint_deploy_token(secret=DEPLOY_SECRET,deployment_id=body["deployment_id"],artifact_digest=body["artifact_digest"],fence_epoch=int(body["fence_epoch"]),idempotency_key=body["idempotency_key"],ttl_seconds=max(1,int(body["expires_at"])-int(time.time())))
    return post("/staging/deploy",dict(body,deploy_authorization=token),"deploy")
def refuse(body):
    if not _authorized(body,"REFUSE"): return 401,{"ok":False,"error":"invalid_caller_auth"}
    return post("/staging/refuse",body,"refuse")
class Handler(BaseHTTPRequestHandler):
    def _reply(self,c,b):
        d=json.dumps(b,sort_keys=True).encode();self.send_response(c);self.send_header("Content-Type","application/json");self.send_header("Content-Length",str(len(d)));self.end_headers();self.wfile.write(d)
    def do_GET(self):
        if self.path=="/health":return self._reply(200,{"ok":True,"service":"reference-authority","caller_auth":"required"})
        return self._reply(404,{"error":"not_found"})
    def do_POST(self):
        n=int(self.headers.get("Content-Length","0"));body=json.loads(self.rfile.read(n) or b"{}")
        if self.path=="/authority/commit":return self._reply(*deploy(body))
        if self.path=="/authority/refuse":return self._reply(*refuse(body))
        return self._reply(404,{"error":"not_found"})
    def log_message(self,*args):pass
def main():
    global DEPLOY_SECRET,CALLER_SECRET,STAGING_URL
    ap=argparse.ArgumentParser();ap.add_argument("--port",type=int,default=18876);ap.add_argument("--staging-url",required=True);ap.add_argument("--deploy-secret-file",required=True);ap.add_argument("--caller-secret-file",required=True);a=ap.parse_args()
    STAGING_URL=a.staging_url.rstrip("/");DEPLOY_SECRET=open(a.deploy_secret_file,encoding="utf-8").read().strip().encode();CALLER_SECRET=open(a.caller_secret_file,"rb").read().strip()
    if not DEPLOY_SECRET or not CALLER_SECRET:raise SystemExit("empty authority credential")
    ThreadingHTTPServer(("127.0.0.1",a.port),Handler).serve_forever()
if __name__=="__main__":main()
