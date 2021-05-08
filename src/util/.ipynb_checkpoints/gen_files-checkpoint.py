from scipy.stats import gamma
import random
import math
import operator, os
import itertools, random
import matplotlib.pyplot as plt 
import numpy as np

class ZipfDistribution:
    def __init__(self, skewness, length, sampleGen=None):
        self.denominator = 0
        self.pdfMemo = []
        self.cdfMemo = []
        self.skewness = skewness
        self.sampleGen = sampleGen
        
        self.length = length
        for i in range(1, self.length+1):
            self.denominator += 1.0 / (i ** self.skewness)

        self.pdfMemo = [1.0/ (1.0 ** self.skewness)/self.denominator]
        self.cdfMemo = [1.0/ (1.0 ** self.skewness)/self.denominator]
        
        for i in range(2, self.length+1):
            self.pdfMemo += [1.0/(float(i) ** self.skewness)/self.denominator]
            self.cdfMemo += [self.cdfMemo[i-2] + (1.0/(float(i) ** self.skewness))/self.denominator]
            
    def PDF(self, rank):
        return self.pdfMemo[rank -1]
    
    def CDF(self, rank):
        return self.cdfMemo[rank -1]
    
    def Intn(self):
        mark = random.random() 
        for i in range(1, self.length+1):
            if self.cdfMemo[i-1] > mark:
                return i
            
    def pdf(self, x): # K = a, theta = lambda
        return math.pow(x, self.K-1) * math.exp(-x/self.theta) / (math.gamma(self.K) * math.pow(self.theta, self.K))	
    
    def inverseCDF(self, C):
        if C > 1 or C < 0:
            return

        tolerance = 0.01
        x = self.length / 2
        if self.skewness != 1:
            pD = C * (12 * (self.length ** (-self.skewness + 1) - 1) / (1 - self.skewness) + 6 + 6 * (self.length ** -self.skewness) + self.skewness - self.skewness * (self.length ** (-self.skewness - 1)))
        else:
            pD = C * (12 * math.log(self.length) + 6 + 6 * (self.length ** -self.skewness) + self.skewness - self.skewness * (self.length ** (-self.skewness - 1)))
            
        while True:
            m = x ** (-self.skewness - 2)   
            mx = m * x                
            mxx = mx * x              
            mxxx = mxx * x           
            if self.skewness != 1:
                a = 12 * (mxxx - 1) / (1 - self.skewness) + 6 + 6 * mxx + self.skewness - (self.skewness * mx) - pD
            else:
                a = 12 * math.log(x) + 6 + 6 * mxx + self.skewness - (self.skewness * mx) - pD
                
            b = 12 * mxx - (6 * self.skewness * mx) + (m * self.skewness * (self.skewness + 1))
            newx = max(1, x - a / b)
            if abs(newx - x) <= tolerance:
                return round(newx)
            x = newx
        
                  
class GammaDistribution:
    def __init__(self, K, theta, length, sampleGen=None):
        self.K = K
        self.theta = theta
        self.sum = 0
        self.sampleGen = sampleGen
        self.pdfMemo = []
        self.cdfMemo = []
        self.length = length
        for i in range(1, self.length+1):
            self.sum += self.pdf(i)

        self.pdfMemo = [self.pdf(1.0)/self.sum]
        self.cdfMemo = [self.pdf(1.0)/self.sum]
        
        for i in range(2, self.length+1):
            self.pdfMemo.append(self.pdf(i)/self.sum)
            self.cdfMemo.append(self.cdfMemo[i-2]+self.pdf(i)/self.sum)
            
            
    def PDF(self, rank):
        return self.pdfMemo[rank -1]
    
    def CDF(self, rank):
        return self.cdfMemo[rank -1]
    
    def Intn(self):
        mark = random.random() 
        for i in range(1, self.length+1):
            if self.cdfMemo[i-1] > mark:
                return i
            
    def pdf(self, x): # K = a, theta = lambda
        return math.pow(x, self.K-1) * math.exp(-x/self.theta) / (math.gamma(self.K) * math.pow(self.theta, self.K))


class ContentGenerator:
    def __init__ (self, dist=None, data_path="", fixedContentSize=-1, sampleGen=None, alpha=1.0):
        self.dist = dist
        self.data_path = data_path
        self.fixedContentSize = fixedContentSize
        self.sampleGen = sampleGen
        self.custom_data = None
        self.alpha = alpha
        if self.dist != None:
            self.getUniqueSortedContentList()
        else:
            self.getCustomData()
            self.getUniqueSortedCustomContentList()
            if sampleGen != None:
                self.samplingCustomData()
                
    def randomGen(self, reqNums):
        if self.dist == None:
            return None
        dic = {}
        i = 0

        while i < reqNums:
            temp = str(self.dist.Intn())
            if temp in dic:
                dic[temp] += 1
            else:
                dic[temp] = 1
            i += 1
        temp = []
        for key in dic:
            for freq in range(dic[key]):
                temp.append(key)

        random.shuffle(temp)
        if self.dist.sampleGen != None:
            temp = self.dist.sampleGen.sample(temp)
        result = []
        for i in temp:
            result.append((i, self.fixedContentSize))
        return result
    

    def getUniqueSortedContentList(self):
        if self.dist == None:
            return None
        dic = {}
        for i in range(self.dist.length * 10):
            temp = str(self.dist.Intn())
            if temp in dic:
                dic[temp] += 1
            else:
                dic[temp] = 1

        for i in range(1, self.dist.length + 1):
            if str(i) not in dic:
                dic[str(i)] = 0

        sorted_list = sorted(dic.items(), key=operator.itemgetter(1))
        sorted_list.reverse()
        self.uniqueSortedContentList = {"noInterval": [str(x[0]) for x in sorted_list]}
        
    
    def getUniqueSortedCustomContentList(self):
        content_freq = {}
        for cache in self.custom_data:
            for interval in self.custom_data[cache]:
                if interval not in content_freq:
                    content_freq[interval] = {}
                for info in self.custom_data[cache][interval]:
                    id = info[0]
                    if id not in content_freq[interval]:
                        content_freq[interval][id] = 1
                    else:
                        content_freq[interval][id] += 1
        result = {}
        for interval in content_freq:
            sorted_list = sorted(content_freq[interval].items(), key=operator.itemgetter(1))
            sorted_list.reverse()
            result[interval] = [x[0] for x in sorted_list]
        self.uniqueSortedContentList = result
            
    def getCustomData(self):
        result = {}
        if not os.path.isdir(self.data_path):
            print("[ERROR] Not valid directory")
        for r, d, f in os.walk(self.data_path):
            for file in f:
                if 'Cache_' in file:
                    cache = file.split(".")[0].strip()
                    interval = r.split("/")[-2].strip()
                    if "Interval" not in interval:
                        continue
                    fileIdList = []
                    with open(os.path.join(r, file), "r") as f:
                        for line in f:
                            if self.fixedContentSize != -1:
                                if len(line.strip().split(",")) > 1:
                                    if len(line.strip().split(",")) == 3:
                                        fileId, fileSize, timeStamp = line.strip().split(",")
                                        fileIdList.append([str(fileId), int(self.fixedContentSize), int(timeStamp)])
                                    else:
                                        fileId, fileSize = line.strip().split(",")
                                        fileIdList.append([str(fileId), self.fixedContentSize])
                            else:
                                if len(line.strip().split(",")) == 3:
                                    fileId, fileSize, timeStamp = line.strip().split(",")
                                    fileSize = float(fileSize) * self.alpha
                                    fileIdList.append([str(fileId), int(fileSize), int(timeStamp)])
                                else:
                                    fileId, fileSize = line.strip().split(",")
                                    fileSize = float(fileSize) * self.alpha
                                    fileIdList.append([str(fileId), int(fileSize)])
                               

                    if cache not in result:
                        result[cache] = {interval: fileIdList}
                    else:
                        result[cache][interval] = fileIdList
        
        self.custom_data = result
    
    
    def samplingCustomData(self):
        for cache in self.custom_data:
            for interval in self.custom_data[cache]:
                self.custom_data[cache][interval] = self.sampleGen.sample(self.custom_data[cache][interval])
         
            
    def getContentId(self, cacheId=None, intervalId=None):
        if clientId == None and intervalId == None and self.dist != None:
            return self.randomGen()
        elif clientId != None and intervalId != None and self.dist == None:
            return self.custom_data[cacheId][intervalId]
        else:
            print("[ERROR] Content Generator is wrong")
            
def chooseColorRoundRobin(numberColor, totalColor):
    colorArray = ["1"] * numberColor + ["0"] * (totalColor - numberColor)
    while True:
        permutations = set(itertools.permutations(colorArray))
        for i in permutations:
            yield "".join(i)
        
def colorizeWithSeparatorRanks(uniqueSortedContentList, separatorRanks, totalColor):
    result = {}
    numberContentAtPreviousRanks = 0
    for idx, numberContentAtThisRank in enumerate(separatorRanks):
        numberColorAtThisRank = len(separatorRanks) - idx
        genColor = chooseColorRoundRobin(numberColorAtThisRank, totalColor)
        
        for i in range(int(numberContentAtThisRank)):
            result[uniqueSortedContentList[i + numberContentAtPreviousRanks]] = next(genColor)
            
        numberContentAtPreviousRanks += numberContentAtThisRank
    for i in range(len(uniqueSortedContentList)):
        if uniqueSortedContentList[i] not in result:
            result[uniqueSortedContentList[i]] = "".join(["0"] * totalColor)
    return result

def colorizeWithRandom(uniqueContentList, totalColor):
    result = {}
    for content in uniqueContentList: 
        random_num = random.randint(0, totalColor)
        random_idx = random.sample(range(totalColor), random_num)
        tmp = ["0"] * totalColor
        for i in random_idx:
            tmp[i] = "1"
        result[content] = "".join(tmp)
    return result
    
# def readCustomWarmUpRequest(custom_data, clientId):
#     clientIdx = int(clientId.replace("client_", ""))
#     cache = "Cache_" + str(clientIdx)
#     if cache in custom_data:
#         return custom_data[cache]["Interval0"]
#     return None

