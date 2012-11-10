Michel-orgmode is a fork of [michel](https://github.com/chmduquesne/michel)
which serves as a bridge between an [org-mode](http://orgmode.org/) textfile
and a google-tasks task list.  It can push/pull org-mode text files to/from
google tasks, and perform bidirectional synchronization/merging between an
org-mode text file and a google tasks list.

Usage
=====

Configuration
-------------

At the first run, you will be shown a URL. Click it, and authorize michel.
You're done!

The authorization token is stored in `$XDG_DATA_HOME/michel/oauth.dat`. This
is the only information stored.

Command line options
--------------------

    usage: michel [-h] (--push | --pull | --sync) [--orgfile FILE]
                  [--listname LISTNAME]

    optional arguments:
      -h, --help           show this help message and exit
      --push               replace LISTNAME with the contents of FILE.
      --pull               replace FILE with the contents of LISTNAME.
      --sync               synchronize changes between FILE and LISTNAME.
      --orgfile FILE       An org-mode file to push from / pull to
      --listname LISTNAME  A GTasks list to pull from / push to (default list if
                           empty)

Org-mode Syntax
---------------

This script currently only supports a subset of the org-mode format.  The
following elements are mapped mapped between google-tasks and an org-mode file:

* Indented Tasks <-> Number of preceding asterisks
* Task Notes <-> Headline's body text
* Checked-off / crossed-out <-> Headline is marked as DONE


Installation Dependencies
=========================

The `michel.py` script runs under Linux (not tested on other platforms yet).
To run the script, you need to install the following dependencies:

* [google-api-python-client](http://code.google.com/p/google-api-python-client/)
* [python-gflags](http://code.google.com/p/python-gflags/) (usually available in
  package repositories of major linux distributions)


About
=====

Author/License
--------------

- License: Public Domain
- Original author: Christophe-Marie Duquesne ([blog post](http://blog.chmd.fr/releasing-michel-a-flat-text-file-to-google-tasks-uploader.html))
- Author of org-mode version: Mark Edgington ([bitbucket site](https://bitbucket.org/edgimar/michel-orgmode))

Contributing
------------

Patches are welcome, as long as they keep the source simple and short.
