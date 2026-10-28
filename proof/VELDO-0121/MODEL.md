# Exchange model, version relay-exchange-v1

The input is an opaque request identity (SHA-256 of its raw bytes), request length,
response length, ordered send and receive chunk widths, and at most one selected
fault. All representative bytes include NUL and invalid UTF-8. The model makes no
application authority decision and has no replay edge.

| State | Production operation | Normal successor | Refusal or terminal transition |
| :--- | :--- | :--- | :--- |
| Input | `read_all`, before transport begins | Connect, if length at most 1 MiB | Request over limit: exit 4, zero stdout |
| Connect | `conn.connect` | Send(0), or Shutdown for empty request | OSError or timeout: exit 3, zero stdout, endpoint diagnostic |
| Send(s) | `conn.send`, at most 65536 bytes per call | Send(s + n), or Shutdown when all bytes sent | OSError, timeout, or zero send: exit 3, zero stdout, endpoint diagnostic |
| Shutdown | `conn.shutdown(SHUT_WR)` | Receive(0) | OSError or timeout: exit 3, zero stdout, endpoint diagnostic |
| Receive(r) | `conn.recv(65536)` | Receive(r + n), while total at most 1 MiB | OSError or timeout: exit 3, zero stdout, endpoint diagnostic; over limit: exit 4, zero stdout |
| Receive(r), EOF | Same recv returns empty bytes | Return exactly the accumulated bytes, exit 0 | Expired overall deadline: exit 3, zero stdout |
| Cleanup | `conn.close` in finally | No live transport | Always executed after socket creation |

A single monotonic deadline is set before connection. Before each blocking transport
operation the socket timeout is the remaining budget. The next phase checks completion
of connect, send and shutdown. Receive checks the deadline immediately on return,
including EOF, and completion checks it again after joining response chunks. Request
stdin acquisition and downstream stdout failures are outside this transport budget.

## Finite exhaustive domain

`shapes()` crosses request and response lengths 0, 1, 2 and 3, and every ordered
positive composition of each length. Thus every byte offset at which a send or recv
can begin is exercised, for every small request/response composition pair. Empty
requests have no send operation. A recv at response length is the EOF operation and
also has every applicable fault. Shutdown is at the full request length.

Large classes are 65535, 65536, 65537, 1048575 and 1048576 bytes in each direction,
with the opposite direction three bytes. Chunking uses 65536-byte chunks, and a
second alignment with an initial one-byte chunk. Faults occur at every resulting
operation boundary, including the terminal recv. This includes every 65536-byte
boundary up through 1 MiB and the adjacent classes, without claiming all million
individual byte positions. Normal size terminals additionally cover limit plus one
in both directions, with 65535 and 65536 byte widths and varied stdin reads.

The applicable outcome classes are deliberately published, not inferred from
whatever happened to run:

| Operation | Injected outcomes |
| :--- | :--- |
| Connect | ENOENT, ECONNREFUSED, EACCES, ECONNRESET, ETIMEDOUT, socket timeout |
| Send | EPIPE, ECONNRESET, ENOTCONN, ETIMEDOUT, socket timeout, zero progress |
| Shutdown | EPIPE, ECONNRESET, ENOTCONN, ETIMEDOUT, socket timeout |
| Receive | ECONNRESET, ENOTCONN, ETIMEDOUT, socket timeout |

Other OSError values follow the same production exception edge. Signal interruption
restarted internally by Python is not an observable relay transition. There is no
claim to enumerate every errno on every OS or every possible network schedule.

`fault_schedules` generates the legal cells without reading production branches.
Every generated cell must fire, the complete phase/outcome set must equal the table,
and expected and executed cell counts must match. An AST reconciliation checks that
the production `conn` calls are exactly connect, send, shutdown, recv, settimeout and
close. Additional transport operations require model review; a changed call set
fails the check. The runtime barriers execute actual AF_UNIX operations. They cap
partial sends and receives, pump the peer synchronously, and substitute only the
selected failure result or the accelerated clock. Every opened socket is closed.

## Native controls and total time

Native controls close the listening endpoint before connect, and close an accepted
peer before request send, during request, after request and between response chunks.
Reset controls retain unread request bytes in the peer's kernel buffer before
closing it. `MSG_PEEK` observes the complete request identity without consuming those
bytes in the reset case. The fixture records the OS diagnostic actually delivered;
a clean EOF is successful with exactly its prefix, while an error must refuse.
It also requires at least one actual ECONNRESET observation. AF_UNIX close behavior
is not inferred from TCP linger semantics.

Accelerated stalls cover connect, first and partial send, shutdown, first and partial
receive, and EOF. Late successful returns at those same barriers exercise deadline
checks between operations and after EOF. A three-byte trickle advances 29 seconds
per received byte: the second wait must use the one remaining second, not 30.

Two real relay CLI children run concurrently, one with no response and one with its
first byte at 29 seconds. Their endpoints finish by 30.25 seconds even under the
renewing-deadline falsifier. Each child receives its complete stdin and has stdout
and stderr drained by `communicate`. The check requires exit 3, zero stdout, the
endpoint diagnostic, at most 31 seconds, and joined endpoint threads and reaped
children. A 32-second fixture watchdog is an invalid mutation drive, not a detected
falsifier. No process detaches. The fixture never opens any host lock.

## Independent observations and evidence

Connection attempts come from the socket wrapper, accepted connections from the
listener, and complete identities from bytes read or peeked at the peer as soon as
the complete fixture request has arrived, even if write-half shutdown later fails.
Empty requests are counted on write-half shutdown. They do not depend on relay stdout. Every generated error cell
feeds both the refusal row and the no-replay row. A failure after a complete request
leaves its application result uncertain; it never means the command was unapplied.

Each record binds its case, input digest, implementation digest and fixture version;
records contain phase, byte offset, outcome, exact stderr, losslessly compressed
stdout, return code, elapsed time and connection/request counts. Decode stdout with
`zlib.decompress(base64.b64decode(record['stdout']['zlib_base64']))`.
The enclosing receipt also binds the fixture digest and reports expected/executed
counts, incomplete schedules and invalid drives.
