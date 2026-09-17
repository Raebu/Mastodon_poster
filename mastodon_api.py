from __future__ import annotations
import os,requests,uuid
class Mastodon:
 def __init__(self):
  self.base=os.environ["MASTODON_BASE_URL"].rstrip("/");self.token=os.environ["MASTODON_ACCESS_TOKEN"];self.h={"Authorization":f"Bearer {self.token}"}
 def req(self,method,path,**kw):
  r=requests.request(method,self.base+path,headers={**self.h,**kw.pop("headers",{})},timeout=30,**kw);r.raise_for_status();return r.json() if r.content else {}
 def me(self):return self.req("GET","/api/v1/accounts/verify_credentials")
 def post(self,text,reply_to=None,visibility="public",language="en"):
  data={"status":text,"visibility":visibility,"language":language};
  if reply_to:data["in_reply_to_id"]=reply_to
  return self.req("POST","/api/v1/statuses",data=data,headers={"Idempotency-Key":str(uuid.uuid4())})
 def favourite(self,status_id):return self.req("POST",f"/api/v1/statuses/{status_id}/favourite")
 def boost(self,status_id):return self.req("POST",f"/api/v1/statuses/{status_id}/reblog")
 def follow(self,account_id):return self.req("POST",f"/api/v1/accounts/{account_id}/follow")
 def notifications(self,limit=30):return self.req("GET","/api/v1/notifications",params={"limit":limit})
 def home(self,limit=40):return self.req("GET","/api/v1/timelines/home",params={"limit":limit})
 def public(self,limit=40,local=False):return self.req("GET","/api/v1/timelines/public",params={"limit":limit,"local":str(local).lower()})
 def context(self,status_id):return self.req("GET",f"/api/v1/statuses/{status_id}/context")
 def search(self,q,limit=20):return self.req("GET","/api/v2/search",params={"q":q,"limit":limit,"resolve":"true"})
