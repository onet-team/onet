Transactions are a fancy way of updating a database.  In the case of Onet they prevent the proliferation of versions, for example by adding multiple files to a directory (although an `addAll` command would mitigate this as well).

Transactions provide a rollback mechanism and an auditing mechanism (to see who changed what and when).

> I'm starting to think transactions and Acls might be overkill.

### Transaction States

 * `CREATING`
 * `DELETED`
 * `EXECUTING`
 * `FINISHED`
 * `QUEUED`

### Transaction methods

 * `create`: (parent OPTIONAL)
 * `read`: I guess to get the progress, makes more sense from a UI perspective
 * `update`: (part ID, changeTo) (why??)
 * `delete`: (part ID | ALL): To cancel
 * `execute`: To begin
 * `status`: (STATE | FULL): Full is same as `read`?
 * `add`: (parent ID, operation OP, args DICT, opts DICT)
  
### Transaction operations

`NEW_RESOURCE`

parent RES-ID, type (DIR | FILE), name FILENAME

`NEW_VERSION`

id RES-ID, name VERSION-NAME

`SET_PAYLOAD`

cont_id CONT-ID, payload PAYLOAD

`SET_ATTR`

res_id RES-ID, n, v
`VIEW_ATTR`
`DEL_ATTR`

`ADD_ACL`

res_id RES-ID, principal, permissions LIST

`VIEW_ACL`
`DEL_ACL`

`REHASH`

res_id RES-ID method METHOD
  
  * `METHOD` is one of `buzhash`, `size`=SIZE, `rabin-karp`=...

`SET_CONTENT`

cont_id CONT-ID, bytes BYTES

  * `BYTES` can be `base64` or `octet-stream`

```
RES-ID = fake:n
       | uuid:u
       | guid:g
```

```
PAYLOAD = PAYLOAD_INT +
PAYLOAD_INT = cont_id BYTES
            | cont_id CONT-ID
```
