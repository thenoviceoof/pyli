pyli
====

Better scripting with python

Haven't you ever missed writing perl one liners? Or maybe you're more
familiar with python than all the options of ``find``, but like the text
interaction paradigm? ``pyli`` aims to make it easier to use python and
all it's batteries in conjunction with your favorite hangout: the shell.

Install
-------

``pyli`` is available via ``pip``:

::

    pip install pyli

Or directly via ``git`` and ``setup.py``:

::

    git clone https://github.com/thenoviceoof/pyli.git

    cd pyli

    sudo python setup.py

Examples
--------

Let's do some warmups:

::

    pyli "2+2" # bc

    cat file.txt | pyli "line if 'string' in line else None" # grep

    cat file.txt | pyli "sum(len(l) + 1 for l in lines)" # wc -m

And now something more complicated:

::

    log | pyli "str(time.time()) + ' ' + line" # time stamping a line

    cat file.txt | pyli "set(w for s in nltk.sent_tokenize(contents) for w in nltk.word_tokenize)" # bag of words a file

    cat file.json | pyli "pickle.dumps(json.loads(conts))" >file.pickle

    cat space_sep.dat | pyli "json.dumps(dict(parts))" >file.json

Maybe it makes sense to separate commands:

::

    cat index.html | pyli "for l in [a.get('href') for a in bs4.BeautifulSoup(cs).find_all('a')]: print l" | pyli --text='something' "r = requests.get(li); li if text in r.text else None"

    cat index.html | pyli "hashlib.sha1(cs).hexdigest()" | pyli "encryptedfile.EncryptedFile(stdout, getpass.getpass()).write(cs)"

Perhaps you want to keep it a one liner, but Python is too opinionated
to let you do that:

::

    pyli -f "`ls -a`" "for l in f.split('\n'):" "    if '.git' == l: print 'git'"

pyli
----

Features:

- Automatically import referred packages
- Populate special CLI oriented variables

  * ``line`` (``li``, ``l``) - Gives you access to each line
  * ``lines`` (``lis``, ``ls``) - Access to the ``line`` generator
  * ``contents`` (``cont``, ``cs``) - Gives you access to all of stdin
    in one string
  * ``part``, (``p``) - Gives you access to the different fields of a
    space-separated line
  * ``parts``, (``ps``) - Access to the ``part`` generator
  * ``stdin``, ``stdout``, ``stderr`` - A shortcut to ``sys.std*`` streams
  * Accept arbitrary GNU style arguments (-c, --blah), and make them available
  * Print last statement; if an assignment, print the value assigned
    to variable(s)
  * If we are using ``line``/``part``, then print the last statement
    for each line

Do note that you should only access one of these special variables at
a time: no work has been put into combining these into something that
makes sense, so if you want multiple variables, you'll have to do the
legwork yourself.

TODO
----

- Move the engine to the nice-looking ``ast`` library
- Make sure it works in more snakes than just 2.7.3

Also see the `issue tracker
<https://github.com/thenoviceoof/pyli/issues?state=open>`_

LICENSE
-------

"THE BEER-WARE LICENSE" (Revision 42):

<thenoviceoof> wrote these files. As long as you retain this notice
you can do whatever you want with this stuff. If we meet some day, and
you think this stuff is worth it, you can buy me a beer in return

-  thenoviceoof
