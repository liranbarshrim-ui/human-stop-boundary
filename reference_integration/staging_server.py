#!/usr/bin/env python3
"""Isolated staging service with separate deploy and maintenance credentials."""
from __future__ import annotations
import argparse,base64,hashlib,hmac as hm,json,os,sys,threading,time
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse
sys.path.insert(0,str(Path(__file__).resolve().parent))
from staging_auth import verify_deploy_token
LOCK=threading.RLock(); DEPLOYMENTS={}; REFUSALS={}; USED_TOKENS=set(); DATA_FILE=None; DEPLOY_SECRET=b""; ADMIN_SECRET=b""
def _save():
    if DATA_FILE: DATA_FILE.write_text(json.dumps({"deployments":DEPLOYMENTS,"refusals":REFUSALS,"used_tokens":sorted(USED_TOKENS)},indent=2,sort_keys=True))
def _load():
    global DEPLOYMENTS,REFUSALS,USED_TOKENS
    if DATA_FILE and DATA_FILE.exists():
        raw=json.loads(DATA_FILE.read_text() or "{}"); DEPLOYMENTS=raw.get("deployments",{}); REFUSALS=raw.get("refusals",{}); USED_TOKENS=set(raw.get("used_tokens",[]))
def _valid_mac(secret,body,purpose):
    mac=str(body.get("mac","")); canonical=f"{purpose}|{body.get('deployment_id','')}|{body.get('reason','') or ''}".encode(); expected=hm.new(secret,canonical,hashlib.sha256).hexdigest(); return bool(mac) and hm.compare_digest(expected,mac)
def deploy(body):
    try: deployment_id=body["deployment_id"]; digest=body["artifact_digest"]; artifact=body["artifact_b64"]; token=body.get("deploy_authorization"); label=body.get("label",""); target=body.get("staging_target","local-staging")
    except KeyError as e: return 400,{"ok":False,"error":f"missing_{e}"}
    if not isinstance(token,dict): return 401,{"ok":False,"error":"missing_deploy_authorization"}
    err=verify_deploy_token(secret=DEPLOY_SECRET,token=token,deployment_id=deployment_id,artifact_digest=digest)
    if err: return 401,{"ok":False,"error":err}
    raw=base64.b64decode(artifact)
    if hashlib.sha256(raw).hexdigest()!=digest: return 400,{"ok":False,"error":"artifact_digest_mismatch"}
    with LOCK:
        if deployment_id in REFUSALS: return 403,{"ok":False,"error":"terminal_refusal","refusal":REFUSALS[deployment_id]}
        existing=DEPLOYMENTS.get(deployment_id)
        if existing:
            if existing.get("artifact_digest")==digest: return 200,{"ok":True,"idempotent":True,**existing}
            return 409,{"ok":False,"error":"deployment_id_conflict"}
        idem=str(token.get("idempotency_key","")); USED_TOKENS.add(idem) if idem else None
        rec={"deployment_id":deployment_id,"artifact_digest":digest,"staging_target":target,"label":label,"state":"DEPLOYED","deployed_at":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),"artifact_size":len(raw),"fence_epoch":int(token["fence_epoch"])}
        DEPLOYMENTS[deployment_id]=rec; _save(); return 200,{"ok":True,"idempotent":False,**rec}
def refuse(body):
    try: deployment_id=body["deployment_id"]; epoch=int(body["fence_epoch"]); rid=body["refusal_id"]; mac=body.get("mac","")
    except Exception: return 400,{"ok":False,"error":"invalid_refuse"}
    expected=hm.new(DEPLOY_SECRET,f"REFUSE|{deployment_id}|{epoch}|{rid}".encode(),hashlib.sha256).hexdigest()
    if not hm.compare_digest(expected,str(mac)): return 401,{"ok":False,"error":"invalid_refuse_mac"}
    with LOCK: REFUSALS[deployment_id]={"fence_epoch":epoch,"refusal_id":rid,"refused_at":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime())}; _save()
    return 200,{"ok":True,"deployment_id":deployment_id}
def reset(body):
    if not _valid_mac(ADMIN_SECRET,body,"RESET"): return 401,{"ok":False,"error":"invalid_reset_mac"}
    with LOCK: DEPLOYMENTS.clear(); REFUSALS.clear(); USED_TOKENS.clear(); _save()
    return 200,{"ok":True,"state":"empty"}
def status(deployment_id):
    with LOCK:
        if deployment_id in REFUSALS and deployment_id not in DEPLOYMENTS: return 200,{"deployment_id":deployment_id,"state":"NOT_DEPLOYED","artifact_digest":None,"refused":True,"refusal":REFUSALS[deployment_id]}
        rec=DEPLOYMENTS.get(deployment_id)
        if not rec: return 200,{"deployment_id":deployment_id,"state":"NOT_DEPLOYED","artifact_digest":None}
        out=dict(rec)
        if deployment_id in REFUSALS: out.update({"refused":True,"refusal":REFUSALS[deployment_id]})
        return 200,out
class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args): pass
    def _read(self):
        n=int(self.headers.get("Content-Length","0") or 0); return json.loads(self.rfile.read(n).decode() if n else "{}")
    def _reply(self,c,b):
        d=json.dumps(b,sort_keys=True).encode(); self.send_response(c); self.send_header("Content-Type","application/json"); self.send_header("Content-Length",str(len(d))); self.end_headers(); self.wfile.write(d)
    def do_GET(self):
        p=urlparse(self.path).path
        if p=="/health": return self._reply(200,{"ok":True,"service":"reference-staging","auth":"deploy/refuse and reset credentials separated"})
        if p.startswith("/staging/status/"): c,b=status(p[len("/staging/status/"):].strip("/")); return self._reply(c,b)
        return self._reply(404,{"error":"not_found"})
    def do_POST(self):
        p=urlparse(self.path).path; body=self._read()
        if p=="/staging/deploy": c,b=deploy(body); return self._reply(c,b)
        if p=="/staging/refuse": c,b=refuse(body); return self._reply(c,b)
        if p=="/staging/reset": c,b=reset(body); return self._reply(c,b)
        return self._reply(404,{"error":"not_found"})
def main():
    global DATA_FILE,DEPLOY_SECRET,ADMIN_SECRET
    ap=argparse.ArgumentParser(); ap.add_argument("--host",default="127.0.0.1"); ap.add_argument("--port",type=int,default=19090); ap.add_argument("--data-dir",default=""); ap.add_argument("--deploy-secret",default=os.environ.get("STAGING_DEPLOY_SECRET","")); ap.add_argument("--admin-secret",default=os.environ.get("STAGING_ADMIN_SECRET","")); a=ap.parse_args()
    if not a.deploy_secret: ap.error("--deploy-secret or STAGING_DEPLOY_SECRET is required")
    if not a.admin_secret: ap.error("--admin-secret or STAGING_ADMIN_SECRET is required")
    DEPLOY_SECRET=a.deploy_secret.encode(); ADMIN_SECRET=a.admin_secret.encode()
    if a.data_dir: DATA_FILE=Path(a.data_dir)/"staging_state.json"; DATA_FILE.parent.mkdir(parents=True,exist_ok=True); _load()
    print(f"staging listening on http://{a.host}:{a.port}",flush=True); ThreadingHTTPServer((a.host,a.port),Handler).serve_forever()
if __name__=="__main__": main()
