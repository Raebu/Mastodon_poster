from __future__ import annotations
import os,random
from openai import OpenAI
from mastodon_api import Mastodon
from voice import MARTIN_VOICE
import social_os,policy,strategy,semantic,resilience
MODEL=os.getenv('OPENAI_MODEL','gpt-5-mini');DRY=os.getenv('DRY_RUN','true').lower()=='true'
def main():
 topics=strategy.PORTFOLIO[:];random.shuffle(topics);chosen=topics[0];extra='\n'.join(str(x.get('Instruction','')) for x in social_os.corrections()[-20:])
 prompt=f"Write one original Mastodon post for Martin. Area: {chosen}. One specific worthwhile observation. Demonstrate executive judgement. Connect technology, strategy, capital, people, economics or execution where useful. For M&A use {strategy.ma_lens()} without claiming personal deal history. No unverified current-event claims, sales pitch, engagement bait or generic wisdom. Output post or NO_POST.\nHuman corrections: {extra}"
 if not resilience.budget_call():print('HOLD model budget');return
 text=OpenAI(api_key=os.environ['OPENAI_API_KEY']).responses.create(model=MODEL,input=MARTIN_VOICE+'\nTASK\n'+prompt).output_text.strip()
 if text.upper().startswith('NO_POST'):print('NO_POST');return
 ok,reason=policy.gate_generated(text);fp=strategy.fingerprint(text)
 if fp in social_os.recent_fingerprints() or semantic.duplicate(text,social_os.recent_texts()):ok=False;reason='semantic duplicate'
 if not ok:print('HOLD',reason);social_os.research_hold('',text[:500],reason) if reason=='research_required' else None;return
 if not DRY and not social_os.control('Publishing Enabled'):print('HOLD Publishing Enabled is FALSE');return
 print('CANDIDATE',text)
 if not DRY:
  r=resilience.retry(Mastodon().post,text);cid=str(r.get('id',''));social_os.lineage(cid,fp,chosen,'',text);social_os.log_run('post',1,False,'published '+chosen);print('PUBLISHED',r.get('url') or r.get('uri') or cid)
 else:social_os.replay('','',chosen,'POST_CANDIDATE','passed policy and semantic duplicate gates',True)
 social_os.usage(resilience.usage(),0 if DRY else 1,1)
if __name__=='__main__':main()
