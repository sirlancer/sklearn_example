"""
author:lancer
Functions for downloading and reading MNIST data.
"""
import gzip
import os
import urllib.request
import numpy as np


SOURCE_URL = "http://yann.lecun.com/exdb/mnist/"

def maybe_download(filename, work_directory):
    """Download the data from Yann's website, unless it's already here."""

    if not os.path.exists(work_directory):
        os.mkdir(work_directory)

    filepath = os.path.join(work_directory, filename)
    if not os.path.exists(filepath):
        filepath, _ = urllib.request.urlretrieve(SOURCE_URL+filename, filepath)
        statinfo = os.stat(filepath)

        print('Successfully downloaded ', filename, statinfo.st_size, 'bytes.')
    return filepath

def _read32(bytestream):
    """Read 4 bytes"""
    dt = np.dtype(np.uint32).newbyteorder('>')
    return np.frombuffer(bytestream.read(4), dtype=dt)

def extract_image(filename):
    """Extract the images into a 4D uint8 numpy array [index, y, x, depth]"""
    print('Extracting ', filename)
    with gzip.open(filename) as bytestream:
        magic = _read32(bytestream)
        if magic != 2051:
            raise ValueError("Invalid magic number %d in MNIST image file:%s" % (magic, filename))
        num_images = _read32(bytestream)
        rows = _read32(bytestream)
        cols = _read32(bytestream)

        buf = bytestream.read(rows[0] * cols[0] * num_images[0])
        data = np.frombuffer(buf, dtype=np.uint8)
        data = data.reshape(num_images[0], rows[0], cols[0], 1)
        return data

def dense_to_one_hot(labels_dense, num_classes=10):
    """Convert class labels from scalars to one-hot vectors."""
    num_labels = labels_dense.shape[0]
    offset_index = np.arange(num_labels)*num_classes
    labels_one_hot = np.zeros([num_labels, num_classes])

    labels_one_hot.flat[offset_index + labels_dense.ravel()] = 1
    return labels_one_hot

def extract_labels(filename, one_hot=True):
    """Extract the labels into a 1D uint8 numpy array [index]."""
    print('Extracting ',filename)
    with gzip.open(filename) as bytestream:
        magic = _read32(bytestream)
        if magic != 2049:
            raise ValueError("Invalid magic number %d in MNIST label file:%s" %(magic, filename))
        num_items = _read32(bytestream)

        buf = bytestream.read(num_items[0])
        labels = np.frombuffer(buf, dtype=np.uint8)
        if one_hot:
            return dense_to_one_hot(labels)
        return labels

class DataSet(object):
    def __init__(self, images, labels):
        assert images.shape[0] == labels.shape[0],("images.shape:%s, labels.shape:%s "%(images.shape, labels.shape))

        self._num_examples = images.shape[0]

        assert images.shape[3] == 1

        n = int(images.shape[0])
        m = int(images.shape[1] * images.shape[2])
        images = images.reshape(n,m)
        images = images.astype(np.float32)
        images = np.multiply(images, 1./255.0)

        shuffle_index = np.arange(self._num_examples)
        np.random.shuffle(shuffle_index)
        self._images = images[shuffle_index]
        self._labels = labels[shuffle_index]

        self._epochs_completed = 0
        self._index_in_epoch = 0

    @property
    def images(self):
        return self._images

    @property
    def labels(self):
        return self._labels

    @property
    def num_examples(self):
        return self._num_examples

    @property
    def epochs_completed(self):
        return self._epochs_completed

    def next_batch(self, batch_size):
        """Return the next 'batch_size' examples from this data set."""
        assert batch_size <= self._num_examples,("batch_size(%s) bigger than data size(%s)"%(batch_size, self._num_examples))
        start = self._index_in_epoch
        self._index_in_epoch += batch_size

        if self._index_in_epoch > self._num_examples:

            self._epochs_completed += 1

            shuffle_index = np.arange(self._num_examples)
            np.random.shuffle(shuffle_index)

            self._images = self._images[shuffle_index]
            self._labels = self._labels[shuffle_index]

            start = 0
            self._index_in_epoch = batch_size

        end = self._index_in_epoch

        return self._images[start:end], self._labels[start:end]



def read_data_sets(train_dir, one_hot=True):
    class DataSets(object):
        pass

    TRAIN_IMAGES = 'train-images-idx3-ubyte.gz'
    TRAIN_LABELS = 'train-labels-idx1-ubyte.gz'
    TEST_IMAGES = 't10k-images-idx3-ubyte.gz'
    TEST_LABELS = 't10k-labels-idx1-ubyte.gz'

    VALIDATION_SIZE = 5000

    local_file = maybe_download(TRAIN_IMAGES, train_dir)
    train_images = extract_image(local_file)

    local_file = maybe_download(TRAIN_LABELS, train_dir)
    train_labels = extract_labels(local_file, one_hot=one_hot)

    local_file = maybe_download(TEST_IMAGES, train_dir)
    test_images = extract_image(local_file)

    local_file = maybe_download(TEST_LABELS, train_dir)
    test_labels = extract_labels(local_file, one_hot=one_hot)

    validation_images = train_images[:VALIDATION_SIZE]
    validation_labels = train_labels[:VALIDATION_SIZE]

    train_images = train_images[VALIDATION_SIZE:]
    train_labels = train_labels[VALIDATION_SIZE:]

    data_sets = DataSets()
    data_sets.train = DataSet(train_images, train_labels)
    data_sets.test = DataSet(test_images, test_labels)
    data_sets.validation = DataSet(validation_images, validation_labels)


    return data_sets
