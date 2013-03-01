import os

get_lockfilename = lambda f: os.path.splitext(f)[0]+'.lock'

def get_lock(filepath):
    lockfile = get_lockfilename(filepath)
    if os.path.exists(lockfile):
        return False
    open(lockfile, 'w').close()
    return True


def release_lock(filepath):
    lockfile = get_lockfilename(filepath)
    if not os.path.exists(lockfile):
        return False
    os.remove(lockfile)
    return True


def release_lock_decorator(decorated_function):
    def inner_function(filepath, *args, **kwargs):
        try:
            decorated_function(filepath, *args, **kwargs)
        finally:
            release_lock(filepath)
    return inner_function
