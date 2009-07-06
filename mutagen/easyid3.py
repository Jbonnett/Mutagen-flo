# Simpler (but far more limited) API for ID3 editing
# Copyright 2006 Joe Wreschnig
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of version 2 of the GNU General Public License as
# published by the Free Software Foundation.
#
# $Id: id3.py 3086 2006-04-04 02:13:21Z piman $

"""Easier access to ID3 tags.

EasyID3 is a wrapper around mutagen.id3.ID3 to make ID3 tags appear
more like Vorbis or APEv2 tags.
"""

from fnmatch import fnmatchcase

import mutagen.id3

from mutagen import Metadata
from mutagen._util import DictMixin, dict_match
from mutagen.id3 import ID3, error, delete

__all__ = ['EasyID3', 'Open', 'delete']

class EasyID3KeyError(KeyError, ValueError, error):
    """Raised when trying to get/set an invalid key.

    Subclasses both KeyError and ValueError for API compatibility,
    catching KeyError is preferred.
    """

class EasyID3(DictMixin, Metadata):
    """A file with an ID3 tag.

    Like Vorbis comments, EasyID3 keys are case-insensitive ASCII
    strings. Only a subset of ID3 frames are supported by default. Use
    EasyID3.RegisterKey and RegisterTextKey to support more.

    To use an EasyID3 class with mutagen.mp3.MP3:
        from mutagen.mp3 import EasyMP3 as MP3
        MP3(filename)

    Because many of the attributes are constructed on the fly, things
    like the following will not work:
        ezid3["performer"].append("Joe")
    Instead, you must do:
        values = ezid3["performer"]
        values.append("Joe")
        ezid3["performer"] = values
    """

    Set = {}
    Get = {}
    Delete = {}
    List = {}

    # For compatibility.
    valid_keys = Get
    
    def RegisterKey(cls, key,
                    getter=None, setter=None, deleter=None, lister=None):
        """Register a new key mapping.

        A key mapping is four functions, a getter, setter, deleter,
        and lister. The key may be either a string or a glob pattern.

        The getter, deleted, and lister receive an ID3 instance and
        the requested key name. The setter also receives the desired
        value, which will be a list of strings.

        The getter, setter, and deleter are used to implement __getitem__,
        __setitem__, and __delitem__.

        The lister is used to implement keys(). It should return a
        list of keys that are actually in the ID3 instance, provided
        by its associated getter.
        """
        key = key.lower()
        if getter is not None:
            cls.Get[key] = getter
        if setter is not None:
            cls.Set[key] = setter
        if deleter is not None:
            cls.Delete[key] = deleter
        if lister is not None:
            cls.List[key] = lister
    RegisterKey = classmethod(RegisterKey)

    def RegisterTextKey(cls, key, frameid):
        """Register a text key.

        If the key you need to register is a simple one-to-one mapping
        of ID3 frame name to EasyID3 key, then you can use this
        function:
            EasyID3.RegisterTextKey("title", "TIT2")
        """
        def getter(id3, key):
            return list(id3[frameid])

        def setter(id3, key, value):
            try:
                frame = id3[frameid]
            except KeyError:
                id3.add(mutagen.id3.Frames[frameid](encoding=3, text=value))
            else:
                frame.text = value

        def deleter(id3, key):
            del(id3[frameid])

        cls.RegisterKey(key, getter, setter, deleter)
    RegisterTextKey = classmethod(RegisterTextKey)

    def __init__(self, filename=None):
        self.__id3 = ID3()
        self.load = self.__id3.load
        self.save = self.__id3.save
        self.delete = self.__id3.delete
        if filename is not None:
            self.load(filename)

    filename = property(lambda s: s.__id3.filename,
                        lambda s, fn: setattr(s.__id3, 'filename', fn))

    _size = property(lambda s: s._id3.size,
                     lambda s, fn: setattr(s.__id3, '_size', fn))

    def __getitem__(self, key):
        key = key.lower()
        func = dict_match(self.Get, key)
        if func is not None:
            return func(self.__id3, key)
        else:
            raise EasyID3KeyError("%r is not a valid key" % key)

    def __setitem__(self, key, value):
        key = key.lower()
        if isinstance(value, basestring):
            value = [value]
        func = dict_match(self.Set, key)
        if func is not None:
            return func(self.__id3, key, value)
        else:
            raise EasyID3KeyError("%r is not a valid key" % key)

    def __delitem__(self, key):
        key = key.lower()
        func = dict_match(self.Delete, key)
        if func is not None:
            return func(self.__id3, key)
        else:
            raise EasyID3KeyError("%r is not a valid key" % key)

    def keys(self):
        keys = []
        for key in self.Get.keys():
            if key in self.List:
                keys.extend(self.List[key](self.__id3, key))
            elif key in self:
                keys.append(key)
        return keys

    def pprint(self):
        """Print tag key=value pairs."""
        strings = []
        for key in sorted(self.keys()):
            values = self[key]
            for value in values:
                strings.append("%s=%s" % (key, value))
        return "\n".join(strings)

Open = EasyID3

def genre_get(id3, key):
    return id3["TCON"].genres

def genre_set(id3, key, value):
    try: frame = id3["TCON"]
    except KeyError:
        id3.add(mutagen.id3.TCON(encoding=3, text=value))
    else:
        frame.genres = value

def genre_delete(id3, key):
    del(id3["TCON"])

def date_get(id3, key):
    return [stamp.text for stamp in id3["TDRC"].text]

def date_set(id3, key, value):
    id3.add(mutagen.id3.TDRC(encoding=3, text=value))

def date_delete(id3, key):
    del(id3["TDRC"])

def performer_get(id3, key):
    people = []
    wanted_role = key.split(":", 1)[1]
    try:
        mcl = id3["TMCL"]
    except KeyError:
        raise KeyError(key)
    for role, person in mcl.people:
        if role == wanted_role:
            people.append(person)
    if people:
        return people
    else:
        raise KeyError(key)
    
def performer_set(id3, key, value):
    wanted_role = key.split(":", 1)[1]
    try: mcl = id3["TMCL"]
    except KeyError:
        mcl = mutagen.id3.TMCL(encoding=3, people=[])
        id3.add(mcl)
    people = [p for p in mcl.people if p[0] != wanted_role]
    for v in value:
        people.append((wanted_role, v))
    mcl.people = people

def performer_delete(id3, key):
    wanted_role = key.split(":", 1)[1]
    try:
        mcl = id3["TMCL"]
    except KeyError:
        raise KeyError(key)
    people = [p for p in mcl.people if p[0] != wanted_role]
    if people == mcl.people:
        raise KeyError(key)
    elif people:
        mcl.people = people
    else:
        del(id3["TMCL"])
        
def performer_list(id3, key):
    try: mcl = id3["TMCL"]
    except KeyError:
        return []
    else:
        return list(set("performer:" + p[0] for p in mcl.people))

for frameid, key in {
    "TALB": "album",
    "TBPM": "bpm",
    "TCMP": "compilation", # iTunes extension
    "TCOM": "composer",
    "TCOP": "copyright",
    "TENC": "encodedby",
    "TEXT": "lyricist",
    "TLEN": "length",
    "TMED": "media",
    "TMOO": "mood",
    "TIT2": "title",
    "TIT3": "version",
    "TPE1": "artist",
    "TPE2": "performer", 
    "TPE3": "conductor",
    "TPE4": "arranger",
    "TPOS": "discnumber",
    "TPUB": "organization",
    "TRCK": "tracknumber",
    "TOLY": "author",
    "TSO2": "albumartistsort", # iTunes extension
    "TSOA": "albumsort",
    "TSOC": "composersort", # iTunes extension
    "TSOP": "artistsort",
    "TSOT": "titlesort",
    "TSRC": "isrc",
    "TSST": "discsubtitle",
    }.iteritems():
    EasyID3.RegisterTextKey(key, frameid)

EasyID3.RegisterKey("genre", genre_get, genre_set, genre_delete)
EasyID3.RegisterKey("date", date_get, date_set, date_delete)
EasyID3.RegisterKey(
    "performer:*", performer_get, performer_set, performer_delete,
    performer_list)
