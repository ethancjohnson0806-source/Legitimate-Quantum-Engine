import numpy as np
try:
    from scipy import linalg
except ImportError:
    linalg = None

class ZeroNoiseExtrapolation:
    def __init__(self, scale_factors=[1, 2, 3]):
        self.scales = scale_factors

    def extrapolate(self, noisy_values):
        x = 1 / np.array(self.scales)
        coeffs = np.polyfit(x, noisy_values, deg=min(len(x) - 1, 2))
        return np.polyval(coeffs, 0.0)

class ReadoutErrorMitigation:
    def __init__(self, n_qubits):
        self.n = n_qubits
        self.calibration = np.eye(2 ** n_qubits)

    def apply_mitigation(self, counts):
        return counts
