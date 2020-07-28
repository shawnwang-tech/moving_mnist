# AUTOGENERATED! DO NOT EDIT! File to edit: nbs/02_models.transformer.ipynb (unless otherwise specified).

__all__ = ['Encoder', 'DETR', 'detr_split', 'TransformerTS', 'tf_split']

# Cell
from fastai2.vision.all import *
from .conv_rnn import *

# Cell
@delegates(create_cnn_model)
class Encoder(Module):
    def __init__(self, arch=resnet34, n_in=3, weights_file=None, n_out=1, strict=False, pretrained=False, **kwargs):
        "Encoder based on resnet, returns the feature map"
        model = create_cnn_model(arch, n_out=n_out, n_in=n_in, pretrained=pretrained, **kwargs)
        if weights_file is not None:
            load_res = load_model(weights_file, model, opt=None, strict=strict)
            print(f'Loading model from file {weights_file} \n>missing keys: {load_res}')
        self.body = model[0]

    def forward(self, x):
        return self.body(x)

# Cell
class DETR(Module):
    def __init__(self,  arch=resnet34, n=80, n_in=1, n_out=1, hidden_dim=256, nheads=4, num_encoder_layers=4,
                 num_decoder_layers=4, debug=False):
        self.debug = debug

        #the image encoder
        self.backbone = TimeDistributed(Encoder(arch, n_in=n_in, pretrained=True))

        # create conversion layer
        self.conv = TimeDistributed(nn.Conv2d(512, hidden_dim, 1))

        # create a default PyTorch transformer
        self.transformer = nn.Transformer(
            hidden_dim, nheads, num_encoder_layers, num_decoder_layers)

        # output positional encodings (object queries)
        self.query_pos = nn.Parameter(torch.rand(100, hidden_dim))

        # spatial positional encodings
        # note that in baseline DETR we use sine positional encodings
        self.pos = nn.Parameter(torch.rand(n, hidden_dim))
#         self.row_embed = nn.Parameter(torch.rand(50, hidden_dim // 4))
#         self.col_embed = nn.Parameter(torch.rand(50, hidden_dim // 4))
#         self.time_embed =nn.Parameter(torch.rand(50, hidden_dim // 2))

        #decoder
        self.decoder = TimeDistributed(nn.Sequential(
                           UpsampleBlock(256, 128, residual=False),
                           UpsampleBlock(128, 128, residual=False),
                           UpsampleBlock(128, 64, residual=False),
                           UpsampleBlock(64, 32, residual=False),
                           UpsampleBlock(32, 16, residual=False),
                           nn.Conv2d(16, n_out, 3,1,1))
                                      )
        self.lin = nn.Linear(100,n)  #hardcodeed

    def forward(self, inputs):
        # propagate inputs through ResNet up to avg-pool layer
        x = self.backbone(inputs)
        if self.debug: print(f'backbone: {x.shape}')

        # convert from the latent dim to 256 feature planes for the transformer
        h = self.conv(x)
        if self.debug: print(f'h: {h.shape}')

        # construct positional encodings
        H, W = h.shape[-2:]
        T = h.shape[1]
#         pos = torch.cat([
#             self.time_embed[:T].view(T,1,1,-1).repeat(1, H, W, 1),
#             self.col_embed[:W].view(1,1,W,-1).repeat(T, H, 1, 1),
#             self.row_embed[:H].view(1,H,1,-1).repeat(T, 1, W, 1),
#         ], dim=-1).flatten(0, 2).unsqueeze(1)
        pos = self.pos.unsqueeze(1)
        if self.debug: print(f'pos: {pos.shape}')

        # propagate through the transformer
        tf_input = pos + 0.1 * h.permute(0,2,1,3,4).flatten(2).permute(2,0,1)
        if self.debug: print(f'tf_input: {tf_input.shape}')
        h = self.transformer(tf_input,
                             self.query_pos.unsqueeze(1)).permute(2,1,0)
        if self.debug: print(f'tf_out: {h.shape}')
        h = self.lin(h)
        if self.debug: print(f'lin: {h.shape}')
        h = h.view(1,T,-1,H,W)
        if self.debug: print(f'before dec: {h.shape}')
        return self.decoder(h)

# Cell
def detr_split(model, stacked=False):
    if not stacked:
        return [params(model.backbone),
                params(model.conv)+params(model.transformer)+[model.query_pos]+[model.pos]+params(model.decoder)+params(model.lin)]
    else:
        return [params(model.module.backbone),
                params(model.module.conv)+params(model.module.transformer)+[model.module.query_pos]+[model.module.pos]+params(model.module.decoder)+params(model.module.lin)]

# Cell
from tst.transformer import Transformer

# Cell
class TransformerTS(Module):
    def __init__(self,  arch=resnet34, n_in=3, n_out=1, hidden_dim=256, debug=False):
        self.debug = debug

        #the image encoder
        self.backbone = TimeDistributed(Encoder(arch, n_in=n_in, pretrained=True))

        # create conversion layer
        self.conv = TimeDistributed(nn.Conv2d(512, hidden_dim, 1))

        # create a default PyTorch transformer
        q = 8 # Query size
        v = 8 # Value size
        h = 8 # Number of heads
        n = 4 # Number of encoder and decoder to stack
        attention_size = 12 # Attention window size
        dropout = 0.2 # Dropout rate
        pe = None # Positional encoding
        chunk_mode = None
        self.transformer = Transformer(hidden_dim, hidden_dim, hidden_dim, q, v, h, n, attention_size, dropout, chunk_mode, pe)

        #decoder
        self.decoder = TimeDistributed(nn.Sequential(
                           UpsampleBlock(256, 128, residual=False),
                           UpsampleBlock(128, 128, residual=False),
                           UpsampleBlock(128, 64, residual=False),
                           UpsampleBlock(64, 32, residual=False),
                           UpsampleBlock(32, 16, residual=False),
                           nn.Conv2d(16, n_out, 3,1,1))
                                      )
    def forward(self, inputs):
        # propagate inputs through ResNet up to avg-pool layer

        x = self.backbone(inputs)
        if self.debug: print(f'backbone: {x.shape}')

        # convert from the latent dim to 256 feature planes for the transformer
        h = self.conv(x)
        if self.debug: print(f'h: {h.shape}')
        bs,T,_, H,W = h.shape

        tf_input = h.permute(0,2,1,3,4).flatten(2).permute(0,2,1)
        if self.debug: print(f'tf_input: {tf_input.shape}')
        h = self.transformer(tf_input)
        if self.debug: print(f'tf_out: {h.shape}')
        h = h.view(bs,T,-1,H,W)
        if self.debug: print(f'before dec: {h.shape}')
        return self.decoder(h)

# Cell
def tf_split(m, stacked=False):
    if not stacked:
        return [params(m.backbone),
                params(m.conv)+params(m.transformer)+params(m.decoder)]
    else:
        return [params(m.module.backbone),
                params(m.module.conv)+params(m.module.transformer)+params(m.module.decoder)]
