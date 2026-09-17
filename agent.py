from __future__ import annotations
import os,re
from collections import Counter
from html import unescape
from openai import OpenAI
from mastodon_api import Mastodon
from voice import MARTIN_VOICE
import social_os
DRY=os.getenv("DRY_RUN","true").lower()=="true";MODEL=os.getenv("OPENAI_MODEL","gpt-5-mini");MAX=int(os.getenv("MASTODON_MAX_ACTIONS","5"));MAX_FOLLOWS=int(os.getenv("MASTODON_MAX_FOLLOWS","2"))
TOPICS=[x.strip() for x in os.getenv("MASTODON_DISCOVERY_TOPICS","AI,automation,software,enterprise technology,digital assets,blockchain,technology governance").split(',') if x.strip()]
def clean(html):return re.sub(r"\s+"," ",re.sub(r"<[^>]+>"," ",unescape(html or ""))).strip()
def ask(prompt):return OpenAI(api_key=os.environ["OPENAI_API_KEY"]).responses.create(model=MODEL,input=MARTIN_VOICE+"\nTASK\n"+prompt).output_text.strip()
def decide(text,source="feed"):
 if not text:return "NO_ACTION"
 x=ask(f"Mastodon {source} post:\n{text}\nChoose exactly one: NO_ACTION, FAVOURITE, REPLY, BOOST. Prefer NO_ACTION. REPLY only if Martin can add a new mechanism, distinction, consequence, useful context or respectful challenge. FAVOURITE when useful but no public reply is warranted. BOOST only if unusually useful to Martin's professional audience. Output label only.").upper();return x if x in {"NO_ACTION","FAVOURITE","REPLY","BOOST"} else "NO_ACTION"
def reply(text):
 x=ask(f"Mastodon post:\n{text}\nWrite a concise Mastodon reply adding genuinely new substance. Complex thinking, simple language. Do not flatter, agree generically or paraphrase. No forced question. Output reply only or NO_REPLY.");return None if x.upper().startswith("NO_REPLY") else x
def follow_worthy(account,text):
 bio=clean(account.get('note',''));name=account.get('display_name') or account.get('acct','')
 x=ask(f"Account: {name}\nBio: {bio}\nRepresentative post: {text}\nShould Martin follow this account for durable professional value, not merely because one post is interesting? Consider expertise, originality, relevance to technology/business and network diversity. Avoid news aggregators, brands with generic feeds, engagement bait and accounts with insufficient evidence. Output FOLLOW or NO_FOLLOW only.").upper()
 return x.startswith('FOLLOW')
def discover(m):
 out=[];seen=set()
 # Hashtag timelines are dependable discovery; status search is included when the instance returns it.
 for topic in TOPICS[:7]:
  tag=re.sub(r'[^A-Za-z0-9_]','',topic.replace(' ','') )
  try:
   for s in m.tag(tag,8):
    sid=str(s.get('id',''))
    if sid and sid not in seen:seen.add(sid);out.append((s,'tag:'+tag))
  except Exception as e:print('DISCOVERY_WARNING',tag,type(e).__name__)
  try:
   for s in m.search(topic,8,'statuses').get('statuses',[]):
    sid=str(s.get('id',''))
    if sid and sid not in seen:seen.add(sid);out.append((s,'search:'+topic))
  except Exception:pass
 return out
def main():
 m=Mastodon();me=m.me();print("Authenticated Mastodon account:",me.get("acct"));seen=set();actions=0;follows=0;run_counts=Counter()
 items=[(x.get('status',x),'notification/home') for x in m.notifications(30)+m.home(40)]+discover(m)
 for s,source in items:
  sid=str(s.get("id",''));account=s.get("account",{});aid=str(account.get('id',''));acct=str(account.get("acct",''));text=clean(s.get("content"))
  if not sid or sid in seen or aid==str(me.get("id")):continue
  seen.add(sid);allowed,reason=social_os.allow_account(acct,run_counts)
  if not allowed:
   print("NO_ACTION",sid,acct,"SOCIAL_OS",reason);continue
  choice=decide(text,source);print(choice,sid,acct,source)
  if choice!="NO_ACTION" and actions<MAX:
   if choice=="REPLY":
    body=reply(text)
    if body:
     if not DRY:m.post(body,reply_to=sid)
     actions+=1;run_counts[acct.lower()]+=1;social_os.log_interaction(acct,sid,choice,source,DRY)
   elif choice=="FAVOURITE":
    if not DRY:m.favourite(sid)
    actions+=1;run_counts[acct.lower()]+=1;social_os.log_interaction(acct,sid,choice,source,DRY)
   elif choice=="BOOST":
    if not DRY:m.boost(sid)
    actions+=1;run_counts[acct.lower()]+=1;social_os.log_interaction(acct,sid,choice,source,DRY)
  if source.startswith(('tag:','search:')) and aid and follows<MAX_FOLLOWS and follow_worthy(account,text):
   try:
    rel=m.relationships([aid]);already=bool(rel and (rel[0].get('following') or rel[0].get('requested')))
   except Exception:already=False
   if not already:
    print('FOLLOW',aid,acct,source)
    if not DRY:m.follow(aid)
    follows+=1;social_os.log_interaction(acct,sid,'FOLLOW',source,DRY)
  if actions>=MAX and follows>=MAX_FOLLOWS:break
 social_os.log_run("growth",actions+follows,DRY,f"engagement={actions}; follows={follows}; unique_accounts={len(run_counts)}")
 print(f"SUMMARY engagement={actions} follows={follows} unique_accounts={len(run_counts)} dry_run={DRY}")
if __name__=="__main__":main()
