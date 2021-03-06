# process_controller
This Python module spawns new processes for other Python modules and controls those processes. "Control" includes job and queue handling, communication of results, and cleanup.  The Python _multiprocessing_ package is primarily used, with the _subprocess_ package used for an optional test logger.


## Compatibility
The module was tested using Windows and Ubuntu (Debian/Linux). Unix compatibility is not guaranteed.


## Installation
### Required Packages/Software
* [Python](https://www.python.org/) 3.6 or greater
* [pip](https://www.python.org/)


### Optional Packages/Software
* [python-json-logger](https://github.com/madzak/python-json-logger) by madzak; use only if the included logging server is intended to be used. This is a third-party module which handles json-formatted logs.


### Setup
1. (_Optional_) If using the included logger, install [python-json-logger](https://github.com/madzak/python-json-logger) through pip:
    > pip install python-json-logger

2. Clone the repository to your machine using git:
    >git clone https://github.com/will-huynh/process_controller.git

3. Go to the cloned directory on your local machine and check for the latest version using git:
    >Navigate to the cloned process_controller folder

    >git branch master

    >git pull


## Using the Module
The _process_controller_ module was designed to be used by other modules. It is primarily invoked through other Python modules but can also be used through the Python interactive shell. The module by default uses the included test logging socket and server modules, though the module is pre-configured to make use of the user's choice of logger if the optional logger is not used.


### Getting Started

For the provided examples, a module with a test function will be used. The test function is a simple two-argument division function configured to run with the optional test logger.

    > import test_function

Use of the _test_function_ module is very simple:

    > test_function.test(4,2)

    > Example Output: Quotient is 2.

To begin, import the module:

    > import process_controller

Next, create a ProcessController object with the desired method to be used. __NOTE: Methods used must be picklable in the object scope (due to the behavior of _multiprocessing_ and _subprocess_).__

    > pc = process_controller.ProcessController(test_function.test)

To disable the included test logger:

    > pc = process_controller.ProcessController(test_function.test, included_logger=False)
    
By default, the test logging server names its file "test_log". Currently, a global option in the logging server module is included to change this name. To change the name of the log file currently, go to the "tcp_log_server.py" file and change the "log_name" attribute for the overall module. Future changes will add more complete configuration capability from the parent module.


### Using a Pool of Worker Processes

A simple way to complete jobs (or the task the user wishes to complete) with new processes is to assign those jobs to a pool. By design, the creation of a pool is left to the user to avoid creating unnecessary overhead.

To begin, use __ProcessController__._create_new_pool(num_processes)_ to create a pool of worker processes. An example is as follows:

    > pc.create_new_pool(2) #Creates a pool with 2 worker processes

It is intentionally designed that only one pool can be created at a time for each object of the __ProcessController__ class. There should not be a practical need to create multiple pools for one assigned method, seeing that more or less processes can be dynamically assigned as needed, and the use of multiple pools would create unnecessary overhead and unforeseen conflicts.

Once a pool is created, assign the pool a batch of jobs with the __ProcessController__._use_pool([job_1,job_2,...])_ method to run the user's assigned method. In this scope, jobs are the required input (ie: arguments) for the user's assigned method:

    > pc.use_pool([[4,2],[12,3]])

    > Example Output: "[2, 4]"

#### Retrieving Results From a Pool of Worker Processes

The _use_pool()_ method does not immediately return results. This is designed to allow use of pools to be non-blocking. Instead, every call of the _use_pool()_ method caches its pending batch of jobs in the _pool_cache_ queue. To retrieve the results of all pending jobs, the user can call the __ProcessController__._get_pool_results()_ method:

    > pc.get_pool_results()

    > Example Output: [[4,2], 'Pool_Batch_ID: 0']

All retrieved results will be deposited in the __ProcessController__._pool_results_ queue in order of job completion and returned to the user. To get a batch of results, use the __collections__._deque.pop()_ method. For example: 

    > pc.pool_results.pop()

    > Example Output: [[4,2], 'Pool_Batch_ID: 0']

Each entry in _pool_results_ contains both the results for the batch of jobs and the ID of the batch for those jobs. If an exception is thrown for a batch of jobs, the exception information will be logged and the information can be retrieved by the user. To retrieve the information, use the __multiprocessing__._pool.AsyncResult.get()_ method:

    > batch = pc.pool_results.pop()

    > batch[0].get()

    > ...Some exception information...

If the user wishes to have finer control over the method in which they recieve results, the __multiprocessing__._pool.AsyncResult.get()_ can be used to retrieve individual batches of results in the order that they are deposited. Using the __ProcessController__._pool_cache_ queue:

    > batch = pc.pool_cache.pop()

    > batch[0].get()

    > Example Output: [4,2]


### Creating Individual Worker Processes

The pool method will be the simpler solution in most cases. However, in situations where the user needs to create individual processes or where the overhead from using/creating a pool needs to be mitigated, the __ProcessController__ class contains the _use_process()_ method to create individual processes:

    > pc.use_process([5,3])

#### Retrieving Results From Individual Worker Processes

Each run of the _use_process_ deposits its results in the __ProcessController__._results_queue_ __multiprocessing__._Queue()_ object as the format __[<Worker_Result>, <Worker_Name>]__. To retrieve the results, the user can either use the controller's class method for automatically returning and caching results or retrieve the results directly from the worker _process_queue_.

To return all pending (unretrieved) results as well as cache them in the __ProcessController__._process_results_ deque, use the method, __ProcessController__._get_process_results_. This method will return all pending results up to the method call as well as assign them to a results deque, _process_results_. An example is as follows:

    > pc.use_process([6,2])

    > pc.get_process_results()

    > [[3.0, 'Process-1']]

A simple way to return results from the __ProcessController__._process_results_ deque for the above example is as follows (read more at the official Python docs [here](https://docs.python.org/3.6/library/collections.html?highlight=collections#collections.deque)):

    > pc.process_results.pop()

    > [[3.0, 'Process-1']]

Results can also be directly retrieved from the __ProcessController__._process_queue_ results queue. While it is recommended to use the controller's native method for retrieving results, users desiring finer manual control can retrieve results one at a time from the results queue using:

    > pc.process_queue.get()

Using __multiprocessing__._Queue.get()_ will retrieve worker results one at a time, starting with processes that have finished first. For control, the number of entries in the queue can be found using __multiprocessing.Queue__._qsize()_. This number is not accurate at every instant however; for more information, read the official Python documentation [here](https://docs.python.org/3.6/library/multiprocessing.html#multiprocessing.Queue).

### Terminating/Cleaning the Controller

The __ProcessController__ class includes three termination methods:  __ProcessController__._quit()_, __ProcessController__._clear()_, and __ProcessController__._exit()_. These handle intentional and unintentional termination, can be called by the user, and are handled automatically with exit code and signals.

The _quit()_ method waits for all pending jobs and workers to finish and signals them to exit. If the included logger is used, the process and window for the logger is closed. Regular module termination (intentional exit) is handled using the _quit()_ method.

The _clear()_ method behaves similarly to the _quit()_ method, except that it also clears the controller from memory. The method was implemented to allow the user the choice to fully terminate the controller if the stored results are no longer important.

In the event of unexpected termination, the _exit()_ method is used. Use of _exit()_ causes forceful module termination, shutting down all related child processes. __This will cause a loss of all pending jobs and results__. This method can be called by the user but is mainly called by signal handlers when unexpected terminations or interrupts occur.

## Reference

### _string_ process_controller.__log_server_dir__ = _tcp_log_server.py_
    
> The directory of the included test logging server. This can be a relative or absolute directory.

### _int_ process_controller.__log_server_pid__ = _None_

> The process id of the included test logging server if it used. 

### _class_ process_controller.__ProcessController__(_target_method_, _included_logger=True_)
    
> The controller class which spawns and handles worker processes and communication. _target_method_ is the method that the class uses 
    to complete jobs with associated worker processes. _included_logger_ specifies whether to use the included test logger; by default       the value is _True_.

#### __target_method__
  
> The method used to complete jobs with worker processes.

#### __pool__
    
> Pool of worker processes. _None_ by default; spawned with _create_new_pool_.

__pool_cache__
    
> Temporary cache of pending pool results.

__pool_results__
    
> __collections__._deque_ which stores pool results retrieved with _get_pool_results_.

__processes__
    
> __collections__._deque_ which tracks active and inactive processes.

__process_queue__
    
> A __multiprocessing__._Queue_ which is used for individual worker process communication.

__process_results__
    
> __collections__._deque_ which stores individual process results.

__create_new_pool__(_num_processes_)
    
> Creates a new pool of worker processes. _num_processes_ is the number of processes to assign to the pool; the user should be             aware of the number of cores available to their system.

__use_pool__(_jobs_)
    
> Uses a pool of worker processes to complete batches of jobs. _jobs_ specifies the total input required for the pool of worker processes to run the specified target method. For a method with arguments, provide a list of the arguments for each run of the target method; if the target method requires multiple arguments, provide a nested list with the inner list containing the arguments for one job. For a method without required arguments, use any filler argument for a single run of that method. For example:

    > test_function.test(4,2); expected result: 2.

    > test_function.test(6,2); expected result: 3.

    > pc.use_pool([[4,2],[6,2]]); expected result: [2, 3]
 
 __get_pool_results__()
 
 > Retrieves pending results from batches of jobs completed through a pool. Results are deposited in the _process_results_ deque in the order of completed jobs. If a job cannot be retrieved, the cause of the interruption or exception will be logged for the user.
 
 __clean_process_list__()
 
 > Checks the _processes_ list for inactive or dead processes and terminates them.
 
 __worker__(_args, **kwargs_)

> This method is not typically called on its own, but through another method such as _use_process_ to give it multiprocessing capability. The method is used for operation of the worker process. It is responsible for running the specified target method and depositing results to the main process through the _process_queue_ __multiprocessing__._Queue_. Keyworded arguments can also be passed.

__use_process__(_args, **kwargs_)

> Spawns new __individual__ worker processes and runs a check for inactive or orphaned processes. The main difference between this method and _use_pool_ is that while _use_pool_ completes a batch of given jobs by automatically assigning workflow to all processes in a __multiprocessing__._Pool_, _use_process_ leaves the task of assigning workflow to the user. An example is below:

    > test_function.test(4,2); expected result: 2.
    
    > pc.use_process([4,2]); expected result: 2

> This method also accepts target methods with no required positional arguments. To use these methods, simply provide any filler argument instead of regular required arguments.

__get_process_results__()

> Retrieves results cached in the _process_queue_ _Queue_ up to that point and returns them to the user. The results are returned in two ways: results up to the point of method call are deposited in the _process_results_ __collections__._deque_ and returned to the user.

__quit__()

> Waits for any workers to finish any pending jobs and signals them to exit. If a pool is created, it is signaled to close. If the included test logger is used, the logger is closed and its process is killed. This is the cleanest termination method and is closed on normal exits and intentional interrupts.

__clear__()

> Calls _quit_ and clears the process controller.

__exit__()

> Exit method used in the case of unexpected exits, interrupts, and termination. This is a quick cleanup method that will kill all worker processes regardless of any pending jobs. Any pools or individual workers will be terminated immediately. If the included test logger is used, it will be closed and its process will be killed.

