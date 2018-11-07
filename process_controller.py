import multiprocessing
import logging
import time
import tcp_log_socket
import sys
import os
from collections import deque
from subprocess import Popen, DETACHED_PROCESS, CREATE_NEW_PROCESS_GROUP

"""The default test logger and logging server are globally implemented.
   Future changes may change this to a class-based implementation."""

logger = logging.getLogger()
log_server_pid = None

"""Method to spawn the included test log server; uses globals at the current time due to pickling restrictions on class-implemented loggers."""
def use_included_logger():
    global log_server
    global logger
    global log_server_pid
    logging_socket = tcp_log_socket.local_logging_socket(__name__)
    logger = logging_socket.logger
    log_server = Popen([sys.executable, "tcp_log_server.py"], close_fds=True, shell=True, creationflags=DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP)
    log_server_pid = log_server.pid

"""Terminate the included logger and close its window."""
def kill_included_logger():
    global log_server_pid
    Popen("TASKKILL /F /PID {} /T".format(log_server_pid))

class ProcessController(object):

    def __init__(self, target_method, included_logger=True):

        """[NOTE: GLOBAL REFERENCE] If included_logger is True, use the included logger and log server."""
        use_included_logger() #Reference to a global function; loggers belonging to the same class implementation cannot be pickled using multiprocessing.Process

        """[NOTE: GLOBAL REFERENCE] Reference to a single global which tracks if the included logging server has been started."""
        global log_server_pid
        if log_server_pid is not None:
            self.log_server_exists = True
            self.log_server_pid = log_server_pid

        """Target method to run with a pool of workers or in another process"""
        self.target_method = target_method  #method to assign to a process or pool

        """Initialization for pool functionality"""
        self.pool = None  #Contains a persistent pool; no pool initialized by default
        self.pool_job_id = 0
        self.pool_results = [] #Results of jobs run using a pool

        """Initialization for process functionality"""
        self.processes = deque([]) #List of created processes
        self.process_results = [] #Multiprocessing queue used to get results from worker process
        self.join_timeout = 10 #Timeout in seconds for joining process (if process is dead or has returned results)
        self.cleaner_interval = 30 #Timeout in seconds for running the process cleaner (if active)

    #Creates a new persistent pool with a number of processes or replaces an existing one
    def create_new_pool(self, num_processes):
        if self.pool is not None:
            logger.info("Pool exists; waiting for existing jobs to finish before closing pool.")
            self.pool.close() #Wait for existing jobs to finish
        self.pool = multiprocessing.Pool(num_processes)
        logger.info("Pool with {} available processes created.".format(num_processes))

    #Runs jobs for a given list of input parameters using the assigned target method and an existing pool
    def use_pool(self, jobs):
        if self.pool is None:
            logger.warning("No pool exists; create a pool to run jobs.")
        if any(isinstance(entry, list) for entry in jobs): #if open jobs (input_data) contain nested lists, use starmap
            results = self.pool.starmap_async(self.target_method, jobs)
        else:
            results = self.pool.map_async(self.target_method, jobs)
        logger.info("Created worker processes; running processes: {}".format(self.pool._processes))
        while True:
            remaining_progress = results._number_left
            if (results.ready()):
                logger.info("All jobs completed.")
                self.pool_results.append([results.get(), "Pool Job ID: {}".format(self.pool_job_id)])
                self.pool_job_id += 1
                break
            else:
                logger.info("Jobs in progress, {} jobs left.".format(remaining_progress)) #Replace with progress bar
                time.sleep(2)

    #Check process list for dead processes
    def clean_process_list(self):
        logger.info("Checking for dead or orphaned processes.")
        if len(self.processes):
            for i in range(0, len(self.processes)):
                process = self.processes.pop()
                if process.is_alive() is not True:
                    logger.info("{} is unresponsive; terminating process.".format(process.name))
                    process.terminate()
                else:
                    self.processes.appendleft(process)

    #Worker method which puts results from a target method into a queue, if any exist. Self-terminates on completion.
    def worker(self, args):
        worker_name = multiprocessing.current_process().name
        if self.log_server_exists:
            logging_socket = tcp_log_socket.local_logging_socket(worker_name)
            logger = logging_socket.logger
        else:
            logger = logging.getLogger(worker_name)
        logger.info("Running process {}; waiting for results.".format(worker_name))
        results = self.target_method(*args)
        results_queue = self.process_results
        logger.info("Ran target method, storing results and name of finished process.")
        results_queue.put([results, worker_name])
        logger.info("Process {} completed, exiting.".format(worker_name))
        sys.exit(0)

    #Creates and uses a process to run a job using the assigned target method. Set "use_cleaner" to turn off the process cleaner (in "process_cleaner")
    def use_process(self, args):
        self.clean_process_list()
        self.process_results = multiprocessing.Queue()
        process = multiprocessing.Process(target=self.worker, args=(args,))
        logger.info("Created process; process name is {}".format(process.name))
        self.processes.append(process)
        process.start()
        logger.info("Process {} started.".format(process.name))
