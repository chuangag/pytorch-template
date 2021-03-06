import numpy as np
import torch
from torch.autograd import Variable
from base import BaseTrainer
from visdom import Visdom


class Trainer(BaseTrainer):
    """
    Trainer class

    Note:
        Inherited from BaseTrainer.
        self.optimizer is by default handled by BaseTrainer based on config.
    """
    def __init__(self, model, loss, metrics, resume, config,
                 data_loader, valid_data_loader=None, train_logger=None):
        super(Trainer, self).__init__(model, loss, metrics, resume, config, train_logger)
        self.config = config
        self.batch_size = data_loader.batch_size
        self.data_loader = data_loader
        self.valid_data_loader = valid_data_loader
        self.valid = True if self.valid_data_loader is not None else False
        self.log_step = int(np.sqrt(self.batch_size))
        self.viz = Visdom()
        self.plt_train_loss = None
        self.plt_val_loss = None

    def _to_variable(self, data, target):
        data, target = torch.FloatTensor(data), torch.LongTensor(target)
        data, target = Variable(data), Variable(target)
        if self.with_cuda:
            data, target = data.cuda(), target.cuda()
        return data, target

    def _eval_metrics(self, output, target):
        acc_metrics = np.zeros(len(self.metrics))
        output = output.cpu().data.numpy()
        target = target.cpu().data.numpy()
        output = np.argmax(output, axis=1)
        for i, metric in enumerate(self.metrics):
            acc_metrics[i] += metric(output, target)
        return acc_metrics

    def _train_epoch(self, epoch):
        """
        Training logic for an epoch

        :param epoch: Current training epoch.
        :return: A log that contains all information you want to save.

        Note:
            If you have additional information to record, for example:
                > additional_log = {"x": x, "y": y}
            merge it with log before return. i.e.
                > log = {**log, **additional_log}
                > return log

            The metrics in log must have the key 'metrics'.
        """
        self.model.train()
        if self.with_cuda:
            self.model.cuda()

        total_loss = 0
        total_metrics = np.zeros(len(self.metrics))
        for batch_idx, (data, target) in enumerate(self.data_loader):
            data, target = self._to_variable(data, target)

            self.optimizer.zero_grad()
            output = self.model(data)
            loss = self.loss(output, target)
            loss.backward()
            self.optimizer.step()

            total_loss += loss.data[0]
            total_metrics += self._eval_metrics(output, target)

            if self.verbosity >= 2 and batch_idx % self.log_step == 0:
                self.logger.info('Train Epoch: {} [{}/{} ({:.0f}%)] Loss: {:.6f}'.format(
                    epoch, 
                    batch_idx * self.data_loader.batch_size,
                    len(self.data_loader) * self.data_loader.batch_size,
                    100.0 * batch_idx / len(self.data_loader), 
                    loss.data[0]))
            
            if self.visualize:
                if self.plt_train_loss is None:
                    self.plt_train_loss = self.viz.line(Y=np.array([loss.data[0]]),
                                                        opts=dict(legend=['Training Loss']))
                else:
                    self.viz.line(
                            X=np.array([batch_idx+(epoch-1)*len(self.data_loader)]),
                            Y = np.array([loss.data[0]]),
                            win = self.plt_train_loss,
                            update = 'append',
                            opts=dict(legend=['Training Loss'])
                        )

        log = {
            'loss': total_loss / len(self.data_loader), 
            'metrics': (total_metrics / len(self.data_loader)).tolist()
        }

        if self.valid:
            val_log = self._valid_epoch(epoch)
            log = {**log, **val_log}

        return log

    def _valid_epoch(self,epoch):
        """
        Validate after training an epoch

        :return: A log that contains information about validation

        Note:
            The validation metrics in log must have the key 'val_metrics'.
        """
        self.model.eval()
        total_val_loss = 0
        total_val_metrics = np.zeros(len(self.metrics))
        for batch_idx, (data, target) in enumerate(self.valid_data_loader):
            data, target = self._to_variable(data, target)

            output = self.model(data)
            loss = self.loss(output, target)

            total_val_loss += loss.data[0]
            total_val_metrics += self._eval_metrics(output, target)
        
        if self.visualize:
                if self.plt_val_loss is None:
                    self.plt_val_loss = self.viz.line(Y=np.array([total_val_loss / len(self.valid_data_loader)]),
                                                        opts=dict(legend=['Validation Loss']))
                else:
                    self.viz.line(
                            X=np.array([epoch-1]),
                            Y=np.array([total_val_loss / len(self.valid_data_loader)]),
                            win=self.plt_val_loss,
                            update='append',
                            opts=dict(legend=['Validation Loss'])
                        )

        return {
            'val_loss': total_val_loss / len(self.valid_data_loader), 
            'val_metrics': (total_val_metrics / len(self.valid_data_loader)).tolist()
        }
