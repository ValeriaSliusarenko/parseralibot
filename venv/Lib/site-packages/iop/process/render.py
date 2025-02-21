import datetime
import os
import socket


def setup_env(env):
    pass


def default_params():
    return {
        "now": datetime.datetime.now(),
        "host": socket.getfqdn(),
        "env": os.environ
    }


def template(text, **params):
    import jinja2
    env = jinja2.Environment(loader=jinja2.BaseLoader())
    setup_env(env)
    return env.from_string(text).render(**params, **default_params())


def file(filename, **params):
    import jinja2
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(os.path.dirname(filename)))
    setup_env(env)
    t = env.get_template(os.path.basename(filename))
    return t.render(**params, **default_params())
