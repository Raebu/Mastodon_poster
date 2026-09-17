from __future__ import annotations
# Research is deliberately fail-closed. A configured trusted research service may populate evidence;
# without one, current claims remain HOLD rather than being guessed.
import os,requests
def verify(claim):
 url=os.getenv('SOCIAL_RESEARCH_ENDPOINT','').strip()
 if not url:return {'verified':False,'reason':'no approved research executor configured','sources':[]}
 try:
  r=requests.post(url,json={'claim':claim},timeout=20);r.raise_for_status();d=r.json();sources=d.get('sources') or []
  return {'verified':bool(d.get('verified') and len(sources)>=1),'reason':d.get('reason',''),'sources':sources}
 except Exception as e:return {'verified':False,'reason':'research failure '+type(e).__name__,'sources':[]}
