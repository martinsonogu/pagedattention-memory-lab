import unittest
from experiment import fixed_allocation, paged_allocation, admit, run

class AllocationTests(unittest.TestCase):
    def test_exact_blocks(self):
        self.assertEqual(paged_allocation(16,16),16)
        self.assertEqual(paged_allocation(17,16),32)
        self.assertEqual(paged_allocation(0,16),0)
    def test_fixed_reservation(self):
        self.assertEqual(fixed_allocation(5,2048),2048)
    def test_invalid(self):
        with self.assertRaises(ValueError): paged_allocation(4,0)
        with self.assertRaises(ValueError): fixed_allocation(2049,2048)
    def test_budget(self):
        for strategy in ('fixed','paged'):
            result=admit([5,8,17,31,40],64,strategy,32,8) if strategy=='paged' else admit([5,8,17,31],64,strategy,32,8)
            self.assertLessEqual(result['allocated_slots'],64)
            self.assertLessEqual(result['used_slots'],result['allocated_slots'])
    def test_determinism(self):
        self.assertEqual(run(trials=3),run(trials=3))
    def test_paging_no_more_than_block_minus_one_per_admitted_request(self):
        lengths=[1,16,17,31,50]
        r=admit(lengths,256,'paged',64,16)
        self.assertLessEqual(r['unused_slots'],r['admitted']*15)
if __name__=='__main__': unittest.main()
