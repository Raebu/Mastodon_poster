from __future__ import annotations
import os,re,json
from html import unescape
from openai import OpenAI
from mastodon_api import Mastodon
from voice import MARTIN_VOICE
DRY=os.getenv("DRY_RUN","true").lower()=="true";MODEL=os.getenv("OPENAI_MODEL","gpt-5-mini");MAX=int(os.getenv("MASTODON_MAX_ACTIONS","5"))
def clean(html):return re.sub(r"\s+"," ",re.sub(r"<[^>]+>"," ",unescape(html or ""))).strip()
def ask(prompt):return OpenAI(api_key=os.environ["OPENAI_API_KEY"]).responses.create(model=MODEL,input=MARTIN_VOICE+"\nTASK\n"+prompt).output_text.strip()
def decide(text):
 if not text:return "NO_ACTION"
 x=ask(f"Mastodon post:\n{text}\nChoose exactly one: NO_ACTION, FAVOURITE, REPLY, BOOST. Prefer NO_ACTION. REPLY only if Martin can add a new mechanism, distinction, consequence, useful context or respectful challenge. BOOST only if unusually useful to Martin's audience. Output label only.").upper();return x if x in {"NO_ACTION","FAVOURITE","REPLY","BOOST"} else "NO_ACTION"
def reply(text):
 x=ask(f"Mastodon post:\n{text}\nWrite a concise Mastodon reply adding genuinely new substance. Do not flatter or paraphrase. No forced question. Output reply only or NO_REPLY.");return None if x.upper().startswith("NO_REPLY") else x
def main():
 m=Mastodon();me=m.me();print("Authenticated Mastodon account:",me.get("acct"));seen=set();actions=0
 items=m.notifications(30)+m.home(40)
 for item in items:
  s=item.get("status",item);sid=str(s.get("id",''));acct=str(s.get("account",{}).get("acct",''));text=clean(s.get("content"))
  if not sid or sid in seen or str(s.get("account",{}).get("id"))==str(me.get("id")):continue
  seen.add(sid);choice=decide(text);print(choice,sid,acct)
  if choice=="NO_ACTION":continue
  if actions>=MAX:break
  if choice=="REPLY":
   body=reply(text)
   if not body:continue
   if not DRY:m.post(body,reply_to=sid)
  elif choice=="FAVOURITE" and not DRY:m.favourite(sid)
  elif choice=="BOOST" and not DRY:m.boost(sid)
  actions+=1
 print(f"SUMMARY actions={actions} dry_run={DRY}")
if __name__=="__main__":main()
