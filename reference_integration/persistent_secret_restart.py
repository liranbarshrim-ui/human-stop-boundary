#!/usr/bin/env python3
"""Verify persistent staging credentials remain valid across restarts."""
from __future__ import annotations
import base64, hashlib, hmac, json, os, subprocess, sys, tempfile, time, urllib.error, urllib.request
from pathlib import Path

PORT=19201
BASE=f"http://127.0.0.1:{PORT}"

def req(method,path,body=None):
    data=None if body is None else json.dumps(body).encode()
    r=urllib.request.Request(BASE+path,data=data,method=method,headers={"Content-Type":"application/json"})
    try:
        with urllib.request.urlopen(r,timeout=5) as x:return x.status,json.loads(x.read())
    except urllib.error.HTTPError as e:return e.code,json.loads(e.read())

def mac(secret,text):return hmac.new(secret,text.encode(),hashlib.sha256).hexdigest()

def wait(proc, stderr_path):
    for _ in range(150):
        try:
            if req("GET","/health")[0]==200:return
        except Exception:pass
        if proc.poll() is not None:
            detail=stderr_path.read_text(errors="replace") if stderr_path.exists() else ""
            raise RuntimeError(f"staging exited rc={proc.returncode}; stderr={detail!r}")
        time.sleep(.1)
    detail=stderr_path.read_text(errors="replace") if stderr_path.exists() else ""
    raise RuntimeError(f"staging did not start; stderr={detail!r}")

def start(root,state,deploy,admin,stderr_path):
    err=stderr_path.open("a",encoding="utf-8")
    return subprocess.Popen([sys.executable,str(root/"staging_server.py"),"--host","127.0.0.1","--port",str(PORT),"--data-dir",str(state),"--deploy-secret",deploy,"--admin-secret",admin],cwd=root,stdout=subprocess.DEVNULL,stderr=err)

def stop(p):
    if p is None:return
    try:p.terminate();p.wait(timeout=3)
    except Exception:
        try:p.kill();p.wait(timeout=2)
        except Exception:pass

def main():
    root=Path(__file__).resolve().parent
    with tempfile.TemporaryDirectory(prefix="dar-persistent-secret-") as td:
        root_tmp=Path(td);state=root_tmp/"state";state.mkdir();secret_dir=root_tmp/"secrets";secret_dir.mkdir(mode=0o700)
        deploy_secret=os.urandom(32).hex().encode();admin_secret=os.urandom(32).hex().encode()
        deploy_file=secret_dir/"deploy.secret";admin_file=secret_dir/"admin.secret";deploy_file.write_bytes(deploy_secret+b"\n");admin_file.write_bytes(admin_secret+b"\n")
        deploy=deploy_secret.decode();admin=admin_secret.decode();stderr_path=root_tmp/"staging.stderr";p=start(root,state,deploy,admin,stderr_path)
        try:
            wait(p,stderr_path);did="persistent-deployment";art=b"persistent-artifact-v1";dig=hashlib.sha256(art).hexdigest()
            auth={"purpose":"DEPLOY","deployment_id":did,"artifact_digest":dig,"fence_epoch":1,"idempotency_key":"persistent-1","issued_at":int(time.time()),"expires_at":int(time.time())+300}
            canonical="|".join(("DEPLOY",did,dig,"1","persistent-1",str(auth["issued_at"]),str(auth["expires_at"]))).encode();auth["mac"]=hmac.new(deploy_secret,canonical,hashlib.sha256).hexdigest()
            first=req("POST","/staging/deploy",{"deployment_id":did,"artifact_digest":dig,"artifact_b64":base64.b64encode(art).decode(),"fence_epoch":1,"idempotency_key":"persistent-1","expires_at":auth["expires_at"],"deploy_authorization":auth})
            if first[0]!=200:raise AssertionError(first)
            stop(p);p=start(root,state,deploy,admin,stderr_path);wait(p,stderr_path);after=req("GET",f"/staging/status/{did}")
            if after[1].get("state")!="DEPLOYED":raise AssertionError(("deployment lost across restart",after))
            rid="persistent-refused";refmac=mac(deploy_secret,f"REFUSE|{rid}|2|persistent-refusal")
            refused=req("POST","/staging/refuse",{"deployment_id":rid,"fence_epoch":2,"refusal_id":"persistent-refusal","mac":refmac})
            if refused[0]!=200:raise AssertionError(refused)
            stop(p);p=start(root,state,deploy,admin,stderr_path);wait(p,stderr_path)
            replay={"purpose":"DEPLOY","deployment_id":rid,"artifact_digest":dig,"fence_epoch":2,"idempotency_key":"persistent-replay","issued_at":int(time.time()),"expires_at":int(time.time())+300};canonical="|".join(("DEPLOY",rid,dig,"2","persistent-replay",str(replay["issued_at"]),str(replay["expires_at"]))).encode();replay["mac"]=hmac.new(deploy_secret,canonical,hashlib.sha256).hexdigest()
            blocked=req("POST","/staging/deploy",{"deployment_id":rid,"artifact_digest":dig,"artifact_b64":base64.b64encode(art).decode(),"deploy_authorization":replay});obs=req("GET",f"/staging/status/{rid}");bad_reset=req("POST","/staging/reset",{"deployment_id":rid,"reason":"attacker-test","mac":mac(deploy_secret,f"RESET|{rid}|attacker-test")})
            result={"status":"PASS" if blocked[0]==403 and obs[1].get("refused") and obs[1].get("state")=="NOT_DEPLOYED" and bad_reset[0]==401 else "FAIL","first_deploy":first,"after_restart":after,"refusal":refused,"blocked_replay":blocked,"refusal_after_restart":obs,"deploy_secret_cannot_reset":bad_reset,"secret_source":"persistent-random-bytes-reused-across-restarts"}
            print(json.dumps(result,sort_keys=True,indent=2));return 0 if result["status"]=="PASS" else 1
        finally:stop(p)

if __name__=="__main__":raise SystemExit(main())
