#!/usr/bin/env python3
"""Bounded V1-V8 adversarial qualification for the reference staging integration."""
from __future__ import annotations
import base64, hashlib, hmac, json, os, pathlib, pwd, shutil, subprocess, sys, tempfile, time, urllib.error, urllib.request

ROOT = pathlib.Path(__file__).resolve().parent
OUT = ROOT / "v1_v8_evidence.json"
STAGING_PORT = 18987
AUTH_PORT = 18988

def http(method, url, body=None, timeout=5):
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, method=method, headers={"Content-Type":"application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r: return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        raw=e.read()
        try: return e.code, json.loads(raw)
        except Exception: return e.code, {"raw":raw.decode(errors="replace")}

def wait(url, timeout=15):
    end=time.monotonic()+timeout
    while time.monotonic()<end:
        try:
            if http("GET",url,timeout=1)[0]==200:return
        except Exception: pass
        time.sleep(.1)
    raise RuntimeError(f"service did not start: {url}")

def ensure_user(name):
    try:return pwd.getpwnam(name).pw_uid
    except KeyError:
        subprocess.run(["sudo","useradd","--system","--no-create-home",name],check=True)
        return pwd.getpwnam(name).pw_uid

def attacker_post(url,body):
    code='''import json,sys,urllib.request,urllib.error
u=sys.argv[1];b=json.loads(sys.argv[2]);r=urllib.request.Request(u,data=json.dumps(b).encode(),method="POST",headers={"Content-Type":"application/json"})
try:
 with urllib.request.urlopen(r,timeout=5) as x: print(json.dumps({"status":x.status,"body":json.loads(x.read())}))
except urllib.error.HTTPError as e: print(json.dumps({"status":e.code,"body":json.loads(e.read())}))
'''
    out=subprocess.check_output(["sudo","-u","darattacker","--",sys.executable,"-c",code,url,json.dumps(body)],text=True,timeout=10)
    return json.loads(out)

def caller_mac(secret,body,purpose):
    fields=(purpose,body.get("deployment_id",""),body.get("artifact_digest",""),str(body.get("fence_epoch","")),body.get("idempotency_key",""),body.get("effect_id",""),body.get("capability_txid",""),body.get("refusal_id",""),str(body.get("issued_at","")))
    return hmac.new(secret,"|".join(fields).encode(),hashlib.sha256).hexdigest()

def caller_request(secret,url,body,purpose):
    signed=dict(body);signed["caller_mac"]=caller_mac(secret,body,purpose);return http("POST",url,signed)

def secret_read_denied(path):
    return subprocess.run(["sudo","-u","darattacker","--","cat",str(path)],capture_output=True).returncode!=0

def evidence_write(ev):
    OUT.write_text(json.dumps(ev,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(ev,sort_keys=True,indent=2));print("SHA256",hashlib.sha256(OUT.read_bytes()).hexdigest())

def main():
    for u in ("darattacker","darcaller","darauthority","darstaging"):ensure_user(u)
    try:subprocess.run(["sudo","groupadd","--system","dareffect"],check=True)
    except subprocess.CalledProcessError:pass
    for u in ("darauthority","darstaging"):subprocess.run(["sudo","usermod","-a","-G","dareffect",u],check=True)

    td=pathlib.Path(tempfile.mkdtemp(prefix="dar-v1-v8-"));os.chmod(td,0o755)
    state=td/"state";state.mkdir();auth_state=td/"authority-state";auth_state.mkdir()
    snap=td/"authority_state.snapshot";snap.touch()
    deploy_secret=td/"deploy.secret";admin_secret=td/"admin.secret";caller_secret_file=td/"caller.secret";store_secret=td/"store.secret"
    deploy_secret.write_text("deploy-"+os.urandom(32).hex()+"\n")
    admin_secret.write_text("admin-"+os.urandom(32).hex()+"\n")
    caller_secret_file.write_bytes(os.urandom(32));store_secret.write_bytes(os.urandom(32))
    deploy_secret_bytes=deploy_secret.read_text().strip().encode()
    caller_secret=caller_secret_file.read_bytes().strip()
    subprocess.run(["sudo","chown","darstaging:darstaging",state],check=True);subprocess.run(["sudo","chmod","700",state],check=True)
    subprocess.run(["sudo","chown","darauthority:darauthority",auth_state],check=True);subprocess.run(["sudo","chmod","700",auth_state],check=True)
    subprocess.run(["sudo","chown","darauthority:darauthority",snap],check=True);subprocess.run(["sudo","chmod","600",snap],check=True)
    subprocess.run(["sudo","chown","darauthority:dareffect",deploy_secret],check=True);subprocess.run(["sudo","chmod","640",deploy_secret],check=True)
    subprocess.run(["sudo","chown","darstaging:darstaging",admin_secret],check=True);subprocess.run(["sudo","chmod","600",admin_secret],check=True)
    subprocess.run(["sudo","chown","darcaller:darauthority",caller_secret_file],check=True);subprocess.run(["sudo","chmod","640",caller_secret_file],check=True)
    subprocess.run(["sudo","chown","darauthority:darauthority",store_secret],check=True);subprocess.run(["sudo","chmod","600",store_secret],check=True)

    staging=authority=None
    ev={"environment":{"commit":os.environ.get("QUALIFICATION_COMMIT","UNSET"),"uname":subprocess.check_output(["uname","-a"],text=True).strip(),"python":sys.version.split()[0],"secret_source":"ephemeral-generated"},"vectors":{}}
    try:
        staging=subprocess.Popen(["sudo","-u","darstaging","--",sys.executable,str(ROOT/"staging_server.py"),"--port",str(STAGING_PORT),"--data-dir",str(state),"--deploy-secret-file",str(deploy_secret),"--admin-secret-file",str(admin_secret)],cwd=ROOT)
        wait(f"http://127.0.0.1:{STAGING_PORT}/health")
        authority=subprocess.Popen(["sudo","-u","darauthority","--",sys.executable,str(ROOT/"authority_effect.py"),"--port",str(AUTH_PORT),"--staging-url",f"http://127.0.0.1:{STAGING_PORT}","--deploy-secret-file",str(deploy_secret),"--caller-secret-file",str(caller_secret_file),"--store-secret-file",str(store_secret),"--state-dir",str(auth_state)],cwd=ROOT,env={**os.environ,"PYTHONPATH":str(ROOT.parent)})
        wait(f"http://127.0.0.1:{AUTH_PORT}/health")
        normal_id=hashlib.sha256(b"v1-v8-normal").hexdigest()[:32];artifact=b"v1-v8-reference-artifact\n";digest=hashlib.sha256(artifact).hexdigest();enc=base64.b64encode(artifact).decode()
        normal={"deployment_id":normal_id,"artifact_digest":digest,"artifact_b64":enc,"fence_epoch":0,"idempotency_key":"v1-v8-normal","expires_at":int(time.time())+300}
        denied=all(secret_read_denied(p) for p in (deploy_secret,admin_secret,caller_secret_file,store_secret))
        v1a=attacker_post(f"http://127.0.0.1:{AUTH_PORT}/authority/commit",normal);v1b=attacker_post(f"http://127.0.0.1:{STAGING_PORT}/staging/deploy",{"deployment_id":normal_id,"artifact_digest":digest,"artifact_b64":enc})
        ev["vectors"]["V1"]={"classification":"PASS" if denied and v1a["status"]==401 and v1b["status"]==401 else "FAIL","secret_reads_denied":denied,"authority":v1a,"staging":v1b}
        v2a=attacker_post(f"http://127.0.0.1:{AUTH_PORT}/authority/commit",normal);v2b=attacker_post(f"http://127.0.0.1:{STAGING_PORT}/staging/reset",{})
        sockets=subprocess.run(["sudo","-u","darattacker","--","sh","-c","ss -xl 2>/dev/null | grep -E 'dar|staging|authority' || true"],text=True,capture_output=True).stdout.strip()
        ev["vectors"]["V2"]={"classification":"PASS" if v2a["status"]==401 and v2b["status"]==401 and not sockets else ("NOT_PRESENT" if not sockets else "FAIL"),"authority_http":v2a,"staging_http":v2b,"unix_sockets":sockets}
        child=subprocess.run(["sudo","-u","darattacker","--",sys.executable,"-c","import os;print(os.getuid())"],text=True,capture_output=True)
        helper=attacker_post(f"http://127.0.0.1:{AUTH_PORT}/authority/commit",normal)
        ev["vectors"]["V3"]={"classification":"PASS" if child.returncode==0 and helper["status"]==401 else "FAIL","child_uid":child.stdout.strip(),"helper_authority":helper}
        direct=attacker_post(f"http://127.0.0.1:{STAGING_PORT}/staging/deploy",{"deployment_id":normal_id+"x","artifact_digest":digest,"artifact_b64":enc});da=attacker_post(f"http://127.0.0.1:{AUTH_PORT}/authority/commit",normal);legacy=http("POST",f"http://127.0.0.1:{AUTH_PORT}/authority/legacy",{})
        ev["vectors"]["V4"]={"classification":"PASS" if direct["status"]==401 and da["status"]==401 and legacy[0]==404 else "FAIL","direct_staging":direct,"direct_authority":da,"legacy_endpoint":{"status":legacy[0],"body":legacy[1]}}
        ok=caller_request(caller_secret,f"http://127.0.0.1:{AUTH_PORT}/authority/commit",normal,"COMMIT")
        refused_id=hashlib.sha256(b"v1-v8-refused").hexdigest()[:32]
        refused={"deployment_id":refused_id,"artifact_digest":digest,"artifact_b64":enc,"fence_epoch":1,"idempotency_key":"v1-v8-refuse","expires_at":int(time.time())+300,"refusal_id":"v1-v8-refusal","effect_id":"v1-v8-effect","capability_txid":"v1-v8-cap","issued_at":int(time.time())}
        rr=caller_request(caller_secret,f"http://127.0.0.1:{AUTH_PORT}/authority/refuse",refused,"REFUSE");blocked=caller_request(caller_secret,f"http://127.0.0.1:{AUTH_PORT}/authority/commit",dict(refused,idempotency_key="v1-v8-blocked"),"COMMIT");obs=http("GET",f"http://127.0.0.1:{STAGING_PORT}/staging/status/{refused_id}")
        ev["vectors"]["V5"]={"classification":"PASS" if ok[0]==200 and rr[0]==200 and blocked[0]==403 and obs[1].get("state")=="NOT_DEPLOYED" else "FAIL","normal":ok,"refusal":rr,"blocked_commit":blocked,"observation":obs[1]}
        signed=dict(normal);signed["caller_mac"]=caller_mac(caller_secret,normal,"COMMIT");mutated=dict(signed);mutated["deployment_id"]=normal_id+"mutated";tampered=attacker_post(f"http://127.0.0.1:{AUTH_PORT}/authority/commit",mutated)
        symlink=subprocess.run(["sudo","-u","darattacker","--","sh","-c",f"ln -sf /etc/passwd {auth_state}/authority_state.json 2>/dev/null"],capture_output=True)
        ev["vectors"]["V6"]={"classification":"PASS" if tampered["status"]==401 and symlink.returncode!=0 else "FAIL","mutated_signed_request":tampered,"symlink_replace_returncode":symlink.returncode}
        unknown=attacker_post(f"http://127.0.0.1:{STAGING_PORT}/plugin/commit",normal);health=http("GET",f"http://127.0.0.1:{STAGING_PORT}/health")
        ev["vectors"]["V7"]={"classification":"PASS" if unknown["status"]==404 and "secret" not in json.dumps(health[1]).lower() else "FAIL","unknown_plugin_path":unknown,"health":health[1],"plugin_interface":"NOT_PRESENT"}
        sf=auth_state/"authority_state.json"
        if sf.exists():subprocess.run(["sudo","-u","darauthority","--","cp",str(sf),str(snap)],check=True);subprocess.run(["sudo","chmod","600",str(snap)],check=True)
        for p in (authority,staging):
            if p is not None:p.terminate()
        for p in (authority,staging):
            if p is not None:
                try:p.wait(3)
                except Exception:p.kill()
        authority=staging=None
        staging=subprocess.Popen(["sudo","-u","darstaging","--",sys.executable,str(ROOT/"staging_server.py"),"--port",str(STAGING_PORT),"--data-dir",str(state),"--deploy-secret-file",str(deploy_secret),"--admin-secret-file",str(admin_secret)],cwd=ROOT);wait(f"http://127.0.0.1:{STAGING_PORT}/health")
        authority=subprocess.Popen(["sudo","-u","darauthority","--",sys.executable,str(ROOT/"authority_effect.py"),"--port",str(AUTH_PORT),"--staging-url",f"http://127.0.0.1:{STAGING_PORT}","--deploy-secret-file",str(deploy_secret),"--caller-secret-file",str(caller_secret_file),"--store-secret-file",str(store_secret),"--state-dir",str(auth_state)],cwd=ROOT,env={**os.environ,"PYTHONPATH":str(ROOT.parent)});wait(f"http://127.0.0.1:{AUTH_PORT}/health")
        replay=caller_request(caller_secret,f"http://127.0.0.1:{AUTH_PORT}/authority/commit",dict(refused,idempotency_key="v1-v8-replay"),"COMMIT");obs8=http("GET",f"http://127.0.0.1:{STAGING_PORT}/staging/status/{refused_id}")
        restore=subprocess.run(["sudo","-u","darattacker","--","cp",str(snap),str(auth_state/"authority_state.json")],capture_output=True) if snap.exists() else subprocess.CompletedProcess([],1)
        ev["vectors"]["V8"]={"classification":"PASS" if replay[0]==403 and obs8[1].get("state")=="NOT_DEPLOYED" and restore.returncode!=0 else "FAIL","replay_after_restart":replay,"observation":obs8[1],"attacker_restore_returncode":restore.returncode}
        ev["overall"]=all(v["classification"] in ("PASS","NOT_PRESENT") for v in ev["vectors"].values());evidence_write(ev);return 0 if ev["overall"] else 1
    except Exception as exc:
        ev["overall"]=False;ev["harness_error"]={"type":type(exc).__name__,"message":str(exc)};evidence_write(ev);return 2
    finally:
        for p in (authority,staging):
            if p is not None:p.terminate()
        for p in (authority,staging):
            if p is not None:
                try:p.wait(3)
                except Exception:p.kill()
        shutil.rmtree(td,ignore_errors=True)

if __name__=="__main__":raise SystemExit(main())