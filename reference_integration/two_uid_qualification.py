#!/usr/bin/env python3
"""Runtime qualification across attacker, caller, authority and staging UIDs."""
from __future__ import annotations
import base64,hashlib,json,os,pathlib,pwd,shutil,subprocess,sys,tempfile,time,urllib.error,urllib.request
ROOT=pathlib.Path(__file__).resolve().parent; OUT=ROOT/"two_uid_evidence.json"; PORT=18877; AUTH_PORT=18878

def http(method,url,body=None):
    data=None if body is None else json.dumps(body).encode(); req=urllib.request.Request(url,data=data,method=method,headers={"Content-Type":"application/json"})
    try:
        with urllib.request.urlopen(req,timeout=5) as r:return r.status,json.loads(r.read())
    except urllib.error.HTTPError as e:return e.code,json.loads(e.read())

def wait(url):
    for _ in range(80):
        try:
            if http("GET",url)[0]==200:return
        except Exception:pass
        time.sleep(.1)
    raise RuntimeError("service did not start")

def ensure_user(name):
    try:return pwd.getpwnam(name).pw_uid
    except KeyError:
        subprocess.run(["sudo","useradd","--system","--no-create-home",name],check=True); return pwd.getpwnam(name).pw_uid

def caller_request(user,secret_file,url,body_file,purpose):
    out=subprocess.check_output(["sudo","-u",user,"--",sys.executable,str(ROOT/"caller_client.py"),"--secret-file",str(secret_file),"--url",url,"--body-file",str(body_file),"--purpose",purpose],text=True)
    return json.loads(out)

def main():
    attacker="darattacker"; caller="darcaller"; authority="darauthority"; staging_user="darstaging"
    for u in (attacker,caller,authority,staging_user): ensure_user(u)
    try: subprocess.run(["sudo","groupadd","--system","dareffect"],check=True)
    except subprocess.CalledProcessError: pass
    for u in (authority,staging_user): subprocess.run(["sudo","usermod","-a","-G","dareffect",u],check=True)
    td=pathlib.Path(tempfile.mkdtemp(prefix="dar-four-uid-")); os.chmod(td,0o755); state=td/"state"; state.mkdir(); os.chmod(state,0o755)
    secret=td/"deploy.secret"; admin=td/"admin.secret"; caller_secret=td/"caller.secret"
    secret.write_text("deploy-"+os.urandom(24).hex()+"\n"); admin.write_text("admin-"+os.urandom(24).hex()+"\n"); caller_secret.write_bytes(os.urandom(32))
    subprocess.run(["sudo","chown",f"{authority}:dareffect",secret],check=True); subprocess.run(["sudo","chmod","640",secret],check=True)
    subprocess.run(["sudo","chown",f"{staging_user}:{staging_user}",admin],check=True); subprocess.run(["sudo","chmod","600",admin],check=True)
    subprocess.run(["sudo","chown",f"{caller}:{authority}",caller_secret],check=True); subprocess.run(["sudo","chmod","640",caller_secret],check=True)
    artifact=ROOT/"artifact.bin"; artifact.write_bytes(b"reference-artifact-v4\n"); digest=hashlib.sha256(artifact.read_bytes()).hexdigest(); enc=base64.b64encode(artifact.read_bytes()).decode()
    staging=subprocess.Popen(["sudo","-u",staging_user,"--",sys.executable,str(ROOT/"staging_server.py"),"--port",str(PORT),"--data-dir",str(state),"--deploy-secret-file",str(secret),"--admin-secret-file",str(admin)],cwd=ROOT)
    authority_p=subprocess.Popen(["sudo","-u",authority,"--",sys.executable,str(ROOT/"authority_effect.py"),"--port",str(AUTH_PORT),"--staging-url",f"http://127.0.0.1:{PORT}","--deploy-secret-file",str(secret),"--caller-secret-file",str(caller_secret)],cwd=ROOT)
    ev={"environment":{"commit":subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip(),"uname":subprocess.check_output(["uname","-a"],text=True).strip(),"python":sys.version.split()[0],"uids":{u:pwd.getpwnam(u).pw_uid for u in (attacker,caller,authority,staging_user)}},"tests":{}}
    try:
        wait(f"http://127.0.0.1:{PORT}/health"); wait(f"http://127.0.0.1:{AUTH_PORT}/health")
        r=subprocess.run(["sudo","-u",attacker,"--","cat",str(secret)],text=True,capture_output=True); ev["tests"]["attacker_cannot_read_deploy_secret"]={"pass":r.returncode!=0,"returncode":r.returncode}
        r=subprocess.run(["sudo","-u",attacker,"--","cat",str(caller_secret)],text=True,capture_output=True); ev["tests"]["attacker_cannot_read_caller_secret"]={"pass":r.returncode!=0,"returncode":r.returncode}
        r=subprocess.run(["sudo","-u",attacker,"--","cat",str(admin)],text=True,capture_output=True); ev["tests"]["attacker_cannot_read_admin_secret"]={"pass":r.returncode!=0,"returncode":r.returncode}
        body={"deployment_id":"four-uid-normal","artifact_digest":digest,"artifact_b64":enc,"fence_epoch":1,"idempotency_key":"normal-1","expires_at":int(time.time())+300}; bf=td/"normal.json"; bf.write_text(json.dumps(body)); os.chmod(bf,0o644)
        result=caller_request(caller,caller_secret,f"http://127.0.0.1:{AUTH_PORT}/authority/commit",bf,"COMMIT"); _,obs=http("GET",f"http://127.0.0.1:{PORT}/staging/status/{body['deployment_id']}"); ev["tests"]["normal_deploy"]={"result":result,"observation":obs,"pass":result["status"]==200 and obs.get("state")=="DEPLOYED" and obs.get("artifact_digest")==digest}
        attack_body={"deployment_id":"attacker-direct","artifact_digest":hashlib.sha256(b"x").hexdigest(),"artifact_b64":base64.b64encode(b"x").decode()}; s,p=http("POST",f"http://127.0.0.1:{PORT}/staging/deploy",attack_body); ev["tests"]["V4_V7_direct_staging_deploy"]={"status":s,"response":p,"pass":s==401}
        s,p=http("POST",f"http://127.0.0.1:{PORT}/staging/reset",{}); ev["tests"]["reset_without_admin"]={"status":s,"response":p,"pass":s==401}
        s,p=http("POST",f"http://127.0.0.1:{AUTH_PORT}/authority/commit",body); ev["tests"]["attacker_direct_authority_without_caller_auth"]={"status":s,"response":p,"pass":s==401}
        refused={"deployment_id":"four-uid-refused","artifact_digest":digest,"artifact_b64":enc,"fence_epoch":2,"idempotency_key":"refuse-1","expires_at":int(time.time())+300,"refusal_id":"ref-1"}; rf=td/"refuse.json"; rf.write_text(json.dumps(refused)); os.chmod(rf,0o644)
        result=caller_request(caller,caller_secret,f"http://127.0.0.1:{AUTH_PORT}/authority/refuse",rf,"REFUSE"); ev["tests"]["publish_refusal"]={"result":result,"pass":result["status"]==200}
        replay=dict(refused,idempotency_key="replay-1"); rp=td/"replay.json"; rp.write_text(json.dumps(replay)); os.chmod(rp,0o644)
        result=caller_request(caller,caller_secret,f"http://127.0.0.1:{AUTH_PORT}/authority/commit",rp,"COMMIT"); _,obs=http("GET",f"http://127.0.0.1:{PORT}/staging/status/{refused['deployment_id']}"); ev["tests"]["V8_post_refusal_replay"]={"result":result,"observation":obs,"pass":result["status"]==403 and obs.get("state")=="NOT_DEPLOYED"}
        ev["overall"]=all(t.get("pass") for t in ev["tests"].values()); OUT.write_text(json.dumps(ev,indent=2,sort_keys=True)+"\n"); print(json.dumps(ev,indent=2,sort_keys=True)); print("SHA256",hashlib.sha256(OUT.read_bytes()).hexdigest()); return 0 if ev["overall"] else 1
    finally:
        authority_p.terminate(); staging.terminate()
        try: authority_p.wait(3); staging.wait(3)
        except Exception: authority_p.kill(); staging.kill()
        shutil.rmtree(td,ignore_errors=True)
if __name__=="__main__": raise SystemExit(main())
