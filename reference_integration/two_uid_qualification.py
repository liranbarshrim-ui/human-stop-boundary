#!/usr/bin/env python3
"""Runtime qualification of separate authority, staging and attacker identities."""
from __future__ import annotations
import base64,hashlib,hmac,json,os,pathlib,pwd,shutil,subprocess,sys,tempfile,time,urllib.error,urllib.request
ROOT=pathlib.Path(__file__).resolve().parent; OUT=ROOT/"two_uid_evidence.json"; PORT=18877; AUTH_PORT=18878

def http(method,url,body=None,headers=None):
    data=None if body is None else json.dumps(body).encode(); req=urllib.request.Request(url,data=data,method=method,headers={"Content-Type":"application/json",**(headers or {})})
    try:
        with urllib.request.urlopen(req,timeout=5) as r:return r.status,json.loads(r.read())
    except urllib.error.HTTPError as e:return e.code,json.loads(e.read())

def wait(url):
    for _ in range(60):
        try:
            if http("GET",url)[0]==200:return
        except Exception:pass
        time.sleep(.1)
    raise RuntimeError("service did not start")
def caller_mac(secret,body,purpose):
    fields=(purpose,body.get("deployment_id",""),body.get("artifact_digest",""),str(body.get("fence_epoch","")),body.get("idempotency_key","") )
    return hmac.new(secret,"|".join(fields).encode(),hashlib.sha256).hexdigest()
def main():
    attacker="darattacker"; authority="darauthority"
    for user in (attacker,authority):
        try:pwd.getpwnam(user)
        except KeyError:subprocess.run(["sudo","useradd","--system","--no-create-home",user],check=True)
    td=pathlib.Path(tempfile.mkdtemp(prefix="dar-two-uid-")); state=td/"state"; secret=td/"deploy.secret"; admin=td/"admin.secret"; caller=td/"caller.secret"
    secret.write_text("deploy-"+os.urandom(24).hex()+"\n");admin.write_text("admin-"+os.urandom(24).hex()+"\n");caller.write_bytes(os.urandom(32));
    for p in (secret,admin,caller):os.chmod(p,0o600)
    subprocess.run(["sudo","chown",f"{authority}:{authority}",secret,admin,caller,td],check=True)
    artifact=ROOT/"artifact.bin";artifact.write_bytes(b"reference-artifact-v3\n");digest=hashlib.sha256(artifact.read_bytes()).hexdigest(); enc=base64.b64encode(artifact.read_bytes()).decode()
    staging=subprocess.Popen([sys.executable,str(ROOT/"staging_server.py"),"--port",str(PORT),"--data-dir",str(state),"--deploy-secret-file",str(secret),"--admin-secret-file",str(admin)],cwd=ROOT)
    authority_p=subprocess.Popen(["sudo","-u",authority,"--",sys.executable,str(ROOT/"authority_effect.py"),"--port",str(AUTH_PORT),"--staging-url",f"http://127.0.0.1:{PORT}","--deploy-secret-file",str(secret),"--caller-secret-file",str(caller)],cwd=ROOT)
    try:
        wait(f"http://127.0.0.1:{PORT}/health");wait(f"http://127.0.0.1:{AUTH_PORT}/health")
        caller_secret=caller.read_bytes()
        ev={"environment":{"commit":subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip(),"uname":subprocess.check_output(["uname","-a"],text=True).strip(),"python":sys.version.split()[0],"attacker_uid":pwd.getpwnam(attacker).pw_uid,"authority_uid":pwd.getpwnam(authority).pw_uid},"tests":{}}
        r=subprocess.run(["sudo","-u",attacker,"--","cat",str(secret)],text=True,capture_output=True);ev["tests"]["secret_custody"]={"pass":r.returncode!=0,"returncode":r.returncode}
        body={"deployment_id":"two-uid-normal","artifact_digest":digest,"artifact_b64":enc,"fence_epoch":1,"idempotency_key":"normal-1","expires_at":int(time.time())+300}
        signed=dict(body,caller_mac=caller_mac(caller_secret,body,"COMMIT"));s,p=http("POST",f"http://127.0.0.1:{AUTH_PORT}/authority/commit",signed);_,o=http("GET",f"http://127.0.0.1:{PORT}/staging/status/{body['deployment_id']}");ev["tests"]["normal_deploy"]={"authority_status":s,"authority_response":p,"observation":o,"pass":s==200 and o.get("state")=="DEPLOYED" and o.get("artifact_digest")==digest}
        attack_body={"deployment_id":"attacker-direct","artifact_digest":hashlib.sha256(b"x").hexdigest(),"artifact_b64":base64.b64encode(b"x").decode()};s,p=http("POST",f"http://127.0.0.1:{PORT}/staging/deploy",attack_body);ev["tests"]["V4_V7_direct_deploy"]={"status":s,"response":p,"pass":s==401}
        s,p=http("POST",f"http://127.0.0.1:{PORT}/staging/reset",{});ev["tests"]["reset_without_admin"]={"status":s,"pass":s==401}
        authority_attack=dict(body);s,p=http("POST",f"http://127.0.0.1:{AUTH_PORT}/authority/commit",authority_attack);ev["tests"]["V1_direct_authority_call_without_caller_auth"]={"status":s,"response":p,"pass":s==401}
        refused={"deployment_id":"two-uid-refused","artifact_digest":digest,"artifact_b64":enc,"fence_epoch":2,"idempotency_key":"refuse-1","expires_at":int(time.time())+300,"refusal_id":"ref-1"}; signed_ref=dict(refused,caller_mac=caller_mac(caller_secret,refused,"REFUSE"));s,p=http("POST",f"http://127.0.0.1:{AUTH_PORT}/authority/refuse",signed_ref);ev["tests"]["publish_refusal"]={"status":s,"response":p,"pass":s==200}
        replay=dict(refused,idempotency_key="replay-1");signed_replay=dict(replay,caller_mac=caller_mac(caller_secret,replay,"COMMIT"));s,p=http("POST",f"http://127.0.0.1:{AUTH_PORT}/authority/commit",signed_replay);_,o=http("GET",f"http://127.0.0.1:{PORT}/staging/status/{refused['deployment_id']}");ev["tests"]["V8_post_refusal_replay"]={"status":s,"response":p,"observation":o,"pass":s==403 and o.get("state")=="NOT_DEPLOYED"}
        ev["overall"]=all(x.get("pass") for x in ev["tests"].values() if "pass" in x);OUT.write_text(json.dumps(ev,indent=2,sort_keys=True)+"\n");print(json.dumps(ev,indent=2,sort_keys=True));print("SHA256",hashlib.sha256(OUT.read_bytes()).hexdigest());return 0 if ev["overall"] else 1
    finally:
        authority_p.terminate();staging.terminate()
        try:authority_p.wait(3);staging.wait(3)
        except Exception:authority_p.kill();staging.kill()
        shutil.rmtree(td,ignore_errors=True)
if __name__=="__main__":raise SystemExit(main())
