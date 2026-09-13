#!/usr/bin/env python3
import argparse, os
from dar.store import Store
from dar.process_dispatcher import UnixDispatcherServer

ap=argparse.ArgumentParser()
ap.add_argument('--socket',required=True); ap.add_argument('--root',required=True); ap.add_argument('--state',required=True)
ap.add_argument('--secret-file',required=True); ap.add_argument('--allowed-uid',type=int,required=True)
ap.add_argument('--boot-id'); ap.add_argument('--seccomp',action='store_true'); ap.add_argument('--landlock',action='store_true')
a=ap.parse_args()
with open(a.secret_file,'rb') as f: secret=f.read()
if len(secret)<32: raise SystemExit('secret must be at least 32 bytes')
os.chmod(a.secret_file,0o600)
store=Store(a.state,secret)
server=UnixDispatcherServer(a.socket,a.root,store,secret,allowed_uid=a.allowed_uid,boot_id=a.boot_id)
server.enable_seccomp=a.seccomp; server.enable_landlock=a.landlock
server.serve_forever()
