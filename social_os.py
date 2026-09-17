from __future__ import annotations
import os,json,time
from collections import Counter
try:
 import gspread
 from google.oauth2.service_account import Credentials
except ImportError:gspread=None
SHEET=os.getenv('SOCIAL_MEMORY_SHEET_ID','1yIwJqlmgRbp1_o4MFCLHMSOOgaE3DYMd31eF43dF9bs')
TABS={'Mastodon Interactions':['At','Account','Status ID','Action','Reason','Dry Run'],'Mastodon Relationships':['Account','Interactions','Last Interaction','Stage'],'Mastodon Agent Runs':['At','Mode','Actions','Dry Run','Notes'],'Social Events':['At','Entity','Event','Old','New','Evidence','Confidence']}
_BOOK=None;_WS={};_READY=False;_RECENT=None
def now():return time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())
def _book():
 global _BOOK
 if _BOOK is not None:return _BOOK
 raw=os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON','')
 if not raw or not gspread:return None
 creds=Credentials.from_service_account_info(json.loads(raw),scopes=['https://www.googleapis.com/auth/spreadsheets'])
 _BOOK=gspread.authorize(creds).open_by_key(SHEET);return _BOOK
def ensure():
 global _READY,_WS
 if _READY:return _book()
 b=_book()
 if not b:return None
 existing={w.title:w for w in b.worksheets()}
 for title,heads in TABS.items():
  w=existing.get(title)
  if w is None:
   w=b.add_worksheet(title=title,rows=1000,cols=max(8,len(heads)));w.append_row(heads,value_input_option='RAW')
  else:
   # Preserve existing shared data. Only extend a header when columns are missing.
   current=w.row_values(1)
   if not current:w.append_row(heads,value_input_option='RAW')
   elif all(h in current for h in heads):pass
   else:
    merged=current+[h for h in heads if h not in current]
    w.update(range_name='A1',values=[merged])
  _WS[title]=w
 _READY=True;return b
def _ws(tab):
 ensure();return _WS.get(tab)
def append(tab,row):
 try:
  w=_ws(tab)
  if w:w.append_row(row,value_input_option='RAW')
 except Exception as e:print('MEMORY_WARNING',type(e).__name__,str(e)[:120])
def recent_accounts(limit=100):
 global _RECENT
 if _RECENT is not None:return _RECENT[-limit:]
 try:
  w=_ws('Mastodon Interactions')
  if not w:return []
  rows=w.get_all_records()
  _RECENT=[str(r.get('Account','')).lower() for r in rows if r.get('Account')]
  return _RECENT[-limit:]
 except Exception as e:
  print('MEMORY_READ_WARNING',type(e).__name__,str(e)[:120]);_RECENT=[];return []
def concentration_penalty(acct):
 recent=recent_accounts(60)
 if not recent:return 0.0
 return min(1.0,Counter(recent)[acct.lower()]/max(1,len(recent))*4)
def contact_fatigue(acct):
 recent=recent_accounts(100);n=sum(x==acct.lower() for x in recent)
 return min(1.0,n/6)
def allow_account(acct,run_counts):
 if run_counts[acct.lower()]>=2:return False,'run concentration'
 p=max(concentration_penalty(acct),contact_fatigue(acct))
 if p>=0.67:return False,'contact fatigue'
 return True,''
def log_interaction(acct,sid,action,reason,dry):
 global _RECENT
 append('Mastodon Interactions',[now(),acct,sid,action,reason,str(dry)])
 if _RECENT is not None:_RECENT.append(acct.lower())
def log_run(mode,actions,dry,notes=''):append('Mastodon Agent Runs',[now(),mode,actions,str(dry),notes])
