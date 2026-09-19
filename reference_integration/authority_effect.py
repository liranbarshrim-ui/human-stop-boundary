#!/usr/bin/env python3
"""Separate authority process for the reference staging effect."""
from __future__ import annotations
import argparse, json, os, secrets, subprocess, sys, time, urllib.error, urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from staging_auth import mint_deploy_token

STATE = {}
DEPLOY_SECRET = None
ADMIN_RESET_SECRET = None
STAGING_URL = None


def post(path, body, secret=None):
    data = json.dumps(body).encode()
    req = urllib.request.Request(STAGING_URL + path, data=data, headers={"Content-Type":"application/json"})
    if secret is not None:
        req.add_header("X-Auth-Mac", __import__("staging_auth").mac_body(secret, body, "deploy" if path.endswith("deploy") else "refuse"))
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


def authorize_and_deploy(body):
    if not body.get("deployment_id") or not body.get("artifact_digest"):
        return 400, {"error":"missing_identity"}
    token = mint_deploy_token(DEPLOY_SECRET, body["deployment_id"], body["artifact_digest"], int(body["fence_epoch"]), body["idempotency_key"], int(body["expires_at"]))
    deploy_body = dict(body, deploy_token=token)
    return post("/staging/deploy", deploy_body)


class Handler(BaseHTTPRequestHandler):
    def _reply(self, status, payload):
        raw=json.dumps(payload, sort_keys=True).encode(); self.send_response(status); self.send_header("Content-Type","application/json"); self.send_header("Content-Length",str(len(raw))); self.end_headers(); self.wfile.write(raw)
    def do_POST(self):
        n=int(self.headers.get("Content-Length","0")); body=json.loads(self.rfile.read(n) or b"{}")
        if self.path == "/authority/commit":
            status,payload=authorize_and_deploy(body); self._reply(status,payload); return
        self._reply(404,{"error":"not_found"})
    def log_message(self,*args): pass


def main():
    global DEPLOY_SECRET, ADMIN_RESET_SECRET, STAGING_URL
    ap=argparse.ArgumentParser(); ap.add_argument("--port",type=int,default=18876); ap.add_argument("--staging-url",required=True); ap.add_argument("--deploy-secret-file",required=True)
    a=ap.parse_args(); STAGING_URL=a.staging_url.rstrip("/")
    DEPLOY_SECRET=open(a.deploy_secret_file,"r",encoding="utf-8").read().strip()
    if not DEPLOY_SECRET: raise SystemExit("empty deploy secret")
    ThreadingHTTPServer(("127.0.0.1",a.port),Handler).serve_forever()

if __name__ == "__main__": main()
