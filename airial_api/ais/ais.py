import numpy as np


class AIS:
    def __init__(self, model, estimator, swor=False, m=1, update_retro = 0, true_var = False):
        self.model = model
        self.mask = np.ones(self.model.N)
        self.labeled_mask = np.zeros(self.model.N)
        self.round = 0
        self.e = estimator
        self.swor = swor
        self.m = m
        self.update_retro = update_retro
        self.ais_weights = []
        self.ais_round = 1
        self.true_var = true_var
        if true_var:
            self.f = self.model.f
            self.true_vars = []

    def step(self, latest_mean = None):
        if np.sum(self.mask) == 0:
            return
        ids = []
        prob = None
        truths = []
        for iteration in range(self.m): # m=1 in the experiments
            id, prob, truth = self.model.sample_index(mask=self.mask)
            ids.append(id)
            truths.append(truth)
            self.labeled_mask[id] = 1

        if self.true_var:
            true_mean = np.sum(self.mask * self.f)
            f_remain = self.f[self.mask.astype(bool)]
            p_remain = prob[self.mask.astype(bool)]
            true_var = np.sum(p_remain * np.square(f_remain/p_remain - true_mean))
            if len(self.true_vars) < 2:
                print(true_var, true_mean)
            self.true_vars.append(true_var/self.m)

        new_f = []
        new_index = []
        sampling_mask = self.mask.copy()
        if self.swor:
            for truth, id in zip(truths, ids):
                if self.mask[id] == 1:
                    new_f.append(truth)
                    new_index.append(id)
                    self.mask[id] = 0
        labeled_ids = []
        unlabeled_ids = []
        for id in range(self.model.N):
            if self.mask[id] == 0:
                unlabeled_ids.append(id)
            else:
                labeled_ids.append(id)

        self.e.append_estimator(q=prob, f=truths, index = ids, new_f=new_f, new_index=new_index, mask = sampling_mask, latest_mean =
        latest_mean)
        self.ais_weights.append(np.sqrt(self.ais_round))
        self.round += 1

    def train(self):
        res = self.model.train(self.labeled_mask)
        if res:
            self.ais_round += 1

    def sqrt_mixer(self, gamma = 0.5, scale_var = False, simple_var=False):
        var = np.array(self.e.variance_estimates)
        if len(var) == 0:
            var = np.array([1])
        if np.sum(var) <= 0.0:
            var = np.ones_like(var)
        min_positive = np.min(var[var > 0])
        var[var == 0] = min_positive
        processed_vars = self.process_variances(var, gamma)
        weights = np.array(self.ais_weights)
        estimate = self.e.estimate(weights = np.array(self.ais_weights),)
        if scale_var:
            total_variance = np.sum(np.square(weights) * processed_vars) / np.square(np.sum(weights))
        elif simple_var:
            total_variance = np.sum(np.square(weights) * np.square(np.array(self.e.estimators) - estimate)) / np.square(
                np.sum(weights))
        else:
            total_variance = self.e.total_variance(weights=weights, retro=0)
        return estimate, total_variance

    def process_variances(self, variances, gamma = 0.5):
        len_v = len(variances)
        cut = int(np.ceil(len_v * gamma))
        swor_weights = 1/np.array(self.e.weights)/np.array(self.ais_weights)
        swor_variances = swor_weights * variances[cut - 1] / swor_weights[cut - 1]
        variances[cut:] = swor_variances[cut:]
        return variances


    def inv_var_mixer(self):
        var = np.array(self.e.variance_estimates)
        if len(var) == 0:
            var = np.array([1])
        if np.sum(var) <= 0.0:
            var = np.ones_like(var)
        min_positive = np.min(var[var > 0])
        var[var == 0] = min_positive
        weights = 1/var
        len_w = len(weights)
        if self.update_retro > 0 and len_w >= self.update_retro:
            weights[len_w-self.update_retro:] = np.full(self.update_retro, weights[-self.update_retro])
        estimate = self.e.estimate(weights = weights, retro = 0)
        total_variance = self.e.total_variance(weights = weights, retro = 0)
        return estimate, total_variance

    def inv_var_mixer_true(self):
        var = np.array(self.true_vars)
        weights = 1/var
        estimate = self.e.estimate(weights = weights, retro = 0)
        total_variance = self.e.total_variance(weights = weights, retro = 0)
        return estimate, total_variance

    def mixer_true(self, weights):
        var = np.array(self.true_vars)
        estimate = self.e.estimate(weights = weights,)
        total_variance = np.sum(np.square(weights) * var) / np.square(np.sum(weights))
        return estimate, total_variance
    def inv_var_mixer_smoothed(self, gamma=0.5, scale_var = False, simple_var=False):
        var = np.array(self.e.variance_estimates)
        if len(var) == 0:
            var = np.array([1])
        if np.sum(var) <= 0.0:
            var = np.ones_like(var)
        min_positive = np.min(var[var > 0])
        var[var == 0] = min_positive
        processed_vars = self.process_variances(var, gamma)
        weights = 1/processed_vars
        estimate = self.e.estimate(weights = weights, retro = 0)
        if scale_var:
            total_variance = np.sum(np.square(weights) * processed_vars) / np.square(np.sum(weights))
        elif simple_var:
            total_variance = np.sum(np.square(weights) * np.square(np.array(self.e.estimators) - estimate)) / np.square(
                np.sum(weights))
        else:
            total_variance = self.e.total_variance(weights = weights, retro = 0)
        return estimate, total_variance

    def lure_mixer(self, gamma = 0.5, scale_var = False, simple_var=False):
        estimate = self.e.estimate(weights = None,)
        weights = self.e.weights
        var = np.array(self.e.variance_estimates)
        if len(var) == 0:
            var = np.array([1])
        if np.sum(var) == 0.0:
            var = np.ones_like(var)
        min_positive = np.min(var[var > 0])
        var[var == 0] = min_positive
        processed_vars = self.process_variances(var, gamma)
        if scale_var:
            total_variance = np.sum(np.square(weights) * processed_vars) / np.square(np.sum(weights))
        elif simple_var:
            total_variance = np.sum(np.square(weights) * np.square(np.array(self.e.estimators) - estimate)) / np.square(
                np.sum(weights))
        else:
            total_variance = self.e.total_variance(weights = weights, retro = 0)
        return estimate, total_variance

    def sqrt_lure_mixer(self,gamma = 0.5, scale_var = False, simple_var = False):
        w1 = np.array(self.ais_weights)
        w2 = self.e.weights
        var = np.array(self.e.variance_estimates)
        if len(var) == 0:
            var = np.array([1])
        if np.sum(var) == 0.0:
            var = np.ones_like(var)
        min_positive = np.min(var[var > 0])
        var[var == 0] = min_positive
        processed_vars = self.process_variances(var.copy(), gamma)
        weights = w1 * w2
        estimate = self.e.estimate(weights = weights, )
        if scale_var:
            total_variance = np.sum(np.square(weights) * processed_vars) / np.square(np.sum(weights))
        elif simple_var:
            total_variance = np.sum(np.square(weights) * np.square(np.array(self.e.estimators)-estimate)) / np.square(np.sum(weights))
        else:
            total_variance = self.e.total_variance(weights=weights, retro=0)
        return estimate, total_variance

    def mixer(self, weights):
        estimate = self.e.estimate(weights = weights,)
        total_variance = self.e.total_variance(weights = weights,)
        return estimate, total_variance