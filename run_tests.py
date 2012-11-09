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

    def test_add_subtrees(self):
        org_text1 = textwrap.dedent("""\
            * Headline A1
            * Headline A2
            ** Headline A2.1
            """)
        org_text2 = textwrap.dedent("""\
            * Headline B1
            ** Headline B1.1
            * Headline B2
            """)
        tree1 = m.parse_text(org_text1)
        tree2 = m.parse_text(org_text2)
        
        # test tree concatenation
        target_tree = m.concatenate_trees(tree1, tree2)
        target_text = textwrap.dedent("""\
            * Headline A1
            * Headline A2
            ** Headline A2.1
            * Headline B1
            ** Headline B1.1
            * Headline B2
            """)
        self.assertEqual(str(target_tree), target_text)
        
        # test subtree grafting
        # add tree2's children to first child of tree1
        tree1[0].add_subtree(tree2)
        target_tree = tree1
        target_text = textwrap.dedent("""\
            * Headline A1
            ** Headline B1
            *** Headline B1.1
            ** Headline B2
            * Headline A2
            ** Headline A2.1
            """)
        self.assertEqual(str(target_tree), target_text)
        
    def test_merge(self):
        org_text0 = textwrap.dedent("""\
            * Headline A1
            * Headline A2
            ** Headline A2.1
            * Headline B1
            ** Headline B1.1
            * Headline B2
            """)
        org_text1 = textwrap.dedent("""\
            * Headline A1
            * Headline B1
            ** Headline B1.1
            * Headline A2
            ** Headline A2.1
            * Headline B2
            """)
        org_text2 = textwrap.dedent("""\
            * Headline A1
            * Headline A2
            ** Headline A2.1
            * Headline B1
            ** Headline B1.1
            * Headline B2 modified
            New B2 body text.
            """)
        tree0 = m.parse_text(org_text0) # original tree
        tree1 = m.parse_text(org_text1) # modified tree 1
        tree2 = m.parse_text(org_text2) # modified tree 2
        
        merged_tree, had_conflict = m.treemerge(tree1, tree0, tree2)
        self.assertTrue(had_conflict)
        self.assertTrue(str(merged_tree).find("<<<<<<< MINE"))

if __name__ == '__main__':
    unittest.main()
