"""Referans çözüm."""
from scipy import signal


def fir_lowpass(fs, fc, ntaps):
    return signal.firwin(ntaps, fc, window="hamming", fs=fs)


def fir_uygula(x, taps):
    return signal.lfilter(taps, 1.0, x)
