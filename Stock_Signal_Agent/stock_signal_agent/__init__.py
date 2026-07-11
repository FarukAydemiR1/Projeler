"""Stock Signal Agent.

Yükselmesi beklenen hisselerin yükselmeden ÖNCEKI teknik "parmak izini"
geçmiş veriden öğrenen ve aynı belirtileri gösteren güncel hisseleri
yakalayıp sinyal üreten bir ajan.

Akış:
    1. data      -> OHLCV veri çekme (Yahoo Finance / CSV / sentetik)
    2. indicators-> teknik göstergeler (RSI, MACD, hacim, kırılım...)
    3. features  -> gösterlerden özellik matrisi (lookahead yok)
    4. labeling  -> "yükseliş olayı" etiketleme (ileriye dönük getiri)
    5. model     -> ML modeli (gradient boosting) öğrenir
    6. rules     -> anlaşılır teknik kural motoru
    7. screener  -> model + kural birleşimi, sinyal üretir
"""

__version__ = "0.1.0"

from .data import load_prices, DataError
from .screener import Screener, Signal
from .model import SignalModel

__all__ = [
    "load_prices",
    "DataError",
    "Screener",
    "Signal",
    "SignalModel",
    "__version__",
]
