import numpy as np
from keras.utils.np_utils import to_categorical

from DeepSymphony.coders import AllInOneCoder
from DeepSymphony.models import StackedRNN
from DeepSymphony.utils import Song
from keras.regularizers import l1, l2


if __name__ == '__main__':
    LEN = 2000  # length of input
    DIM = 128+128+100+7

    data = np.load('./datasets/e-comp-allinone.npz')['data']

    def data_generator():
        batch_size = 16
        while True:
            x = []
            y = []
            for _ in range(batch_size):
                ind = np.random.randint(len(data))
                start = np.random.randint(data[ind].shape[0]-LEN-1)
                x.append(data[ind][start:start+LEN])
                y.append(data[ind][start+1:start+LEN+1])
            x = np.array(x)
            y = np.array(y)

            # sparse to complex
            x = to_categorical(x.flatten(), num_classes=DIM).\
                reshape(x.shape[0], x.shape[1], DIM)
            y = y.reshape(x.shape[0], x.shape[1], 1)
            yield (x, y)

    # model
    model = StackedRNN(timespan=LEN,
                       input_dim=DIM,
                       output_dim=DIM,
                       cells=[512, 512, 512],)
    #                  block_kwargs={'kernel_regularizer': l2(1e-5)})
    model.build()
#   model.model.load_weights('temp/stackedrnn_kernel_l2.h5')
#   model.model.load_weights('temp/simple_rnn.h5')
#   model.train(data_generator(),
#               opt=1e-5,
#               steps_per_epoch=30,
#               epochs=100,
#               save_path='temp/simple_rnn.h5')

    model.build_generator('temp/e-comp_simple_rnn.h5')
    res = model.generate(seed=32,
                         length=2000)

    mid = Song()
    track = mid.add_track()
    for msgi in AllInOneCoder().decode(res):
        track.append(msgi)
    mid.save_as('simple_rnn.mid')
