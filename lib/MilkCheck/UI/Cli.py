# Copyright CEA (2011)
# Contributor: TATIBOUET Jeremie <tatibouetj@ocre.cea.fr>

'''
This module contains the UserView class definition.
'''

# classes
import logging
import logging.config
from os import environ
from sys import stderr, stdout
from MilkCheck.UI.UserView import UserView
from MilkCheck.UI.OptionParser import McOptionParser
from MilkCheck.UI.OptionParser import InvalidOptionError
from MilkCheck.Engine.Action import Action
from MilkCheck.Engine.Service import Service, ActionNotFoundError
from MilkCheck.ActionManager import action_manager_self
from MilkCheck.ServiceManager import service_manager_self
from MilkCheck.ServiceManager import ServiceNotFoundError
from MilkCheck.Engine.BaseEntity import TIMED_OUT, TOO_MANY_ERRORS, ERROR, DONE

class CommandLineInterface(UserView):
    '''
    This class models the Command Line Interface which is a UserView. From
    this class you can get back events generated by the engine and send order
    to the ServiceManager.
    '''

    def __init__(self):
        UserView.__init__(self)
        # Parser which reads the command line
        self._mop = None
        # Store the options parsed
        self._options = None
        # Store the arguments parsed
        self._args = None
        # Profiling mode (help in unit tests)
        self.profiling = False
        # Used in profiling mode
        # Each counter match to a verbosity level
        self.count_low_verbmsg = 0
        self.count_average_verbmsg = 0
        self.count_high_verbmsg = 0

        # HAS TO BE REMOVED AND SET UP IN THE MAIN
        logging.config.fileConfig(environ['PYTHONPATH']+
            '/MilkCheck/Log/mc_logging.conf')

    def execute(self, command_line):
        '''
        Ask for the manager to execute orders given by the command line.
        '''
        watcher = logging.getLogger('watcher')
        userMessenger = logging.getLogger('user')
        self._mop = McOptionParser()
        self._mop.configure_mop()
        try:
            (self._options, self._args) = self._mop.parse_args(command_line)
        except InvalidOptionError, exc:
            watcher.error('%s' % exc)
            self._mop.print_help()
        else:
            manager = service_manager_self()
            self.count_low_verbmsg = 0
            self.count_average_verbmsg = 0
            self.count_high_verbmsg = 0
            # Case 1 : we call services and we are able to add constraints
            if len(self._args) > 1:
                try:
                    manager.call_services(
                        self._args[:len(self._args)-1], self._args[-1],
                            opts=self._options)
                except ServiceNotFoundError, exc:
                    watcher.error(' %s' % exc)
                except ActionNotFoundError, exc:
                    watcher.error(' %s' % exc)
            # Case 2 : we just display dependencies of one or several services
            elif self._options.print_servs:
                print 'TODO : Print service dependencies'
            # Case 3 : Just load another configuration
            elif self._options.config_dir:
                manager.load_config(self._options.config_dir)
            # Case 4: If version option detected so print version number
            elif self._options.version:
                userMessenger.info(self._options.version)
            else:
                self._mop.print_help()

    def __print_service_banner(self, service):
        '''
        This service print the banner specifying that a service is going
        to be compute.
        '''
        userMessenger = logging.getLogger('user')
        msg_len = len('%s - %s' %(service.name, service.desc))
        if msg_len + 2 <= 80:
            userMessenger.info('\n+%s+' % (80*'-'))
            userMessenger.info(
            '|%s%s|' % \
            (' %s - %s ' %(service.name, service.desc),
                (80-(msg_len+2))*' '))
            userMessenger.info('+%s+' % (80*'-'))
        else:
            msg = '%s - %s' %(obj.name, obj.desc)
            userMessenger.info('\n+%s+',(len(msg)+2)*'-')
            userMessenger.info('| %s - %s |' \
            %(obj.name, obj.last_action().name))
            userMessenger.info('+%s+',(len(msg)+2)*'-')

    def __print_msg_status(self, msg, status):
        userMessenger = logging.getLogger('user')
        msg_len = len('%s' % msg)+len('[%s]' % status)
        if msg_len <= 79 :
            userMessenger.info(
                '%s %s' % (msg, '%s[%s]' %(((79 - msg_len)+2)*' ', status)))
        else:
            userMessenger.info('%s [%s]' % (msg, status))

    def ev_started(self, obj):
        '''
        Something has started on the object given as parameter. This migh be
        the beginning of a command one a node, an action or a service.
        '''
        userMessenger = logging.getLogger('user')
        if isinstance(obj, Action) and self._options.verbosity >= 2:
            userMessenger.info('    > %s %s :\n      command %s on %s' % \
            (obj.name, obj.parent.name, obj.command, obj.target))
            if self.profiling:
                self.count_average_verbmsg += 1
        elif isinstance(obj, Service) and not obj.simulate and \
                self._options.verbosity >= 1:
            self.__print_service_banner(obj)
            if self.profiling:
                self.count_low_verbmsg += 1

    def ev_complete(self, obj):
        '''
        Something is complete on the object given as parameter. This migh be
        the end of a command on a node,  an action or a service.
        '''
        userMessenger = logging.getLogger('user')
        #if isinstance(obj, NodeInfo) and self._options.verbosity >= 3:
            #userMessenger.info('        ===> %s' % obj)
            #if obj.node_buffer:
                #userMessenger.info('        [buffer]')
                #userMessenger.info('        %s', obj.node_buffer)
            #if self.profiling:
                #self.count_high_verbmsg += 1
        if isinstance(obj, Action) and self._options.verbosity >= 3:
            self.__print_msg_status(
                '    > action %s of service %s ran in %f second(s)' \
                    %(obj.name, obj.parent.name, obj.duration),
                        obj.status)
            if self.profiling:
                self.count_high_verbmsg += 1
        elif isinstance(obj, Service) and not obj.simulate and \
            self._options.verbosity >= 1:
            self.__print_msg_status('    > %s %s - %s' \
                %(obj.last_action().name,
                    obj.name,
                        obj.last_action().desc),
                            obj.status)
            if self.profiling:
                self.count_low_verbmsg += 1

    def ev_status_changed(self, obj):
        '''
        Status of the object given as parameter. Actions or Service's status
        might have changed.
        '''
        userMessenger = logging.getLogger('user')
        if isinstance(obj, Action) and self._options.verbosity >= 3 and \
            obj.status not in (TIMED_OUT, TOO_MANY_ERRORS, ERROR, DONE) and \
                not obj.parent.simulate:
            self.__print_msg_status('    > action %s of service %s' \
                %(obj.name, obj.parent.name), obj.status)
            if self.profiling:
                self.count_average_verbmsg += 1
        elif isinstance(obj, Service) and self._options.verbosity >= 3 and \
            obj.status not in (TIMED_OUT, TOO_MANY_ERRORS, ERROR, DONE) and \
                not obj.simulate:
            self.__print_msg_status('    > %s %s - %s' \
            %(obj.last_action().name,
                    obj.name,
                        obj.last_action().desc,
                            ), obj.status)
            if self.profiling:
                self.count_low_verbmsg += 1

    def ev_delayed(self, obj):
        '''
        Object given as parameter has been delayed. This event is only raised
        when an action was delayed
        '''
        userMessenger = logging.getLogger('user')
        if isinstance(obj, Action) and not obj.parent.simulate and \
            self._options.verbosity >= 2:
            userMessenger.info(
                '    > %s %s has been delayed during %d second(s)'\
            % (obj.name, obj.parent.name, obj.delay))
            if self.profiling:
                self.count_average_verbmsg += 1

    def ev_trigger_dep(self, obj_source, obj_triggered):
        '''
        obj_source/obj_triggered might be an action or a service. This
        event is raised when the obj_source triggered another object. Sample :
        Action A triggers Action B
        Service A triggers Service B
        '''
        userMessenger = logging.getLogger('user')
        if isinstance(obj_source, Action) and \
                isinstance(obj_triggered, Action) and \
                    self._options.verbosity >= 3:
            userMessenger.info(
            '    > action %s of service %s has triggered action %s'\
                % (obj_source.name, obj_source.parent.name,
                        obj_triggered.name))
            if self.profiling:
                self.count_high_verbmsg += 1
        elif isinstance(obj_source, Service) and \
                isinstance(obj_triggered, Service) and \
                    not obj_source.simulate and \
                        self._options.verbosity >= 3:
            userMessenger.info('    > service %s has triggered service %s'\
                % (obj_source.name, obj_triggered.name))
            if self.profiling:
                self.count_high_verbmsg += 1

    def get_totalmsg_count(self):
        '''Sum all counter to know how many message the CLI got'''
        return  (self.count_low_verbmsg + \
                    self.count_average_verbmsg + \
                        self.count_high_verbmsg)

    total_msg_count = property(fget=get_totalmsg_count)