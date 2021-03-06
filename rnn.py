import tensorflow as tf
import numpy as np
import random


num_of_input_nodes = 1
num_of_hidden_nodes = 80
num_of_output_nodes = 1
length_of_sequences = 10
num_of_training_epochs = 5000
size_of_mini_batch = 100
num_of_prediction_epochs = 100
learning_rate = 0.01
forget_bias = 0.8
num_of_sample = 1000


def get_batch(batch_size, X, t):
    """
    サンプルからランダムなミニバッチを取得
    バッチサイズだけランダムな行の添字リストを作成し、
    その各添字に対する入力Xとラベルtの一覧をつくる
    """
    rnum = [random.randint(0, len(X) - 1) for x in range(batch_size)]
    xs = np.array([[[y] for y in list(X[r])] for r in rnum])
    ts = np.array([[t[r]] for r in rnum])
    return xs, ts


def create_data(nb_of_samples, sequence_len):
    """
    入力データとラベルの作成
    nb_of_samples ... num_of_sampleが入る
    sequence_len ... length_of_sequencesが入る
    長さsequence_lenのリストを複数個(nb_of_samplesだけ)用意し、それをまとめて行列Xとする
    各要素は0か1の値がランダムで入る
    tは正解ラベルでリストの各要素の合計値入っている(大きさnb_of_sanplesの)リスト
    """
    X = np.zeros((nb_of_samples, sequence_len))
    for row_idx in range(nb_of_samples):
        X[row_idx, :] = np.around(np.random.rand(sequence_len)).astype(int)
    # Create the targets for each sequence
    t = np.sum(X, axis=1)
    return X, t


def make_prediction(nb_of_samples):
    sequence_len = 10
    xs, ts = create_data(nb_of_samples, sequence_len)
    return np.array([[[y] for y in x] for x in xs]), np.array([[x] for x in ts])


def inference(input_ph, istate_ph):
    """
    LSTM層の設計
    phはplaceholderの略
    istateはinitial stateの略　セル状態の初期値?
    """
    # 実際のプログラムと同じような(変数の)スコープを定義する
    with tf.name_scope("inference") as scope:
	# 重みとバイアスの初期化 入力層-隠れ層間と隠れ層-出力層間のパラメータ
        weight1_var = tf.Variable(tf.truncated_normal(
            [num_of_input_nodes, num_of_hidden_nodes], stddev=0.1), name="weight1")
        weight2_var = tf.Variable(tf.truncated_normal(
            [num_of_hidden_nodes, num_of_output_nodes], stddev=0.1), name="weight2")
        bias1_var = tf.Variable(tf.truncated_normal([num_of_hidden_nodes], stddev=0.1), name="bias1")
        bias2_var = tf.Variable(tf.truncated_normal([num_of_output_nodes], stddev=0.1), name="bias2")

        in1 = tf.transpose(input_ph, [1, 0, 2])
        in2 = tf.reshape(in1, [-1, num_of_input_nodes])
	# ここでLSTMユニット内でのセル更新式を与えている
        in3 = tf.matmul(in2, weight1_var) + bias1_var

        in4 = tf.split(in3, length_of_sequences, 0)

        cell = tf.nn.rnn_cell.BasicLSTMCell(
            num_of_hidden_nodes, forget_bias=forget_bias)
        rnn_output, states_op = tf.contrib.rnn.static_rnn(cell=cell, inputs=in4, dtype=tf.float32)
	# ここで前ステップのうち最後のLSTM層から得られた出力に重みとバイアスをかけて最終的な出力としている
        output_op = tf.matmul(rnn_output[-1], weight2_var) + bias2_var

        # Add summary ops to collect data
        w1_hist = tf.summary.histogram("weights1", weight1_var)
        w2_hist = tf.summary.histogram("weights2", weight2_var)
        b1_hist = tf.summary.histogram("biases1", bias1_var)
        b2_hist = tf.summary.histogram("biases2", bias2_var)
        output_hist = tf.summary.histogram("output",  output_op)
        results = [weight1_var, weight2_var, bias1_var,  bias2_var]
        return output_op, states_op, results


def loss(output_op, supervisor_ph):
    """
    目的関数はMSE(mean squared error)平均二乗誤差
    """
    with tf.name_scope("loss") as scope:
        square_error = tf.reduce_mean(tf.square(output_op - supervisor_ph))
        loss_op = square_error
        tf.summary.scalar("loss", loss_op)
        return loss_op


def training(loss_op):
    with tf.name_scope("training") as scope:
        training_op = optimizer.minimize(loss_op)
        return training_op


def calc_accuracy(output_op, prints=False):
    """
    学習モデルの精度の検証
    """
    inputs, ts = make_prediction(num_of_prediction_epochs)
    pred_dict = {
        input_ph:  inputs,
        supervisor_ph: ts,
        istate_ph:    np.zeros((num_of_prediction_epochs, num_of_hidden_nodes * 2)),
    }
    output = sess.run([output_op], feed_dict=pred_dict)

    def print_result(i, p, q):
        [print(list(x)[0]) for x in i]
        print("output: %f, correct: %d" % (p, q))
    if prints:
        [print_result(i, p, q) for i, p, q in zip(inputs, output[0], ts)]

    opt = abs(output - ts)[0]
    total = sum([1 if x[0] < 0.05 else 0 for x in opt])
    print("accuracy %f" % (total / float(len(ts))))
    return output

random.seed(0)
np.random.seed(0)
tf.set_random_seed(0)

optimizer = tf.train.GradientDescentOptimizer(learning_rate=learning_rate)

X, t = create_data(num_of_sample, length_of_sequences)

with tf.Graph().as_default():
    # バッチサイズ × リスト幅 × 入力ノード数の3階テンソルのプレースホルダーを定義
    input_ph = tf.placeholder(tf.float32, [None, length_of_sequences, num_of_input_nodes], name="input")
    # バッチサイズ × 出力ノード数 教師データつまりラベル？
    supervisor_ph = tf.placeholder(tf.float32, [None, num_of_output_nodes], name="supervisor")
    # バッチサイズ × (隠れ層ノード数 * 2)
    istate_ph = tf.placeholder(tf.float32, [None, num_of_hidden_nodes * 2], name="istate")

    # LSTM層を定義 出力判断ゲートとセル状態とパラメータ?
    output_op, states_op, datas_op = inference(input_ph, istate_ph)
    # 目的関数を定義
    loss_op = loss(output_op, supervisor_ph)
    # 学習方法を定義
    training_op = training(loss_op)

    # Tensor Board出力用
    summary_op = tf.summary.merge_all()

    init = tf.global_variables_initializer()

    with tf.Session() as sess:
        saver = tf.train.Saver()
        summary_writer = tf.summary.FileWriter("/tmp/tensorflow_log", graph=sess.graph)
        sess.run(init)

        for epoch in range(num_of_training_epochs):
            inputs, supervisors = get_batch(size_of_mini_batch, X, t)
            train_dict = {
                input_ph:      inputs,
                supervisor_ph: supervisors,
                istate_ph:     np.zeros((size_of_mini_batch, num_of_hidden_nodes * 2)),
            }
            sess.run(training_op, feed_dict=train_dict)

	    # 100回ごとに誤差を出力し、500回ごとに精度を出力する
            if (epoch) % 100 == 0:
                summary_str, train_loss = sess.run([summary_op, loss_op], feed_dict=train_dict)
                print("train#%d, train loss: %e" % (epoch, train_loss))
                summary_writer.add_summary(summary_str, epoch)
                if (epoch) % 500 == 0:
                    calc_accuracy(output_op)

        calc_accuracy(output_op, prints=True)
        datas = sess.run(datas_op)
        saver.save(sess, "model.ckpt")
