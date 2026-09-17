import unittest
from collections import Counter
import policy,strategy
class Tests(unittest.TestCase):
 def test_current_claim_holds(self):self.assertTrue(policy.current_claim('Company X acquired Company Y today'))
 def test_sales_blocked(self):self.assertFalse(policy.gate_generated('Interesting. DM me and we can help.')[0])
 def test_fake_deal_blocked(self):self.assertFalse(policy.gate_generated('I led the acquisition and learned a lot.')[0])
 def test_ma_topic(self):self.assertEqual(strategy.topic('Integration destroys many acquisition synergies'),'ma_corpdev')
 def test_executive_score(self):
  a={'text':'Acquisition diligence and integration assumptions matter.','topic':'ma_corpdev'};b={'text':'A nice software tool.','topic':'technology_ai'}
  self.assertGreater(strategy.score(a,Counter()),strategy.score(b,Counter()))
 def test_fingerprint_stable(self):self.assertEqual(strategy.fingerprint('Hello, world!'),strategy.fingerprint('hello world'))
if __name__=='__main__':unittest.main()
