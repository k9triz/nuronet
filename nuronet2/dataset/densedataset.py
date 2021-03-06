# -*- coding: utf-8 -*-
"""
Created on Wed Apr 20 09:17:58 2016

@author: Evander
"""

import numpy
import itertools
import threading
from sklearn.cross_validation import KFold


class IndexIterator(object):
    """
    Base class for an iterator that yields the next batch of array indexes.
    Very useful for model's fit_dataset / fit_generator function which 
    uses this to progressively iterate over its batches.
    
    DenseDataset is a child of this class
    """
    def __init__(self, n, batch_size=32, shuffle=False, seed=None):
        if(batch_size > n):
            raise ValueError("The batch_size: {},".format(batch_size) + \
                   " is too large compared to the dataset size: {}".format(n))
        self._n = n
        self.batch_size = batch_size
        self.shuffle = shuffle
        self.batch_idx = 0
        self.batches_seen = 0
        self.lock = threading.Lock()
        self.index_generator = self.index_flow(batch_size, shuffle, seed)
        
    @property
    def n(self):
        return self._n

    @n.setter
    def n(self, value):
        if(self.batch_size > value):
            raise ValueError("The batch_size: {}, ".format(self.batch_size) + \
                   "is too large compared to the dataset size: {}".format(value))
        with self.lock:
            self._n = value


    def reset(self):
        self.batch_idx = 0
        
    def index_flow(self, batch_size, shuffle, seed):
        self.reset()
        while(1):
            if(seed is not None):
                numpy.random.seed(seed + self.batches_seen)
            if(self.batch_idx == 0):
                idx_array = numpy.arange(self.n)
                if(shuffle):
                    idx_array = numpy.random.permutation(self.n)
            
            current_idx = (self.batch_idx * batch_size) % self.n
            if(self.n >= current_idx + batch_size):
                current_batch_size = batch_size
                self.batch_idx += 1
            else:
                current_batch_size = self.n - current_idx
                self.batch_idx = 0
            self.batches_seen += 1
            yield (idx_array[current_idx: current_idx + current_batch_size],
                   current_idx, current_batch_size)

    def __iter__(self):
        return self
        
    def __next__(self, *args, **kwargs):
        return self.next(*args, **kwargs)
        
    def __call__(self, *args, **kwargs):
        return self.next(*args, **kwargs)

    def next(self):
        with self.lock:
            index_array, current_index, current_batch_size = next(self.index_generator)
        print index_array, current_index, current_batch_size
        #return index_array

class DenseDataset(IndexIterator):
    """
    An abstract class representing a dataset
    which can be used to train various ML models
    efficiently.
    """
    def __init__(self, x, y=None, x_test=None, y_test=None,
                 batch_size=1, validation=0., shuffle=True, seed=None):
        if(y is not None and (x.shape[0] != y.shape[0])):
            raise ValueError("x and y must have the same number of entries")
        self.x = x
        self.y = y
        self.x_test = x_test
        self.y_test = y_test
        self.train_indices = numpy.arange(self.x.shape[0])
        self.valid_indices = []
        
        IndexIterator.__init__(self, x.shape[0], batch_size, shuffle, seed)
        
        if(validation is not None and validation > 0.):
            self.validation = validation
            self.valid_iterator = self.make_validation_iterator(self.x.shape[0])
    @property
    def x_valid(self):
        return self.x[self.valid_indices]
        
    @property
    def y_valid(self):
        return self.y[self.valid_indices]

    def make_validation_splits(self):
        if(not hasattr(self, 'validation')):
            return
        train_indices, valid_indices = next(self.valid_iterator)
        self.train_indices = train_indices
        self.valid_indices = valid_indices
        self.n = self.train_indices.shape[0]
        self.reset()

    def make_validation_iterator(self, n):
        n_folds = round(1. / self.validation)
        kfold = KFold(n, n_folds)
        return itertools.cycle(kfold)
    
    def next(self):
        with self.lock:
            index_array, current_index, current_batch_size = next(self.index_generator)
        batch_x = self.x[index_array]
        if(self.y is None):
            return batch_x
        return batch_x, self.y[index_array]

    def index_flow(self, batch_size, shuffle, seed):
        self.reset()
        while(1):
            if(seed is not None):
                numpy.random.seed(seed + self.batches_seen)
            if(self.batch_idx == 0):
                idx_array = self.train_indices
                if(shuffle):
                    idx_array = numpy.random.permutation(self.train_indices)
            
            current_idx = (self.batch_idx * batch_size) % self.n
            if(self.n >= current_idx + batch_size):
                current_batch_size = batch_size
                self.batch_idx += 1
            else:
                current_batch_size = self.n - current_idx
                self.batch_idx = 0
            self.batches_seen += 1
            yield (idx_array[current_idx: current_idx + current_batch_size],
                   current_idx, current_batch_size)
        

if __name__ == "__main__":
    N = 10
    x = numpy.arange(N).reshape((N, 1))
    y = numpy.arange(N)
    g = DenseDataset(x, y, shuffle=False, validation=0.2, batch_size=2)
