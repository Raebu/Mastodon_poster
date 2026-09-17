from __future__ import annotations
from collections import Counter
def outcome_weight(action):return {'REPLY':3,'FOLLOW':2,'BOOST':1.5,'FAVOURITE':1,'NO_ACTION':0}.get(action,0)
def topic_weights(rows):
 score=Counter();count=Counter()
 for r in rows:
  t=str(r.get('Topic',''));a=str(r.get('Action',''));score[t]+=outcome_weight(a);count[t]+=1
 return {t:score[t]/max(1,count[t]) for t in count}
def network_health(rows):
 active=[r for r in rows if str(r.get('Action',''))!='NO_ACTION'];accounts=Counter(str(r.get('Account','')).lower() for r in active);topics=Counter(str(r.get('Topic','')) for r in active)
 n=max(1,len(active));return {'actions':len(active),'unique_accounts':len(accounts),'unique_topics':len(topics),'max_account_share':max(accounts.values(),default=0)/n,'max_topic_share':max(topics.values(),default=0)/n}
