#!/usr/bin/env python
#-*- coding: utf-8 -*-
"""Module for caching variables in different stores."""
import argparse
import json
import logging
from abc import ABCMeta, abstractmethod
from ast import literal_eval
from os import _exit, environ
from sys import stdout
from time import sleep

import requests
from six import PY2, add_metaclass

from kazoo import exceptions as kazoo_exceptions
from kazoo.client import KazooClient

__all__ = ['MemoryCache', 'ZookeeperCache', 'MarathonCache']


@add_metaclass(ABCMeta)
class CacheManager(object):

    """Base cache manager class."""

    def __init__(self):
        self.__variables = {}

    def __getattr__(self, name):
        """Insert a new attribute variable."""
        if name not in self.__variables:
            return self.add_variable(name)
        return self.__variables[name]

    @abstractmethod
    def get_var(self, name):
        """Method GET for a cached variable.

        :param name: 

        """
        pass

    @abstractmethod
    def set_var(self, name, value):
        """Method SET for a cached variable.

        :param name: 
        :param value: 

        """
        pass

    @abstractmethod
    def del_var(self, name):
        """Method DEL for a cached variable.

        :param name: 

        """
        pass

    @abstractmethod
    def pre_add(self, name):
        """Function called before insertion in __variables.

        :param name: str

        """
        pass

    @abstractmethod
    def post_add(self, name, variable):
        """Function called after insertion in __variables.

        :param name: str
        :param variable: Variable

        """
        pass

    def add_variable(self, name):
        """Insert a variable with a specific GET, SET, DEL methods.

        This function call pre_add and post_add. It wraps the
        creation of the variable.

        :param name: str

        """
        self.pre_add(name)
        new_var = Variable(
            name,
            self.get_var,
            self.set_var,
            self.del_var
        )
        self.__variables[name] = new_var
        self.post_add(name, new_var)
        return self.__variables[name]


class Variable(object):

    """Class representing a variable in cache.

    This object will have an attribute called 'value'
    that is linked to the external fget, fset and fdel.
    These functions are passed during the initialization
    along with the name of the variable. The name of
    the variable is binded and is passed as first argument
    each time a GET, SET, DEL function is called.


    """

    def __init__(self, name, fget, fset, fdel):
        self.__name = name
        self.__fget = fget
        self.__fset = fset
        self.__fdel = fdel

    def m_get(self):
        """Call of the real GET method.


        .. note:: the real function needs the name of the
              variable (self.__name) and it's a function
              overrided in CacheManager class.


        """
        return self.__fget(self.__name)

    def m_set(self, value):
        """Call of the real SET method.


        .. note:: the real function needs the name of the
              variable (self.__name) and it's a function
              overrided in CacheManager class.

        :param value: 

        """
        return self.__fset(self.__name, value)

    def m_del(self):
        """Call of the real DEL method.


        .. note:: the real function needs the name of the
              variable (self.__name) and it's a function
              overrided in CacheManager class.


        """
        return self.__fdel(self.__name)

    value = property(m_get, m_set, m_del)


class MemoryCache(CacheManager):

    """Base cache manager class."""

    def __init__(self):
        super(MemoryCache, self).__init__()
        self.__mem = {}

    def get_var(self, name):
        """Method GET for a cached variable.

        :param name: 

        """
        logging.debug("Memory GET variable %s", name)
        return self.__mem.get(name)

    def set_var(self, name, value):
        """Method SET for a cached variable.

        :param name: 
        :param value: 

        """
        logging.debug("Memory SET variable %s to %s", name, value)
        self.__mem[name] = value
        return self.__mem[name]

    def del_var(self, name):
        """Method DEL for a cached variable.

        :param name: 

        """
        logging.debug("Memory DEL variable %s", name)
        tmp = self.__mem[name]
        del self.__mem[name]
        return tmp

    def pre_add(self, name):
        """Function called before insertion in __variables.

        :param name: str

        """
        if name not in self.__mem:
            self.__mem[name] = ""

    def post_add(self, name, variable):
        """Function called after insertion in __variables.

        :param name: str
        :param variable: Variable

        """
        pass


class ZookeeperCache(CacheManager):

    """Cache manager with Zookeeper."""

    def __init__(self, zookeeper_host_list, prefix="/cache/"):
        super(ZookeeperCache, self).__init__()

        self.zookeeper_host_list = None
        self.zk_client = None
        self.map_ = {}
        self.zookeeper_prefix = prefix

        self.init(zookeeper_host_list)
        self.start()

    def __del__(self):
        """Ensure to close the connection."""
        self.stop()

    def string_2_path(self, name):
        """Return the zookeeper cache path for the given name.

        It uses the zookeeper prefix, take a look at
        __init__ function.

        :param name: str
        :returns: str: the zookeeper path in cache

        """
        path_ = self.zookeeper_prefix + name
        logging.debug("Zookeeper PATH: %s", path_)
        return path_

    def get_var(self, name):
        """Returns the variable string.

        :param name: str
        :returns: value: the value of the variable

        .. note::
            The method get of zk_client returns a byte string that have
            to be converted into a string with the method decode.

        """
        try:
            logging.debug("Zookeeper GET variable %s", name)
            container, _ = self.zk_client.get(self.map_[name])
            value = json.loads(container).get('val')
        except kazoo_exceptions.NoNodeError:
            return "ERROR: Node NOT EXISTS or was DELETED!"
        return value

    def set_var(self, name, value):
        """Set the variable into the zookeeper environment.

        Value is forced to be a JSON string to store the basic
        Python types in Zookeeper.

        :param name: str
        :param value: str
        :returns: kazoo.protocol.states.ZnodeStat

        """
        logging.debug("Zookeeper SET variable %s to %s", name, value)
        if PY2:
            return self.zk_client.set(self.map_[name], json.dumps({'val': value}))
        else:
            return self.zk_client.set(self.map_[name], json.dumps({'val': value}).encode())

    def del_var(self, name):
        """Returns the variable string.

        :param name: str
        :returns: tuple(value, ZnodeStat)

        """
        logging.debug("Zookeeper DEL variable %s", name)
        return self.zk_client.delete(self.map_[name])

    def pre_add(self, name):
        """Store the variable into the map as Zookeeper node.

        :param name: str
        :returns: str: the path of that variable inside Zookeeper

        .. hint::
            "my_var" -> "/cache/my_var"

        """
        self.map_[name] = self.string_2_path(name)
        logging.debug("Prepared map for %s", name)
        return self.map_[name]

    def post_add(self, name, variable):
        """Add the variable as Zookeeper node.

        :param name: str
        :param variable: Variable

        """
        logging.debug("Create Zookeeper node for %s", name)
        self.zk_client.ensure_path(self.map_[name])
        val, _ = self.zk_client.get(self.map_[name])
        if not val:
            if PY2:
                self.zk_client.set(self.map_[name], json.dumps({'val': None}))
            else:
                self.zk_client.set(
                    self.map_[name], json.dumps({'val': None}).encode())

    def init(self, zookeeper_host_list):
        """Parse and save zookeeper host list string.

        This function tries also to add the default port
        when is not present in the host address.

        The list is normally retreived from the envirnment
        variables where is stored as a string like:

        ZOOKEEPER_HOST_LIST="['10.1.4.2']"

        :param zookeeper_host_list: str
        :returns: self

        """
        host_list = literal_eval(zookeeper_host_list)
        self.zookeeper_host_list = ",".join(
            [host + ":2181" if host.find(":") == -
             1 else host for host in host_list]
        )
        logging.debug("Zookeeper host string: %s", self.zookeeper_host_list)
        return self  # Enable Chaining

    def start(self):
        """Start zookeeper connection.

        Kazoo client needs a string with the list of zookeeper hosts
        divided by a comma. This little piece of code converts the
        list given as environment variable to a proper kazoo host string
        and starts the connection only if ZOOKEEPER_HOST_LIST is not None.
        In this phase we also prepare the zookeeper nodes to store variables.

        Check KazooClient_ for more information.

        .. hint::
            host1:port1,host2:port2,host3:port3


        :returns: self

        .. note::
            In zookeeper cms cluser are present these children from root ("/") node:

            ["marathon", "mesos", "zookeeper"]

            So path like "/marathon", "/mesos", "/zookeeper" are already available

        .. _KazooClient: https://kazoo.readthedocs.io/en/latest/api/client.html#kazoo.client.KazooClient

        """
        self.zk_client = KazooClient(hosts=self.zookeeper_host_list)
        self.zk_client.start()
        logging.debug("Zookeeper session started!")
        return self  # Enable Chaining

    def stop(self):
        """Close zookeeper connection.


        :returns: self

        """
        self.zk_client.stop()
        logging.debug("Zookeeper session stopped!")
        return self  # Enable Chaining


class MarathonCache(CacheManager):

    """Cache manager with Marathon environment variables.

    Cache is stored as a JSON string in the environment variable
    named CACHE. This object update the Marathon app environment (PATCH)
    only when a variable is setted (set_var) or deleted (del_var)
    because in those two cases the Marathon app will be restarted
    and we don't want a restart when we just use the GET method
    without updating the environment; for this reason the
    creation of the variable is lazy, not like in ZookeeperCache
    where when you create the variable is immediatly created in the
    cache node of Zookeeper.


    """

    def __init__(self, user, passwd, app_id=None, port=8443):
        super(MarathonCache, self).__init__()

        if app_id is not None and app_id[0] != "/":
            app_id = "/" + app_id
        self.__app_name = environ.get(
            'MARATHON_APP_ID') if app_id is None else app_id
        self.__api_url = "https://marathon.service.consul:{}/v2/apps{}"
        self.__port = port
        self.__cache = None
        self.__env = None
        self.__session = requests.Session()
        self.__session.auth = (user, passwd)

    def __del__(self):
        """Ensure to close the session."""
        self.__session.close()
        logging.debug("Session closed!")

    @property
    def app_url(self):
        """Return the base API URL for Marathon.


        :returns: str: APP URL in marathon

        """
        url_ = self.__api_url.format(self.__port, self.__app_name)
        logging.debug("URL generated: %s", url_)
        return url_

    def get_var(self, name):
        """Returns the variable value.

        :param name: str
        :returns: variable: the value of the variable

        """
        logging.debug("Marathon GET variable %s", name)
        return self.__cache.get(name, None)

    def set_var(self, name, value):
        """Set the variable into the zookeeper environment.

        :param name: str
        :param value: str
        :returns: Response object

        """
        logging.debug("Marathon SET variable %s to %s", name, value)
        self.__cache[name] = value
        try:
            res = self.__session.patch(
                self.app_url,
                data=self.json_cache_data(),
                verify=False
            )
        except requests.exceptions.RequestException as exc:
            logging.error("Requests exception SET method: '%s'", exc)

        return res

    def del_var(self, name):
        """Returns the variable string.

        :param name: str
        :returns: Response object

        """
        logging.debug("Marathon DEL variable %s", name)
        del self.__cache[name]
        try:
            res = self.__session.patch(
                self.app_url,
                data=self.json_cache_data(),
                verify=False
            )
        except requests.exceptions.RequestException as exc:
            logging.error("Requests exception DEL method: '%s'", exc)
        return res

    def pre_add(self, name):
        """Update the cache from environment variables.

        :param name: 

        """
        logging.debug("PRE ADD")
        res = self.__session.get(self.app_url, verify=False).json()
        logging.debug("Marathon response: %s", res)
        self.__env = res.get("app").get("env", {})
        if 'CACHE' not in self.__env:
            self.__env['CACHE'] = "{}"
        self.__cache = json.loads(self.__env['CACHE'])
        logging.debug("Current CACHE: %s", self.__cache)

    def post_add(self, name, variable):
        """Nothing to do in post add with Marathon.

        :param name: 
        :param variable: 

        """
        pass

    def json_cache_data(self):
        """Generate the cache JSON string."""
        data = {
            'id': self.__app_name,
            'env': dict(
                (key, value) if key != 'CACHE' else (
                    key, '{}'.format(
                        json.dumps(self.__cache)
                    )
                )
                for key, value in self.__env.items()
            )
        }
        json_data = json.dumps(data)
        logging.debug("JSON data: %s", json_data)
        return json_data


def main():
    """Command line operations.

    Usage Example:
        export ZOOKEEPER_HOST_LIST='["127.0.0.1"]'
        python cache.py zookeeper test
        python cache.py zookeeper test 42 --value-type=int
        python cache.py zookeeper test
    """
    parser = argparse.ArgumentParser(description='Manage cluster cache.')
    parser.add_argument('type', metavar='cache_type', type=str, choices=['memory', 'zookeeper', 'marathon'],
                        help='The type of cache to use')
    parser.add_argument('variable', metavar='variable_name', type=str,
                        help='The name of the variable to retrieve')
    parser.add_argument('value', metavar='value', nargs="?",
                        help='Value to set on selected variable')
    parser.add_argument('--value-type', metavar='value_type', type=str, choices=['int', 'float', 'str'], default="str",
                        help='The type of the value to set')
    parser.add_argument('--wait-for', metavar='wait_for', type=bool, default=False,
                        help='Wait for the variable to be set (!= None)')

    args = parser.parse_args()

    cache = None
    converter = {
        'str': str,
        'int': int,
        'float': float
    }

    if args.type == "zookeeper":
        zookeeper_host_list = environ.get('ZOOKEEPER_HOST_LIST', None)
        if zookeeper_host_list:
            cache = ZookeeperCache(environ.get('ZOOKEEPER_HOST_LIST'))
        else:
            raise Exception(
                "Environment variable ZOOKEEPER_HOST_LIST is not set...")
    elif args.type == "marathon":
        marathon_user = environ.get('MARATHON_USER', None)
        marathon_passwd = environ.get('MARATHON_PASSWD', None)
        if marathon_user and marathon_passwd:
            cache = cache = MarathonCache(marathon_user, marathon_passwd)
        else:
            raise Exception(
                "Environment variable MARATHON_USER or MARATHON_PASSWD are not set...")
    elif args.type == "memory":
        cache = MemoryCache()

    cur_var = getattr(cache, args.variable)
        
    if args.value is not None:
        cur_var.value = converter[args.value_type](
            args.value)

    if args.wait_for:
        while cur_var.value is None or cur_var.value == "None":
            sleep(1)

    stdout.write(str(cur_var.value))
    stdout.flush()
    _exit(0)


if __name__ == '__main__':
    main()