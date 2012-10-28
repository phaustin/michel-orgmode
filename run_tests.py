#!/usr/bin/env python
"""
Suite of unit-tests for testing Michel
"""
import unittest
import textwrap
import michel.michel as m

class TestMichel(unittest.TestCase):
    def setUp(self):
        pass
    
    def test_text_to_tasktree(self):
        # text should have trailing "\n" character, like most textfiles
        org_text = textwrap.dedent("""\
            * Headline 1
            Body 1a
                Body 1b
            * DONE    Headline 2
            ** Headline 2.1
            """)

        tasktree = m.parse_text(org_text)
        self.assertEqual(str(tasktree), org_text)

    def test_initial_non_headline_text(self):
        """
        Test the case where the first lines of an org-mode file are not
        org-mode headlines.
        
        """
        # text should have trailing "\n" character, like most textfiles
        org_text = textwrap.dedent("""\

            Some non-headline text...
            Another line of it.
            * Headline 1
            Body 1a
                Body 1b
            * DONE    Headline 2
            ** Headline 2.1
            """)

        tasktree = m.parse_text(org_text)
        # a dummy headline will be added to contain the initial text
        self.assertEqual(str(tasktree), "* \n" + org_text)

if __name__ == '__main__':
    unittest.main()
