import numpy as np
from numpy.testing import assert_array_equal, assert_almost_equal
from scipy import stats

import mne
from ..permutations import permutation_t_test


def test_permutation_t_test():
    """Test T-test based on permutations
    """
    # 1 sample t-test
    np.random.seed(10)
    n_samples, n_tests = 30, 5
    X = np.random.randn(n_samples, n_tests)
    X[:,:2] += 1

    p_values, T0, H0 = permutation_t_test(X, n_permutations=999, tail=0)
    is_significant = p_values < 0.05
    assert_array_equal(is_significant, [True, True, False, False, False])

    p_values, T0, H0 = permutation_t_test(X, n_permutations=999, tail=1)
    is_significant = p_values < 0.05
    assert_array_equal(is_significant, [True, True, False, False, False])

    p_values, T0, H0 = permutation_t_test(X, n_permutations=999, tail=-1)
    is_significant = p_values < 0.05
    assert_array_equal(is_significant, [False, False, False, False, False])

    X = np.random.randn(18, 1)
    p_values, T0, H0 = permutation_t_test(X[:, [0]], n_permutations='exact')
    T0_scipy, p_values_scipy = stats.ttest_1samp(X[:, 0], 0)
    assert_almost_equal(T0[0], T0_scipy, 8)
    assert_almost_equal(p_values[0], p_values_scipy, 2)