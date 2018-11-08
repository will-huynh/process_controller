# process_controller
This Python module spawns new processes for other Python modules and controls those processes. Control includes job and queue handling, communication of results, and cleanup.  The Python _multiprocessing_ module is primarily used, with the _subprocess_ package used for an optional test logger.

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

> __Example result:__ "Quotient is 2."

To begin, import the module:
> import process_controller

Next, create a ProcessController object with the desired method to be used. __NOTE: Methods used must be picklable in the object scope (due to the behavior of _multiprocessing_ and _subprocess_).__
> pc = process_controller.ProcessController(test_function.test)

To disable the included test logger:
> pc = process_controller.ProcessController(test_function.test, included_logger=False)

### Using a Pool of Worker Processes

A simple way to complete jobs (or the task the user wishes to complete) with new processes is to assign those jobs to a pool. By design, the creation of a pool is left to the user to avoid creating unnecessary overhead.

To begin, use _create_new_pool_ to create a pool of worker processes. An example is as follows:
> pc.create_new_pool(2) #Creates a pool with 2 worker processes

It is intentionally designed that only one pool can be created at a time for each object of the __ProcessController__ class. There should not be a practical need to create multiple pools for one assigned method, seeing that more or less processes can be dynamically assigned as needed, and the use of multiple pools would create unnecessary overhead and unforeseen conflicts.

Once a pool is created, assign the pool a batch of jobs with the _use_pool_ method to run the user's assigned method. In this scope, jobs are the required input (ie: arguments) for the user's assigned method:
> pc.use_pool([[4,2],[12,3]])

>__Example result__:"[2, 4]"

The _use_pool_ method returns results in two ways. Every use of the method returns the immediate results for that batch of jobs upon completion. Objects of the __ProcessController__ class also contain a list of pool results, _pool_results_, as an attribute. Each entry in _pool_results_ contains both the results for the batch of jobs and the ID of the batch for those jobs. For the previous example where the batch was the first batch given:

>print(pc.pool_results)

>[[[2, 4], 'Pool Batch ID: 0']]

### Creating Individual Worker Processes

The pool method will be the simpler solution in most cases. However, in situations where the user needs to create individual processes or where the overhead from using/creating a pool needs to be mitigated, the __ProcessController__ class contains the _use_process_ method to create individual processes.

> pc.use_process([5,3])

Each run of the _use_process_ deposits its results in the _results_queue_ multiprocessing.Queue() object.
