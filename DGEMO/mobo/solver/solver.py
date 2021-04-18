import numpy as np
from pymoo.optimize import minimize
from pymoo.util.nds.non_dominated_sorting import NonDominatedSorting
from pymoo.operators.sampling.random_sampling import FloatRandomSampling
from pymoo.operators.sampling.latin_hypercube_sampling import LatinHypercubeSampling
from DGEMO.external import lhs
from pymoo.factory import  get_crossover, get_mutation

class Solver:
    '''
    Multi-objective solver
    '''
    def __init__(self, n_gen, pop_init_method, batch_size, algo, **kwargs):
        '''
        Input:
            n_gen: number of generations to solve
            pop_init_method: method to initialize population
            algo: class of multi-objective algorithm to use
            kwargs: other keyword arguments for algorithm to initialize
        '''
        self.n_gen = n_gen
        self.pop_init_method = pop_init_method
        self.batch_size = batch_size
        self.algo_type = algo
        self.algo_kwargs = kwargs
        self.solution = None

    def solve(self, problem, X, Y, useInteger, bound=None):
        '''
        Solve the multi-objective problem
        '''
        # initialize population
        sampling = self._get_sampling(X, Y, bound)
        if useInteger and bound is None:
            print("error solver!!!") 
            return
        # setup algorithm
        if useInteger:
            algo = self.algo_type(sampling=sampling,
                      crossover=get_crossover("int_one_point"),
                      mutation=get_mutation("int_pm", prob=1/X.shape[1]))
        else:
            algo = self.algo_type(sampling=sampling, **self.algo_kwargs)

        # optimization
        res = minimize(problem, algo, ('n_gen', self.n_gen))

        # construct solution
        self.solution = {'x': res.pop.get('X'), 'y': res.pop.get('F'), 'algo': res.algorithm}

        # fill the solution in case less than batch size
        pop_size = len(self.solution['x'])
        if pop_size < self.batch_size:
            indices = np.concatenate([np.arange(pop_size), np.random.choice(np.arange(pop_size), self.batch_size - pop_size)])
            self.solution['x'] = np.array(self.solution['x'])[indices]
            self.solution['y'] = np.array(self.solution['y'])[indices]
        return self.solution

    def _get_sampling(self, X, Y, bound=None):
        '''
        Initialize population from data
        '''
        if self.pop_init_method == 'lhs':
            sampling = LatinHypercubeSampling()
        elif self.pop_init_method == 'nds':
            sorted_indices = NonDominatedSorting().do(Y)
            pop_size = self.algo_kwargs['pop_size']
            sampling = X[np.concatenate(sorted_indices)][:pop_size]
            # NOTE: use lhs if current samples are not enough
            if len(sampling) < pop_size:
                if bound is None:
                    rest_sampling = lhs(X.shape[1], pop_size - len(sampling))
                else:
                    rest_sampling = lhs(X.shape[1], pop_size - len(sampling))
                    rest_sampling = bound[0] + rest_sampling * (bound[1] - bound[0])
                    rest_sampling = np.round(rest_sampling)
                sampling = np.vstack([sampling, rest_sampling])
        elif self.pop_init_method == 'random':
            sampling = FloatRandomSampling()
        else:
            raise NotImplementedError

        return sampling


