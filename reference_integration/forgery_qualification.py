#!/usr/bin/env python3
"""Bounded attacker-side forgery qualification for the isolated staging effect."""
from __future__ import annotations
import base64, hashlib, hmac, json, os, pathlib, pwd, subprocess, tempfile, time, urllib.error, urllib.request

ROOT = pathlib.Path(__file__).resolve().parent
PORT = 18879

def attacker_post(url, body):
    code = '''import json,sys,urllib.request,urllib.error
url=sys.argv[1]; body=json.loads(sys.argv[2])
req=urllib.request.Request(url,data=json.dumps(body).encode(),method="POST",headers={"Content-Type":"application/json"})
try:
 with urllib.request.urlopen(req,timeout=5) as r: print(json.dumps({"status":r.status,"body":json.loads(r.read())}))
except urllib.error.HTTPError as e: print(json.dumps({"status":e.code,"body":json.loads(e.read())}))
'''
    out = subprocess.check_output(["sudo", "-u", "darattacker", "--", "python3", "-c", code, url, json.dumps(body)], text=True, timeout=10)
    return json.loads(out)

def wait_health(url, proc):
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            stdout = proc.stdout.read().strip() if proc.stdout else ""
            stderr = proc.stderr.read().strip() if proc.stderr else ""
            raise RuntimeError(f"staging service exited before health check: exit={proc.returncode}; stdout={stdout!r}; stderr={stderr!r}")
        try:
            with urllib.request.urlopen(url, timeout=2) as r:
                if r.status == 200:
                    return
        except Exception:
            pass
        time.sleep(.1)
    stdout = proc.stdout.read().strip() if proc.stdout else ""
    stderr = proc.stderr.read().strip() if proc.stderr else ""
    raise RuntimeError(f"staging service did not start: exit={proc.poll()}; stdout={stdout!r}; stderr={stderr!r}")

def ensure_user(name):
    try: return pwd.getpwnam(name).pw_uid
    except KeyError:
        subprocess.run(["sudo", "useradd", "--system", "--no-create-home", name], check=True)
        return pwd.getpwnam(name).pw_uid

def forged_token(secret_guess, deployment_id, digest, epoch=0, idem="forge"):
    now = int(time.time()); expires = now + 300
    canonical = "|".join(("DEPLOY", deployment_id, digest, str(epoch), idem, str(now), str(expires))).encode()
    mac = hmac.new(secret_guess, canonical, hashlib.sha256).hexdigest()
    return {"purpose":"DEPLOY","deployment_id":deployment_id,"artifact_digest":digest,"fence_epoch":epoch,"idempotency_key":idem,"issued_at":now,"expires_at":expires,"mac":mac}

def forged_refusal(secret_guess, deployment_id, epoch=0, refusal_id="forge-refusal"):
    mac = hmac.new(secret_guess, f"REFUSE|{deployment_id}|{epoch}|{refusal_id}".encode(), hashlib.sha256).hexdigest()
    return {"deployment_id":deployment_id,"fence_epoch":epoch,"refusal_id":refusal_id,"mac":mac}

def main():
    attacker, staging_user = "darattacker", "darstaging"
    ensure_user(attacker); ensure_user(staging_user)
    td = pathlib.Path(tempfile.mkdtemp(prefix="dar-forgery-")); state = td / "state"; state.mkdir()
    secret = td / "deploy.secret"; secret.write_text("deploy-" + os.urandom(24).hex() + "\n")
    subprocess.run(["sudo", "chown", f"{staging_user}:{staging_user}", state], check=True)
    subprocess.run(["sudo", "chmod", "700", state], check=True)
    subprocess.run(["sudo", "chown", f"{staging_user}:{staging_user}", secret], check=True)
    subprocess.run(["sudo", "chmod", "640", secret], check=True)
    artifact = td / "artifact.bin"; artifact.write_bytes(b"forgery-qualification-artifact\n")
    raw = artifact.read_bytes(); digest = hashlib.sha256(raw).hexdigest(); enc = base64.b64encode(raw).decode()
    forged_id = hashlib.sha256(b"forgery-deployment").hexdigest()[:32]
    p = subprocess.Popen(["sudo","-u",staging_user,"--","python3",str(ROOT/"staging_server.py"),"--port",str(PORT),"--data-dir",str(state),"--deploy-secret-file",str(secret),"--admin-secret-file",str(secret)], cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    ev = {"environment":{"commit":os.environ.get("QUALIFICATION_COMMIT","UNSET"),"python":__import__("sys").version.split()[0]},"tests":{}}
    try:
        wait_health(f"http://127.0.0.1:{PORT}/health", p)
        guessed = b"wrong-secret-guess"; token = forged_token(guessed, forged_id, digest)
        body={"deployment_id":forged_id,"artifact_digest":digest,"artifact_b64":enc,"deploy_authorization":token}
        r=attacker_post(f"http://127.0.0.1:{PORT}/staging/deploy",body)
        ev["tests"]["forged_deploy_wrong_secret"]={**r,"pass":r["status"]==401 and r["body"].get("error")=="invalid_mac"}
        mutated=dict(token); mutated["deployment_id"]=hashlib.sha256(b"mutated-id").hexdigest()[:32]
        r=attacker_post(f"http://127.0.0.1:{PORT}/staging/deploy",{**body,"deployment_id":mutated["deployment_id"],"deploy_authorization":mutated})
        ev["tests"]["forged_deploy_mutated_identity"]={**r,"pass":r["status"]==401 and r["body"].get("error")=="invalid_mac"}
        guesses=[os.urandom(32) for _ in range(64)] + [b"",b"deploy",b"deploy-secret",b"wrong-secret-guess"]
        brute_results=[]
        for i,guess in enumerate(guesses):
            t=forged_token(guess, forged_id, digest, idem=f"guess-{i}")
            rr=attacker_post(f"http://127.0.0.1:{PORT}/staging/deploy",{**body,"deploy_authorization":t})
            brute_results.append(rr["status"]==401 and rr["body"].get("error")=="invalid_mac")
        ev["tests"]["bounded_secret_guessing_68_attempts"]={"attempts":len(guesses),"all_rejected":all(brute_results),"pass":all(brute_results)}
        rr=attacker_post(f"http://127.0.0.1:{PORT}/staging/refuse",forged_refusal(guessed, forged_id))
        ev["tests"]["forged_refusal_wrong_secret"]={**rr,"pass":rr["status"]==401 and rr["body"].get("error")=="invalid_refuse_mac"}
        tamper = state / "staging_state.json"
        result=subprocess.run(["sudo","-u",attacker,"--","sh","-c",f"printf tampered >> {tamper}"],text=True,capture_output=True)
        ev["tests"]["attacker_cannot_tamper_persistent_state"]={"returncode":result.returncode,"stderr":result.stderr.strip(),"pass":result.returncode!=0}
        ev["overall"]=all(x.get("pass") for x in ev["tests"].values())
        out=ROOT/"forgery_evidence.json"; out.write_text(json.dumps(ev,indent=2,sort_keys=True)+"\n")
        print(json.dumps(ev,indent=2,sort_keys=True)); print("SHA256",hashlib.sha256(out.read_bytes()).hexdigest()); return 0 if ev["overall"] else 1
    except Exception as exc:
        ev["overall"]=False; ev["harness_error"]={"type":type(exc).__name__,"message":str(exc)}
        out=ROOT/"forgery_evidence.json"; out.write_text(json.dumps(ev,indent=2,sort_keys=True)+"\n")
        print(json.dumps(ev,indent=2,sort_keys=True)); print("SHA256",hashlib.sha256(out.read_bytes()).hexdigest()); return 2
    finally:
        p.terminate()
        try: p.wait(3)
        except Exception: p.kill()
        import shutil; shutil.rmtree(td,ignore_errors=True)

if __name__ == "__main__": raise SystemExit(main())
