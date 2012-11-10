#!/usr/bin/env python
"""
michel-orgmode -- a script to push/pull an org-mode text file to/from a google
                  tasks list.

"""
from __future__ import with_statement
import gflags
import httplib2
from apiclient.discovery import build
from oauth2client.file import Storage
from oauth2client.client import OAuth2WebServerFlow
from oauth2client.tools import run
from xdg.BaseDirectory import save_data_path #, save_config_path 
import argparse
import os.path
import sys
import re
import cStringIO
import diff3

class TasksTree(object):
    """
    Tree for holding tasks

    A TasksTree:
    - is a task (except the root, which just holds the list)
    - has subtasks
    - may have a task_id
    - may have a title
    """

    def __init__(self, title=None, task_id=None, task_notes=None, task_status=None):
        self.title = title
        self.task_id = task_id
        self.subtasks = []
        self.notes = task_notes
        # *status* usually takes on the value 'completed' or 'needsAction'
        self.status = task_status
        
    def __getitem__(self, key):
        return self.subtasks[key]
         
    def __setitem__(self, key, val):
        self.subtasks[key] = val
        
    def __delitem__(self, key):
        del(self.subtasks[key])
    
    def __len__(self):
        return len(self.subtasks)

    def get_task_with_id(self, task_id):
        """Returns the task of given id"""
        if self.task_id == task_id:
            return self
        else:
            # depth first search for id
            for subtask in self.subtasks:
                if subtask.get_task_with_id(task_id) is not None:
                    return subtask.get_task_with_id(task_id)
            # if there are no subtasks to search
            return None

    def add_subtask(self, title, task_id = None, parent_id = None,
            task_notes=None, task_status=None):
        """
        Adds a subtask to the tree
        - with the specified task_id
        - as a child of parent_id
        """
        if parent_id is None:
            self.subtasks.append(
                TasksTree(title, task_id, task_notes, task_status))
        else:
            if self.get_task_with_id(parent_id) is None:
                raise ValueError, "No element with suitable parent id"
            self.get_task_with_id(parent_id).add_subtask(title, task_id, None,
                    task_notes, task_status)
    
    def add_subtree(self, tree_to_add, include_root=False, root_title=None,
            root_notes=None):
        """Add *tree_to_add* as a subtree of this tree.
        
        If *include_root* is False, then the children of *tree_to_add* will be
        added as children of this tree's root node.  Otherwise, the root node
        of *tree_to_add* will be added as a child of this tree's root node.
        
        The *root_title* and *root_notes* arguments are optional, and can be
        used to set the title and notes of *tree_to_add*'s root node when
        *include_root* is True. 
        
        """
        if not include_root:
            self.subtasks.extend(tree_to_add.subtasks)
        else:
            if root_title is not None:
                tree_to_add.title = root_title
            if tree_to_add.title is None:
                tree_to_add.title = ""
                
            if root_notes is not None:
                tree_to_add.notes = root_notes
            
            self.subtasks.append(tree_to_add)
    
    def last(self, level):
        """Return the last task added at a given level of the tree.
        
        Level 0 is the "root" node of the tree, and there is only one node at
        this level, which contains all of the level 1 nodes (tasks/headlines).
        
        A TaskTree object is returned that corresponds to the last task having
        the specified level.  This TaskTree object will have the last task as
        the root node of the tree, and will maintain all of the node's
        descendants.
        
        """
        if level == 0:
            return self
        else:
            res = None
            for subtask in self.subtasks:
                x = subtask.last(level - 1)
                if x is not None:
                    res = x
            if res is not None:
                return res

    def push(self, service, list_id, parent = None, root=True):
        """Pushes the task tree to the given list"""
        # We do not want to push the root node
        if not root:
            args = {'tasklist': list_id,
                    'body': {
                                'title': self.title,
                                'notes': self.notes,
                                'status': self.status
                            }
                   }
            if parent:
                args['parent'] = parent
            res = service.tasks().insert(**args).execute()
            self.task_id = res['id']
        # the API head inserts, so we insert in reverse.
        for subtask in reversed(self.subtasks):
            subtask.push(service, list_id, parent=self.task_id, root=False)

    def _lines(self, level):
        """Returns the sequence of lines of the string representation"""
        res = []
        for subtask in self.subtasks:
            #indentations = '\t' * level
            # add number of asterisks corresponding to depth of task, followed
            # by "DONE" if the task is marked as completed.
            done_string = ""
            if (subtask.status is not None) and (subtask.status == "completed"):
                done_string = " DONE"
            indentations = '*' * (level+1) + done_string + " "
            res.append(indentations + subtask.title)
            if subtask.notes is not None:
                notes = subtask.notes
                # add initial space to lines starting w/'*', so that it isn't treated as a task
                if notes.startswith("*"):
                    notes = " " + notes
                notes = notes.replace("\n*", "\n *")
                res.append(notes)
            subtasks_lines = subtask._lines(level + 1)
            res += subtasks_lines
        return res


    def __str__(self):
        """string representation of the tree.
        
        Only the root-node's children (and their descendents...) are printed,
        not the root-node itself.
        
        """
        # always add a trailing "\n" because text-files normally include a "\n"
        # at the end of the last line of the file.
        return '\n'.join(self._lines(0)) + "\n"


def concatenate_trees(t1, t2):
    """Combine tree *t1*'s children with tree *t2*'s children.
    
    A tree is returned whose children include the children of *t1* and the
    children of *t2*.  The root node of the returned tree is a dummy node
    having no title.
    
    Note: children are treated as references, so modifying *t1* after creating
    the combined tree will also modify the combined tree.
    
    """
    joined_tree = TasksTree()
    joined_tree.add_subtree(t1)
    joined_tree.add_subtree(t2)
    
    return joined_tree

def treemerge(new_tree, old_tree, other_tree):
    old = str(old_tree)
    other = str(other_tree)
    new = str(new_tree)
    merged_text, conflict_occurred = diff3.merge3_text(new, old, other)
    
    merged_tree = parse_text(merged_text)
    
    return merged_tree, conflict_occurred

def get_service():
    """
    Handle oauth's shit (copy-pasta from
    http://code.google.com/apis/tasks/v1/using.html)
    Yes I do publish a secret key here, apparently it is normal
    http://stackoverflow.com/questions/7274554/why-google-native-oauth2-flow-require-client-secret
    """
    FLAGS = gflags.FLAGS
    FLOW = OAuth2WebServerFlow(
            client_id='617841371351.apps.googleusercontent.com',
            client_secret='_HVmphe0rqwxqSR8523M6g_g',
            scope='https://www.googleapis.com/auth/tasks',
            user_agent='michel/0.0.1')
    FLAGS.auth_local_webserver = False
    storage = Storage(os.path.join(save_data_path("michel"), "oauth.dat"))
    credentials = storage.get()
    if credentials is None or credentials.invalid == True:
        credentials = run(FLOW, storage)
    http = httplib2.Http()
    http = credentials.authorize(http)
    return build(serviceName='tasks', version='v1', http=http)

def get_list_id(service, list_name=None):
    if list_name is None:
        list_id = "@default"
    else:
        # look up id by list name
        tasklists = service.tasklists().list().execute()
        for tasklist in tasklists['items']:
            if tasklist['title'] == list_name:
                list_id = tasklist['id']
                break
        else:
            # no list with the given name was found
            print '\nERROR: No google task-list named "%s"\n' % list_name
            sys.exit(2)

    return list_id

def get_gtask_list_as_tasktree(list_name=None):
    """Get a TaskTree object representing a google tasks list.
    
    The Google Tasks list named *list_name* is retrieved, and converted into a
    TaskTree object which is returned.  If *list_name* is not specified, then
    the default Google-Tasks list will be used.
    
    """
    service = get_service()
    list_id = get_list_id(service, list_name)
    tasks = service.tasks().list(tasklist=list_id).execute()
    tasks_tree = TasksTree()
    tasklist = [t for t in tasks.get('items', [])]
    fail_count = 0
    while tasklist != [] and fail_count < 1000 :
        t = tasklist.pop(0)
        try:
            tasks_tree.add_subtask(t['title'].encode('utf-8'), t['id'],
                    t.get('parent'), t.get('notes'), t.get('status'))
        except ValueError:
            fail_count += 1
            tasklist.append(t)
 
    return tasks_tree

def print_todolist(list_name=None):
    """Print an orgmode-formatted string representing a google tasks list.
    
    The Google Tasks list named *list_name* is used.  If *list_name* is not
    specified, then the default Google-Tasks list will be used.
    
    """
    tasks_tree = get_gtask_list_as_tasktree(list_name)
    print(tasks_tree)
    
def write_todolist(orgfile_path, list_name=None):
    """Create an orgmode-formatted file representing a google tasks list.
    
    The Google Tasks list named *list_name* is used.  If *list_name* is not
    specified, then the default Google-Tasks list will be used.
    
    """
    tasks_tree = get_gtask_list_as_tasktree(list_name)
    f = open(orgfile_path, 'wb')
    f.write(str(tasks_tree))
    f.close()

def erase_todolist(list_id):
    """Erases the todo list of given id"""
    service = get_service()
    tasks = service.tasks().list(tasklist=list_id).execute()
    for task in tasks.get('items', []):
        service.tasks().delete(tasklist=list_id,
                task=task['id']).execute()


def parse_path(path):
    """Parses an org-mode file and returns a tree"""
    file_lines = open(path, "r").readlines()
    file_text = "".join(file_lines)
    return parse_text(file_text)
    
def parse_text(text):
    """Parses an org-mode formatted block of text and returns a tree"""
    # create a (read-only) file object containing *text*
    f = cStringIO.StringIO(text)
    
    headline_regex = re.compile("^(\*+ )( *)(DONE )?")
    tasks_tree = TasksTree()
    
    indent_level = 0
    last_indent_level = 0
    seen_first_task = False
    task_notes = None
    for n, line in enumerate(f):
        matches = headline_regex.findall(line)
        line = line.rstrip("\n")
        try:
            # assign task_depth; root depth starts at 0
            num_asterisks_and_space = len(matches[0][0])
            
            # if we get to this point, then it means that a new task is
            # starting on this line -- we need to add the last-parsed task
            # to the tree (if this isn't the first task encountered)
            
            if seen_first_task:
                # add the task to the tree
                tasks_tree.last(indent_level).add_subtask(
                        title=task_title,
                        task_notes=task_notes,
                        task_status=task_status)
            else:
                if task_notes is not None:
                    # this means there was some text at the beginning of the
                    # file before any headline was encountered.  We create a
                    # dummy headline to contain this text.
                    tasks_tree.last(0).add_subtask(
                            title="",
                            task_notes=task_notes,
                            task_status=None)
                # this is the first task, so skip adding a last-task to the
                # tree, and record that we've encountered our first task
                seen_first_task = True
            
            indent_level = num_asterisks_and_space - 2
            
            # strip off asterisks-and-space prefix
            line = line[num_asterisks_and_space:]
            
            if matches[0][2] == 'DONE ':
                task_status = 'completed'
                # number of spaces preceeding 'DONE' and after
                # asterisks+single-space
                num_extra_spaces = len(matches[0][1])
                # remove the '[ ...]DONE ' from the line
                line = line[num_extra_spaces + len('DONE '):]
            else:
                task_status = 'needsAction'
            
            task_title = line
            task_notes = None
        except IndexError:
            # this is not a task, but a task-notes line
            if task_notes is None:
                task_notes = line
            else:
                task_notes += "\n" + line
        
        assert indent_level <= last_indent_level + 1, ("line %d: "
                "subtask has no parent task" % n)
        last_indent_level = indent_level
    # END: for loop
    
    # add the last task to the tree, since the for loop won't be iterated
    # again after the last line of the file (tasks are added at beginning
    # of the for loop)
    tasks_tree.last(indent_level).add_subtask(
            title=task_title,
            task_notes=task_notes,
            task_status=task_status)

    f.close()
    return tasks_tree

def push_todolist(path, list_name):
    """Pushes the specified file to the specified todolist"""
    service = get_service()
    list_id = get_list_id(service, list_name)
    tasks_tree = parse_path(path)
    erase_todolist(list_id)
    tasks_tree.push(service, list_id)

def store_current_tree(tree, listname):
    "Store the current tree persistently for later use"
    # dirty hack -- eventually will write to a persistent database
    open("/tmp/curr_tree","wb").write(str(tree))

def get_last_tree(listname):
    if os.path.exists("/tmp/curr_tree"):
        org_text = open("/tmp/curr_tree","rb").read()
        tree = parse_text(org_text)
        return tree
    else:
        return None

def sync_todolist(path, list_name):
    """Synchronizes the specified file with the specified todolist"""
    gtasks_tree = get_gtask_list_as_tasktree(list_name)
    orgfile_tree = parse_path(path)
    orig_tree = get_last_tree(list_name)
    if orig_tree is None:
        # by default use the gtasks tree if no original tree is available
        orig_tree = gtasks_tree
    
    merged_tree, conflict_occurred = treemerge(orgfile_tree, orig_tree, gtasks_tree)
    
    if conflict_occurred:
        conflicted_filename = path + ".conflicted"
        open(conflicted_filename, "wb").write(str(merged_tree))
        print "\nWARNING:  Org-file and task-list could not be cleanly merged:  " \
              "the attempted merge can be found in '%s'.  Please " \
              "modify this file, copy it to '%s', and push '%s' back " \
              "to the desired GTasks list.\n" % (conflicted_filename, path, path)
        sys.exit(2)
    else:
        # store the successfully merged tree locally so we can use it as the
        # original/base tree in future 3-way merges.
        # TODO: do this also when pushing/pulling?
        store_current_tree(merged_tree, list_name)
        
        # write merged tree to tasklist
        service = get_service()
        list_id = get_list_id(service, list_name)
        erase_todolist(list_id)
        merged_tree.push(service, list_id)
        
        # write merged tree to orgfile
        f = open(path, 'wb')
        f.write(str(merged_tree))
        f.close()


def main():
    parser = argparse.ArgumentParser(description="Synchronize org-mode text" 
                                           "files with a google-tasks list.")
    
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--push", action='store_true',
            help='replace *gtasks_list_name* with the contents of *org_file*.')
    action.add_argument("--pull", action='store_true',
            help='replace *org_file* with the contents of *gtasks_list_name*.')
    action.add_argument("--sync", action='store_true',
            help='synchronize changes between *org_file* and *gtasks_list_name*.')
    
    parser.add_argument('--orgfile',
            metavar='FILE',
            help='An org-mode file to push from / pull to')
    parser.add_argument('--listname',
            help='A GTasks list to pull from / push to (default list if empty)')
    
    args = parser.parse_args()
    
    if args.push and not args.orgfile:
        parser.error('--orgfile must be specified when using --push')
    if args.sync and not args.orgfile:
        parser.error('--orgfile must be specified when using --sync')
    
    if args.pull:
        if args.orgfile is None:
            print_todolist(args.listname)
        else:
            write_todolist(args.orgfile, args.listname)
    elif args.push:
        if not os.path.exists(args.orgfile):
            print("The org-file you want to push does not exist.")
            sys.exit(2)
        push_todolist(args.orgfile, args.listname)
    elif args.sync:
        if not os.path.exists(args.orgfile):
            print("The org-file you want to synchronize does not exist.")
            sys.exit(2)
        sync_todolist(args.orgfile, args.listname)

if __name__ == "__main__":
    main()
