from __future__ import annotations
import os,json,time,datetime
try:
 import gspread
 from google.oauth2.service_account import Credentials
except ImportError:gspread=None
SHEET=os.getenv('SOCIAL_MEMORY_SHEET_ID','1yIwJqlmgRbp1_o4MFCLHMSOOgaE3DYMd31eF43dF9bs')
TABS={'Mastodon Interactions':['At','Account','Status ID','Action','Reason','Dry Run','Topic','Fingerprint'],'Mastodon Relationships':['Account','Interactions','Last Interaction','Stage','Last Action'],'Mastodon Conversations':['At','Account','Status ID','Direction','Text','Closed'],'Mastodon Agent Runs':['At','Mode','Actions','Dry Run','Notes'],'Social Decision Replay':['At','Platform','Status ID','Account','Topic','Decision','Reason','Confidence','Dry Run','Policy Version','Schema Version'],'Social Research Queue':['At','Platform','Status ID','Claim','Reason','Status'],'Social Health':['At','Platform','Component','Status','Detail'],'Social Content Lineage':['At','Platform','Content ID','Fingerprint','Topic','Parent','Text'],'Social Opportunities':['At','Platform','Account','Signal','Evidence Count','Stage'],'Social Controls':['Control','Value'],'Social Human Corrections':['At','Scope','Instruction','Active'],'Social Negative Learning':['At','Pattern','Reason','Active'],'Social Events':['At','Entity','Event','Old','New','Evidence','Confidence'],'Social Entity Graph':['At','Entity ID','Platform','Handle','Type','Relation','Evidence'],'Social Knowledge':['Claim','Status','Source','Verified At','Expires At','Confidence'],'Social Outcomes':['At','Platform','Account','Content ID','Outcome','Value'],'Social Usage':['At','Platform','Model Calls','Actions','Pool'],'Social Backups':['At','Platform','Kind','Reference']}
DEFAULT_CONTROLS={'Publishing Enabled':'FALSE','Growth Enabled':'FALSE','Replies Enabled':'FALSE','Reactions Enabled':'FALSE','Boosts Enabled':'FALSE','Follow Enabled':'FALSE','Research Enabled':'FALSE'}
_BOOK=None;_WS={};_READY=False;_ROWS=None
def now():return time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())
def _book():
 global _BOOK
 if _BOOK is not None:return _BOOK
 raw=os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON','');
 if not raw or not gspread:return None
 creds=Credentials.from_service_account_info(json.loads(raw),scopes=['https://www.googleapis.com/auth/spreadsheets']);_BOOK=gspread.authorize(creds).open_by_key(SHEET);return _BOOK
def ensure():
 global _READY,_WS
 if _READY:return _book()
 b=_book();
 if not b:return None
 existing={w.title:w for w in b.worksheets()}
 for title,heads in TABS.items():
  w=existing.get(title)
  if w is None:w=b.add_worksheet(title=title,rows=1500,cols=max(12,len(heads)));w.append_row(heads,value_input_option='RAW')
  else:
   cur=w.row_values(1)
   if not cur:w.append_row(heads,value_input_option='RAW')
   elif not all(h in cur for h in heads):w.update(range_name='A1',values=[cur+[h for h in heads if h not in cur]])
  _WS[title]=w
 rows=_WS['Social Controls'].get_all_records();known={str(r.get('Control')) for r in rows}
 for k,v in DEFAULT_CONTROLS.items():
  if k not in known:_WS['Social Controls'].append_row([k,v],value_input_option='RAW')
 _READY=True;return b
def _ws(t):ensure();return _WS.get(t)
def append(t,row):
 try:
  w=_ws(t)
  if w:w.append_row(row,value_input_option='RAW')
 except Exception as e:print('MEMORY_WARNING',type(e).__name__,str(e)[:120])
def control(n,default=False):
 try:m={str(r.get('Control')):str(r.get('Value','')).upper() for r in _ws('Social Controls').get_all_records()};return m.get(n,'TRUE' if default else 'FALSE') in {'TRUE','1','YES','ON'}
 except Exception:return default
def interactions():
 global _ROWS
 if _ROWS is None:
  try:_ROWS=_ws('Mastodon Interactions').get_all_records()
  except Exception:_ROWS=[]
 return _ROWS
def _age(s):
 try:return (datetime.datetime.now(datetime.timezone.utc)-datetime.datetime.fromisoformat(str(s).replace('Z','+00:00'))).total_seconds()/86400
 except Exception:return 9999
def fatigue(a):
 ages=[_age(r.get('At')) for r in interactions() if str(r.get('Account','')).lower()==a.lower() and str(r.get('Action',''))!='NO_ACTION'];n7=sum(x<=7 for x in ages);n30=sum(x<=30 for x in ages);n90=sum(x<=90 for x in ages);return max(n7/3,n30/7,n90/14),f'7d={n7};30d={n30};90d={n90}'
def allow_account(a,counts):
 if counts[a.lower()]>=1:return False,'run concentration'
 p,d=fatigue(a);return (False,'contact fatigue '+d) if p>=1 else (True,d)
def relationship_stage(a):
 rows=[r for r in interactions() if str(r.get('Account','')).lower()==a.lower() and str(r.get('Action',''))!='NO_ACTION'];n=len(rows);reciprocal=any(str(r.get('Reason','')).lower().find('reciprocal')>=0 for r in rows)
 return 'STRONG' if n>=10 and reciprocal else 'RECURRING' if n>=6 else 'RECIPROCAL' if reciprocal else 'ENGAGED' if n>=3 else 'FAMILIAR' if n else 'DISCOVERED'
def log_interaction(a,sid,action,reason,dry,topic='',fp=''):
 global _ROWS
 row=[now(),a,sid,action,reason,str(dry),topic,fp];append('Mastodon Interactions',row)
 if _ROWS is not None:_ROWS.append(dict(zip(TABS['Mastodon Interactions'],row)))
 append('Mastodon Relationships',[a,sum(1 for r in interactions() if str(r.get('Account','')).lower()==a.lower()),now(),relationship_stage(a),action]);append('Social Entity Graph',[now(),a.lower(),'Mastodon',a,'person/account',action,reason])
def replay(sid,a,t,d,r,dry,confidence=''):append('Social Decision Replay',[now(),'Mastodon',sid,a,t,d,r,confidence,str(dry),'1.1','2.2'])
def research_hold(sid,claim,reason):append('Social Research Queue',[now(),'Mastodon',sid,claim,reason,'PENDING'])
def lineage(cid,fp,t,parent='',text=''):append('Social Content Lineage',[now(),'Mastodon',cid,fp,t,parent,text])
def recent_fingerprints(limit=300):
 try:return {str(r.get('Fingerprint','')) for r in _ws('Social Content Lineage').get_all_records()[-limit:] if r.get('Fingerprint')}
 except Exception:return set()
def recent_texts(limit=300):
 try:return [str(r.get('Text','')) for r in _ws('Social Content Lineage').get_all_records()[-limit:] if r.get('Text')]
 except Exception:return []
def corrections():
 try:return [r for r in _ws('Social Human Corrections').get_all_records() if str(r.get('Active','')).upper() not in {'FALSE','0','NO'}]
 except Exception:return []
def conversation_closed(a):
 try:
  r=[x for x in _ws('Mastodon Conversations').get_all_records() if str(x.get('Account','')).lower()==a.lower()];return bool(r and str(r[-1].get('Closed','')).upper() in {'TRUE','1','YES'})
 except Exception:return False
def opportunity(a,signal):
 rows=[r for r in _ws('Social Opportunities').get_all_records() if str(r.get('Account','')).lower()==a.lower()];n=len(rows)+1;stage='QUALIFIED' if n>=2 else 'OBSERVED';append('Social Opportunities',[now(),'Mastodon',a,signal,n,stage]);return stage
def usage(calls,actions,pool):append('Social Usage',[now(),'Mastodon',calls,actions,pool])
def log_run(mode,actions,dry,notes=''):append('Mastodon Agent Runs',[now(),mode,actions,str(dry),notes]);append('Social Health',[now(),'Mastodon',mode,'OK',notes])
