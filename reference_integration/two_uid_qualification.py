#!/usr/bin/env python3
"""Runtime qualification for the separate authority/staging trust boundary."""
from __future__ import annotations
import hashlib, json, os, pathlib, pwd, shutil, subprocess, sys, tempfile, time, urllib.error, urllib.request

ROOT=pathlib.Path(__file__).resolve().parent
OUT=ROOT/"two_uid_evidence.json"
PORT=18877
AUTH_PORT=18878
DEPLOY_ID="two-uid-reference-001"
ART=ROOT/"artifact.bin"


def http(method,url,body=None):
    data=None if body is None else json.dumps(body).encode(); req=urllib.request.Request(url,data=data,method=method,headers={"Content-Type":"application/json"} if data else {})
    try:
        with urllib.request.urlopen(req,timeout=5) as r:return r.status,json.loads(r.read())
    except urllib.error.HTTPError as e:return e.code,json.loads(e.read())


def wait(url):
    for _ in range(50):
        try:
            if http("GET",url)[0]==200:return
        except Exception:pass
        time.sleep(.1)
    raise RuntimeError("service did not start")


def run_as(user,cmd,env=None):
    return subprocess.run(["sudo","-u",user,"--"]+cmd,text=True,capture_output=True,env=env)


def main():
    attacker="darattacker"; authority="darauthority"
    try:
        pwd.getpwnam(attacker); pwd.getpwnam(authority)
    except KeyError:
        subprocess.run(["sudo","useradd","--system","--no-create-home",attacker],check=True)
        subprocess.run(["sudo","useradd","--system","--no-create-home",authority],check=True)
    td=pathlib.Path(tempfile.mkdtemp(prefix="dar-two-uid-")); state=td/"state.json"; secret=td/"deploy.secret"; admin=td/"admin.secret"
    secret.write_text("deploy-"+os.urandom(24).hex()+"\n"); admin.write_text("admin-"+os.urandom(24).hex()+"\n")
    os.chmod(secret,0o600); os.chmod(admin,0o600); subprocess.run(["sudo","chown",f"{authority}:{authority}",secret,admin],check=True)
    subprocess.run(["sudo","chown",f"{authority}:{authority}",td],check=True)
    shutil.copy(ROOT/"artifact.bin",td/"artifact.bin") if ART.exists() else ART.write_bytes(b"reference-artifact-v1\n")
    digest=hashlib.sha256(ART.read_bytes()).hexdigest()
    # The authority and staging are separate processes; attacker receives neither secret.
    staging=subprocess.Popen([sys.executable,str(ROOT/"staging_server.py"),"--port",str(PORT),"--state",str(state),"--secret-file",str(secret),"--admin-secret-file",str(admin)],cwd=ROOT)
    authority_p=subprocess.Popen(["sudo","-u",authority,"--",sys.executable,str(ROOT/"authority_effect.py"),"--port",str(AUTH_PORT),"--staging-url",f"http://127.0.0.1:{PORT}","--deploy-secret-file",str(secret)],cwd=ROOT)
    try:
        wait(f"http://127.0.0.1:{PORT}/health"); wait(f"http://127.0.0.1:{AUTH_PORT}/health")
        evidence={"environment":{},"tests":{}}
        evidence["environment"]={"commit":subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip(),"uname":subprocess.check_output(["uname","-a"],text=True).strip(),"python":sys.version.split()[0],"attacker_uid":pwd.getpwnam(attacker).pw_uid,"authority_uid":pwd.getpwnam(authority).pw_uid}
        # Secret custody: attacker cannot read the authority-owned file.
        r=run_as(attacker,["cat",str(secret)]); evidence["tests"]["secret_custody"]={"pass":r.returncode!=0,"returncode":r.returncode}
        body={"deployment_id":DEPLOY_ID,"artifact_digest":digest,"fence_epoch":1,"idempotency_key":"id-1","expires_at":int(time.time())+300}
        s,p=http("POST",f"http://127.0.0.1:{AUTH_PORT}/authority/commit",body); evidence["tests"]["normal_deploy"]={"status":s,"state":p}
        s,p=http("GET",f"http://127.0.0.1:{PORT}/staging/status/{DEPLOY_ID}"); evidence["tests"]["normal_observation"]={"status":s,"state":p}
        # Attacker cannot mint a deploy token or call reset/refuse directly.
        for name,path in [("direct_deploy","/staging/deploy"),("direct_refuse","/staging/refuse"),("deploy_secret_reset","/staging/reset")]:
            s,p=http("POST",f"http://127.0.0.1:{PORT}"+path,body); evidence["tests"][name]={"status":s,"response":p}
        # New adapter/replay cannot reset the external refusal; refusal is published by the authority path.
        ref=dict(body,reason="qualification-refusal",fence_epoch=2)
        # We intentionally do not expose admin credential to attacker. Refusal is injected by test setup only via authority-owned secret.
        import staging_auth
        refmac=staging_auth.mac_body(secret.read_text().strip(),ref,"refuse")
        req=urllib.request.Request(f"http://127.0.0.1:{PORT}/staging/refuse",data=json.dumps(ref).encode(),headers={"Content-Type":"application/json","X-Auth-Mac":refmac})
        with urllib.request.urlopen(req,timeout=5) as rr: refusal=(rr.status,json.loads(rr.read()))
        evidence["tests"]["publish_refusal"]={"status":refusal[0],"response":refusal[1]}
        s,p=http("POST",f"http://127.0.0.1:{AUTH_PORT}/authority/commit",dict(body,fence_epoch=2,idempotency_key="id-replay")); evidence["tests"]["post_refusal_commit"]={"status":s,"response":p}
        evidence["tests"]["overall"] = all([
            evidence["tests"]["secret_custody"]["pass"],
            evidence["tests"]["normal_observation"]["state"].get("state")=="DEPLOYED",
            evidence["tests"]["direct_deploy"]["status"]==401,
            evidence["tests"]["direct_refuse"]["status"]==401,
            evidence["tests"]["deploy_secret_reset"]["status"]==401,
            evidence["tests"]["post_refusal_commit"]["status"]==403,
        ])
        OUT.write_text(json.dumps(evidence,indent=2,sort_keys=True)+"\n")
        print(json.dumps(evidence,indent=2,sort_keys=True)); print("SHA256",hashlib.sha256(OUT.read_bytes()).hexdigest())
        if not evidence["tests"]["overall"]: raise SystemExit(1)
    finally:
        authority_p.terminate(); staging.terminate(); authority_p.wait(timeout=5); staging.wait(timeout=5); shutil.rmtree(td,ignore_errors=True)

if __name__=="__main__": main()
