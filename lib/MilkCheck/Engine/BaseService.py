# Copyright CEA (2011) 
# Contributor: TATIBOUET Jeremie <tatibouetj@ocre.cea.fr>

"""
This module contains the definition of the Base class of a service and the
defnition of the different states that a service can go through
"""

# Classes
from MilkCheck.Engine.BaseEntity import BaseEntity
from MilkCheck.Engine.Dependency import Dependency
from ClusterShell.Event import EventHandler
from ClusterShell.Task import task_self

# Symbols
from MilkCheck.Engine.Dependency import CHECK, REQUIRE, REQUIRE_WEAK

# Exceptions
from MilkCheck.Engine.Dependency import IllegalDependencyTypeError
from MilkCheck.Engine.BaseEntity import MilkCheckEngineError

"""
Symbols defining the differents status of a service
"""
NO_STATUS = "NO_STATUS"
IN_PROGRESS = "IN_PROGRESS"
SUCCESS = "SUCCESS"
SUCCESS_WITH_WARNINGS = "SUCCESS_WITH_WARNINGS"
TIMED_OUT = "TIMED_OUT"
TOO_MANY_ERRORS = "TOO_MANY_ERRORS"
ERROR = "ERROR"

class DependencyAlreadyReferenced(MilkCheckEngineError):
    """
    This exception is raised if you try to add two times the same
    depedency to the same service.
    """

class BaseService(BaseEntity, EventHandler):
    """
    This class is abstract and define the method that a service or a 
    group of service has to implement. In implementing an EventHandler
    this class can handler events generated by ClusterShell.
    """
    
    def __init__(self, name):
        BaseEntity.__init__(self, name)
        EventHandler.__init__(self)
        
        # Define the initial status
        self.status = NO_STATUS
        
        # Define whether the service has warnings
        self.warnings = False
        
        # Define the task
        self._task = task_self()
        
        # Define the last action called on the service
        self._last_action = None
        
        # Define a dictionnary of dependencies
        # key: Dependency object 
        self._deps = {}
    
    def add_dependency(self, service, dep_type=REQUIRE, internal=False):
        """Add a new dependency to a the current base service."""
        if service:
            if service.name in self._deps:
                raise DependencyAlreadyReferenced()
            else:
                if dep_type in (CHECK, REQUIRE, REQUIRE_WEAK):
                    self._deps[service.name] = Dependency(service,
                                                    dep_type, internal)
                    service.add_child(self)
                else:
                    raise IllegalDependencyTypeError()
        else:
            raise TypeError("service cannot be None")
    
    def has_dependency(self, dep_name):
        """Return true if the service own this dependency"""
        return dep_name in self._deps
            
    def search_deps(self, symbols=None):
        """Search the dependencies matching one of the symbol."""
        matching = []
        for dep_name in self._deps:
            if symbols:
                if self._deps[dep_name].target.status in symbols:
                    matching.append(self._deps[dep_name])
            else:
                matching.append(self._deps[dep_name])
        return matching
            
    def eval_deps_status(self):
        """
        Evaluate the result of the dependencies in order to check
        if we have to continue in normal mode or in a degraded mode.
        """
        temp_dep_status = SUCCESS
        for dep_name in self._deps:
            if self._deps[dep_name].target.status in \
                (TOO_MANY_ERRORS, TIMED_OUT, ERROR):
                if self._deps[dep_name].is_strong():
                    return ERROR
                else:
                   temp_dep_status = SUCCESS_WITH_WARNINGS
            elif self._deps[dep_name].target.status == IN_PROGRESS:
                return IN_PROGRESS
            elif self._deps[dep_name].target.status == NO_STATUS:
                temp_dep_status = NO_STATUS
        return temp_dep_status
    
    def has_in_progress_dep(self):
        """
        Allow us to determine if the current services has to wait before to
        start due to unterminated dependencies.
        """
        for dep_name in self._deps:
            if self._deps[dep_name].target.status == IN_PROGRESS:
                return True
        return False

    def clear_deps(self):
        """Clear dependencies."""
        self._deps.clear()
        
    def prepare(self, action_name=None):
        """
        Abstract method which will be overriden in Service and ServiceGroup.
        """
        raise NotImplementedError

    def update_status(self, status):
        """Update the status of a service and launch his dependencies."""
        self.status = status 
        print "[%s] is [%s]" % (self.name, self.status)
      
        if self.status not in (NO_STATUS, IN_PROGRESS):
            # The action performed on the current service
            # had some issues
            for child in self.children:
                if child.status == NO_STATUS and \
                    not child.has_in_progress_dep():
                    print  "*** %s triggers %s" % (self.name, child.name)
                    child.prepare()
    
    def run(self, action_name):
        """Run the action_name over the current service."""
        self.prepare(action_name)
        self.resume()
        
    def resume(self):
        """Start the execution of the tasks on the nodes specified."""
        self._task.resume()
    
    def ev_timer(self, timer):
        """Handle firing timer."""
        raise NotImplementedError
    
    def ev_close(self, worker):
        """
        Called to indicate that a worker has just finished (it may already
        have failed on timeout).
        """
        raise NotImplementedError