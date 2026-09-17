from __future__ import annotations
import os,json,time,datetime
from collections import Counter
try:
 import gspread
 from google.oauth2.service_account import Credentials
except ImportError:gspread=None
SHEET=os.getenv('SOCIAL_MEMORY_SHEET_ID','1yIwJqlmgRbp1_o4MFCLHMSOOgaE3DYMd31eF43dF9bs')
TABS={
'Mastodon Interactions':['At','Account','Status ID','Action','Reason','Dry Run','Topic','Fingerprint'],
'Mastodon Relationships':['Account','Interactions','Last Interaction','Stage','Last Action'],
'Mastodon Conversations':['At','Account','Status ID','Direction','Text','Closed'],
'Mastodon Agent Runs':['At','Mode','Actions','Dry Run','Notes'],
'Social Decision Replay':['At','Platform','Status ID','Account','Topic','Decision','Reason','Confidence','Dry Run','Policy Version','Schema Version'],
'Social Research Queue':['At','Platform','Status ID','Claim','Reason','Status'],
'Social Health':['At','Platform','Component','Status','Detail'],
'Social Content Lineage':['At','Platform','Content ID','Fingerprint','Topic','Parent'],
'Social Opportunities':['At','Platform','Account','Signal','Evidence Count','Stage'],
'Social Controls':['Control','Value'],
'Social Human Corrections':['At','Scope','Instruction','Active'],
'Social Negative Learning':['At','Pattern','Reason','Active'],
'Social Events':['At','Entity','Event','Old','New','Evidence','Confidence']}
DEFAULT_CONTROLS={'Publishing Enabled':'FALSE','Growth Enabled':'FALSE','Replies Enabled':'FALSE','Reactions Enabled':'FALSE','Boosts Enabled':'FALSE','Follow Enabled':'FALSE','Research Enabled':'FALSE'}
_BOOK=None;_WS={};_READY=False;_ROWS=None
def now():return time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())
def _book():
 global _BOOK
 if _BOOK is not None:return _BOOK
 raw=os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON','')
 if not raw or not gspread:return None
 creds=Credentials.from_service_account_info(json.loads(raw),scopes=['https://www.googleapis.com/auth/spreadsheets']);_BOOK=gspread.authorize(creds).open_by_key(SHEET);return _BOOK
def ensure():
 global _READY,_WS
 if _READY:return _book()
 b=_book()
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
 cw=_WS['Social Controls'];rows=cw.get_all_records();known={str(r.get('Control')) for r in rows}
 for k,v in DEFAULT_CONTROLS.items():
  if k not in known:cw.append_row([k,v],value_input_option='RAW')
 _READY=True;return b
def _ws(tab):ensure();return _WS.get(tab)
def append(tab,row):
 try:
  w=_ws(tab)
  if w:w.append_row(row,value_input_option='RAW')
 except Exception as e:print('MEMORY_WARNING',type(e).__name__,str(e)[:120])
def control(name,default=False):
 try:
  rows=_ws('Social Controls').get_all_records();m={str(r.get('Control')):str(r.get('Value','')).upper() for r in rows};return m.get(name,'TRUE' if default else 'FALSE') in {'TRUE','1','YES','ON'}
 except Exception:return default
def interactions():
 global _ROWS
 if _ROWS is None:
  try:_ROWS=_ws('Mastodon Interactions').get_all_records()
  except Exception:_ROWS=[]
 return _ROWS
def _age_days(s):
 try:return (datetime.datetime.now(datetime.timezone.utc)-datetime.datetime.fromisoformat(str(s).replace('Z','+00:00'))).total_seconds()/86400
 except Exception:return 9999
def fatigue(acct):
 rows=[r for r in interactions() if str(r.get('Account','')).lower()==acct.lower() and str(r.get('Action',''))!='NO_ACTION'];ages=[_age_days(r.get('At')) for r in rows]
 n7=sum(x<=7 for x in ages);n30=sum(x<=30 for x in ages);n90=sum(x<=90 for x in ages);return max(n7/3,n30/7,n90/14),f'7d={n7};30d={n30};90d={n90}'
def allow_account(acct,run_counts):
 if run_counts[acct.lower()]>=1:return False,'run concentration'
 p,detail=fatigue(acct)
 if p>=1:return False,'contact fatigue '+detail
 return True,detail
def relationship_stage(acct):
 n=sum(1 for r in interactions() if str(r.get('Account','')).lower()==acct.lower() and str(r.get('Action',''))!='NO_ACTION')
 return 'STRONG' if n>=10 else 'RECURRING' if n>=6 else 'ENGAGED' if n>=3 else 'FAMILIAR' if n>=1 else 'DISCOVERED'
def log_interaction(acct,sid,action,reason,dry,topic='',fingerprint=''):
 global _ROWS
 row=[now(),acct,sid,action,reason,str(dry),topic,fingerprint];append('Mastodon Interactions',row)
 if _ROWS is not None:_ROWS.append(dict(zip(TABS['Mastodon Interactions'],row)))
 append('Mastodon Relationships',[acct,sum(1 for r in interactions() if str(r.get('Account','')).lower()==acct.lower()),now(),relationship_stage(acct),action])
def replay(sid,acct,topic,decision,reason,dry,confidence=''):
 append('Social Decision Replay',[now(),'Mastodon',sid,acct,topic,decision,reason,confidence,str(dry),'1.0','2.1'])
def research_hold(sid,claim,reason):append('Social Research Queue',[now(),'Mastodon',sid,claim,reason,'PENDING'])
def lineage(cid,fp,topic,parent=''):append('Social Content Lineage',[now(),'Mastodon',cid,fp,topic,parent])
def recent_fingerprints(limit=300):
 try:return {str(r.get('Fingerprint','')) for r in _ws('Social Content Lineage').get_all_records()[-limit:] if r.get('Fingerprint')}
 except Exception:return set()
def corrections():
 try:return [r for r in _ws('Social Human Corrections').get_all_records() if str(r.get('Active','')).upper() not in {'FALSE','0','NO'}]
 except Exception:return []
def conversation_closed(acct):
 try:
  rows=[r for r in _ws('Mastodon Conversations').get_all_records() if str(r.get('Account','')).lower()==acct.lower()];return bool(rows and str(rows[-1].get('Closed','')).upper() in {'TRUE','1','YES'})
 except Exception:return False
def log_run(mode,actions,dry,notes=''):append('Mastodon Agent Runs',[now(),mode,actions,str(dry),notes]);append('Social Health',[now(),'Mastodon',mode,'OK',notes])
