#!/usr/bin/env python
"""
Suite of unit-tests for testing Michel
"""
import unittest
import michel.michel as m

class TestMichel(unittest.TestCase):
    def setUp(self):
        pass
    
    def test_text_to_tasktree(self):
        org_text = """\
* Headline 1
Body 1a
Body 1b
* DONE Headline 2
** Headline 2.1"""
        
        tasktree = m.parse_text(org_text)
        self.assertEqual(org_text, str(tasktree))
    
    def test_tree_to_text(self):
        pass


if __name__ == '__main__':
    unittest.main()
