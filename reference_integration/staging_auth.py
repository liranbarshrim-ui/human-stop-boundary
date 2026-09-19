"""Deploy authorization tokens bound to deployment identity and fence epoch."""
from __future__ import annotations
import hashlib,hmac,time

def mint_deploy_token(*,secret: bytes|str,deployment_id:str,artifact_digest:str,fence_epoch:int,idempotency_key:str,ttl_seconds:int=60)->dict:
    secret=secret.encode() if isinstance(secret,str) else secret
    issued_at=int(time.time()); expires_at=issued_at+ttl_seconds
    canonical="|".join(("DEPLOY",deployment_id,artifact_digest,str(int(fence_epoch)),idempotency_key,str(issued_at),str(expires_at))).encode()
    return {"purpose":"DEPLOY","deployment_id":deployment_id,"artifact_digest":artifact_digest,"fence_epoch":int(fence_epoch),"idempotency_key":idempotency_key,"issued_at":issued_at,"expires_at":expires_at,"mac":hmac.new(secret,canonical,hashlib.sha256).hexdigest()}

def verify_deploy_token(*,secret:bytes|str,token:dict,deployment_id:str,artifact_digest:str)->str|None:
    secret=secret.encode() if isinstance(secret,str) else secret
    try:
        if token.get("purpose")!="DEPLOY": return "bad_purpose"
        if token.get("deployment_id")!=deployment_id: return "deployment_id_mismatch"
        if token.get("artifact_digest")!=artifact_digest: return "artifact_digest_mismatch"
        issued_at=int(token["issued_at"]); expires_at=int(token["expires_at"]); fence_epoch=int(token["fence_epoch"]); idem=str(token["idempotency_key"]); mac=str(token["mac"])
    except Exception: return "malformed_token"
    now=int(time.time())
    if now>expires_at:return "token_expired"
    if issued_at>now+30:return "token_from_future"
    canonical="|".join(("DEPLOY",deployment_id,artifact_digest,str(fence_epoch),idem,str(issued_at),str(expires_at))).encode()
    if not hmac.compare_digest(hmac.new(secret,canonical,hashlib.sha256).hexdigest(),mac):return "invalid_mac"
    return None

def mac_refusal(secret:bytes|str,deployment_id:str,fence_epoch:int,refusal_id:str)->str:
    secret=secret.encode() if isinstance(secret,str) else secret
    return hmac.new(secret,f"REFUSE|{deployment_id}|{int(fence_epoch)}|{refusal_id}".encode(),hashlib.sha256).hexdigest()
