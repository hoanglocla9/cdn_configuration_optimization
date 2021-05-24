import autograd.numpy as anp

from .problem import Problem
from pymoo.util.normalization import normalize
import multiprocessing as mp
from simulation import *
# NUM_PROCESSORS = 4
import random, os, re

class CDN(Problem):
    ## 324, 5188
    def __init__ (self, n_var=4, n_obj=2, n_constr=0, xl=10, xu=180, min_cost=0.5, transformToInteger=False):
        super().__init__(n_var=n_var, n_obj=n_obj, n_constr=n_constr, xl=xl, xu=xu)
        self.min_cost = min_cost
        self.count_step = 0
        self.transformToInteger = transformToInteger
        
    def compute_y_bounds(self):
        performance_lower = 1.0 * self.performance_function([self.xu])
        cost_lower = self.cost_function([self.xl])
        performance_upper = 1.0 * self.performance_function([self.xl])
        cost_upper = self.cost_function([self.xu])
        
        self.performance_bounds = [performance_lower, performance_upper]
        self.cost_bounds = [cost_lower, cost_upper]
    
class CDN_PLACEMENT(CDN):
    def __init__(self, n_var=4, n_obj=2, n_constr=0, xl=0, xu=1, min_cost=0.5, transformToInteger=False):
        super().__init__(n_var=n_var, n_obj=n_obj, n_constr=n_constr, xl=xl, xu=xu, min_cost=min_cost, transformToInteger=transformToInteger)
        
    def _calc_pareto_front(self, n_pareto_points=100):
        raise "Not implement yet"

    def _evaluate(self, x, out,  *args, **kwargs):
        x_temp = np.round(x.copy())
        self.count_step += len(x_temp)
        if self.n_process > 1:
            performance = 1.0 * self.performance_function_parallel(x_temp)
        else:
            performance = 1.0 * self.performance_function(x_temp)
        cost = self.cost_function(x_temp)
        del x, x_temp
        normalized_performance = (performance - np.ones(performance.shape) * self.performance_bounds[0]) / (self.performance_bounds[1] - self.performance_bounds[0])
        normalized_cost = (cost - self.cost_bounds[0]) / (self.cost_bounds[1] - self.cost_bounds[0])
        out["F"] = np.column_stack([normalized_performance, normalized_cost])
        if not self.deleteCachePath is None:
            for f in os.listdir(self.deleteCachePath):
                if re.search("save_*", f):
                    os.remove(os.path.join(self.deleteCachePath, f))
            for f in os.listdir(self.deleteCachePath):
                if re.search("cacheDict*", f):
                    os.remove(os.path.join(self.deleteCachePath, f))
                    
    def get_parameters(self, topo, fileSize, mode, colorList, runReqNums, warmUpReqNums, separatorRankIncrement, n_process, deleteCachePath=None, interval=None):
        self.topo = topo
        self.fileSize = fileSize
        self.mode = mode
        self.colorList = colorList
        self.runReqNums = runReqNums
        self.warmUpReqNums = warmUpReqNums
        self.separatorRankIncrement = separatorRankIncrement
        self.n_process = n_process
        self.deleteCachePath = deleteCachePath
        self.interval = interval
        savePredefinedContent = os.path.join(self.deleteCachePath, "content.pkl")
        if interval is None:
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
        with open(os.path.join(self.deleteCachePath, "save_-1.pkl"), "wb") as f:
            pickle.dump(self.topo, f)
        
        self.compute_y_bounds()
    def performance_function_parallel(self, avaiableVector):
        dataList = []
        for i in range(len(avaiableVector)):
            randomIdx = random.randint(10000, 99999)
            save_data = [randomIdx, self.fileSize, self.mode, self.topo, self.colorList, self.runReqNums, self.warmUpReqNums, self.separatorRankIncrement, avaiableVector[i]]
            with open(os.path.join(self.deleteCachePath, "save_" + str(randomIdx) + ".pkl"), "wb") as f:
                pickle.dump(save_data, f)
            dataList.append(randomIdx)
        pool = mp.Pool(processes=self.n_process)
        results = pool.map(self.process_compute_perforamnce, dataList)
        
        pool.terminate()
        del pool, dataList
        return np.array(results)
    
    def process_compute_perforamnce(self, randomIdx):
        with open(os.path.join(self.deleteCachePath, "save_" + str(randomIdx) + ".pkl"), "rb") as f:
            data = pickle.load(f)
                
        idx, fileSize, mode, topo, colorList, runReqNums, warmUpReqNums, separatorRankIncrement, avaiableVector = data
        topo.reconfigTopology(avaiableVector, idx)
        
        routingTable = {}
        if not self.interval is None:
            traffic = runSimulationWithRealDataset(self.interval, fileSize, mode, routingTable, topo, colorList, runReqNums, warmUpReqNums, separatorRankIncrement)
        else:
            traffic = runSimulationWithPredefinedDistribution(fileSize, mode, routingTable, topo, colorList, runReqNums, warmUpReqNums, separatorRankIncrement, self.generateData, idx)

       
        del data, fileSize, mode, topo, colorList, runReqNums, warmUpReqNums, separatorRankIncrement, avaiableVector
        return int(traffic)
 
    def performance_function(self, avaiableVector):
        results = []
        with open(os.path.join(self.deleteCachePath, "save_-1.pkl"), "rb") as f:
            topo = pickle.load( f)
        for i in range(len(avaiableVector)):
            topo.reconfigTopology(avaiableVector[i], 0)
            routingTable = {}
            if not self.interval is None:
                traffic = runSimulationWithRealDataset(self.interval, self.fileSize, self.mode, routingTable, topo, self.colorList, self.runReqNums, self.warmUpReqNums, self.separatorRankIncrement)
            else:
                traffic = runSimulationWithPredefinedDistribution(self.fileSize, self.mode, routingTable, topo, self.colorList, self.runReqNums, self.warmUpReqNums, self.separatorRankIncrement, self.generateData, 0)
            results.append(traffic)
        
        return np.array(results)
    
    def cost_function(self, avaiableVector):
        result = []
        for i in range(len(avaiableVector)):
            result.append(int(sum(avaiableVector[i])))
        
        return np.array(result)
    
    
    
class CDN_RAM(CDN):
    def _calc_pareto_front(self, n_pareto_points=100):
        raise "Not implement yet"

    def _evaluate(self, x, out,  *args, **kwargs):
        x_temp = np.round(x.copy())
        self.count_step += len(x_temp)
        if self.n_process > 1:
            performance = 1.0 * self.performance_function_parallel(x_temp)
        else:
            performance = 1.0 * self.performance_function(x_temp)
        cost = self.cost_function(x_temp)
        del x, x_temp
        normalized_performance = (performance - np.ones(performance.shape) * self.performance_bounds[0]) / (self.performance_bounds[1] - self.performance_bounds[0])
        normalized_cost = (cost - self.cost_bounds[0]) / (self.cost_bounds[1] - self.cost_bounds[0])

        out["F"] = np.column_stack([normalized_performance, normalized_cost])
#         out["G"] = int(self.min_cost * (80*1024-10*1024) + 10 *1024) - cost
        if not self.deleteCachePath is None:
            for f in os.listdir(self.deleteCachePath):
                if re.search("save_*", f):
                    os.remove(os.path.join(self.deleteCachePath, f))
            for f in os.listdir(self.deleteCachePath):
                if re.search("cacheDict*", f):
                    os.remove(os.path.join(self.deleteCachePath, f)) # "./config/sbd_custom"
                    
    def get_parameters(self, topo, fileSize, mode, colorList, runReqNums, warmUpReqNums, separatorRankIncrement, n_process, deleteCachePath=None, interval=None):
        self.topo = topo
        self.fileSize = fileSize
        self.mode = mode
        self.colorList = colorList
        self.runReqNums = runReqNums
        self.warmUpReqNums = warmUpReqNums
        self.separatorRankIncrement = separatorRankIncrement
        self.n_process = n_process
        self.deleteCachePath = deleteCachePath
        self.interval = interval
        savePredefinedContent = os.path.join(self.deleteCachePath, "content.pkl")
        if interval is None:
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
        with open(os.path.join(self.deleteCachePath, "save_-1.pkl"), "wb") as f:
            pickle.dump(self.topo, f)
            
        self.compute_y_bounds()
        
    def performance_function_parallel(self, cacheSizeFactorList):
        dataList = []
        for i in range(len(cacheSizeFactorList)):
            temp = [0] * (len(cacheSizeFactorList[i]))
            for j in range(len(cacheSizeFactorList[i])):
                temp[j] = int(cacheSizeFactorList[i][j] * 1024) # 982013
            randomIdx = random.randint(10000, 99999)
            save_data = [randomIdx, self.fileSize, self.mode, self.topo, self.colorList, self.runReqNums, self.warmUpReqNums, self.separatorRankIncrement, temp]
            
            with open(os.path.join(self.deleteCachePath, "save_" + str(randomIdx) + ".pkl"), "wb") as f:
                pickle.dump(save_data, f)
            dataList.append(randomIdx)
        pool = mp.Pool(processes=self.n_process)
        results = pool.map(self.process_compute_perforamnce, dataList)
        
        pool.terminate()
        del pool, dataList
        return np.array(results)
    def process_compute_perforamnce(self, randomIdx):
        with open(os.path.join(self.deleteCachePath, "save_" + str(randomIdx) + ".pkl"), "rb") as f:
            data = pickle.load(f)
            
        idx, fileSize, mode, topo, colorList, runReqNums, warmUpReqNums, separatorRankIncrement, cacheSizeFactorList = data
        topo.reconfigRam(cacheSizeFactorList, idx)
        routingTable = {}
        if not self.interval is None:
            traffic = runSimulationWithRealDataset(self.interval, fileSize, mode, routingTable, topo, colorList, runReqNums, warmUpReqNums, separatorRankIncrement)
        else:
            traffic = runSimulationWithPredefinedDistribution(fileSize, mode, routingTable, topo, colorList, runReqNums, warmUpReqNums, separatorRankIncrement, self.generateData, idx)

       
        del data, fileSize, mode, topo, colorList, runReqNums, warmUpReqNums, separatorRankIncrement, cacheSizeFactorList
        return int(traffic)
 
    def performance_function(self, cacheSizeFactorList):
        with open(os.path.join(self.deleteCachePath, "save_-1.pkl"), "rb") as f:
            topo = pickle.load( f)
            
        results = []
        for i in range(len(cacheSizeFactorList)):
            temp = [0] * (len(cacheSizeFactorList[i]))
            for j in range(len(cacheSizeFactorList[i])):
                temp[j] = int(cacheSizeFactorList[i][j] * 1024) # * (800*1024-100*1024) + 100 *1024
            topo.reconfigRam(temp, 0)
            routingTable = {}
            if not self.interval is None:
                traffic = runSimulationWithRealDataset(self.interval, self.fileSize, self.mode, routingTable, topo, self.colorList, self.runReqNums, self.warmUpReqNums, self.separatorRankIncrement)
            else:
                traffic = runSimulationWithPredefinedDistribution(self.fileSize, self.mode, routingTable, topo, self.colorList, self.runReqNums, self.warmUpReqNums, self.separatorRankIncrement, self.generateData, 0)
            results.append(traffic)
        
        return np.array(results)
    
    def cost_function(self, cacheSizeFactorList):
        result = []
        for i in range(len(cacheSizeFactorList)):
            temp = [0] * (len(cacheSizeFactorList[i]))
            for j in range(len(cacheSizeFactorList[i])):
                temp[j] = int(cacheSizeFactorList[i][j]) # (800*1024-100*1024) + 100*1024
            result.append(int(sum(temp)))
        
        return np.array(result)
