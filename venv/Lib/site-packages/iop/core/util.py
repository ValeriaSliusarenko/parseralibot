class Stop(RuntimeError): pass


def stop():
    raise Stop()
