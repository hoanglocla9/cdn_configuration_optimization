import numpy as np
from pymoo.model.problem import Problem
from src.optimize.func import *
from simulation import *
import pickle
import multiprocessing as mp
NUM_PROCESSORS = 8

class CDNOptimizationProblem(Problem):
    def __init__ (self, n_var=2, n_obj=2, n_constr=1, xl=0, xu=10, min_cost=1000):
        super().__init__(n_var=n_var, n_obj=n_obj, n_constr=n_constr, xl=xl, xu=xu)
        self.min_cost = min_cost
        
        
    def _evaluate(self, x, out, *args, **kwargs):
        performance = -1.0 * self.performance_function(x)
        cost =  self.cost_function(x)
        out["F"] = np.column_stack([performance, cost])
        out["G"] = self.cost_function(x) - self.min_cost
        
    def get_parameters(self, topo, net, fileSize, mode, colorList, runReqNums, warmUpReqNums, separatorRankIncrement):
        self.net = net
        self.topo = topo
        self.fileSize = fileSize
        self.mode = mode
        self.colorList = colorList
        self.runReqNums = runReqNums
        self.warmUpReqNums = warmUpReqNums
        self.separatorRankIncrement = separatorRankIncrement
        
    def performance_function(self, cacheSizeFactorList):
        print("Start stage")
        for i in range(len(cacheSizeFactorList)):
#             print("** Compute step " + str(i) + "/" + str(len(cacheSizeFactorList)))
            for j in range(len(cacheSizeFactorList[i])):
                cacheSizeFactorList[i][j] = cacheSizeFactorList[i][j] * 1024 * 1024 * 1024 * 2
            with open("./tmp/save_" + str(i), "wb") as f:
                save_data = [self.fileSize, self.mode, self.net, self.topo, self.colorList, self.runReqNums, self.warmUpReqNums, self.separatorRankIncrement, cacheSizeFactorList[i]]
                pickle.dump(save_data, f)
                
        print("** Start parallel")
        pool = mp.Pool(processes=NUM_PROCESSORS)
        results = pool.map(self.process_compute_perforamnce, range(len(cacheSizeFactorList)))
        
        print("Done stage")
        return np.array(results)
    
    def process_compute_perforamnce(self, idx):
#         return 0
        with open("./tmp/save_" + str(idx), "rb") as f:
            data = pickle.load(f)
        fileSize, mode, net, topo, colorList, runReqNums, warmUpReqNums, separatorRankIncrement, cacheSizeFactorList = data
        topo.reconfig(cacheSizeFactorList)
        net.reconfig(topo, idx)
        routingTable = {}
        traffic = runSimulationWithPredefinedDistribution(fileSize, mode, routingTable, net, colorList, runReqNums, warmUpReqNums, separatorRankIncrement, idx)
        return int(traffic)
    
    def cost_function(self, cacheSizeFactorList):
        result = []
        for i in range(len(cacheSizeFactorList)):
            for j in range(len(cacheSizeFactorList[i])):
                cacheSizeFactorList[i][j] = cacheSizeFactorList[i][j] * 1024 * 1024
            result.append(int(sum(cacheSizeFactorList[i])))
        return np.array(result)