"""
Wrapper around diff3 to allow merging text strings.

"""
import tempfile
import subprocess

def merge3_text(my_text, orig_text, other_text):
    "Perform diff3 merge on the text-string arguments."
    
    # create temp files for operating on with diff3 tool
    my_file = tempfile.NamedTemporaryFile(mode='w')
    orig_file = tempfile.NamedTemporaryFile(mode='w')
    other_file = tempfile.NamedTemporaryFile(mode='w')
    
    # write text strings to files
    my_file.write(my_text)
    my_file.flush()
    
    orig_file.write(orig_text)
    orig_file.flush()
    
    other_file.write(other_text)
    other_file.flush()

    # call the diff3 executable, and collect results
    p = subprocess.Popen([
                             'diff3', 
                             '-m',
                             '-L', 'MINE',
                             '-L', 'ORIGINAL',
                             '-L', 'OTHER',
                             my_file.name,
                             orig_file.name,
                             other_file.name
                         ],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE)
    stdout_text, stderr_text = p.communicate()
    stdout_text=stdout_text.decode('utf-8')
    stderr_text=stderr_text.decode('utf-8')
    retcode = p.wait()
    # evaluate results
    if retcode == 0: # no conflicts; successful merge
        was_conflict = False
    elif retcode == 1: # there was a conflict
        was_conflict = True
    else: # merge failed
        was_conflict = True

    return stdout_text, was_conflict

