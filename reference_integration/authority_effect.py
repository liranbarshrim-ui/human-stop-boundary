#!/usr/bin/env python3
"""Reference authority process: DAR RefusalAuthority + fenced staging effect."""
from __future__ import annotations
import argparse,hashlib,hmac,json,pathlib,time
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from dar_v36_14.dar import Store
from dar_v36_14.dar.canonical import canonical_digest,canonical_outcome_key
from dar_v36_14.dar.effect_transaction import AdapterContractError,EffectTxn,protected_commit
from dar_v36_14.dar.refusal import RefusalAuthority
from staging_adapter import StagingDeploymentAdapter

AUTH=None
ADAPTER=None
CALLER_SECRET=None
STAGING_URL=None

def _caller_mac(body,purpose):
    fields=(purpose,body.get("deployment_id",""),body.get("artifact_digest",""),str(body.get("fence_epoch","")),body.get("idempotency_key",""),body.get("effect_id",""),body.get("capability_txid",""),body.get("refusal_id",""),str(body.get("issued_at","")))
    return hmac.new(CALLER_SECRET,"|".join(fields).encode("utf-8"),hashlib.sha256).hexdigest()

def _authorized(body,purpose):
    supplied=str(body.get("caller_mac","")); return bool(supplied) and hmac.compare_digest(_caller_mac(body,purpose),supplied)

def deploy(body):
    if not _authorized(body,"COMMIT"): return 401,{"ok":False,"error":"invalid_caller_auth"}
    required=("deployment_id","artifact_digest","fence_epoch","idempotency_key","expires_at","artifact_b64")
    if any(k not in body for k in required): return 400,{"ok":False,"error":"missing_identity"}
    outcome=canonical_outcome_key(body["deployment_id"])
    params={"deployment_id":outcome,"artifact_digest":body["artifact_digest"],"artifact_b64":body["artifact_b64"],"label":body.get("label",""),"staging_target":body.get("staging_target","local-staging")}
    txn=EffectTxn(effect_key=outcome,idempotency_key=body["idempotency_key"],effect_class="WRITE",params_digest=canonical_digest(params),outcome_key=outcome,fence_epoch=int(body["fence_epoch"]))
    try:
        status=protected_commit(ADAPTER,txn,params)
        return 200,{"ok":True,"status":str(status),"deployment_id":outcome}
    except AdapterContractError as exc:
        msg=str(exc)
        if "terminally refused" in msg or "fenced protected commit rejected" in msg:
            return 403,{"ok":False,"error":msg}
        return 409,{"ok":False,"error":msg}

def refuse(body):
    if not _authorized(body,"REFUSE"): return 401,{"ok":False,"error":"invalid_caller_auth"}
    required=("deployment_id","fence_epoch","refusal_id","effect_id","capability_txid")
    if any(k not in body for k in required): return 400,{"ok":False,"error":"missing_refusal_identity"}
    issued_at=int(body.get("issued_at",int(time.time())))
    try:
        refusal=AUTH.issue_protected("caller",body["effect_id"],body["capability_txid"],canonical_outcome_key(body["deployment_id"]),target_epoch=int(body["fence_epoch"]),refusal_id=body["refusal_id"],issued_at=issued_at)
        AUTH.commit_protected(refusal,ADAPTER)
        return 200,{"ok":True,"refusal_id":refusal.refusal_id,"target_epoch":refusal.target_epoch,"outcome_key":refusal.outcome_key}
    except (PermissionError,ValueError,RuntimeError,TypeError) as exc:
        return 409,{"ok":False,"error":str(exc)}

class Handler(BaseHTTPRequestHandler):
    def _reply(self,c,b):
        d=json.dumps(b,sort_keys=True).encode(); self.send_response(c); self.send_header("Content-Type","application/json"); self.send_header("Content-Length",str(len(d))); self.end_headers(); self.wfile.write(d)
    def do_GET(self):
        if self.path=="/health": return self._reply(200,{"ok":True,"service":"reference-authority","dar":"RefusalAuthority+protected_commit","caller_auth":"required"})
        return self._reply(404,{"error":"not_found"})
    def do_POST(self):
        try:
            n=int(self.headers.get("Content-Length","0")); body=json.loads(self.rfile.read(n) or b"{}")
        except Exception: return self._reply(400,{"ok":False,"error":"invalid_json"})
        if self.path=="/authority/commit": return self._reply(*deploy(body))
        if self.path=="/authority/refuse": return self._reply(*refuse(body))
        return self._reply(404,{"error":"not_found"})
    def log_message(self,*args): pass

def main():
    global AUTH,ADAPTER,CALLER_SECRET,STAGING_URL
    ap=argparse.ArgumentParser(); ap.add_argument("--port",type=int,default=18876); ap.add_argument("--staging-url",required=True); ap.add_argument("--deploy-secret-file",required=True); ap.add_argument("--caller-secret-file",required=True); ap.add_argument("--store-secret-file",required=True); ap.add_argument("--state-dir",required=True); a=ap.parse_args()
    STAGING_URL=a.staging_url.rstrip("/")
    deploy_secret=pathlib.Path(a.deploy_secret_file).read_text(encoding="utf-8").strip().encode()
    CALLER_SECRET=pathlib.Path(a.caller_secret_file).read_bytes().strip()
    store_secret=pathlib.Path(a.store_secret_file).read_bytes().strip()
    if not deploy_secret or not CALLER_SECRET or not store_secret: raise SystemExit("empty authority credential")
    state_dir=pathlib.Path(a.state_dir); state_dir.mkdir(parents=True,exist_ok=True); state_path=state_dir/"authority_state.json"
    store=Store(state_path,store_secret)
    ADAPTER=StagingDeploymentAdapter(STAGING_URL,deploy_secret)
    AUTH=RefusalAuthority(store,{"caller":CALLER_SECRET})
    print(f"authority listening on http://127.0.0.1:{a.port}",flush=True)
    ThreadingHTTPServer(("127.0.0.1",a.port),Handler).serve_forever()
if __name__=="__main__": main()
