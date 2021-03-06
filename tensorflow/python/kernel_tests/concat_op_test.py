"""Functional tests for Concat Op."""
import tensorflow.python.platform

import numpy as np
import tensorflow as tf


class ConcatOpTest(tf.test.TestCase):

  def testHStack(self):
    with self.test_session():
      p1 = tf.placeholder(tf.float32, shape=[4, 4])
      p2 = tf.placeholder(tf.float32, shape=[4, 4])
      c = tf.concat(0, [p1, p2])
      params = {
          p1: np.random.rand(4, 4).astype("f"),
          p2: np.random.rand(4, 4).astype("f")
          }
      result = c.eval(feed_dict=params)

    self.assertEqual(result.shape, c.get_shape())
    self.assertAllEqual(result[:4, :], params[p1])
    self.assertAllEqual(result[4:, :], params[p2])

  def testVStack(self):
    with self.test_session():
      p1 = tf.placeholder(tf.float32, shape=[4, 4])
      p2 = tf.placeholder(tf.float32, shape=[4, 4])
      c = tf.concat(1, [p1, p2])
      params = {
          p1: np.random.rand(4, 4).astype("f"),
          p2: np.random.rand(4, 4).astype("f")
          }
      result = c.eval(feed_dict=params)

    self.assertEqual(result.shape, c.get_shape())
    self.assertAllEqual(result[:, :4], params[p1])
    self.assertAllEqual(result[:, 4:], params[p2])

  def testInt32GPU(self):
    with self.test_session(use_gpu=True):
      p1 = np.random.rand(2, 3).astype("i")
      p2 = np.random.rand(2, 3).astype("i")
      x1 = tf.constant(p1)
      x2 = tf.constant(p2)
      c = tf.concat(0, [x1, x2])
      result = c.eval()
    self.assertAllEqual(result[:2, :], p1)
    self.assertAllEqual(result[2:, :], p2)

  def testRefType(self):
    with self.test_session():
      p1 = tf.placeholder(tf.float32_ref, shape=[4, 4])
      p2 = tf.placeholder(tf.float32_ref, shape=[4, 4])
      c = tf.concat(0, [p1, p2])
      params = {
          p1: np.random.rand(4, 4).astype("f"),
          p2: np.random.rand(4, 4).astype("f")
          }
      result = c.eval(feed_dict=params)

    self.assertEqual(result.shape, c.get_shape())
    self.assertAllEqual(result[:4, :], params[p1])
    self.assertAllEqual(result[4:, :], params[p2])

  def _testRandom(self, dtype, use_gpu=False):
    # Random dims of rank 5
    shape = np.random.randint(1, 5, size=5)
    # Random number of tensors, but always > 1.
    num_tensors = np.random.randint(2, 10)
    # Random dim to concat on
    concat_dim = np.random.randint(5)
    params = {}
    with self.test_session(use_gpu=use_gpu):
      p = []
      for i in np.arange(num_tensors):
        input_shape = shape
        input_shape[concat_dim] = np.random.randint(1, 5)
        placeholder = tf.placeholder(dtype, shape=input_shape)
        p.append(placeholder)

        t = dtype.as_numpy_dtype
        params[placeholder] = np.random.rand(*input_shape).astype(t)

      c = tf.concat(concat_dim, p)
      result = c.eval(feed_dict=params)

    self.assertEqual(result.shape, c.get_shape())
    cur_offset = 0

    for i in np.arange(num_tensors):
      # The index into the result is the ':' along all dimensions
      # except the concat_dim. slice(0, size) is used for ':', and
      # a list of slices is used to index into result.
      ind = [slice(0, params[p[i]].shape[j]) for j in np.arange(5)]
      ind[concat_dim] = slice(cur_offset,
                              cur_offset + params[p[i]].shape[concat_dim])
      cur_offset += params[p[i]].shape[concat_dim]
      self.assertAllEqual(result[ind], params[p[i]])

  def testRandom(self):
    self._testRandom(tf.float32)
    self._testRandom(tf.int16)
    self._testRandom(tf.int32, use_gpu=True)
    # Note that the following does not work since bfloat16 is not supported in
    # numpy.
    # self._testRandom(tf.bfloat16)

  def _testGradientsSimple(self, use_gpu):
    with self.test_session(use_gpu=use_gpu):
      inp = []
      inp_tensors = []
      for x in [1, 2, 6]:
        shape = [10, x, 2]
        t = np.random.rand(*shape).astype("f")
        inp.append(t)
        inp_tensors.append(
            tf.constant([float(y) for y in t.flatten()],
                                 shape=shape, dtype=tf.float32))
      c = tf.concat(1, inp_tensors)
      output_shape = [10, 9, 2]
      grad_inp = np.random.rand(*output_shape).astype("f")
      grad_tensor = tf.constant([float(x) for x in grad_inp.flatten()],
                                         shape=output_shape)
      grad = tf.gradients([c], inp_tensors, [grad_tensor])
      concated_grad = tf.concat(1, grad)
      result = concated_grad.eval()

    self.assertAllEqual(result, grad_inp)

  def testGradientsSimpleAll(self):
    self._testGradientsSimple(use_gpu=False)
    self._testGradientsSimple(use_gpu=True)

  def _testGradientsFirstDim(self, use_gpu):
    with self.test_session(use_gpu=use_gpu):
      inp = []
      inp_tensors = []
      for x in [1, 2, 6]:
        shape = [x, 10, 2]
        t = np.random.rand(*shape).astype("f")
        inp.append(t)
        inp_tensors.append(
            tf.constant([float(y) for y in t.flatten()],
                                 shape=shape, dtype=tf.float32))
      c = tf.concat(0, inp_tensors)
      output_shape = [9, 10, 2]
      grad_inp = np.random.rand(*output_shape).astype("f")
      grad_tensor = tf.constant([float(x) for x in grad_inp.flatten()],
                                         shape=output_shape)
      grad = tf.gradients([c], inp_tensors, [grad_tensor])
      concated_grad = tf.concat(0, grad)
      result = concated_grad.eval()

    self.assertAllEqual(result, grad_inp)

  def testGradientsFirstDimAll(self):
    self._testGradientsFirstDim(use_gpu=False)
    self._testGradientsFirstDim(use_gpu=True)

  def _testGradientsLastDim(self, use_gpu):
    with self.test_session(use_gpu=use_gpu):
      inp = []
      inp_tensors = []
      for x in [1, 2, 6]:
        shape = [10, 2, x]
        t = np.random.rand(*shape).astype("f")
        inp.append(t)
        inp_tensors.append(
            tf.constant([float(y) for y in t.flatten()],
                                 shape=shape, dtype=tf.float32))
      c = tf.concat(2, inp_tensors)
      output_shape = [10, 2, 9]
      grad_inp = np.random.rand(*output_shape).astype("f")
      grad_tensor = tf.constant([float(x) for x in grad_inp.flatten()],
                                         shape=output_shape)
      grad = tf.gradients([c], inp_tensors, [grad_tensor])
      concated_grad = tf.concat(2, grad)
      result = concated_grad.eval()

    self.assertAllEqual(result, grad_inp)

  def testGradientsLastDimAll(self):
    self._testGradientsLastDim(use_gpu=False)
    self._testGradientsLastDim(use_gpu=True)

  def _RunAndVerifyGradientsRandom(self, use_gpu):
    # Random dims of rank 5
    input_shape = np.random.randint(1, 5, size=5)
    # Random number of tensors
    num_tensors = np.random.randint(1, 10)
    # Random dim to concat on
    concat_dim = np.random.randint(5)
    concat_dim_sizes = np.random.randint(1, 5, size=num_tensors)
    with self.test_session(use_gpu=use_gpu):
      inp = []
      inp_tensors = []
      for x in concat_dim_sizes:
        shape = input_shape
        shape[concat_dim] = x
        t = np.random.rand(*shape).astype("f")
        inp.append(t)
        inp_tensors.append(
            tf.constant([float(y) for y in t.flatten()],
                                 shape=shape, dtype=tf.float32))
      c = tf.concat(concat_dim, inp_tensors)
      output_shape = input_shape
      output_shape[concat_dim] = concat_dim_sizes.sum()
      grad_inp = np.random.rand(*output_shape).astype("f")
      grad_tensor = tf.constant([float(x) for x in grad_inp.flatten()],
                                         shape=output_shape)
      grad = tf.gradients([c], inp_tensors, [grad_tensor])
      concated_grad = tf.concat(concat_dim, grad)
      result = concated_grad.eval()

    self.assertAllEqual(result, grad_inp)

  def testGradientsRandom(self):
    for _ in range(5):
      self._RunAndVerifyGradientsRandom(use_gpu=False)
      self._RunAndVerifyGradientsRandom(use_gpu=True)

  def testShapeError(self):
    # Rank doesn't match.
    with self.assertRaises(ValueError):
      tf.concat(1, [tf.constant(10.0, shape=[4, 4, 4, 4]),
                           tf.constant(20.0, shape=[4, 4, 4])])

    # Dimensions don't match in a non-concat dim.
    with self.assertRaises(ValueError):
      tf.concat(1, [tf.constant(10.0, shape=[1, 2, 1]),
                           tf.constant(20.0, shape=[3, 2, 1])])

    # concat_dim out of range.
    with self.assertRaises(ValueError):
      tf.concat(3, [tf.constant(10.0, shape=[4, 4, 4]),
                           tf.constant(20.0, shape=[4, 4, 4])])

  def testShapeWithUnknownConcatDim(self):
    p1 = tf.placeholder(tf.float32)
    c1 = tf.constant(10.0, shape=[4, 4, 4, 4])
    p2 = tf.placeholder(tf.float32)
    c2 = tf.constant(20.0, shape=[4, 4, 4, 4])
    dim = tf.placeholder(tf.int32)
    concat = tf.concat(dim, [p1, c1, p2, c2])
    self.assertEqual(4, concat.get_shape().ndims)

    # Rank doesn't match.
    c3 = tf.constant(30.0, shape=[4, 4, 4])
    with self.assertRaises(ValueError):
      tf.concat(dim, [p1, c1, p2, c3])

  def testZeroSize(self):
    # Verify that concat doesn't crash and burn for zero size inputs
    np.random.seed(7)
    for use_gpu in False, True:
      with self.test_session(use_gpu=use_gpu) as sess:
        for shape0 in (), (2,):
          axis = len(shape0)
          for shape1 in (), (3,):
            for n0 in 0, 1, 2:
              for n1 in 0, 1, 2:
                x0 = np.random.randn(*(shape0 + (n0,) + shape1))
                x1 = np.random.randn(*(shape0 + (n1,) + shape1))
                correct = np.concatenate([x0, x1], axis=axis)
                xs = map(tf.constant, [x0, x1])
                c = tf.concat(axis, xs)
                self.assertAllEqual(c.eval(), correct)
                # Check gradients
                dc = np.random.randn(*c.get_shape().as_list())
                dxs = sess.run(tf.gradients(c, xs, dc))
                self.assertAllEqual(dc, np.concatenate(dxs, axis=axis))


if __name__ == "__main__":
  tf.test.main()
