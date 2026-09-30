import numpy as np

class ImportanceSamplingUpdate:
    def __init__(self, update_weighting = 'uniform'):
        self.fs = []
        self.estimators = []
        self.weights = []
        self.variance_estimates = []
        self.variance_estimate_unnormalized = []
        self.variance_normalizer = []
        self.helper1 = []
        self.helper2 = []
        self.helper3 = []
        self.v1 = []
        self.v2 = []
        self.v3 = []
        self.variance_estimates1 = []
        self.variance_estimates2 = []
        self.mean_estimates = []
        self.prefixes = [0]
        self.true_vars = []
        self.qs = []
        self.variance_weighter = update_weighting
        self.var_data = []
        self.N = 0
        self.size = None
        self.next_size = None

    def append_estimator(self, q, f, index, new_f, new_index, mask, latest_mean = None):
        q = np.array(q)
        means = np.mean(np.array(f) / q[index])
        estimator = np.sum(self.fs) + means
        self.estimators.append(estimator)
        self.N += 1
        if self.size is None:
            self.size = len(q)
        elif len(new_f) > 0:
            self.size = self.next_size
        S = np.sum(mask)
        self.weights.append(1/S/(S-1)) # SWOR weights
        self.qs.append(q.copy())
        vars = np.mean(np.square(np.array(f) / q[index] - means)) / len(f)
        self.mean_estimates.append(means) # means of IS estimators without labeled f
        self.prefixes.append(np.sum(self.fs))
        self.helper1.append(0)
        self.helper2.append(0)
        self.helper3.append(0)
        self.v1.append(0)
        self.v2.append(0)
        self.v3.append(0)
        self.variance_estimates1.append(0)
        self.variance_estimates2.append(vars)
        self.variance_estimates.append(vars)
        self.variance_estimate_unnormalized.append(vars)
        if len(f) > 1:
            self.variance_normalizer.append(1)
        else:
            self.variance_normalizer.append(0)
        if latest_mean is None:
            latest_mean = np.mean(self.estimators)
        for tau in range(self.N):
            q_tau = self.qs[tau][index]
            mean_now = latest_mean - self.prefixes[tau]
            if self.variance_weighter == 'uniform':
                self.variance_normalizer[tau] += 1
                self.v1[tau] += self.helper1[tau] + np.mean(q_tau / q[index])
                self.v2[tau] += self.helper2[tau] + np.mean(np.array(f) / q[index])
                self.v3[tau] += self.helper3[tau] + np.mean(q_tau / q[index] * np.square(np.array(f) / q_tau))
            elif self.variance_weighter == 'LURE':
                S = np.sum(mask)
                self.variance_normalizer[tau] += 1/S/(S-1)
                self.v1[tau] += (self.helper1[tau] + np.mean(q_tau / q[index]))/S/(S-1)
                self.v2[tau] += (self.helper2[tau] + np.mean(np.array(f) / q[index]))/S/(S-1)
                self.v3[tau] += (self.helper3[tau] + np.mean(q_tau / q[index] * np.square(np.array(f) / q_tau)))/S/(S-1)
            self.variance_estimates[tau] = (self.v1[tau] * np.square(mean_now) + self.v3[tau] - 2 * self.v2[tau] * mean_now)/ self.variance_normalizer[tau]/len(f)
            diff_prob = self.qs[tau][new_index]
            diff_f = np.array(new_f)
            self.helper1[tau] += np.sum(diff_prob)
            self.helper2[tau] += np.sum(diff_f)
            self.helper3[tau] += np.sum(diff_prob * np.square(diff_f/diff_prob))

        self.fs.extend(new_f)


    def estimate(self, weights = None, retro = None):
        if self.N == 0:
            return
        if retro is None:
            max_n = self.N
        else:
            max_n = self.N - retro
        if weights is None:
            weights = np.array(self.weights)
        estimators = np.array(self.estimators)
        return np.sum(weights[:max_n] * estimators[:max_n]) / np.sum(weights[:max_n])

    def total_variance(self, weights = None, retro = None):
        if retro is None:
            max_n = self.N
        else:
            max_n = self.N - retro
        if weights is None:
            weights = np.array(self.weights)
        variances = np.array(self.variance_estimates)
        return np.sum(np.square(weights[:max_n]) * variances[:max_n]) / np.square(np.sum(weights[:max_n]))

