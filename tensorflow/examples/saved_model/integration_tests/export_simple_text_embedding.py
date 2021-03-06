# Copyright 2019 The TensorFlow Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ==============================================================================
"""Text embedding model stored as a SavedModel."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from absl import app
from absl import flags

import tensorflow as tf

FLAGS = flags.FLAGS

flags.DEFINE_string("export_dir", None, "Directory to export SavedModel.")


class TextEmbeddingModel(tf.train.Checkpoint):
  """Text embedding model.

  A text embeddings model that takes a sentences on input and outputs the
  sentence embedding.
  """

  def __init__(self, emb_dim, buckets):
    super(TextEmbeddingModel, self).__init__()
    self._buckets = buckets
    self._embeddings = tf.Variable(tf.random.uniform(shape=[buckets, emb_dim]))

  def _tokenize(self, sentences):
    # Perform a minimalistic text preprocessing by removing punctuation and
    # splitting on spaces.
    normalized_sentences = tf.strings.regex_replace(
        input=sentences, pattern=r"\pP", rewrite="")
    normalized_sentences = tf.reshape(normalized_sentences, [-1])
    sparse_tokens = tf.string_split(normalized_sentences, " ")

    # Deal with a corner case: there is one empty sentence.
    sparse_tokens, _ = tf.sparse.fill_empty_rows(sparse_tokens, tf.constant(""))
    # Deal with a corner case: all sentences are empty.
    sparse_tokens = tf.sparse.reset_shape(sparse_tokens)

    return (sparse_tokens.indices, self._words_to_indices(sparse_tokens.values),
            sparse_tokens.dense_shape)

  def _words_to_indices(self, words):
    return tf.strings.to_hash_bucket(words, self._buckets)

  @tf.function(input_signature=[tf.TensorSpec([None], tf.dtypes.string)])
  def __call__(self, sentences):
    token_ids, token_values, token_dense_shape = self._tokenize(sentences)

    return tf.nn.safe_embedding_lookup_sparse(
        embedding_weights=self._embeddings,
        sparse_ids=tf.SparseTensor(token_ids, token_values, token_dense_shape),
        sparse_weights=None,
        combiner="sqrtn")


def main(argv):
  del argv

  module = TextEmbeddingModel(emb_dim=10, buckets=100)
  tf.saved_model.save(module, FLAGS.export_dir)


if __name__ == "__main__":
  app.run(main)
