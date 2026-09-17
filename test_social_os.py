import unittest,tempfile,os
from collections import Counter
import policy,strategy,semantic,resilience,research,learning
class Tests(unittest.TestCase):
 def test_current_claim_holds(self):self.assertTrue(policy.current_claim('Company X acquired Company Y today'))
 def test_sales_blocked(self):self.assertFalse(policy.gate_generated('Interesting. DM me and we can help.')[0])
 def test_fake_deal_blocked(self):self.assertFalse(policy.gate_generated('I led the acquisition and learned a lot.')[0])
 def test_politics_detected(self):self.assertTrue(policy.political('Vote for this candidate in the election'))
 def test_ma_topic(self):self.assertEqual(strategy.topic('Integration destroys many acquisition synergies'),'ma_corpdev')
 def test_executive_score(self):
  a={'text':'Acquisition diligence and integration assumptions matter.','topic':'ma_corpdev'};b={'text':'A nice software tool.','topic':'technology_ai'};self.assertGreater(strategy.score(a,Counter()),strategy.score(b,Counter()))
 def test_fingerprint_stable(self):self.assertEqual(strategy.fingerprint('Hello, world!'),strategy.fingerprint('hello world'))
 def test_semantic_echo(self):self.assertTrue(semantic.duplicate('Integration risk can destroy acquisition value',['Acquisition value can be destroyed by integration risk'],.6))
 def test_semantic_distinct(self):self.assertFalse(semantic.duplicate('Cloud costs need ownership',['Post merger integration destroys synergies'],.72))
 def test_research_fails_closed(self):
  old=os.environ.pop('SOCIAL_RESEARCH_ENDPOINT',None)
  try:self.assertFalse(research.verify('breaking acquisition')['verified'])
  finally:
   if old:os.environ['SOCIAL_RESEARCH_ENDPOINT']=old
 def test_network_health(self):
  h=learning.network_health([{'Action':'REPLY','Account':'a','Topic':'x'},{'Action':'FOLLOW','Account':'b','Topic':'y'}]);self.assertEqual(h['unique_accounts'],2);self.assertEqual(h['unique_topics'],2)
 def test_outbox(self):
  old=resilience.OUTBOX
  with tempfile.TemporaryDirectory() as d:
   resilience.OUTBOX=os.path.join(d,'o.jsonl');resilience.queue('memory',{'x':1});self.assertEqual(len(resilience.pending()),1)
  resilience.OUTBOX=old
if __name__=='__main__':unittest.main()
