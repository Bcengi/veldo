# Native wait compatibility

The minimum supported interpreter remains Python 3.11. A source check of
[CPython 3.11's exported kqueue constants](https://raw.githubusercontent.com/python/cpython/3.11/Modules/selectmodule.c)
found that it exports the READ and PROC filters but not USER/NOTE_TRIGGER. The
stop wake therefore uses a nonblocking pipe registered with KQ_FILTER_READ in
the same queue as NOTE_EXIT. The native-stop-pipe row supplies only the published
3.11 constants and drives a real pipe, including consuming the wake and closing
the descriptors. This is Linux seam evidence, not a native macOS qualification.

The first two falsifier runs began before this compatibility correction and its
extra row. Supplemental controls repeat those two mutations on the final tree
and add a mutation that removes the pipe write. Their new records supersede the
earlier runs for final-tree evidence; earlier logs remain unchanged.
