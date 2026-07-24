from stimpack.experiment import server


class BaseServer(server.BaseServer):
    """Lab-wide server base class. Put behavior shared by all of your rigs here.

    Arguments are forwarded verbatim to stimpack's BaseServer rather than re-declared, so this
    wrapper does not go stale when stimpack gains a parameter (e.g. start_loop) and does not
    silently shadow a stimpack default.

    Note on `host`: stimpack binds to loopback (127.0.0.1) by default, because the RPC control
    channel is unauthenticated. If a rig must accept connections from another machine (the usual
    remote-server setup), pass host explicitly in that rig's server script -- preferably the rig's
    own network address rather than '0.0.0.0' -- and firewall the port to the trusted rig network.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
