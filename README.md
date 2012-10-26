Michel-orgmode is a fork of [michel](https://github.com/chmduquesne/michel)
which serves as a bridge between an [org-mode](http://orgmode.org/) textfile
and a google-tasks task list.  It can push/pull org-mode text files to/from
google tasks.

Usage
=====

Configuration
-------------

At the first run, you will be shown a URL. Click it, and authorize michel.
You're done!

The authorization token is stored in `$XDG_DATA_HOME/michel/oauth.dat`. This
is the only information stored.

Commands
--------

Michel keeps it simple. It only has two commands:

    michel.py pull [list name]
Print the named (or default if no name is given) task list on the standard
output.

    michel.py push <TODO.org> [list name]
Replace the named (or default if no name is given) task list with the contents
of TODO.org

Syntax
------

This script currently only supports a subset of the org-mode format.  The
following elements are mapped mapped between google-tasks and an org-mode file:

* Indented Tasks <-> Number of preceding asterisks
* Task Notes <-> Headline's body text
* Checked-off / crossed-out <-> Headline is marked as DONE

How to
------

Here is how michel can be used. A crontask pulls every 15 minutes the
default TODO list, and another one displays a notification during 10
seconds every hour (requires notify-send).

    */15 * * * * /path/to/michel.py pull > /tmp/TODO && mv /tmp/TODO ~/.TODO
    0 * * * * DISPLAY=":0.0" notify-send -t 10000 TODO "$(cat ~/.TODO)"

After you modify your TODO list, don't forget to push it!

    michel.py push .TODO

If this trick is not working, it is probably because the variable PATH
does not contains /usr/local/bin in crontab. You might want to set it
manually. See 'man 5 crontab'.

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
