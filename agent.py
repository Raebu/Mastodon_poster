from __future__ import annotations
import os,re
from collections import Counter
from html import unescape
from openai import OpenAI
from mastodon_api import Mastodon
from voice import MARTIN_VOICE
import social_os,policy,strategy
DRY=os.getenv('DRY_RUN','true').lower()=='true';MODEL=os.getenv('OPENAI_MODEL','gpt-5-mini');MAX=int(os.getenv('MASTODON_MAX_ACTIONS','5'));MAX_FOLLOWS=int(os.getenv('MASTODON_MAX_FOLLOWS','2'))
TOPICS=['AI','M&A','software','corporate strategy','automation','private equity','enterprise technology','corporate development','investment','operating model','technology leadership','venture capital','digital transformation','digital assets','blockchain','technology governance']
def clean(h):return re.sub(r'\s+',' ',re.sub(r'<[^>]+>',' ',unescape(h or ''))).strip()
def ask(p):
 corrections=social_os.corrections();extra='\nHUMAN CORRECTIONS:\n'+'\n'.join(str(x.get('Instruction','')) for x in corrections[-20:]) if corrections else ''
 return OpenAI(api_key=os.environ['OPENAI_API_KEY']).responses.create(model=MODEL,input=MARTIN_VOICE+extra+'\nTASK\n'+p).output_text.strip()
def observe(m,me):
 raw=[]
 for x in m.notifications(30)+m.home(40):raw.append((x.get('status',x),'feed'))
 for q in TOPICS:
  tag=re.sub(r'[^A-Za-z0-9_]','',q.replace('&','and').replace(' ',''))
  try:
   for s in m.tag(tag,5):raw.append((s,'tag:'+q))
  except Exception as e:print('DISCOVERY_WARNING',q,type(e).__name__)
  try:
   for s in m.search(q,5,'statuses').get('statuses',[]):raw.append((s,'search:'+q))
  except Exception:pass
 out=[];seen=set();known=social_os.recent_fingerprints()
 for s,source in raw:
  sid=str(s.get('id',''));a=s.get('account',{});aid=str(a.get('id',''));acct=str(a.get('acct',''));text=clean(s.get('content'));fp=strategy.fingerprint(text)
  if not sid or sid in seen or aid==str(me.get('id')) or not text or fp in known:continue
  seen.add(sid);t=strategy.topic(text,source);pen=social_os.fatigue(acct)[0];out.append({'s':s,'sid':sid,'account':a,'aid':aid,'acct':acct,'text':text,'source':source,'topic':t,'fp':fp,'score':strategy.score({'text':text,'topic':t},Counter(),pen)})
 return sorted(out,key=lambda x:x['score'],reverse=True)
def decision(c):
 if policy.political(c['text']):return 'NO_ACTION','political restraint'
 if policy.current_claim(c['text']):return 'HOLD','current claim requires verified research'
 p=f"Post: {c['text']}\nTopic: {c['topic']}\nSource: {c['source']}\nChoose NO_ACTION, FAVOURITE, REPLY or BOOST. Prefer NO_ACTION. Reward genuinely new executive/operator value, not agreement. For M&A use only the most relevant lens from: {strategy.ma_lens()}. Never imply personal deal experience. Output label then a short reason."
 x=ask(p);label=x.split()[0].strip(':').upper();return (label if label in {'NO_ACTION','FAVOURITE','REPLY','BOOST'} else 'NO_ACTION'),x[:220]
def make_reply(c):
 x=ask(f"Reply to this post with one concise, original contribution:\n{c['text']}\nTopic: {c['topic']}. Add mechanism, trade-off or second-order effect. Never invent personal experience or current facts. No generic praise, sales pitch or forced question. Output reply or NO_REPLY.")
 if x.upper().startswith('NO_REPLY'):return None
 ok,reason=policy.gate_generated(x);return x if ok else None
def follow_worthy(c):
 bio=clean(c['account'].get('note',''));x=ask(f"Account {c['acct']}\nBio: {bio}\nPost: {c['text']}\nIs there enough evidence of durable professional value to follow? Seek CEOs/founders, operators, M&A/corp-dev, investors, strategists, technology leaders and strong independent experts. One good post or prestigious title is insufficient. Output FOLLOW or NO_FOLLOW plus reason.");return x.upper().startswith('FOLLOW'),x[:220]
def main():
 m=Mastodon();me=m.me();print('Authenticated Mastodon account:',me.get('acct'));pool=observe(m,me);print('POOL',len(pool));actions=follows=0;run_counts=Counter();topic_counts=Counter()
 growth_enabled=DRY or social_os.control('Growth Enabled');replies_enabled=DRY or social_os.control('Replies Enabled');reactions_enabled=DRY or social_os.control('Reactions Enabled');boosts_enabled=DRY or social_os.control('Boosts Enabled');follow_enabled=DRY or social_os.control('Follow Enabled')
 for c in pool:
  if actions>=MAX and follows>=MAX_FOLLOWS:break
  allowed,why=social_os.allow_account(c['acct'],run_counts)
  if not allowed:social_os.replay(c['sid'],c['acct'],c['topic'],'NO_ACTION',why,DRY);continue
  if topic_counts[c['topic']]>=2:social_os.replay(c['sid'],c['acct'],c['topic'],'NO_ACTION','topic concentration',DRY);continue
  choice,reason=decision(c);print(choice,c['sid'],c['acct'],c['topic'],c['source'])
  if choice=='HOLD':social_os.research_hold(c['sid'],c['text'][:500],reason);social_os.replay(c['sid'],c['acct'],c['topic'],'HOLD',reason,DRY);continue
  social_os.replay(c['sid'],c['acct'],c['topic'],choice,reason,DRY)
  acted=False
  if growth_enabled and actions<MAX:
   if choice=='REPLY' and replies_enabled and not social_os.conversation_closed(c['acct']):
    body=make_reply(c)
    if body:
     if not DRY:m.post(body,reply_to=c['sid'])
     acted=True
   elif choice=='FAVOURITE' and reactions_enabled:
    if not DRY:m.favourite(c['sid']);acted=True
    if DRY:acted=True
   elif choice=='BOOST' and boosts_enabled:
    if not DRY:m.boost(c['sid']);acted=True
    if DRY:acted=True
  if acted:
   actions+=1;run_counts[c['acct'].lower()]+=1;topic_counts[c['topic']]+=1;social_os.log_interaction(c['acct'],c['sid'],choice,reason,DRY,c['topic'],c['fp']);social_os.lineage(c['sid'],c['fp'],c['topic'])
  if c['source']!='feed' and follows<MAX_FOLLOWS and follow_enabled and run_counts[c['acct'].lower()]==0:
   worthy,freason=follow_worthy(c)
   if worthy:
    try:rel=m.relationships([c['aid']]);already=bool(rel and (rel[0].get('following') or rel[0].get('requested')))
    except Exception:already=False
    if not already:
     print('FOLLOW',c['acct'],c['topic'],freason)
     if not DRY:m.follow(c['aid'])
     follows+=1;run_counts[c['acct'].lower()]+=1;topic_counts[c['topic']]+=1;social_os.log_interaction(c['acct'],c['sid'],'FOLLOW',freason,DRY,c['topic'],c['fp']);social_os.replay(c['sid'],c['acct'],c['topic'],'FOLLOW',freason,DRY)
 social_os.log_run('growth',actions+follows,DRY,f'pool={len(pool)}; engagement={actions}; follows={follows}; accounts={len(run_counts)}; topics={len(topic_counts)}')
 print(f'SUMMARY pool={len(pool)} engagement={actions} follows={follows} unique_accounts={len(run_counts)} topics={len(topic_counts)} dry_run={DRY}')
if __name__=='__main__':main()
