"""SigMF kaydı için meta veri dosyası yazma (sentetik veri, donanım yok).

sigmf 1.14.0, numpy 2.5.5. Kaynak: sigmf-python v1.14.0
docs/source/quickstart.rst ("Save a Numpy array with Full Metadata").
"""

import json

import numpy as np
import sigmf
from sigmf.utils import get_data_type_str, get_sigmf_iso8601_datetime_now

# 1) Örnekleri ham dosyaya yaz (complex64 -> cf32_le)
data = np.zeros(1024, dtype=np.complex64)
data.tofile("kayit.sigmf-data")

# 2) Genel (global) meta veri
meta = sigmf.SigMFFile(
    data_file="kayit.sigmf-data",
    global_info={
        sigmf.DATATYPE_KEY: get_data_type_str(data),  # "cf32_le"
        sigmf.SAMPLE_RATE_KEY: 2_000_000,
        sigmf.AUTHOR_KEY: "EH lab",
        sigmf.DESCRIPTION_KEY: "Örnek kayıt",
    },
)

# 3) Yakalama (capture): 0. örnekten itibaren merkez frekans ve zaman
meta.add_capture(0, metadata={
    sigmf.FREQUENCY_KEY: 915_000_000,
    sigmf.DATETIME_KEY: get_sigmf_iso8601_datetime_now(),
})

# 4) İsteğe bağlı not (annotation): 100. örnekten başlayan 200 örnek, 10 kHz bant
meta.add_annotation(100, 200, metadata={
    sigmf.FREQ_LOWER_EDGE_KEY: 914_995_000.0,
    sigmf.FREQ_UPPER_EDGE_KEY: 915_005_000.0,
    sigmf.COMMENT_KEY: "ilgi çeken sinyal",
})

# 5) Doğrula ve yaz
meta.tofile("kayit.sigmf-meta")

# 6) Doğrulama: dosyayı geri oku ve özetle
with open("kayit.sigmf-meta", encoding="utf-8") as f:
    print(json.dumps(json.load(f), indent=4, ensure_ascii=False))
okunan = sigmf.fromfile("kayit")
ornekler = okunan.read_samples()
print("datatype:", okunan.get_global_field(sigmf.DATATYPE_KEY))
print("sample_rate:", okunan.get_global_field(sigmf.SAMPLE_RATE_KEY))
print("örnek sayısı:", ornekler.shape[0], "dtype:", ornekler.dtype)
print("capture sayısı:", len(okunan.get_captures()), "annotation sayısı:", len(okunan.get_annotations()))
print("örnekler yazılanla aynı:", bool(np.array_equal(ornekler, data)))
