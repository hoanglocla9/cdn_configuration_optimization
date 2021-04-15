import networkx as nx
import random, pickle, string
from src.util.gen_files import *
import threading
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

def findColorCacheServer(graph, nearestColorServerInfo, currentCacheId, contentColor, packetPath):
    for entryInfo in nearestColorServerInfo[currentCacheId]:
        cacheColor = entryInfo["color"]
        cacheId = entryInfo["node"]
        cacheIdx = cacheId.split("_")[1]
        if packetPath[int(cacheIdx)-1] == "1":
            continue
        if int(contentColor, 2) & int(cacheColor, 2) != 0:
            return cacheId
    return None

def findShortestCacheServer(graph, sourceId, targetId, routingTable):
    if sourceId not in routingTable:
        cacheIdPath = nx.dijkstra_path(graph, sourceId, targetId, "weight") # 
        routingTable[sourceId] = {targetId: cacheIdPath[1]}
        return cacheIdPath[1]
    else:
        if targetId not in routingTable[sourceId]:
            cacheIdPath = nx.dijkstra_path(graph, sourceId, targetId, "weight") # , "weight"
            routingTable[sourceId] = {targetId: cacheIdPath[1]}
            return cacheIdPath[1]
        else:
            return routingTable[sourceId][targetId]
    

def processRequestFlow(sourceCacheId, cacheDict, graph, nearestColorServerInfo, serverToColorMap, contentId, contentColor, routingTable, hitMissDict):
    packetPath = ["0"] * len(cacheDict.keys())
    
    currentCacheId = sourceCacheId
    while True:
        if currentCacheId == "mainServer":
            return currentCacheId, hitMissDict
        if cacheDict[currentCacheId].get(contentId, contentColor) != -1:
            hitMissDict[currentCacheId] = {"hit":1, "miss": 0}
            return currentCacheId, hitMissDict
        else:
            hitMissDict[currentCacheId] = {"hit":0, "miss": 1}
                
            currentCacheIdx = currentCacheId.split("_")[1]
            packetPath[int(currentCacheIdx)-1] = "1"
            nextColorId = findColorCacheServer(graph, nearestColorServerInfo, currentCacheId, contentColor, packetPath)
            if nextColorId == None:
                currentCacheId = findShortestCacheServer(graph, currentCacheId, "mainServer", routingTable)
            else:
                tempCacheId = currentCacheId
                currentCacheId = findShortestCacheServer(graph, currentCacheId, nextColorId, routingTable)
                if currentCacheId != "mainServer":
                    currentCacheIdx = currentCacheId.split("_")[1]
                    if packetPath[int(currentCacheIdx)-1] == "1":
                        currentCacheId = findShortestCacheServer(graph, tempCacheId, "mainServer", routingTable)
                    
    
def processResponseFlow(targetCacheId, sourceCacheId, cacheDict, graph, contentId, contentColor, fileSize):
    cacheIdPath = nx.dijkstra_path(graph, targetCacheId, sourceCacheId, "weight")
    cacheIdPath = cacheIdPath[1:]
    traffic = 0
    for cacheId in cacheIdPath:
        traffic += 1
        if cacheId == "mainServer":
            return traffic
        
        if cacheDict[cacheId].get(contentId, contentColor) == -1:
            cacheDict[cacheId].set(contentId, contentColor, fileSize)
        
    return traffic

def runVirtualSendFileColorBased(graph, cacheDict, client, contentId, contentColor, nearestColorServerInfo, 
                       serverToColorMap, fileSize, routingTable):
    result = {}
    traffic = 0
    sourceCacheId = client.replace("client_", "router_")
    targetCacheId, result = processRequestFlow(sourceCacheId, cacheDict, graph, nearestColorServerInfo, serverToColorMap, contentId, contentColor, routingTable, result)    
    traffic += processResponseFlow(targetCacheId, sourceCacheId, cacheDict, graph, contentId, contentColor, fileSize)
    
    return result, traffic


def runWithColorRouting(graph, cacheDict, contentToColorDict, nearestColorServerInfo, 
                               serverToColorMap, fileSize, routingTable, runReqDict, clientList=[], interval=""):
    result = {}
    idx = 0
    totalTraffic = 0
    while True:
        isEnd = True
        for client in clientList:
            cacheId = client.replace("client_", "Cache_")
            if idx >= len(runReqDict[cacheId][interval]):
                continue
            if fileSize != -1:
                contentId = runReqDict[cacheId][interval][idx][0] ###
                _fileSize = fileSize
            else:
                contentId, _fileSize, _ = runReqDict[cacheId][interval][idx]
            contentColor = contentToColorDict[contentId]
            hitMissDict, traffic = runVirtualSendFileColorBased(graph, cacheDict, client, contentId, contentColor, 
                               nearestColorServerInfo, serverToColorMap, int(_fileSize), routingTable)
            if int(contentId) > MAX_COUNT_INDEX:
                for routerId in hitMissDict:
                    if routerId in result:
                        result[routerId]["hit"] += hitMissDict[routerId]["hit"]
                        result[routerId]["miss"] += hitMissDict[routerId]["miss"]
                    else:
                        result[routerId] = {"hit": hitMissDict[routerId]["hit"], "miss": hitMissDict[routerId]["miss"]}
                        
            isEnd = False
            totalTraffic += traffic
        if isEnd:
            break
        idx+= 1
            
    return result, totalTraffic

def runVirtualSendFileShortestPath(graph, cacheDict, client, contentId, fileSize, routingTable, mode="no-color", contentColor=""):
    traffic = 0
    nextCacheId = client.replace("client_", "router_")
    result = {}
    result[nextCacheId] = {"hit": 0, "miss": 0} 
    
    if mode == "no-cache":
        shortestRoutePath = nx.dijkstra_path(graph, nextCacheId, "mainServer", "weight")
        shortestRoutePath = shortestRoutePath[1:] 
        for routerId in shortestRoutePath:
            traffic += 1
            if routerId == "mainServer":
                break
        return {}, traffic
    
    if mode== "no-color":
        if cacheDict[nextCacheId].get(contentId) != -1:
            result[nextCacheId]["hit"] = 1 
            return result, traffic
        else:
            cacheDict[nextCacheId].set(contentId, fileSize)
            result[nextCacheId]["miss"] = 1
            
        while True:
            routerId = findShortestCacheServer(graph, nextCacheId, "mainServer", routingTable)
            result[routerId] = {"hit": 0, "miss": 0} 
            traffic += 1
            if routerId == "mainServer":
                return result, traffic
            else:
                if cacheDict[routerId].get(contentId) == -1:
                    result[routerId]["miss"] = 1 
                    cacheDict[routerId].set(contentId, fileSize)
                else:
                    result[routerId]["hit"] = 1
                    return result, traffic
            nextCacheId = routerId
    else: ## mode == "tag-color"
        if cacheDict[nextCacheId].get(contentId, contentColor) != -1:
            result[nextCacheId]["hit"] = 1 
            return result, traffic
        else:
            cacheDict[nextCacheId].set(contentId, contentColor, fileSize)
            result[nextCacheId]["miss"] = 1
            
        while True:
            routerId = findShortestCacheServer(graph, nextCacheId, "mainServer", routingTable)
            traffic += 1
            result[routerId] = {"hit": 0, "miss": 0}
            if routerId == "mainServer":
                return result, traffic
            else:
                if cacheDict[routerId].get(contentId, contentColor) == -1:
                    result[routerId]["miss"] = 1 
                    cacheDict[routerId].set(contentId, contentColor, fileSize)
                else:
                    result[routerId]["hit"] = 1
                    return result, traffic
            nextCacheId = routerId
    
def runWithShortestPath(graph, cacheDict, fileSize, mode, routingTable, runReqDict, clientList, interval, contentToColorDict=None):
    result = {}
    totalTraffic = 0
    idx = 0
    while True:
        isEnd = True
        for client in clientList:
            cacheId = client.replace("client_", "Cache_")
            if idx >= len(runReqDict[cacheId][interval]):
                continue
            if fileSize != -1:
                contentId = runReqDict[cacheId][interval][idx][0]
                _fileSize = fileSize
            else:
                contentId, _fileSize, _ = runReqDict[cacheId][interval][idx]
            if mode == "tag-color":
                contentColor = str(contentToColorDict[contentId])
            else:
                contentColor = ""
            hitMissDict, traffic = runVirtualSendFileShortestPath(graph, cacheDict, client, contentId, _fileSize, routingTable, mode, contentColor)
            if int(contentId) > MAX_COUNT_INDEX:
                for routerId in hitMissDict:
                    if routerId in result:
                        result[routerId]["hit"] += hitMissDict[routerId]["hit"]
                        result[routerId]["miss"] += hitMissDict[routerId]["miss"]
                    else:
                        result[routerId] = {"hit": hitMissDict[routerId]["hit"], "miss": hitMissDict[routerId]["miss"]}
            totalTraffic += traffic
            isEnd = False
        if isEnd:
            break
        idx += 1
    return result, totalTraffic



def reAssignCacheDict(config):
    cacheMemoryDict = {}
    for routerInfo in config["Routers"]:
        routerId = routerInfo["ID"]
        if "type" in routerInfo:
            if routerInfo["type"] == "LRU":
                cacheMemoryDict[routerId] = {"type": "LRU", "memory": LRUCache(routerInfo["maxSize"])}
            elif routerInfo["type"] == "LFU":
                cacheMemoryDict[routerId] = {"type": "LFU", "memory": LFUCache(routerInfo["maxSize"])}
            elif routerInfo["type"] == "FIFO":
                cacheMemoryDict[routerId] = {"type": "FIFO", "memory": FIFOCache(routerInfo["maxSize"])} 
            elif routerInfo["type"] == "Hyrid":
                cacheMemoryDict[routerId] = {"type": "Hyrid", 
                                                    "memory": ColorCache(None, routerInfo["capacityRatio"] , routerInfo["maxSize"])}
    return cacheMemoryDict
    
def runSimulationWithRealDataset(interval, fileSize, mode, routingTable, topo, colorList, runReqNums, warmUpReqNums, separatorRankIncrement, parallel_idx=0):
    graph = topo.graph
    cacheDict = topo.cacheMemoryDict
    custom_data = topo.contentGenerator.custom_data
    clientIds = topo.clientIds
    contentGenerator = topo.contentGenerator
    cacheCapacity = cacheDict[list(cacheDict.keys())[0]].maxSize
    traffic = 0
    hit, hit1, miss = 0,0,0
    result = {}
    for i in range(interval):
        print("Interval %s" % str(i))
        uniqueSortedContentList = topo.contentGenerator.uniqueSortedContentList["Interval%s" % str(i)]
        if mode == "no-color":
            hitRateDict, traffic = runWithShortestPath(graph, cacheDict, fileSize, mode, routingTable, custom_data, clientIds, "Interval"+str(i))
        elif mode == "full-color": # color
            nearestColorServerInfo = colorRouteInfo
            serverToColorMap = serverToColorMap
            
            
            rankInfo = compute_rank(len(colorList), cacheCapacity, fileSize, graph, nearestColorServerInfo, contentGenerator,
                                                             cacheDict,  serverToColorMap, warmUpReqNums, runReqNums, 
                                                            clientIds, separatorRankIncrement, "Interval"+str(i))
            contentToColorDict = colorizeWithSeparatorRanks(uniqueSortedContentList, rankInfo["S"], len(colorList)) 
            hitRateDict, traffic = runWithColorRouting(graph, cacheDict, contentToColorDict, nearestColorServerInfo, 
                                   serverToColorMap, fileSize, routingTable, custom_data, clientIds, "Interval"+str(i))
        elif mode == "tag-color": # color
            nearestColorServerInfo = colorRouteInfo
            rankInfo = compute_rank_shortest_path_with_color(len(colorList), cacheCapacity, fileSize, graph, nearestColorServerInfo, contentGenerator,
                                        cacheDict, warmUpReqNums, runReqNums, 
                                        clientIds, separatorRankIncrement, "Interval"+str(i))
            contentToColorDict = colorizeWithSeparatorRanks(uniqueSortedContentList, rankInfo["S"], len(colorList)) 
            hitRateDict, traffic = runWithShortestPath(graph, cacheDict, fileSize, mode, routingTable, custom_data, clientIds, "Interval"+str(i), contentToColorDict)
        else:
            hitRateDict, traffic = runWithShortestPath(graph, cacheDict, fileSize, mode, routingTable, custom_data, clientIds, "Interval"+str(i))

    return traffic

def runSimulationWithPredefinedDistribution(fileSize, mode, routingTable, topo, colorList, runReqNums, warmUpReqNums, separatorRankIncrement, parallel_idx=0):
    graph = topo.graph
    cacheDict = topo.cacheMemoryDict
    custom_data = topo.contentGenerator.custom_data
    clientIds = topo.clientIds
    uniqueSortedContentList = topo.contentGenerator.uniqueSortedContentList["noInterval"]
    contentGenerator =topo.contentGenerator
    cacheCapacity = cacheDict[list(cacheDict.keys())[0]].maxSize
    traffic = 0
    hit, hit1, miss = 0,0,0
    generateData = {}
    for client in topo.clientIds:
        cacheId = client.replace("client", "Cache")
        generateData[cacheId] = {"noInterval": topo.contentGenerator.randomGen(runReqNums)}
            
    if mode == "no-color":
        hitRateDict, traffic = runWithShortestPath(graph, cacheDict, fileSize, mode, routingTable, generateData, clientIds, "noInterval")
    elif mode == "full-color": # color
        nearestColorServerInfo = topo.colorRouteInfo
        serverToColorMap = topo.serverToColorMap
        rankInfo = compute_rank(len(colorList), cacheCapacity, fileSize, graph, nearestColorServerInfo, contentGenerator,
                                                            cacheDict,  serverToColorMap, warmUpReqNums, runReqNums, 
                                                            clientIds, separatorRankIncrement, "noInterval", parallel_idx)
        contentToColorDict = colorizeWithSeparatorRanks(uniqueSortedContentList, rankInfo["S"], len(colorList)) 
        hitRateDict, traffic = runWithColorRouting(graph, rankInfo['cacheDict'], contentToColorDict, nearestColorServerInfo, 
                                serverToColorMap, fileSize, routingTable, generateData, clientIds, "noInterval")
    elif mode == "tag-color": # color
        nearestColorServerInfo = topo.colorRouteInfo
        rankInfo = compute_rank_shortest_path_with_color(len(colorList), cacheCapacity, fileSize, graph, nearestColorServerInfo, contentGenerator,
                                    cacheDict, warmUpReqNums, runReqNums, 
                                    clientIds, separatorRankIncrement, "noInterval", parallel_idx)

        contentToColorDict = colorizeWithSeparatorRanks(uniqueSortedContentList, rankInfo["S"], len(colorList)) 
        hitRateDict, traffic = runWithShortestPath(graph, rankInfo['cacheDict'], fileSize, mode, routingTable, generateData, clientIds, "noInterval", contentToColorDict)
    else:
        hitRateDict, traffic = runWithShortestPath(graph, cacheDict, fileSize, mode, routingTable, generateData, clientIds, "noInterval")
    
    return traffic
    
if __name__ == '__main__':
    global dataPath
    
    jsonFile = "/home/loclh/cdn_configuration_optimization/config/json/france_cdn.json"
    configDirPath = "/home/loclh/cdn_configuration_optimization/config/france_cdn/"
    dataPath = "/home/loclh/cdn_configuration_optimization/data/"
    
    config = loadJSON(jsonFile)
    interval = 1 if "custom" not in config["RequestModels"] else config["RequestModels"]["custom"]["interval"]
    mode = config["RoutingMode"]  # [no-cache, no-color, tag-color, full-color]
    fileSize = config["FileSize"]
    runReqNums = config["RunReqNums"] if "RunReqNums" in config else -1
    warmUpReqNums = config["WarmUpReqNums"] if "WarmUpReqNums" in config else -1
    colorNums = config["colorNums"]
    separatorRankIncrement = config["separatorRankIncrement"]
    
    colorList = [''.join(random.choices(string.ascii_uppercase + string.digits, k=6)) for i in range(colorNums)]
    
    topo = NetTopology(config, configDirPath, mode, warmUpReqNums, fileSize, colorList)
    topo.build()
    routingTable = {}
    print("*** Start runing simulation ***")
    if topo.contentGenerator.dist == None:
        result = runSimulationWithRealDataset(interval, fileSize, mode, routingTable, topo, colorList, runReqNums, warmUpReqNums, separatorRankIncrement)
    else:
        MAX_COUNT_INDEX = 0
        result = runSimulationWithPredefinedDistribution(fileSize, mode, routingTable, topo, colorList, runReqNums, warmUpReqNums, separatorRankIncrement)
    print(result)
