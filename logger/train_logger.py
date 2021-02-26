"""
Logs training metrics and metadata to visualize on tensorboard.
Inherits BaseLogger class.
"""

from time import time
from logger.base_logger import BaseLogger


class AverageMeter(object):
    """
    Class which computes and stores the average and current value.
    Adapted from: https://github.com/pytorch/examples/blob/master/imagenet/main.py
    Attributes
    ----------
    avg : float
        Average value
    val : float
        Current value
    sum : float
        Sum of values
    count : float
        Number of values
    Methods
    -------
    reset():
        Reinitializes the class object
    update(val, n):
        Updates attributes with new value
    """

    def __init__(self):
        self.avg = 0
        self.val = 0
        self.sum = 0
        self.count = 0

    def reset(self):
        """Reinitializes the class object."""
        self.__init__()

    def update(self, val, n=1):
        """
        Updates attributes with new value.
        Parameters
        ----------
        val : float
            New value
        n : int
            Number of values to update
        """
        self.val = val
        self.sum += val * n
        self.count += n
        self.avg = self.sum / self.count


class TrainLogger(BaseLogger):
    """
    Class for logging training info to the console and saving model parameters to disk.
    In inherits from BaseLogger.
    Attruibutes:
        iter_start_time (time): Records the start time of each iteration
        epoch_start_time (time): Records the start time of each epoch
        steps_per_print (int): Number of iterations between metrics are logged and printed
        num_epochs (int): Total number of epochs to train
    Methods:
        log_hparams(args): Log all the hyper parameters in tensorboard
        log_iter(loss_dict={}): Log results from a training iteration
        log_metrics(metrics): Log scalar metrics from training
        start_iter(): Log info for start of an iteration
        end_iter(): Log info for end of an iteration
        start_epoch(): Log info for start of an epoch
        end_epoch(metrics): Log info for end of an epoch. Save model parameters and update learning rate.
        is_finished_training(): Return True if finished training, otherwise return False.
    """

    def __init__(self, args, dataset_len):
        super(TrainLogger, self).__init__(args, dataset_len)
        """
        Args:
            args (Namespace): Program arguments
            dataset_len (int): Number of samples in dataset
        """
        self.iter_start_time = None
        self.epoch_start_time = None
        self.steps_per_print = args.steps_per_print
        self.num_epochs = args.num_epochs

    def log_hparams(self, args):
        """
        Log all the hyper parameters in tensorboard.
        Args:
            args (Namespace): Program arguments
        """
        hparams = {}
        args_dict = vars(args)
        for key in args_dict:
            hparams.update({'hparams/' + key: args_dict[key]})

        self._log_text(hparams)

    def log_iter(self, loss_dict={}):
        """
        Log results from a training iteration.
        Args:
            loss_dict (dict): str to scalar dictionary of losses
        """
        if not hasattr(self, 'loss_meters'):
            self.loss_meters = {loss_name: AverageMeter()
                                for loss_name in loss_dict.keys()}
        for loss_name, meter in self.loss_meters.items():
            meter.update(loss_dict[loss_name], self.batch_size)

        # Periodically write to the log and TensorBoard
        if self.iter % self.steps_per_print == 0:
            # Write a header for the log entry
            avg_time = (time() - self.iter_start_time) / self.batch_size
            message = '(epoch: %d, iter: %d, time: %.3f) ' % (
                self.epoch, self.iter, avg_time)
            for loss_name, meter in self.loss_meters.items():
                message += '%s: %.3f ' % (loss_name, meter.avg)

            # Write all errors as scalars to the graph
            self._log_scalars(
                {loss_name: meter.avg for loss_name, meter in self.loss_meters.items()}, print_to_stdout=False)

            for _, meter in self.loss_meters.items():
                meter.reset()

            # write to .log file
            self.write(message)

    def log_metrics(self, metrics):
        """
        Logs scalar metrics from training.
        Args:
            metrics (dict): str to scalar dictionary containing metrics such as losses to log
        """
        self._log_scalars(metrics)

    def start_iter(self):
        """Log info for start of an iteration."""
        self.iter_start_time = time()

    def end_iter(self):
        """Log info for end of an iteration."""
        self.iter += self.batch_size
        self.global_step += self.batch_size

    def start_epoch(self):
        """Log info for start of an epoch."""
        self.epoch_start_time = time()
        self.iter = 0
        self.write('[start of epoch {}]'.format(self.epoch))

    def end_epoch(self, metrics=None):
        """
        Log info for end of an epoch.
        Args:
            metrics (dict): str to scalar dictionary of metric values.
        """
        self.write('[end of epoch {}/{}, epoch time: {:.2g}]'.format(
            self.epoch, self.num_epochs, time() - self.epoch_start_time))
        if metrics:
            self._log_scalars(metrics)
        self.epoch += 1

    def is_finished_training(self):
        """Return True if finished training, otherwise return False."""
        return 0 < self.num_epochs < self.epoch
