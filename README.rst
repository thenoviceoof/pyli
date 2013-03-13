pyli
====

Better scripting with python

Haven't you ever missed writing perl one liners? Or maybe you're more
familiar with python than all the options of ``find``, but like the text
interaction paradigm? ``pyli`` aims to make it easier to use python and
all it's batteries in conjunction with your favorite hangout: the shell.

Examples
--------

Let's do some warmups:

::

    pyli "2+2" # bc

    cat file.txt | pyli "line if 'string' in line else None" # grep

    cat file.txt | pyli "sum(len(l) for l in lines)" # wc -m

And now something more complicated:

::

    log | pyli "str(time.time()) + ' ' + line" # time stamping a line

    cat file.txt | pyli "set(w for s in nltk.sent_tokenize(contents) for w in nltk.word_tokenize)" # bag of words a file

    cat file.json | pyli "pickle.dumps(json.loads(conts))" >file.pickle

Maybe it makes sense to separate commands:

::

    cat index.html | pyli "a.get('href') for a in bs4.BeautifulSoup(cs).find_all('a')" | pyli --text='something' "r = requests.get(li); li if text in r.text else None"

    cat index.html | pyli "hashlib.sha1(cs).hexdigest()" | pyli "encryptedfile.EncryptedFile(stdout, getpass.getpass()).write(cs)"

pyli
----

Features:

- Automatically import referred packages
- Populate special CLI oriented variables

  * ``line`` (``li``, ``l``)
  * ``lines`` (``lis``, ``ls``)
  * ``contents`` (``cont``, ``cs``)
  * ``stdin``, ``stdout``, ``stderr``
  * Accept arbitrary GNU style arguments (-c, --blah), and make them available
  * Print last statement; if an assignment, print the assigned to variables
  * If we are using ``line``, then print the last statement for each line

pylie
-----

So your perl one-liner itch hasn't been itched enough yet? This command
is for things that do not strictly fit into 'normal' python usage. For
example:

::

    log | pyli "'{0} {1}'.fo(s(ti.ti()), l)"

    cat index.html | pyli "a.g('href') for a in BeSp(cs).f_all('a')" | pyli --text='something' "r = req.get(li); li if text in r.text else None"

Features:

- Autocomplete
- Look through modules for 2nd level functions to import

TODO
----

What's left to do? Well, pretty much everything: it currently imports
things and prints things out, and detects the use of
contents/input/conts, but that's it. If you think this would be actually
useful, do send me a message, since I just ran out of motivation with
which to work on this. Or better yet, contribute!

LICENSE
-------

"THE BEER-WARE LICENSE" (Revision 42):

<thenoviceoof> wrote this file. As long as you retain this notice you
can do whatever you want with this stuff. If we meet some day, and you
think this stuff is worth it, you can buy me a beer in return

-  thenoviceoof
