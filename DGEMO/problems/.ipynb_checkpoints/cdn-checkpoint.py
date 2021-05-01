import autograd.numpy as anp

from .problem import Problem
from pymoo.util.normalization import normalize
import multiprocessing as mp
from simulation import *
# NUM_PROCESSORS = 4
import random, os, re

class CDN(Problem):
    def __init__ (self, n_var=4, n_obj=2, n_constr=0, xl=10, xu=80, min_cost=0.5):
        super().__init__(n_var=n_var, n_obj=n_obj, n_constr=n_constr, xl=xl, xu=xu)
        self.min_cost = min_cost
        self.count_step = 0
        
class CDN_RAM(CDN):
    def _calc_pareto_front(self, n_pareto_points=100):
        raise "Not implement yet"

    def _evaluate(self, x, out,  *args, **kwargs):
        x_temp = x.copy()
        self.count_step += len(x_temp)

        if self.n_process > 1:
            performance = 1.0 * self.performance_function_parallel(x)
        else:
            performance = 1.0 * self.performance_function(x)
        cost = self.cost_function(x_temp)
        del x, x_temp
        out["F"] = np.column_stack([performance, cost/1024])
#         out["G"] = int(self.min_cost * (80*1024-10*1024) + 10 *1024) - cost
        if self.deleteCachePath:
            for f in os.listdir("./tmp/"):
                if re.search("save_*", f):
                    os.remove(os.path.join("./tmp", f))
            for f in os.listdir(self.deleteCachePath):
                if re.search("cacheDict*", f):
                    os.remove(os.path.join(self.deleteCachePath, f)) # "./config/sbd_custom"
                    
    def get_parameters(self, topo, fileSize, mode, colorList, runReqNums, warmUpReqNums, separatorRankIncrement, n_process, deleteCachePath=None):
        self.topo = topo
        self.fileSize = fileSize
        self.mode = mode
        self.colorList = colorList
        self.runReqNums = runReqNums
        self.warmUpReqNums = warmUpReqNums
        self.separatorRankIncrement = separatorRankIncrement
        self.n_process = n_process
        self.deleteCachePath = deleteCachePath
        savePredefinedContent = os.path.join("tmp/", "save_content.pkl")
        if os.path.isfile(savePredefinedContent):
            with open(savePredefinedContent, "rb") as f:
                generateData = pickle.load(f)
        else:
            generateData = {}
            for client in self.topo.clientIds:
                cacheId = client.replace("client", "Cache")
                generateData[cacheId] = {"noInterval": self.topo.contentGenerator.randomGen(self.runReqNums)}
            with open(savePredefinedContent, "wb") as f:
                pickle.dump(generateData, f)
        self.generateData = generateData
        
    def performance_function_parallel(self, cacheSizeFactorList):
        randomIdxList = []
        for i in range(len(cacheSizeFactorList)):
            temp = [0] * (len(cacheSizeFactorList[i]))
            for j in range(len(cacheSizeFactorList[i])):
                temp[j] = int(cacheSizeFactorList[i][j] * 1024)
            randomIdx = random.randint(10000, 99999)
            with open("./tmp/save_" + str(randomIdx), "wb") as f:
                save_data = [self.fileSize, self.mode, self.topo, self.colorList, self.runReqNums, self.warmUpReqNums, self.separatorRankIncrement, temp]
                pickle.dump(save_data, f)
            del save_data
            randomIdxList.append(randomIdx)
        pool = mp.Pool(processes=self.n_process)
        results = pool.map(self.process_compute_perforamnce, randomIdxList)

        pool.terminate()
        del pool
        return np.array(results)
    def process_compute_perforamnce(self, idx):
        with open("./tmp/save_" + str(idx), "rb") as f:
            data = pickle.load(f)
        fileSize, mode, topo, colorList, runReqNums, warmUpReqNums, separatorRankIncrement, cacheSizeFactorList = data
        topo.reconfig(cacheSizeFactorList, idx)
        routingTable = {}
        traffic = runSimulationWithPredefinedDistribution(fileSize, mode, routingTable, topo, colorList, runReqNums, warmUpReqNums, separatorRankIncrement, self.generateData, idx)

       
        del data, fileSize, mode, topo, colorList, runReqNums, warmUpReqNums, separatorRankIncrement, cacheSizeFactorList
        return int(traffic)
 
    def performance_function(self, cacheSizeFactorList):
        results = []
        for i in range(len(cacheSizeFactorList)):
            temp = [0] * (len(cacheSizeFactorList[i]))
            for j in range(len(cacheSizeFactorList[i])):
                temp[j] = int(cacheSizeFactorList[i][j] * 1024) # * (800*1024-100*1024) + 100 *1024
            self.topo.reconfig(temp)
            routingTable = {}
            traffic = runSimulationWithPredefinedDistribution(self.fileSize, self.mode, routingTable, self.topo, self.colorList, self.runReqNums, self.warmUpReqNums, self.separatorRankIncrement, self.generateData, 0)
            results.append(traffic)
        
        return np.array(results)
    
    def cost_function(self, cacheSizeFactorList):
        result = []
        for i in range(len(cacheSizeFactorList)):
            temp = [0] * (len(cacheSizeFactorList[i]))
            for j in range(len(cacheSizeFactorList[i])):
                temp[j] = int(cacheSizeFactorList[i][j] * 1024) # (800*1024-100*1024) + 100*1024
            result.append(int(sum(temp)))
        
        return np.array(result)
