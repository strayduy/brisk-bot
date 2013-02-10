Brisk Bots
==========

Bots for competing in the [Brisk Challenge](http://www.briskchallenge.com/).

Requirements
------------

* Python 2.7
* [Requests](http://docs.python-requests.org/en/latest/)
* [NetworkX](http://networkx.github.com/)
* virtualenv/virtualenvwrapper (optional)

Setup
-----

### Install Dependencies (using virtualenv)

```
$ mkvirtualenv brisk
$ workon brisk
$ git clone git@github.com:strayduy/brisk-bot.git
$ cd brisk-bot
$ pip install -r virtualenv-requirements.txt
```

### Install Dependencies (without virtualenv)

```
$ git clone git@github.com:strayduy/brisk-bot.git
$ cd brisk-bot
$ pip install requests networkx
```

### Running the Bot

```
$ python area-control-bot.py
```
