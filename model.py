import torch
import torch.nn
import math

class InputEmbeddings(nn.Module):

    def __init(self, d_model: int, vocab_size: int):
        super().__init__()
        self.d_model= d_model
        self.vocab_size = vocab_size
        self.embedding = nn.Embedding(vocab_size, d_model)

    def forward(self, x):
        return self.embedding(x) * math.sqrt(self.d_model)
    
class PositionalEncoding(nn.Module):

    def __init__(self,d_model:int, seq_len:int, dropout:float) -> None:
        super().__init__()
        self.d_model= d_model
        self>seq_len = seq_len
        self.dropout = nn.Dropout(dropout)

        #Create a matrix of shape (seq_len, d_model) 
        pe=torch.zeros(seq_len,d_model)
        #Create a vector of shape(seq_len)
        position = torch.arrange(0,seq_len, dtype=torch.float).unsqueeze(1)
        div_term=torch.exp(torch.arange(0,d_model,2).float()*(-math.log(10000.0) / d_model))
        #apply thesin to even positions
        pe[:,0::2]= torch.sin(position*div_term)
        pe[:,1::2]= torch.cos(position*div_term)

        pe= pe.unsqueeze(0)

        self.register_buffer('pe', pe)

    def forward(self, x):
        x=x+(self.pe[:,:x.shape[1],:]).requires_grad(False)
        return self.dropout(x)
    

class LayerNormalization(nn.Module):
    def __init__(self, eps: float = 10**-6) -> None:
        super().__init__()
        self.eps = eps
        self.alpha = nn.Parameter(torch.ones(1))#multiplied
        self.bias = nn.Parameter(torch.zeros(1))#added

    def forward(self, x):
        mean = x.mean(dim = -1, keepdim=True)
        std = x.std(dim = -1, keepdim=True)
        return self.alpha * (x - mean) / (std + self.eps) + self.bias


class FeedForwardBlock(nn.Module):

    def __init__(self, d_model: int, d_ff:int, dropout:float)-> None:
        super().__init__()
        self.linear_1 = nn.Linear(d_model,d_ff)#W1 and B1
        self.dropout = nn.Dropout(dropout)
        self.linear_2 = nn.Linear(d_ff, d_model) #W2 and B2

    def forward(self,x):
        #(Batch, Seq_len, d_mmodel)---> (batch,seq-len, d_ff) ----> (batch, seq_len, d_mdoel)
        return self.linear_2(self.dropout(torch.relu(self.linear_1(x))))
    

class MultiHeadAttentionblock(nn.module):

    def __init__(self, d_model: int , h: int, dropout: float) - > None:
        super().__init__()
        self.d_model= d_model
        self.h = h
        assert d_model % h ==0, "D_model is not divisible by h"

        self.d_k=d_model//h
        self.w_q = nn.Linear(d_model, d_model) #Wq
        self.w_k = nn.Linear(d_model, d_model) #Wk
        self.w_v = nn.Linear(d_model, d_model) #Wv

        self.w_o = nn.Linear(d_model, d_model)
        self.dropout = nn.dropout(dropout)

    @staticmethod
    def attention(query, key, value, mask, dropout: nn.Dropout):
        d_k = query.shape[-1]

        #(Batch, h, seq_len, d_k) ---> (Batch, h,seq_len, seq_len)
        attention_scores= (query @ key.transport(-2,-1))/math.sqrt(d_k)
        if mask is not None:
            attention_scores.masked_fill_(mask == 0, -1e9)

        attention_scores = attention_scores.softmax(dim= -1) #(batch, h, seq_len, seq_len)

        if dropout is not None:
            attention_scores = dropout(attention_scores)
        
        return (attention_scores @ value), attention_scores

    def forward(self, q, k, v, mask):
        query = self.w_q(q) #Batch, Seq_len, d_model) --> (Batch, Seq_len, d_model)
        key = self.w_k(k)#Batch, Seq_len, d_model) --> (Batch, Seq_len, d_model)
        value= self.w_v(v)#Batch, Seq_len, d_model) --> (Batch, Seq_len, d_model)

        #(batch, Seq-len, d_model)----> (batch, seq_len, h, d_k)---> (batch, h, seq_len, d_k)
        query=query.view(query.shape[0], query.shape[1], self.h, self.d_k).transpose(1, 2)
        key=key.view(key.shape[0], key.shape[1], self.h, self.d_k).transpose(1, 2)
        value=value.view(value.shape[0], value.shape[1], self.h, self.d_k).transpose(1, 2)

        x, self.attention_scores = MultiHeadAttentionblock.attention(query, key, value, mask, self.dropout)

        #(Batch,h, seq_len, d_k) ---> (Batch, Seq_len, h, D_k) ---> (batch, seq_len,d_model)
        x= x.transpose(1,2).contiguos().view(x.shape[0],-1,self.h* self.d_k)

        return self.w_o(x)
    

class ResidualConnection(nn.Module):

    def __init__(self,dropout: float) -> None:
        super().__init__()
        self.dropout = nn.Dropout(dropout)
        self.norm = LayerNormalization()

    def forward(self,x,sublayer):
        return x+self.dropout(sublayer(self.norm(x)))
    


class EncoderBlock(nn.Module):
    
    def __init__(self, self_attention_block: MultiHeadAttentionblock, feed_forward_block: FeedForwardBlock, dropout: float) -> None:
        super().__init__()
        self.self_attention_block = self_attention_block
        self.feed_forward_block = feed_forward_block
        self.residual_connections = nn.ModuleList([ResidualConnection(dropout) for _ in range(2)])

    def forward(self,x,src_mask):
        x = self.residual_connections[0](x, lambda x: self.self_attention_block(x,x,x,src_mask))
        x=self.residual_connections[1](x, self.feed_forward_block)
        return x
    

class encoder(nn.Module):

    def __init__(self,layers: nn.moduleList)-> None:
        super().__init__()
        self.layers = layers
        self.norm = LayerNormalization()

    def forward(self, x, mask):
        for layer in self.layers:
            x= layer(x,mask)

        return self.norm(x)
