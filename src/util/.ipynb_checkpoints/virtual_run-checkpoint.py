import networkx as nx
import random, pickle
from src.util.gen_files import *
 
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
    

def processRequestFlow(sourceCacheId, cacheDict, graph, nearestColorServerInfo, serverToColorMap, contentId, contentColor, routingTable):
    packetPath = ["0"] * len(list(cacheDict.keys()))
    
    currentCacheId = sourceCacheId
    while True:
        if currentCacheId == "mainServer":
            return currentCacheId
        if cacheDict[currentCacheId].get(contentId, contentColor) != -1:
            return currentCacheId
        else:
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

def runVirtualSendFile(graph, cacheDict, client, contentId, contentColor, nearestColorServerInfo, 
                       serverToColorMap, fileSize, routingTable):
    traffic = 0
    sourceCacheId = client.replace("client_", "router_")
    targetCacheId = processRequestFlow(sourceCacheId, cacheDict, graph, nearestColorServerInfo, serverToColorMap, contentId, contentColor, routingTable)
    responseTraffic = processResponseFlow(targetCacheId, sourceCacheId, cacheDict, graph, contentId, contentColor, fileSize)
    traffic += responseTraffic
    
    return traffic

def refreshCache(cacheDict):
    for cacheId in cacheDict:
        cacheDict[cacheId].refresh()
        
def warmUpColor(graph, cacheDict, contentToColorDict, nearestColorServerInfo, serverToColorMap, fileSize, routingTable, warmUpReqDict, clientList):
    idx = 0
    while True:
        isEnd = True
        for client in clientList:
            if idx >= len(warmUpReqDict[client]):
                continue
            if fileSize != -1:
                contentId = warmUpReqDict[client][idx][0]
                _fileSize = fileSize
            else:
                contentId, _fileSize, _ = warmUpReqDict[client][idx]
                
            contentColor = contentToColorDict[contentId]
            runVirtualSendFile(graph, cacheDict, client, contentId, contentColor, 
                               nearestColorServerInfo, serverToColorMap, int(_fileSize), routingTable)
            isEnd = False
        if isEnd:
            break
        idx += 1
    return cacheDict

def runWithColorRouting(graph, cacheDict, contentToColorDict, nearestColorServerInfo, 
                               serverToColorMap, fileSize, routingTable, runReqDict, clientList=[]):
#     print(routingTable)
    totalTraffic = 0
    idx = 0
    while True:
        isEnd = True
        for client in clientList:
            if idx >= len(runReqDict[client]):
                continue
            if fileSize != -1:
                contentId = runReqDict[client][idx][0]
                _fileSize = fileSize
            else:
                contentId, _fileSize, _ = runReqDict[client][idx]
                
            contentColor = contentToColorDict[contentId]
            oneFileTraffic = runVirtualSendFile(graph, cacheDict, client, contentId, contentColor, 
                               nearestColorServerInfo, serverToColorMap, int(_fileSize), routingTable)
            totalTraffic += oneFileTraffic
            isEnd = False
        if isEnd:
            break
        idx+= 1
    return totalTraffic

def runVirtualSendFileShortestPath(graph, cacheDict, client, contentId, fileSize, routingTable, mode="no-color", contentColor=""):
    traffic = 0
    nextCacheId = client.replace("client_", "router_")
    
    if mode == "no-cache":
        shortestRoutePath = nx.dijkstra_path(graph, nextCacheId, "mainServer", "weight")
        shortestRoutePath = shortestRoutePath[1:] 
        for routerId in shortestRoutePath:
            traffic += 1
            if routerId == "mainServer":
                break
        return traffic
    
    if mode== "no-color":
        if cacheDict[nextCacheId] is None:
            pass
        else:
            if cacheDict[nextCacheId].get(contentId) != -1:
                return traffic
            else:
                cacheDict[nextCacheId].set(contentId, fileSize)

        while True:
            routerId = findShortestCacheServer(graph, nextCacheId, "mainServer", routingTable)
            traffic += 1
            if routerId == "mainServer":
                return traffic
            else:
                if cacheDict[routerId] is None:
                    pass
                else:
                    if cacheDict[routerId].get(contentId) == -1:
                        cacheDict[routerId].set(contentId, fileSize)
                    else:
                        return traffic
                    
            nextCacheId = routerId
    else: ## mode == "tag-color"
        if cacheDict[nextCacheId] is None:
            pass
        else:
            if cacheDict[nextCacheId].get(contentId, contentColor) != -1:
                return traffic
            else:
                cacheDict[nextCacheId].set(contentId, contentColor, fileSize)

        while True:
            routerId = findShortestCacheServer(graph, nextCacheId, "mainServer", routingTable)
            traffic += 1
            if routerId == "mainServer":
                return traffic
            else:
                if cacheDict[routerId] is None:
                    pass
                else:
                    if cacheDict[routerId].get(contentId, contentColor) == -1:
                        cacheDict[routerId].set(contentId, contentColor, fileSize)
                    else:
                        return traffic
            nextCacheId = routerId
        
    return traffic


def warmUpCacheShortestPath(graph, cacheDict, fileSize, mode, routingTable, warmUpReqDict, clientList=[], contentToColorDict=None):
    idx = 0
    while True:
        isEnd = True
        for client in clientList:
            if idx >= len(warmUpReqDict[client]):
                continue
            if fileSize != -1:
                contentId = warmUpReqDict[client][idx][0]
                _fileSize = fileSize
            else:
                contentId, _fileSize, _ = warmUpReqDict[client][idx]
            if mode == "tag-color":
                contentColor = str(contentToColorDict[contentId])
            else:
                contentColor = ""
            runVirtualSendFileShortestPath(graph, cacheDict, client, contentId, _fileSize, routingTable, mode, contentColor)
            isEnd = False
        if isEnd:
            break
        idx += 1
    
def runWithShortestPath(graph, cacheDict, fileSize, mode, routingTable, runReqDict, clientList, contentToColorDict=None):
    totalTraffic = 0
    idx = 0
    while True:
        isEnd = True
        for client in clientList:
            if idx >= len(runReqDict[client]):
                continue
            if fileSize != -1:
                contentId = runReqDict[client][idx][0]
                _fileSize = fileSize
            else:
                contentId, _fileSize, _ = runReqDict[client][idx]
            if mode == "tag-color":
                contentColor = str(contentToColorDict[contentId])
            else:
                contentColor == ""
            oneFileTraffic = runVirtualSendFileShortestPath(graph, cacheDict, client, contentId, _fileSize, routingTable, mode, contentColor)
            totalTraffic += oneFileTraffic
            isEnd = False
        if isEnd:
            break
        idx += 1
    return totalTraffic

