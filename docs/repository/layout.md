##

* Version
* Attributes
* Acls
* Entries
* Content
* Chunks

### Version Storage Models

#### Chunks

The file is broken into pieces called chunks that have some special attribute. Maybe they satisfy an algorithm (like in `buzhash` for example), or are of a certain size.

It makes sense to break up large files that wont change much, if ever, with the size model, than with the algorithm model.

#### Diffs

Meant for storing documents or source files.

Usually done with the `rdiff` algorithm.

#### Plain

As it says, plain.
