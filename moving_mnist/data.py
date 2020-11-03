# AUTOGENERATED! DO NOT EDIT! File to edit: nbs/00_data.ipynb (unless otherwise specified).

__all__ = ['load_mnist', 'MovingMNIST', 'ImageSeq', 'ImageTupleTransform']

# Cell
import gzip
from fastai.vision.all import *

# Cell
def load_mnist(path):
    "Load MNIST dataset for generating training data"
    path = path + 'train_images.gz'
    with gzip.open(path, 'rb') as f:
        mnist = np.frombuffer(f.read(), np.uint8, offset=16)
        mnist = mnist.reshape(-1, 28, 28)
    return mnist

# Cell
class MovingMNIST:
    def __init__(self, root, n_in, n_out, n_obj, th=None):
        self.dataset = None
        self.mnist = load_mnist(root)
        self.length = int(1e4) if self.dataset is None else self.dataset.shape[1]
        self.num_objects = [n_obj] if not is_listy(n_obj) else n_obj
        self.n_frames_input = n_in
        self.n_frames_output = n_out
        self.n_frames_total = self.n_frames_input + self.n_frames_output
        # For generating data
        self.image_size_ = 64
        self.digit_size_ = 28
        self.step_length_ = 0.1
        self.th = th

    def get_random_trajectory(self, seq_length):
        ''' Generate a random sequence of a MNIST digit '''
        canvas_size = self.image_size_ - self.digit_size_
        x = random.random()
        y = random.random()
        theta = random.random() * 2 * np.pi
        v_y = np.sin(theta)
        v_x = np.cos(theta)

        start_y = np.zeros(seq_length)
        start_x = np.zeros(seq_length)
        for i in range(seq_length):
            # Take a step along velocity.
            y += v_y * self.step_length_
            x += v_x * self.step_length_

            # Bounce off edges.
            if x <= 0:
                x = 0
                v_x = -v_x
            if x >= 1.0:
                x = 1.0
                v_x = -v_x
            if y <= 0:
                y = 0
                v_y = -v_y
            if y >= 1.0:
                y = 1.0
                v_y = -v_y
            start_y[i] = y
            start_x[i] = x

        # Scale to the size of the canvas.
        start_y = (canvas_size * start_y).astype(np.int32)
        start_x = (canvas_size * start_x).astype(np.int32)
        return start_y, start_x

    def generate_moving_mnist(self, num_digits=2):
        "Get random trajectories for the digits and generate a video"
        data = np.zeros((self.n_frames_total, self.image_size_, self.image_size_), dtype=np.float32)
        for n in range(num_digits):
            # Trajectory
            start_y, start_x = self.get_random_trajectory(self.n_frames_total)
            ind = random.randint(0, self.mnist.shape[0] - 1)
            digit_image = self.mnist[ind]
            for i in range(self.n_frames_total):
                top = start_y[i]
                left = start_x[i]
                bottom = top + self.digit_size_
                right = left + self.digit_size_
                # Draw digit
                data[i, top:bottom, left:right] = np.maximum(data[i, top:bottom, left:right], digit_image)

        data = data[..., np.newaxis]
        return data

    def __getitem__(self, idx):
        length = self.n_frames_input + self.n_frames_output
        if self.num_objects[0] != 2:
            # Sample number of objects
            num_digits = random.choice(self.num_objects)
            # Generate data on the fly
            images = self.generate_moving_mnist(num_digits)
        else:
            images = self.dataset[:, idx, ...]
        r = 1
        w = int(64 / r)
        images = images.reshape((length, w, r, w, r)).transpose(0, 2, 4, 1, 3).reshape((length, r * r, w, w))

        input = images[:self.n_frames_input]
        if self.n_frames_output > 0:
            output = images[self.n_frames_input:length]
        else:
            output = []

        frozen = input[-1]
        output = torch.from_numpy(output / 255.0).contiguous().float()
        input = torch.from_numpy(input / 255.0).contiguous().float()
        if self.th is not None:
            return (input>self.th).float(), (output>self.th).long()
        return input, output

    def __len__(self):
        return self.length

# Cell
class ImageSeq(fastuple):
    @classmethod
    def create(cls, t, cl_type=TensorImageBW):
        return cls(tuple(cl_type(im) for im in t))
    def show(self, ctx=None, **kwargs):
        return show_image(torch.cat([t for t in self], dim=2), ctx=ctx, **self[0]._show_args, **kwargs)

# Cell
class ImageTupleTransform(Transform):
    def __init__(self, ds, cl_type=TensorImageBW):
        self.ds = ds
        self.cl_type = cl_type

    def encodes(self, idx):
        x,y = self.ds[idx]
        # plt.imshow(x[0, 0])
        # plt.show()
        return ImageSeq.create(x, self.cl_type), ImageSeq.create(y, self.cl_type)

# Cell
@typedispatch
def show_batch(x:ImageSeq, y:ImageSeq, samples, ctxs=None, max_n=6, nrows=None, ncols=2, figsize=None, **kwargs):
    if figsize is None: figsize = (ncols*6, max_n* 1.2)
    if ctxs is None:
        _, ctxs = plt.subplots(min(x[0].shape[0], max_n), ncols, figsize=figsize)
    for i,ctx in enumerate(ctxs):
        samples[i][0].show(ctx=ctx[0]), samples[i][1].show(ctx=ctx[1])


def main():
    DATA_PATH = '/home/wshuo/workspace/moving_mnist/data/'
    ds = MovingMNIST(DATA_PATH, n_in=5, n_out=5, n_obj=[1, 2, 3])
    print(len(ds))
    train_tl = TfmdLists(range(7500), ImageTupleTransform(ds))
    valid_tl = TfmdLists(range(100), ImageTupleTransform(ds))

    dls = DataLoaders.from_dsets(train_tl, valid_tl, bs=32,
                                 after_batch=[Normalize.from_stats(imagenet_stats[0][0],
                                                                   imagenet_stats[1][0])]).cuda()

    dls.show_batch()

if __name__ == '__main__':
    main()