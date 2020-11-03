# AUTOGENERATED! DO NOT EDIT! File to edit: nbs/00_data.ipynb (unless otherwise specified).

__all__ = ['Heat', 'ImageSeq', 'ImageTupleTransform']

# Cell
import gzip
from fastai.vision.all import *


# Cell
class Heat:
    def __init__(self, root):
        self.data = np.load(root)
        self.length = self.data.shape[0]
        self.n_frames_input = 5
        self.n_frames_output = 5
        self.n_frames_total = self.n_frames_input + self.n_frames_output

    def __getitem__(self, idx):
        images = self.data[idx, :, :, :, None]
        length = 10
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

        # for i in range(5):
            # plt.imshow(x[i, 0])
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

    # if figsize is None: figsize = (ncols*6, max_n* 1.2)
    # if ctxs is None:
    #     _, ctxs = plt.subplots(min(x[0].shape[0], max_n), ncols, figsize=figsize)
    # for i,ctx in enumerate(ctxs):
    #     samples[i][0].show(ctx=ctx[0]), samples[i][1].show(ctx=ctx[1])


def main():
    DATA_PATH = "/data/wangshuo/data/heat_diffusion/heat_diffusion_batch_128_size_64x64_objs_1.npy"
    ds = Heat(DATA_PATH)
    train_tl = TfmdLists(range(100), ImageTupleTransform(ds))
    valid_tl = TfmdLists(range(100), ImageTupleTransform(ds))

    dls = DataLoaders.from_dsets(train_tl, valid_tl, bs=32,
                                 after_batch=[Normalize.from_stats(imagenet_stats[0][0],
                                                                   imagenet_stats[1][0])]).cuda()

    dls.show_batch()

if __name__ == '__main__':
    main()