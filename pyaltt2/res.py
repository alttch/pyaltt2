import importlib.util
from functools import lru_cache
from types import SimpleNamespace
from pathlib import Path


class ResourceStorage:
    """
    Resource storage loader

    Usage example:

    from pyaltt.res import ResourceStorage
    from functools import partial

    rs = ResourceStorage(mod=mymod)

    rq = partial(rs.get, resource_subdir='sql', ext='sql')

    rq('object.select.data') - will load resource from (will try all
    variations until file is found):

    * sql/object.select.data.sql
    * sql/object/select.data.sql
    * sql/object/select/data.sql

    Resource is loaded once and cached forever.
    """

    def __init__(self, resource_dir='.', mod=None):
        """
        init resource storage for module

        If module is specified, set directory to module_dir/resources

        Args:
            resource_dir: resource directory or
            mod: module name
        Raises:
            LookupError: if module name is specified, but module is not found
        """
        if mod:
            spec = importlib.util.find_spec(mod)
            if spec is None:
                raise LookupError
            else:
                self.resource_dir = (Path(spec.origin).absolute().parent /
                                     'resources').as_posix()
        else:
            self.resource_dir = resource_dir

    @lru_cache(maxsize=None)
    def get(self,
            resource_id,
            resource_subdir=None,
            ext=None,
            mode='r',
            default=None):
        """
        Get resource

        Loads resource from resource storage directory

        Args:
            resource_id: resource id. dots are replaced with "/" automatically
                until resource is found
            resource_subdir: resource sub directory
            ext: resource extension
            mode: file open mode (default: "r", use "rb" for binary data)
            default: return default value if resource is not found
        Raises:
            LookupError: if resource is not found and no default value provided
        """
        fname = str(resource_id)
        while True:
            fname_full = '{}{}/{}{}'.format(
                self.resource_dir,
                '' if resource_subdir is None else f'/{resource_subdir}', fname,
                '' if ext is None else f'.{ext}')
            try:
                with open(fname_full, mode) as fh:
                    return fh.read()
            except FileNotFoundError:
                if '.' not in fname: break
                fname = fname.replace('.', '/', 1)
        if default is None:
            raise LookupError('resource not found: {}{}'.format(
                resource_id, '' if ext is None else f'.{ext}'))
        else:
            return default
