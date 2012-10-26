#!/usr/bin/env python
"""
Pushes/pulls org-mode text files to google tasks

USAGE:
  michel pull [list name]             prints the default tasklist to stdout
                                      in org-mode format.
  michel push <org-file> [list name]  replace the default tasklist with the
                                      content of <org-file>.
"""
from __future__ import with_statement
import gflags
import httplib2
from apiclient.discovery import build
from oauth2client.file import Storage
from oauth2client.client import OAuth2WebServerFlow
from oauth2client.tools import run
from xdg.BaseDirectory import save_config_path, save_data_path
import os.path
import sys
import re

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

    def get(self, task_id):
        """Returns the task of given id"""
        if self.task_id == task_id:
            return self
        else:
            for subtask in self.subtasks:
                if subtask.get(task_id) != None:
                    return subtask.get(task_id)

    def add_subtask(self, title, task_id = None, parent_id = None,
            task_notes=None, task_status=None):
        """
        Adds a subtask to the tree
        - with the specified task_id
        - as a child of parent_id
        """
        if not parent_id:
            self.subtasks.append(TasksTree(title, task_id, task_notes, task_status))
        else:
            if not self.get(parent_id):
                raise ValueError, "No element with suitable parent id"
            self.get(parent_id).add_subtask(title, task_id, None, task_notes,
                    task_status)

    def last(self, level):
        """Returns the last task added at a given level of the tree"""
        if level == 0:
            return self
        else:
            res = None
            for subtask in self.subtasks:
                res = subtask.last(level - 1) or res
            if res:
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
        """string representation of the tree"""
        return '\n'.join(self._lines(0))

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


def print_todolist(list_name=None):
    """Prints the todo list of given id"""
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
    print(tasks_tree)

def erase_todolist(list_id):
    """Erases the todo list of given id"""
    service = get_service()
    tasks = service.tasks().list(tasklist=list_id).execute()
    for task in tasks.get('items', []):
        service.tasks().delete(tasklist=list_id,
                task=task['id']).execute()

def parse(path):
    """Parses a todolist file and returns a tree"""
    headline_regex = re.compile("^(\*+ )( *)(DONE )?")
    tasks_tree = TasksTree()
    with open(path) as f:
        last_indent_level = 0
        seen_first_task = False
        for n, line in enumerate(f):
            matches = headline_regex.findall(line)
            line = line.rstrip("\n")
            try:
                # assign task_depth; root depth starts at 0
                num_asterisks_and_space = len(matches[0][0])
                indent_level = num_asterisks_and_space - 2
                
                # strip off asterisks-and-space prefix
                line = line[num_asterisks_and_space:]
                
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
                    # this is the first task, so skip adding a task to the
                    # tree, and record that we've encountered our first task
                    seen_first_task = True
                
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
        
        # add the last task to the tree, since the for loop won't be iterated
        # again after the last line of the file (tasks are added at beginning
        # of the for loop)
        tasks_tree.last(indent_level).add_subtask(
                title=task_title,
                task_notes=task_notes,
                task_status=task_status)

    return tasks_tree

def push_todolist(path, list_name):
    """Pushes the specified file to the specified todolist"""
    service = get_service()
    list_id = get_list_id(service, list_name)
    tasks_tree = parse(path)
    erase_todolist(list_id)
    tasks_tree.push(service, list_id)

def main():
    if (len(sys.argv)) < 2:
        print(__doc__)
    elif sys.argv[1] == "pull":
        if not len(sys.argv) > 2:
            list_name = None
        else:
            list_name = sys.argv[2]
        print_todolist(list_name)
    elif sys.argv[1] == "push":
        if len(sys.argv) < 3:
            print("'push' expects at least 1 argument")
            sys.exit(2)
        path = sys.argv[2]
        if not os.path.exists(path):
            print("The file you want to push does not exist.")
            sys.exit(2)
        if not len(sys.argv) > 3:
            list_name = None
        else:
            list_name = sys.argv[3]
        push_todolist(path, list_name)
    else:
        print(__doc__)
        sys.exit(2)

if __name__ == "__main__":
    main()
