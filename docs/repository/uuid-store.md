The UUID store is not implemented.

It stores files in a mechanism similar to [HiStore](histore.md). There 256 per directory, for a number of levels, maybe 2 or 3, and then by uuid. This allows for unlimited resources 

It may have the same problem as [chunked store](chunked-store.md), that being the separation of resource items from each other.
I do not know how to implement they key * filename mechanism that other stores (HiStore) employ.

It has no need for a cache to map `GUID`s and `UUID`s to keys, because the keys are UUIDs and GUIDs.