import json,time,hashlib
class AuditLog:
    def __init__(self,path): self.path=path
    def append(self,event):
        rec={'ts':time.time(),'event':event}; raw=json.dumps(rec,sort_keys=True,separators=(',',':')).encode(); rec['digest']=hashlib.sha256(raw).hexdigest()
        with open(self.path,'a',encoding='utf8') as f: f.write(json.dumps(rec,sort_keys=True)+'\n'); f.flush()
