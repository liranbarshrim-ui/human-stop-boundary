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

def wait():
    for _ in range(150):
        try:
            if req("GET","/health")[0]==200:return
        except Exception:pass
        time.sleep(.1)
    raise RuntimeError("staging did not start")

def start(root,state,deploy,admin):
    return subprocess.Popen([sys.executable,str(root/"staging_server.py"),"--host","127.0.0.1","--port",str(PORT),"--data-dir",str(state),"--deploy-secret",deploy,"--admin-secret",admin],cwd=root)

def main():
    root=Path(__file__).resolve().parent
    with tempfile.TemporaryDirectory(prefix="dar-persistent-secret-") as td:
        state=Path(td)/"state";state.mkdir()
        secret_dir=Path(td)/"secrets";secret_dir.mkdir(mode=0o700)
        deploy_secret=os.urandom(32).hex().encode();admin_secret=os.urandom(32).hex().encode()
        deploy_file=secret_dir/"deploy.secret";admin_file=secret_dir/"admin.secret"
        deploy_file.write_bytes(deploy_secret+b"\n");admin_file.write_bytes(admin_secret+b"\n")
        deploy=deploy_secret.decode();admin=admin_secret.decode()
        # The same credential bytes and files are reused after every restart.
        p=start(root,state,deploy,admin)
        try:
            wait();did="persistent-deployment";art=b"persistent-artifact-v1";dig=hashlib.sha256(art).hexdigest()
            auth=mac(deploy_secret,"DEPLOY|"+did+"|"+dig+"|1|persistent-1")
            first=req("POST","/staging/deploy",{"deployment_id":did,"artifact_digest":dig,"artifact_b64":base64.b64encode(art).decode(),"fence_epoch":1,"idempotency_key":"persistent-1","expires_at":int(time.time())+300,"deploy_authorization":auth})
            if first[0]!=200:raise AssertionError(first)
            p.terminate();p.wait(timeout=3);p=start(root,state,deploy,admin);wait()
            after=req("GET",f"/staging/status/{did}")
            if after[1].get("state")!="DEPLOYED":raise AssertionError(("deployment lost across restart",after))
            rid="persistent-refused";refmac=mac(admin_secret,f"REFUSE|{rid}|2|persistent-refusal")
            refused=req("POST","/staging/refuse",{"deployment_id":rid,"epoch":2,"refusal_id":"persistent-refusal","mac":refmac})
            if refused[0]!=200:raise AssertionError(refused)
            p.terminate();p.wait(timeout=3);p=start(root,state,deploy,admin);wait()
            replay_auth=mac(deploy_secret,"DEPLOY|"+rid+"|"+dig+"|2|persistent-replay")
            blocked=req("POST","/staging/deploy",{"deployment_id":rid,"artifact_digest":dig,"artifact_b64":base64.b64encode(art).decode(),"deploy_authorization":replay_auth})
            obs=req("GET",f"/staging/status/{rid}")
            bad_reset=req("POST","/staging/reset",{"deployment_id":rid,"reason":"attacker-test","mac":mac(deploy_secret,f"RESET|{rid}|attacker-test")})
            result={"status":"PASS" if blocked[0]==409 and obs[1].get("refused") and obs[1].get("state")=="NOT_DEPLOYED" and bad_reset[0]==401 else "FAIL","first_deploy":first,"after_restart":after,"refusal":refused,"blocked_replay":blocked,"refusal_after_restart":obs,"deploy_secret_cannot_reset":bad_reset,"secret_source":"persistent-random-bytes-reused-across-restarts"}
            print(json.dumps(result,sort_keys=True,indent=2));return 0 if result["status"]=="PASS" else 1
        finally:
            try:p.terminate();p.wait(timeout=2)
            except Exception:
                try:p.kill()
                except Exception:pass

if __name__=="__main__":raise SystemExit(main())
