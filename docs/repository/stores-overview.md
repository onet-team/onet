Stores implement a simple interface (this is not complete):

```
allocate() -> Key
openReader(key, filename) -> Reader
openWriter(key, filename) -> Writer
```
There are 3 (or 4, depending on your viewpoint) stores planned for `Onet`:
  * [HiStore](histore.md) (Available now in32-bit version, 64-bit planned)
  * [UUID](uuid-store.md) (Not available now)
  * [Chunked](chunked-store.md) (Not available now)

