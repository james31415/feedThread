# feedThread
## A command line podcatcher implemented in Python

It's coming time for a revamp of this system.

Gripes and future enhancements:

1. Configuration is hard coded in feedThread.py. This should be external to the
source so it doesn't pollute the source code.

2. Having feeds.list, feeds.log, and playlistOrder.list is frustrating. We could
consolidate the files into a YAML file.

3. Clean up the threaded/multiprocessing of feedThread. I don't trust that it's
performant or safe. Need to investigate this and fix.

4. Clean up the interface for feedThread. I'm sticking with a command line interface,
but the wall of text and debug information is a bit much. If we could position
the cursor smarter we'd end up with a cleaner display.

5. Need a better way to specify the order of a podcast. Currently, I'm using the
show's title, but some podcasts like to change their title semi-frequently (WHY!?!?).
Better to use the url as the sort, but this makes it more difficult for a human to
create the list. Maybe another utility to create the sort order?

6. Maybe an option to enable downloading show notes for certain podcasts?
