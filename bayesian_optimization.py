import os
os.environ['OMP_NUM_THREADS'] = '1' # speed up
import numpy as np
from DGEMO.problems.common import build_problem
from DGEMO.mobo.algorithms import get_algorithm
from DGEMO.visualization.data_export import DataExport
from DGEMO.arguments import get_args
from DGEMO.utils import save_args, setup_logger
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

import matplotlib.pyplot as pl


def main():
    jsonFile = "/home/loclh/cdn_configuration_optimization/config/json/france_cdn.json"
    configDirPath = "/home/loclh/cdn_configuration_optimization/config/france_cdn/"
    dataPath = "/home/loclh/cdn_configuration_optimization/data/"
    
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
    
    colorList = [''.join(random.choices(string.ascii_uppercase + string.digits, k=6)) for i in range(colorNums)]
    
    topo = NetTopology(config, configDirPath, mode, warmUpReqNums, fileSize, colorList)
    topo.build()
    
    # load arguments
    args, framework_args = get_args()

    # set seed
    np.random.seed(args.seed)

    # build problem, get initial samples
    extra_params = (topo, fileSize, mode, colorList, runReqNums, warmUpReqNums, separatorRankIncrement)
    problem, X_init, Y_init = build_problem(args.problem, args.n_var, args.n_obj, args.n_init_sample, args.n_process, extra_params=extra_params)
    
    args.n_var, args.n_obj = problem.n_var, problem.n_obj
    print("Start the optimizer")
    # initialize optimizer
    optimizer = get_algorithm(args.algo)(problem, args.n_iter, args.ref_point, framework_args)

    # save arguments & setup logger
    save_args(args, framework_args)
    logger = setup_logger(args)
    print(problem, optimizer, sep='\n')
    
    # initialize data exporter
    exporter = DataExport(optimizer, X_init, Y_init, args)

    # optimization
    solution = optimizer.solve(X_init, Y_init)

    # export true Pareto front to csv
#     if true_pfront is not None:
#         exporter.write_truefront_csv(true_pfront)

    for _ in range(args.n_iter):
        # get new design samples and corresponding performance
        X_next, Y_next, _ = next(solution)
        
        # update & export current status to csv
        exporter.update(X_next, Y_next)
        exporter.write_csvs()

    # close logger
    if logger is not None:
        logger.close()


if __name__ == '__main__':
    main()
