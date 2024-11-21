# pyli

Better scripting with python

Haven't you ever missed writing perl one liners? Or maybe you're more
familiar with python than all the options of `find`, but like the text
interaction paradigm of the command line? `pyli` aims to make it
easier to use python and all its batteries in conjunction with the
shell.

## Install

`pyli` is available from `pypi` via `pip`:

```
pip install pyli
```

You can also download the source directly:

```
git clone https://github.com/thenoviceoof/pyli.git
pip install pyli/
```

Unfortunately, type annotations mean the minimum supported Python
version is 3.9.

## Examples

Let's do some warmups:

```
pyli "2+2" # bc
cat file.txt | pyli "line if 'string' in line else None" # grep
cat file.txt | pyli "sum(len(l) + 1 for l in lines)" # wc -m
```

And now some more complicated examples:

```
log | pyli "str(time.time()) + ' ' + line" # time stamping a line
cat file.txt | pyli "set(w for s in nltk.sent_tokenize(contents) for w in nltk.word_tokenize)" # bag of words a file
cat file.json | pyli "pickle.dumps(json.loads(conts))" >file.pickle
cat space_sep.dat | pyli "json.dumps(dict(parts))" >file.json
```

Maybe it makes sense to separate commands:

```
cat index.html | pyli "for l in [a.get('href') for a in bs4.BeautifulSoup(cs).find_all('a')]: print l" | pyli --text='something' "r = requests.get(li); li if text in r.text else None"
cat index.html | pyli "hashlib.sha1(cs).hexdigest()" | pyli "encryptedfile.EncryptedFile(stdout, getpass.getpass()).write(cs)"
```

Perhaps you want to keep it a one liner, but Python is too opinionated
to let you do that:

```
pyli -f "`ls -a`" "for l in f.split('\n'):" "    if '.git' == l: print 'git'"
```

## pyli

Features:

- Automatically import referred packages
- Populate special CLI oriented variables
    - ``line`` (``li``, ``l``): Gives you access to each line
    - ``lines`` (``lis``, ``ls``): Access to the ``line`` generator
    - ``contents`` (``cont``, ``cs``): Gives you access to all of stdin
      in one string
    - ``part``, (``p``): Gives you access to the different fields of a
      space-separated line
    - ``parts``, (``ps``): Access to the ``part`` generator
    - ``stdin``, ``stdout``, ``stderr``: A shortcut to ``sys.std*`` streams
    - Accept arbitrary GNU style arguments (-c, --blah), and make them available
    - Print last statement; if an assignment, print the value assigned
      to variable(s)
    - If we are using ``line``/``part``, then print the last statement
      for each line

Do note that you should only access one of these special variables at
a time: no work has been put into combining these into something that
makes sense, so if you want multiple variables, you'll have to do the
legwork yourself.

See the [issue tracker](https://github.com/thenoviceoof/pyli/issues?state=open).

## Related Projects

In alphabetical order:

- [funcpy](http://www.pixelbeat.org/scripts/funcpy)
- [Oneliner](https://github.com/gvalkov/python-oneliner)
- [Pyle](https://github.com/aljungberg/pyle)
- [pyp](https://code.google.com/p/pyp/)

## LICENSE

Copyright (c) <2014> <thenoviceoof>

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
