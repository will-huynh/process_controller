import multiprocessing
import logging
import time
from inspect import getfullargspec
import sys
import os
import signal
import atexit
from collections import deque
from subprocess import Popen, DETACHED_PROCESS, CREATE_NEW_PROCESS_GROUP
import tcp_log_socket

"""The default test logger and logging server are globally implemented.
   Future changes may change this to a class-based implementation."""

logger = logging.getLogger()
log_server_pid = None
log_server_dir = "tcp_log_server.py" #The name of the log file to be output; created relative to the directory of the logging server

"""Method to spawn the included test log server; uses globals at the current time due to pickling restrictions on class-implemented loggers."""
def use_included_logger():
    global log_server
    global logger
    global log_server_pid
    logging_socket = tcp_log_socket.local_logging_socket(__name__)
    logger = logging_socket.logger
    log_server = Popen([sys.executable, log_server_dir], close_fds=True, shell=True, creationflags=DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP)
    log_server_pid = log_server.pid

"""Terminate the included logger and close its window."""
def kill_included_logger():
    global log_server_pid
    Popen("TASKKILL /F /PID {} /T".format(log_server_pid))

class ProcessController(object):

    def __init__(self, target_method, included_logger=True):

        """[NOTE: GLOBAL REFERENCE] If included_logger is True, use the included logger and log server.
        Reference to a single global which tracks if the included logging server has been started."""
        self.included_logger = included_logger
        if self.included_logger:
            use_included_logger() #Reference to a global function; loggers belonging to the same class implementation cannot be pickled using multiprocessing.Process
            global log_server_pid
            self.log_server_pid = log_server_pid

        """Exit handlers for normal and abnormal termination"""
        atexit.register(self.quit)
        signal.signal(signal.SIGABRT, self.exit)
        signal.signal(signal.SIGTERM, self.exit)

        """Target method to run with a pool of workers or in another process. If the method has no arguments, apply a wrapper to allow it to be used by worker processes."""
        self.target_method = target_method  #method to assign to a process or pool
        self.target_method_no_args = False
        self.req_args = getfullargspec(self.target_method).args #Get list of required positional arguments
        if not len(self.req_args):
            self.target_method_no_args = True


        """Initialization for pool functionality"""
        self.pool = None  #Contains a persistent pool; no pool initialized by default
        self.pool_batch_id = 0
        self.pool_cache = deque([]) #Cache which holds results of pending and recently finished batches of jobs
        self.pool_results = deque([]) #Stores all results that have been created by a controller instance by order of worker completion

        """Initialization for process functionality"""
        self.processes = deque([]) #List of created processes
        self.process_queue = None #Multiprocessing queue used to get results from worker process
        self.process_results = deque([]) #Stores all worker process results for processing

    #Creates a new persistent pool with a number of processes or replaces an existing one
    def create_new_pool(self, num_processes):
        if self.pool is not None:
            logger.info("Pool exists; waiting for existing jobs to finish before closing pool.")
            self.pool.close() #Wait for existing jobs to finish
        self.pool = multiprocessing.Pool(num_processes)
        logger.info("Pool with {} available processes created.".format(num_processes))

    #Runs jobs for a given list of input parameters using the assigned target method and an existing pool
    def use_pool(self, jobs, **kwargs):
        if self.pool is None:
            logger.warning("No pool exists; create a pool to run jobs.")
        if self.target_method_no_args: #if target method uses no positional arguments, use apply_async
            results = []
            for job in jobs:
                result = self.pool.apply_async(self.target_method, (), **kwargs)
                results.append(result)
        elif any(isinstance(entry, list) for entry in jobs): #if open jobs (input_data) contain nested lists, use starmap
            results = self.pool.starmap_async(self.target_method, jobs)
        else:
            results = self.pool.map_async(self.target_method, jobs)
        logger.info("Created worker processes; running processes: {}".format(self.pool._processes))
        self.pool_cache.appendleft(results)
        logger.info("Caching pending batch of jobs in temporary storage.")

    #Get unretrieved results from pool temporary cache and retrieve them. The method stores all results retrieved in a pool results queue and returns all unretrieved results to that point to the user.
    def get_pool_results(self):
        results = []
        while len(self.pool_cache):
            logger.info("Unretrieved results in pool cache: {} batches. Attempting to retrieve a batch.".format(len(self.pool_cache)))
            result = self.pool_cache.pop()
            if isinstance(result, list): #if any result is a list (if target_method does not use positional args)
                batch = []
                for entry in result:
                    try:
                        entry = entry.get()
                        batch.append(entry)
                    except Exception as e:
                        logger.warning("Result could not be retrieved; Pool Batch ID: {}".format(self.pool_batch_id))
                        logger.error("Specific cause for failure: {}".format(e))
                result = batch
            else:
                try:
                    result = result.get()
                    logger.info("Result successfully retrieved for Pool Batch ID: {}".format(self.pool_batch_id))
                except Exception as e:
                    logger.warning("Result could not be retrieved; Pool Batch ID: {}".format(self.pool_batch_id))
                    logger.error("Specific cause for failure: {}".format(e))
            result = [result, "Pool Batch ID: {}".format(self.pool_batch_id)]
            results.append(result)
            self.pool_batch_id += 1
            logger.info("Appending result to pool results queue.")
            self.pool_results.appendleft(result)
        logger.info("All retrieved results returned; {} batches retrieved.".format(len(results)))
        return results

    #Check process list for dead processes
    def clean_process_list(self):
        logger.info("Checking for dead or orphaned processes.")
        while len(self.processes) > 0:
            process = self.processes.pop()
            if process.is_alive() is not True:
                logger.info("{} is unresponsive; terminating process.".format(process.name))
                if process is not None:
                    process.terminate()
            else:
                self.processes.appendleft(process)

    #Worker method which puts results from a target method into a queue, if any exist. Self-terminates on completion.
    def worker(self, args, **kwargs):
        worker_name = multiprocessing.current_process().name
        if self.included_logger:
            logging_socket = tcp_log_socket.local_logging_socket(worker_name)
            logger = logging_socket.logger
        else:
            logger = logging.getLogger(worker_name)
        logger.info("Running process {}; waiting for results.".format(worker_name))
        print("kwargs: {}".format(kwargs))
        if self.target_method_no_args:
            results = self.target_method(**kwargs)
        elif not isinstance(args, list):
            results = self.target_method(args, **kwargs)
        else:
            results = self.target_method(*args, **kwargs)
        results_queue = self.process_queue
        logger.info("Ran target method, storing results and name of finished process.")
        results_queue.put([results, worker_name])
        logger.info("Process {} completed, exiting.".format(worker_name))
        sys.exit(0)

    #Creates and uses a process to run a job using the assigned target method.
    def use_process(self, args, **kwargs):
        if self.pool:
            logger.warning("""Pool exists; close pool before using individual workers.""")
        else:
            self.clean_process_list()
            if self.process_queue is None:
                self.process_queue = multiprocessing.Queue()
            process = multiprocessing.Process(target=self.worker, args=(args,), kwargs=kwargs)
            logger.info("Created process; process name is {}".format(process.name))
            self.processes.append(process)
            process.start()
            logger.info("Process {} started.".format(process.name))

    #Dump the results from worker processes to a sorted deque. Return the results as well.
    def get_process_results(self):
        results = []
        if self.process_queue is None:
            logging.info("No worker results queue; use a process to retrieve results.")
        else:
            while self.process_queue.qsize() > 0:
                logging.info("Worker results queue is not empty: {} entries. Getting result from queue.".format(self.process_queue.qsize()))
                result = self.process_queue.get()
                results.append(result)
                logging.info("Storing result to controller process results queue.")
                self.process_results.appendleft(result)
        logging.info("Worker results queue is empty, returning retrieved results.")
        return results

    #Waits for workers to finish pending jobs and signals them to exit. If the included test logger is used, the logger is closed and its process is killed.
    def quit(self):
        if len(self.processes):
            self.clean_process_list()
        if self.pool is not None:
            self.pool.close()
        if self.included_logger:
            kill_included_logger() #Reference to global (module-level) method which terminates the included test logger

    #Clears the controller as well as signaling all pending jobs and workers to exit
    def clear(self):
        self.quit()
        self = None

    #Quick cleanup called in the event of interruptions or unexpected terminations. Pending jobs and results will be lost!
    def exit(self, signal, frame):
        if len(self.processes):
            for process in self.processes:
                process.terminate()
        if self.pool is not None:
            self.pool.terminate()
        if self.included_logger:
            kill_included_logger() #Reference to global (module_level) method
