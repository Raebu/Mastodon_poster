from __future__ import annotations
import os,json,time
from collections import Counter
try:
 import gspread
 from google.oauth2.service_account import Credentials
except ImportError:gspread=None
SHEET=os.getenv('SOCIAL_MEMORY_SHEET_ID','1yIwJqlmgRbp1_o4MFCLHMSOOgaE3DYMd31eF43dF9bs')
TABS={'Mastodon Interactions':['At','Account','Status ID','Action','Reason','Dry Run'],'Mastodon Relationships':['Account','Interactions','Last Interaction','Stage'],'Mastodon Agent Runs':['At','Mode','Actions','Dry Run','Notes'],'Social Events':['At','Entity','Event','Old','New','Evidence','Confidence']}
def now():return time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())
def _book():
 raw=os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON','')
 if not raw or not gspread:return None
 creds=Credentials.from_service_account_info(json.loads(raw),scopes=['https://www.googleapis.com/auth/spreadsheets'])
 return gspread.authorize(creds).open_by_key(SHEET)
def ensure():
 b=_book()
 if not b:return None
 existing={w.title:w for w in b.worksheets()}
 for title,heads in TABS.items():
  if title not in existing:
   w=b.add_worksheet(title=title,rows=1000,cols=max(8,len(heads)));w.append_row(heads);existing[title]=w
 return b
def append(tab,row):
 try:
  b=ensure()
  if b:b.worksheet(tab).append_row(row,value_input_option='RAW')
 except Exception as e:print('MEMORY_WARNING',type(e).__name__)
def recent_accounts(limit=60):
 try:
  b=ensure()
  if not b:return []
  rows=b.worksheet('Mastodon Interactions').get_all_records()[-limit:]
  return [str(r.get('Account','')).lower() for r in rows if r.get('Account')]
 except Exception:return []
def concentration_penalty(acct):
 recent=recent_accounts();
 if not recent:return 0.0
 return min(1.0,Counter(recent)[acct.lower()]/max(1,len(recent))*4)
def contact_fatigue(acct):
 recent=recent_accounts(100);n=sum(x==acct.lower() for x in recent)
 return min(1.0,n/6)
def allow_account(acct,run_counts):
 # One source may not dominate a run; previous interactions also cool it down.
 if run_counts[acct.lower()]>=2:return False,'run concentration'
 p=max(concentration_penalty(acct),contact_fatigue(acct))
 if p>=0.67:return False,'contact fatigue'
 return True,''
def log_interaction(acct,sid,action,reason,dry):append('Mastodon Interactions',[now(),acct,sid,action,reason,str(dry)])
def log_run(mode,actions,dry,notes=''):append('Mastodon Agent Runs',[now(),mode,actions,str(dry),notes])
