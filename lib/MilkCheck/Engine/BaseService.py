# coding=utf-8
# Copyright CEA (2011) 
# Contributor: TATIBOUET Jérémie <tatibouetj@ocre.cea.fr>

"""
This module contains the definition of the Base class of a service and the
defnition of the different states that a service can go through
"""
from exceptions import NotImplementedError, Exception, TypeError
from MilkCheck.Engine.BaseEntity import BaseEntity
from ClusterShell.Event import EventHandler
from ClusterShell.Task import task_self


"""
Symbols defining the differents status of a service
"""
NO_STATUS = "NO_STATUS"
IN_PROGRESS = "IN_PROGRESS"
SUCCESS = "SUCCESS"
SUCCESS_WITH_WARNINGS = "SUCESS_WITH_WARNINGS"
TIMED_OUT = "TIMED_OUT"
TOO_MANY_ERRORS = "TOO_MANY_ERRORS"


class BaseService(BaseEntity, EventHandler):
    """
    This class is abstract and define the method that a service or a 
    group of service has to implement. In implementing an EventHandler
    this class can handler events generated by ClusterShell.
    """
    
    def __init__(self, name):
        """Constructor"""
        BaseEntity.__init__(self, name)
        EventHandler.__init__(self)
        
        # Define the initial status
        self.status = NO_STATUS
        
        # Define the task
        self._task = task_self()
        
        # Define the last action called on the service
        self._last_action = "unknow"
        
        # Require type dependencies 
        self._requires = {}
        
        # Check type dependencies
        self._checks = {}
       
    
    def add_dependency(self, service, dep_type="require", obl=True):
        """
        Add the dependency in the right dictionnary
        """
        if service:
            dep_type = dep_type.lower()
            if dep_type == "require":
                self._requires[service.name] = (service, "require", obl)
                service.add_child(self)
            elif dep_type == "check":
                self._checks[service.name] = (service, "check", True)
                service.add_child(self)
            else:
                raise IllegalDependencyIdentifier()
        else:
            raise TypeError("service cannot be None") 
    
    def _remaining_dependencies(self):
        """
        Analyze dependencies and returns those which have not state
        """
        remaining = []
        for rname, cname in zip(self._requires, self._checks):
            if rname and self._requires[rname][0].status == NO_STATUS:
                    remaining.append(self._requires[rname])
            if cname and self._checks[cname][0].status == NO_STATUS:
                    remaining.append(self._checks[cname])
        return remaining
    
    def is_check_dep(self, service):
        """
        Evaluate if the dependency given as a parameter is check
        """
        return service.name in self._checks
        
    def is_require_dep(self, service):
        """
        Evaluate if the dependency given as a parameter is require
        """
        return service.name in self._requires

    def cleanup_dependencies(self):
        """
        Clean check and require dependencies
        """
        self._requires.clear()
        self._checks.clear()
        
    def prepare(self, action_name = None):
        """
        Abstract method which will be overriden in Service and ServiceGroup
        """
        raise NotImplementedError

    def update_status(self, status):
        """
        Update the status of a service and launch his dependencies
        """
        self.status = status
        if self.status == SUCCESS or \
            self.status == SUCCESS_WITH_WARNINGS:
            print "%s is done" % self.name
            for child in self.children:
                if child.status == NO_STATUS:
                    child.prepare()
    
    def run(self, action_name):
        """
        Run the action_name over the current service
        """
        self._last_action = action_name
        self.prepare(action_name)
        self.resume()
        
    def resume(self):
        """
        Start the execution of the tasks on the nodes specified
        """
        self._task.resume()
    
    def ev_hup(self, worker):
        """
        Called to indicate that a worker's connection has been closed.
        """
    
    def ev_close(self, worker):
        """
        Called to indicate that a worker has just finished (it may already
        have failed on timeout).
        """
        self.update_status(SUCCESS)

class MilkCheckEngineException(Exception):
    """Base class for Engine exceptions"""
    
    def __init__(self, message=None):
        """Constructor"""
        self._msg = message
        
class ServiceNotFoundError(MilkCheckEngineException):
    """
    Define an exception raised when you are looking for a service
    that does not exist
    """
    
    def __init__(self, message="Service is not referenced by the manager"):
        """Constructor"""
        MilkCheckEngineException.__init__(self, message)

class IllegalDependencyIdentifier(MilkCheckEngineException):
    """
    Exception raised when you try to use another keyword than require
    or check for a depdency
    """
    
    def __init__(self, message="You have to use require or check"):
        """Constructor"""
        MilkCheckEngineException.__init__(self, message)