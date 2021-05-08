from src.util.utils import *
from src.algorithm.cache import *
import networkx as nx 
from src.util.gen_files import *
from src.util.coloring import *
import pickle , random
from src.util.separator_rank import *
from src.util.sampling import ReservoirSampling

class NetTopology (object):
    def __init__( self, config, configDirPath, mode, warmUpReqNums, fileSize, colorList=None):
        self.networkInfo = config
        self.configDirPath = configDirPath
        self.graph = nx.Graph()
        self.warmUpReqNums = warmUpReqNums
        
        self.parallel_idx = 0
        self.colorList = colorList
        self.serverToColorMap = {}
        self.mode = mode
        self.cacheMemoryDict = {}
        self.fileSize = fileSize
        
    def saveCacheDict(self):
        with open(os.path.join(self.configDirPath, "cacheDict.pkl"), 'wb') as f:
            pickle.dump(self.cacheMemoryDict, f)
            
    def reconfigRam(self, cacheSizeList, parallel_idx=0):
        self.cacheMemoryDict = {}
        idx = 0
        self.parallel_idx = parallel_idx
        for routerInfo in self.networkInfo["Routers"]:
            if "type" in routerInfo:
                routerId = routerInfo["ID"]
                newSize = cacheSizeList[idx]
                maxSize = float(newSize) * self.alpha
                if routerInfo["type"] == "LRU":
                    self.cacheMemoryDict[routerId] = LRUCache(maxSize)
                elif routerInfo["type"] == "LFU":
                    self.cacheMemoryDict[routerId] = LFUCache(maxSize)
                elif routerInfo["type"] == "FIFO":
                    self.cacheMemoryDict[routerId] = FIFOCache(maxSize) 
                elif routerInfo["type"] == "Hybrid":
                    self.cacheMemoryDict[routerId] = ColorCache(None, routerInfo["capacityRatio"] , maxSize)
                idx += 1
        self.warmUp()
       
        
    def reconfigTopology(self, avaiableVector, parallel_idx=0):
        self.parallel_idx = parallel_idx
        for idx, status in enumerate(avaiableVector):
            if status == 0:
                self.cacheMemoryDict["router_" + str(idx+1)] = None
            
        self.warmUp()
    
    def warmUp(self, savedFile="tmp/warmUpFile.pkl"):
        if self.mode == "no-cache":
            pass
        elif self.mode == "no-color":
            routingTable = {}
            if os.path.isfile(savedFile):
                with open(savedFile, "rb") as f:
                    warmUpReqDict = pickle.load(f)
            else:
                warmUpReqDict = {}
                for client in self.clientIds:
                    if self.contentGenerator.dist != None:
                        warmUpReqDict[client] = self.contentGenerator.randomGen(self.warmUpReqNums)
                    else:
                        cache = client.replace("client", "Cache")
                        warmUpReqDict[client] = self.contentGenerator.custom_data[cache]["Interval0"]
                with open(savedFile, "wb") as f:
                    pickle.dump(warmUpReqDict, f)
            warmUpCacheShortestPath(self.graph, self.cacheMemoryDict, self.fileSize, self.mode, routingTable, warmUpReqDict, warmUpReqDict.keys())
            self.saveCacheDict()  
        elif self.mode == "tag-color":
            self.colorRouteInfo, self.serverToColorMap = getColoringInfo(self.graph, self.colorList)
            self.assignColorForCacheMemory()
        else:
            self.colorRouteInfo, self.serverToColorMap = getColoringInfo(self.graph, self.colorList)
            self.assignColorForCacheMemory()
            self.saveNearestColorServerInfo()
            
        
                
    def saveNearestColorServerInfo(self):
        with open(os.path.join(self.configDirPath, "nearestColorServerInfo.pkl"), "wb") as f:
            pickle.dump(self.colorRouteInfo, f)
            
    def assignColorForCacheMemory(self):
        for server in self.serverToColorMap:
            colorId = self.serverToColorMap[server]
            self.cacheMemoryDict[server].setServerColor(colorId)
            
    def build(self):
        self.cacheMemoryDict = {}
        self.clientIds = []
        self.routerIds = []
        self.tempClientIds = ["mainClone"]
        print( '*** Processing content list\n')
        if self.networkInfo["samplingMethod"] != None:
            sampleMethod = self.networkInfo["samplingMethod"]["method"]
            if sampleMethod == "reservoir":
                sampleGen = ReservoirSampling(self.networkInfo["samplingMethod"]["sampleRate"])
            else:
                sampleGen = None
        else:
            sampleGen = None
            
        fixedFileSize = self.networkInfo["FileSize"]
        
        if "custom" not in self.networkInfo["RequestModels"]:
            if "gamma" in self.networkInfo["RequestModels"]:
                dist = GammaDistribution(K=self.networkInfo["RequestModels"]["gamma"]["K"], 
                                     theta=self.networkInfo["RequestModels"]["gamma"]["Theta"], 
                                     length=self.networkInfo["RequestModels"]["gamma"]["contentNums"],
                                     sampleGen = sampleGen)
            elif "zipf" in self.networkInfo["RequestModels"]:
                dist = ZipfDistribution(skewness=self.networkInfo["RequestModels"]["zipf"]["Skewness"], 
                                     length=self.networkInfo["RequestModels"]["zipf"]["contentNums"],
                                       sampleGen=sampleGen)
            self.contentGenerator = ContentGenerator(dist=dist, fixedContentSize=fixedFileSize)
            self.alpha = 1.0
        else:
            
            self.alpha = float(self.networkInfo["RequestModels"]["custom"]["alpha"]) if fixedFileSize == -1 else 1.0
            self.contentGenerator = ContentGenerator(data_path=self.networkInfo["RequestModels"]["custom"]["path"],
                                                    fixedContentSize=fixedFileSize,
                                                    sampleGen=sampleGen,
                                                    alpha=self.alpha)
        for routerInfo in self.networkInfo["Routers"]:
            routerId = routerInfo["ID"]
            self.routerIds.append(routerId)
            self.graph.add_node(routerId, ip=routerInfo["IP"])
            if "type" in routerInfo:
                maxSize = float(routerInfo["maxSize"]) * self.alpha
                if routerInfo["type"] == "LRU":
                    self.cacheMemoryDict[routerId] = LRUCache(maxSize)
                elif routerInfo["type"] == "LFU":
                    self.cacheMemoryDict[routerId] = LFUCache(maxSize)
                elif routerInfo["type"] == "FIFO":
                    self.cacheMemoryDict[routerId] = FIFOCache(maxSize) 
                elif routerInfo["type"] == "Hybrid":
                    self.cacheMemoryDict[routerId] = ColorCache(None, routerInfo["capacityRatio"] , maxSize)
                
        self.routerIds.remove("mainServer")
        
        for clientInfo in self.networkInfo['Clients']:
            clientId = clientInfo['ID']
            self.clientIds.append(clientId)
            self.graph.add_node(clientId, ip=clientInfo["IP"], gw=clientInfo['gateway'])
            if clientInfo['isTemp']:
                self.tempClientIds.append(clientId)
                
        
        for idx, linkInfo in enumerate(self.networkInfo['Links']):
            nodeIds = linkInfo['NodeIds']
            nodeId_1, interface_1 = nodeIds[0].split("/")
            params1Info = linkInfo['params1']
            if 'params2' in linkInfo:
                nodeId_2, _ = nodeIds[1].split("/")
                self.graph.add_edge(nodeId_1, nodeId_2, weight=1.0)
    
            else:
                nodeId_2 = nodeIds[1]
                self.graph.add_edge(nodeId_1, nodeId_2, weight=1.0)
        self.warmUp()