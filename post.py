from __future__ import annotations
import os
from openai import OpenAI
from mastodon_api import Mastodon
from voice import MARTIN_VOICE
MODEL=os.getenv("OPENAI_MODEL","gpt-5-mini");DRY=os.getenv("DRY_RUN","true").lower()=="true"
def main():
 prompt="Write one original Mastodon post for Martin. One worthwhile thought about technology, AI, automation, software, systems, enterprise execution, commercial reality or emerging technology. Do not invent current events or facts. Do not make it a sales pitch. Avoid generic wisdom. Prefer one specific observation. Mastodon-native and concise. Output only post text or NO_POST."
 text=OpenAI(api_key=os.environ["OPENAI_API_KEY"]).responses.create(model=MODEL,input=MARTIN_VOICE+"\nTASK\n"+prompt).output_text.strip()
 if text.upper().startswith("NO_POST"):print("NO_POST");return
 print("CANDIDATE",text)
 if not DRY:
  r=Mastodon().post(text);print("PUBLISHED",r.get("url") or r.get("uri") or r.get("id"))
if __name__=="__main__":main()
