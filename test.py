import os
os.environ['OMP_NUM_THREADS'] = '1' # speed up
import numpy as np
from MMO.problems.common import build_problem
from MMO.mobo.algorithms import get_algorithm
from MMO.visualization.data_export import DataExport
from MMO.arguments import get_args
from MMO.utils import save_args, setup_logger
import networkx as nx
import random, pickle, string
from src.util.gen_files import *
import time
from src.net.topology import NetTopology
from src.algorithm import *
import os, sys
from random import randint, shuffle, sample
from src.util.utils import *
from src.algorithm.cache import *
from src.util.separator_rank import *

sys.setrecursionlimit(2000000)
MAX_COUNT_INDEX = 3001946 # 3001946 3001946
from pymoo.optimize import minimize
from pymoo.algorithms.nsga2 import NSGA2
from pymoo.algorithms.moead import MOEAD

from simulation import *
import matplotlib.pyplot as pl


def main():
    jsonFile = "/home/picarib_home/cdn_configuration_optimization/config/json/sbd_custom.json"
    configDirPath = "/home/picarib_home/cdn_configuration_optimization/config/sbd_custom/"
    dataPath = "/home/picarib_home/cdn_configuration_optimization/data/"
    deleteCachePath = "/home/picarib_home/cdn_configuration_optimization/tmp/sbd_custom"    
    
    config = loadJSON(jsonFile)
    interval = 1 if "custom" not in config["RequestModels"] else config["RequestModels"]["custom"]["interval"]
    isLoadRTable = config["isLoadRTable"]
    isLoadSeparatorRank = config["isLoadSeparatorRank"]
    mode = config["RoutingMode"]  # [no-cache, no-color, tag-color, full-color]
    fileSize = config["FileSize"]
    runReqNums = config["RunReqNums"] if "RunReqNums" in config else -1
    warmUpReqNums = config["WarmUpReqNums"] if "WarmUpReqNums" in config else -1
    colorNums = config["colorNums"]
    separatorRankIncrement = config["separatorRankIncrement"]
    savePredefinedContent = os.path.join(deleteCachePath, "content.pkl")
    if os.path.isfile(savePredefinedContent):
        with open(savePredefinedContent, "rb") as f:
            generateData = pickle.load(f)
    else:
        generateData = {}
        for client in topo.clientIds:
            cacheId = client.replace("client", "Cache")
            generateData[cacheId] = {"noInterval": topo.contentGenerator.randomGen(runReqNums)}
        with open(savePredefinedContent, "wb") as f:
            pickle.dump(generateData, f)
    generateData = generateData
        
    colorList = [''.join(random.choices(string.ascii_uppercase + string.digits, k=6)) for i in range(colorNums)]
    
    topo = NetTopology(config, configDirPath, mode, warmUpReqNums, fileSize, colorList)
    topo.build()
    topo.reconfigTopology([1, 1, 1, 1])
    routingTable = {}
    traffic = runSimulationWithPredefinedDistribution(fileSize, mode, routingTable, topo, colorList, runReqNums, warmUpReqNums, separatorRankIncrement, generateData, 0)
    print(traffic)
    
if __name__ == '__main__':
    main()
