#!/usr/bin/env python3
"""Run caller-authenticated requests as the untrusted-but-authorized caller UID."""
from __future__ import annotations
import argparse,hashlib,hmac,json,pathlib,urllib.error,urllib.request

def mac(secret,body,purpose):
    fields=(purpose,body.get("deployment_id",""),body.get("artifact_digest",""),str(body.get("fence_epoch","")),body.get("idempotency_key",""),body.get("effect_id",""),body.get("capability_txid",""),body.get("refusal_id",""),str(body.get("issued_at","")))
    return hmac.new(secret,"|".join(fields).encode("utf-8"),hashlib.sha256).hexdigest()

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--secret-file",required=True); ap.add_argument("--url",required=True); ap.add_argument("--body-file",required=True); ap.add_argument("--purpose",choices=("COMMIT","REFUSE"),required=True); a=ap.parse_args()
    secret=pathlib.Path(a.secret_file).read_bytes().strip(); body=json.loads(pathlib.Path(a.body_file).read_text()); body["caller_mac"]=mac(secret,body,a.purpose)
    req=urllib.request.Request(a.url,data=json.dumps(body).encode(),method="POST",headers={"Content-Type":"application/json"})
    try:
        with urllib.request.urlopen(req,timeout=5) as r: print(json.dumps({"status":r.status,"body":json.loads(r.read())},sort_keys=True)); return 0
    except urllib.error.HTTPError as e: print(json.dumps({"status":e.code,"body":json.loads(e.read())},sort_keys=True)); return 0
if __name__=="__main__": raise SystemExit(main())
