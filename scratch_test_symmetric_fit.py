import numpy as np
import cv2
import matplotlib.pyplot as plt

# Simulate bottle bottom right curve
cx = 250
x_right = np.linspace(250, 400, 50)
# True parabola: a = 0.001, c = 800
y_true = 0.001 * (x_right - cx)**2 + 800

# Add some noise
y_noisy = y_true + np.random.normal(0, 1.0, len(x_right))

# 1. Unconstrained polyfit
p_unconstrained = np.polyfit(x_right, y_noisy, 2)

# 2. Symmetric polyfit around cx
x_sym = (x_right - cx)**2
p_sym_1d = np.polyfit(x_sym, y_noisy, 1)
a = p_sym_1d[0]
c = p_sym_1d[1]
b = -2 * a * cx
c_orig = a * cx**2 + c
p_sym = np.array([a, b, c_orig])

# Evaluate on full width
x_full = np.linspace(100, 400, 100)
y_unc = np.polyval(p_unconstrained, x_full)
y_sym = np.polyval(p_sym, x_full)

plt.figure()
plt.plot(x_right, y_noisy, 'k.', label='Data (Right half only)')
plt.plot(x_full, y_unc, 'r--', label='Unconstrained Parabola')
plt.plot(x_full, y_sym, 'g-', label='Symmetric Parabola (Arc)')
plt.axvline(cx, color='b', linestyle=':', label='Center')
plt.legend()
plt.gca().invert_yaxis()
plt.savefig('scratch_test_symmetric_fit.png')
print("Saved scratch_test_symmetric_fit.png")
