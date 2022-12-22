## Resources

A `resource` is a fancy name for a file.  The reason for the fancy name is that

A Resource is described in the file `Page.onet`, and contains at least the following fields:

* `Type`: `Directory` or `File`
    
* `URN`: The `GUID` (which is actually a UUID4) of the resource. This uniquely identifies it to the system.
    
* `Last-Version`: The `UUID` which refers to the latest version

## Content

Content is stored either as a flat file or as chunks.  The chunker is not currently operational but I plan to use `buzhash` and `rabin-karp` for the chunking algorithms.
