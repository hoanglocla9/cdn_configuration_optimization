
import networkx as nx
import numpy as np
import matplotlib.pyplot as plt
from src.util.utils import *
from operator import itemgetter


def getSortNodeList(graph) :
        # sort nodes V base on degree descendingly; value1 node name, value2 node degree
    sorted_V = sorted(graph.degree, key=lambda x: x[1], reverse=True)
    return sorted_V

def getCadidateColors(listOfColors, adjacent_colors):
    candidate_color = []
    for color in listOfColors :
        if color not in adjacent_colors:
            candidate_color.append(color)

    return candidate_color

#sort candidate_colors based on the minimal distance to the same color descendingly
def new_func(graph, candidate_colors, color_dict, current_node):
    path_length_to_same_color = []
    for candidate_color in candidate_colors:
        temp = []
        for color_node in color_dict.keys() :
            if candidate_color == color_dict[color_node]:
                temp = nx.dijkstra_path(graph, current_node,  color_node, "weight")
        path_length_to_same_color.append(len(temp))
    path_length_to_same_color = np.array(path_length_to_same_color)
    candidate_colors = np.array(candidate_colors)

    inds = path_length_to_same_color.argsort()

    sorted_candidate_colors = candidate_colors[inds]
    
    list_sorted_candidate_colors = sorted_candidate_colors.tolist()
    
    return list_sorted_candidate_colors[0] 

def checkInfor(graph):
    print("Number of Cache servers: {}".format(graph.number_of_nodes()))
    print("Graph nodes: {}".format(graph.nodes))
    for currentNode in graph.nodes:
        print("adj Node with {} : {}".format(currentNode, graph.adj[currentNode]))
        
def coloringServer(graph, listOfColors) :
        # sort nodes V base on degree descendingly; value1 node name, value2 node degree
    sorted_V = getSortNodeList(graph)

    color_dict = {}
    for i in sorted_V:
        color_dict.update({i[0]:None})

    for v in sorted_V:
        adjacent_colors = []
        for a in graph.adj[v[0]]:
            if (color_dict[a]) :
                adjacent_colors.append(color_dict[a])
        adjacent_colors.append(v[0])
        #candidate_colors = C except in adjacent_colors
        candidate_colors = getCadidateColors(listOfColors, adjacent_colors)

        #sort candidate_colors based on the minimal distance to the same color descendingly
        candidate_color = new_func(graph, candidate_colors, color_dict, v[0])

        #colorOfCurrentNode = candidate_color[0]
        color_dict.update({v[0]:candidate_color})
    return color_dict

def buildColorToServerMap(serverToColorMap):
    result = {}
    for serverId in serverToColorMap:
        color = serverToColorMap[serverId]
        if color in result:
            result[color].append(serverId)
        else:
            result[color] = [serverId]
    return result

def buildNearstColorServerInfo(graph, colorToServerMap, listOfColors):
    result = {}
    for currentNode in graph.nodes:
        result[currentNode] = []
        for color in colorToServerMap:
            temp = None
            minDistance = float("inf")
            for node in colorToServerMap[color]:
                if currentNode != node:
                    distance = nx.shortest_path_length(graph, source=currentNode,target=node)
                    if minDistance < distance:
                        continue
                    minDistance = distance
                    temp = {"color": color, "node": node, "distance": distance}
            
            if temp != None:
                result[currentNode].append(temp)
        result[currentNode] = sortRouteInfo(result[currentNode])
        
    return result

def sortRouteInfo(nodeRouteInfo): ### quick sort
    less = []
    equal = []
    greater = []

    if len(nodeRouteInfo) > 1:
        pivot = nodeRouteInfo[0]["distance"]
        for x in nodeRouteInfo:
            x_distance = x["distance"]
            if x_distance < pivot:
                less.append(x)
            elif x_distance == pivot:
                equal.append(x)
            elif x_distance > pivot:
                greater.append(x)
        return sortRouteInfo(less) + equal + sortRouteInfo(greater) 
    else:
        return nodeRouteInfo
                 
def getColoringInfo(graph, listOfColors):
    serverGraph = graph.copy()
    ### Remove all not necessary nodes
    for node in list(serverGraph):
        if "mainServer" in str(node):
            serverGraph.remove_node(node)

        if "client" in str(node):
            serverGraph.remove_node(node)
            
        if "mainClone" in str(node):
            serverGraph.remove_node(node)
            
    encodedListOfColors = []
    for color in listOfColors:
        encodedListOfColors.append(encodeColor([color], listOfColors))
        
#     serverToColorMap = coloringServer(serverGraph, encodedListOfColors)


    serverToColorMap = getServerToColorMap(serverGraph, encodedListOfColors)
    # print(serverToColorMap)
    colorToServerMap = buildColorToServerMap(serverToColorMap)
    
    nearstColorServerInfo = buildNearstColorServerInfo(serverGraph, colorToServerMap, listOfColors)
    
    checkColoringGraph(serverGraph, serverToColorMap, colorToServerMap)
    return nearstColorServerInfo, serverToColorMap

def checkColoringGraph(graph, serverToColorMap, colorToServerMap):
    for node in graph.nodes:
        if not "router" in node or node == "router_0":
            continue
        currentColor = serverToColorMap[node]
        for adj_node in graph.neighbors(node):
            if not "router" in adj_node or adj_node == "router_0":
                continue
            adjColor = serverToColorMap[adj_node]
            if adjColor == currentColor:
                print("false adj coloring")
                return False
    
    # for color in colorToServerMap:
    #     print(color + ": " + str(len(colorToServerMap[color])))
        
    
        
def getAvailableColorOfNode(graph, currentNode, listOfColor, serverToColorMap):
    candidateColorList = list(listOfColor)
    neighborList = [n for n in graph.neighbors(currentNode)]
    for neighborNode in neighborList:
        neighborColor = serverToColorMap[neighborNode]
        if neighborColor == None:
            continue
        if neighborColor in candidateColorList:
            candidateColorList.remove(neighborColor)
            
    return candidateColorList



def countColorInGraph(serverToColorMap, listOfColors):
    result = {}
    for server in serverToColorMap:
        serverColor = serverToColorMap[server]
        if serverColor == None:
            continue
        if serverColor not in result:
            result[serverColor] = 1
        else:
            result[serverColor] += 1
    return result

def selectDistantColor(graph, currentNode, avaiableColors, serverToColorMap, countColorMap):
    distances = {}
    for color in avaiableColors:
        distances[color] = 0
    
    for node in graph.nodes:
        if node == currentNode:
            continue
            
        nodeColor = serverToColorMap[node]
        if nodeColor == None or nodeColor not in avaiableColors:
            continue
        distanceToNode = nx.shortest_path_length(graph, currentNode, node)
        if distanceToNode < distances[nodeColor]:
            distances[nodeColor] = distanceToNode
   
    selectedColor = avaiableColors[0]
    maxDistance = distances[selectedColor]
    for i in range(len(avaiableColors)): 
        if distances[avaiableColors[i]] > maxDistance:
            maxDistance = distances[avaiableColors[i]]
            selectedColor = avaiableColors[i]
        if distances[avaiableColors[i]] == maxDistance:
            if countColorMap[selectedColor] > countColorMap[avaiableColors[i]]:
                selectedColor = avaiableColors[i]
    return selectedColor
        
    
def getServerToColorMap(graph, listOfColors):
    serverToColorMap = {}
    for node in graph.nodes:
        serverToColorMap[node] = None
    
    verticesDegrees = []
        
        ### find degree
    for currentNode in graph.nodes: 
        verticesDegrees.append((currentNode, graph.degree[currentNode]))
        
    sortedVerticesDegrees = sorted(verticesDegrees, key=lambda k: k[1], reverse=True)
    
        ### 
    for i in range(len(sortedVerticesDegrees)): 
        currentNode = sortedVerticesDegrees[i][0]
        ### find available color
        availableColors = getAvailableColorOfNode(graph, currentNode, listOfColors, serverToColorMap)
        if i >= len(listOfColors):
            countColorMap = countColorInGraph(serverToColorMap, listOfColors)
            selectedColor = selectDistantColor(graph, currentNode, availableColors, serverToColorMap, countColorMap)
        else:
            selectedColor = listOfColors[i]
        serverToColorMap[currentNode] = selectedColor
        
    return serverToColorMap