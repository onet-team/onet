The hierarchical store is the default store (and currently the only one implemented).

It stores files in a mechanism similar to [Squid](http://www.squid-cache.org/). (Or at least the way it used to -- I don't know anymore.), 256 per directory, 4 levels deep.  This allows for 4 billion plus resources, plus infinite versions.  You should never run out of IDs. (Of course if you do then you can use a 64 bit version, which holds ALOT more).

It chooses `key`s by a random (ie sequential) order and stores resources one per directory.

It uses a cache to map `GUID`s and `UUID`s to HiStore keys.
