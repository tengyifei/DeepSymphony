'''
    Using Conv rather than cnn to generate
'''
import os
import numpy as np
from scipy.misc import imsave
from midiwrapper import Song
import shutil

from keras.layers import Conv2D, Dense, Activation, \
    Input, BatchNormalization, Reshape, \
    UpSampling2D, Conv2DTranspose, LeakyReLU, \
    Flatten, LSTM, Dropout
from keras.models import Model, Sequential
from keras.optimizers import Adam, SGD
from gan import cnn_dis, cnn_gen
from encoder_decoder import AllInOneEncoder

import argparse
parser = argparse.ArgumentParser(description='GAN-RNN Model')
parser.add_argument('--activation', type=str, default='tanh',
                    help='define activation and normalization range')

parser.add_argument('--code_dim', type=int, default=500)
# parser.add_argument('--note_dim', type=int, default=128)
parser.add_argument('--seq_len', type=int, default=96)
parser.add_argument('--nbatch', type=int, default=64)
parser.add_argument('--niter', type=int, default=1000)

parser.add_argument('--vis_interval', type=int, default=100)
parser.add_argument('--work_dir', type=str, default='temp/gan',
                    help='work dir')

args = parser.parse_args()
print args


if __name__ == '__main__':
    seq_len = args.seq_len
    code_dim = args.code_dim
    # note_dim = args.note_dim
    niter = args.niter
    nbatch = args.nbatch
    vis_iterval = args.vis_interval
    work_dir = args.work_dir
    vis_dir = os.path.join(args.work_dir, 'vis')

    # env setup
    if os.path.exists(work_dir):
        shutil.rmtree(work_dir)
    os.mkdir(work_dir)
    os.mkdir(vis_dir)

    # data preparation
    # data = Song.load_from_dir("./datasets/easymusicnotes/")
    # data = Song.load_from_dir("./datasets/easymusicnotes/",
    #                         encoder=AllInOneEncoder())
    # data = np.load('./datasets/e-comp-allinone-partial.npz')['data']
    data = np.load('./datasets/e-comp-allinone-partial.npz')['data']
    data = np.array([datai[:,:360] for datai in data])
    print data[0].shape
    note_dim = data[0].shape[-1]

    def data_generator(bs):
        indices = np.random.randint(data.shape[0], size=(bs,))
        x = []
        for ind_i in indices:
            start = np.random.randint(data[ind_i].shape[0]-seq_len)
            x.append(data[ind_i][start:start+seq_len])
        x = np.array(x).astype('float')
        x = np.expand_dims(x, -1)
        if args.activation == 'tanh':
            x = x*2 - 1
        return x

    def code_generator(bs):
        # Z = np.random.uniform(-1., 1., size=(bs, code_dim))
        Z = np.random.normal(0, 1., size=(bs, code_dim))
        return Z

    # component definition
    note_dim = data[0].shape[-1]
    gen = cnn_gen(coding_shape=(code_dim,),
                  img_shape=(seq_len, note_dim, 1),
                  nf=128,
                  scale=3,
                  FC=[],
                  use_upsample=True)
    gen.summary()

    dis = cnn_dis(input_shape=(seq_len, note_dim, 1),
                  nf=32,
                  scale=2,
                  FC=[])
    dis.summary()

    # model definition
    gen_opt = Adam(5e-4, beta_1=0.5, beta_2=0.9)
    dis_opt = SGD(5e-4)  # , momentum=0.9)

    gendis = Sequential([gen, dis])
    dis.trainable = False
    gendis.compile(optimizer=gen_opt, loss='binary_crossentropy')

    shape = dis.get_input_shape_at(0)[1:]
    gen_input, real_input = Input(shape), Input(shape)
    dis2batch = Model([gen_input, real_input],
                      [dis(gen_input), dis(real_input)])
    dis.trainable = True
    dis2batch.compile(optimizer=dis_opt,
                      loss='binary_crossentropy',
                      metrics=['binary_accuracy'])

    gen_trainner = gendis
    dis_trainner = dis2batch

    gh = 2
    gw = 7
    imsave('{}/real.png'.format(vis_dir),
           Song.grid_vis_songs(data_generator(gh*gw)[:, :, :, 0], gh=gh, gw=gw))
    vis_Z = code_generator(gh*gw)
    fake_pool = gen.predict(vis_Z)
    for iteration in range(0, niter):
        print 'iteration', iteration
        Z = code_generator(nbatch)
        gen_img = gen.predict(Z)

        fake_pool = np.vstack([fake_pool[:nbatch], gen_img])
        shuffle_indices = np.random.permutation(len(fake_pool))
        fake_pool = fake_pool[shuffle_indices]
        gen_img = fake_pool[:nbatch]

        real_img = data_generator(nbatch)
        gen_y = np.zeros((nbatch, 1))
        real_y = np.ones((nbatch, 1))
        d_loss = dis_trainner.train_on_batch([gen_img, real_img],
                                             [gen_y, real_y])
        print('\tDiscriminator:\t{}'.format(d_loss))

        y = np.ones((nbatch, 1))
        g_loss = gen_trainner.train_on_batch(Z, y)
        print('\tGenerator:\t{}'.format(g_loss))

        if iteration % vis_iterval == 0:
            songs = gen.predict(vis_Z)[:, :, :, 0]
            imsave('{}/{:03d}.png'.format(vis_dir, iteration),
                   Song.grid_vis_songs(songs, gh=gh, gw=gw))
    gen.save('{}/gen.h5'.format(work_dir))
