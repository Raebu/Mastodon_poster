from __future__ import annotations
import os,re
from collections import Counter
from html import unescape
from openai import OpenAI
from mastodon_api import Mastodon
from voice import MARTIN_VOICE
import social_os,policy,strategy,semantic,resilience,research
DRY=os.getenv('DRY_RUN','true').lower()=='true';MODEL=os.getenv('OPENAI_MODEL','gpt-5-mini');MAX=int(os.getenv('MASTODON_MAX_ACTIONS','5'));MAX_FOLLOWS=int(os.getenv('MASTODON_MAX_FOLLOWS','2'));MAX_MODEL_CANDIDATES=int(os.getenv('SOCIAL_MAX_MODEL_CANDIDATES','25'))
TOPICS=['AI','M&A','software','corporate strategy','automation','private equity','enterprise technology','corporate development','investment','operating model','technology leadership','venture capital','digital transformation','digital assets','blockchain','technology governance']
OPPORTUNITY=re.compile(r'\b(partner|partnership|speaker|speaking|investment|acquisition|vendor|procurement|rfp|tender|pilot|collaboration)\b',re.I)
def clean(h):return re.sub(r'\s+',' ',re.sub(r'<[^>]+>',' ',unescape(h or ''))).strip()
def ask(p):
 if not resilience.budget_call():return 'NO_ACTION budget exhausted'
 extra='\n'.join(str(x.get('Instruction','')) for x in social_os.corrections()[-20:]);return OpenAI(api_key=os.environ['OPENAI_API_KEY']).responses.create(model=MODEL,input=MARTIN_VOICE+'\nHUMAN CORRECTIONS\n'+extra+'\nTASK\n'+p).output_text.strip()
def observe(m,me):
 raw=[]
 for x in resilience.retry(m.notifications,30)+resilience.retry(m.home,40):raw.append((x.get('status',x),'feed'))
 for q in TOPICS:
  tag=re.sub(r'[^A-Za-z0-9_]','',q.replace('&','and').replace(' ',''))
  try:
   for s in m.tag(tag,5):raw.append((s,'tag:'+q))
   for s in m.search(q,5,'statuses').get('statuses',[]):raw.append((s,'search:'+q))
  except Exception as e:print('DISCOVERY_WARNING',q,type(e).__name__)
 out=[];seen=set();known=social_os.recent_fingerprints();recent_text=social_os.recent_texts()
 for s,source in raw:
  sid=str(s.get('id',''));a=s.get('account',{});aid=str(a.get('id',''));acct=str(a.get('acct',''));text=clean(s.get('content'));fp=strategy.fingerprint(text)
  if not sid or sid in seen or aid==str(me.get('id')) or len(text)<45 or fp in known or semantic.duplicate(text,recent_text):continue
  seen.add(sid);t=strategy.topic(text,source);pen=social_os.fatigue(acct)[0];out.append({'s':s,'sid':sid,'account':a,'aid':aid,'acct':acct,'text':text,'source':source,'topic':t,'fp':fp,'score':strategy.score({'text':text,'topic':t},Counter(),pen)})
 return sorted(out,key=lambda x:x['score'],reverse=True)[:MAX_MODEL_CANDIDATES]
def decision(c):
 if policy.political(c['text']):return 'NO_ACTION','political restraint'
 if policy.current_claim(c['text']):
  ev=research.verify(c['text']) if social_os.control('Research Enabled') else {'verified':False,'reason':'research disabled'}
  if not ev.get('verified'):return 'HOLD','current claim: '+ev.get('reason','unverified')
 p=f"Post: {c['text']}\nTopic: {c['topic']}\nChoose NO_ACTION, FAVOURITE, REPLY or BOOST. Prefer NO_ACTION. Reward new executive/operator value. For M&A use the most relevant lens from {strategy.ma_lens()}. Never imply personal deal experience. Output label then short reason.";x=ask(p);label=x.split()[0].strip(':').upper();return (label if label in {'NO_ACTION','FAVOURITE','REPLY','BOOST'} else 'NO_ACTION'),x[:220]
def make_reply(c):
 x=ask(f"Reply concisely with one original mechanism, trade-off or second-order effect:\n{c['text']}\nNo invented personal experience/current facts, praise, sales pitch or forced question. Output reply or NO_REPLY.")
 if x.upper().startswith('NO_REPLY'):return None
 ok,_=policy.gate_generated(x);return x if ok and not semantic.duplicate(x,social_os.recent_texts()) else None
def follow_worthy(c):
 x=ask(f"Account {c['acct']}\nBio: {clean(c['account'].get('note',''))}\nPost: {c['text']}\nFollow only with evidence of durable professional value. One post/title is insufficient. Output FOLLOW or NO_FOLLOW plus reason.");return x.upper().startswith('FOLLOW'),x[:220]
def main():
 m=Mastodon();me=resilience.retry(m.me);print('Authenticated Mastodon account:',me.get('acct'));pool=observe(m,me);print('POOL',len(pool));actions=follows=0;counts=Counter();topics=Counter();growth=DRY or social_os.control('Growth Enabled')
 for c in pool:
  if actions>=MAX and follows>=MAX_FOLLOWS:break
  allowed,why=social_os.allow_account(c['acct'],counts)
  if not allowed or topics[c['topic']]>=2:social_os.replay(c['sid'],c['acct'],c['topic'],'NO_ACTION',why if not allowed else 'topic concentration',DRY);continue
  choice,reason=decision(c);print(choice,c['sid'],c['acct'],c['topic'],c['source']);social_os.replay(c['sid'],c['acct'],c['topic'],choice,reason,DRY)
  if choice=='HOLD':social_os.research_hold(c['sid'],c['text'][:500],reason);continue
  acted=False
  if growth and actions<MAX:
   if choice=='REPLY' and (DRY or social_os.control('Replies Enabled')) and not social_os.conversation_closed(c['acct']):
    body=make_reply(c)
    if body:
     if not DRY:resilience.retry(m.post,body,reply_to=c['sid'])
     acted=True
   elif choice=='FAVOURITE' and (DRY or social_os.control('Reactions Enabled')):
    if not DRY:resilience.retry(m.favourite,c['sid'])
    acted=True
   elif choice=='BOOST' and (DRY or social_os.control('Boosts Enabled')):
    if not DRY:resilience.retry(m.boost,c['sid'])
    acted=True
  if acted:
   actions+=1;counts[c['acct'].lower()]+=1;topics[c['topic']]+=1;social_os.log_interaction(c['acct'],c['sid'],choice,reason,DRY,c['topic'],c['fp']);social_os.lineage(c['sid'],c['fp'],c['topic'],'',c['text'])
  if OPPORTUNITY.search(c['text']):print('OPPORTUNITY',c['acct'],social_os.opportunity(c['acct'],c['text'][:180]))
  if c['source']!='feed' and follows<MAX_FOLLOWS and (DRY or social_os.control('Follow Enabled')) and counts[c['acct'].lower()]==0:
   worthy,fr=follow_worthy(c)
   if worthy:
    try:r=m.relationships([c['aid']]);already=bool(r and (r[0].get('following') or r[0].get('requested')))
    except Exception:already=False
    if not already:
     if not DRY:resilience.retry(m.follow,c['aid'])
     follows+=1;counts[c['acct'].lower()]+=1;topics[c['topic']]+=1;social_os.log_interaction(c['acct'],c['sid'],'FOLLOW',fr,DRY,c['topic'],c['fp']);social_os.replay(c['sid'],c['acct'],c['topic'],'FOLLOW',fr,DRY)
 social_os.usage(resilience.usage(),actions+follows,len(pool));social_os.log_run('growth',actions+follows,DRY,f'pool={len(pool)}; calls={resilience.usage()}; engagement={actions}; follows={follows}; accounts={len(counts)}; topics={len(topics)}');print(f'SUMMARY pool={len(pool)} calls={resilience.usage()} engagement={actions} follows={follows} unique_accounts={len(counts)} topics={len(topics)} dry_run={DRY}')
if __name__=='__main__':main()
